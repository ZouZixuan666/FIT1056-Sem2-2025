# app/core/audit.py
import json
from datetime import datetime
from app.core.config import AUDIT_LOG, APP_VERSION

def audit(event: str, who: str | None = None, role: str | None = None, details: dict | None = None):
    rec = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "user": who,
        "role": role,
        "details": details or {},
        "app_version": APP_VERSION,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
