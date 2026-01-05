import json
import streamlit as st

from client.api_client import ApiClient, ApiError
from ui.components import inject_css, render_card, render_json_response, render_error, render_nav

st.set_page_config(page_title="Roles", layout="wide", menu_items={"Get help": None, "Report a bug": None, "About": None})

inject_css(st.session_state.get("theme", "dark"))

def require_auth():
    if not st.session_state.get("authenticated"):
        st.error("Sign in required")
        if st.button("Go to login"):
            st.switch_page("app.py")
        st.stop()


def get_client():
    return ApiClient(base_url=st.session_state.get("api_base_url"))


def create_role_section():
    def body():
        with st.form("create_role"):
            name = st.text_input("Role name")
            description = st.text_area("Description")
            wireguard = st.checkbox("Wireguard tunnel", value=False)
            job_control = st.checkbox("Job control", value=False)
            interfaces_raw = st.text_area("Interfaces JSON (optional)", value="", height=120)
            submitted = st.form_submit_button("Create")
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
                        st.error("Invalid JSON")
                        return
                try:
                    data = get_client().post("/roles", payload)
                    st.success("Created")
                    render_json_response(data)
                except ApiError as e:
                    render_error(e)
    render_card("Create role", body)


def clone_role_section():
    def body():
        with st.form("clone_role"):
            name = st.text_input("Source role")
            new_name = st.text_input("New role name")
            submitted = st.form_submit_button("Clone")
            if submitted:
                payload = {"name": name.strip(), "new_role_name": new_name.strip()}
                try:
                    data = get_client().post("/roles/clone", payload)
                    st.success("Cloned")
                    render_json_response(data)
                except ApiError as e:
                    render_error(e)
    render_card("Clone role", body)


def list_roles_section():
    def body():
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Refresh"):
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
            st.info("No roles")
            return
        st.dataframe(roles, use_container_width=True)
        for role in roles:
            with st.expander(role.get("name", "")):
                st.json(role)
                with st.form(f"update_{role.get('name')}"):
                    new_name = st.text_input("Name", value=role.get("name", ""))
                    description = st.text_area("Description", value=role.get("description", ""))
                    wireguard = st.checkbox("Wireguard", value=bool(role.get("wireguard_tunnel")))
                    job_control = st.checkbox("Job control", value=bool(role.get("job_control")))
                    submitted = st.form_submit_button("Update")
                    if submitted:
                        payload = {
                            "name": new_name.strip(),
                            "description": description,
                            "wireguard_tunnel": wireguard,
                            "job_control": job_control,
                        }
                        try:
                            data = get_client().patch(f"/roles/{role.get('name')}", payload)
                            st.success("Updated")
                            render_json_response(data)
                            st.session_state["roles_reload"] = True
                        except ApiError as e:
                            render_error(e)
                with st.form(f"delete_{role.get('name')}"):
                    confirm = st.text_input("Type name to delete", value="")
                    submitted = st.form_submit_button("Delete")
                    if submitted and confirm == role.get("name"):
                        try:
                            data = get_client().delete(f"/roles/{role.get('name')}")
                            st.warning("Deleted")
                            render_json_response(data)
                            st.session_state["roles_reload"] = True
                        except ApiError as e:
                            render_error(e)
    render_card("Roles list", body)


def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.ws_log = []
    st.session_state.ws_connected = False
    st.switch_page("app.py")


def page():
    require_auth()
    content = render_nav("Roles")
    if st.session_state.pop("nav_logout", False):
        logout()
    with content:
        st.title("Roles")
        create_role_section()
        clone_role_section()
        list_roles_section()


page()
