"""Internationalization (i18n) utilities for CLI"""
import json
from pathlib import Path
from typing import Dict, Optional

# Locales directory
LOCALES_DIR = Path(__file__).parent.parent / "locales"

# Cache for loaded translations
_translations_cache: Dict[str, Dict[str, str]] = {}


def load_translations(lang: str) -> Dict[str, str]:
    """
    Load translations for a specific language

    Args:
        lang: Language code (en, zh, ja)

    Returns:
        Dictionary of translations
    """
    if lang in _translations_cache:
        return _translations_cache[lang]

    locale_file = LOCALES_DIR / f"{lang}.json"

    if not locale_file.exists():
        print(
            f"[WARNING] Locale file not found: {locale_file}, falling back to English")
        lang = "en"
        locale_file = LOCALES_DIR / "en.json"

    try:
        with open(locale_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)
            _translations_cache[lang] = translations
            return translations
    except Exception as e:
        print(f"[ERROR] Failed to load translations for {lang}: {e}")
        return {}


def t(key: str, lang: str = "en") -> str:
    """
    Get translated text

    Args:
        key: Translation key
        lang: Language code (en, zh, ja)

    Returns:
        Translated text, or key if not found
    """
    translations = load_translations(lang)
    return translations.get(key, key)


def get_available_languages() -> list:
    """
    Get list of available language codes

    Returns:
        List of language codes
    """
    if not LOCALES_DIR.exists():
        return ["en"]

    return [
        f.stem for f in LOCALES_DIR.glob("*.json")
        if f.is_file()
    ]


def reload_translations():
    """Clear the translations cache to force reload"""
    global _translations_cache
    _translations_cache.clear()
