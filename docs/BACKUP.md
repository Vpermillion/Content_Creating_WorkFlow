# Backups, restore and assistant replacement

This CLI backs up the legacy application store. Site OAuth data and the hosted publisher's private volume have separate storage contracts; see [CONTINUITY.md](CONTINUITY.md). Do not assume an application backup includes them.

Pause workers before a private backup. The command refuses an active lease and uses SQLite's online backup API plus checksummed media files, instead of copying a live WAL database. It excludes neither your job content nor your media: treat the archive as private. It excludes external `.env` files and the n8n volume because those live outside application state.

```sh
python -m whatif backup /safe/path/whatif-state.tgz
python -m whatif restore /safe/path/whatif-state.tgz /new/path/state
python -m whatif --data /new/path/state status
python -m whatif --data /new/path/state run pilot-001
```

Restore requires a fresh destination, rejects archive traversal/symlinks, checks sizes and hashes, checks SQLite integrity, and clears old leases. Keep source code, private application state and credentials as separate backup concerns. Copy the archive to user-owned durable storage; a file on a cloud task machine alone is not a disaster-recovery plan. Drive is not connected here. There is no background off-machine backup service.

For the three **demonstration-only** fixtures, a safe export command packages JSON job state and the exact checkpoint files without any SQLite DB, credentials or live receipts:

```sh
python scripts/demo_snapshot.py export artifacts/demo-state.tar.gz
python scripts/demo_snapshot.py restore artifacts/demo-state.tar.gz --destination /new/path/demo-data
python -m whatif --data /new/path/demo-data run pilot-001
```

This allows the bundled demonstration to resume on another host without regenerating speech. Do not extend the public demo archive to real/private jobs. Their database and media must use your private backup storage. Git stores software, safe sample media and documentation only.

For n8n: stop that service, securely back up the complete `n8n_data` volume and the exact `N8N_ENCRYPTION_KEY` from `.env`, then restart. Workflow exports alone omit credentials, instance state and keys. Restore a compatible pinned n8n version and the volume/key together; verify worker connectivity before activating anything. Never commit either the volume backup or encryption key.

Replacement-assistant procedure:

1. Authorize access to the same user-owned repository and private state storage. Personal plugin connections may need a manual reconnect.
2. Read `START_HERE.md`, `docs/CURRENT.md` and `AGENTS.md` in the checkout.
3. Restore private application state, or restore the bundled safe demonstration into a fresh directory. Restore n8n separately if needed.
4. Rediscover tools and credentials by metadata/presence only. Validate the specific operations; do not assume this chat's connections transfer.
5. Start services using the README, inspect `status`, and resume the named job through the CLI/API.
6. Update the handoff and preserve the next checkpoint outside chat.

