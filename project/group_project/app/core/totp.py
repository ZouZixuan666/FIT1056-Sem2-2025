# app/core/totp.py
"""
Lightweight TOTP helper (RFC 6238-ish) with a 20s period by default.

- totp(secret: str, period: int = 20) -> tuple[str, int]
    Returns (6-digit code, seconds_left_in_current_period)

- start_console_printer(secret_env_var="SITEADMIN_SECRET", period=20)
    Starts a background daemon thread that keeps a single, live-updating
    AUTH CODE line in your console. (No growing spam.)
"""

from __future__ import annotations
import hmac
import hashlib
import struct
import time
import os
import threading
import sys


def _hotp(secret_bytes: bytes, counter: int, digits: int = 6) -> str:
    msg = struct.pack(">Q", counter)
    h = hmac.new(secret_bytes, msg, hashlib.sha1).digest()
    off = h[-1] & 0x0F
    code = (struct.unpack(">I", h[off:off+4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return f"{code:0{digits}d}"


def totp(secret: str, period: int = 20, digits: int = 6) -> tuple[str, int]:
    """Return (code, seconds_left)."""
    if period <= 0:
        period = 20
    now = int(time.time())
    ctr = now // period
    secs_left = period - (now - ctr * period)
    code = _hotp(secret.encode("utf-8"), ctr, digits=digits)
    return code, secs_left


# ---- Single-line console printer ----

_started_flag = False
_started_lock = threading.Lock()

def _write_one_line(line: str) -> None:
    """
    Overwrite a single line in the console.
    Uses carriage return + clear-to-EOL. Works well in VS Code & most terminals.
    """
    sys.stdout.write("\r\033[K")       # move to start + clear current line
    sys.stdout.write(line)
    sys.stdout.flush()


def start_console_printer(secret_env_var: str = "SITEADMIN_SECRET", period: int = 20) -> None:
    """
    Spawn one daemon thread that updates a single AUTH CODE line every second.
    Idempotent: calling multiple times will only start it once.
    """
    global _started_flag
    with _started_lock:
        if _started_flag:
            return
        _started_flag = True

    secret = os.getenv(secret_env_var, "SITEADMIN_DEMO_SECRET")

    def _runner():
        last_code = None
        # Print a one-time header above the line we keep updating
        sys.stdout.write("SiteAdmin One-Time Password (TOTP):\n")
        sys.stdout.flush()
        while True:
            code, left = totp(secret, period=period)
            # Always rewrite the same line
            _write_one_line(f"AUTH CODE: {code} ({left:02d} seconds) ")
            last_code = code   # not used, but kept in case you want edge logic later
            time.sleep(1)

    t = threading.Thread(target=_runner, name="TOTPConsolePrinter", daemon=True)
    t.start()
