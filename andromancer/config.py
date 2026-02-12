import os
from pathlib import Path

def load_env(filepath=".env"):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

# Load .env at the start
load_env()

def _env(key: str, default=None):
    v = os.getenv(key)
    return v if v is not None else default

def _bool_env(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")

# Paths
BASE_DIR = Path(__file__).parent.parent.resolve()
STATE_DIR = Path(os.path.expanduser(_env("ANDROMANCER_STATE_DIR", "~/.andromancer"))).resolve()
STATE_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = STATE_DIR / "agent_state.json"
VECTOR_DB_PATH = STATE_DIR / "memory.vec"
LOG_FILE = STATE_DIR / "agent.log"

# AI / LLM
GROQ_API_KEY = _env("GROQ_API_KEY", "")
MODEL_NAME = _env("MODEL_NAME", "meta-llama/llama-4-scout-17b-16e-instruct")
MAX_STEPS = int(_env("MAX_STEPS", 20))

# ADB
ADB_TIMEOUT = int(_env("ADB_TIMEOUT", 15))
ADB_DELAY = float(_env("ADB_DELAY", 1.0))

# Autonomy
AUTONOMY_LEVEL = _env("AUTONOMY_LEVEL", "full")
CONFIDENCE_THRESHOLD = float(_env("CONFIDENCE_THRESHOLD", 0.75))
PARALLEL_ACTIONS = _bool_env("PARALLEL_ACTIONS", True)
SAFETY_CHECKPOINTS = _bool_env("SAFETY_CHECKPOINTS", True)

# Logging
LOG_LEVEL = _env("LOG_LEVEL", "INFO")
SILENT_MODE = _bool_env("SILENT_MODE", False)
