# gui/views/admin_Dashboard.py
from __future__ import annotations

import pandas as pd
import streamlit as st
from datetime import datetime

from gui.ui import u
from app.database.controller import Controller


# ---------------------------------------------------
# Controller portal (single point of backend access)
# ---------------------------------------------------
controller = Controller()


# ---------------------------------------------------
# UI: Assignments Section
# ---------------------------------------------------
def _render_assignments():
    st.subheader(u("Assignments"))
    st.caption(u("Assign staff to patients. This links their access across views."))

    pid = st.text_input(u("Patient ID (e.g., P001)"), key="__adm_pid__", placeholder="P001")
    sid = st.text_input(u("Staff ID (e.g., S001)"), key="__adm_sid__", placeholder="S001")

    c1, c2 = st.columns([1, 1])
    with c1:
        # NOTE: width='stretch' replaces deprecated use_container_width=True
        if st.button(u("Assign"), key="__btn_assign__", width="stretch"):
            username = (st.session_state.get("auth") or {}).get("username") or "admin"
            ok, msg = controller.assign_staff_to_patient(pid, sid, username)
            (st.success if ok else st.error)(u(msg))
            st.rerun()

    with c2:
        # NOTE: width='stretch' replaces deprecated use_container_width=True
        if st.button(u("Unassign"), key="__btn_unassign__", width="stretch"):
            ok, msg = controller.unassign_staff_from_patient(pid, sid)
            (st.success if ok else st.error)(u(msg))
            st.rerun()

    st.markdown("---")
    st.caption(u("Current assignments"))

    rows = controller.list_assignments()  # shim in Controller
    if not rows:
        st.caption(u("No assignments yet."))
    else:
        # Keep the same visible columns for consistency
        df = pd.DataFrame(rows, columns=["patientID", "staffID", "assignedBy", "ts"])
        # NOTE: width='stretch' replaces deprecated use_container_width=True
        st.dataframe(df, width="stretch", height=240)


# ---------------------------------------------------
# UI: Audit Log Section
# ---------------------------------------------------
def _render_audit_log():
    st.subheader(u("Audit Log"))
    st.caption(u("System-level audit of user actions, security events, and database changes."))

    rows = controller.get_audit_log()  # shim in Controller

    if not rows:
        st.caption(u("No audit entries yet."))
        return

    # Sort by timestamp descending if present
    try:
        rows.sort(key=lambda r: str(r.get("ts", "")), reverse=True)
    except Exception:
        pass

    df = pd.DataFrame(rows, columns=["ts", "who", "role", "event", "details"])
    # NOTE: width='stretch' replaces deprecated use_container_width=True
    st.dataframe(df, width="stretch", height=340)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            label=u("📥 Download CSV"),
            data=controller.export_audit_log_csv(),   # shim in Controller
            file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            width="stretch",
        )
    with c2:
        st.download_button(
            label=u("📥 Download JSONL"),
            data=controller.export_audit_log_jsonl(),  # shim in Controller
            file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
            mime="application/json",
            width="stretch",
        )


# ---------------------------------------------------
# Public Entry Point
# ---------------------------------------------------
def render():
    st.title("🛡️ " + u("Admin Dashboard"))
    st.caption(u("FR: Account Management, Role Assignments, Audit, and Reporting"))

    _render_assignments()
    st.markdown("---")
    _render_audit_log()