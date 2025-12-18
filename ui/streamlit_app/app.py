import streamlit as st
from services.api_client import APIClient

st.set_page_config(page_title="uDPU Console", layout="wide")

client = APIClient()


def init_state():
    defaults = {
        "auth": False,
        "username": "",
        "role_delete": "",
        "udpu_delete": "",
        "job_delete": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def login_view():
    st.title("Login")
    with st.form("login_form"):
        user = st.text_input("Имя пользователя")
        pwd = st.text_input("Пароль", type="password")
        submit = st.form_submit_button("Войти")
        if submit:
            if user == "admin" and pwd == "admin":
                st.session_state["auth"] = True
                st.session_state["username"] = user
                st.success("Вход выполнен")
                st.experimental_rerun()
            else:
                st.error("Неверные учетные данные")


def logout_action():
    st.session_state["auth"] = False
    st.session_state["username"] = ""
    st.experimental_rerun()


def show_header():
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown(f"**Пользователь:** {st.session_state['username']}")
    with cols[1]:
        st.button("Выйти", on_click=logout_action, type="primary")
    st.divider()


def role_create_form():
    with st.expander("Создать роль"):
        with st.form("create_role_form"):
            name = st.text_input("Имя")
            description = st.text_area("Описание")
            wireguard_tunnel = st.checkbox("Wireguard туннель")
            job_control = st.checkbox("Контроль заданий")
            submit = st.form_submit_button("Создать")
            if submit:
                if not name.strip() or not description.strip():
                    st.error("Имя и описание обязательны")
                else:
                    payload = {
                        "name": name.strip(),
                        "description": description.strip(),
                        "wireguard_tunnel": wireguard_tunnel,
                        "job_control": job_control,
                    }
                    ok, data, error = client.create_role(payload)
                    if ok:
                        st.success("Роль создана")
                        st.experimental_rerun()
                    else:
                        st.error(error or data)


def role_list():
    ok, data, error = client.get_roles()
    if not ok:
        st.error(error or data)
        return
    if not data:
        st.info("Нет ролей")
        return
    for item in data:
        name = item.get("name", "")
        with st.expander(name or "Роль"):
            st.markdown(f"**Описание:** {item.get('description', '')}")
            st.markdown(f"Wireguard: {'Да' if item.get('wireguard_tunnel') else 'Нет'}")
            st.markdown(f"Контроль заданий: {'Да' if item.get('job_control') else 'Нет'}")
            with st.form(f"edit_role_{name}"):
                st.text_input("Имя", value=name, disabled=True)
                description = st.text_area("Описание", value=item.get("description", ""))
                wireguard_tunnel = st.checkbox("Wireguard туннель", value=item.get("wireguard_tunnel", False))
                job_control = st.checkbox("Контроль заданий", value=item.get("job_control", False))
                submit = st.form_submit_button("Сохранить")
                if submit:
                    if not description.strip():
                        st.error("Описание обязательно")
                    else:
                        payload = {
                            "name": name,
                            "description": description.strip(),
                            "wireguard_tunnel": wireguard_tunnel,
                            "job_control": job_control,
                        }
                        ok_update, updated, err_update = client.update_role(name, payload)
                        if ok_update:
                            st.success("Роль обновлена")
                            st.experimental_rerun()
                        else:
                            st.error(err_update or updated)
            delete_cols = st.columns(2)
            with delete_cols[0]:
                if st.button("Удалить", key=f"delete_role_{name}"):
                    st.session_state["role_delete"] = name
            with delete_cols[1]:
                if st.session_state.get("role_delete") == name:
                    if st.button("Подтвердить удаление", key=f"confirm_role_{name}"):
                        ok_del, resp, err_del = client.delete_role(name)
                        st.session_state["role_delete"] = ""
                        if ok_del:
                            st.success("Роль удалена")
                            st.experimental_rerun()
                        else:
                            st.error(err_del or resp)


def udpu_create_form(role_names):
    with st.expander("Создать uDPU"):
        with st.form("create_udpu_form"):
            location = st.text_input("Локация")
            role = st.selectbox("Роль", options=[""] + role_names, format_func=lambda x: "Не выбрано" if x == "" else x)
            upstream_qos = st.text_input("Upstream QoS")
            downstream_qos = st.text_input("Downstream QoS")
            mac_address = st.text_input("MAC-адрес")
            hostname = st.text_input("Hostname")
            submit = st.form_submit_button("Создать")
            if submit:
                if not location.strip() or not role.strip() or not upstream_qos.strip() or not downstream_qos.strip():
                    st.error("Все обязательные поля должны быть заполнены")
                else:
                    payload = {
                        "location": location.strip(),
                        "role": role.strip(),
                        "upstream_qos": upstream_qos.strip(),
                        "downstream_qos": downstream_qos.strip(),
                    }
                    if mac_address.strip():
                        payload["mac_address"] = mac_address.strip()
                    if hostname.strip():
                        payload["hostname"] = hostname.strip()
                    ok, data, error = client.create_udpu(payload)
                    if ok:
                        st.success("uDPU создан")
                        st.experimental_rerun()
                    else:
                        st.error(error or data)


def load_udpu_items():
    ok, locations, error = client.get_udpu_locations()
    if not ok:
        st.error(error or locations)
        return []
    items = []
    for loc in locations:
        ok_list, udpu_list, err_list = client.get_udpu_list_by_location(loc)
        if ok_list:
            items.extend(udpu_list or [])
        elif err_list and "not found" in str(err_list).lower():
            continue
        else:
            st.warning(err_list or udpu_list)
    return items


def udpu_list(role_names):
    items = load_udpu_items()
    if not items:
        st.info("Нет записей")
        return
    for item in items:
        uid = item.get("subscriber_uid", "")
        header = item.get("hostname") or uid or "uDPU"
        with st.expander(header):
            st.markdown(f"UID: {uid}")
            st.markdown(f"Локация: {item.get('location', '')}")
            st.markdown(f"MAC: {item.get('mac_address', '')}")
            st.markdown(f"Роль: {item.get('role', '')}")
            st.markdown(f"Upstream: {item.get('upstream_qos', '')}")
            st.markdown(f"Downstream: {item.get('downstream_qos', '')}")
            with st.form(f"edit_udpu_{uid}"):
                location = st.text_input("Локация", value=item.get("location", ""))
                role_options = ["" ] + role_names
                role_val = item.get("role", "")
                role_index = 0
                if role_val in role_names:
                    role_index = role_options.index(role_val)
                role = st.selectbox("Роль", options=role_options, index=role_index, key=f"role_select_{uid}", format_func=lambda x: "Не выбрано" if x == "" else x)
                upstream_qos = st.text_input("Upstream QoS", value=item.get("upstream_qos", ""))
                downstream_qos = st.text_input("Downstream QoS", value=item.get("downstream_qos", ""))
                mac_address = st.text_input("MAC-адрес", value=item.get("mac_address", ""))
                hostname = st.text_input("Hostname", value=item.get("hostname", ""))
                submit = st.form_submit_button("Сохранить")
                if submit:
                    if not location.strip() or not role.strip() or not upstream_qos.strip() or not downstream_qos.strip():
                        st.error("Поля обязательны")
                    else:
                        payload = {
                            "location": location.strip(),
                            "role": role.strip(),
                            "upstream_qos": upstream_qos.strip(),
                            "downstream_qos": downstream_qos.strip(),
                        }
                        if mac_address.strip():
                            payload["mac_address"] = mac_address.strip()
                        if hostname.strip():
                            payload["hostname"] = hostname.strip()
                        ok_update, updated, err_update = client.update_udpu(uid, payload)
                        if ok_update:
                            st.success("uDPU обновлен")
                            st.experimental_rerun()
                        else:
                            st.error(err_update or updated)
            delete_cols = st.columns(2)
            with delete_cols[0]:
                if st.button("Удалить", key=f"delete_udpu_{uid}"):
                    st.session_state["udpu_delete"] = uid
            with delete_cols[1]:
                if st.session_state.get("udpu_delete") == uid:
                    if st.button("Подтвердить удаление", key=f"confirm_udpu_{uid}"):
                        ok_del, resp, err_del = client.delete_udpu(uid)
                        st.session_state["udpu_delete"] = ""
                        if ok_del:
                            st.success("uDPU удален")
                            st.experimental_rerun()
                        else:
                            st.error(err_del or resp)


def job_create_form(role_names):
    with st.expander("Создать задание"):
        with st.form("create_job_form"):
            name = st.text_input("Имя")
            description = st.text_area("Описание")
            command = st.text_area("Команда")
            frequency = st.selectbox("Частота", options=["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"], format_func=lambda x: "Не выбрано" if x == "" else x)
            require_output = st.text_input("Требуется вывод")
            required_software = st.text_input("Требуемое ПО")
            role = st.selectbox("Роль", options=["" ] + role_names)
            locked = st.text_input("Locked")
            job_type = st.text_input("Тип", value="common")
            vbuser_id = st.text_input("VBUser ID")
            submit = st.form_submit_button("Создать")
            if submit:
                if not name.strip() or not command.strip():
                    st.error("Имя и команда обязательны")
                else:
                    payload = {
                        "name": name.strip(),
                        "description": description.strip(),
                        "command": command.strip(),
                        "require_output": require_output.strip(),
                        "required_software": required_software.strip(),
                        "locked": locked.strip(),
                        "role": role.strip(),
                        "type": job_type.strip(),
                        "vbuser_id": vbuser_id.strip(),
                    }
                    if frequency:
                        payload["frequency"] = frequency
                    ok, data, error = client.create_job(payload)
                    if ok:
                        st.success("Задание создано")
                        st.experimental_rerun()
                    else:
                        st.error(error or data)


def job_list(role_names):
    ok, data, error = client.get_jobs()
    if not ok:
        st.error(error or data)
        return
    if not data:
        st.info("Нет заданий")
        return
    for job in data:
        name = job.get("name", "")
        with st.expander(name or "Задание"):
            st.markdown(f"Описание: {job.get('description', '')}")
            st.markdown(f"Команда: `{job.get('command', '')}`")
            st.markdown(f"Частота: {job.get('frequency', '')}")
            st.markdown(f"Роль: {job.get('role', '')}")
            with st.form(f"edit_job_{name}"):
                st.text_input("Имя", value=name, disabled=True)
                description = st.text_area("Описание", value=job.get("description", ""))
                command = st.text_area("Команда", value=job.get("command", ""))
                frequency_val = job.get("frequency") or ""
                frequency = st.selectbox(
                    "Частота",
                    options=["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"],
                    index=["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"].index(frequency_val) if frequency_val in ["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"] else 0,
                    key=f"freq_{name}",
                    format_func=lambda x: "Не выбрано" if x == "" else x,
                )
                require_output = st.text_input("Требуется вывод", value=job.get("require_output", ""))
                required_software = st.text_input("Требуемое ПО", value=job.get("required_software", ""))
                locked = st.text_input("Locked", value=job.get("locked", ""))
                role_val = job.get("role", "")
                role = st.selectbox("Роль", options=["" ] + role_names, index=(["" ] + role_names).index(role_val) if role_val in role_names else 0, key=f"role_job_{name}")
                job_type = st.text_input("Тип", value=job.get("type", ""))
                vbuser_id = st.text_input("VBUser ID", value=job.get("vbuser_id", ""))
                submit = st.form_submit_button("Сохранить")
                if submit:
                    if not command.strip():
                        st.error("Команда обязательна")
                    else:
                        payload = {}
                        if description.strip() != job.get("description", ""):
                            payload["description"] = description.strip()
                        if command.strip() != job.get("command", ""):
                            payload["command"] = command.strip()
                        if frequency:
                            payload["frequency"] = frequency
                        if require_output.strip() != job.get("require_output", ""):
                            payload["require_output"] = require_output.strip()
                        if required_software.strip() != job.get("required_software", ""):
                            payload["required_software"] = required_software.strip()
                        if locked.strip() != job.get("locked", ""):
                            payload["locked"] = locked.strip()
                        if role.strip() != job.get("role", ""):
                            payload["role"] = role.strip()
                        if job_type.strip() != job.get("type", ""):
                            payload["type"] = job_type.strip()
                        if vbuser_id.strip() != job.get("vbuser_id", ""):
                            payload["vbuser_id"] = vbuser_id.strip()
                        if not payload:
                            st.info("Нет изменений")
                        else:
                            ok_update, updated, err_update = client.update_job(name, payload)
                            if ok_update:
                                st.success("Задание обновлено")
                                st.experimental_rerun()
                            else:
                                st.error(err_update or updated)
            delete_cols = st.columns(2)
            with delete_cols[0]:
                if st.button("Удалить", key=f"delete_job_{name}"):
                    st.session_state["job_delete"] = name
            with delete_cols[1]:
                if st.session_state.get("job_delete") == name:
                    if st.button("Подтвердить удаление", key=f"confirm_job_{name}"):
                        ok_del, resp, err_del = client.delete_job(name)
                        st.session_state["job_delete"] = ""
                        if ok_del:
                            st.success("Задание удалено")
                            st.experimental_rerun()
                        else:
                            st.error(err_del or resp)


def render_tabs():
    role_names = []
    ok_roles, data_roles, error_roles = client.get_roles()
    if ok_roles and data_roles:
        role_names = [item.get("name", "") for item in data_roles if item.get("name")]
    tabs = st.tabs(["Roles", "uDPU", "Jobs"])
    with tabs[0]:
        role_create_form()
        role_list()
    with tabs[1]:
        udpu_create_form(role_names)
        st.button("Обновить uDPU", key="refresh_udpu", on_click=st.experimental_rerun)
        udpu_list(role_names)
    with tabs[2]:
        job_create_form(role_names)
        job_list(role_names)


init_state()
if not st.session_state.get("auth"):
    login_view()
    st.stop()
show_header()
render_tabs()
