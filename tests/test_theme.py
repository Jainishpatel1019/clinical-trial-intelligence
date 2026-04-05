"""Tests for theme module (import-only, no Streamlit runtime needed)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_theme_module_imports():
    from app.theme import inject_theme, _BASE, _CHAT
    assert callable(inject_theme)
    assert len(_BASE) > 100
    assert len(_CHAT) > 100


def test_base_css_contains_palette():
    from app.theme import _BASE
    assert "#FAFAF7" in _BASE or "#FFFFFF" in _BASE
    assert "#1A5276" in _BASE
    assert "Inter" in _BASE


def test_chat_css_contains_chat_elements():
    from app.theme import _CHAT
    assert "cti-chat" in _CHAT
    assert "stChatMessage" in _CHAT
    assert "stChatInput" in _CHAT
