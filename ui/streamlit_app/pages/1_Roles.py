import json
import streamlit as st

from client.api_client import ApiClient, ApiError
from ui.components import inject_css, render_card, render_json_response, render_error

st.set_page_config(page_title="Roles", layout="wide")

inject_css()

def require_auth():
    if not st.session_state.get("authenticated"):
        st.error("Нужен вход")
        if st.button("К логину"):
            st.switch_page("app.py")
        st.stop()


def get_client():
    return ApiClient(base_url=st.session_state.get("api_base_url"))


def create_role_section():
    def body():
        with st.form("create_role"):
            name = st.text_input("Имя роли")
            description = st.text_area("Описание")
            wireguard = st.checkbox("Wireguard tunnel", value=False)
            job_control = st.checkbox("Job control", value=False)
            interfaces_raw = st.text_area("Interfaces JSON (опционально)", value="", height=120)
            submitted = st.form_submit_button("Создать")
            if submitted:
                payload = {
                    "name": name.strip(),
                    "description": description,
                    "wireguard_tunnel": wireguard,
                    "job_control": job_control,
                }
                if interfaces_raw.strip():
                    try:
                        payload["interfaces"] = json.loads(interfaces_raw)
                    except json.JSONDecodeError:
                        st.error("Некорректный JSON интерфейсов")
                        return
                try:
                    data = get_client().post("/roles", payload)
                    st.success("Создано")
                    render_json_response(data)
                except ApiError as e:
                    render_error(e)
    render_card("Создать роль", body)


def clone_role_section():
    def body():
        with st.form("clone_role"):
            name = st.text_input("Имя исходной роли")
            new_name = st.text_input("Новое имя роли")
            submitted = st.form_submit_button("Клонировать")
            if submitted:
                payload = {"name": name.strip(), "new_role_name": new_name.strip()}
                try:
                    data = get_client().post("/roles/clone", payload)
                    st.success("Клонировано")
                    render_json_response(data)
                except ApiError as e:
                    render_error(e)
    render_card("Клонировать роль", body)


def list_roles_section():
    def body():
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Обновить список"):
                st.session_state["roles_reload"] = True
        roles = []
        if st.session_state.get("roles_reload") is None:
            st.session_state["roles_reload"] = True
        if st.session_state.get("roles_reload"):
            try:
                roles = get_client().get("/roles")
                st.session_state["roles_cache"] = roles
                st.session_state["roles_reload"] = False
            except ApiError as e:
                render_error(e)
        else:
            roles = st.session_state.get("roles_cache", [])
        if not roles:
            st.info("Нет ролей")
            return
        st.dataframe(roles, use_container_width=True)
        for role in roles:
            with st.expander(role.get("name", "")):
                st.json(role)
                with st.form(f"update_{role.get('name')}"):
                    new_name = st.text_input("Имя", value=role.get("name", ""))
                    description = st.text_area("Описание", value=role.get("description", ""))
                    wireguard = st.checkbox("Wireguard", value=bool(role.get("wireguard_tunnel")))
                    job_control = st.checkbox("Job control", value=bool(role.get("job_control")))
                    submitted = st.form_submit_button("Обновить")
                    if submitted:
                        payload = {
                            "name": new_name.strip(),
                            "description": description,
                            "wireguard_tunnel": wireguard,
                            "job_control": job_control,
                        }
                        try:
                            data = get_client().patch(f"/roles/{role.get('name')}", payload)
                            st.success("Обновлено")
                            render_json_response(data)
                            st.session_state["roles_reload"] = True
                        except ApiError as e:
                            render_error(e)
                with st.form(f"delete_{role.get('name')}"):
                    confirm = st.text_input("Введите имя для удаления", value="")
                    submitted = st.form_submit_button("Удалить")
                    if submitted and confirm == role.get("name"):
                        try:
                            data = get_client().delete(f"/roles/{role.get('name')}")
                            st.warning("Удалено")
                            render_json_response(data)
                            st.session_state["roles_reload"] = True
                        except ApiError as e:
                            render_error(e)
    render_card("Список ролей", body)


def page():
    require_auth()
    st.title("Roles")
    st.caption(f"База API: {st.session_state.get('api_base_url')}")
    if st.button("Выйти"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.ws_log = []
        st.session_state.ws_connected = False
        st.switch_page("app.py")
    create_role_section()
    clone_role_section()
    list_roles_section()


page()
