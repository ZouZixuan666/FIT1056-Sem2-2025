import json
import os
from cryptography.fernet import Fernet
from app.core import security_utils

path = "data/audit_log.jsonl"

def manual_decrypt_jsonl(path):
    """Decrypts a Fernet-encrypted JSONL file line by line."""
    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        return

    with open(path, "rb") as f:
        lines = f.readlines()

    key = security_utils.load_key()
    fernet = Fernet(key)
    decrypted_data = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            decrypted_text = fernet.decrypt(line).decode("utf-8")
            decrypted_data.append(json.loads(decrypted_text))
        except Exception:
            # fallback: not encrypted
            try:
                decrypted_data.append(json.loads(line.decode("utf-8")))
            except Exception:
                print("⚠️  Skipped invalid line:", line[:30])

    print(json.dumps(decrypted_data, indent=2, ensure_ascii=False))

manual_decrypt_jsonl(path)
