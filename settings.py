# settings.py - AndroMancer v11 compatible configuration
# Adaptado para Termux / Linux. Valores por defecto seguros y
# override mediante variables de entorno.

from pathlib import Path
import os

# -----------------------
# Helpers
# -----------------------
def _env(key: str, default=None):
    v = os.getenv(key)
    return v if v is not None else default

def _bool_env(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")

# -----------------------
# Rutas y almacenamiento
# -----------------------
# Base dir (expande ~)
STATE_DIR = Path(os.path.expanduser(_env("ANDROMANCER_STATE_DIR", "~/.andromancer"))).resolve()
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Archivos dentro del STATE_DIR
STATE_FILE = STATE_DIR / "agent_state.json"
VECTOR_DB_PATH = STATE_DIR / "memory.vec"
LOG_FILE = STATE_DIR / "agent.log"

# -----------------------
# IA / LLM (override with env)
# -----------------------
GROQ_API_KEY = _env("GROQ_API_KEY", "Enter_your_API_key_here")
MODEL_NAME = _env("MODEL_NAME", "llama-3.3-70b-versatile")
MAX_STEPS = int(_env("MAX_STEPS", 20))

# -----------------------
# ADB & Dispositivo
# -----------------------
# Nota: andromancer.py espera ADB_TIMEOUT
ADB_TIMEOUT = int(_env("ADB_TIMEOUT", 15))
ADB_DELAY = float(_env("ADB_DELAY", 1.0))
DRY_RUN = _bool_env("DRY_RUN", False)
FORCE_ADB = _bool_env("FORCE_ADB", False)

# -----------------------
# Autonomía / seguridad
# -----------------------
AUTONOMY_LEVEL = _env("AUTONOMY_LEVEL", "full")   # full, assisted, manual
CONFIDENCE_THRESHOLD = float(_env("CONFIDENCE_THRESHOLD", 0.75))
PARALLEL_ACTIONS = _bool_env("PARALLEL_ACTIONS", True)
SAFETY_CHECKPOINTS = _bool_env("SAFETY_CHECKPOINTS", True)

# Backward-compatible flags from v10 (no romper)
AUTOPILOT_ENABLED = _bool_env("AUTOPILOT_ENABLED", True)
AUTOPILOT_THRESHOLD = float(_env("AUTOPILOT_THRESHOLD", 0.8))
CONFIRM_RISKY_ACTIONS = _bool_env("CONFIRM_RISKY_ACTIONS", True)

# -----------------------
# Seguridad / apps permitidas
# -----------------------
SAFE_MODE = _bool_env("SAFE_MODE", False)
ALLOWED_APPS = set()  # si SAFE_MODE=True, rellenar manualmente en este archivo o por env (adaptar a tus necesidades)

# -----------------------
# Telegram (opcional)
# -----------------------
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN", None)
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID", None)
TELEGRAM_POLL_INTERVAL = int(_env("TELEGRAM_POLL_INTERVAL", 2))
TELEGRAM_MAX_RETRIES = int(_env("TELEGRAM_MAX_RETRIES", 5))
TELEGRAM_COMMAND_PREFIX = _env("TELEGRAM_COMMAND_PREFIX", "/cmd ")

# -----------------------
# Logging / UX / misc
# -----------------------
LOG_LEVEL = _env("LOG_LEVEL", "INFO")  # usado por andromancer.py
LOG_FILE = LOG_FILE  # Path a usar para logging.FileHandler en andromancer.py

COMMAND_QUEUE_MAX = int(_env("COMMAND_QUEUE_MAX", 100))
MAX_LLM_RETRIES = int(_env("MAX_LLM_RETRIES", 3))

TERMUX_NOTIFY = _bool_env("TERMUX_NOTIFY", True)
TTS_ENABLED = _bool_env("TTS_ENABLED", True)
VIBRATE_ON_ERROR = _bool_env("VIBRATE_ON_ERROR", True)

# -----------------------
# Valores legacy (compatibilidad con v10 si algún script los lee)
# -----------------------
# En v10 STATE_FILE era string con ~, aquí dejamos la variable
LEGACY_STATE_FILE = _env("LEGACY_STATE_FILE", str(STATE_FILE))

# -----------------------
# Fin de configuración
# -----------------------
# Mensaje opcional para confirmar carga (puedes comentar)
if _bool_env("ANDROMANCER_DEBUG_PRINT", False):
    print(f"Loaded settings: STATE_DIR={STATE_DIR}, STATE_FILE={STATE_FILE}, VECTOR_DB_PATH={VECTOR_DB_PATH}")
