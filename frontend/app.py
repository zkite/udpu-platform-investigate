import json
import os
import urllib.error
import urllib.request

import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://api-service:8888")

st.set_page_config(page_title="UDPU Admin", layout="wide")

st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 2rem;
        max-width: 1100px;
        margin-left: auto;
        margin-right: auto;
        width: 100%;
    }
    .content-card {
        max-width: 820px;
        width: 100%;
        margin-left: 0;
        margin-right: auto;
    }
    .content-card .stTextInput,
    .content-card .stTextArea,
    .content-card .stCheckbox,
    .content-card .stButton {
        max-width: 820px;
    }
    .sidebar .sidebar-content { padding-top: 2rem; }
    .role-row { padding: 0.25rem 0; border-bottom: 1px solid #e6e6e6; }
    .role-header { font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_request(method, path, payload=None):
    url = f"{API_BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8")
        try:
            detail = json.loads(message)
        except json.JSONDecodeError:
            detail = {"message": message}
        raise RuntimeError(detail.get("message", "Request failed")) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("API is unavailable") from exc


def ensure_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Roles"
    if "roles_view" not in st.session_state:
        st.session_state.roles_view = "list"
    if "selected_role" not in st.session_state:
        st.session_state.selected_role = None


def render_login():
    st.title("Login")
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    st.markdown("</div>", unsafe_allow_html=True)
    if submitted:
        if username == "admin" and password == "admin":
            st.session_state.authenticated = True
            st.rerun()
        st.error("Invalid credentials")


def fetch_roles():
    roles = api_request("GET", "/roles")
    if roles is None:
        return []
    if isinstance(roles, list):
        return roles
    return []


def fetch_role(name):
    return api_request("GET", f"/roles/{name}")


def render_role_list():
    st.markdown("### Roles")
    _, add_col = st.columns([5, 1])
    if add_col.button("Add role", use_container_width=True):
        st.session_state.roles_view = "add"
        st.session_state.selected_role = None
        st.rerun()

    try:
        roles = fetch_roles()
    except RuntimeError as exc:
        st.error(str(exc))
        return

    if not roles:
        st.info("No roles found")
        return

    header_cols = st.columns([3, 4, 2])
    header_cols[0].markdown("<div class='role-header'>Name</div>", unsafe_allow_html=True)
    header_cols[1].markdown("<div class='role-header'>Description</div>", unsafe_allow_html=True)
    header_cols[2].markdown("<div class='role-header'>Actions</div>", unsafe_allow_html=True)

    for role in roles:
        row_cols = st.columns([3, 4, 2])
        if row_cols[0].button(role.get("name", ""), key=f"open-{role.get('name','')}"):
            st.session_state.roles_view = "detail"
            st.session_state.selected_role = role.get("name")
            st.rerun()
        row_cols[1].write(role.get("description", ""))
        edit_col, delete_col = row_cols[2].columns(2)
        if edit_col.button("Edit", key=f"edit-{role.get('name','')}"):
            st.session_state.roles_view = "edit"
            st.session_state.selected_role = role.get("name")
            st.rerun()
        if delete_col.button("Delete", key=f"delete-{role.get('name','')}"):
            try:
                api_request("DELETE", f"/roles/{role.get('name','')}")
                st.success("Role deleted")
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))


def render_role_detail():
    name = st.session_state.selected_role
    if not name:
        st.session_state.roles_view = "list"
        st.rerun()
    if st.button("Back to roles"):
        st.session_state.roles_view = "list"
        st.rerun()
    try:
        role = fetch_role(name)
    except RuntimeError as exc:
        st.error(str(exc))
        return
    st.subheader(role.get("name", ""))
    st.write(role.get("description", ""))
    st.markdown(f"**Wireguard tunnel:** {'Yes' if role.get('wireguard_tunnel') else 'No'}")
    st.markdown(f"**Job control:** {'Yes' if role.get('job_control') else 'No'}")


def render_role_form(title, role=None):
    st.markdown(f"### {title}")
    defaults = role or {}
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    with st.form(title):
        name = st.text_input("Name", value=defaults.get("name", ""))
        description = st.text_area("Description", value=defaults.get("description", ""))
        wireguard_tunnel = st.checkbox("Wireguard tunnel", value=defaults.get("wireguard_tunnel", False))
        job_control = st.checkbox("Job control", value=defaults.get("job_control", False))
        submitted = st.form_submit_button("Save")
    st.markdown("</div>", unsafe_allow_html=True)
    if submitted:
        payload = {
            "name": name,
            "description": description,
            "wireguard_tunnel": wireguard_tunnel,
            "job_control": job_control,
        }
        try:
            if role:
                updated = api_request("PATCH", f"/roles/{role.get('name','')}", payload)
                st.session_state.selected_role = updated.get("name", name)
                st.session_state.roles_view = "detail"
            else:
                api_request("POST", "/roles", payload)
                st.session_state.roles_view = "list"
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))
    if st.button("Cancel"):
        st.session_state.roles_view = "list"
        st.rerun()


def render_roles():
    st.title("Roles")
    view = st.session_state.roles_view
    if view == "detail":
        render_role_detail()
        return
    if view == "add":
        render_role_form("Add role")
        return
    if view == "edit":
        name = st.session_state.selected_role
        if not name:
            st.session_state.roles_view = "list"
            st.rerun()
        try:
            role = fetch_role(name)
        except RuntimeError as exc:
            st.error(str(exc))
            return
        render_role_form("Edit role", role)
        return
    render_role_list()


def render_placeholder(title):
    st.title(title)
    st.write("Section is under development")


def render_app():
    st.sidebar.markdown("### Navigation")
    selection = st.sidebar.radio(
        "",
        ["Roles", "VBCE", "UDPU", "Jobs"],
        index=0,
    )
    st.session_state.active_tab = selection

    if selection == "Roles":
        render_roles()
        return
    if selection == "VBCE":
        render_placeholder("VBCE")
        return
    if selection == "UDPU":
        render_placeholder("UDPU")
        return
    if selection == "Jobs":
        render_placeholder("Jobs")
        return


ensure_state()

if not st.session_state.authenticated:
    render_login()
else:
    render_app()
