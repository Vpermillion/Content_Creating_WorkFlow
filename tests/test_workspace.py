import copy
import io
import json
import sqlite3
import tarfile
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
from whatif.store import Store, digest, identifier
from whatif import pipeline, backup, tts
from whatif.server import make_server

ROOT=Path(__file__).resolve().parents[1]


def spec(job="test-pilot"):
    data=json.loads((ROOT/"pilots/pilot-001.json").read_text())
    data["id"]=job
    data["profile"].update(width=360,height=640,min_seconds=1,max_seconds=30)
    data["scenes"]=[{"text":"Imagine the Moon disappears. This is an illustration.","visual":"earth-moon","label":"AN IMPOSSIBLE CHANGE"},
                    {"text":"The Sun still contributes to ocean tides.","visual":"tides","label":"TIDES WOULD CHANGE"}]
    return data


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.store=Store(self.root/"state")
        self.store.add(spec())
    def tearDown(self): self.temp.cleanup()

    def test_immutable_inputs_and_unique_topic_id(self):
        self.store.add(spec())
        changed=spec(); changed["scenes"][0]["text"]="Changed approved content."
        with self.assertRaises(ValueError): self.store.add(changed)
        repeated=spec("another-id")
        with self.assertRaisesRegex(ValueError,"Topic title already exists"): self.store.add(repeated)
        self.assertEqual(len(self.store.snapshot()["jobs"]),1)

    def test_lease_exclusion_and_expired_worker_recovery(self):
        owner=self.store.claim("test-pilot",seconds=-1)
        successor=Store(self.store.root).claim("test-pilot")
        with self.assertRaises(RuntimeError): self.store.heartbeat("test-pilot",owner)
        with self.assertRaises(RuntimeError): self.store.start("test-pilot","render",owner=owner)
        with self.assertRaises(RuntimeError): self.store.claim("test-pilot")
        self.store.release("test-pilot",owner)
        self.store.heartbeat("test-pilot",successor)
        self.store.release("test-pilot",successor)

    def test_simultaneous_workers_have_one_winner(self):
        barrier=threading.Barrier(2)
        outcomes=[]
        def claim():
            barrier.wait()
            try: outcomes.append(self.store.claim("test-pilot"))
            except RuntimeError: outcomes.append(None)
        threads=[threading.Thread(target=claim) for _ in range(2)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(sum(v is not None for v in outcomes),1)

    def test_publication_duplicates_uncertainty_and_platform_isolation(self):
        youtube=self.store.draft("test-pilot","youtube",{"video":"test"})
        self.store.draft("test-pilot","youtube",{"video":"test"})
        insta=self.store.draft("test-pilot","instagram",{"video":"test"})
        self.assertEqual(len(self.store.snapshot()["publications"]),2)
        with self.assertRaises(PermissionError): self.store.begin_delivery(youtube["idempotency_key"])
        with self.assertRaises(RuntimeError): self.store.begin_delivery(youtube["idempotency_key"],authorized=True)
        # State-machine test only. No provider is called or represented as connected.
        self.store.set_status("test-pilot","ready","test fixture")
        self.store.begin_delivery(youtube["idempotency_key"],authorized=True)
        with self.assertRaises(RuntimeError): self.store.begin_delivery(youtube["idempotency_key"],authorized=True)
        self.store.receipt(youtube["idempotency_key"],{"state":"published","provider_id":"test-only-receipt"})
        self.assertEqual(self.store.draft("test-pilot","instagram",{})["state"],"draft")
        with self.assertRaises(RuntimeError): self.store.begin_delivery(youtube["idempotency_key"],authorized=True)

    def test_backup_restore_and_active_lease_refusal(self):
        artifact=self.store.root/"nested/file.txt"
        artifact.parent.mkdir(); artifact.write_text("preserve me")
        owner=self.store.claim("test-pilot")
        with self.assertRaises(RuntimeError): backup.backup(self.store,self.root/"bad.tgz")
        self.store.release("test-pilot",owner)
        archive=backup.backup(self.store,self.root/"good.tgz")
        restored=backup.restore(archive,self.root/"restored")
        self.assertEqual((restored/"nested/file.txt").read_text(),"preserve me")
        self.assertEqual(Store(restored).get("test-pilot")["version"],self.store.get("test-pilot")["version"])
        with self.assertRaises(ValueError): backup.restore(archive,restored)

    def test_archive_traversal_rejected(self):
        archive=self.root/"malicious.tgz"
        with tarfile.open(archive,"w:gz") as t:
            info=tarfile.TarInfo("state/../../escape"); info.size=1
            t.addfile(info,io.BytesIO(b"x"))
        with self.assertRaises(ValueError): backup.restore(archive,self.root/"restore")
        self.assertFalse((self.root/"escape").exists())

    def test_kaggle_wrong_run_and_missing_outputs_rejected(self):
        batch=tts.export_batch(self.store,["test-pilot"],self.root/"input.json")
        folder=self.root/"outputs"; folder.mkdir()
        (folder/"output.json").write_text(json.dumps({"schema_version":1,"batch_id":batch["batch_id"],"jobs":[]}))
        with self.assertRaises(ValueError): tts.import_batch(self.store,folder)
        self.assertIsNone(self.store.stage("test-pilot","narration"))

    def test_bounded_retries(self):
        for _ in range(3):
            self.store.start("test-pilot","render")
            self.store.fail("test-pilot","render","test failure")
            with self.store.connect() as db: db.execute("UPDATE stages SET retry_at=0")
        with self.assertRaises(RuntimeError): self.store.start("test-pilot","render")

    def test_validation_rejects_filter_and_path_control(self):
        for value in ("../../escape","a;whoami","x/y","UPPER"):
            with self.assertRaises(ValueError): identifier(value)
        bad=spec(); bad["scenes"][0]["text"]="{\\an8}subtitle control"
        with self.assertRaises(ValueError): pipeline.validate_spec(bad)

    def test_worker_authentication_and_functional_status(self):
        server=make_server(self.store,"127.0.0.1",0,"x"*64)
        t=threading.Thread(target=server.serve_forever); t.start()
        url=f"http://127.0.0.1:{server.server_port}"
        # Local-only requests should not leave through an inherited HTTP proxy.
        client=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            self.assertTrue(json.load(client.open(url+"/health"))["ok"])
            with self.assertRaises(urllib.error.HTTPError) as error: client.open(url+"/jobs/test-pilot")
            self.assertEqual(error.exception.code,401)
            req=urllib.request.Request(url+"/jobs/test-pilot",headers={"Authorization":"Bearer "+"x"*64})
            self.assertEqual(json.load(client.open(req))["status"],"queued")
        finally:
            server.shutdown(); server.server_close(); server.executor.shutdown(); t.join()


class MediaTests(StateTests):
    # A real FFmpeg path, not a mocked render. Other inherited state tests are excluded below.
    def test_render_failure_resume_preserves_speech_and_detects_corruption(self):
        with patch("whatif.media.render",side_effect=RuntimeError("simulated worker failure after speech")):
            with self.assertRaises(RuntimeError): pipeline.run(self.store,"test-pilot")
        folder=self.store.root/"jobs/test-pilot"
        speech_hash=digest(folder/"narration.wav")
        speech_mtime=(folder/"narration.wav").stat().st_mtime_ns
        with self.store.connect() as db: db.execute("UPDATE stages SET retry_at=0")
        output=pipeline.run(Store(self.store.root),"test-pilot")
        report=json.loads((folder/"quality.json").read_text())
        self.assertTrue(report["automated_pass"])
        self.assertFalse(report["publish_ready"])
        self.assertEqual(self.store.get("test-pilot")["status"],"quality_review")
        mtime=output.stat().st_mtime_ns
        pipeline.run(Store(self.store.root),"test-pilot")
        self.assertEqual(mtime,output.stat().st_mtime_ns)
        self.assertEqual(speech_hash,digest(folder/"narration.wav"))
        self.assertEqual(speech_mtime,(folder/"narration.wav").stat().st_mtime_ns)
        external=spec("external-voice")
        external["title"]="External narration fixture"
        self.store.add(external)
        batch=tts.export_batch(self.store,["external-voice"],self.root/"external-input.json")
        outputs=self.root/"external-output"; outputs.mkdir()
        import shutil
        shutil.copy2(folder/"narration.wav",outputs/"external-voice.wav")
        manifest={"schema_version":1,"batch_id":batch["batch_id"],"jobs":[{
            "job_id":"external-voice","content_version":self.store.get("external-voice")["version"],
            "file":"external-voice.wav","sha256":speech_hash,
            "segments":json.loads((folder/"narration.json").read_text())["segments"]}]}
        (outputs/"output.json").write_text(json.dumps(manifest))
        self.assertEqual(tts.import_batch(self.store,outputs),["external-voice"])
        pipeline.run(self.store,"external-voice")
        external_narration=json.loads((self.store.root/"jobs/external-voice/narration.json").read_text())
        self.assertEqual(external_narration["batch_id"],batch["batch_id"])
        self.assertEqual(digest(self.store.root/"jobs/external-voice/narration.wav"),speech_hash)
        output.write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError,"Checkpoint artifact changed"):
            pipeline.run(Store(self.store.root),"test-pilot")


# Avoid running the same inherited state tests twice.
def load_tests(loader, tests, pattern):
    suite=unittest.TestSuite(loader.loadTestsFromTestCase(StateTests))
    suite.addTest(MediaTests("test_render_failure_resume_preserves_speech_and_detects_corruption"))
    return suite
