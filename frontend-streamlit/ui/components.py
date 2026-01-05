import json
from pathlib import Path
import streamlit as st

from ui.theme import COLORS

BASE_DIR = Path(__file__).resolve().parent


def inject_css():
    path = BASE_DIR / "styles.css"
    if path.exists():
        st.markdown(f"<style>{path.read_text()}</style>", unsafe_allow_html=True)


def render_card(title, body_fn):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"<h3>{title}</h3>", unsafe_allow_html=True)
        st.markdown('<div class="card-body">', unsafe_allow_html=True)
        body_fn()
        st.markdown('</div></div>', unsafe_allow_html=True)


def render_json_response(data):
    if data is None:
        return
    text = data
    if not isinstance(text, str):
        text = json.dumps(data, ensure_ascii=False, indent=2)
    st.markdown('<div class="code-block">', unsafe_allow_html=True)
    st.code(text, language="json")
    st.markdown('</div>', unsafe_allow_html=True)


def render_error(err):
    msg = str(err)
    if hasattr(err, "message"):
        msg = getattr(err, "message")
    st.error(msg)


def status_badge(text):
    st.markdown(
        f"<span style='background:{COLORS['surface']}; color:{COLORS['text']}; padding:4px 8px; border-radius:8px; font-size:12px; border:1px solid {COLORS['border']}'>"
        f"{text}</span>",
        unsafe_allow_html=True,
    )
