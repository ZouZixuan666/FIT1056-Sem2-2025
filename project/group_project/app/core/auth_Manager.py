# app/core/auth_Manager.py
from __future__ import annotations

import time
import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

from app.core.config import PBKDF2_ITER  # kept for compatibility (not used directly here)
from app.core.totp import totp
from app.core.otp_console import start_console_totp
from app.database.database_Manager import DatabaseManager

# Canonical username/ID for the SiteAdmin
SITEADMIN_USERNAME = "siteadmin"

# TOTP settings (20s window, per your spec)
_TOTP_PERIOD = 20
_TOTP_SECRET_ENV = "SITEADMIN_SECRET"  # falls back to demo if unset

# Lockout policy
LOCK_THRESHOLD = 5
LOCK_WINDOW_MIN = 5  # minutes


# --- DB accessor: always get a fresh, up-to-date instance ---
def _db() -> DatabaseManager:
    # Each call loads the latest files and avoids stale in-memory snapshots.
    return DatabaseManager()


# ----------------------
# Public helpers (delegate to DBM)
# ----------------------
def user_exists(username: str) -> bool:
    return _db().user_exists(username)

def list_users_by_role(role: str) -> List[Dict]:
    return _db().user_list_by_role(role)

def delete_user(username: str) -> Tuple[bool, str]:
    db = _db()
    if not db.user_exists(username):
        return False, "User not found."
    if username == SITEADMIN_USERNAME:
        return False, "Cannot delete SiteAdmin."
    ok = db.user_delete(username)
    return (True, "User deleted.") if ok else (False, "Delete failed.")

def create_user(username: str, password: str, role: str, name: str) -> None:
    """
    IMPORTANT: pass PLAINTEXT. DatabaseManager will hash internally.
    """
    _db().create_user(username, password, role, name)

def ensure_user(username: str, password: str, role: str, name: str) -> None:
    """
    IMPORTANT: pass PLAINTEXT. DatabaseManager will hash internally.
    """
    db = _db()
    if not db.user_exists(username):
        db.create_user(username, password, role, name)

# ⚠️ No seeding here.
# Siteadmin bootstrap happens ONLY inside DatabaseManager.__init__().


# ----------------------
# Patient Name → ID resolver (patients may log in by Name)
# ----------------------
def _find_patient_id_by_name_exact(name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Return (patient_id, err). Case-insensitive EXACT match on name.
    If multiple patients share the same name, refuse and ask for ID.
    """
    nm = (name or "").strip().casefold()
    if not nm:
        return None, None

    # users.json layout is a dict keyed by username; get_all_users() returns list of (uname, rec)
    matches = [
        uname
        for uname, rec in _db().get_all_users()
        if (rec.get("role") or "").lower() == "patient"
        and (rec.get("name") or "").strip().casefold() == nm
    ]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, "Multiple patients share this name. Please use your Patient ID."
    return None, None


# ----------------------
# Auth service
# ----------------------
@dataclass
class LockInfo:
    fails: int = 0
    until: Optional[float] = None  # epoch seconds


class AuthService:
    """
    - username/password verification (PBKDF2 via DatabaseManager)
    - SiteAdmin multi-step login (requires current OTP)
    - Patients can log in with **ID or Name**; staff/admin = **ID only**
    - Lockout state is **persisted** in DatabaseManager users.json
    - NOTE: Do NOT seed users here.
    """

    def __init__(self, state):
        # Ensure keys exist
        state.setdefault("auth", {"is_authed": False, "username": None, "name": None, "role": None})
        state.setdefault("awaiting_otp", False)
        state.setdefault("pending_user", None)
        self.state = state

    # ---- DB access ----
    def _get_user(self, username: str) -> Optional[Dict]:
        return _db().user_get(username)

    def _set_authed(self, username: str, rec: Dict) -> None:
        self.state["auth"].update(
            {"is_authed": True, "username": username, "name": rec.get("name"), "role": rec.get("role")}
        )

    def _check_password(self, username: str, password: str) -> bool:
        rec = self._get_user(username)
        # Compare DB-side PBKDF2 hash with freshly hashed plaintext using DB helper
        return bool(rec and rec.get("hash") == _db().hash_pwd(username, password))

    # ---- Lock helpers (persisted in DBM) ----
    def _get_lock(self, username: str) -> LockInfo:
        db = _db()
        if not db.user_exists(username):
            # Do NOT create lock state for unknown users
            return LockInfo(0, None)
        s = db.lock_get_state(username)
        return LockInfo(fails=int(s.get("fails") or 0), until=s.get("until"))

    def _set_lock(self, username: str, fails: int, until: Optional[float]):
        db = _db()
        if not db.user_exists(username):
            return
        db.lock_set_state(username, fails, until)

    def _clear_lock(self, username: str):
        db = _db()
        if db.user_exists(username):
            db.lock_clear(username)

    # ---- Public API ----
    def login_step1_password(self, username: str, password: str) -> Tuple[bool, str, bool]:
        """
        First step: verify username/password.
        Patients may enter their Name instead of ID; staff/admin must use ID.
        Returns (ok, message, require_otp)
        """
        raw = (username or "").strip()
        resolved_username = raw

        # 1) Try exact username first
        rec = self._get_user(raw)

        # 2) If not found, allow PATIENT name->ID resolution
        if not rec:
            patient_id, err = _find_patient_id_by_name_exact(raw)
            if err:
                return False, err, False
            if patient_id:
                resolved_username = patient_id
                rec = self._get_user(resolved_username)

        # ---------- Lockout gate (only for existing users) ----------
        if rec:
            lock = self._get_lock(resolved_username)
            if lock.until and lock.until > time.time():
                remaining = int(lock.until - time.time())
                return False, f"Account locked. Try again in {remaining}s.", False

        if not rec:
            # Non-existent users: do not change any lock state
            return False, "Invalid username or password.", False

        # Check password
        if not self._check_password(resolved_username, password):
            cur = self._get_lock(resolved_username)
            cur.fails += 1
            if cur.fails >= LOCK_THRESHOLD:
                until = time.time() + LOCK_WINDOW_MIN * 60
                self._set_lock(resolved_username, cur.fails, until)
                return False, f"Too many failed attempts. Account locked for {LOCK_WINDOW_MIN} minutes.", False
            else:
                self._set_lock(resolved_username, cur.fails, None)
                return False, f"Invalid username or password. Attempts: {cur.fails}/{LOCK_THRESHOLD}.", False

        # Password OK → clear lock
        self._clear_lock(resolved_username)

        # SiteAdmin requires OTP
        role = (rec.get("role") or "").lower()
        if role == "siteadmin":
            self.state["awaiting_otp"] = True
            self.state["pending_user"] = SITEADMIN_USERNAME
            secret = os.getenv(_TOTP_SECRET_ENV, "SITEADMIN_DEMO_SECRET")
            start_console_totp(secret, period=_TOTP_PERIOD, force_single_line=True)
            return True, "Password accepted. Enter the 6-digit auth code.", True

        # Normal users log in immediately
        self._set_authed(resolved_username, rec)
        self.state["awaiting_otp"] = False
        self.state["pending_user"] = None
        return True, "", False

    def login_step2_verify_otp(self, code: str) -> Tuple[bool, str]:
        """
        Second step for SiteAdmin: verify OTP and complete login.
        """
        if not self.state.get("awaiting_otp"):
            return False, "No OTP requested."

        pending = self.state.get("pending_user")
        if pending != SITEADMIN_USERNAME:
            return False, "Invalid OTP flow."

        secret = os.getenv(_TOTP_SECRET_ENV, "SITEADMIN_DEMO_SECRET")
        current, _ = totp(secret, period=_TOTP_PERIOD)
        if (code or "").strip() != current:
            return False, "Invalid auth code."

        rec = self._get_user(pending)
        if not rec:
            return False, "User disappeared."

        self._set_authed(pending, rec)
        self.state["awaiting_otp"] = False
        self.state["pending_user"] = None
        return True, ""

    # Convenience for normal users (used by UI)
    def login_password_only(self, username: str, password: str) -> Tuple[bool, str]:
        ok, msg, need = self.login_step1_password(username, password)
        if ok and not need:
            return True, ""
        return False, msg

    def logout(self):
        self.state["auth"].update({"is_authed": False, "username": None, "name": None, "role": None})
        self.state["awaiting_otp"] = False
        self.state["pending_user"] = None
