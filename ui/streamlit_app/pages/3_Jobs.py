import streamlit as st

from client.api_client import ApiClient, ApiError
from ui.components import inject_css, render_card, render_json_response, render_error, render_nav, page_header

st.set_page_config(page_title="Jobs", layout="wide", menu_items={"Get help": None, "Report a bug": None, "About": None})

inject_css(st.session_state.get("theme", "dark"))

def require_auth():
    if not st.session_state.get("authenticated"):
        st.error("Sign in required")
        if st.button("Back to login"):
            st.switch_page("app.py")
        st.stop()


def get_client():
    return ApiClient(base_url=st.session_state.get("api_base_url"))


def create_job():
    with st.form("create_job"):
        name = st.text_input("Имя")
        description = st.text_area("Описание", value="")
        command = st.text_area("Команда")
        require_output = st.text_input("Требовать вывод", value="")
        required_software = st.text_input("Необходимое ПО", value="")
        frequency = st.selectbox("Частота", ["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"], index=5)
        locked = st.text_input("Locked", value="")
        role = st.text_input("Роль", value="")
        type_val = st.text_input("Тип", value="common")
        vbuser_id = st.text_input("VB user id", value="")
        submitted = st.form_submit_button("Создать")
        if submitted:
            payload = {
                "name": name.strip(),
                "description": description,
                "command": command,
                "require_output": require_output,
                "required_software": required_software,
                "locked": locked,
                "role": role,
                "type": type_val,
                "vbuser_id": vbuser_id,
            }
            if frequency:
                payload["frequency"] = frequency
            try:
                data = get_client().post("/jobs", payload)
                st.success("Создано")
                render_json_response(data)
            except ApiError as e:
                render_error(e)


def list_jobs():
    with st.form("list_jobs"):
        name = st.text_input("Фильтр по имени", value="")
        submitted = st.form_submit_button("Получить список")
        if submitted:
            params = {"name": name.strip()} if name.strip() else None
            try:
                data = get_client().get("/jobs", params=params)
                render_json_response(data)
            except ApiError as e:
                render_error(e)


def get_job():
    with st.form("get_job"):
        identifier = st.text_input("Имя или UID")
        submitted = st.form_submit_button("Получить")
        if submitted:
            try:
                data = get_client().get(f"/jobs/{identifier.strip()}")
                render_json_response(data)
            except ApiError as e:
                render_error(e)


def update_job():
    with st.form("update_job"):
        identifier = st.text_input("Имя или UID для обновления")
        description = st.text_area("Описание", value="")
        command = st.text_area("Команда", value="")
        require_output = st.text_input("Требовать вывод", value="")
        required_software = st.text_input("Необходимое ПО", value="")
        frequency = st.selectbox("Частота", ["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"], index=0)
        locked = st.text_input("Locked", value="")
        role = st.text_input("Role", value="")
        type_val = st.text_input("Type", value="")
        submitted = st.form_submit_button("Save")
        if submitted:
            payload = {}
            if description:
                payload["description"] = description
            if command:
                payload["command"] = command
            if require_output:
                payload["require_output"] = require_output
            if required_software:
                payload["required_software"] = required_software
            if frequency:
                payload["frequency"] = frequency
            if locked:
                payload["locked"] = locked
            if role:
                payload["role"] = role
            if type_val:
                payload["type"] = type_val
            try:
                data = get_client().patch(f"/jobs/{identifier.strip()}", payload)
                st.success("Обновлено")
                render_json_response(data)
            except ApiError as e:
                render_error(e)


def delete_job():
    with st.form("delete_job"):
        identifier = st.text_input("Имя или UID для удаления")
        submitted = st.form_submit_button("Удалить")
        if submitted:
            try:
                data = get_client().delete(f"/jobs/{identifier.strip()}")
                st.warning("Удалено")
                render_json_response(data)
            except ApiError as e:
                render_error(e)


def jobs_by_role():
    with st.form("jobs_by_role"):
        role = st.text_input("Роль")
        frequency = st.selectbox("Частота", ["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"], index=0)
        submitted = st.form_submit_button("Получить")
        if submitted:
            params = {"frequency": frequency} if frequency else None
            try:
                data = get_client().get(f"/roles/{role.strip()}/jobs", params=params)
                render_json_response(data)
            except ApiError as e:
                render_error(e)


def jobs_by_frequency():
    with st.form("jobs_by_frequency"):
        frequency = st.selectbox("Частота", ["1", "15", "60", "1440", "first_boot", "every_boot", "once"], index=0)
        submitted = st.form_submit_button("Получить")
        if submitted:
            try:
                data = get_client().get(f"/jobs/frequency/{frequency}")
                render_json_response(data)
            except ApiError as e:
                render_error(e)


def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.ws_log = []
    st.session_state.ws_connected = False
    st.switch_page("app.py")


def page():
    require_auth()
    content = render_nav("Задания")
    if st.session_state.pop("nav_logout", False):
        logout()
    with content:
        page_header("Jobs", "Queues, frequencies and role mappings")
        options = {
            "Создать": create_job,
            "Список": list_jobs,
            "Получить": get_job,
            "Обновить": update_job,
            "Удалить": delete_job,
            "По роли": jobs_by_role,
            "По частоте": jobs_by_frequency,
        }
        cols = st.columns([1, 3])
        with cols[0]:
            choice = st.radio("Действие", list(options.keys()))
        with cols[1]:
            render_card(choice, options[choice])


page()
