# app/core/translate.py
from __future__ import annotations
from functools import lru_cache
from typing import Optional, Tuple, Dict
import inspect, asyncio, json
from pathlib import Path

# Speed knobs
PREFER_ARGOS_FIRST = True
ARGOS_AUTO_INSTALL = False
CACHE_PATH = Path("data/translate_cache.json")

SUPPORTED_LANGS = ["en", "ms", "zh", "ta"]
GT_MAP     = {"en":"en","ms":"ms","zh":"zh-CN","ta":"ta"}
ARGOS_MAP  = {"en":"en","ms":"ms","zh":"zh","ta":"ta"}

# persistent cache
_cache: Dict[str, str] = {}
def _load_cache():
    global _cache
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if CACHE_PATH.exists():
            _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        _cache = {}
def _save_cache():
    try:
        CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
_load_cache()

def _ckey(text: str, tgt: str) -> str:
    return f"{tgt}::{text}"

# googletrans
def _await_if_needed(x):
    if inspect.isawaitable(x):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(x)
        else:
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(x)
            finally:
                new_loop.close()
    return x

def _gt_translate(text: str, target: str) -> Optional[str]:
    try:
        from googletrans import Translator  # type: ignore
        tr = Translator()
        res = tr.translate(text, dest=GT_MAP.get(target, target))
        res = _await_if_needed(res)
        return getattr(res, "text", None) or None
    except Exception:
        return None

# Argos
def _argos_available_pair(src: str, tgt: str) -> bool:
    try:
        import argostranslate.translate as argos  # type: ignore
        s = ARGOS_MAP.get(src, src)
        t = ARGOS_MAP.get(tgt, tgt)
        for lang in argos.get_installed_languages():
            if lang.code == s:
                for tr in lang.translations:
                    if getattr(tr, "to_code", "") == t:
                        return True
        return False
    except Exception:
        return False

def _argos_install_pairs_if_needed(pairs: Tuple[Tuple[str, str], ...]) -> None:
    if not ARGOS_AUTO_INSTALL:
        return
    try:
        import argostranslate.package as pkg  # type: ignore
        pkg.update_package_index()
        available = pkg.get_available_packages()
        for src, tgt in pairs:
            if _argos_available_pair(src, tgt):
                continue
            for p in available:
                if p.from_code == ARGOS_MAP.get(src, src) and p.to_code == ARGOS_MAP.get(tgt, tgt):
                    pkg.install_from_path(p.download()); break
    except Exception:
        pass

def _argos_translate(text: str, src: str | None, target: str) -> Optional[str]:
    try:
        import argostranslate.translate as argos  # type: ignore
        s = ARGOS_MAP.get(src, "auto") if src else "auto"
        t = ARGOS_MAP.get(target, target)
        out = argos.translate(text, s, t)
        return out if isinstance(out, str) and out.strip() else None
    except Exception:
        return None

# Public API
@lru_cache(maxsize=4096)
def translate_text(text: str, target_lang: str, source_lang: str | None = None) -> str:
    """
    Translate text to target_lang. We DO allow target_lang == 'en'
    so users can translate back to English.
    """
    if not text or target_lang not in SUPPORTED_LANGS:
        return text

    key = _ckey(text, target_lang)
    if key in _cache:
        return _cache[key]

    # Prefer Google when translating to English (it auto-detects source well)
    def try_gt():
        return _gt_translate(text, target_lang)

    def try_argos():
        if not _argos_available_pair(source_lang or "en", target_lang):
            _argos_install_pairs_if_needed(((source_lang or "en"), target_lang))
        return _argos_translate(text, source_lang, target_lang)

    out = None
    if target_lang == "en":
        # Prefer Google for zh/ms/ta -> en
        out = try_gt() or try_argos()
    else:
        # Existing preference knob
        out = (try_argos() if PREFER_ARGOS_FIRST else try_gt()) or \
              (try_gt() if PREFER_ARGOS_FIRST else try_argos())

    if isinstance(out, str) and out.strip():
        _cache[key] = out
        _save_cache()
        return out

    # Fallback to original if both engines failed
    return text

def translate_selftest() -> str:
    try:
        out = translate_text("Hello", "ms")
        return "ok" if out and out.lower() != "hello" else "no-translation"
    except Exception as e:
        return f"error:{e.__class__.__name__}"

def warmup():
    for tgt in ("ms", "zh", "ta"):
        _ = translate_text("ready", tgt)
