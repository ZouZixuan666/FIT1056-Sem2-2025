# app/core/ui.py
from __future__ import annotations
from typing import List, Dict

# Map: full language name <-> code
LANG_NAME_TO_CODE: Dict[str, str] = {
    "English": "en",
    "Malay": "ms",
    "Chinese": "zh",
    "Tamil": "ta",
}
LANG_CODE_TO_NAME: Dict[str, str] = {v: k for k, v in LANG_NAME_TO_CODE.items()}

def language_names() -> List[str]:
    return list(LANG_NAME_TO_CODE.keys())

def code_to_name(code: str) -> str:
    return LANG_CODE_TO_NAME.get(code, "English")

def name_to_code(name: str) -> str:
    return LANG_NAME_TO_CODE.get(name, "en")

def get_ui_lang(state) -> str:
    return state.get("ui_lang", "en")

def set_ui_lang(state, lang_code: str) -> None:
    state["ui_lang"] = lang_code if lang_code in LANG_CODE_TO_NAME else "en"

def u(text: str) -> str:
    """
    Translate a UI string to the current UI language using app.core.translate.translate_text().
    If current UI language is English, return the original string.
    """
    if not text:
        return text
    try:
        import streamlit as st
        from app.core.translate import translate_text
        lang = get_ui_lang(st.session_state)
        if lang == "en":
            return text
        return translate_text(text, lang)
    except Exception:
        return text
