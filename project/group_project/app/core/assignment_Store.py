# app/core/assignment_Store.py
from __future__ import annotations
from app.core.validator import read_json_file, atomic_write_json  # ensure both imported
import os, json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import List, Tuple, Dict, Any
from app.core.validator import atomic_write_json
ASSIGNMENTS_FILE = os.path.join("data", "assignments.json")

# Try to use your app's atomic writer if present




def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def _load_rows() -> List[Dict[str, Any]]:
    """
    Loads assignment records (automatically handles encryption if enabled).
    Falls back to empty list if file missing or unreadable.
    """
    try:
        data = read_json_file(ASSIGNMENTS_FILE, encrypted=True)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️ _load_rows() failed to read: {e}")
        return []

def _save_rows(rows: List[Dict[str, Any]]) -> None:
    atomic_write_json(ASSIGNMENTS_FILE, rows, encrypt=True)

def _normalize_row(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "patientID": r.get("patientID") or r.get("patient_id") or "",
        "staffID":   r.get("staffID")   or r.get("staff_id")   or "",
        "assignedBy": r.get("assignedBy") or r.get("assigned_by") or "",
        "ts": r.get("ts") or r.get("timestamp") or "",
    }

# ---------- Core helpers ----------
def patients_for_staff(staff_id: str) -> List[str]:
    """Return list of patientIDs assigned to a staff member."""
    sid = (staff_id or "").strip()
    out = [r["patientID"] for r in map(_normalize_row, _load_rows()) if r["staffID"] == sid]
    # De-duplicate, preserve order (newest first)
    seen = set()
    out_rev = []
    for pid in reversed(out):
        if pid not in seen:
            seen.add(pid)
            out_rev.append(pid)
    return list(reversed(out_rev))

def staff_for_patient(patient_id: str) -> List[str]:
    """Return list of staffIDs assigned to a patient."""
    pid = (patient_id or "").strip()
    out = [r["staffID"] for r in map(_normalize_row, _load_rows()) if r["patientID"] == pid]
    seen = set()
    out_rev = []
    for sid in reversed(out):
        if sid not in seen:
            seen.add(sid)
            out_rev.append(sid)
    return list(reversed(out_rev))

def is_allowed(staff_id: str, patient_id: str) -> bool:
    """RBAC check for staff-to-patient access."""
    sid = (staff_id or "").strip()
    pid = (patient_id or "").strip()
    if not sid or not pid:
        return False
    return sid in staff_for_patient(pid)

# ---------- Mutations (both API styles supported) ----------
def assign(patient_id: str, staff_id: str, assigned_by: str = "admin") -> Tuple[bool, str]:
    """Add an assignment if not present (returns idempotent success)."""
    pid = (patient_id or "").strip()
    sid = (staff_id or "").strip()
    if not pid or not sid:
        return False, "patient_id and staff_id are required"
    rows = list(map(_normalize_row, _load_rows()))
    if any(r["patientID"] == pid and r["staffID"] == sid for r in rows):
        return True, "Already assigned"
    rows.append({"patientID": pid, "staffID": sid, "assignedBy": assigned_by or "admin", "ts": _utc_now_iso()})
    _save_rows(rows)
    return True, "Assigned"

def unassign(patient_id: str, staff_id: str, assigned_by: str = "admin") -> Tuple[bool, str]:
    pid = (patient_id or "").strip()
    sid = (staff_id or "").strip()

    rows = list(map(_normalize_row, _load_rows()))

    new_rows = [r for r in rows if not (r["patientID"] == pid and r["staffID"] == sid)]
    
    if len(new_rows) == len(rows):
        return False, "No such assignment"
    _save_rows(new_rows)
    return True, "Unassigned"

def replace_assignments(patient_id: str, new_staff_id: str, assigned_by: str = "admin") -> Tuple[bool, str]:
    pid = (patient_id or "").strip()
    sid = (new_staff_id or "").strip()
    if not pid or not sid:
        return False, "patient_id and new_staff_id are required"
    rows = list(map(_normalize_row, _load_rows()))
    rows = [r for r in rows if r["patientID"] != pid]  # remove all current staff for pid
    rows.append({"patientID": pid, "staffID": sid, "assignedBy": assigned_by or "admin", "ts": _utc_now_iso()})
    _save_rows(rows)
    return True, "Replaced assignments"

# ---------- Alternate names used in other parts of the app ----------
def assign_staff_to_patient(staff_id: str, patient_id: str, assigned_by: str = "admin") -> Tuple[bool, str]:
    return assign(patient_id=patient_id, staff_id=staff_id, assigned_by=assigned_by)

def unassign_staff_from_patient(staff_id: str, patient_id: str) -> Tuple[bool, str]:
    return unassign(patient_id=patient_id, staff_id=staff_id)

def list_all():
    """Return rows with attribute access (r.patientID etc.) to match existing UI code."""
    rows = list(map(_normalize_row, _load_rows()))
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return [SimpleNamespace(**r) for r in rows]

def get_assignments() -> List[Dict[str, Any]]:
    """Return plain dicts (used by some admin dashboards)."""
    return list(map(_normalize_row, _load_rows()))
