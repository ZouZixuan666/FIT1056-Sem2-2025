# gui/views/siteadmin_Dashboard.py
"""
SiteAdmin page now ONLY handles 'Create Admin' (no tabs). Navigation
between sections happens from the sidebar.
Routes: UI -> Controller -> Database (no direct auth/db calls).
"""
from __future__ import annotations
import streamlit as st
import pandas as pd

from gui.ui import u
from app.database.controller import Controller


# single Controller for the session
def _get_ctrl() -> Controller:
    if "__CTRL__" not in st.session_state:
        st.session_state["__CTRL__"] = Controller()
    return st.session_state["__CTRL__"]


def _looks_like_admin_id(uname: str) -> bool:
    # A followed by exactly 3 digits
    return len(uname) == 4 and uname.startswith("A") and uname[1:].isdigit()


def render():
    ctrl = _get_ctrl()

    st.title("🛡️ " + u("SiteAdmin Dashboard"))
    st.caption(u("Create and manage **admin** accounts."))

    # -----------------------------
    # Create Admin
    # -----------------------------
    with st.container(border=True):
        st.subheader(u("Create Admin"))
        with st.form("__create_admin__"):
            raw_uname = st.text_input(u("Admin ID (A###, e.g., A001)")).strip()
            uname = raw_uname.upper()  # normalize to match IDs
            name = st.text_input(u("Full name")).strip()
            pwd = st.text_input(u("Password"), type="password")
            submitted = st.form_submit_button(
                u("Create Admin"),
                key="__btn_create_admin__",
                type="primary",
                width="content",
            )
            if submitted:
                try:
                    if not uname or not pwd or not name:
                        raise ValueError(u("All fields are required."))
                    if uname.lower() == "siteadmin":
                        raise ValueError(u("Cannot overwrite the SiteAdmin account."))
                    if not _looks_like_admin_id(uname):
                        raise ValueError(u("Admin ID must match A### (e.g., A001)."))

                    # existence via Controller
                    if ctrl.get_user(uname) is not None:
                        raise ValueError(u("ID already exists."))

                    ctrl.create_user(uname, pwd, "admin", name)
                    st.success(u(f"Admin created: {uname}"))
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except Exception:
                    st.error(u("Could not create admin. Please try again."))

    # -----------------------------
    # List Admins (table view)
    # -----------------------------
    st.divider()
    st.subheader(u("Admin accounts"))

    admins = ctrl.list_users_by_role("admin")
    if not admins:
        st.caption(u("No accounts yet."))
    else:
        admins_sorted = sorted(admins, key=lambda r: r.get("username", ""))
        df = pd.DataFrame(
            [{"ID": u["username"], "name": u.get("name", ""), "role": u.get("role", "")} for u in admins_sorted]
        )
        st.dataframe(df, use_container_width=True, height=220)

    # -----------------------------
    # Delete Admin
    # -----------------------------
    st.subheader(u("Delete an account"))
    admin_ids = [u["username"] for u in (admins or []) if u.get("username", "").lower() != "siteadmin"]

    if admin_ids:
        pick = st.selectbox(u("Pick an admin ID to delete"), admin_ids, key="__del_admin__")
        if st.button(u("Delete"), key="__del_btn__", use_container_width=False):
            try:
                ok = ctrl.delete_user(pick)
                if ok:
                    st.success(u(f"Deleted: {pick}"))
                    st.rerun()
                else:
                    st.error(u("Could not delete."))
            except Exception:
                st.error(u("Delete failed. Please try again."))
    else:
        st.caption(u("No admin to delete."))