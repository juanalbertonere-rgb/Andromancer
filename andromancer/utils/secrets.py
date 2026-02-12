import json
import os
from pathlib import Path
from typing import Optional, Dict

SECRETS_FILE = Path.home() / ".andromancer" / "secrets.json"

class SecretStore:
    def __init__(self, secrets_file: Path = SECRETS_FILE):
        self.secrets_file = secrets_file
        self._ensure_file()

    def _ensure_file(self):
        if not self.secrets_file.exists():
            self.secrets_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.secrets_file, "w") as f:
                json.dump({}, f)
            try:
                os.chmod(self.secrets_file, 0o600)
            except Exception:
                pass

    def get_secret(self, key: str) -> Optional[Dict[str, str]]:
        """Retrieves a secret dictionary (e.g., {'user': '...', 'pass': '...'}) by key."""
        try:
            with open(self.secrets_file, "r") as f:
                secrets = json.load(f)
            return secrets.get(key.lower())
        except Exception:
            return None

    def set_secret(self, key: str, value: Dict[str, str]):
        """Stores a secret."""
        try:
            with open(self.secrets_file, "r") as f:
                secrets = json.load(f)
            secrets[key.lower()] = value
            with open(self.secrets_file, "w") as f:
                json.dump(secrets, f, indent=4)
        except Exception:
            pass

secret_store = SecretStore()
