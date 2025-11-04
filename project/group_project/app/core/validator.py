import os
import re
import json
import tempfile
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet

# Optional: only needed when using encryption helpers
try:
    from app.core import security_utils
except Exception:
    security_utils = None


class Validator:
    """
    Unified validator:
    - Strict ID formats: A###, S###, P### (code2)
    - Legacy 'staff or admin startswith S/A' (code1) via validate_staff_or_admin_id()
    - Flexible log entry validation: strict=True (code2 behavior) or strict=False (code1 behavior)
    """
    _PATTERNS = {
        "A": re.compile(r"^A\d{3}$"),  # Admin  e.g., A001
        "S": re.compile(r"^S\d{3}$"),  # Staff  e.g., S001
        "P": re.compile(r"^P\d{3}$"),  # Patient e.g., P001
    }

    @staticmethod
    def require_field(name: str, value):
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise ValueError(f"{name} is required")

    # ---- Strict ID validators (code2) ----
    @staticmethod
    def validate_admin_id(aid: str) -> bool:
        Validator.require_field("adminID", aid)
        aid = aid.upper().strip()
        if not Validator._PATTERNS["A"].fullmatch(aid):
            raise ValueError("adminID must match A### (e.g., A001)")
        return True

    @staticmethod
    def validate_staff_id(sid: str) -> bool:
        """
        Staff IDs must be exactly S### (e.g., S001).
        Use validate_admin_id() for admin IDs.
        """
        Validator.require_field("staffID", sid)
        sid = sid.upper().strip()
        if not Validator._PATTERNS["S"].fullmatch(sid):
            raise ValueError("staffID must match S### (e.g., S001)")
        return True

    @staticmethod
    def validate_patient_id(pid: str) -> bool:
        Validator.require_field("patientID", pid)
        pid = pid.upper().strip()
        if not Validator._PATTERNS["P"].fullmatch(pid):
            raise ValueError("patientID must match P### (e.g., P001)")
        return True

    # ---- Legacy lenient validator (code1 semantics) ----
    @staticmethod
    def validate_staff_or_admin_id(sid: str) -> bool:
        """
        Legacy: only check that it starts with 'S' or 'A' (code1 behavior).
        Keep this for backward-compat callers.
        """
        Validator.require_field("staffID", sid)
        s = sid.strip().upper()
        if not (s.startswith("S") or s.startswith("A")):
            raise ValueError("staffID should start with 'S' or 'A'")
        return True

    # ---- Other field validators ----
    @staticmethod
    def validate_temperature(temp: Optional[float]):
        if temp is None:
            return True
        if not (30.0 <= temp <= 45.0):
            raise ValueError("temperature out of realistic human range (30–45°C)")
        return True

    @staticmethod
    def validate_log_entry_dict(d: Dict[str, Any], *, strict: bool = True):
        """
        strict=True  -> code2 behavior: enforce A###/S###/P### where applicable
        strict=False -> code1 behavior: required fields + temperature range only
        """
        Validator.require_field("logID", d.get("logID"))
        Validator.require_field("patientID", d.get("patientID"))
        Validator.require_field("staffID", d.get("staffID"))

        if strict:
            Validator.validate_patient_id(d["patientID"])
            # 'staffID' here must be S###; use validate_admin_id where relevant in your flows
            sid = str(d["staffID"]).strip().upper()
            if sid.startswith("A"):
                Validator.validate_admin_id(sid)
            else:
                Validator.validate_staff_id(sid)
        # else: legacy mode skips strict ID format checks

        if d.get("temperature") is not None:
            Validator.validate_temperature(d["temperature"])


# -------- Module-level JSON helpers (encrypted + plaintext, with auto-fallbacks) --------

def atomic_write_json(path: str, data, encrypt: bool = True):
    """
    Atomically write JSON data to disk.
    If encryption support is unavailable, transparently write plaintext.
    """
    import json, os, tempfile

    dir_path = os.path.dirname(path) or "."
    os.makedirs(dir_path, exist_ok=True)

    # Create a temporary file safely in the same directory
    tmp_fd, tmp_path = tempfile.mkstemp(dir=dir_path)
    try:
        # We'll only open the fd ONCE
        with os.fdopen(tmp_fd, "wb") as f:
            if encrypt and security_utils is not None:
                try:
                    f.write(security_utils.encrypt_json(data))
                except Exception:
                    # If encryption fails, reopen in text mode
                    f.close()  # ensure closure before text reopen
                    with open(tmp_path, "w", encoding="utf-8") as fw:
                        json.dump(data, fw, ensure_ascii=False, indent=2)
            else:
                f.close()
                with open(tmp_path, "w", encoding="utf-8") as fw:
                    json.dump(data, fw, ensure_ascii=False, indent=2)

        # Atomically replace
        os.replace(tmp_path, path)

    except Exception:
        # Clean up any leftover temporary file
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise


def read_json_file(path: str, encrypted: bool = True):
    """
    Read JSON file. If encryption support isn't available, try plaintext.
    If decrypt fails, fall back to plaintext automatically.
    Returns [] if missing/empty.
    """
    import json, os
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        raw = f.read()
    if not raw.strip():
        return []
    # Try decrypt first only when supported
    if encrypted and security_utils is not None:
        try:
            return security_utils.decrypt_json(raw)
        except Exception:
            # Fall back to plaintext
            try:
                return json.loads(raw.decode("utf-8"))
            except Exception:
                # As a last resort, return empty for malformed files
                return []
    # No encryption available: read plaintext
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return []


def atomic_write_jsonl(path: str, data: List[Dict[str, Any]], encrypt: bool = True):
    """
    Atomically write JSONL (one JSON object per line).
    - encrypt=True: Fernet-encrypt each line (compatible with read_jsonl_file)
    - encrypt=False: write plaintext JSONL
    """
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        if encrypt:
            if security_utils is None:
                raise RuntimeError("security_utils not available for encryption key")
            key = security_utils.load_key()
            fern = Fernet(key)
            with os.fdopen(tmp_fd, "wb") as f:
                for obj in data:
                    line = json.dumps(obj, ensure_ascii=False)
                    f.write(fern.encrypt(line.encode()) + b"\n")
        else:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                for obj in data:
                    json_line = json.dumps(obj, ensure_ascii=False)
                    f.write(json_line + "\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise


def read_jsonl_file(path: str, encrypted: bool = True):
    """
    Read JSONL file (one JSON object per line).
    - If encrypted=True: decrypt each line, fallback to plaintext per-line
    - If encrypted=False: plaintext JSONL
    Returns list[dict].
    """
    if not os.path.exists(path):
        return []

    with open(path, "rb") as f:
        lines = f.readlines()

    if not lines:
        return []

    results = []
    fern = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if encrypted:
            if security_utils is None:
                raise RuntimeError("security_utils not available for decryption key")
            if fern is None:
                key = security_utils.load_key()
                fern = Fernet(key)
            try:
                decrypted = fern.decrypt(line).decode("utf-8")
                results.append(json.loads(decrypted))
            except Exception:
                # Fallback: treat as plaintext
                try:
                    results.append(json.loads(line.decode("utf-8")))
                except Exception:
                    raise ValueError(f"Invalid line in {path}: not valid encrypted or plain JSONL.")
        else:
            results.append(json.loads(line.decode("utf-8")))

    return results


def atomic_write_encrypted_jsonl(path: str, data, encrypt: bool = True):
    """
    JSONL writer with graceful plaintext fallback.
    """
    import json, os, tempfile
    from cryptography.fernet import Fernet

    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path) or ".")
    try:
        if encrypt and security_utils is not None:
            try:
                key = security_utils.load_key()
                fernet = Fernet(key)
                with os.fdopen(tmp_fd, "wb") as f:
                    for obj in data:
                        line = json.dumps(obj, ensure_ascii=False)
                        f.write(fernet.encrypt(line.encode("utf-8")) + b"\n")
            except Exception:
                # Fallback to plaintext on any encryption failure
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    for obj in data:
                        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        else:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                for obj in data:
                    f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise


def read_encrypted_jsonl(path: str, encrypted: bool = True):
    """
    Alternate JSONL reader (kept for compatibility with code1 callers).
    Behaves like read_jsonl_file with per-line decrypt + plaintext fallback.
    """
    if not os.path.exists(path):
        return []

    with open(path, "rb") as f:
        lines = f.readlines()

    if not lines:
        return []

    results = []
    fernet = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if encrypted:
            if security_utils is None:
                raise RuntimeError("security_utils not available for decryption key")
            if fernet is None:
                key = security_utils.load_key()
                fernet = Fernet(key)
            try:
                decrypted = fernet.decrypt(line).decode("utf-8")
                results.append(json.loads(decrypted))
            except Exception:
                try:
                    results.append(json.loads(line.decode("utf-8")))
                except Exception:
                    raise ValueError(f"Invalid line in {path}: not valid encrypted or plain JSONL.")
        else:
            results.append(json.loads(line.decode("utf-8")))

    return results
