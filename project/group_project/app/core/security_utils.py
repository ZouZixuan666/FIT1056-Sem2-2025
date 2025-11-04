# app/core/security_utils.py
from __future__ import annotations
import json
import os
from cryptography.fernet import Fernet

KEY_FILE = os.path.join("data", "_app_secret.key")

def load_key() -> bytes:
    with open(KEY_FILE, "rb") as f:
        return f.read().strip()

def ensure_key_exists() -> bytes:
    os.makedirs(os.path.dirname(KEY_FILE) or ".", exist_ok=True)
    if not os.path.exists(KEY_FILE) or not open(KEY_FILE, "rb").read().strip():
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        return key
    return load_key()

def encrypt_json(obj) -> bytes:
    """
    Serialize obj to JSON and return **bytes** (Fernet token).
    """
    key = load_key()
    f = Fernet(key)
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return f.encrypt(payload)  # <-- bytes

def decrypt_json(token) -> object:
    """
    Accept **bytes or str** (Fernet token) and return the parsed Python object.
    Falls back to plain JSON if not a valid token.
    """
    # accept bytes or str
    tok_bytes = token.encode("utf-8") if isinstance(token, str) else token
    key = load_key()
    f = Fernet(key)
    try:
        raw = f.decrypt(tok_bytes)          # bytes
        return json.loads(raw.decode("utf-8"))
    except Exception:
        # Not a valid token? try treat input as plaintext JSON text/bytes.
        try:
            if isinstance(token, bytes):
                return json.loads(token.decode("utf-8"))
            return json.loads(token)
        except Exception as e:
            raise ValueError(f"Unable to decrypt or parse JSON: {e}")
