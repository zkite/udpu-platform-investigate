import streamlit as st
from services.api_client import APIClient

st.set_page_config(page_title="uDPU Console", layout="wide")
st.markdown(
    """
    <style>
    .block-container { max-width: 1000px; margin: 0 auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

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
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in")
        if submit:
            if user == "admin" and pwd == "admin":
                st.session_state["auth"] = True
                st.session_state["username"] = user
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")


def logout_action():
    st.session_state["auth"] = False
    st.session_state["username"] = ""
    st.rerun()


def show_header():
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown(f"**User:** {st.session_state['username']}")
    with cols[1]:
        st.button("Log out", on_click=logout_action, type="primary")
    st.divider()


def role_create_form():
    with st.expander("Create role"):
        with st.form("create_role_form"):
            name = st.text_input("Name")
            description = st.text_area("Description")
            wireguard_tunnel = st.checkbox("Wireguard tunnel")
            job_control = st.checkbox("Job control")
            submit = st.form_submit_button("Create")
            if submit:
                if not name.strip() or not description.strip():
                    st.error("Name and description are required")
                else:
                    payload = {
                        "name": name.strip(),
                        "description": description.strip(),
                        "wireguard_tunnel": wireguard_tunnel,
                        "job_control": job_control,
                    }
                    ok, data, error = client.create_role(payload)
                    if ok:
                        st.success("Role created")
                        st.rerun()
                    else:
                        st.error(error or data)


def role_list():
    ok, data, error = client.get_roles()
    if not ok:
        st.error(error or data)
        return
    if not data:
        st.info("No roles")
        return
    for item in data:
        name = item.get("name", "")
        with st.expander(name or "Role"):
            st.markdown(f"**Description:** {item.get('description', '')}")
            st.markdown(f"Wireguard: {'Yes' if item.get('wireguard_tunnel') else 'No'}")
            st.markdown(f"Job control: {'Yes' if item.get('job_control') else 'No'}")
            with st.form(f"edit_role_{name}"):
                st.text_input("Name", value=name, disabled=True)
                description = st.text_area("Description", value=item.get("description", ""))
                wireguard_tunnel = st.checkbox("Wireguard tunnel", value=item.get("wireguard_tunnel", False))
                job_control = st.checkbox("Job control", value=item.get("job_control", False))
                submit = st.form_submit_button("Save")
                if submit:
                    if not description.strip():
                        st.error("Description is required")
                    else:
                        payload = {
                            "name": name,
                            "description": description.strip(),
                            "wireguard_tunnel": wireguard_tunnel,
                            "job_control": job_control,
                        }
                        ok_update, updated, err_update = client.update_role(name, payload)
                        if ok_update:
                            st.success("Role updated")
                            st.rerun()
                        else:
                            st.error(err_update or updated)
            delete_cols = st.columns(2)
            with delete_cols[0]:
                if st.button("Delete", key=f"delete_role_{name}"):
                    st.session_state["role_delete"] = name
            with delete_cols[1]:
                if st.session_state.get("role_delete") == name:
                    if st.button("Confirm deletion", key=f"confirm_role_{name}"):
                        ok_del, resp, err_del = client.delete_role(name)
                        st.session_state["role_delete"] = ""
                        if ok_del:
                            st.success("Role removed")
                            st.rerun()
                        else:
                            st.error(err_del or resp)


def udpu_create_form(role_names):
    with st.expander("Create uDPU"):
        with st.form("create_udpu_form"):
            location = st.text_input("Location")
            role = st.selectbox("Role", options=[""] + role_names, format_func=lambda x: "Not selected" if x == "" else x)
            upstream_qos = st.text_input("Upstream QoS")
            downstream_qos = st.text_input("Downstream QoS")
            mac_address = st.text_input("MAC address")
            hostname = st.text_input("Hostname")
            submit = st.form_submit_button("Create")
            if submit:
                if not location.strip() or not role.strip() or not upstream_qos.strip() or not downstream_qos.strip():
                    st.error("All required fields must be filled")
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
                        st.success("uDPU created")
                        st.rerun()
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
        st.info("No records")
        return
    for item in items:
        uid = item.get("subscriber_uid", "")
        header = item.get("hostname") or uid or "uDPU"
        with st.expander(header):
            st.markdown(f"UID: {uid}")
            st.markdown(f"Location: {item.get('location', '')}")
            st.markdown(f"MAC: {item.get('mac_address', '')}")
            st.markdown(f"Role: {item.get('role', '')}")
            st.markdown(f"Upstream: {item.get('upstream_qos', '')}")
            st.markdown(f"Downstream: {item.get('downstream_qos', '')}")
            with st.form(f"edit_udpu_{uid}"):
                location = st.text_input("Location", value=item.get("location", ""))
                role_options = ["" ] + role_names
                role_val = item.get("role", "")
                role_index = 0
                if role_val in role_names:
                    role_index = role_options.index(role_val)
                role = st.selectbox("Role", options=role_options, index=role_index, key=f"role_select_{uid}", format_func=lambda x: "Not selected" if x == "" else x)
                upstream_qos = st.text_input("Upstream QoS", value=item.get("upstream_qos", ""))
                downstream_qos = st.text_input("Downstream QoS", value=item.get("downstream_qos", ""))
                mac_address = st.text_input("MAC address", value=item.get("mac_address", ""))
                hostname = st.text_input("Hostname", value=item.get("hostname", ""))
                submit = st.form_submit_button("Save")
                if submit:
                    if not location.strip() or not role.strip() or not upstream_qos.strip() or not downstream_qos.strip():
                        st.error("All required fields must be filled")
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
                            st.success("uDPU updated")
                            st.rerun()
                        else:
                            st.error(err_update or updated)
            delete_cols = st.columns(2)
            with delete_cols[0]:
                if st.button("Delete", key=f"delete_udpu_{uid}"):
                    st.session_state["udpu_delete"] = uid
            with delete_cols[1]:
                if st.session_state.get("udpu_delete") == uid:
                    if st.button("Confirm deletion", key=f"confirm_udpu_{uid}"):
                        ok_del, resp, err_del = client.delete_udpu(uid)
                        st.session_state["udpu_delete"] = ""
                        if ok_del:
                            st.success("uDPU removed")
                            st.rerun()
                        else:
                            st.error(err_del or resp)


def job_create_form(role_names):
    with st.expander("Create job"):
        with st.form("create_job_form"):
            name = st.text_input("Name")
            description = st.text_area("Description")
            command = st.text_area("Command")
            frequency = st.selectbox("Frequency", options=["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"], format_func=lambda x: "Not selected" if x == "" else x)
            require_output = st.text_input("Require output")
            required_software = st.text_input("Required software")
            role = st.selectbox("Role", options=["" ] + role_names)
            locked = st.text_input("Locked")
            job_type = st.text_input("Type", value="common")
            vbuser_id = st.text_input("VBUser ID")
            submit = st.form_submit_button("Create")
            if submit:
                if not name.strip() or not command.strip():
                    st.error("Name and command are required")
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
                        st.success("Job created")
                        st.rerun()
                    else:
                        st.error(error or data)


def job_list(role_names):
    ok, data, error = client.get_jobs()
    if not ok:
        st.error(error or data)
        return
    if not data:
        st.info("No jobs")
        return
    for job in data:
        name = job.get("name", "")
        with st.expander(name or "Job"):
            st.markdown(f"Description: {job.get('description', '')}")
            st.markdown(f"Command: `{job.get('command', '')}`")
            st.markdown(f"Frequency: {job.get('frequency', '')}")
            st.markdown(f"Role: {job.get('role', '')}")
            with st.form(f"edit_job_{name}"):
                st.text_input("Name", value=name, disabled=True)
                description = st.text_area("Description", value=job.get("description", ""))
                command = st.text_area("Command", value=job.get("command", ""))
                frequency_val = job.get("frequency") or ""
                frequency = st.selectbox(
                    "Frequency",
                    options=["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"],
                    index=["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"].index(frequency_val) if frequency_val in ["", "1", "15", "60", "1440", "first_boot", "every_boot", "once"] else 0,
                    key=f"freq_{name}",
                    format_func=lambda x: "Not selected" if x == "" else x,
                )
                require_output = st.text_input("Require output", value=job.get("require_output", ""))
                required_software = st.text_input("Required software", value=job.get("required_software", ""))
                locked = st.text_input("Locked", value=job.get("locked", ""))
                role_val = job.get("role", "")
                role = st.selectbox("Role", options=["" ] + role_names, index=(["" ] + role_names).index(role_val) if role_val in role_names else 0, key=f"role_job_{name}")
                job_type = st.text_input("Type", value=job.get("type", ""))
                vbuser_id = st.text_input("VBUser ID", value=job.get("vbuser_id", ""))
                submit = st.form_submit_button("Save")
                if submit:
                    if not command.strip():
                        st.error("Command is required")
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
                            st.info("No changes")
                        else:
                            ok_update, updated, err_update = client.update_job(name, payload)
                            if ok_update:
                                st.success("Job updated")
                                st.rerun()
                            else:
                                st.error(err_update or updated)
            delete_cols = st.columns(2)
            with delete_cols[0]:
                if st.button("Delete", key=f"delete_job_{name}"):
                    st.session_state["job_delete"] = name
            with delete_cols[1]:
                if st.session_state.get("job_delete") == name:
                    if st.button("Confirm deletion", key=f"confirm_job_{name}"):
                        ok_del, resp, err_del = client.delete_job(name)
                        st.session_state["job_delete"] = ""
                        if ok_del:
                            st.success("Job removed")
                            st.rerun()
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
        st.button("Refresh uDPU", key="refresh_udpu", on_click=st.rerun)
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
