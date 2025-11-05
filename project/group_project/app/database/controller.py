# app/database/controller.py

from __future__ import annotations

import datetime
from typing import List, Callable, Optional, Tuple, Dict, Any

from app.database.database_Manager import DatabaseManager
from app.users.patient import Patient
from app.users.staff import Staff
from app.core.alert import Alert
from app.logging.logentry import LogEntry
from app.users.preferences import Preferences
from app.core.validator import Validator
from app.logging.system_log import SystemLog
from app.reports.report_Generator import ReportGenerator
from app.logging.patient_Log import PatientLog
from app.core.search import SearchEngine

# ---- Assignments store (single source of truth) ----
# Keep this import tolerant to minor path/name differences in your repo.
try:
    from app.core import assignment_Store as _ASG
except Exception:
    # Fallback: provide a tiny no-op shim so the UI stays functional even if
    # the assignment store isn’t available during a refactor.
    class _NoopAssignments:
        @staticmethod
        def assign(pid: str, sid: str, by: str) -> tuple[bool, str]:
            return False, "Assignment store is unavailable."

        @staticmethod
        def unassign(pid: str, sid: str, by: str | None = None) -> tuple[bool, str]:
            return False, "Assignment store is unavailable."

        @staticmethod
        def replace_assignments(pid: str, sid: str, by: str | None = None) -> tuple[bool, str]:
            return False, "Assignment store is unavailable."

        @staticmethod
        def patients_for_staff(sid: str) -> List[str]:
            return []

        @staticmethod
        def staff_for_patient(pid: str) -> List[str]:
            return []

        @staticmethod
        def is_allowed(sid: str, pid: str) -> bool:
            return False

        @staticmethod
        def get_assignments() -> List[Dict[str, Any]]:
            return []

    _ASG = _NoopAssignments()  # type: ignore


# ---- Optional UI language map (safe import) ----
try:
    from gui.ui import LANG_CODE_TO_NAME
except Exception:
    LANG_CODE_TO_NAME = {}  # graceful no-op map


# Back-compat global used by a few legacy modules
current_user_id = None


class Controller:
    """
    Thin application service that coordinates the DB manager, the assignment
    store, and the view layer. It **does not** seed users or pre-hash passwords.
    All persistence goes:  file (views) -> controller -> db  (and back).
    """

    def __init__(self, currentuser: Optional[Any] = None):
        # Single DBM instance for this controller
        self.db = DatabaseManager()

        # Optional external user store (object-style users); most flows use DBM directly
        self.user_store = currentuser
        self.current_user: Optional[Any] = None
        self.current_user_id: Optional[str] = None

        # Feature helpers
        self.patient_log = PatientLog()
        self.report_generator = ReportGenerator(self.db)
        self.search_engine = SearchEngine(self.db)

    # ----------------------------------
    # Per-account language settings
    # ----------------------------------
    def get_user_default_lang(self, userID: str) -> Optional[str]:
        try:
            rec = self.db.get_user(userID) or {}
        except Exception:
            return None
        lang = rec.get("default_ui_lang")
        return lang if lang in LANG_CODE_TO_NAME else None

    def set_user_default_lang(self, username: str, lang_code: str) -> bool:
        if lang_code not in LANG_CODE_TO_NAME:
            return False
        try:
            self.db.user_set_default_lang(username, lang_code)
            return True
        except Exception:
            return False

    # ----------------------------------
    # Session / current user (merge of code1+code2)
    # ----------------------------------
    def refresh_current_user(self, user_id: str):
        global current_user_id
        self.current_user_id = user_id
        current_user_id = user_id  # keep legacy behavior

        if self.user_store and hasattr(self.user_store, "get_user_by_id"):
            user = self.user_store.get_user_by_id(user_id)
            self.current_user = user if user else None

    # ----------------------------------
    # Helpers for "who is acting"
    # ----------------------------------
    def _actor_id(self) -> str:
        if self.current_user and hasattr(self.current_user, "userID"):
            return self.current_user.userID
        return self.current_user_id or "system"

    # ----------------------------------
    # PATIENT MANAGEMENT
    # ----------------------------------
    def register_patient(self, patient_data: dict):
        """Create a patient profile in patients.json."""
        Validator.validate_patient_id(patient_data["patientID"])
        patient = Patient.from_dict(patient_data)
        self.db.add_patient(patient)
        self.log_action(self._actor_id(), f"Patient {patient.patientID} registered by {self._actor_id()}.")
        return patient

    def delete_patient(self, patientID: str) -> bool:
        """Delete internal patient profile + related DB items."""
        return self.db.delete_patient(patientID)

    def get_patient(self, patientID: str):
        self.log_action(self._actor_id(), f"Request for patient ID:{patientID} by {self._actor_id()}")
        return self.db.get_patient(patientID)

    def get_all_patients(self) -> List[Patient]:
        return self.db.get_all_patients()

    def update_patient_info(self, patientID: str, updates: dict):
        patient = self.db.get_patient(patientID)
        if not patient:
            raise ValueError("Patient not found.")
        for key, val in updates.items():
            if hasattr(patient, key):
                setattr(patient, key, val)
        self.db.save_all()
        self.log_action(self._actor_id(), f"Patient info updated: {list(updates.keys())} by {self._actor_id()}")

    # ----------------------------------
    # STAFF MANAGEMENT
    # ----------------------------------
    def register_staff(self, staff_data: dict):
        """Create a staff profile in staffs.json."""
        Validator.validate_staff_id(staff_data.get("staffID"))
        staff = Staff.from_dict(staff_data)
        self.db.add_staff(staff)
        self.log_action(self._actor_id(), f"Staff {staff.staffID} registered by {self._actor_id()}.")
        return staff

    def get_staff(self, staffID: str):
        self.log_action(self._actor_id(), f"Request for staff ID:{staffID} by {self._actor_id()}")
        return self.db.get_staff(staffID)

    def get_all_staff(self) -> List[Staff]:
        return self.db.get_all_staff()

    # Clean up all assignments & references when a staff is deleted
    def cleanup_staff_on_delete(self, staff_id: str, *, actor: str = "admin") -> None:
        """
        Unassign staff_id from every patient and clear any profile references.
        Safe to call even if assignment store or patient fields differ.
        """
        sid = (staff_id or "").strip().upper()

        # 1) Unassign via assignment store
        try:
            pids = list(self.get_patients_for_staff(sid) or [])
        except Exception:
            pids = []
        for pid in pids:
            try:
                _ASG.unassign(pid, sid, actor)
            except Exception:
                pass

        # 2) Clear direct references inside patient profiles
        changed = False
        try:
            for p in self.db.patients.values():
                if getattr(p, "assignedStaffID", None) == sid:
                    try:
                        p.assignedStaffID = None
                        changed = True
                    except Exception:
                        pass
        except Exception:
            pass
        if changed:
            try:
                self.db.save_all()
            except Exception:
                pass

        # 3) If DB holds simple assignment rows keyed by staffID, drop them too
        try:
            self.db.delete_assignment(sid)
        except Exception:
            pass

    # ----------------------------------
    # PREFERENCES MANAGEMENT
    # ----------------------------------
    def set_preferences(self, patientID: str, pref_data: dict):
        pref = Preferences.from_dict({"patientID": patientID, **pref_data})
        self.db.add_preferences(pref)
        self.log_action(self._actor_id(), f"Preferences set/updated by {self._actor_id()}")
        return pref

    def edit_preferences(self, patientID: str, updates: dict):
        self.db.update_preferences(patientID, updates)
        self.log_action(self._actor_id(), f"Preferences edited: {list(updates.keys())} by {self._actor_id()}")

    def get_preferences(self, patientID: str):
        self.log_action(patientID, f"Request for preference of ID:{patientID} by {self._actor_id()}")
        return self.db.get_preferences(patientID)

    # ----------------------------------
    # ASSIGNMENTS (single point of truth: assignment_Store + persisted list)
    # ----------------------------------
    def assign_patient_to_staff(self, patient_id: str, staff_id: str, admin_username: str):
        # Validate IDs
        Validator.validate_patient_id((patient_id or "").strip().upper())
        Validator.validate_staff_id((staff_id or "").strip().upper())

        ok, msg = _ASG.assign(patient_id, staff_id, admin_username)

        # Best-effort mirror into DBM.assignments for quick list rendering
        if ok:
            try:
                self.db.add_assignment(staff_id, {
                    "patientID": patient_id,
                    "staffID": staff_id,
                    "assignedBy": admin_username,
                    "ts": datetime.datetime.utcnow().isoformat() + "Z",
                })
            except Exception:
                pass
            try:
                self.log_action(admin_username, f"Assigned patient {patient_id} to staff {self._actor_id()}")
            except Exception:
                pass
        return ok, msg

    def unassign_patient_from_staff(self, patient_id: str, staff_id: str, admin_username: str = "admin"):
        ok, msg = _ASG.unassign(patient_id, staff_id, admin_username)

        # Mirror removal from DBM.assignments if it matches staffID and patientID
        if ok:
                # Always attempt local cleanup to keep the GUI consistent
            try:
                rows = self.db.get_all_assignments()
                
                new_rows = [
                    r for r in rows
                    if not ((r.get("staffID") == staff_id) and (r.get("patientID") == patient_id))
                ]
                removed = len(rows) - len(new_rows)

                self.db.assignments = {r.get("staffID"): r for r in new_rows if r.get("staffID")}
                self.db.save_all()
            except Exception as e:
                print(f"ERROR during DB cleanup: {e}")

            if not ok and "No such assignment" in msg and removed > 0:
                # adjust msg to be clearer
                ok, msg = True, "Local record cleaned up"

            try:
                actor_id = self._actor_id()
                self.log_action(admin_username, f"Unassigned patient {patient_id} from staff {actor_id}")
            except Exception as e:
                print(f"ERROR during log_action: {e}")

        return ok, msg

    def replace_patient_staff(self, patient_id: str, new_staff_id: str, admin_username: str):
        ok, msg = _ASG.replace_assignments(patient_id, new_staff_id, admin_username)
        if ok:
            try:
                self.db.add_assignment(new_staff_id, {
                    "patientID": patient_id,
                    "staffID": new_staff_id,
                    "assignedBy": admin_username,
                    "ts": datetime.datetime.utcnow().isoformat() + "Z",
                })
            except Exception:
                pass
            try:
                actor_id = self._actor_id() 
                self.log_action(admin_username, f"Reassigned patient {patient_id} to staff {actor_id}")
            except Exception:
                pass
        return ok, msg

    def get_patients_for_staff(self, staff_id: str) -> List[str]:
        return _ASG.patients_for_staff(staff_id)

    def get_staff_for_patient(self, patient_id: str) -> List[str]:
        return _ASG.staff_for_patient(patient_id)

    def is_staff_allowed_for_patient(self, staff_id: str, patient_id: str) -> bool:
        return _ASG.is_allowed(staff_id, patient_id)

    def list_assignments(self) -> List[Dict[str, Any]]:
        """
        Prefer the assignment store; if unavailable, fall back to DB mirror.
        Always return a homogeneous list of dict rows.
        """
        try:
            if hasattr(_ASG, "get_assignments"):
                rows = _ASG.get_assignments()
                if isinstance(rows, list) and rows:
                    out = []
                    for r in rows:
                        out.append({
                            "patientID": r.get("patientID") or r.get("pid") or "",
                            "staffID": r.get("staffID") or r.get("sid") or "",
                            "assignedBy": r.get("assignedBy") or r.get("by") or "",
                            "ts": r.get("ts") or r.get("timestamp") or "",
                        })
                    return out
        except Exception:
            pass

        # Fallback: mirror in DBM
        try:
            out = []
            for rec in self.db.get_all_assignments():
                out.append({
                    "patientID": rec.get("patientID") or rec.get("pid") or "",
                    "staffID": rec.get("staffID") or rec.get("sid") or "",
                    "assignedBy": rec.get("assignedBy") or rec.get("by") or "",
                    "ts": rec.get("ts") or rec.get("timestamp") or "",
                })
            return out
        except Exception:
            return []

    # ----------------------------------
    # SEARCH
    # ----------------------------------
    def search_logs(self, keyword: str, patient_id: str = None, start_date: str = None, end_date: str = None):
        date_range = None
        if start_date and end_date:
            date_range = (start_date, end_date)
        return self.search_engine.search_logs(keyword, patient_id, date_range)

    def refresh_log_index(self):
        self.search_engine.refresh_index()
        return f"Search index refreshed. {self.search_engine.get_index_size()} logs indexed."

    def highlight_text(self, text: str, keyword: str):
        return self.search_engine.highlight_matches(text, keyword)

    # ----------------------------------
    # LOGS (legacy PatientLog façade)
    # ----------------------------------
    def _new_log_id(self) -> str:
        try:
            n = len(self.patient_log.get_logs())
        except Exception:
            n = int(datetime.datetime.now().timestamp())
        return f"L{n + 1:03}"

    def add_patient_log(self, patient_id: str, staff_id: str,
                        temperature: float, heart_rate: int,
                        blood_pressure: str, notes: str = ""):
        log = LogEntry(
            logID=self._new_log_id(),
            patientID=patient_id,
            staffID=staff_id,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            temperature=temperature,
            heartRate=heart_rate,
            bloodPressure=blood_pressure,
            notes=notes,
        )
        self.patient_log.add_log(log.to_dict())
        return log

    def get_patient_logs(self, patient_id: str):
        return self.patient_log.find_by_patient(patient_id)

    def find_by_staff(self, staff_id: str):
        return self.patient_log.find_by_staff(staff_id)

    def find_by_date(self, start: str, end: str):
        return self.patient_log.find_by_date(start, end)

    def delete_log(self, log_id: str):
        self.patient_log.delete_log(log_id)

    # ----------------------------------
    # Simple patient filters
    # ----------------------------------
    def filter_patients_by_condition(self, keyword: str):
        keyword = keyword.lower()
        return [
            p.patientID for p in self.db.patients.values()
            if getattr(p, "condition", None) and keyword in p.condition.lower()
        ]

    def filter_patients_by_metric(self, metric: str, comparison: Callable[[float], bool]):
        return self.patient_log.filter_by_metric(metric, comparison)

    # ----------------------------------
    # ALERTS
    # ----------------------------------
    def create_alert(self, *args, **kwargs):
        if len(args) >= 4:
            severity, patientID, staffID, message = args[:4]
            alert = Alert(
                alertID=f"A{len(self.db.alerts) + 1:03}",
                staffID=staffID,
                message=message,
                patientID=patientID,
                severity=severity,
                timestamp=datetime.datetime.now().isoformat(),
            )
        else:
            staffID, message = args[:2]
            severity = kwargs.get("severity", "info")
            patientID = kwargs.get("patientID")
            alert = Alert(
                alertID=f"A{len(self.db.alerts) + 1:03}",
                staffID=staffID,
                message=message,
                patientID=patientID,
                severity=severity,
                timestamp=datetime.datetime.now().isoformat(),
            )
        self.db.add_alert(alert)
        self.log_action(staffID, f"Alert created: {message}")
        return alert

    def get_staff_alerts(self, staffID: str):
        return self.db.get_alerts_for_staff(staffID)

    # ----------------------------------
    # REPORT GENERATION
    # ----------------------------------
    def get_patient_report(self, patient_id) -> List[dict]:
        return self.report_generator.generate_patient_report(patient_id)

    def get_multi_patient_report(self, patient_ids: List[str]) -> List[dict]:
        return self.report_generator.generate_multi_patient_report(patient_ids)

    def get_filter_report_by_keywords(self, keywords: str) -> List[dict]:
        ids = self.patient_log.find_patient_ids_by_note_keyword(keywords)
        return self.report_generator.generate_multi_patient_report(ids)

    def get_filter_report_by_metric(self, metric: str, comparison: Callable[[float], bool]) -> List[dict]:
        ids = self.patient_log.filter_by_metric(metric, comparison)
        return self.report_generator.generate_multi_patient_report(ids)

    def export_patient_report(self, patient_id, filename: str):
        data = self.get_patient_report(patient_id)
        self.report_generator.export_report_to_file(data, filename=filename)

    def export_multi_patient_report(self, patient_ids: List[str], filename: str):
        data = self.get_multi_patient_report(patient_ids)
        self.report_generator.export_report_to_file(data, filename=filename)

    def export_filter_report_by_keywords(self, keywords: str, filename: str):
        data = self.get_filter_report_by_keywords(keywords)
        self.report_generator.export_report_to_file(data, filename=filename)

    def export_filter_report_by_metric(self, metric: str, comparison: Callable[[float], bool], filename: str):
        data = self.get_filter_report_by_metric(metric, comparison)
        self.report_generator.export_report_to_file(data, filename=filename)

    def export_patient_report_inpdf(self, staff_id,
                                    patientID,
                                    out_path,
                                    period,  # 'weekly' or 'monthly'
                                    ):
        return self.report_generator.export_patient_report_to_pdf(
            staff_id=staff_id,
            patientID=patientID,
            out_path=out_path,
            period=period,
        )

    # ----------------------------------
    # System logging
    # ----------------------------------
    def log_action(self, userID: str, action: str):
        entry = SystemLog(
            logID=self._new_log_id(),
            userID=userID,
            action=action,
            timestamp=datetime.datetime.now().isoformat(),
        )
        self.db.store_system_log(entry)

    # ----------------------------------
    # Users (DB passthroughs)
    # ----------------------------------
    def hash_password(self, username: str, password: str) -> str:
        return self.db.hash_pwd(username, password)

    def create_user(self, username: str, password: str, role: str, name: str) -> None:
        # IMPORTANT: pass PLAINTEXT; DBM hashes internally.
        self.db.create_user(username, password, role, name)

    def ensure_user(self, username: str, password: str, role: str, name: str) -> None:
        # IMPORTANT: pass PLAINTEXT; DBM hashes internally.
        self.db.ensure_user(username, password, role, name)

    def delete_user(self, username: str) -> bool:
        return self.db.delete_user(username)

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.db.get_user(user_id)

    def get_all_users(self) -> List[dict]:
        return self.db.get_all_users()

    def verify_user(self, username: str, password: str) -> bool:
        return self.db.verify_user(username, password)

    def list_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        return self.db.list_users_by_role(role)

    def find_patient_id_by_name_exact(self, name: str) -> Tuple[Optional[str], Optional[str]]:
        return self.db.find_patient_id_by_name_exact(name)

    # ----------------------------------
    # Quick properties for views
    # ----------------------------------
    @property
    def patients(self):
        return self.db.patients

    @property
    def staffs(self):
        return self.db.staffs

    # --- Admin Dashboard shims ---
    def assign_staff_to_patient(self, patient_id: str, staff_id: str, admin_username: str):
        # (kept for back-compat; calls the canonical method above)
        return self.assign_patient_to_staff(patient_id, staff_id, admin_username)

    def unassign_staff_from_patient(self, patient_id: str, staff_id: str, admin_username: str = "admin"):
        return self.unassign_patient_from_staff(patient_id, staff_id, admin_username)

    # ----------------------------------
    # Audit log access/exports
    # ----------------------------------
    def get_audit_log(self):
        try:
            return list(self.db.audit_logs)
        except Exception:
            return []

    def export_audit_log_csv(self) -> str:
        import io, csv, json
        rows = self.get_audit_log()
        if not rows:
            return ""
        header = ["ts", "who", "role", "event", "details"]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            rr = dict(r)
            if isinstance(rr.get("details"), (dict, list)):
                rr["details"] = json.dumps(rr["details"], ensure_ascii=False)
            w.writerow({k: rr.get(k, "") for k in header})
        return buf.getvalue()

    def export_audit_log_jsonl(self) -> str:
        import json
        rows = self.get_audit_log()
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else "")
