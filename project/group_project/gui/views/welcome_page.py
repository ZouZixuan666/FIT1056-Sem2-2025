# gui/views/welcome_page.py
from __future__ import annotations

from datetime import datetime
import streamlit as st

from gui.ui import u
from app.database.controller import Controller


def _greeting(name: str | None) -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        t = u("Good morning")
    elif 12 <= hour < 18:
        t = u("Good afternoon")
    else:
        t = u("Good evening")
    name = name or u("there")
    return f"{t}, {name} 👋"


def _go(nav_key: str) -> None:
    st.session_state["__nav__"] = nav_key
    st.rerun()


def _card(title: str, desc: str, button_label: str, nav_key: str):
    with st.container(border=True):
        st.markdown(f"### {u(title)}")
        st.caption(u(desc))
        st.button(
            u(button_label),
            key=f"__wlcm_{nav_key}__",
            on_click=_go,
            args=(nav_key,),
            use_container_width=True
        )


def render():
    auth = st.session_state.get("auth", {}) or {}
    role = (auth.get("role") or "").lower()
    name = auth.get("name") or auth.get("username")

    st.title("🏠 " + u("Welcome"))
    st.success(_greeting(name))
    st.caption(u("Use the shortcuts below. You can also navigate from the sidebar anytime."))

    # Optional: light stats (best-effort, never crash)
    try:
        ctrl = Controller()
    except Exception:
        ctrl = None

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        try:
            if role in {"admin", "siteadmin"} and ctrl:
                total_admins = len(ctrl.list_users_by_role("admin") or [])
                total_staff = len(ctrl.list_users_by_role("staff") or [])
                total_patients = len(ctrl.list_users_by_role("patient") or [])
                c1.metric(u("Admins"), total_admins)
                c2.metric(u("Staff"), total_staff)
                c3.metric(u("Patients"), total_patients)

            elif role == "staff" and ctrl:
                sid = auth.get("staff_id") or auth.get("username")

                # ---- Primary source: assignment store (assignments.json)
                my_patients = []
                try:
                    if hasattr(ctrl, "get_patients_for_staff"):
                        my_patients = sorted(list(ctrl.get_patients_for_staff(sid) or []))
                except Exception:
                    my_patients = []

                # ---- Fallback: scan patient profiles (patients.json) by assignedStaffID
                if not my_patients:
                    try:
                        profs = ctrl.get_all_patients() or []
                        my_patients = sorted([
                            getattr(p, "patientID", None)
                            for p in profs
                            if (getattr(p, "assignedStaffID", None) or "").upper() == (sid or "").upper()
                        ])
                        my_patients = [p for p in my_patients if p]
                    except Exception:
                        pass

                c1.metric(u("My Patients"), len(my_patients))

                # Logs in scope (sum per my patient)
                recent = 0
                try:
                    for p in my_patients:
                        recent += len(ctrl.get_patient_logs(p) or [])
                except Exception:
                    pass
                c2.metric(u("Logs (scope)"), recent)

                # Unread alerts
                unread = 0
                try:
                    unread = len([a for a in (ctrl.get_staff_alerts(sid) or []) if not getattr(a, "isRead", True)])
                except Exception:
                    pass
                c3.metric(u("Unread Alerts"), unread)

            elif role == "patient" and ctrl:
                pid = auth.get("patientID") or auth.get("username")
                has_prefs = False
                try:
                    has_prefs = bool(ctrl.get_preferences(pid))
                except Exception:
                    pass
                c1.metric(u("Preferences saved"), u("Yes") if has_prefs else u("No"))
        except Exception:
            pass

    st.divider()

    # Role-specific shortcuts (only allowed pages)
    if role == "siteadmin":
        st.subheader(u("Quick actions"))
        c1, c2, c3 = st.columns(3)
        with c1: _card("Admin Management", "Create/delete admins (SiteAdmin page).", "Open", "AdminMgmt")
        with c2: _card("Staff Management", "Create/delete staff accounts.", "Open", "StaffMgmt")
        with c3: _card("Patient Management", "Create/delete patient accounts.", "Open", "PatientMgmt")

        d1, d2, d3, d4 = st.columns(4)
        with d1: _card("Admin Dashboard", "Assignments & audit.", "Go", "AdminDash")
        with d2: _card("Staff Dashboard", "Logs, search, alerts, reports.", "Go", "StaffDash")
        with d3: _card("Patient Dashboard", "Patient portal & preferences.", "Go", "PatientDash")
        with d4: _card("Language Settings", "Set your default UI language.", "Open", "LangSettings")

    elif role == "admin":
        st.subheader(u("Quick actions"))
        c1, c2 = st.columns(2)
        with c1: _card("Staff Management", "Create/delete staff accounts.", "Open", "StaffMgmt")
        with c2: _card("Patient Management", "Create/delete patient accounts.", "Open", "PatientMgmt")

        d1, d2, d3, d4 = st.columns(4)
        with d1: _card("Admin Dashboard", "Assignments & audit.", "Go", "AdminDash")
        with d2: _card("Staff Dashboard", "Logs, search, alerts, reports.", "Go", "StaffDash")
        with d3: _card("Patient Dashboard", "Patient portal & preferences.", "Go", "PatientDash")
        with d4: _card("Language Settings", "Set your default UI language.", "Open", "LangSettings")

    elif role == "staff":
        st.subheader(u("Quick actions"))
        c1, c2, c3 = st.columns(3)
        with c1: _card("Staff Dashboard", "Create/manage logs, search, alerts, reports.", "Go", "StaffDash")
        with c2: _card("Patient Dashboard", "View patient preferences (read-only).", "Go", "PatientDash")
        with c3: _card("Language Settings", "Set your default UI language.", "Open", "LangSettings")

    elif role == "patient":
        st.subheader(u("Quick actions"))
        c1, c2 = st.columns(2)
        with c1: _card("Patient Dashboard", "Edit your preferences & translate notes.", "Go", "PatientDash")
        with c2: _card("Language Settings", "Set your default UI language.", "Open", "LangSettings")

    else:
        st.warning(u("Unknown role. Contact administrator."))
