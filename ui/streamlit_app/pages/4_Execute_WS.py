import json
import streamlit as st

from client.api_client import ApiClient, ApiError
from client.ws_client import WsClient, WsError
from ui.components import inject_css, render_card, render_json_response, render_error, render_nav

st.set_page_config(page_title="Execute", layout="wide")

inject_css(st.session_state.get("theme", "dark"))

def require_auth():
    if not st.session_state.get("authenticated"):
        st.error("Sign in required")
        if st.button("Go to login"):
            st.switch_page("app.py")
        st.stop()


def get_http():
    return ApiClient(base_url=st.session_state.get("api_base_url"))


def ensure_ws():
    if "ws_client" not in st.session_state:
        st.session_state.ws_client = WsClient(base_url=st.session_state.get("api_base_url"))


def load_jobs():
    try:
        return get_http().get("/jobs")
    except ApiError as e:
        render_error(e)
        return []


def load_udpu():
    try:
        locations = get_http().get("/udpu/locations")
        all_items = []
        for loc in locations:
            try:
                items = get_http().get(f"/{loc}/udpu_list")
                all_items.extend(items)
            except ApiError as e:
                render_error(e)
        return all_items
    except ApiError as e:
        render_error(e)
        return []


def ws_url(channel):
    client = WsClient(base_url=st.session_state.get("api_base_url"))
    return f"{client.ws_base}/pub?channel={channel}"


def connect_section():
    def body():
        ensure_ws()
        jobs = load_jobs()
        udpu_list = load_udpu()
        job_names = [j.get("uid") or j.get("name") for j in jobs]
        udpu_channels = [u.get("subscriber_uid") for u in udpu_list]
        job = st.selectbox("Job UID/Name", job_names)
        channel = st.selectbox("UDPU channel", udpu_channels)
        st.markdown(f"WS: {ws_url(channel)}")
        if st.button("Connect"):
            try:
                st.session_state.ws_client.connect(f"/pub?channel={channel}")
                st.session_state.ws_connected = True
                st.success("Connected")
            except Exception as e:
                render_error(e)
        if st.button("Disconnect"):
            try:
                st.session_state.ws_client.disconnect()
                st.session_state.ws_connected = False
                st.success("Disconnected")
            except Exception as e:
                render_error(e)
    render_card("Connection", body)


def actions_section():
    def body():
        ensure_ws()
        if not st.session_state.get("ws_connected"):
            st.warning("No connection")
            return
        job_id = st.text_input("Job name/uid to run")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ping"):
                try:
                    st.session_state.ws_client.ping()
                    st.session_state.ws_log.append("pong")
                except WsError as e:
                    render_error(e)
        with col2:
            if st.button("Run job"):
                try:
                    st.session_state.ws_client.send(f"run job {job_id}")
                    st.session_state.ws_log.extend(st.session_state.ws_client.receive())
                except Exception as e:
                    render_error(e)
        if st.button("Fetch status"):
            try:
                st.session_state.ws_client.send("run job status")
                st.session_state.ws_log.extend(st.session_state.ws_client.receive())
            except Exception as e:
                render_error(e)
        st.markdown("### Logs")
        for line in st.session_state.ws_log[-200:]:
            st.markdown(f"- {line}")
    render_card("Actions", body)


def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.ws_log = []
    st.session_state.ws_connected = False
    st.switch_page("app.py")


def page():
    require_auth()
    st.title("Execute")
    render_nav("Execute")
    if st.button("Sign out"):
        logout()
    connect_section()
    actions_section()


page()
