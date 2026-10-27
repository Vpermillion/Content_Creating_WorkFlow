"""Offline credential/provider fixtures only; never contact Google or publish."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from whatif import youtube as yt

ID_A = "UC" + "a" * 22
ID_B = "UC" + "b" * 22


class Credentials:
    def __init__(self, valid=True, scope=True, refresh_token="fixture-refresh"):
        self.valid, self.scope, self.refresh_token = valid, scope, refresh_token
        self.granted_scopes = [yt.READ_SCOPE] if scope else []
        self.token = "fixture-access"
        self.refresh_count = 0

    def has_scopes(self, scopes):
        return self.scope and scopes == [yt.READ_SCOPE]

    def refresh(self, request):
        self.refresh_count += 1
        self.valid = True
        self.token = "fixture-refreshed"

    def to_json(self):
        return json.dumps({"token": self.token, "refresh_token": self.refresh_token,
                           "token_uri": yt.TOKEN_URI, "client_id": "fixture.apps.googleusercontent.com",
                           "client_secret": "fixture-secret", "scopes": [yt.READ_SCOPE]})


def item(channel_id=ID_A, handle="@ifverse_anime"):
    return {"id": channel_id, "snippet": {"title": "Ifverse Anime", "customUrl": handle}}


def response(items=None, status=200, **extra):
    result = Mock(status_code=status)
    result.json.return_value = {"items": items if items is not None else [item()], **extra}
    return result


class YouTubeConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = yt.ConnectionStore(self.root / "private")
        self.creds = Credentials()
        self.flow_class = Mock()
        self.flow_class.from_client_config.return_value.run_local_server.return_value = self.creds
        self.credentials_class = Mock()
        self.credentials_class.from_authorized_user_info.return_value = self.creds
        self.session = Mock()
        self.session.get.return_value = response()
        self.session_factory = Mock(return_value=self.session)
        self.sdk_patch = patch.object(yt, "sdk", return_value=(self.flow_class, self.credentials_class, Mock(), self.session_factory))
        self.sdk_patch.start()
        self.client = self.root / "client.json"
        self.client.write_text(json.dumps({"installed": {"client_id": "fixture.apps.googleusercontent.com",
            "client_secret": "fixture-secret", "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": yt.TOKEN_URI}}))

    def tearDown(self):
        self.sdk_patch.stop()
        self.temp.cleanup()

    def connect(self, **kwargs):
        return yt.connect(self.store, "alpha-anime", self.client, expected_handle="@ifverse_anime", **kwargs)

    def test_connect_checks_owned_identity_before_saving_and_uses_pkce(self):
        result = self.connect()
        self.assertEqual(result["channel_id"], ID_A)
        self.assertEqual(result["status"], "verified_readonly")
        self.assertFalse(result["publishing_enabled"])
        self.assertNotIn("fixture-", json.dumps(result))
        self.assertEqual(self.store.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.store.path("alpha-anime").stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.flow_class.from_client_config.call_args.kwargs["autogenerate_code_verifier"])
        call = self.flow_class.from_client_config.return_value.run_local_server.call_args.kwargs
        self.assertEqual(call["host"], "127.0.0.1")
        self.assertEqual(call["access_type"], "offline")
        self.assertFalse(call["open_browser"])
        request = self.session.get.call_args
        self.assertEqual(request.args[0], yt.CHANNELS_URL)
        self.assertEqual(request.kwargs["params"]["mine"], "true")
        self.assertFalse(request.kwargs["allow_redirects"])

    def test_wrong_channel_or_empty_result_never_saves(self):
        for items in ([item(ID_B, "@other")], []):
            self.session.get.return_value = response(items=items)
            with self.assertRaises(yt.ConnectionError):
                self.connect()
            self.assertFalse(self.store.path("alpha-anime").exists())

    def test_scope_denial_and_missing_offline_access_do_not_save(self):
        self.creds.granted_scopes = []
        with self.assertRaisesRegex(yt.ConnectionError, "consent"):
            self.connect()
        self.creds.granted_scopes = [yt.READ_SCOPE]
        self.creds.refresh_token = None
        with self.assertRaisesRegex(yt.ConnectionError, "refresh token"):
            self.connect()
        self.assertFalse(self.store.path("alpha-anime").exists())

    def test_reconnect_cannot_overwrite_different_channel(self):
        self.connect()
        original = self.store.path("alpha-anime").read_bytes()
        with self.assertRaisesRegex(yt.ConnectionError, "already has credentials"):
            self.connect()
        self.session.get.return_value = response(items=[item(ID_B)])
        with self.assertRaisesRegex(yt.ConnectionError, "different channel"):
            self.connect(replace=True)
        self.assertEqual(original, self.store.path("alpha-anime").read_bytes())

    def test_expired_token_refresh_and_live_identity_check(self):
        self.connect()
        self.creds.valid = False
        result = yt.check(self.store, "alpha-anime")
        self.assertEqual(self.creds.refresh_count, 1)
        self.assertEqual(result["status"], "verified_readonly")
        self.assertEqual(self.store.load("alpha-anime")["credentials"]["token"], "fixture-refreshed")
        self.session.get.return_value = response(items=[item(ID_B, "@other")])
        with self.assertRaisesRegex(yt.ConnectionError, "does not match"):
            yt.check(self.store, "alpha-anime")

    def test_refresh_failure_and_http_denial_remain_blocked(self):
        self.connect()
        original = self.store.path("alpha-anime").read_bytes()
        self.creds.valid = False
        self.creds.refresh = Mock(side_effect=RuntimeError("sensitive-provider-detail"))
        with self.assertRaisesRegex(yt.ConnectionError, "refresh failed"):
            yt.check(self.store, "alpha-anime")
        self.assertEqual(original, self.store.path("alpha-anime").read_bytes())
        self.creds.valid = True
        for status in (401, 403, 429, 500, 302):
            self.session.get.return_value = response(status=status)
            with self.assertRaises(yt.ConnectionError):
                yt.check(self.store, "alpha-anime")

    def test_cached_status_never_claims_live_check_and_cli_redacts_errors(self):
        self.connect()
        result = self.store.cached()
        self.assertEqual(result[0]["status"], "stored_not_live_checked")
        self.assertNotIn("fixture-", json.dumps(result))
        self.session.get.side_effect = RuntimeError("fixture-refresh secret provider URL")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = yt.main(["--credentials-dir", str(self.store.root), "check", "--connection", "alpha-anime"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())["status"], "blocked")
        self.assertNotIn("fixture-", output.getvalue())

    def test_provider_pagination_completes_and_loop_is_rejected(self):
        self.session.get.side_effect = [response(nextPageToken="page2"), response(items=[item(ID_B, "@other")])]
        channels = yt.owned_channels(self.creds, self.session_factory)
        self.assertEqual({c["id"] for c in channels}, {ID_A, ID_B})
        self.session.get.side_effect = None
        self.session.get.return_value = response(nextPageToken="repeated")
        with self.assertRaisesRegex(yt.ConnectionError, "pagination"):
            yt.owned_channels(self.creds, self.session_factory)

    def test_secret_path_permissions_alias_validation_and_locking(self):
        with self.assertRaises(yt.ConnectionError):
            self.store.path("../../escape")
        with self.store.lock("alpha-anime"):
            with self.assertRaisesRegex(yt.ConnectionError, "Another operation"):
                with self.store.lock("alpha-anime"):
                    pass
        self.connect()
        self.store.path("alpha-anime").chmod(0o644)
        with self.assertRaisesRegex(yt.ConnectionError, "owner-only"):
            self.store.load("alpha-anime")

    def test_client_rejects_web_or_untrusted_token_endpoint(self):
        data = json.loads(self.client.read_text())
        data["installed"]["token_uri"] = "https://example.com/token"
        self.client.write_text(json.dumps(data))
        with self.assertRaisesRegex(yt.ConnectionError, "Google Desktop"):
            self.connect()
        self.flow_class.from_client_config.assert_not_called()

    def test_expected_identity_cannot_be_an_email_or_an_absent_selection(self):
        for handle in ("owner@example.invalid", "https://example.invalid/channel", ""):
            with self.assertRaises(yt.ConnectionError):
                yt.connect(self.store, "alpha-anime", self.client, expected_handle=handle)
        with self.assertRaises(yt.ConnectionError):
            yt.connect(self.store, "alpha-anime", self.client)
        self.flow_class.from_client_config.assert_not_called()

    def test_bind_writes_verified_metadata_only_and_rejects_wrong_or_duplicate_binding(self):
        self.connect()
        registry = self.root / "registry.json"
        registry.write_text(json.dumps({"publishing_authorized": False, "channels": [
            {"slot_id": "alpha-1", "channel_id": None, "setup_blocker": "old"},
            {"slot_id": "alpha-2", "channel_id": None}]}))
        original = registry.read_bytes()
        with self.assertRaises(yt.ConnectionError):
            yt.bind_registry(self.store, "alpha-anime", registry, "alpha-1", ID_B)
        self.assertEqual(original, registry.read_bytes())
        yt.bind_registry(self.store, "alpha-anime", registry, "alpha-1", ID_A)
        data = json.loads(registry.read_text())
        self.assertEqual(data["channels"][0]["channel_id"], ID_A)
        self.assertNotIn("setup_blocker", data["channels"][0])
        self.assertFalse(data["publishing_authorized"])
        self.assertNotIn("fixture-", registry.read_text())
        with self.assertRaisesRegex(yt.ConnectionError, "another slot"):
            yt.bind_registry(self.store, "alpha-anime", registry, "alpha-2", ID_A)


if __name__ == "__main__":
    unittest.main()
