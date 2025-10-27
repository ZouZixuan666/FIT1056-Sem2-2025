# decrypter.py
from __future__ import annotations

import base64
import json
import os
import sys
from typing import Optional, Tuple

# Optional: your helper (if present, we'll use it too)
try:
    from app.core import security_utils  # type: ignore
except Exception:  # pragma: no cover
    security_utils = None  # type: ignore

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception as e:
    print("❌ cryptography not installed. Install with: pip install cryptography")
    sys.exit(1)

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(REPO_ROOT, "data")
OUT_DIR = os.path.join(REPO_ROOT, "decrypt")

# ---------------- helpers ----------------
def list_data_files() -> list[str]:
    if not os.path.isdir(DATA_DIR):
        return []
    names = [n for n in os.listdir(DATA_DIR) if n.lower().endswith((".json", ".jsonl"))]
    names.sort()
    return names

def load_key_from_file(path: str) -> bytes:
    with open(path, "rb") as f:
        raw = f.read().strip()
    # Accept both raw text and base64-encoded text
    try:
        # If it's already urlsafe base64 Fernet key, this won't error; if it's plain, will error, then we wrap.
        base64.urlsafe_b64decode(raw)
        return raw
    except Exception:
        # Treat as plaintext -> encode -> base64-url-safe (Fernet spec wants 32-byte key already b64)
        # If your file already contains a proper Fernet key like b'rYY-...=', we just return raw.
        # If your file contains the exact b64 string (most common), just return raw bytes.
        return raw

def load_key_interactive() -> Optional[bytes]:
    """
    Ask user for a key path or paste a key. Empty = None.
    """
    print("\n(Optional) Provide key for decryption:")
    print(" - Press Enter to skip and use security_utils.load_key() if available")
    print(" - Enter a path to key file (e.g. data/_app_secret.key)")
    print(" - Or paste a Fernet key (urlsafe base64, ends with '=')")
    s = input("Key path or key (blank to skip): ").strip()
    if not s:
        return None

    # If it's a path that exists, read it
    if os.path.exists(s):
        try:
            return load_key_from_file(s)
        except Exception as e:
            print(f"  ⚠️  Failed to read key file: {e}")
            return None

    # If looks like a Fernet key string
    try:
        # Normalize to bytes
        kb = s.encode("utf-8").strip()
        # quick validation
        base64.urlsafe_b64decode(kb)
        return kb
    except Exception:
        print("  ⚠️  That doesn't look like a valid Fernet key (urlsafe base64).")
        return None

def decrypt_json_text(text: str, key: Optional[bytes]) -> Tuple[Optional[object], str]:
    """
    Try plaintext JSON -> Fernet (given key) -> Fernet(security_utils) -> security_utils.decrypt_json.
    Returns (obj, error_summary)
    """
    errors = []

    # 1) Plain JSON
    try:
        obj = json.loads(text)
        return obj, ""
    except Exception as e:
        errors.append(f"- Plain JSON parse failed: {type(e).__name__}: {e}")

    # 2) Fernet with provided key
    if key:
        try:
            f = Fernet(key)
            dec = f.decrypt(text.encode("utf-8"))
            return json.loads(dec.decode("utf-8")), ""
        except InvalidToken as e:
            errors.append(f"- Fernet (provided key) failed: InvalidToken")
        except Exception as e:
            errors.append(f"- Fernet (provided key) failed: {type(e).__name__}: {e}")

    # 3) Fernet with security_utils.load_key()
    if security_utils and hasattr(security_utils, "load_key"):
        try:
            k2 = security_utils.load_key()
            f2 = Fernet(k2)
            dec2 = f2.decrypt(text.encode("utf-8"))
            return json.loads(dec2.decode("utf-8")), ""
        except InvalidToken:
            errors.append("- Fernet (security_utils key) failed: InvalidToken")
        except Exception as e:
            errors.append(f"- Fernet (security_utils key) failed: {type(e).__name__}: {e}")

    # 4) security_utils.decrypt_json (it may do its own logic)
    if security_utils and hasattr(security_utils, "decrypt_json"):
        try:
            obj = security_utils.decrypt_json(text)
            return obj, ""
        except Exception as e:
            errors.append(f"- security_utils.decrypt_json failed: {type(e).__name__}: {e}")

    return None, "\n  ".join(errors)

def decrypt_jsonl_lines(lines: list[bytes], key: Optional[bytes]) -> Tuple[list[object], str]:
    """
    Decrypt JSONL file (one JSON object per line). Supports:
      - plaintext JSON lines
      - Fernet(token per line) with provided key
      - Fernet(security_utils key)
      - raw JSON lines
    """
    out: list[object] = []
    errors = []
    f_provided = Fernet(key) if key else None
    f_su = None
    if security_utils and hasattr(security_utils, "load_key"):
        try:
            k2 = security_utils.load_key()
            f_su = Fernet(k2)
        except Exception:
            f_su = None

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        # Try plaintext JSON
        try:
            out.append(json.loads(line.decode("utf-8")))
            continue
        except Exception:
            pass

        # Try Fernet (provided key)
        if f_provided:
            try:
                dec = f_provided.decrypt(line)
                out.append(json.loads(dec.decode("utf-8")))
                continue
            except Exception:
                pass

        # Try Fernet (security_utils key)
        if f_su:
            try:
                dec2 = f_su.decrypt(line)
                out.append(json.loads(dec2.decode("utf-8")))
                continue
            except Exception:
                pass

        # Last-ditch: treat as utf-8 json again
        try:
            out.append(json.loads(line.decode("utf-8")))
            continue
        except Exception as e:
            errors.append(f"  line {idx}: {type(e).__name__}: {e}")

    return out, "\n".join(errors)

def write_output(filename: str, obj) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    out_name = f"decrypted_{filename}"
    out_path = os.path.join(OUT_DIR, out_name)
    # If this is a list (from jsonl), write pretty JSON array
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return out_path

# ---------------- main ----------------
def main():
    print(f"🗝️  Data directory: {DATA_DIR}")
    print(f"📂 Output directory: {OUT_DIR}")

    files = list_data_files()
    if not files:
        print("❌ No .json/.jsonl files found in data/")
        return

    # menu
    print("\nWhich file do you want to decrypt?")
    print("Type a number, a name (e.g. 'alerts'), or 'all' to decrypt everything.\n")
    for i, n in enumerate(files, start=1):
        print(f"  [{i}] {n}")
    choice = input("\nEnter choice: ").strip().lower()

    # Optional key
    key = load_key_interactive()

    targets: list[str] = []
    if choice == "all":
        targets = files
    elif choice.isdigit() and 1 <= int(choice) <= len(files):
        targets = [files[int(choice) - 1]]
    else:
        # try logical name
        logical = choice if choice.endswith(".json") or choice.endswith(".jsonl") else f"{choice}.json"
        if logical in files:
            targets = [logical]
        else:
            # try exact match
            if choice in files:
                targets = [choice]
            else:
                print("❌ Not found.")
                return

    print("\n🔧 Processing…\n")

    ok_count = 0
    for fname in targets:
        fpath = os.path.join(DATA_DIR, fname)
        try:
            if fname.lower().endswith(".jsonl"):
                with open(fpath, "rb") as f:
                    lines = f.readlines()
                arr, err = decrypt_jsonl_lines(lines, key)
                if err:
                    print(f"  ⚠️  {fname}: partially decrypted with warnings:\n{err}")
                out = write_output(fname, arr)
                print(f"  ✅ {fname} → {out}")
                ok_count += 1
            else:
                with open(fpath, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                obj, err = decrypt_json_text(text, key)
                if obj is None:
                    print(f"  ❌ {fname}: All decrypt/parse attempts failed:\n  {err}")
                else:
                    out = write_output(fname, obj)
                    print(f"  ✅ {fname} → {out}")
                    ok_count += 1
        except Exception as e:
            print(f"  ❌ {fname}: {type(e).__name__}: {e}")

    print(f"\nDone. {ok_count}/{len(targets)} file(s) decrypted.")

if __name__ == "__main__":
    main()
