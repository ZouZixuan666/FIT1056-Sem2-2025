# app/database/database_Manager.py
from __future__ import annotations

from typing import List, Optional, Dict, Any, Tuple
import os
import json
import hashlib
import time
import datetime  # <-- for assignment timestamps

# Config / utilities (import with fallbacks)
try:
    from app.core.config import PBKDF2_ITER  # type: ignore
except Exception:
    PBKDF2_ITER = 200_000  # safe default if config is missing

from app.core.validator import (
    Validator,
    read_json_file,
    atomic_write_json,
)

# Encrypted audit helpers (optional; we will fall back if unavailable)
try:
    from app.core.validator import read_encrypted_jsonl, atomic_write_encrypted_jsonl  # type: ignore
    _HAS_ENCRYPT = True
except Exception:
    _HAS_ENCRYPT = False

from app.users.patient import Patient
from app.users.staff import Staff
from app.core.alert import Alert
from app.logging.logentry import LogEntry
from app.users.preferences import Preferences
from app.core.audit import audit
from app.logging.system_log import SystemLog


class DatabaseManager:
    """
    Central persistent store for:
      - Clinical data: patients, staffs, logs, alerts, preferences, system_logs
      - Assignments, patient_logs (auxiliary), translate_cache
      - Users & auth (PBKDF2), per-account UI language, lockout state
      - Audit logs (encrypted JSONL if available; plaintext JSONL fallback)

    Users schema (stored in users.json as a dict keyed by username):
      {
        "P001": {
          "userID": "P001",
          "hash": "<pbkdf2 hex>",
          "role": "patient"|"staff"|"admin"|"siteadmin",
          "name": "Full Name",
          "default_ui_lang": "en",
          "lock_fails": 0,
          "lock_until_ts": null
        },
        ...
      }
    """

    # -------------------------
    # Init / Paths / Repos
    # -------------------------
    def __init__(self, data_dir: str = "data"):
        os.makedirs(data_dir, exist_ok=True)

        # File paths
        self.data_dir = data_dir
        self.patient_file = os.path.join(data_dir, "patients.json")
        self.staff_file = os.path.join(data_dir, "staffs.json")
        self.log_file = os.path.join(data_dir, "logs.json")
        self.alert_file = os.path.join(data_dir, "alerts.json")
        self.pref_file = os.path.join(data_dir, "preferences.json")
        self.system_log_file = os.path.join(data_dir, "system_logs.json")
        self.assignments_file = os.path.join(data_dir, "assignments.json")
        self.patient_log_file = os.path.join(data_dir, "patient_logs.json")
        self.translate_cache_file = os.path.join(data_dir, "translate_cache.json")
        self.users_file = os.path.join(data_dir, "users.json")

        # Audit (encrypted JSONL if available)
        self.audit_log_file = os.path.join(data_dir, "audit_log.jsonl")

        # In-memory repositories
        self.patients: Dict[str, Patient] = {}
        self.staffs: Dict[str, Staff] = {}
        self.logs: List[LogEntry] = []
        self.alerts: List[Alert] = []
        self.preferences: Dict[str, Preferences] = {}
        self.system_logs: List[SystemLog] = []
        # ✅ Store assignments as a LIST of rows, not a dict
        # Each row: {"patientID": "...", "staffID": "...", "assignedBy": "...", "ts": "..."}
        self.assignments: List[Dict[str, Any]] = []
        self.patient_logs: Dict[str, List[Dict[str, Any]]] = {}  # patientID -> list of dict logs (aux)
        self.translate_cache: Dict[str, str] = {}
        self.audit_logs: List[Dict[str, Any]] = []         # in-memory audit cache (for encrypted JSONL tool)

        # Users (new layout)
        self.users: Dict[str, Dict[str, Any]] = {}

        self.load_all()

        # Ensure bootstrap siteadmin
        self.ensure_user("siteadmin", "siteadmin123", "siteadmin", "Site Administrator")

    # -------------------------
    # Helpers (audit I/O safe)
    # -------------------------
    def _safe_read_encrypted_jsonl(self, path: str) -> List[Dict[str, Any]]:
        if _HAS_ENCRYPT:
            try:
                return read_encrypted_jsonl(path)  # type: ignore
            except Exception:
                # encryption helper present but failed → fall back to plaintext read
                pass
        # Fallback: plaintext JSONL
        rows: List[Dict[str, Any]] = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rows.append(json.loads(line))
                        except Exception:
                            # skip malformed
                            continue
            except Exception:
                pass
        return rows

    def _safe_write_encrypted_jsonl(self, path: str, rows: List[Dict[str, Any]]) -> None:
        if _HAS_ENCRYPT:
            try:
                atomic_write_encrypted_jsonl(path, rows)  # type: ignore
                return
            except Exception:
                # encryption helper present but failed → fall back to plaintext write
                pass
        # Fallback: plaintext JSONL
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(payload + ("\n" if payload else ""))
            os.replace(tmp, path)
        except Exception as e:
            print(f"Error writing plaintext JSONL audit log: {e}")

    # -------------------------
    # Load / Save
    # -------------------------
    def load_all(self) -> None:
        try:
            # patients
            pdata = read_json_file(self.patient_file)
            self.patients = {p["patientID"]: Patient.from_dict(p) for p in pdata}

            # staffs
            sdata = read_json_file(self.staff_file)
            self.staffs = {s["staffID"]: Staff.from_dict(s) for s in sdata}

            # logs
            ldata = read_json_file(self.log_file)
            self.logs = [LogEntry.from_dict(l) for l in ldata]

            # alerts
            adata = read_json_file(self.alert_file)
            self.alerts = [Alert.from_dict(a) for a in adata]

            # preferences
            pref_data = read_json_file(self.pref_file)
            self.preferences = {p["patientID"]: Preferences.from_dict(p) for p in pref_data}

            # system logs
            sysdata = read_json_file(self.system_log_file)
            self.system_logs = [SystemLog.from_dict(s) for s in sysdata]

            # ✅ assignments (keep list-of-rows, convert old dict if found)
            assign_data = read_json_file(self.assignments_file)
            if isinstance(assign_data, list):
                self.assignments = [a for a in assign_data if isinstance(a, dict)]
            elif isinstance(assign_data, dict):
                tmp: List[Dict[str, Any]] = []
                for sid, v in assign_data.items():
                    row = v if isinstance(v, dict) else {}
                    row.setdefault("staffID", sid)
                    tmp.append(row)
                self.assignments = tmp
            else:
                self.assignments = []

            # patient logs (aux)
            plog_data = read_json_file(self.patient_log_file)
            self.patient_logs = plog_data if isinstance(plog_data, dict) else {}

            # translate cache
            trans_data = read_json_file(self.translate_cache_file)
            self.translate_cache = trans_data if isinstance(trans_data, dict) else {}

            # users (dict)
            users_data = read_json_file(self.users_file)
            if isinstance(users_data, dict):
                self.users = users_data
            elif isinstance(users_data, list):
                # legacy list → convert
                self.users = {u.get("userID") or u.get("id"): u for u in users_data if (u.get("userID") or u.get("id"))}
            else:
                self.users = {}

            # Backfill per-account language + lock fields
            changed = False
            for u, rec in self.users.items():
                if "default_ui_lang" not in rec or not rec.get("default_ui_lang"):
                    rec["default_ui_lang"] = "en"
                    changed = True
                rec.setdefault("lock_fails", 0)
                rec.setdefault("lock_until_ts", None)
                rec.setdefault("userID", u)
            if changed:
                self._save_users_file()

            # audit logs (possibly encrypted)
            self.audit_logs = self._safe_read_encrypted_jsonl(self.audit_log_file)
        except Exception as e:
            print(f"Error loading data: {e}")

    def save_all(self) -> None:
        try:
            atomic_write_json(self.patient_file, [p.to_dict() for p in self.patients.values()])
            atomic_write_json(self.staff_file,   [s.to_dict() for s in self.staffs.values()])
            atomic_write_json(self.log_file,     [l.to_dict() for l in self.logs])
            atomic_write_json(self.alert_file,   [a.to_dict() for a in self.alerts])
            atomic_write_json(self.pref_file,    [p.to_dict() for p in self.preferences.values()])
            atomic_write_json(self.system_log_file, [s.to_dict() for s in self.system_logs])
            # ✅ persist list-of-rows directly
            atomic_write_json(self.assignments_file, self.assignments)
            atomic_write_json(self.patient_log_file, self.patient_logs)
            atomic_write_json(self.translate_cache_file, self.translate_cache)
            atomic_write_json(self.users_file, self._save_users_file())
            self._save_users_file()
            self._safe_write_encrypted_jsonl(self.audit_log_file, self.audit_logs)  # OK as is
        except Exception as e:
            print(f"Error saving data: {e}")
            raise

    # -------------------------
    # Users / Auth (PBKDF2)
    # -------------------------
    def hash_pwd(self, username: str, password: str) -> str:
        """PBKDF2-HMAC-SHA256 using username as salt; returns hex."""
        salt = (username or "").encode("utf-8")
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITER).hex()

    def _save_users_file(self) -> None:
        atomic_write_json(self.users_file, self.users, encrypt=False)

    # New API (preferred)
    def verify_user(self, username: str, password: str) -> bool:
        rec = self.users.get(username)
        if not rec or "hash" not in rec:
            return False
        return rec["hash"] == self.hash_pwd(username, password)

    def create_user(self, username: str, password: str, role: str, name: str) -> None:
        self.users[username] = {
            "userID": username,
            "hash": self.hash_pwd(username, password),
            "role": role,
            "name": name,
            "default_ui_lang": "en",
            "lock_fails": 0,
            "lock_until_ts": None,
        }
        self._save_users_file()

    def ensure_user(self, username: str, password: str, role: str, name: str) -> None:
        if username not in self.users:
            self.create_user(username, password, role, name)

    def delete_user(self, username: str) -> bool:
        if username.lower() == "siteadmin":
            return False
        if username in self.users:
            del self.users[username]
            self._save_users_file()
            return True
        return False

    def list_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        role = (role or "").lower()
        return [{"username": u, **rec} for u, rec in self.users.items() if (rec.get("role") or "").lower() == role]

    def get_user(self, userID: str) -> Optional[dict]:
        return self.users.get(userID)

    def get_all_users(self) -> List[dict]:
        return list(self.users.items())

    # Per-account language
    def user_get_default_lang(self, username: str) -> str:
        rec = self.users.get(username) or {}
        return rec.get("default_ui_lang") or "en"

    def user_set_default_lang(self, username: str, lang_code: str) -> bool:
        rec = self.users.get(username)
        if not rec:
            return False
        rec["default_ui_lang"] = (lang_code or "en")
        self._save_users_file()
        return True

    # Lockout state
    def lock_get_state(self, username: str) -> Dict[str, Any]:
        rec = self.users.get(username)
        if not rec:
            return {"fails": 0, "until": None}
        return {"fails": int(rec.get("lock_fails") or 0), "until": rec.get("lock_until_ts")}

    def lock_set_state(self, username: str, fails: int, until_ts: float | None) -> None:
        rec = self.users.get(username)
        if not rec:
            return
        rec["lock_fails"] = int(max(0, fails))
        rec["lock_until_ts"] = float(until_ts) if until_ts is not None else None
        self._save_users_file()

    def lock_clear(self, username: str) -> None:
        self.lock_set_state(username, 0, None)

    # -------------------------
    # Compatibility shims (legacy names expected by older modules)
    # -------------------------
    def user_exists(self, username: str) -> bool:
        return (username or "") in self.users

    def user_get(self, username: str):  # legacy alias
        return self.get_user(username)

    def user_list_by_role(self, role: str):  # legacy alias
        return self.list_users_by_role(role)

    def user_delete(self, username: str) -> bool:  # legacy alias
        return self.delete_user(username)

    def user_ensure(self, username: str, password_hash_or_plain: str, role: str, name: str) -> None:
        """
        Legacy alias. Older callers may pass a *hash* here, but our new flow expects
        plaintext. Since this is only used when the user is missing, re-hashing the
        provided value is OK (it becomes the initial password).
        """
        self.ensure_user(username, password_hash_or_plain, role, name)

    # -------------------------
    # Patients
    # -------------------------
    def add_patient(self, patient: Patient) -> None:
        Validator.validate_patient_id(patient.patientID)
        if patient.patientID in self.patients:
            raise ValueError(f"Patient {patient.patientID} already exists")
        self.patients[patient.patientID] = patient
        self.save_all()
        
    def delete_patient(self, patientID: str) -> bool:
        """
        Remove a patient profile and related local data.
        (Does not touch users dict — that is handled separately.)
        """
        changed = False

        # patient profile
        if patientID in self.patients:
            del self.patients[patientID]
            changed = True

        # preferences
        if patientID in self.preferences:
            del self.preferences[patientID]
            changed = True

        # aux patient logs json
        if patientID in self.patient_logs:
            del self.patient_logs[patientID]
            changed = True

        # clean any alert rows tied to this patient (optional but nice)
        if self.alerts:
            before = len(self.alerts)
            self.alerts = [a for a in self.alerts if getattr(a, "patientID", None) != patientID]
            changed = changed or (len(self.alerts) != before)

        if changed:
            self.save_all()
        return changed

    def get_patient(self, patientID: str) -> Optional[Patient]:
        return self.patients.get(patientID)

    def get_patients(self, patientIDs: List[str]) -> List[Patient]:
        return [self.patients[pid] for pid in patientIDs if pid in self.patients]

    def get_all_patients(self) -> List[Patient]:
        return list(self.patients.values())

    # -------------------------
    # Staff
    # -------------------------
    def add_staff(self, staff: Staff) -> None:
        Validator.validate_staff_id(staff.staffID)
        if staff.staffID in self.staffs:
            raise ValueError(f"Staff {staff.staffID} already exists")
        self.staffs[staff.staffID] = staff
        self.save_all()

    def get_staff(self, staffID: str) -> Optional[Staff]:
        return self.staffs.get(staffID)

    def get_all_staff(self) -> List[Staff]:
        return list(self.staffs.values())

    # -------------------------
    # Logs (clinical)
    # -------------------------
    def store_log(self, log: LogEntry) -> None:
        Validator.validate_log_entry_dict(log.to_dict())
        self.logs.append(log)
        self.save_all()

    def retrieve_logs(self, patientID: Optional[str] = None) -> List[LogEntry]:
        if patientID is None:
            return list(self.logs)
        return [l for l in self.logs if l.patientID == patientID]

    def get_log_by_id(self, log_id: str) -> Optional[LogEntry]:
        for log in self.logs:
            if log.logID == log_id:
                return log
        return None

    def update_log(
        self,
        log_id: str,
        updates: Dict[str, Any],
        who: Optional[str] = None,
        role: Optional[str] = None,
    ) -> bool:
        """
        Allowed fields: temperature, heartRate, bloodPressure, notes.
        RBAC: owner (staffID) or admin/siteadmin.
        Full audit snapshot recorded.
        """
        log = self.get_log_by_id(log_id)
        if not log:
            return False

        # RBAC check
        if who and hasattr(log, "staffID") and log.staffID != who and (role or "").lower() != "admin" and (role or "").lower() != "siteadmin":
            audit("log.update_denied", who=who, role=role, details={"logID": log_id, "reason": "insufficient_permissions"})
            return False

        before = log.to_dict()

        if "temperature" in updates:
            log.temperature = float(updates["temperature"]) if updates["temperature"] is not None else None
        if "heartRate" in updates:
            log.heartRate = int(updates["heartRate"]) if updates["heartRate"] is not None else None
        if "bloodPressure" in updates:
            log.bloodPressure = updates["bloodPressure"] or None
        if "notes" in updates:
            log.notes = updates["notes"] or None

        try:
            Validator.validate_log_entry_dict(log.to_dict())
        except Exception as e:
            audit("log.update_failed", who=who, role=role, details={"logID": log_id, "reason": "validation_error", "error": str(e)})
            return False

        self.save_all()

        audit(
            "log.update",
            who=who,
            role=role,
            details={
                "logID": log_id,
                "patientID": log.patientID,
                "before": {
                    "temperature": before.get("temperature"),
                    "heartRate": before.get("heartRate"),
                    "bloodPressure": before.get("bloodPressure"),
                    "notes": before.get("notes"),
                },
                "after": {
                    "temperature": log.temperature,
                    "heartRate": log.heartRate,
                    "bloodPressure": log.bloodPressure,
                    "notes": log.notes,
                },
            },
        )
        return True

    def delete_log(self, log_id: str, who: Optional[str] = None, role: Optional[str] = None) -> bool:
        idx = None
        victim = None

        for i, log in enumerate(self.logs):
            if log.logID == log_id:
                # RBAC: owner or admin/siteadmin
                if who and hasattr(log, "staffID") and log.staffID != who and (role or "").lower() not in {"admin", "siteadmin"}:
                    audit("log.delete_denied", who=who, role=role, details={"logID": log_id, "reason": "insufficient_permissions"})
                    return False
                idx = i
                victim = log
                break

        if idx is None or victim is None:
            return False

        del self.logs[idx]
        self.save_all()

        audit("log.delete",
              who=who, role=role,
              details={"logID": victim.logID, "patientID": victim.patientID, "staffID": getattr(victim, "staffID", None)})
        return True

    # PatientLog façade helpers (aliases)
    def store_patient_log(self, log: LogEntry) -> None:
        self.store_log(log)
        audit("patientlog.add", who=getattr(log, "staffID", None), role="staff",
              details={"patientID": log.patientID, "logID": log.logID})

    def retrieve_patient_logs(self, patientID: Optional[str] = None) -> List[LogEntry]:
        return self.retrieve_logs(patientID)

    def delete_patient_log(self, log_id: str, who: Optional[str] = None, role: Optional[str] = None) -> bool:
        ok = self.delete_log(log_id, who=who, role=role)
        if ok:
            audit("patientlog.delete", who=who, role=role, details={"logID": log_id})
        return ok

    # -------------------------
    # System logs (UI/system events)
    # -------------------------
    def store_system_log(self, entry: SystemLog) -> None:
        self.system_logs.append(entry)
        self.save_all()

    def get_system_logs(self) -> List[SystemLog]:
        return list(self.system_logs)

    # -------------------------
    # Alerts
    # -------------------------
    def add_alert(self, alert: Alert) -> None:
        self.alerts.append(alert)
        self.save_all()

    def get_alerts_for_staff(self, staffID: str) -> List[Alert]:
        return [a for a in self.alerts if a.staffID == staffID]

    def get_all_alerts(self) -> List[Alert]:
        return list(self.alerts)

    # -------------------------
    # Preferences
    # -------------------------
    def add_preferences(self, pref: Preferences) -> None:
        Validator.validate_patient_id(pref.patientID)
        self.preferences[pref.patientID] = pref
        self.save_all()

    def get_preferences(self, patientID: str) -> Optional[Preferences]:
        return self.preferences.get(patientID)

    def update_preferences(self, patientID: str, new_data: Dict[str, Any]) -> None:
        """
        Accepts keys:
          - preferred_language
          - dietaryNeeds (list or comma-separated string)
          - roomType
          - culturalNeeds
          - religiousNeeds
        """
        pref = self.preferences.get(patientID)

        # Normalize
        norm: Dict[str, Any] = {}

        d = new_data.get("dietaryNeeds") or new_data.get("dietary") or new_data.get("diet", "")
        if isinstance(d, str):
            dietary_list = [x.strip() for x in d.split(",") if x.strip()]
        elif isinstance(d, list):
            dietary_list = d
        else:
            dietary_list = []
        norm["dietaryNeeds"] = dietary_list

        norm["culturalNeeds"] = new_data.get("culturalNeeds") or new_data.get("cultural") or ""
        norm["religiousNeeds"] = new_data.get("religiousNeeds") or new_data.get("religious") or []

        for k in ["preferred_language", "roomType"]:
            if k in new_data:
                norm[k] = new_data[k]

        if not pref:
            # Create
            try:
                if hasattr(Preferences, "from_dict"):
                    pref_obj = Preferences.from_dict({"patientID": patientID, **norm})
                else:
                    pref_obj = Preferences(
                        patientID=patientID,
                        dietaryNeeds=norm.get("dietaryNeeds", []),
                        culturalNeeds=norm.get("culturalNeeds", ""),
                        religiousNeeds=norm.get("religiousNeeds", []),
                    )
                if hasattr(pref_obj, "preferred_language") and "preferred_language" in norm:
                    pref_obj.preferred_language = norm["preferred_language"]
                if hasattr(pref_obj, "roomType") and "roomType" in norm:
                    pref_obj.roomType = norm["roomType"]
                self.preferences[patientID] = pref_obj
            except Exception:
                self.preferences[patientID] = Preferences(
                    patientID=patientID,
                    dietaryNeeds=norm.get("dietaryNeeds", []),
                    culturalNeeds=norm.get("culturalNeeds", ""),
                    religiousNeeds=norm.get("religiousNeeds", []),
                )
        else:
            # Update
            try:
                if hasattr(pref, "editPreference"):
                    pref.editPreference(norm)  # type: ignore[attr-defined]
                else:
                    for k, v in norm.items():
                        if hasattr(pref, k):
                            setattr(pref, k, v)

                if "preferred_language" in norm and hasattr(pref, "preferred_language"):
                    pref.preferred_language = norm["preferred_language"]
                if "roomType" in norm and hasattr(pref, "roomType"):
                    pref.roomType = norm["roomType"]
            except Exception:
                for k, v in norm.items():
                    try:
                        setattr(pref, k, v)
                    except Exception:
                        pass

        self.save_all()

    # -------------------------
    # Audit log (memory + persisted)
    # -------------------------
    def add_audit_log(self, log_entry: Dict[str, Any]) -> None:
        self.audit_logs.append(log_entry)
        # write-through for durability
        self._safe_write_encrypted_jsonl(self.audit_log_file, self.audit_logs)

    def get_audit_logs(self, action: Optional[str] = None, who: Optional[str] = None) -> List[Dict[str, Any]]:
        logs = self.audit_logs
        if action:
            logs = [l for l in logs if l.get("action") == action]
        if who:
            logs = [l for l in logs if l.get("who") == who]
        return logs

    # -------------------------
    # Assignments (patient <-> staff pairs)
    # -------------------------
    def _row_key(self, row: Dict[str, Any]) -> tuple[str, str]:
        return (str(row.get("patientID") or ""), str(row.get("staffID") or ""))

    def add_assignment(self, staffID: str, assignment_data: Dict[str, Any]) -> bool:
        """
        Add a unique (patientID, staffID) pair. Returns True if added, False if duplicate.
        assignment_data must contain patientID, assignedBy, ts. staffID is injected/overridden.
        """
        row = dict(assignment_data or {})
        row["staffID"] = staffID
        pid, sid = self._row_key(row)
        if not pid or not sid:
            return False

        # de-dup
        for r in self.assignments:
            if self._row_key(r) == (pid, sid):
                return False

        self.assignments.append(row)
        self.save_all()
        return True

    def get_assignment(self, staffID: str) -> List[Dict[str, Any]]:
        sid = str(staffID or "")
        return [r for r in self.assignments if str(r.get("staffID") or "") == sid]

    def get_all_assignments(self) -> List[Dict[str, Any]]:
        return list(self.assignments)

    def delete_assignment(self, staffID: str, patientID: str | None = None) -> bool:
        """
        Remove either all rows for a staff (if patientID is None) or the specific pair.
        Returns True if anything was removed.
        """
        before = len(self.assignments)
        sid = str(staffID or "")
        pid = str(patientID or "")

        if patientID is None:
            self.assignments = [r for r in self.assignments if str(r.get("staffID") or "") != sid]
        else:
            self.assignments = [
                r for r in self.assignments
                if not (str(r.get("staffID") or "") == sid and str(r.get("patientID") or "") == pid)
            ]
        changed = len(self.assignments) != before
        if changed:
            self.save_all()
        return changed

    def replace_assignment(self, patientID: str, new_staffID: str, assignment_data: Dict[str, Any] | None = None) -> bool:
        """
        Remove all staff mappings for a patient and add the new (patientID,new_staffID) row.
        """
        pid = str(patientID or "")
        before = len(self.assignments)
        self.assignments = [r for r in self.assignments if str(r.get("patientID") or "") != pid]
        _ = len(self.assignments) != before  # removed?

        base = dict(assignment_data or {})
        base["patientID"] = pid
        base["assignedBy"] = base.get("assignedBy") or "admin"
        base["ts"] = base.get("ts") or datetime.datetime.utcnow().isoformat() + "Z"
        self.add_assignment(new_staffID, base)
        return True

    # -------------------------
    # Patient Logs (aux JSON)
    # -------------------------
    def add_patient_log(self, patientID: str, log_data: Dict[str, Any]) -> None:
        if patientID not in self.patient_logs:
            self.patient_logs[patientID] = []
        self.patient_logs[patientID].append(log_data)
        self.save_all()

    def get_patient_logs(self, patientID: str) -> List[Dict[str, Any]]:
        return self.patient_logs.get(patientID, [])

    # -------------------------
    # Translate Cache
    # -------------------------
    def add_translation(self, key: str, translation: str) -> None:
        self.translate_cache[key] = translation
        self.save_all()

    def get_translation(self, key: str) -> Optional[str]:
        return self.translate_cache.get(key)

    def clear_translation_cache(self) -> None:
        self.translate_cache = {}
        self.save_all()

    # -------------------------
    # Utilities
    # -------------------------
    def find_patient_id_by_name_exact(self, name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Exact, case-insensitive match on patient 'name'.
        Returns (patient_id, error_message). If multiple, returns (None, msg).
        """
        nm = (name or "").strip().casefold()
        if not nm:
            return None, None

        matches = [
            pid for pid, patient in self.patients.items()
            if (getattr(patient, "name", "") or "").strip().casefold() == nm
        ]

        if not matches:
            # fall back to users with role=patient
            matches = [
                uid for uid, user in self.users.items()
                if (user.get("role") or "").lower() == "patient"
                and (user.get("name") or "").strip().casefold() == nm
            ]

        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            return None, "Multiple patients share this name. Please use your Patient ID."
        return None, None
