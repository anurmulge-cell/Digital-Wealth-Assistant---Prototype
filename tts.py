"""
tts.py
Converts WealthAssist's text responses to spoken audio using gTTS (a free,
unofficial wrapper around Google Translate's TTS engine - no separate
Google Cloud project or credential needed, so it doesn't add a second key
to manage alongside the Gemini key).

Cached by text so the same response is never re-synthesized on every
Streamlit rerun. If synthesis fails for any reason (no network, etc.),
callers should catch the exception and continue with text only - voice is
an enhancement, not something the app should ever depend on to function.
"""

import io
import streamlit as st
from gtts import gTTS


@st.cache_data(show_spinner=False)
def text_to_speech_bytes(text: str) -> bytes:
    """Converts text to MP3 audio bytes. tld='co.in' gives an Indian-English
    accent, consistent with the app's persona/context."""
    buf = io.BytesIO()
    gTTS(text=text, lang="en", tld="co.in").write_to_fp(buf)
    buf.seek(0)
    return buf.read()
