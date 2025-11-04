# gui/main_dashboard.py
from __future__ import annotations
import os
from datetime import datetime, timezone

import streamlit as st

# Pages
from gui.views import admin_Dashboard as admin_page
from gui.views import staff_Dashboard as staff_page
from gui.views import patient_Preference as patient_page  
from gui.views import staff_Management as staff_mgmt_page
from gui.views import patient_Management as patient_mgmt_page
from gui.views import siteadmin_Dashboard as siteadmin_page
from gui.views import language_Settings as lang_settings_page
from gui.views import welcome_page

# Auth / UI / TOTP
from app.core.auth_Manager import AuthService
from gui.ui import (
    u,
    get_ui_lang,
    set_ui_lang,
    language_names,
    code_to_name,
    name_to_code,
)
from app.core.translate import warmup
from app.core.totp import totp  # validation
from app.core.otp_console import start_console_totp  # single-line console printer

# Use Controller as the portal to backend
from app.database.controller import Controller

APP_TITLE = "Hospital Control Panel"
TOTP_PERIOD = 20
TOTP_SECRET_ENV = "SITEADMIN_SECRET"


# ---------- Helpers ----------

def _start_totp_console_once():
    """Start the single-line console OTP printer only once per process."""
    if not st.session_state.get("__otp_console_started__", False):
        start_console_totp(os.getenv(TOTP_SECRET_ENV, "SITEADMIN_DEMO_SECRET"), period=TOTP_PERIOD)
        st.session_state["__otp_console_started__"] = True


def _validate_siteadmin_otp(code: str) -> bool:
    secret = os.getenv(TOTP_SECRET_ENV, "SITEADMIN_DEMO_SECRET")
    cur_code, _left = totp(secret, period=TOTP_PERIOD)
    return (code or "").strip() == cur_code


def _ensure_session_defaults():
    ss = st.session_state
    ss.setdefault("ui_lang", "en")
    ss.setdefault("auth", {"is_authed": False, "username": None, "name": None, "role": None})
    # One nav key for everything. Accepted values:
    #   Welcome, AdminMgmt, StaffMgmt, PatientMgmt, AdminDash, StaffDash, PatientDash, LangSettings
    ss.setdefault("__nav__", "Welcome")
    ss.setdefault("__xlate_warmed__", False)
    ss.setdefault("__pending_siteadmin_user__", None)
    ss.setdefault("lock_until_ts", None)
    ss.setdefault("awaiting_otp", False)  # OTP flow flag


# ---------- Username resolution (ID or Name) ----------

def _resolve_username_from_id_or_name(raw: str, ctrl: Controller) -> tuple[bool, str]:
    """
    Accepts either:
      - ID/username: A001, S001, P001, siteadmin, etc.  (exact match)
      - Name: 'Admin', 'Alice Tan', etc.                 (case-insensitive)
    Returns (ok, username_or_error_message).
    """
    term = (raw or "").strip()
    if not term:
        return False, u("Enter your ID or Name.")

    # 1) Try direct username/ID match
    try:
        user = ctrl.get_user(term)
        if user is not None:
            return True, term
    except Exception:
        pass

    # 2) Try by name across roles (case-insensitive)
    matches: list[str] = []
    # siteadmin isn't always in list_users_by_role; fetch explicitly
    try:
        su = ctrl.get_user("siteadmin")
        if su:
            nm = (su.get("name") or "").strip()
            if nm and nm.lower() == term.lower():
                uname = su.get("username") or su.get("userID") or "siteadmin"
                matches.append(uname)
    except Exception:
        pass

    for role in ["admin", "staff", "patient"]:
        try:
            recs = ctrl.list_users_by_role(role) or []
            for r in recs:
                nm = (r.get("name") or "").strip()
                if nm and nm.lower() == term.lower():
                    uname = r.get("username") or r.get("userID")
                    if uname:
                        matches.append(uname)
        except Exception:
            continue

    if len(matches) == 1:
        return True, matches[0]
    if len(matches) > 1:
        return False, u("Multiple accounts share that name. Please use your ID (e.g., A001/S001/P001).")

    return False, u("No account found for that ID or Name.")


# ---------- App shell ----------

def launch():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _ensure_session_defaults()

    if not st.session_state["__xlate_warmed__"]:
        warmup()
        st.session_state["__xlate_warmed__"] = True

    auth = AuthService(st.session_state)

    _sidebar(auth)

    if not st.session_state.auth.get("is_authed"):
        _login_form(auth)
        return

    _route()


def _sidebar(auth: AuthService):
    sb = st.sidebar
    a = st.session_state.auth

    # Logo / Title
    sb.title("🩺 " + APP_TITLE)

    if a.get("is_authed"):
        # Home button
        if sb.button(u("Home"), key="__nav_home__", width="stretch"):
            st.session_state["__nav__"] = "Welcome"
            st.rerun()

        role = (a.get("role") or "").lower()

        # --------------------------
        # Sections (role-gated)
        # --------------------------
        def btn(label, nav_key):
            if sb.button(u(label), key=f"__nav_{nav_key}__", width="stretch"):
                st.session_state["__nav__"] = nav_key
                st.rerun()

        if role in ("siteadmin", "admin", "staff", "patient"):
            sb.subheader(u("Sections"))

        if role == "siteadmin":
            btn("Admin Management", "AdminMgmt")
            btn("Staff Management", "StaffMgmt")
            btn("Patient Management", "PatientMgmt")

        elif role == "admin":
            btn("Staff Management", "StaffMgmt")
            btn("Patient Management", "PatientMgmt")

        elif role == "staff":
            btn("Patient Management", "PatientMgmt")

        elif role == "patient":
            pass

        # --------------------------
        # Dashboards (role-gated)
        # --------------------------
        if role in ("siteadmin", "admin", "staff", "patient"):
            sb.subheader(u("Dashboards"))

        if role == "siteadmin":
            btn("Admin Dashboard", "AdminDash")
            btn("Staff Dashboard", "StaffDash")
            btn("Patient Dashboard", "PatientDash")

        elif role == "admin":
            btn("Admin Dashboard", "AdminDash")
            btn("Staff Dashboard", "StaffDash")
            btn("Patient Dashboard", "PatientDash")

        elif role == "staff":
            btn("Staff Dashboard", "StaffDash")
            btn("Patient Dashboard", "PatientDash")

        elif role == "patient":
            btn("Patient Dashboard", "PatientDash")

    # spacer to push language to bottom
    sb.markdown("<div style='flex:1 1 auto;height:52vh'></div>", unsafe_allow_html=True)

    # If language was just changed elsewhere, seed the selectbox BEFORE creating it
    if "__pending_lang_sync__" in st.session_state:
        new_code = st.session_state["__pending_lang_sync__"]
        set_ui_lang(st.session_state, new_code)
        st.session_state["__sb_lang__"] = code_to_name(new_code)
        del st.session_state["__pending_lang_sync__"]

    # Language selector
    current_code = get_ui_lang(st.session_state)
    current_name = code_to_name(current_code)
    opts = language_names()
    choice = sb.selectbox(
        u("Language"),
        opts,
        index=opts.index(current_name) if current_name in opts else 0,
        key="__sb_lang__",
    )
    if choice != current_name:
        set_ui_lang(st.session_state, name_to_code(choice))
        st.rerun()

    # Open Language Settings page
    if sb.button(u("Language Settings…"), key="__lang_settings_btn__", width="stretch"):
        st.session_state["__nav__"] = "LangSettings"
        st.rerun()

    # Signed in & logout
    if st.session_state.auth.get("is_authed"):
        sb.caption(u(f"Signed in as: {a.get('name')} ({a.get('role')})"))
        if sb.button(u("Log out"), key="__btn_logout__", width="stretch"):
            auth.logout()
            st.session_state["__pending_siteadmin_user__"] = None
            st.session_state["awaiting_otp"] = False
            st.rerun()


def _login_form(auth: AuthService):
    st.title("🩺 " + u("Hospital Control Panel"))
    st.subheader(u("Sign in"))

    with st.form("login_step1", clear_on_submit=False):
        u_input = st.text_input(u("ID or Name (e.g., A001 / James)"))
        p = st.text_input(u("Password"), type="password")
        submitted = st.form_submit_button(u("Log in"))

    if submitted:
        # Resolve to a username using Controller
        try:
            ctrl = Controller()
        except Exception as e:
            st.error(u(f"Login unavailable: {e}"))
            return

        ok_resolve, username_or_err = _resolve_username_from_id_or_name(u_input, ctrl)
        if not ok_resolve:
            st.error(username_or_err)
            return

        username = username_or_err  # resolved username (ID)
        ok, msg, need_otp = auth.login_step1_password((username or "").strip(), p)
        if not ok:
            st.error(u(msg or "Invalid credentials."))
            return

        if need_otp:
            # >>> show OTP input immediately and print rotating code to console
            st.session_state["awaiting_otp"] = True
            _start_totp_console_once()
            st.info(u("Password accepted. Enter the 6-digit auth code shown in your console."))
        else:
            # ---- APPLY ACCOUNT PREFERRED LANGUAGE (immediate) ----
            try:
                uname = st.session_state.auth.get("username")
                pref = (ctrl.get_user_default_lang(uname) or "").strip()
                if pref:
                    set_ui_lang(st.session_state, pref)
                    st.session_state["__pending_lang_sync__"] = pref
            except Exception:
                pass
            # Land on Welcome
            st.session_state["__nav__"] = "Welcome"
            st.success(u(f"Welcome, {st.session_state.auth.get('name')}"))
            st.rerun()

    # If awaiting OTP, show step 2
    if st.session_state.get("awaiting_otp"):
        with st.form("__siteadmin_otp__", clear_on_submit=False):
            otp_code = st.text_input(u("Auth code (6 digits)"), max_chars=6)
            go = st.form_submit_button(u("Verify & continue"))
        if go:
            ok, msg = auth.login_step2_verify_otp(otp_code)
            if ok:
                st.session_state["awaiting_otp"] = False
                # ---- APPLY ACCOUNT PREFERRED LANGUAGE (after OTP) ----
                try:
                    ctrl = Controller()
                    uname = st.session_state.auth.get("username")
                    pref = (ctrl.get_user_default_lang(uname) or "").strip()
                    if pref:
                        set_ui_lang(st.session_state, pref)
                        st.session_state["__pending_lang_sync__"] = pref
                except Exception:
                    pass
                # Land on Welcome
                st.session_state["__nav__"] = "Welcome"
                st.success(u("Verification successful. Welcome SiteAdmin."))
                st.rerun()
            else:
                st.error(u(msg or "Invalid or expired auth code."))


def _render_siteadmin_otp_step(auth: AuthService, pending_username: str):
    """(kept for reference; not used in current flow)"""
    st.info(u("Additional verification required (SiteAdmin). Enter 6-digit auth code."))
    _start_totp_console_once()

    with st.form("__siteadmin_otp__", clear_on_submit=False):
        otp_code = st.text_input(u("Auth code (6 digits)"), max_chars=6)
        go = st.form_submit_button(u("Verify & continue"))
    if go:
        if _validate_siteadmin_otp(otp_code):
            st.success(u("Verification successful."))
            st.rerun()
        else:
            st.error(u("Invalid or expired auth code. Try again."))


def _route():
    role = st.session_state.auth.get("role")
    nav = st.session_state.get("__nav__", "Welcome")

    # Welcome route for all roles
    if nav == "Welcome":
        welcome_page.render()
        return

    # SiteAdmin: can go anywhere; "AdminMgmt" is the Create Admin page
    if role == "siteadmin":
        if nav == "AdminMgmt":
            siteadmin_page.render()                # Create Admin
        elif nav == "StaffMgmt":
            staff_mgmt_page.render()               # Create/Delete Staff
        elif nav == "PatientMgmt":
            patient_mgmt_page.render()             # Create/Delete Patient
        elif nav == "AdminDash":
            admin_page.render()
        elif nav == "StaffDash":
            staff_page.render()
        elif nav == "PatientDash":
            patient_page.render()
        elif nav == "LangSettings":
            lang_settings_page.render()
        else:
            siteadmin_page.render()
        return

    # Admin: manage staff/patient + dashboards
    if role == "admin":
        if nav == "StaffMgmt":
            staff_mgmt_page.render()
        elif nav == "PatientMgmt":
            patient_mgmt_page.render()
        elif nav == "AdminDash":
            admin_page.render()
        elif nav == "StaffDash":
            staff_page.render()
        elif nav == "PatientDash":
            patient_page.render()
        elif nav == "LangSettings":
            lang_settings_page.render()
        else:
            admin_page.render()  # default for admin
        return

    # Staff ✅ route by selected nav (fixes your issue)
    if role == "staff":
        if nav == "PatientMgmt":
            patient_mgmt_page.render()
        elif nav == "StaffDash":
            staff_page.render()
        elif nav == "PatientDash":
            patient_page.render()
        elif nav == "LangSettings":
            lang_settings_page.render()
        else:
            staff_page.render()  # default for staff
        return

    # Patient
    if role == "patient":
        if nav == "LangSettings":
            lang_settings_page.render()
        else:
            patient_page.render()
        return

    st.warning(u("Unknown role. Contact administrator."))


if __name__ == "__main__":
    launch()
