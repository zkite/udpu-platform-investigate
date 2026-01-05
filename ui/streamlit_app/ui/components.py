import json
from pathlib import Path
import streamlit as st

from ui.theme import get_colors, theme_style

BASE_DIR = Path(__file__).resolve().parent


def inject_css(theme):
    st.markdown(theme_style(theme), unsafe_allow_html=True)
    st.markdown("<style>[data-testid='stSidebarNav']{display:none}</style>", unsafe_allow_html=True)
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
    colors = get_colors(st.session_state.get("theme", "dark"))
    st.markdown(
        f"<span style='background:{colors['surface']}; color:{colors['text']}; padding:4px 8px; border-radius:8px; font-size:12px; border:1px solid {colors['border']}'>"
        f"{text}</span>",
        unsafe_allow_html=True,
    )


def render_nav(active):
    cols = st.columns(5)
    labels = [
        ("Roles", "pages/1_Roles.py"),
        ("VBCE", "pages/2_VBCE.py"),
        ("Jobs", "pages/3_Jobs.py"),
        ("Execute", "pages/4_Execute_WS.py"),
        ("Environment", "pages/5_Environment.py"),
    ]
    for idx, item in enumerate(labels):
        label, target = item
        if cols[idx].button(label, disabled=label == active):
            st.switch_page(target)
