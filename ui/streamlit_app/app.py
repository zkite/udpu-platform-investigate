import os
import streamlit as st

from ui.components import inject_css, theme_toggle

st.set_page_config(page_title="UDPU Console", layout="wide", menu_items={"Get help": None, "Report a bug": None, "About": None})


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
    if "nav_logout" not in st.session_state:
        st.session_state.nav_logout = False


def sidebar_settings():
    st.sidebar.header("Настройки")
    base = st.sidebar.text_input("API_BASE_URL", st.session_state.api_base_url)
    if st.sidebar.button("Save"):
        st.session_state.api_base_url = base
        st.sidebar.success("Сохранено")


def login_view():
    top = st.columns([5, 2.2])
    with top[1]:
        theme_toggle("login")
    st.markdown(
        """
        <div class="page-hero">
          <div class="hero-title">UDPU Platform</div>
          <p class="hero-sub">Clean control panel for services and configs</p>
          <div class="hero-meta">
            <span>⚡ Quick access</span>
            <span>🔒 Secure login</span>
            <span>🎨 Theme toggle</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns([1.1, 1])
    with cols[0]:
        st.markdown(
            """
            <div class="card">
              <div class="card-title">Minimal layout</div>
              <div class="card-body">
                <p>Tailwind-inspired surfaces, crisp typography and calm spacing for faster work.</p>
                <p>Switch between light and dark instantly and keep key actions in one place.</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Sign in</div>', unsafe_allow_html=True)
        st.markdown('<p class="login-sub">Use administrator credentials</p>', unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", value="admin", type="password")
            submitted = st.form_submit_button("Sign in")
            if submitted:
                if username == "admin" and password == "admin":
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("Signed in")
                    st.switch_page("pages/1_Roles.py")
                else:
                    st.error("Invalid credentials")
        st.markdown("</div>", unsafe_allow_html=True)


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
