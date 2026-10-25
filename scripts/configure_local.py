"""Generate local-only secrets. Never overwrite an existing environment file."""
import secrets
from pathlib import Path

path=Path('.env')
with path.open('x') as f:
    f.write('WORKER_TOKEN='+secrets.token_hex(32)+'\n')
    f.write('N8N_ENCRYPTION_KEY='+secrets.token_hex(32)+'\n')
    f.write('GENERIC_TIMEZONE=Asia/Ulaanbaatar\n')
path.chmod(0o600)
print('Created .env; store it securely, separately from source control.')
