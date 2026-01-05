import os
import streamlit as st

from ui.components import inject_css

st.set_page_config(page_title="UDPU Console", layout="wide")


def ensure_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = os.getenv("API_BASE_URL") or os.getenv("BACKEND_BASE_URL") or "http://localhost:8888/api/v1.0"
    if "ws_log" not in st.session_state:
        st.session_state.ws_log = []
    if "ws_connected" not in st.session_state:
        st.session_state.ws_connected = False
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"


def sidebar_settings():
    st.sidebar.header("Settings")
    base = st.sidebar.text_input("API_BASE_URL", st.session_state.api_base_url)
    theme = st.sidebar.selectbox("Theme", ["dark", "light"], index=0 if st.session_state.theme == "dark" else 1)
    if st.sidebar.button("Apply"):
        st.session_state.api_base_url = base
        st.session_state.theme = theme
        st.sidebar.success("Saved")


def login_view():
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", value="admin", type="password")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            if username == "admin" and password == "admin":
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("Authenticated")
                st.switch_page("pages/1_Roles.py")
            else:
                st.error("Invalid credentials")


def main():
    ensure_state()
    inject_css(st.session_state.theme)
    sidebar_settings()
    if st.session_state.authenticated:
        st.switch_page("pages/1_Roles.py")
        return
    login_view()


if __name__ == "__main__":
    main()
