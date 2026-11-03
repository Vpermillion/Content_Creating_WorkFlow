import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    Fernet = None
from scripts import youtube_upload_state as state


@unittest.skipIf(Fernet is None,'Optional publishing encryption dependency not installed')
class UploadStateTests(unittest.TestCase):
    def test_private_session_restores_only_from_authenticated_ciphertext(self):
        key=Fernet.generate_key();f=Fernet(key)
        plain={'episode.json':{'id':'episode','session_url':'https://www.googleapis.com/upload/youtube/v3/videos?upload_id=fixture'}}
        blob=f.encrypt(json.dumps(plain).encode())
        self.assertNotIn(b'upload_id',blob)
        def git(*args,**kwargs):
            if args[0]=='ls-remote':return b'fixture refs/heads/codex/youtube-upload-state'
            if args[0]=='show':return blob
            return b''
        with tempfile.TemporaryDirectory() as t,patch.object(state,'ROOT',Path(t)),patch.object(state,'git',side_effect=git),patch.dict(os.environ,{'YOUTUBE_UPLOAD_STATE_KEY':key.decode()}):
            state.restore();p=Path(t)/'private/youtube-upload-state/episode.json'
            self.assertEqual(json.loads(p.read_text()),plain['episode.json'])
            self.assertEqual(p.stat().st_mode & 0o777,0o600)

    def test_wrong_key_does_not_restore_or_overwrite_any_journal(self):
        blob=Fernet(Fernet.generate_key()).encrypt(b'{"episode.json":{"state":"uploading"}}')
        def git(*args,**kwargs):return blob if args[0]=='show' else b'fixture'
        with tempfile.TemporaryDirectory() as t,patch.object(state,'ROOT',Path(t)),patch.object(state,'git',side_effect=git),patch.dict(os.environ,{'YOUTUBE_UPLOAD_STATE_KEY':Fernet.generate_key().decode()}):
            with self.assertRaises(InvalidToken):state.restore()
            self.assertEqual(list((Path(t)/'private/youtube-upload-state').glob('*.json')),[])
