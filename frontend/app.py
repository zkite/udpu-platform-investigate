import json
import os
import urllib.error
import urllib.request

import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://api-service:8888")
API_PREFIX = "/api/v1.0"

st.set_page_config(page_title="UDPU Admin", layout="wide")

st.markdown(
    """
    <style>
    :root {
        color-scheme: light;
    }
    .stApp {
        background: #f5f6f8;
    }
    .main .block-container {
        padding-top: 2.5rem;
        max-width: 1140px;
        margin-left: auto;
        margin-right: auto;
        width: 100%;
    }
    h1, h2, h3, h4 {
        color: #1a1d24;
    }
    .app-shell {
        background: #ffffff;
        border-radius: 18px;
        padding: 1.5rem 2rem 2rem 2rem;
        box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
    }
    .page-intro {
        color: #5a6472;
        margin-top: -0.5rem;
        margin-bottom: 1.5rem;
        font-size: 0.95rem;
    }
    .content-card {
        width: 360px;
        margin-left: 0;
        margin-right: auto;
        background: #ffffff;
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    }
    .content-card .stTextInput,
    .content-card .stTextArea,
    .content-card .stCheckbox,
    .content-card .stButton {
        max-width: 360px;
    }
    .section-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 1.5rem 1.75rem;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
        margin-bottom: 1.5rem;
    }
    .sidebar .sidebar-content { padding-top: 2rem; }
    .role-row { padding: 0.5rem 0; border-bottom: 1px solid #eef1f5; }
    .role-header { font-weight: 600; color: #4a5568; text-transform: uppercase; letter-spacing: 0.04em; font-size: 0.75rem; }
    .pill {
        display: inline-block;
        background: #eef2ff;
        color: #3949ab;
        border-radius: 999px;
        padding: 0.2rem 0.7rem;
        font-size: 0.75rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_request(method, path, payload=None):
    if API_BASE_URL.endswith(API_PREFIX):
        url = f"{API_BASE_URL}{path}"
    else:
        url = f"{API_BASE_URL}{API_PREFIX}{path}"
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
    query_value = st.query_params.get("auth", "0")
    auth_value = query_value[0] if isinstance(query_value, list) and query_value else query_value
    auth_flag = auth_value == "1"
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = auth_flag
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Roles"
    if "roles_view" not in st.session_state:
        st.session_state.roles_view = "list"
    if "selected_role" not in st.session_state:
        st.session_state.selected_role = None


def render_login():
    st.title("Login")
    st.caption("Use your admin credentials to access the console.")
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    st.markdown("</div>", unsafe_allow_html=True)
    if submitted:
        if username == "admin" and password == "admin":
            st.query_params["auth"] = "1"
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
    st.markdown(
        "<div class='page-intro'>Manage access policies, permissions, and system capabilities.</div>",
        unsafe_allow_html=True,
    )
    _, add_col = st.columns([5, 1])
    if add_col.button("Add role", use_container_width=True):
        st.session_state.roles_view = "add"
        st.session_state.selected_role = None
        st.rerun()

    try:
        with st.spinner("Loading roles..."):
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
                with st.spinner("Deleting role..."):
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
        with st.spinner("Loading role..."):
            role = fetch_role(name)
    except RuntimeError as exc:
        st.error(str(exc))
        return
    st.subheader(role.get("name", ""))
    st.write(role.get("description", ""))
    st.markdown(
        f"**Wireguard tunnel:** {'Yes' if role.get('wireguard_tunnel') else 'No'}"
    )
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
        if not name.strip():
            st.error("Role name is required")
            return
        payload = {
            "name": name,
            "description": description,
            "wireguard_tunnel": wireguard_tunnel,
            "job_control": job_control,
        }
        try:
            if role:
                with st.spinner("Updating role..."):
                    updated = api_request("PATCH", f"/roles/{role.get('name','')}", payload)
                st.session_state.selected_role = updated.get("name", name)
                st.session_state.roles_view = "detail"
            else:
                with st.spinner("Creating role..."):
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
    st.markdown(
        "<div class='section-card'><span class='pill'>Coming soon</span>"
        "<h3 style='margin-top: 1rem;'>This section is under development</h3>"
        "<p class='page-intro'>We are preparing this area. Check back soon for updates.</p></div>",
        unsafe_allow_html=True,
    )


def render_app():
    st.sidebar.markdown("### Navigation")
    selection = st.sidebar.radio(
        "",
        ["Roles", "VBCE", "UDPU", "Jobs"],
        index=0,
    )
    st.session_state.active_tab = selection

    st.markdown("<div class='app-shell'>", unsafe_allow_html=True)
    if selection == "Roles":
        render_roles()
        st.markdown("</div>", unsafe_allow_html=True)
        return
    if selection == "VBCE":
        render_placeholder("VBCE")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    if selection == "UDPU":
        render_placeholder("UDPU")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    if selection == "Jobs":
        render_placeholder("Jobs")
        st.markdown("</div>", unsafe_allow_html=True)
        return


ensure_state()

if not st.session_state.authenticated:
    render_login()
else:
    render_app()
