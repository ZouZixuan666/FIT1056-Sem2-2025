# gui/views/patient_Management.py
from __future__ import annotations

import streamlit as st
import pandas as pd

from gui.ui import u
from app.database.controller import Controller
from app.users.patient import Patient
from app.core.validator import Validator  # strict P### / S### validation

# Auditing (safe import)
try:
    from app.core.audit import audit
except Exception:
    def audit(*args, **kwargs):  # type: ignore
        pass


# -----------------------------
# Controller singleton for this session
# -----------------------------
def _get_ctrl() -> Controller:
    if "__CTRL__" not in st.session_state:
        st.session_state["__CTRL__"] = Controller()
    return st.session_state["__CTRL__"]


# -----------------------------
# Small, robust extractors
# -----------------------------
def _rec_username(rec) -> str | None:
    if isinstance(rec, dict):
        return rec.get("username") or rec.get("userID") or rec.get("id")
    if isinstance(rec, (list, tuple)) and rec:
        return str(rec[0])
    try:
        return getattr(rec, "username", None) or getattr(rec, "userID", None) or getattr(rec, "id", None)
    except Exception:
        return None


def _rec_name(rec) -> str | None:
    if isinstance(rec, dict):
        return rec.get("name") or rec.get("full_name")
    if isinstance(rec, (list, tuple)) and len(rec) > 1:
        return str(rec[1])
    try:
        return getattr(rec, "name", None) or getattr(rec, "full_name", None)
    except Exception:
        return None


def _get_attr(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        val = obj.get(key, default)
        return default if val in (None, "") else val
    try:
        val = getattr(obj, key, default)
        return default if val in (None, "") else val
    except Exception:
        return default


# -----------------------------
# Helpers
# -----------------------------
def _ensure_patient_profile(
    ctrl: Controller,
    patient_id: str,
    full_name: str,
    age: int | None,
    condition: str | None,
    assigned_staff: str | None,
    *,
    allow_assign: bool
) -> None:
    """Ensure a patient profile exists or is synced. Only admins/siteadmins can set assignedStaffID."""
    try:
        existing = getattr(ctrl, "get_patient", None)
        existing = existing(patient_id) if existing else None

        if existing:
            changed = False
            if full_name and _get_attr(existing, "name") != full_name:
                setattr(existing, "name", full_name); changed = True
            if age is not None and _get_attr(existing, "age") != age:
                setattr(existing, "age", age); changed = True
            if _get_attr(existing, "condition") != (condition or None):
                setattr(existing, "condition", condition or None); changed = True

            if allow_assign and _get_attr(existing, "assignedStaffID") != (assigned_staff or None):
                setattr(existing, "assignedStaffID", assigned_staff or None); changed = True

            if changed:
                ctrl.update_patient_info(
                    patient_id,
                    {
                        "name": _get_attr(existing, "name"),
                        "age": _get_attr(existing, "age"),
                        "condition": _get_attr(existing, "condition"),
                        "assignedStaffID": _get_attr(existing, "assignedStaffID"),
                    },
                )
            return
    except Exception:
        pass

    # Create profile if missing (Patient class import is used here)
    try:
        p = Patient(
            userID=patient_id,
            patientID=patient_id,
            name=full_name or patient_id,
            age=age if age is not None else None,
            condition=condition or None,
            assignedStaffID=(assigned_staff or None) if allow_assign else None,
        )
        # Controller.register_patient expects dict
        payload = p.to_dict() if hasattr(p, "to_dict") else {
            "patientID": p.patientID,
            "name": p.name,
            "age": p.age,
            "condition": p.condition,
            "assignedStaffID": p.assignedStaffID
        }
        ctrl.register_patient(payload)
    except Exception:
        pass


def _create_patient_login(
    ctrl: Controller,
    patient_id: str,
    full_name: str,
    temp_password: str,
    *,
    age: int | None,
    condition: str | None,
    assigned_staff: str | None,
    allow_assign: bool
) -> tuple[bool, str]:
    patient_id = (patient_id or "").upper().strip()
    try:
        Validator.validate_patient_id(patient_id)
    except Exception as e:
        return False, u(str(e))

    if ctrl.get_user(patient_id):
        return False, u("A user with this ID already exists.")

    # Optional: validate assigned staff if present and allowed
    if allow_assign and assigned_staff:
        try:
            Validator.validate_staff_id(assigned_staff)
        except Exception as e:
            return False, u(str(e))

    try:
        # IMPORTANT: pass PLAINTEXT. DB hashes internally.
        ctrl.create_user(patient_id, temp_password, "patient", full_name or patient_id)

        _ensure_patient_profile(
            ctrl,
            patient_id,
            full_name,
            age,
            condition,
            (assigned_staff or None) if allow_assign else None,
            allow_assign=allow_assign,
        )

        audit("patient.create",
              who=(st.session_state.get("auth") or {}).get("username"),
              role=(st.session_state.get("auth") or {}).get("role"),
              details={"username": patient_id})
        return True, u("Patient login created.")
    except Exception as e:
        audit("patient.create_failed",
              who=(st.session_state.get("auth") or {}).get("username"),
              role=(st.session_state.get("auth") or {}).get("role"),
              details={"username": patient_id, "error": str(e)})
        return False, u(f"Failed to create login: {e}")


def _collect_profile_map(ctrl: Controller, ids: list[str]) -> dict[str, object]:
    pmap: dict[str, object] = {}
    try:
        repo = getattr(ctrl, "patients", None)
        if isinstance(repo, dict) and repo:
            for pid, obj in repo.items():
                pmap[str(pid)] = obj
    except Exception:
        pass

    if not pmap:
        try:
            allp = ctrl.get_all_patients()  # may be list of Patient objects
            for obj in (allp or []):
                pid = _get_attr(obj, "patientID")
                if pid:
                    pmap[str(pid)] = obj
        except Exception:
            pass

    for pid in ids:
        if pid in pmap:
            continue
        try:
            obj = ctrl.get_patient(pid)
            if obj:
                pmap[pid] = obj
        except Exception:
            continue

    return pmap


def _migrate_unlinked_patients(ctrl: Controller, default_temp_pw: str) -> tuple[int, int, list[str], list[str]]:
    created = skipped = 0
    created_ids: list[str] = []
    invalid_ids: list[str] = []

    # Gather profiles
    try:
        patients = ctrl.get_all_patients() or []
    except Exception:
        patients = []
        try:
            repo = getattr(ctrl, "patients", {})
            if isinstance(repo, dict):
                patients = list(repo.values())
        except Exception:
            pass

    existing = {(_rec_username(u) or "").upper() for u in (ctrl.list_users_by_role("patient") or [])}

    for p in patients:
        pid = (_get_attr(p, "patientID") or "").upper().strip()
        if not pid:
            continue
        try:
            Validator.validate_patient_id(pid)
        except Exception:
            invalid_ids.append(pid)
            continue

        if pid in existing:
            skipped += 1
            continue

        try:
            # PLAINTEXT -> DB hashes
            ctrl.create_user(pid, default_temp_pw, "patient", _get_attr(p, "name") or pid)
            created += 1
            created_ids.append(pid)
        except Exception:
            skipped += 1

    audit("patient.bulk_create",
          who=(st.session_state.get("auth") or {}).get("username"),
          role=(st.session_state.get("auth") or {}).get("role"),
          details={"created": created, "skipped": skipped, "invalid": invalid_ids})
    return created, skipped, created_ids, invalid_ids


def _patient_accounts_table_and_delete(ctrl: Controller) -> None:
    st.subheader(u("Patient accounts"))

    users = ctrl.list_users_by_role("patient") or []
    if not users:
        st.caption(u("No accounts yet."))
        return

    ids = [pid for pid in (_rec_username(r) for r in users) if pid]
    pmap = _collect_profile_map(ctrl, ids)

    rows = []
    for rec in users:
        pid = _rec_username(rec)
        if not pid:
            continue
        prof = pmap.get(pid)
        rows.append({
            u("ID"): pid,
            u("name"): _rec_name(rec) or pid,
            u("role"): (rec.get("role") if isinstance(rec, dict) else "patient") or "patient",
            u("Condition"): _get_attr(prof, "condition", "-") or "-",
            u("Assigned Staff ID"): _get_attr(prof, "assignedStaffID", "-") or "-",
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.markdown("---")
    st.subheader(u("Delete a patient account"))

    sel = st.selectbox(u("Pick a patient ID to delete"), options=ids, key="__del_patient_id__")
    also_remove_profile = st.checkbox(
        u("Also delete patient profile (from internal records)"),
        value=False,
        key="__del_patient_profile__",
    )

    if st.button(u("Delete"), key="__btn_del_patient__", use_container_width=True):
        ok = ctrl.delete_user(sel)  # delete LOGIN
        if ok and also_remove_profile:
            try:
                ctrl.delete_patient(sel)  # delete profile
            except Exception:
                pass

        if ok:
            audit("patient.delete",
                  who=(st.session_state.get("auth") or {}).get("username"),
                  role=(st.session_state.get("auth") or {}).get("role"),
                  details={"username": sel, "profile_deleted": also_remove_profile})
            st.success(u(f"Deleted patient login: {sel}"))
            st.rerun()
        else:
            audit("patient.delete_failed",
                  who=(st.session_state.get("auth") or {}).get("username"),
                  role=(st.session_state.get("auth") or {}).get("role"),
                  details={"username": sel})
            st.error(u("Failed to delete (user not found)."))


# -----------------------------
# Public entry
# -----------------------------
def render():
    st.title("🧑‍⚕️ " + u("Patient Management"))
    st.caption(u("Create patient logins and profiles. Admins/SiteAdmin/Staff can create & delete patients."))

    role_me = (st.session_state.get("auth") or {}).get("role")
    if role_me not in ("admin", "siteadmin", "staff"):
        audit("access.denied",
              who=(st.session_state.get("auth") or {}).get("username"),
              role=role_me,
              details={"page": "PatientManagement"})
        st.error(u("Access denied."))
        return

    ctrl = _get_ctrl()
    can_assign = role_me in ("admin", "siteadmin")  # only these can assign staff

    # --- Create Patient Login ---
    with st.container(border=True):
        st.subheader(u("Create Patient Login"))

        c1, c2 = st.columns([2, 2], vertical_alignment="bottom")
        with c1:
            patient_id_raw = st.text_input(u("Patient ID (login, e.g., P001)"), key="__new_patient_id__").strip()
            patient_id = patient_id_raw.upper()
            full_name = st.text_input(u("Full Name"), key="__new_patient_fullname__").strip()
            condition = st.text_input(u("Condition (optional)"), key="__new_patient_condition__").strip()
        with c2:
            tmp_pwd = st.text_input(u("Temporary Password"), type="password", key="__new_patient_pwd__")
            age = st.number_input(u("Age"), min_value=0, max_value=130, step=1, value=0, key="__new_patient_age__")
            if can_assign:
                assigned_staff = st.text_input(
                    u("Assigned Staff ID (optional, e.g., S001)"),
                    key="__new_patient_staff__"
                ).strip().upper()
            else:
                assigned_staff = ""

        if st.button(u("Create Patient Account"), key="__btn_create_patient__", type="primary", use_container_width=True):
            if not patient_id or not full_name or not tmp_pwd:
                st.error(u("Patient ID, Full Name and Temporary Password are required."))
            else:
                if can_assign and assigned_staff:
                    try:
                        Validator.validate_staff_id(assigned_staff)
                    except Exception as e:
                        st.error(u(str(e)))
                        st.stop()

                ok, msg = _create_patient_login(
                    ctrl,
                    patient_id,
                    full_name,
                    tmp_pwd,
                    age=int(age) if age else None,
                    condition=condition or None,
                    assigned_staff=(assigned_staff or None) if can_assign else None,
                    allow_assign=can_assign,
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.markdown("---")

    # --- Bulk migrate profiles without logins ---
    try:
        prof_ids = set()
        try:
            allp = ctrl.get_all_patients()
        except Exception:
            allp = None
        if allp:
            prof_ids = {(_get_attr(p, "patientID") or "") for p in allp}
        if not prof_ids:
            repo = getattr(ctrl, "patients", {})
            if isinstance(repo, dict):
                prof_ids = set(str(k) for k in repo.keys())
        prof_ids.discard("")
    except Exception:
        prof_ids = set()

    try:
        role_patients = ctrl.list_users_by_role("patient") or []
    except Exception:
        role_patients = []
    login_ids = {(_rec_username(u) or "") for u in role_patients}
    login_ids.discard("")
    unlinked = sorted(list(prof_ids - login_ids))

    if unlinked:
        st.warning(
            u("We found patient profiles without logins: ") + ", ".join(unlinked)
            + u(". These won’t appear in the Patient accounts table until a login is created.")
        )
        with st.expander(u("Create logins for unlinked patients")):
            default_pw = st.text_input(
                u("Temporary password to set for all new patient logins"),
                type="password",
                key="__pat_bulk_pw__",
                placeholder="e.g., ChangeMe123!",
            )
            if st.button(u("Create missing patient logins"), key="__btn_pat_bulk__", use_container_width=True):
                created, skipped, created_ids, invalid_ids = _migrate_unlinked_patients(ctrl, default_pw)
                if created:
                    st.success(u(f"Created {created} login(s): ") + ", ".join(created_ids))
                if skipped:
                    st.info(u(f"Skipped {skipped} (already had a login)."))
                if invalid_ids:
                    st.warning(u("Invalid patient IDs (must be P###): ") + ", ".join(invalid_ids))
                st.rerun()

    # --- Optional: reset patient password (for legacy accounts) ---
    with st.expander(u("Reset Patient Password (legacy fix)")):
        col_r1, col_r2, col_r3 = st.columns([1.2, 1.2, 0.8])
        with col_r1:
            fix_pid = st.text_input(u("Patient ID (e.g., P001)"), key="__fix_pid__").strip().upper()
        with col_r2:
            new_pw = st.text_input(u("New password"), type="password", key="__fix_ppw__")
        with col_r3:
            if st.button(u("Reset Password"), key="__btn_fix_ppwd__", use_container_width=True):
                if not fix_pid or not new_pw:
                    st.error(u("Patient ID and new password are required."))
                else:
                    try:
                        Validator.validate_patient_id(fix_pid)
                        rec = ctrl.get_user(fix_pid)
                        if not rec or (rec.get("role") or "").lower() != "patient":
                            st.error(u("Patient user not found."))
                        else:
                            new_hash = ctrl.db.hash_pwd(fix_pid, new_pw)
                            ctrl.db.users[fix_pid]["hash"] = new_hash
                            ctrl.db.save_all()
                            audit("patient.password_reset",
                                  who=(st.session_state.get("auth") or {}).get("username"),
                                  role=(st.session_state.get("auth") or {}).get("role"),
                                  details={"username": fix_pid})
                            st.success(u(f"Password reset for {fix_pid}."))
                    except Exception as e:
                        st.error(u(f"Failed: {e}"))

    # --- Accounts table + delete ---
    _patient_accounts_table_and_delete(ctrl)
