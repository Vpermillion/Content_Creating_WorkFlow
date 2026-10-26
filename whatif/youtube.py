"""Read-only YouTube OAuth connections; separate from publishing and job state.

Linux/cloud CLI: python -m whatif.youtube --help
Google SDK imports are lazy so the existing standard-library worker is unchanged.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import tempfile

READ_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
TOKEN_URI = "https://oauth2.googleapis.com/token"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
ALIAS = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
CHANNEL_ID = re.compile(r"UC[A-Za-z0-9_-]{22}\Z")


class ConnectionError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def sdk():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request, AuthorizedSession
    except ImportError:
        raise ConnectionError("dependencies_missing", "Install requirements-youtube.txt in this runtime.") from None
    return InstalledAppFlow, Credentials, Request, AuthorizedSession


def now():
    return datetime.now(timezone.utc).isoformat()


def alias(value):
    if not isinstance(value, str) or not ALIAS.fullmatch(value):
        raise ConnectionError("invalid_alias", "Use a lowercase connection alias with letters, digits and hyphens.")
    return value


def require_channel_id(value):
    if not isinstance(value, str) or not CHANNEL_ID.fullmatch(value):
        raise ConnectionError("invalid_channel_id", "A canonical UC channel ID is required.")
    return value


def normalized_handle(value):
    if not isinstance(value, str) or not value.strip().lstrip("@"):
        raise ConnectionError("invalid_handle", "Supply the intended YouTube handle, not an account email or URL.")
    value = value.strip().lstrip("@")
    if any(c in value for c in "/?&#:\\@") or any(c.isspace() for c in value):
        raise ConnectionError("invalid_handle", "Supply a handle, not a URL or account identifier.")
    return value.casefold()


def atomic_json(path, value, mode=0o600):
    """Write once through a private temporary file; never expose partial tokens."""
    path = Path(path)
    if path.is_symlink():
        raise ConnectionError("unsafe_path", "Refusing a symbolic-link output file.")
    fd, temporary = tempfile.mkstemp(prefix=".youtube-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), mode)
            json.dump(value, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def file_lock(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ConnectionError("busy", "Another operation owns this connection or registry. Retry after it finishes.") from None
        yield
    finally:
        os.close(fd)


class ConnectionStore:
    def __init__(self, root):
        self.root = Path(root)

    def prepare(self):
        if self.root.is_symlink():
            raise ConnectionError("unsafe_path", "The credentials directory must not be a symbolic link.")
        self.root.mkdir(parents=True, mode=0o700, exist_ok=True)
        if self.root.stat().st_mode & 0o077:
            raise ConnectionError("unsafe_permissions", "The credentials directory must have owner-only permissions (0700).")

    def path(self, name):
        return self.root / (alias(name) + ".json")

    @contextmanager
    def lock(self, name):
        self.prepare()
        with file_lock(self.root / ("." + alias(name) + ".lock")):
            yield

    def load(self, name):
        path = self.path(name)
        if not path.exists():
            raise ConnectionError("not_connected", "No saved connection exists for this alias. Run connect first.")
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode) or path.stat().st_mode & 0o077:
            raise ConnectionError("unsafe_permissions", "Credential files must be regular owner-only files (0600).")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("schema_version") != 1 or record.get("connection") != name:
            raise ConnectionError("invalid_record", "Unsupported or mismatched private connection record.")
        require_channel_id(record.get("channel", {}).get("id"))
        info = record.get("credentials", {})
        if info.get("token_uri") != TOKEN_URI:
            raise ConnectionError("invalid_record", "Only Google's official token endpoint is supported.")
        return record

    def save(self, name, record):
        self.prepare()
        atomic_json(self.path(name), record)

    def cached(self):
        if not self.root.exists():
            return []
        self.prepare()
        records = []
        for path in sorted(self.root.glob("*.json")):
            if ALIAS.fullmatch(path.stem):
                records.append(summary(self.load(path.stem), live=False))
        return records


def summary(record, live):
    ch = record["channel"]
    # Explicit allowlist: never serialize the credentials or raw provider response.
    return {"connection": record["connection"], "status": "verified_readonly" if live else "stored_not_live_checked",
            "channel_id": ch["id"], "title": ch["title"], "handle": ch["handle"], "url": ch["url"],
            "last_verified_at": record["verified_at"], "publishing_enabled": False}


def owned_channels(credentials, session_factory):
    channels, pages, seen_pages = {}, 0, set()
    session = session_factory(credentials)
    try:
        token = None
        while True:
            params = {"part": "snippet", "mine": "true", "maxResults": 50}
            if token:
                params["pageToken"] = token
            response = session.get(CHANNELS_URL, params=params, timeout=30, allow_redirects=False)
            if response.status_code == 401:
                raise ConnectionError("reconnect_required", "Google rejected this credential. Reconnect the intended channel.")
            if response.status_code == 403:
                raise ConnectionError("access_denied", "YouTube denied this request. Check API enablement, granted scope and quota in Google Cloud.")
            if response.status_code == 429:
                raise ConnectionError("rate_limited", "YouTube rate limit reached. Leave the connection unchanged and retry later.")
            if response.status_code != 200:
                raise ConnectionError("provider_unavailable", "YouTube channel verification failed. No connection was verified.")
            body = response.json()
            if not isinstance(body, dict) or not isinstance(body.get("items", []), list):
                raise ConnectionError("invalid_response", "YouTube returned an invalid channel response.")
            for item in body.get("items", []):
                channel_id = require_channel_id(item.get("id"))
                snippet = item.get("snippet", {})
                title, handle = snippet.get("title", ""), snippet.get("customUrl")
                if not isinstance(title, str) or (handle is not None and not isinstance(handle, str)):
                    raise ConnectionError("invalid_response", "YouTube returned invalid channel metadata.")
                channels[channel_id] = {"id": channel_id, "title": title, "handle": handle,
                                        "url": "https://www.youtube.com/channel/" + channel_id}
            token = body.get("nextPageToken")
            if not token:
                break
            pages += 1
            if not isinstance(token, str) or token in seen_pages or pages >= 20:
                raise ConnectionError("invalid_response", "Channel pagination did not finish safely.")
            seen_pages.add(token)
    finally:
        session.close()
    if not channels:
        raise ConnectionError("no_channel", "No owned channel was returned. Select the intended YouTube channel during consent; an email alone is not a channel.")
    return list(channels.values())


def select_channel(channels, expected_id=None, expected_handle=None):
    if bool(expected_id) == bool(expected_handle):
        raise ConnectionError("expected_identity_required", "Supply exactly one expected channel ID or handle.")
    if expected_id:
        require_channel_id(expected_id)
        matches = [c for c in channels if c["id"] == expected_id]
    else:
        expected = normalized_handle(expected_handle)
        matches = [c for c in channels if c["handle"] and normalized_handle(c["handle"]) == expected]
    if len(matches) != 1:
        raise ConnectionError("channel_mismatch", "The authorized channel does not match the intended channel. No credentials were saved or rebound.")
    return matches[0]


def validate_scope(credentials):
    granted = getattr(credentials, "granted_scopes", None)
    if (granted is not None and READ_SCOPE not in granted) or not credentials.has_scopes([READ_SCOPE]):
        raise ConnectionError("scope_missing", "Read-only YouTube consent was not granted. Reconnect with the required scope.")


def client_config(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    config = data.get("installed", {})
    if (config.get("auth_uri") not in {"https://accounts.google.com/o/oauth2/auth", "https://accounts.google.com/o/oauth2/v2/auth"}
            or config.get("token_uri") != TOKEN_URI
            or not isinstance(config.get("client_id"), str)
            or not config["client_id"].endswith(".apps.googleusercontent.com")
            or not config.get("client_secret")):
        raise ConnectionError("invalid_client", "Use a Google Desktop OAuth client JSON with official Google endpoints. Web clients are not supported by this loopback CLI.")
    return {"installed": config}


def connect(store, name, client_file, expected_id=None, expected_handle=None, port=8765, replace=False):
    # Validate identity and config before opening an authorization listener.
    if bool(expected_id) == bool(expected_handle):
        raise ConnectionError("expected_identity_required", "Supply exactly one expected channel ID or handle.")
    require_channel_id(expected_id) if expected_id else normalized_handle(expected_handle)
    if not 1024 <= port <= 65535:
        raise ConnectionError("invalid_port", "Choose a loopback port between 1024 and 65535.")
    config = client_config(client_file)
    Flow, _, _, Session = sdk()
    with store.lock(name):
        previous = store.load(name) if store.path(name).exists() else None
        if previous and not replace:
            raise ConnectionError("already_connected", "This alias already has credentials. Check it, or explicitly use --replace to reconnect the same channel.")
        flow = Flow.from_client_config(config, scopes=[READ_SCOPE], autogenerate_code_verifier=True)
        credentials = flow.run_local_server(host="127.0.0.1", port=port, open_browser=False,
            timeout_seconds=300, access_type="offline", prompt="consent select_account",
            authorization_prompt_message="Open this Google consent link in your browser (do not paste codes into chat):\n{url}",
            success_message="Consent received. Return to the terminal for channel verification.")
        validate_scope(credentials)
        channel = select_channel(owned_channels(credentials, Session), expected_id, expected_handle)
        if previous and previous["channel"]["id"] != channel["id"]:
            raise ConnectionError("channel_mismatch", "An existing connection cannot be replaced with a different channel. Use a new alias.")
        if not credentials.refresh_token:
            raise ConnectionError("offline_access_missing", "No refresh token was returned. No credentials saved; check Google consent and retry explicitly.")
        record = {"schema_version": 1, "connection": name, "channel": channel, "verified_at": now(),
                  "credentials": json.loads(credentials.to_json())}
        store.save(name, record)
        return summary(record, live=True)


def check(store, name):
    _, Credentials, Request, Session = sdk()
    with store.lock(name):
        record = store.load(name)
        credentials = Credentials.from_authorized_user_info(record["credentials"])
        validate_scope(credentials)
        if not credentials.valid:
            if not credentials.refresh_token:
                raise ConnectionError("reconnect_required", "Offline authorization is missing. Reconnect this channel.")
            try:
                credentials.refresh(Request())
            except Exception:
                raise ConnectionError("refresh_failed", "Token refresh failed. Check network and Google authorization; reconnect if consent was revoked.") from None
        channel = select_channel(owned_channels(credentials, Session), expected_id=record["channel"]["id"])
        record.update(channel=channel, verified_at=now(), credentials=json.loads(credentials.to_json()))
        store.save(name, record)
        return summary(record, live=True)


def bind_registry(store, name, registry_path, slot_id, expected_id):
    require_channel_id(expected_id)
    result = check(store, name)
    if result["channel_id"] != expected_id:
        raise ConnectionError("channel_mismatch", "Live channel does not match --expected-channel-id. Registry unchanged.")
    path = Path(registry_path)
    with file_lock(path.parent / ".youtube-registry.lock"):
        registry = json.loads(path.read_text(encoding="utf-8"))
        slots = [r for r in registry["channels"] if r.get("slot_id") == slot_id]
        if len(slots) != 1:
            raise ConnectionError("invalid_slot", "The registry must contain exactly one matching planned slot.")
        slot = slots[0]
        if slot.get("channel_id") not in (None, expected_id):
            raise ConnectionError("channel_mismatch", "This slot is already bound to a different channel. Registry unchanged.")
        if any(r is not slot and r.get("channel_id") == expected_id for r in registry["channels"]):
            raise ConnectionError("duplicate_channel", "This channel is already bound to another slot. Registry unchanged.")
        slot.update(channel_id=result["channel_id"], display_name=result["title"], handle=result["handle"],
                    url=result["url"], last_verified_at=result["last_verified_at"], setup_status="verified_readonly")
        slot.pop("setup_blocker", None)
        # Only non-secret verified metadata belongs in Git; do not copy private binding paths or tokens.
        atomic_json(path, registry, mode=0o644)
    return {**result, "slot_id": slot_id, "registry_updated": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only YouTube connections; no channel creation, upload or publishing.")
    parser.add_argument("--credentials-dir", default=os.environ.get("YOUTUBE_CREDENTIALS_DIR", "private/youtube"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show stored metadata only; does not prove live access")
    p = sub.add_parser("connect", help="Authorize one intended channel through Google's loopback consent flow")
    p.add_argument("--connection", required=True)
    p.add_argument("--client-secrets", required=True)
    identity = p.add_mutually_exclusive_group(required=True)
    identity.add_argument("--expected-channel-id")
    identity.add_argument("--expected-handle")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--replace", action="store_true")
    p = sub.add_parser("check", help="Refresh if needed and verify the saved channel ID against YouTube")
    p.add_argument("--connection", required=True)
    p = sub.add_parser("bind", help="Live-check then save non-secret verified metadata into a planned registry slot")
    p.add_argument("--connection", required=True)
    p.add_argument("--expected-channel-id", required=True)
    p.add_argument("--slot", required=True)
    p.add_argument("--registry", default="channels/youtube-registry.json")
    args = parser.parse_args(argv)
    store = ConnectionStore(args.credentials_dir)
    try:
        if args.command == "status":
            result = {"connections": store.cached(), "live_checked": False, "publishing_enabled": False}
        elif args.command == "connect":
            result = connect(store, args.connection, args.client_secrets, args.expected_channel_id,
                             args.expected_handle, args.port, args.replace)
        elif args.command == "check":
            result = check(store, args.connection)
        else:
            result = bind_registry(store, args.connection, args.registry, args.slot, args.expected_channel_id)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except ConnectionError as exc:
        print(json.dumps({"status": "blocked", "code": exc.code, "message": str(exc), "publishing_enabled": False}))
    except Exception:
        # SDK/provider exceptions can contain request details or tokens. Do not echo them.
        print(json.dumps({"status": "blocked", "code": "connection_failed",
                          "message": "Operation failed; no successful connection check was reported. Check private configuration and network access.",
                          "publishing_enabled": False}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
