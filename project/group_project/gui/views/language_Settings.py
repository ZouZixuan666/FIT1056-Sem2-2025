# gui/views/language_Settings.py
import streamlit as st
from gui.ui import (
    u,
    language_names,
    code_to_name,
    name_to_code,
    get_ui_lang,
    set_ui_lang,
)
from app.database.controller import Controller

# Instantiate controller
controller = Controller()


def render():
    if not st.session_state.auth.get("is_authed"):
        st.warning(u("You must be signed in to change language settings."))
        return

    st.markdown("### 🌐 " + u("Language Settings"))
    st.caption(u("This sets your default UI language for next logins and applies immediately."))

    username = st.session_state.auth.get("username")

    # Load current default (from Controller), fallback to session language
    current_code = controller.get_user_default_lang(username) or get_ui_lang(st.session_state)
    current_name = code_to_name(current_code)

    opts = language_names()
    idx = opts.index(current_name) if current_name in opts else 0
    choice = st.selectbox(u("Default language"), options=opts, index=idx, key="__lang_settings_choice__")

    col1, col2 = st.columns([3, 1], gap="small")

    with col1:
        if st.button(u("Save"), type="primary", use_container_width=True):
            lang_code = name_to_code(choice)

            # 1) Persist via Controller
            ok = controller.set_user_default_lang(username, lang_code)

            # 2) Apply immediately to this session
            set_ui_lang(st.session_state, lang_code)

            # 3) Flag for sidebar sync on next render
            st.session_state["__pending_lang_sync__"] = lang_code

            if ok:
                st.success(u("Saved. Your interface language has been updated."))
            else:
                st.error(u("Could not save your language preference."))

            # 4) Rerun to refresh all pages
            st.rerun()

    with col2:
        if st.button(u("Back"), use_container_width=True):
            st.session_state["__nav__"] = st.session_state.get("__nav_back__", "PatientDash")
            st.rerun()
