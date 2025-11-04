# app/core/otp_console.py
from __future__ import annotations

import sys
import threading
import time
from typing import Optional

try:
    # On Windows this enables ANSI sequences in many terminals
    import colorama  # type: ignore
    colorama.just_fix_windows_console()
except Exception:
    pass

from .totp import totp

_started = False  # singleton guard


def _supports_ansi() -> bool:
    """True when stdout is a TTY that supports ANSI cursor control."""
    return sys.stdout.isatty()


def start_console_totp(secret: str, period: int = 20, *, force_single_line: bool = True) -> None:
    """
    Start a background daemon that prints a live TOTP and updates it in place.

    - For your requirement we keep a strict single-line format:
        AUTH CODE: 857936 (20s)
      and overwrite it every second without growing the output.
    """
    global _started
    if _started:
        return
    _started = True

    def _printer():
        while True:
            code, left = totp(secret, period=period)
            # Strict single-line overwrite, exact format:
            # (pad to avoid remnants if terminal resizes)
            line = f"AUTH CODE: {code} ({left:02d}s)"
            sys.stdout.write("\r" + line.ljust(48))
            sys.stdout.flush()
            time.sleep(1)

    t = threading.Thread(target=_printer, name="otp_console_printer", daemon=True)
    t.start()
