import os
import streamlit as st

from ui.components import inject_css

st.set_page_config(page_title="UDPU Console", layout="wide")

inject_css()

def ensure_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8888/api/v1.0")
    if "ws_log" not in st.session_state:
        st.session_state.ws_log = []
    if "ws_connected" not in st.session_state:
        st.session_state.ws_connected = False


def sidebar_settings():
    st.sidebar.header("Настройки")
    base = st.sidebar.text_input("API_BASE_URL", st.session_state.api_base_url)
    if st.sidebar.button("Сохранить"):
        st.session_state.api_base_url = base
        st.sidebar.success("Базовый URL обновлён")


def login_view():
    st.title("Вход")
    with st.form("login_form"):
        username = st.text_input("Логин", value="admin")
        password = st.text_input("Пароль", value="admin", type="password")
        submitted = st.form_submit_button("Войти")
        if submitted:
            if username == "admin" and password == "admin":
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("Успешно")
                st.switch_page("pages/1_Roles.py")
            else:
                st.error("Неверные учетные данные")


def main():
    ensure_state()
    sidebar_settings()
    if st.session_state.authenticated:
        st.info("Вы уже вошли")
        if st.button("Перейти к ролям"):
            st.switch_page("pages/1_Roles.py")
        return
    login_view()


if __name__ == "__main__":
    main()
