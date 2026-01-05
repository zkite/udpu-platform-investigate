import json
from pathlib import Path
import streamlit as st

from ui.theme import get_colors, theme_style

BASE_DIR = Path(__file__).resolve().parent


def inject_css(theme):
    st.markdown(theme_style(theme), unsafe_allow_html=True)
    st.markdown(
        "<style>[data-testid='stSidebarNav']{display:none} button[title='Deploy this app']{display:none!important}</style>",
        unsafe_allow_html=True,
    )
    path = BASE_DIR / "styles.css"
    if path.exists():
        st.markdown(f"<style>{path.read_text()}</style>", unsafe_allow_html=True)


def theme_toggle(label="Темная тема"):
    current = st.session_state.get("theme", "dark")
    next_theme = "light" if current == "dark" else "dark"
    icon = "🌙" if current == "dark" else "☀️"
    caption = "Dark" if current == "dark" else "Light"
    if st.button(f"{icon} {caption} mode", key=f"theme_btn_{label}", use_container_width=True):
        st.session_state.theme = next_theme


def render_card(title, body_fn):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{title}</div>", unsafe_allow_html=True)
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
    labels = [
        ("Роли", "pages/1_Roles.py"),
        ("VBCE", "pages/2_VBCE.py"),
        ("Jobs", "pages/3_Jobs.py"),
        ("Execute", "pages/4_Execute_WS.py"),
        ("Env", "pages/5_Environment.py"),
    ]
    with st.container():
        top = st.columns([1.4, 3, 1.2], gap="large")
        with top[0]:
            st.markdown("<div class='brand-badge'>UDPU Console</div><p class='brand-sub'>Minimal control center</p>", unsafe_allow_html=True)
        with top[1]:
            btn_cols = st.columns(len(labels))
            for (label, target), col in zip(labels, btn_cols):
                with col:
                    if st.button(label, use_container_width=True, disabled=label == active, key=f"nav_{label}"):
                        st.switch_page(target)
        with top[2]:
            theme_toggle("nav")
            if st.button("Sign out", use_container_width=True, key="nav_sign_out"):
                st.session_state["nav_logout"] = True
        st.markdown('<div class="nav-underline"></div>', unsafe_allow_html=True)
    content_col = st.container()
    return content_col


def page_header(title, subtitle=None, extra=None):
    labels = [
        ("🛡️", "Roles"),
        ("🛰️", "uDPU & VBCE"),
        ("⚡", "Jobs & actions"),
    ]
    with st.container():
        st.markdown('<div class="page-hero">', unsafe_allow_html=True)
        st.markdown(f"<div class='hero-title'>{title}</div>", unsafe_allow_html=True)
        if subtitle:
            st.markdown(f"<p class='hero-sub'>{subtitle}</p>", unsafe_allow_html=True)
        st.markdown('<div class="hero-meta">', unsafe_allow_html=True)
        for icon, text in labels:
            st.markdown(f"<span>{icon} {text}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        if extra:
            extra()
        st.markdown("</div>", unsafe_allow_html=True)
