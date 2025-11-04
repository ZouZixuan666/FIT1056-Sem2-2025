# app/core/config.py
from pathlib import Path
from zoneinfo import ZoneInfo

APP_NAME = "Hospital Control Panel"
APP_VERSION = "1.0"

LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW_MIN = 5
PBKDF2_ITER = 200_000  # PBKDF2-HMAC-SHA256 iteration count (work factor) for hashing passwords—higher = slower logins, harder to brute-force.

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
AUDIT_LOG = DATA_DIR / "audit_log.jsonl"
PATIENT_LOGS = DATA_DIR / "patient_logs.jsonl"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---- Timezone ----
LOCAL_TZ = ZoneInfo("Asia/Kuala_Lumpur")  
LOCAL_TZ_LABEL = "GMT+8"
