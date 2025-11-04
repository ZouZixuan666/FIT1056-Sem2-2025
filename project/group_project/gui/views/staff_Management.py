# gui/views/staff_Management.py
from __future__ import annotations

import streamlit as st
import pandas as pd

from gui.ui import u
from app.core.validator import Validator  # strict S### validation
from app.database.controller import Controller
from app.users.staff import Staff 

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
# Helpers
# -----------------------------
def _ensure_staff_profile(ctrl: Controller, staff_id: str, full_name: str) -> None:
    """Ensure a staff profile exists (sync name if changed)."""
    try:
        existing = ctrl.get_staff(staff_id)
        if existing and full_name and getattr(existing, "name", None) != full_name:
            existing.name = full_name
            ctrl.db.save_all()
        elif not existing:
            # ✅ create via Staff model (mirrors Patient page pattern)
            s = Staff(
                userID=staff_id,
                staffID=staff_id,
                name=full_name or staff_id,
                role="care",
                assignedPatients=[],
            )
            payload = s.to_dict() if hasattr(s, "to_dict") else {
                "staffID": s.staffID,
                "name": s.name,
                "role": s.role,
                "assignedPatients": s.assignedPatients,
            }
            ctrl.register_staff(payload)
    except Exception:
        pass


def _create_staff_login(ctrl: Controller, staff_id: str, full_name: str, temp_password: str) -> tuple[bool, str]:
    staff_id = (staff_id or "").upper().strip()
    try:
        Validator.validate_staff_id(staff_id)
    except Exception as e:
        return False, u(str(e))

    if ctrl.get_user(staff_id):
        return False, u("A user with this ID already exists.")

    try:
        # IMPORTANT: pass PLAINTEXT (do NOT pre-hash here)
        ctrl.create_user(staff_id, temp_password, "staff", full_name or staff_id)
        audit("staff.create",
              who=(st.session_state.get("auth") or {}).get("username"),
              role=(st.session_state.get("auth") or {}).get("role"),
              details={"username": staff_id})
        return True, u("Staff login created.")
    except Exception as e:
        audit("staff.create_failed",
              who=(st.session_state.get("auth") or {}).get("username"),
              role=(st.session_state.get("auth") or {}).get("role"),
              details={"username": staff_id, "error": str(e)})
        return False, u(f"Failed to create login: {e}")


def _migrate_unlinked_staff(ctrl: Controller, default_temp_pw: str) -> tuple[int, int, list[str], list[str]]:
    """Create logins for staff that exist only as profiles."""
    created, skipped = 0, 0
    created_ids: list[str] = []
    invalid_ids: list[str] = []

    for staff_id in (ctrl.staffs or {}).keys():
        sid = (staff_id or "").upper().strip()
        try:
            Validator.validate_staff_id(sid)
        except Exception:
            invalid_ids.append(staff_id)
            continue

        if ctrl.get_user(sid):
            skipped += 1
            continue

        staff_obj = ctrl.get_staff(sid)
        name = getattr(staff_obj, "name", None) if staff_obj else sid
        try:
            # IMPORTANT: pass PLAINTEXT; DB hashes internally.
            ctrl.create_user(sid, default_temp_pw, "staff", name or sid)
            created += 1
            created_ids.append(sid)
        except Exception:
            skipped += 1

    audit("staff.bulk_create",
          who=(st.session_state.get("auth") or {}).get("username"),
          role=(st.session_state.get("auth") or {}).get("role"),
          details={"created": created, "skipped": skipped, "invalid": invalid_ids})
    return created, skipped, created_ids, invalid_ids


def _delete_staff_profile(ctrl: Controller, staff_id: str) -> None:
    """Optional: remove internal staff profile record."""
    try:
        ctrl.db.staffs.pop(staff_id, None)
        ctrl.db.save_all()
    except Exception:
        pass


def _staff_accounts_table_and_delete(ctrl: Controller) -> None:
    """Render staff table with delete option."""
    st.subheader(u("Staff accounts"))

    users = ctrl.list_users_by_role("staff")
    if not users:
        st.caption(u("No accounts yet."))
        return

    rows = [
        {
            u("ID"): rec.get("username") or rec.get("userID"),
            u("name"): rec.get("name") or rec.get("username"),
            u("role"): rec.get("role") or "staff",
        }
        for rec in users
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.markdown("---")
    st.subheader(u("Delete a staff account"))

    ids = [r.get("username") or r.get("userID") for r in users]
    sel = st.selectbox(u("Pick a staff ID to delete"), options=ids, key="__del_staff_id__")

    also_remove_profile = st.checkbox(
        u("Also delete staff profile"),
        value=False,
        key="__del_staff_profile__",
        help=u("If checked, removes the profile record as well."),
    )

    col_del, _ = st.columns([1, 3])
    with col_del:
        if st.button(u("Delete"), key="__btn_del_staff__", use_container_width=True):
            # Clean up assignments BEFORE deleting the user
            actor = (st.session_state.get("auth") or {}).get("username") or "admin"
            try:
                ctrl.cleanup_staff_on_delete(sel, actor=actor)
            except Exception:
                pass

            ok = ctrl.delete_user(sel)

            if ok and also_remove_profile:
                _delete_staff_profile(ctrl, sel)

            if ok:
                audit("staff.delete",
                      who=(st.session_state.get("auth") or {}).get("username"),
                      role=(st.session_state.get("auth") or {}).get("role"),
                      details={"username": sel, "profile_deleted": also_remove_profile})
                st.success(u(f"Deleted staff login: {sel}"))
                st.rerun()
            else:
                audit("staff.delete_failed",
                      who=(st.session_state.get("auth") or {}).get("username"),
                      role=(st.session_state.get("auth") or {}).get("role"),
                      details={"username": sel})
                st.error(u("Failed to delete (user not found)."))


# -----------------------------
# Public entry
# -----------------------------
def render():
    st.title("👥 " + u("Staff Management"))
    st.caption(u("Admins can create/delete staff. (SiteAdmin can also create admins from the SiteAdmin page.)"))

    role_me = (st.session_state.get("auth") or {}).get("role")
    if role_me not in ("admin", "siteadmin"):
        audit("access.denied", who=(st.session_state.get("auth") or {}).get("username"),
              role=role_me, details={"page": "StaffManagement"})
        st.error(u("Access denied."))
        return

    ctrl = _get_ctrl()

    # Create Staff Login
    with st.container(border=True):
        st.subheader(u("Create Staff Login"))

        c1, c2 = st.columns([2, 2], vertical_alignment="bottom")
        with c1:
            staff_id_raw = st.text_input(u("Staff ID (login, e.g., S001)"), key="__new_staff_id__").strip()
            staff_id = staff_id_raw.upper()
            full_name = st.text_input(u("Full Name"), key="__new_staff_fullname__").strip()
        with c2:
            tmp_pwd = st.text_input(u("Temporary Password"), type="password", key="__new_staff_pwd__")

        if st.button(u("Create Staff Account"), key="__btn_create_staff__", type="primary", width="content"):
            if not staff_id or not full_name or not tmp_pwd:
                st.error(u("All fields are required."))
            else:
                ok, msg = _create_staff_login(ctrl, staff_id, full_name, tmp_pwd)
                if ok:
                    _ensure_staff_profile(ctrl, staff_id, full_name)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.markdown("---")

    # Reset Staff Password (legacy fix)
    with st.container(border=True):
        st.subheader(u("Reset Staff Password (fix legacy accounts)"))
        st.caption(u("Use this if a staff account was created with a broken (double-hashed) password."))

        col_r1, col_r2, col_r3 = st.columns([1.2, 1.2, 0.8])
        with col_r1:
            fix_sid = st.text_input(u("Staff ID (e.g., S001)"), key="__fix_sid__").strip().upper()
        with col_r2:
            new_pw = st.text_input(u("New password"), type="password", key="__fix_pw__")
        with col_r3:
            if st.button(u("Reset Password"), key="__btn_fix_pwd__", use_container_width=True):
                if not fix_sid or not new_pw:
                    st.error(u("Staff ID and new password are required."))
                else:
                    try:
                        Validator.validate_staff_id(fix_sid)
                        rec = ctrl.get_user(fix_sid)
                        if not rec or (rec.get("role") or "").lower() != "staff":
                            st.error(u("Staff user not found."))
                        else:
                            new_hash = ctrl.db.hash_pwd(fix_sid, new_pw)
                            ctrl.db.users[fix_sid]["hash"] = new_hash
                            ctrl.db.save_all()
                            audit("staff.password_reset",
                                  who=(st.session_state.get("auth") or {}).get("username"),
                                  role=(st.session_state.get("auth") or {}).get("role"),
                                  details={"username": fix_sid})
                            st.success(u(f"Password reset for {fix_sid}."))
                    except Exception as e:
                        st.error(u(f"Failed: {e}"))

    # Warn about unlinked profiles & bulk-migrate
    profiles = set((ctrl.staffs or {}).keys())
    logins = set([(u.get("username") or u.get("userID")) for u in ctrl.list_users_by_role("staff")])
    unlinked = sorted(list(profiles - logins))

    if unlinked:
        st.warning(
            u("We found staff profiles without logins: ") + ", ".join(unlinked) + ". "
            + u("These won’t appear in the Staff accounts table until a login is created.")
        )
        with st.expander(u("Create logins for unlinked staff")):
            default_pw = st.text_input(
                u("Temporary password to set for all new logins"),
                type="password",
                key="__bulk_pw__",
                placeholder="e.g., ChangeMe123!",
            )
            if st.button(u("Create missing staff logins"), key="__btn_bulk_create__", use_container_width=True):
                try:
                    created, skipped, created_ids, invalid_ids = _migrate_unlinked_staff(ctrl, default_pw)
                    if created:
                        st.success(u(f"Created {created} login(s): ") + ", ".join(created_ids))
                    if skipped:
                        st.info(u(f"Skipped {skipped} (already had a login)."))
                    if invalid_ids:
                        st.warning(u("Invalid staff IDs (must be S###): ") + ", ".join(invalid_ids))
                    st.rerun()
                except Exception as e:
                    audit("staff.bulk_create_failed",
                          who=(st.session_state.get("auth") or {}).get("username"),
                          role=(st.session_state.get("auth") or {}).get("role"),
                          details={"error": str(e)})
                    st.error(u(f"Bulk creation failed: {e}"))

    # Table + delete
    _staff_accounts_table_and_delete(ctrl)
