"""Small .env reader: no shell execution, dependencies or secret logging."""
import os
from pathlib import Path

ALLOWED = {'FATHOM_API_KEY', 'OLLAMA_URL', 'OLLAMA_MODEL', 'DATA_DIR'}

def load_env(path):
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key in ALLOWED:
            os.environ.setdefault(key, value)
