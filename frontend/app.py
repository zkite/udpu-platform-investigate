import json
import os
import urllib.error
import urllib.request

import streamlit as st

try:
    import pandas as pd
except Exception:
    pd = None


API_BASE_URL = os.getenv("API_BASE_URL", "http://api-service:8888")
API_PREFIX = "/api/v1.0"

st.set_page_config(page_title="UDPU Admin", layout="wide")


# -----------------------------
# Styling
# -----------------------------
st.html(
    """
<style>
:root {
    color-scheme: light;
    --app-bg: #f5f6f8;
    --topbar-h: 3.25rem; /* fixed topbar height to align sidebar + main */
}

/* Force ONE background everywhere (including top header area) */
html, body { background: var(--app-bg) !important; }

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stSidebar"],
[data-testid="stSidebarContent"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    background: var(--app-bg) !important;
}


/* Center content */
.main .block-container {
    padding-top: 0;
    max-width: 1140px;
    margin-left: auto;
    margin-right: auto;
}

/* Sidebar topbar spacer to align with main (Logout + gap) */
.st-key-sidebar_topbar {
    height: calc(var(--topbar-h) + 0.75rem + 0.5rem); 
    margin-bottom: 0;
}

/* Headings */
h1, h2, h3, h4 { color: #1a1d24; }

/* Top bar above shell (Logout) */
.st-key-topbar {
    height: var(--topbar-h);
    display: flex;
    align-items: center;
    margin-bottom: 0.75rem; /* gap between Logout and shell */
}

/* Shell */
.st-key-app_shell {
    background: #ffffff;
    border-radius: 18px;
    padding: 1.25rem 2rem 2rem 2rem;
    box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
}

/* Content cards (wide, e.g. action panels) */
.st-key-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

/* Narrow cards (forms, role editor) */
.st-key-card_narrow {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    max-width: 520px; /* slightly wider to fit interfaces editor */
    margin-left: 0;
    margin-right: auto;
}

/* ---- LOGIN CENTERING ---- */
.st-key-login_center {
    min-height: calc(100vh - 5.5rem); /* compensates for header area */
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Separate card style for login so other narrow cards stay left-aligned */
.st-key-login_card {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    max-width: 520px;
    width: 100%;
    margin: 0 auto;
}

/* Section card */
.st-key-section {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.5rem 1.75rem;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    margin-bottom: 1.5rem;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 14px;
    overflow: hidden;
}

/* ---- Sidebar vertical tabs ---- */
.st-key-nav_tabs {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    margin-top: calc(var(--topbar-h) + 0.75rem + 1.75rem) !important;
}

.st-key-nav_tabs .stButton > button {
    width: 100%;
    text-align: left;
    padding: 0.9rem 1rem;
    border-radius: 14px;
    border: 1px solid #e7ebf2;
    background: #ffffff;
    font-size: 1.05rem;
    font-weight: 650;
    color: #1a1d24;
    box-shadow: 0 6px 14px rgba(15, 23, 42, 0.06);
}

.st-key-nav_tabs .stButton > button:hover {
    border-color: #d7deea;
    box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
}

/* Active tab */
.st-key-nav_tabs .stButton > button[kind="primary"] {
    background: #eef2ff;
    border-color: #cdd5ff;
    color: #27329a;
}

/* ---- Hard-hide Deploy (CSS fallback) ---- */
[data-testid="stDeployButton"],
[data-testid="stAppDeployButton"],
button[title="Deploy"],
a[title="Deploy"],
.stAppDeployButton,
#MainMenu,
footer,
[data-testid="stStatusWidget"] {
    display: none !important;
    visibility: hidden !important;
}
</style>
"""
)


# -----------------------------
# API helpers
# -----------------------------
def api_request(method: str, path: str, payload=None):
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


def fetch_roles():
    roles = api_request("GET", "/roles")
    if isinstance(roles, list):
        return roles
    return []


def fetch_role(name: str):
    return api_request("GET", f"/roles/{name}")


# -----------------------------
# State
# -----------------------------
def ensure_state():
    auth_value = st.query_params.get("auth", "0")
    if isinstance(auth_value, list):
        auth_value = auth_value[0] if auth_value else "0"
    auth_flag = str(auth_value) == "1"

    st.session_state.setdefault("authenticated", auth_flag)
    st.session_state.setdefault("active_tab", "Roles")
    st.session_state.setdefault("roles_view", "list")  # list | detail | add | edit
    st.session_state.setdefault("selected_role", None)


def do_logout():
    st.session_state.authenticated = False
    st.session_state.active_tab = "Roles"
    st.session_state.roles_view = "list"
    st.session_state.selected_role = None

    try:
        if "auth" in st.query_params:
            del st.query_params["auth"]
    except Exception:
        st.query_params["auth"] = "0"

    st.rerun()


def set_active_tab(tab: str):
    st.session_state.active_tab = tab
    st.rerun()


# -----------------------------
# Dialogs
# -----------------------------
@st.dialog("Delete role?")
def confirm_delete_role(role_name: str):
    st.write(f"Role: **{role_name}**")
    st.warning("This action cannot be undone.")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Delete", type="primary", use_container_width=True):
            try:
                with st.spinner("Deleting role..."):
                    api_request("DELETE", f"/roles/{role_name}")
                st.toast("Role deleted")
                st.session_state.roles_view = "list"
                st.session_state.selected_role = None
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))


# -----------------------------
# UI: Login (centered)
# -----------------------------
def render_login():
    with st.container(key="login_center"):
        with st.container(key="login_card"):
            st.title("Login")

            with st.form("login", border=False):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in", use_container_width=True)

            if submitted:
                if username == "admin" and password == "admin":
                    st.query_params["auth"] = "1"
                    st.session_state.authenticated = True
                    st.rerun()
                st.error("Invalid credentials")


# -----------------------------
# Roles helpers
# -----------------------------
def _interfaces_defaults(role: dict) -> dict:
    interfaces = (role or {}).get("interfaces") or {}
    mgmt = interfaces.get("management_vlan") or {}
    ghn_ports = interfaces.get("ghn_ports") or []
    if not isinstance(ghn_ports, list):
        ghn_ports = []
    return {
        "management_vlan_interface": str(mgmt.get("interface", "vlan") or "vlan"),
        "ghn_ports": ghn_ports,
    }


def _normalize_ghn_ports(ports):
    if not isinstance(ports, list):
        return []
    out = []
    for p in ports:
        if not isinstance(p, dict):
            continue
        out.append(
            {
                "ghn_interface": str(p.get("ghn_interface", "") or ""),
                "lcmp_interface": str(p.get("lcmp_interface", "") or ""),
                "vb": bool(p.get("vb", False)),
            }
        )
    cleaned = []
    for p in out:
        if p["ghn_interface"] or p["lcmp_interface"] or p["vb"]:
            cleaned.append(p)
    return cleaned


# -----------------------------
# UI: Roles
# -----------------------------
def render_role_detail():
    name = st.session_state.selected_role
    if not name:
        st.session_state.roles_view = "list"
        st.rerun()

    top = st.columns([1, 6, 2, 2])
    if top[0].button("← Back", use_container_width=True):
        st.session_state.roles_view = "list"
        st.rerun()
    if top[2].button("Edit", use_container_width=True):
        st.session_state.roles_view = "edit"
        st.rerun()
    if top[3].button("Delete", use_container_width=True):
        confirm_delete_role(name)

    try:
        with st.spinner("Loading role..."):
            role = fetch_role(name)
    except RuntimeError as exc:
        st.error(str(exc))
        return

    st.subheader(role.get("name", ""))
    st.write(role.get("description", ""))

    interfaces = (role.get("interfaces") or {})
    mgmt_iface = (interfaces.get("management_vlan") or {}).get("interface", "")
    ports = interfaces.get("ghn_ports") or []

    c1, c2 = st.columns(2)
    c1.metric("Management VLAN", mgmt_iface or "-")
    c2.metric("GHN ports", str(len(ports) if isinstance(ports, list) else 0))

    if isinstance(ports, list) and ports:
        if pd is not None:
            st.markdown("#### GHN ports")
            dfp = pd.DataFrame(_normalize_ghn_ports(ports))
            st.dataframe(dfp, use_container_width=True, hide_index=True)
        else:
            st.markdown("#### GHN ports")
            st.code(json.dumps(_normalize_ghn_ports(ports), indent=2), language="json")


def render_role_form(title: str, role=None):
    defaults = role or {}
    st.subheader(title)

    iface_defaults = _interfaces_defaults(defaults)

    with st.container(key="card_narrow"):
        with st.form(f"form-{title}", border=False):
            name = st.text_input("Name", value=defaults.get("name", ""))
            description = st.text_area("Description", value=defaults.get("description", ""))

            st.markdown("##### Interfaces")

            management_vlan_interface = st.text_input(
                "Management VLAN interface",
                value=iface_defaults["management_vlan_interface"],
                help='Example: "vlan"',
            )

            ghn_ports_editor_value = iface_defaults["ghn_ports"]

            if pd is not None:
                ports_df = pd.DataFrame(_normalize_ghn_ports(ghn_ports_editor_value))
                if ports_df.empty:
                    ports_df = pd.DataFrame(
                        [{"ghn_interface": "", "lcmp_interface": "", "vb": True}]
                    )

                edited_ports = st.data_editor(
                    ports_df,
                    use_container_width=True,
                    num_rows="dynamic",
                    hide_index=True,
                    column_config={
                        "ghn_interface": st.column_config.TextColumn("ghn_interface"),
                        "lcmp_interface": st.column_config.TextColumn("lcmp_interface"),
                        "vb": st.column_config.CheckboxColumn("vb"),
                    },
                    key=f"ghn_ports_editor_{title}",
                )
                ghn_ports = _normalize_ghn_ports(edited_ports.to_dict(orient="records"))
            else:
                st.caption("GHN ports (JSON list)")
                raw = st.text_area(
                    "ghn_ports",
                    value=json.dumps(_normalize_ghn_ports(ghn_ports_editor_value), indent=2),
                    height=180,
                )
                try:
                    ghn_ports = _normalize_ghn_ports(json.loads(raw))
                except Exception:
                    ghn_ports = None

            save = st.form_submit_button("Save", use_container_width=True)

        if st.button("Cancel", use_container_width=True):
            st.session_state.roles_view = "list"
            st.rerun()

    if not save:
        return

    if not name.strip():
        st.error("Role name is required")
        return

    if pd is None and ghn_ports is None:
        st.error("Invalid JSON in ghn_ports")
        return

    payload = {
        "name": name.strip(),
        "description": description,
        "interfaces": {
            "management_vlan": {"interface": management_vlan_interface.strip() or "vlan"},
            "ghn_ports": ghn_ports or [],
        },
    }

    try:
        if role:
            with st.spinner("Updating role..."):
                updated = api_request("PATCH", f"/roles/{role.get('name','')}", payload)
            st.session_state.selected_role = (updated or {}).get("name", payload["name"])
            st.session_state.roles_view = "detail"
            st.toast("Role updated")
        else:
            with st.spinner("Creating role..."):
                api_request("POST", "/roles", payload)
            st.session_state.roles_view = "list"
            st.toast("Role created")
        st.rerun()
    except RuntimeError as exc:
        st.error(str(exc))


def render_role_list():
    st.title("Roles")

    _, add_col = st.columns([7, 2])
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

    if pd is not None:
        rows = []
        for r in roles:
            interfaces = (r.get("interfaces") or {})
            mgmt_iface = (interfaces.get("management_vlan") or {}).get("interface", "")
            ports = interfaces.get("ghn_ports") or []
            if not isinstance(ports, list):
                ports = []
            vb_any = any(bool(p.get("vb", False)) for p in ports if isinstance(p, dict))

            rows.append(
                {
                    "Name": r.get("name", ""),
                    "Description": r.get("description", ""),
                    "Management VLAN": mgmt_iface or "",
                    "GHN ports": len(ports),
                    "VB": vb_any,
                }
            )

        df = pd.DataFrame(rows)

        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
        )

        selected_idx = None
        if event and getattr(event, "selection", None):
            rows_sel = event.selection.get("rows", [])
            if rows_sel:
                selected_idx = rows_sel[0]

        with st.container(key="card"):
            st.markdown("#### Actions")
            if selected_idx is None:
                st.caption("Select a role in the table to enable actions.")
                return

            selected_name = str(df.iloc[selected_idx]["Name"])
            st.write(f"Selected: **{selected_name}**")

            a1, a2, a3 = st.columns(3)
            if a1.button("Open", use_container_width=True):
                st.session_state.selected_role = selected_name
                st.session_state.roles_view = "detail"
                st.rerun()
            if a2.button("Edit", use_container_width=True):
                st.session_state.selected_role = selected_name
                st.session_state.roles_view = "edit"
                st.rerun()
            if a3.button("Delete", use_container_width=True):
                confirm_delete_role(selected_name)

    else:
        for r in roles:
            c1, c2, c3 = st.columns([3, 5, 2])
            c1.write(r.get("name", ""))
            c2.write(r.get("description", ""))
            if c3.button("Open", key=f"open-{r.get('name','')}"):
                st.session_state.selected_role = r.get("name")
                st.session_state.roles_view = "detail"
                st.rerun()


def render_roles():
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
        render_role_form("Edit role", role=role)
        return

    render_role_list()


# -----------------------------
# Placeholders
# -----------------------------
def render_placeholder(title: str):
    st.title(title)
    with st.container(key="section"):
        st.markdown("### Coming soon")


# -----------------------------
# App
# -----------------------------
def render_app():
    with st.sidebar:

        with st.container(key="nav_tabs"):
            current = st.session_state.active_tab

            if st.button("Roles", use_container_width=True, type="primary" if current == "Roles" else "secondary"):
                set_active_tab("Roles")
            if st.button("VBCE", use_container_width=True, type="primary" if current == "VBCE" else "secondary"):
                set_active_tab("VBCE")
            if st.button("UDPU", use_container_width=True, type="primary" if current == "UDPU" else "secondary"):
                set_active_tab("UDPU")
            if st.button("Jobs", use_container_width=True, type="primary" if current == "Jobs" else "secondary"):
                set_active_tab("Jobs")

    selection = st.session_state.active_tab

    # Logout above shell, aligned to top-right of main area
    with st.container(key="topbar"):
        _, right = st.columns([10, 2])
        with right:
            if st.button("Logout", use_container_width=True):
                do_logout()

    with st.container(key="app_shell"):
        if selection == "Roles":
            render_roles()
        elif selection == "VBCE":
            render_placeholder("VBCE")
        elif selection == "UDPU":
            render_placeholder("UDPU")
        elif selection == "Jobs":
            render_placeholder("Jobs")


ensure_state()

if not st.session_state.authenticated:
    render_login()
else:
    render_app()
