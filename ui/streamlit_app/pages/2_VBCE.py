import json
import streamlit as st

from client.api_client import ApiClient, ApiError
from ui.components import inject_css, render_card, render_json_response, render_error, render_nav, page_header

st.set_page_config(page_title="VBCE", layout="wide", menu_items={"Get help": None, "Report a bug": None, "About": None})

inject_css(st.session_state.get("theme", "dark"))

def require_auth():
    if not st.session_state.get("authenticated"):
        st.error("Sign in required")
        if st.button("Back to login"):
            st.switch_page("app.py")
        st.stop()


def get_client():
    return ApiClient(base_url=st.session_state.get("api_base_url"))


def create_vbce_section():
    def body():
        mode = st.radio("Input mode", ["Form", "Raw JSON"], horizontal=True)
        if mode == "Raw JSON":
            with st.form("vbce_json"):
                raw = st.text_area("JSON", height=240)
                submitted = st.form_submit_button("Создать")
                if submitted:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        st.error("Некорректный JSON")
                        return
                    try:
                        data = get_client().post("/vbce", payload)
                        st.success("Создано")
                        render_json_response(data)
                    except ApiError as e:
                        render_error(e)
        else:
            with st.form("vbce_form"):
                name = st.text_input("Имя")
                description = st.text_area("Описание", value="")
                max_users = st.number_input("Максимум пользователей", value=510, step=1)
                ip_address = st.text_input("IP адрес", value="")
                tcp_port = st.text_input("TCP порт", value="")
                location_id = st.text_input("ID локации", value="")
                force_local = st.checkbox("Force local", value=False)
                lq_min_rate = st.number_input("LQ min rate", value=0, step=1)
                lq_max_rate = st.number_input("LQ max rate", value=0, step=1)
                lq_mean_rate = st.number_input("LQ mean rate", value=0, step=1)
                submitted = st.form_submit_button("Создать")
                if submitted:
                    payload = {
                        "name": name.strip(),
                        "description": description,
                        "max_users": int(max_users),
                        "ip_address": ip_address.strip(),
                        "tcp_port": tcp_port.strip(),
                        "location_id": location_id.strip(),
                        "force_local": force_local,
                        "lq_min_rate": int(lq_min_rate),
                        "lq_max_rate": int(lq_max_rate),
                        "lq_mean_rate": int(lq_mean_rate),
                    }
                    try:
                        data = get_client().post("/vbce", payload)
                        st.success("Создано")
                        render_json_response(data)
                    except ApiError as e:
                        render_error(e)
    render_card("Создание VBCE", body)


def list_vbce_section():
    def body():
        if st.button("Обновить список"):
            st.session_state["vbce_reload"] = True
        if st.session_state.get("vbce_reload") is None:
            st.session_state["vbce_reload"] = True
        data = []
        if st.session_state.get("vbce_reload"):
            try:
                data = get_client().get("/vbces")
                st.session_state["vbce_cache"] = data
                st.session_state["vbce_reload"] = False
            except ApiError as e:
                render_error(e)
        else:
            data = st.session_state.get("vbce_cache", [])
        if not data:
            st.info("Нет записей VBCE")
            return
        st.dataframe(data, use_container_width=True)
    render_card("Список VBCE", body)


def manage_vbce_section():
    def body():
        with st.form("vbce_get"):
            name = st.text_input("Имя VBCE для просмотра")
            submitted = st.form_submit_button("Получить")
            if submitted:
                try:
                    data = get_client().get(f"/vbce/{name.strip()}")
                    render_json_response(data)
                except ApiError as e:
                    render_error(e)
        with st.form("vbce_patch"):
            target = st.text_input("VBCE для обновления")
            max_users = st.text_input("Max users")
            ip_address = st.text_input("IP адрес")
            tcp_port = st.text_input("TCP port")
            location_id = st.text_input("Location ID")
            force_local = st.selectbox("Force local", ["", True, False], index=0)
            submitted = st.form_submit_button("Save")
            if submitted:
                payload = {}
                if max_users.strip():
                    payload["max_users"] = int(max_users)
                if ip_address.strip():
                    payload["ip_address"] = ip_address.strip()
                if tcp_port.strip():
                    payload["tcp_port"] = tcp_port.strip()
                if location_id.strip():
                    payload["location_id"] = location_id.strip()
                if force_local != "":
                    payload["force_local"] = force_local
                try:
                    data = get_client().patch(f"/vbce/{target.strip()}", payload)
                    st.success("Обновлено")
                    render_json_response(data)
                    st.session_state["vbce_reload"] = True
                except ApiError as e:
                    render_error(e)
        with st.form("vbce_delete"):
            name = st.text_input("Имя VBCE для удаления")
            submitted = st.form_submit_button("Удалить")
            if submitted:
                try:
                    data = get_client().delete(f"/vbce/{name.strip()}")
                    st.warning("Удалено")
                    render_json_response(data)
                    st.session_state["vbce_reload"] = True
                except ApiError as e:
                    render_error(e)
    render_card("Действия", body)


def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.ws_log = []
    st.session_state.ws_connected = False
    st.switch_page("app.py")


def page():
    require_auth()
    content = render_nav("VBCE")
    if st.session_state.pop("nav_logout", False):
        logout()
    with content:
        page_header("VBCE", "Manage entry points and connection settings")
        cols = st.columns([1.1, 1])
        with cols[0]:
            create_vbce_section()
        with cols[1]:
            manage_vbce_section()
        list_vbce_section()


page()
