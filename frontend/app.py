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

st.set_page_config(page_title="uDPU Admin", layout="wide")


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


def fetch_vbces():
    vbces = api_request("GET", "/vbces")
    if isinstance(vbces, list):
        return vbces
    return []


def fetch_vbce_locations():
    locations = api_request("GET", "/vbce/locations")
    if isinstance(locations, list):
        return locations
    return []


def fetch_vbce(name):
    return api_request("GET", f"/vbce/{name}")


def fetch_udpu_locations():
    locations = api_request("GET", "/udpu/locations")
    if isinstance(locations, list):
        return locations
    return []


def fetch_udpu_list_by_location(location_id: str):
    udpus = api_request("GET", f"/{location_id}/udpu_list")
    if isinstance(udpus, list):
        return udpus
    return []


def fetch_udpu(subscriber_uid: str):
    return api_request("GET", f"/subscriber/{subscriber_uid}/udpu")

def fetch_udpu_statuses():
    statuses = api_request("GET", "/udpu/status")
    if isinstance(statuses, list):
        return statuses
    return []


def fetch_udpu_status(subscriber_uid):
    return api_request("GET", f"/udpu/{subscriber_uid}/status")

def fetch_udpu_by_mac(mac_address, subscriber_uid="none"):
    if subscriber_uid:
        return api_request("GET", f"/adapter/{mac_address}/udpu?subscriber={subscriber_uid}")
    return api_request("GET", f"/adapter/{mac_address}/udpu")

def update_udpu_bulk(location_id, payload):
    return api_request("PUT", f"/udpu_bulk/{location_id}", payload)

def delete_udpu_by_mac(mac_address):
    return api_request("DELETE", f"/adapter/{mac_address}/udpu")

def post_udpu_status(payload):
    return api_request("POST", "/udpu/status", payload)

def post_unregistered_device(payload):
    return api_request("POST", "/unregistered_device", payload)


def fetch_unregistered_devices():
    devices = api_request("GET", "/unregistered_devices")
    if isinstance(devices, list):
        return devices
    return []


def fetch_jobs():
    jobs = api_request("GET", "/jobs")
    if isinstance(jobs, list):
        return jobs
    return []


def fetch_job(identifier):
    return api_request("GET", f"/jobs/{identifier}")


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
    st.session_state.setdefault("vbce_view", "list")
    st.session_state.setdefault("selected_vbce", None)
    st.session_state.setdefault("udpu_view", "list")
    st.session_state.setdefault("selected_udpu", None)
    st.session_state.setdefault("udpu_location", "")
    st.session_state.setdefault("udpu_mac_lookup", "")
    st.session_state.setdefault("udpu_mac_subscriber", "")
    st.session_state.setdefault("udpu_mac_result", None)
    st.session_state.setdefault("jobs_view", "list")
    st.session_state.setdefault("selected_job", None)


def do_logout():
    st.session_state.authenticated = False
    st.session_state.active_tab = "Roles"
    st.session_state.roles_view = "list"
    st.session_state.selected_role = None
    st.session_state.vbce_view = "list"
    st.session_state.selected_vbce = None
    st.session_state.udpu_view = "list"
    st.session_state.selected_udpu = None
    st.session_state.udpu_location = ""
    st.session_state.jobs_view = "list"
    st.session_state.selected_job = None

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

@st.dialog("Clone role?")
def confirm_clone_role(role_name: str):
    st.write(f"Source role: **{role_name}**")
    new_name = st.text_input("New role name")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Clone", type="primary", use_container_width=True):
            if not new_name.strip():
                st.error("New role name is required")
                return
            try:
                with st.spinner("Cloning role..."):
                    api_request(
                        "POST",
                        "/roles/clone",
                        {"name": role_name, "new_role_name": new_name.strip()},
                    )
                st.toast("Role cloned")
                st.session_state.selected_role = new_name.strip()
                st.session_state.roles_view = "detail"
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))


@st.dialog("Delete VBCE?")
def confirm_delete_vbce(vbce_name):
    st.write(f"VBCE: **{vbce_name}**")
    st.warning("This action cannot be undone.")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Delete", type="primary", use_container_width=True):
            try:
                with st.spinner("Deleting VBCE..."):
                    api_request("DELETE", f"/vbce/{vbce_name}")
                st.toast("VBCE deleted")
                st.session_state.vbce_view = "list"
                st.session_state.selected_vbce = None
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))


@st.dialog("Delete uDPU?")
def confirm_delete_udpu(subscriber_uid: str):
    st.write(f"uDPU: **{subscriber_uid}**")
    st.warning("This action cannot be undone.")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Delete", type="primary", use_container_width=True):
            try:
                with st.spinner("Deleting uDPU..."):
                    api_request("DELETE", f"/subscriber/{subscriber_uid}/udpu")
                st.toast("uDPU deleted")
                st.session_state.udpu_view = "list"
                st.session_state.selected_udpu = None
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))

@st.dialog("Delete job?")
def confirm_delete_job(job_name):
    st.write(f"Job: **{job_name}**")
    st.warning("This action cannot be undone.")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Delete", type="primary", use_container_width=True):
            try:
                with st.spinner("Deleting job..."):
                    api_request("DELETE", f"/jobs/{job_name}")
                st.toast("Job deleted")
                st.session_state.jobs_view = "list"
                st.session_state.selected_job = None
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
        "management_vlan_interface": str(mgmt.get("interface", "br-lan") or "br-lan"),
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
    wireguard_tunnel = bool(role.get("wireguard_tunnel", False))
    job_control = bool(role.get("job_control", False))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Management VLAN", mgmt_iface or "-")
    c2.metric("GHN ports", str(len(ports) if isinstance(ports, list) else 0))
    c3.metric("Wireguard tunnel", "Enabled" if wireguard_tunnel else "Disabled")
    c4.metric("Job control", "Enabled" if job_control else "Disabled")

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
            wireguard_tunnel = st.checkbox(
                "Wireguard tunnel",
                value=bool(defaults.get("wireguard_tunnel", False)),
            )
            job_control = st.checkbox(
                "Job control",
                value=bool(defaults.get("job_control", False)),
            )

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
                        [{"ghn_interface": "", "lcmp_interface": "", "vb": False}]
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
        "wireguard_tunnel": wireguard_tunnel,
        "job_control": job_control,
        "interfaces": {
            "management_vlan": {"interface": management_vlan_interface.strip() or "br-lan"},
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

            a1, a2, a3, a4 = st.columns(4)
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
            if a4.button("Clone", use_container_width=True):
                confirm_clone_role(selected_name)

    else:
        for r in roles:
            c1, c2, c3 = st.columns([3, 5, 2])
            c1.write(r.get("name", ""))
            c2.write(r.get("description", ""))
            if c3.button("Open", key=f"open-{r.get('name','')}"):
                st.session_state.selected_role = r.get("name")
                st.session_state.roles_view = "detail"
                st.rerun()
            if c3.button("Clone", key=f"clone-{r.get('name','')}"):
                confirm_clone_role(r.get("name"))


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


def _vbce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return False


def render_vbce_detail():
    name = st.session_state.selected_vbce
    if not name:
        st.session_state.vbce_view = "list"
        st.rerun()

    top = st.columns([1, 6, 2, 2])
    if top[0].button("← Back", use_container_width=True):
        st.session_state.vbce_view = "list"
        st.rerun()
    if top[2].button("Edit", use_container_width=True):
        st.session_state.vbce_view = "edit"
        st.rerun()
    if top[3].button("Delete", use_container_width=True):
        confirm_delete_vbce(name)

    try:
        with st.spinner("Loading VBCE..."):
            vbce = fetch_vbce(name)
    except RuntimeError as exc:
        st.error(str(exc))
        return

    st.subheader(vbce.get("name", ""))
    st.write(vbce.get("description", ""))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current users", str(vbce.get("current_users", 0)))
    c2.metric("Max users", str(vbce.get("max_users", 0)))
    c3.metric("Available users", str(vbce.get("available_users", 0)))
    c4.metric("Force local", "Enabled" if _vbce_bool(vbce.get("force_local")) else "Disabled")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Empty", "Yes" if _vbce_bool(vbce.get("is_empty")) else "No")
    c6.metric("Full", "Yes" if _vbce_bool(vbce.get("is_full")) else "No")
    c7.metric("IP address", vbce.get("ip_address", "") or "-")
    c8.metric("TCP port", vbce.get("tcp_port", "") or "-")

    with st.container(key="section"):
        st.markdown("#### Details")
        left, right = st.columns(2)
        with left:
            st.write(f"Location ID: **{vbce.get('location_id', '') or '-'}**")
            st.write(f"LQ min rate: **{vbce.get('lq_min_rate', 0)}**")
            st.write(f"LQ max rate: **{vbce.get('lq_max_rate', 0)}**")
        with right:
            st.write(f"LQ mean rate: **{vbce.get('lq_mean_rate', 0)}**")
            st.write(f"Seed idx used: **{vbce.get('seed_idx_used', '') or '-'}**")


def render_vbce_form(title, vbce=None):
    defaults = vbce or {}
    st.subheader(title)

    with st.container(key="card_narrow"):
        with st.form(f"form-{title}", border=False):
            name = st.text_input("Name", value=defaults.get("name", ""), disabled=bool(vbce))
            description = st.text_area("Description", value=defaults.get("description", ""), disabled=bool(vbce))
            location_id = st.text_input("Location ID", value=defaults.get("location_id", ""))
            ip_address = st.text_input("IP address", value=defaults.get("ip_address", ""))
            tcp_port = st.text_input("TCP port", value=defaults.get("tcp_port", ""))
            max_users = st.number_input(
                "Max users",
                min_value=0,
                step=1,
                value=int(defaults.get("max_users", 510) or 0),
            )
            force_local = st.checkbox(
                "Force local",
                value=_vbce_bool(defaults.get("force_local")),
            )
            save = st.form_submit_button("Save", use_container_width=True)

        if st.button("Cancel", use_container_width=True):
            st.session_state.vbce_view = "list"
            st.rerun()

    if not save:
        return

    if not name.strip():
        st.error("VBCE name is required")
        return

    payload = {
        "max_users": int(max_users),
        "ip_address": ip_address.strip(),
        "tcp_port": tcp_port.strip(),
        "location_id": location_id.strip(),
        "force_local": "true" if force_local else "false",
    }

    try:
        if vbce:
            with st.spinner("Updating VBCE..."):
                updated = api_request("PATCH", f"/vbce/{vbce.get('name','')}", payload)
            st.session_state.selected_vbce = (updated or {}).get("name", vbce.get("name"))
            st.session_state.vbce_view = "detail"
            st.toast("VBCE updated")
        else:
            payload.update(
                {
                    "name": name.strip(),
                    "description": description,
                }
            )
            with st.spinner("Creating VBCE..."):
                api_request("POST", "/vbce", payload)
            st.session_state.vbce_view = "list"
            st.toast("VBCE created")
        st.rerun()
    except RuntimeError as exc:
        st.error(str(exc))


def render_vbce_list():
    st.title("VBCE")

    _, add_col = st.columns([7, 2])
    if add_col.button("Add VBCE", use_container_width=True):
        st.session_state.vbce_view = "add"
        st.session_state.selected_vbce = None
        st.rerun()

    try:
        with st.spinner("Loading VBCE..."):
            vbces = fetch_vbces()
    except RuntimeError as exc:
        st.error(str(exc))
        return

    if not vbces:
        st.info("No VBCE found")
        return

    if pd is not None:
        rows = []
        for v in vbces:
            rows.append(
                {
                    "Name": v.get("name", ""),
                    "Description": v.get("description", ""),
                    "Location ID": v.get("location_id", ""),
                    "IP address": v.get("ip_address", ""),
                    "TCP port": v.get("tcp_port", ""),
                    "Current users": v.get("current_users", 0),
                    "Max users": v.get("max_users", 0),
                    "Force local": _vbce_bool(v.get("force_local")),
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
                st.caption("Select a VBCE in the table to enable actions.")
                return

            selected_name = str(df.iloc[selected_idx]["Name"])
            st.write(f"Selected: **{selected_name}**")

            a1, a2, a3 = st.columns(3)
            if a1.button("Open", use_container_width=True):
                st.session_state.selected_vbce = selected_name
                st.session_state.vbce_view = "detail"
                st.rerun()
            if a2.button("Edit", use_container_width=True):
                st.session_state.selected_vbce = selected_name
                st.session_state.vbce_view = "edit"
                st.rerun()
            if a3.button("Delete", use_container_width=True):
                confirm_delete_vbce(selected_name)

    else:
        for v in vbces:
            c1, c2, c3 = st.columns([3, 5, 2])
            c1.write(v.get("name", ""))
            c2.write(v.get("description", ""))
            if c3.button("Open", key=f"open-{v.get('name','')}"):
                st.session_state.selected_vbce = v.get("name")
                st.session_state.vbce_view = "detail"
                st.rerun()


def render_vbce():
    view = st.session_state.vbce_view

    if view == "detail":
        render_vbce_detail()
        return
    if view == "add":
        render_vbce_form("Add VBCE")
        return
    if view == "edit":
        name = st.session_state.selected_vbce
        if not name:
            st.session_state.vbce_view = "list"
            st.rerun()
        try:
            vbce = fetch_vbce(name)
        except RuntimeError as exc:
            st.error(str(exc))
            return
        render_vbce_form("Edit VBCE", vbce=vbce)
        return

    render_vbce_list()


# -----------------------------
# UDPU helpers
# -----------------------------
def _udpu_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return False


def _normalize_location_options(locations):
    options = []
    for location in locations:
        if isinstance(location, dict):
            name = location.get("name")
            if name:
                options.append(str(name))
        elif location is not None:
            options.append(str(location))
    return options


def render_udpu_detail():
    subscriber_uid = st.session_state.selected_udpu
    if not subscriber_uid:
        st.session_state.udpu_view = "list"
        st.rerun()

    top = st.columns([1, 6, 2, 2])
    if top[0].button("← Back", use_container_width=True):
        st.session_state.udpu_view = "list"
        st.rerun()
    if top[2].button("Edit", use_container_width=True):
        st.session_state.udpu_view = "edit"
        st.rerun()
    if top[3].button("Delete", use_container_width=True):
        confirm_delete_udpu(subscriber_uid)

    try:
        with st.spinner("Loading uDPU..."):
            udpu = fetch_udpu(subscriber_uid)
    except RuntimeError as exc:
        st.error(str(exc))
        return

    st.subheader(udpu.get("subscriber_uid", ""))
    st.write(f"Location: **{udpu.get('location', '') or '-'}**")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Role", udpu.get("role", "") or "-")
    c2.metric("Hostname", udpu.get("hostname", "") or "-")
    c3.metric("MAC address", udpu.get("mac_address", "") or "-")
    c4.metric("Wireguard", "Enabled" if _udpu_bool(udpu.get("wg_server_public_key")) else "Disabled")

    with st.container(key="section_provisioning"):
        st.markdown("#### Provisioning")
        left, right = st.columns(2)
        with left:
            st.write(f"Upstream QoS: **{udpu.get('upstream_qos', '') or '-'}**")
            st.write(f"Downstream QoS: **{udpu.get('downstream_qos', '') or '-'}**")
        with right:
            st.write(f"PPPoE username: **{udpu.get('pppoe_username', '') or '-'}**")
            st.write(f"PPPoE password: **{udpu.get('pppoe_password', '') or '-'}**")

    with st.container(key="section_wireguard"):
        st.markdown("#### Wireguard")
        left, right = st.columns(2)
        with left:
            st.write(f"Client IP: **{udpu.get('wg_client_ip', '') or '-'}**")
            st.write(f"Server IP: **{udpu.get('wg_server_ip', '') or '-'}**")
            st.write(f"Server port: **{udpu.get('wg_server_port', '') or '-'}**")
        with right:
            st.write(f"Allowed IPs: **{udpu.get('wg_allowed_ips', '') or '-'}**")
            st.write(f"Routes: **{udpu.get('wg_routes', '') or '-'}**")
            st.write(f"Endpoint: **{udpu.get('endpoint', '') or '-'}**")

    status_data = None
    status_error = None
    try:
        status_data = fetch_udpu_status(subscriber_uid)
    except RuntimeError as exc:
        status_error = str(exc)

    with st.container(key="section"):
        st.markdown("#### Status")
        if status_data:
            st.write(f"State: **{status_data.get('state', '') or '-'}**")
            st.write(f"Status: **{status_data.get('status', '') or '-'}**")
        elif status_error:
            st.caption(f"Status unavailable: {status_error}")
        else:
            st.caption("Status not found.")

    with st.container(key="card_narrow"):
        st.markdown("#### Report status")
        with st.form("udpu_status_form", border=False):
            status_value = st.selectbox(
                "Status",
                options=["online", "offline", "unknown"],
                index=0,
            )
            submitted = st.form_submit_button("Send status", use_container_width=True)

        if submitted:
            try:
                payload = {"subscriber_uid": subscriber_uid, "status": status_value}
                with st.spinner("Sending status..."):
                    post_udpu_status(payload)
                st.toast("Status updated")
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))


def render_udpu_form(title: str, udpu=None):
    defaults = udpu or {}
    st.subheader(title)

    locations = []
    try:
        locations = fetch_udpu_locations()
    except RuntimeError:
        locations = []

    roles = []
    try:
        roles = fetch_roles()
    except RuntimeError:
        roles = []

    role_options = [r.get("name", "") for r in roles if r.get("name")]
    if defaults.get("role") and defaults.get("role") not in role_options:
        role_options.append(defaults.get("role"))

    location_options = _normalize_location_options(locations)
    if defaults.get("location") and defaults.get("location") not in location_options:
        location_options.append(defaults.get("location"))

    with st.container(key="card_narrow"):
        with st.form(f"form-{title}", border=False):
            if udpu:
                st.text_input("Subscriber UID", value=defaults.get("subscriber_uid", ""), disabled=True)

            if not udpu and location_options:
                location = st.selectbox(
                    "Location",
                    options=location_options,
                    index=location_options.index(defaults.get("location"))
                    if defaults.get("location") in location_options
                    else 0,
                )
            else:
                location = st.text_input("Location", value=defaults.get("location", ""))

            if role_options:
                role = st.selectbox(
                    "Role",
                    options=role_options,
                    index=role_options.index(defaults.get("role")) if defaults.get("role") in role_options else 0,
                )
            else:
                role = st.text_input("Role", value=defaults.get("role", ""))

            mac_address = st.text_input("MAC address", value=defaults.get("mac_address", ""))
            upstream_qos = st.text_input("Upstream QoS", value=defaults.get("upstream_qos", ""))
            downstream_qos = st.text_input("Downstream QoS", value=defaults.get("downstream_qos", ""))

            if not udpu:
                hostname = st.text_input("Hostname", value=defaults.get("hostname", ""))
            else:
                hostname = defaults.get("hostname", "")

            save = st.form_submit_button("Save", use_container_width=True)

        if st.button("Cancel", use_container_width=True):
            st.session_state.udpu_view = "list"
            st.rerun()

    if not save:
        return

    if not location.strip():
        st.error("Location is required")
        return

    if not role.strip():
        st.error("Role is required")
        return

    payload = {
        "location": location.strip(),
        "role": role.strip(),
        "upstream_qos": upstream_qos.strip(),
        "downstream_qos": downstream_qos.strip(),
    }

    if mac_address.strip():
        payload["mac_address"] = mac_address.strip()

    if not udpu and hostname.strip():
        payload["hostname"] = hostname.strip()

    try:
        if udpu:
            with st.spinner("Updating uDPU..."):
                updated = api_request("PUT", f"/subscriber/{udpu.get('subscriber_uid','')}/udpu", payload)
            st.session_state.selected_udpu = (updated or {}).get("subscriber_uid", udpu.get("subscriber_uid"))
            st.session_state.udpu_view = "detail"
            st.toast("uDPU updated")
        else:
            with st.spinner("Creating uDPU..."):
                created = api_request("POST", "/udpu", payload)
            st.session_state.selected_udpu = (created or {}).get("subscriber_uid")
            st.session_state.udpu_view = "detail"
            st.toast("uDPU created")
        st.rerun()
    except RuntimeError as exc:
        st.error(str(exc))


def render_udpu_list():
    st.title("uDPU")

    try:
        locations = fetch_udpu_locations()
    except RuntimeError:
        locations = []

    location_options = sorted(_normalize_location_options(locations))

    top_left, top_right = st.columns([6, 2])
    if location_options:
        if st.session_state.udpu_location not in location_options:
            st.session_state.udpu_location = location_options[0]
        selected_location = top_left.selectbox(
            "Location",
            options=location_options,
            index=location_options.index(st.session_state.udpu_location),
        )
        st.session_state.udpu_location = selected_location
    else:
        top_left.caption("No locations available.")

    if top_right.button("Add UDPU", use_container_width=True):
        st.session_state.udpu_view = "add"
        st.session_state.selected_udpu = None
        st.rerun()

    with st.container(key="card"):
        st.markdown("#### Lookup by MAC")
        with st.form("udpu_mac_lookup_form", border=False):
            mac_value = st.text_input("MAC address", value=st.session_state.udpu_mac_lookup)
            subscriber_uid = st.text_input("Fallback subscriber UID", value=st.session_state.udpu_mac_subscriber)
            lookup = st.form_submit_button("Find", use_container_width=True)

        if lookup:
            st.session_state.udpu_mac_lookup = mac_value
            st.session_state.udpu_mac_subscriber = subscriber_uid
            try:
                with st.spinner("Searching uDPU..."):
                    result = fetch_udpu_by_mac(mac_value.strip(), subscriber_uid.strip() or "none")
                st.session_state.udpu_mac_result = result
            except RuntimeError as exc:
                st.session_state.udpu_mac_result = None
                st.error(str(exc))

        result = st.session_state.udpu_mac_result
        if result:
            st.write(f"Subscriber UID: **{result.get('subscriber_uid', '')}**")
            st.write(f"Location: **{result.get('location', '') or '-'}**")
            st.write(f"Role: **{result.get('role', '') or '-'}**")
            st.write(f"MAC address: **{result.get('mac_address', '') or '-'}**")

            a1, a2 = st.columns(2)
            if a1.button("Open", use_container_width=True):
                st.session_state.selected_udpu = result.get("subscriber_uid")
                st.session_state.udpu_view = "detail"
                st.rerun()
            if a2.button("Delete by MAC", use_container_width=True):
                try:
                    with st.spinner("Deleting uDPU..."):
                        delete_udpu_by_mac(result.get("mac_address", ""))
                    st.session_state.udpu_mac_result = None
                    st.toast("uDPU deleted")
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

    if not st.session_state.udpu_location:
        st.info("No locations available.")
        return

    try:
        with st.spinner("Loading uDPU..."):
            udpus = fetch_udpu_list_by_location(st.session_state.udpu_location)
    except RuntimeError as exc:
        st.error(str(exc))
        return

    if not udpus:
        st.info("No uDPU devices found")
        return

    if pd is not None:
        rows = []
        for u in udpus:
            rows.append(
                {
                    "Subscriber UID": u.get("subscriber_uid", ""),
                    "Hostname": u.get("hostname", ""),
                    "MAC address": u.get("mac_address", ""),
                    "Role": u.get("role", ""),
                    "Upstream QoS": u.get("upstream_qos", ""),
                    "Downstream QoS": u.get("downstream_qos", ""),
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
                st.caption("Select a uDPU in the table to enable actions.")
                return

            selected_uid = str(df.iloc[selected_idx]["Subscriber UID"])
            st.write(f"Selected: **{selected_uid}**")

            a1, a2, a3 = st.columns(3)
            if a1.button("Open", use_container_width=True):
                st.session_state.selected_udpu = selected_uid
                st.session_state.udpu_view = "detail"
                st.rerun()
            if a2.button("Edit", use_container_width=True):
                st.session_state.selected_udpu = selected_uid
                st.session_state.udpu_view = "edit"
                st.rerun()
            if a3.button("Delete", use_container_width=True):
                confirm_delete_udpu(selected_uid)

    else:
        for u in udpus:
            c1, c2, c3 = st.columns([3, 5, 2])
            c1.write(u.get("subscriber_uid", ""))
            c2.write(u.get("hostname", ""))
            if c3.button("Open", key=f"open-{u.get('subscriber_uid','')}"):
                st.session_state.selected_udpu = u.get("subscriber_uid")
                st.session_state.udpu_view = "detail"
                st.rerun()

    st.markdown("### Bulk update")
    roles = []
    try:
        roles = fetch_roles()
    except RuntimeError:
        roles = []

    role_options = [r.get("name", "") for r in roles if r.get("name")]

    with st.container(key="card_narrow"):
        with st.form("udpu_bulk_update_form", border=False):
            if role_options:
                role_value = st.selectbox("Role", options=role_options, index=0)
            else:
                role_value = st.text_input("Role")

            new_location = st.text_input("New location", value="")
            mac_address = st.text_input("MAC address", value="")
            upstream_qos = st.text_input("Upstream QoS", value="")
            downstream_qos = st.text_input("Downstream QoS", value="")
            submitted = st.form_submit_button("Apply bulk update", use_container_width=True)

        if submitted:
            if not st.session_state.udpu_location:
                st.error("Location is required")
            elif not role_value or not role_value.strip():
                st.error("Role is required")
            else:
                payload = {"role": role_value.strip()}
                if new_location.strip():
                    payload["location"] = new_location.strip()
                if mac_address.strip():
                    payload["mac_address"] = mac_address.strip()
                if upstream_qos.strip():
                    payload["upstream_qos"] = upstream_qos.strip()
                if downstream_qos.strip():
                    payload["downstream_qos"] = downstream_qos.strip()
                try:
                    with st.spinner("Applying bulk update..."):
                        update_udpu_bulk(st.session_state.udpu_location, payload)
                    st.toast("Bulk update applied")
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

    st.markdown("### Status overview")
    try:
        statuses = fetch_udpu_statuses()
    except RuntimeError as exc:
        st.error(str(exc))
        statuses = []

    if statuses:
        if pd is not None:
            df_status = pd.DataFrame(statuses)
            st.dataframe(df_status, use_container_width=True, hide_index=True)
        else:
            st.code(json.dumps(statuses, indent=2), language="json")
    else:
        st.info("No UDPU status data found")

    st.markdown("### Unregistered devices")
    try:
        devices = fetch_unregistered_devices()
    except RuntimeError as exc:
        st.error(str(exc))
        devices = []

    if devices:
        if pd is not None:
            df_devices = pd.DataFrame(devices)
            st.dataframe(df_devices, use_container_width=True, hide_index=True)
        else:
            st.code(json.dumps(devices, indent=2), language="json")
    else:
        st.info("No unregistered devices found")

    st.markdown("### Add unregistered device")
    with st.container(key="card_narrow"):
        with st.form("unregistered_device_form", border=False):
            subscriber_uid = st.text_input("Subscriber UID", value="")
            ip_address = st.text_input("IP address", value="")
            last_call_home_dt = st.text_input("Last call home (ISO 8601)", value="")
            submitted = st.form_submit_button("Add device", use_container_width=True)

        if submitted:
            if not subscriber_uid.strip():
                st.error("Subscriber UID is required")
            elif not ip_address.strip():
                st.error("IP address is required")
            elif not last_call_home_dt.strip():
                st.error("Last call home is required")
            else:
                payload = {
                    "subscriber_uid": subscriber_uid.strip(),
                    "ip_address": ip_address.strip(),
                    "last_call_home_dt": last_call_home_dt.strip(),
                }
                try:
                    with st.spinner("Adding device..."):
                        post_unregistered_device(payload)
                    st.toast("Device added")
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))


def render_udpu():
    view = st.session_state.udpu_view

    if view == "detail":
        render_udpu_detail()
        return
    if view == "add":
        render_udpu_form("Add uDPU")
        return
    if view == "edit":
        subscriber_uid = st.session_state.selected_udpu
        if not subscriber_uid:
            st.session_state.udpu_view = "list"
            st.rerun()
        try:
            udpu = fetch_udpu(subscriber_uid)
        except RuntimeError as exc:
            st.error(str(exc))
            return
        render_udpu_form("Edit uDPU", udpu=udpu)
        return

    render_udpu_list()

def _job_frequency_options():
    return [
        {"value": "", "label": "Not set"},
        {"value": "1", "label": "Every minute"},
        {"value": "15", "label": "Every 15 minutes"},
        {"value": "60", "label": "Every hour"},
        {"value": "1440", "label": "Every 24 hours"},
        {"value": "first_boot", "label": "First boot"},
        {"value": "every_boot", "label": "Every boot"},
        {"value": "once", "label": "Once"},
    ]


def _job_frequency_label(value):
    for item in _job_frequency_options():
        if item["value"] == value:
            return item["label"]
    return value


def render_job_detail():
    name = st.session_state.selected_job
    if not name:
        st.session_state.jobs_view = "list"
        st.rerun()

    top = st.columns([1, 6, 2, 2])
    if top[0].button("← Back", use_container_width=True):
        st.session_state.jobs_view = "list"
        st.rerun()
    if top[2].button("Edit", use_container_width=True):
        st.session_state.jobs_view = "edit"
        st.rerun()
    if top[3].button("Delete", use_container_width=True):
        confirm_delete_job(name)

    try:
        with st.spinner("Loading job..."):
            job = fetch_job(name)
    except RuntimeError as exc:
        st.error(str(exc))
        return

    st.subheader(job.get("name", ""))
    st.write(job.get("description", ""))

    frequency_value = str(job.get("frequency") or "")
    frequency_label = _job_frequency_label(frequency_value or "")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Frequency", frequency_label or "-")
    c2.metric("Role", job.get("role", "") or "-")
    c3.metric("Type", job.get("type", "") or "-")
    c4.metric("Locked", job.get("locked", "") or "-")

    st.markdown("#### Command")
    st.code(job.get("command", "") or "", language="bash")

    if job.get("require_output"):
        st.markdown("#### Require output")
        st.code(job.get("require_output", "") or "", language="text")

    if job.get("required_software"):
        st.markdown("#### Required software")
        st.code(job.get("required_software", "") or "", language="text")

    if job.get("vbuser_id"):
        st.markdown("#### VB user id")
        st.write(job.get("vbuser_id", ""))


def render_job_form(title, job=None):
    defaults = job or {}
    st.subheader(title)

    frequency_value = str(defaults.get("frequency") or "")
    vbce_locations = []
    if not job:
        try:
            vbce_locations = fetch_vbce_locations()
        except RuntimeError:
            vbce_locations = []

    with st.container(key="card_narrow"):
        with st.form(f"form-{title}", border=False):
            name = st.text_input(
                "Name",
                value=defaults.get("name", ""),
                disabled=bool(job),
            )
            description = st.text_area(
                "Description",
                value=defaults.get("description", ""),
            )
            command = st.text_area(
                "Command",
                value=defaults.get("command", ""),
                height=140,
            )
            require_output = st.text_area(
                "Require output",
                value=defaults.get("require_output", ""),
                height=100,
            )
            required_software = st.text_input(
                "Required software",
                value=defaults.get("required_software", ""),
            )
            location_id = ""
            if not job:
                if vbce_locations:
                    location_options = sorted([str(loc) for loc in vbce_locations if loc is not None])
                    location_id = st.selectbox(
                        "Location",
                        options=location_options,
                        index=0,
                    )
                else:
                    location_id = st.text_input(
                        "Location",
                        value=defaults.get("location_id", ""),
                    )

            frequency_options = [item["value"] for item in _job_frequency_options()]
            frequency = st.selectbox(
                "Frequency",
                options=frequency_options,
                index=frequency_options.index(frequency_value)
                if frequency_value in frequency_options
                else 0,
                format_func=_job_frequency_label,
            )

            locked = st.text_input(
                "Locked",
                value=defaults.get("locked", ""),
            )
            role = st.text_input(
                "Role",
                value=defaults.get("role", ""),
            )
            job_type = st.text_input(
                "Type",
                value=defaults.get("type", ""),
            )
            vbuser_id = st.text_input(
                "VB user id",
                value=defaults.get("vbuser_id", ""),
            )

            save = st.form_submit_button("Save", use_container_width=True)

        if st.button("Cancel", use_container_width=True):
            st.session_state.jobs_view = "list"
            st.rerun()

    if not save:
        return

    if not name.strip():
        st.error("Job name is required")
        return

    if not command.strip():
        st.error("Command is required")
        return

    payload = {
        "name": name.strip(),
        "description": description,
        "command": command,
        "require_output": require_output,
        "required_software": required_software,
        "frequency": frequency or None,
        "locked": locked,
        "role": role,
        "type": job_type,
        "vbuser_id": vbuser_id,
    }
    if not job and location_id.strip():
        payload["location_id"] = location_id.strip()

    try:
        if job:
            payload.pop("name", None)
            payload.pop("vbuser_id", None)
            with st.spinner("Updating job..."):
                updated = api_request("PATCH", f"/jobs/{job.get('name','')}", payload)
            st.session_state.selected_job = (updated or {}).get("name", job.get("name", ""))
            st.session_state.jobs_view = "detail"
            st.toast("Job updated")
        else:
            with st.spinner("Creating job..."):
                api_request("POST", "/jobs", payload)
            st.session_state.jobs_view = "list"
            st.toast("Job created")
        st.rerun()
    except RuntimeError as exc:
        st.error(str(exc))


def render_job_list():
    st.title("Jobs")

    _, add_col = st.columns([7, 2])
    if add_col.button("Add job", use_container_width=True):
        st.session_state.jobs_view = "add"
        st.session_state.selected_job = None
        st.rerun()

    try:
        with st.spinner("Loading jobs..."):
            jobs = fetch_jobs()
    except RuntimeError as exc:
        st.error(str(exc))
        return

    if not jobs:
        st.info("No jobs found")
        return

    if pd is not None:
        rows = []
        for job in jobs:
            frequency_value = str(job.get("frequency") or "")
            rows.append(
                {
                    "Name": job.get("name", ""),
                    "Description": job.get("description", ""),
                    "Frequency": _job_frequency_label(frequency_value),
                    "Role": job.get("role", ""),
                    "Type": job.get("type", ""),
                    "Locked": job.get("locked", ""),
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
                st.caption("Select a job in the table to enable actions.")
                return

            selected_name = str(df.iloc[selected_idx]["Name"])
            st.write(f"Selected: **{selected_name}**")

            a1, a2, a3 = st.columns(3)
            if a1.button("Open", use_container_width=True):
                st.session_state.selected_job = selected_name
                st.session_state.jobs_view = "detail"
                st.rerun()
            if a2.button("Edit", use_container_width=True):
                st.session_state.selected_job = selected_name
                st.session_state.jobs_view = "edit"
                st.rerun()
            if a3.button("Delete", use_container_width=True):
                confirm_delete_job(selected_name)

    else:
        for job in jobs:
            c1, c2, c3 = st.columns([3, 5, 2])
            c1.write(job.get("name", ""))
            c2.write(job.get("description", ""))
            if c3.button("Open", key=f"open-{job.get('name','')}"):
                st.session_state.selected_job = job.get("name")
                st.session_state.jobs_view = "detail"
                st.rerun()


def render_jobs():
    view = st.session_state.jobs_view

    if view == "detail":
        render_job_detail()
        return
    if view == "add":
        render_job_form("Add job")
        return
    if view == "edit":
        name = st.session_state.selected_job
        if not name:
            st.session_state.jobs_view = "list"
            st.rerun()
        try:
            job = fetch_job(name)
        except RuntimeError as exc:
            st.error(str(exc))
            return
        render_job_form("Edit job", job=job)
        return

    render_job_list()


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
            if st.button("uDPU", use_container_width=True, type="primary" if current == "UDPU" else "secondary"):
                set_active_tab("uDPU")
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
            render_vbce()
        elif selection == "UDPU":
            render_udpu()
        elif selection == "Jobs":
            render_jobs()


ensure_state()

if not st.session_state.authenticated:
    render_login()
else:
    render_app()
