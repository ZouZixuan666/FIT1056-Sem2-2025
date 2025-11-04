# gui/views/patient_Preference.py
import streamlit as st
from typing import Optional, List

from gui.ui import u, language_names, name_to_code, get_ui_lang, set_ui_lang
from app.core.translate import translate_text
from app.database.controller import Controller  # ← fixed import
from app.users.preferences import Preferences
from app.core.audit import audit

# Instantiate controller
controller = Controller()


# ---------- Helpers ----------
def _get_current_patient_id() -> Optional[str]:
    """Derive the current patient ID from session auth info."""
    auth = st.session_state.get("auth", {}) or {}
    return auth.get("patientID") or auth.get("patient_id") or auth.get("username")


def _resolve_patient_id_from_auth() -> str:
    """If logged-in role is patient and username looks like a PatientID (P###), return it."""
    auth = st.session_state.get("auth", {}) or {}
    if auth.get("role") == "patient":
        uname = auth.get("username") or ""
        if isinstance(uname, str) and uname.startswith("P"):
            return uname
    return ""


# ---------- Page ----------
def render():
    st.title("🧑‍🦰 " + u("Patient Portal"))
    st.caption(u("FR: View/Update personal preferences, read-only logs"))

    # Role check
    role = st.session_state.get("auth", {}).get("role") if isinstance(st.session_state.get("auth"), dict) else None
    is_patient_user = (role == "patient")

    st.subheader(u("Preferences"))

    # Patient ID: try strong detect; allow manual if not found
    default_pid = _resolve_patient_id_from_auth() or (_get_current_patient_id() or "")
    pid = st.text_input(
        u("Patient ID"),
        value=default_pid,
        placeholder=u("e.g., P001"),
        help=u("If you are a patient and your username is your patient ID, this is filled automatically."),
        disabled=bool(default_pid),
        key="__prefs_pid__",
    ).strip()

    if not pid:
        st.info(u("Enter your Patient ID to view or edit preferences."))
        return

    # Load current preferences via Controller
    try:
        current: Optional[Preferences] = controller.get_preferences(pid)
    except Exception:
        current = None

    # Option sets
    dietary_options = ["No pork", "No beef", "Vegetarian", "Vegan", "Lactose-free", "Gluten-free", "Diabetic"]
    religious_options = ["Halal", "Kosher", "Hindu", "Buddhist", "Christian", "Sikh", "Other"]
    room_choices = ["Single", "Shared", "Isolation"]

    # Defaults from existing prefs
    init_diet = getattr(current, "dietaryNeeds", []) if current else []
    init_relig = getattr(current, "religiousNeeds", []) if current else []
    init_cultural = getattr(current, "culturalNeeds", "") if current else ""
    init_room = getattr(current, "roomType", "Single") if current else "Single"
    selected_lang_name = getattr(current, "preferred_language", get_ui_lang(st.session_state)) if current else get_ui_lang(st.session_state)
    languages = language_names()
    if selected_lang_name not in languages:
        selected_lang_name = languages[0]

    with st.form("__prefs_form__", clear_on_submit=False):
        c1, c2 = st.columns([1, 1])

        with c1:
            pref_language = st.selectbox(
                u("Preferred language"), languages,
                index=languages.index(selected_lang_name),
                key="__pref_lang__"
            )

            diet_sel = st.multiselect(
                u("Dietary Needs (pick all that apply)"),
                options=dietary_options,
                default=[x for x in init_diet if x in dietary_options],
                help=u("Choose from the list. Add anything else below."),
                key="__diet_sel__",
            )
            diet_extra = st.text_input(
                u("Additional dietary needs (comma-separated)"),
                value=", ".join([x for x in init_diet if x not in dietary_options]) if init_diet else "",
                placeholder=u("e.g., Low sodium, High fiber"),
                key="__diet_extra__",
            )

        with c2:
            relig_sel = st.multiselect(
                u("Religious Needs"),
                options=religious_options,
                default=[x for x in init_relig if x in religious_options],
                help=u("Choose from the list. Add anything else below."),
                key="__relig_sel__",
            )
            relig_extra = st.text_input(
                u("Additional religious needs (comma-separated)"),
                value=", ".join([x for x in init_relig if x not in religious_options]) if init_relig else "",
                placeholder=u("e.g., Fasting schedule, Prayer timing"),
                key="__relig_extra__",
            )

        cultural_txt = st.text_area(
            u("Cultural Needs / Notes"),
            value=init_cultural,
            placeholder=u("Anything staff should be mindful of."),
            height=120,
            key="__cultural__",
        )

        room_type = st.selectbox(
            u("Room type"),
            room_choices,
            index=room_choices.index(init_room) if init_room in room_choices else 0,
            key="__pref_room__",
        )

        st.caption(u("Changes are saved to your profile and can be viewed by assigned staff (read-only)."))

        can_edit = is_patient_user and (pid == (_get_current_patient_id() or _resolve_patient_id_from_auth() or pid))
        if not can_edit:
            st.warning(u("Preferences can only be changed by the patient account."))
        save = st.form_submit_button(u("Save Preferences"), type="primary", disabled=not can_edit)

        if save:
            def _merge(base_list: List[str], extra_csv: str) -> List[str]:
                extras = [x.strip() for x in (extra_csv or "").split(",") if x.strip()]
                return [*base_list, *extras]

            new_diet = _merge(diet_sel, diet_extra)
            new_relig = _merge(relig_sel, relig_extra)
            new_cultural = (cultural_txt or "").strip()

            payload = {
                "patientID": pid,
                "preferred_language": pref_language,
                "dietaryNeeds": new_diet,
                "religiousNeeds": new_relig,
                "culturalNeeds": new_cultural,
                "roomType": room_type,
            }

            try:
                if current:
                    controller.edit_preferences(pid, payload)
                    audit("preferences.update", who=pid, role="patient", details={"patientID": pid})
                    st.success(u("Preferences updated."))
                else:
                    controller.set_preferences(pid, payload)
                    audit("preferences.create", who=pid, role="patient", details={"patientID": pid})
                    st.success(u("Preferences saved."))
            except Exception as e:
                st.error(u(f"Failed to save preferences: {e}"))

    # Show current saved prefs
    st.markdown(u("#### Current Saved Preferences"))
    refreshed = controller.get_preferences(pid)
    if not refreshed:
        st.caption(u("No preferences saved yet."))
    else:
        with st.container():
            st.write(f"**{u('Patient ID')}:** {pid}")
            st.write(f"**{u('Preferred language')}:** {getattr(refreshed, 'preferred_language', '-') or '-'}")
            st.write(f"**{u('Dietary Needs')}:** {', '.join(getattr(refreshed, 'dietaryNeeds', [])) or '-'}")
            st.write(f"**{u('Religious Needs')}:** {', '.join(getattr(refreshed, 'religiousNeeds', [])) or '-'}")
            st.write(f"**{u('Cultural Notes')}:** {getattr(refreshed, 'culturalNeeds', '') or '-'}")
            st.write(f"**{u('Room type')}:** {getattr(refreshed, 'roomType', '') or '-'}")

    # -------- Translation demo (kept) --------
    st.divider()
    st.subheader(u("My Logs (read-only)"))
    demo_text = st.text_area(u("Text"), key="__patient_text__")
    cols = st.columns([2, 2])
    with cols[0]:
        tgt_name = st.selectbox(u("Translate text to"), language_names(), index=0, key="__pat_tgt__")
        tgt_code = name_to_code(tgt_name)
    with cols[1]:
        if st.button(u("Translate"), key="__pat_go__"):
            if demo_text:
                st.session_state["__patient_text__"] = translate_text(demo_text, tgt_code)
                st.success(u("Translated."))
            else:
                st.warning(u("No text to translate."))
