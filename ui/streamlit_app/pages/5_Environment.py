import os
import streamlit as st

from ui.components import inject_css, render_card, render_nav, page_header

st.set_page_config(page_title="Environment", layout="wide", menu_items={"Get help": None, "Report a bug": None, "About": None})

inject_css(st.session_state.get("theme", "dark"))


def require_auth():
    if not st.session_state.get("authenticated"):
        st.error("Требуется вход")
        if st.button("Перейти к логину"):
            st.switch_page("app.py")
        st.stop()


def env_items():
    keys = [
        "API_BASE_URL",
        "BACKEND_BASE_URL",
        "API_TIMEOUT",
        "WS_TIMEOUT",
        "ENV",
        "UI_REQUEST_TIMEOUT",
    ]
    rows = []
    for key in keys:
        rows.append({"name": key, "value": os.getenv(key, "not set")})
    rows.append({"name": "Active API base", "value": st.session_state.get("api_base_url")})
    rows.append({"name": "Theme", "value": st.session_state.get("theme", "dark")})
    return rows


def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.ws_log = []
    st.session_state.ws_connected = False
    st.switch_page("app.py")


def page():
    require_auth()
    content = render_nav("Окружение")
    if st.session_state.pop("nav_logout", False):
        logout()
    with content:
        page_header("Окружение", "Активные переменные и настройки подключения")
        rows = env_items()
        render_card("Параметры окружения", lambda: st.table(rows))


page()
