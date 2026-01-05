import os
import streamlit as st
from api_client import APIClient
from views import roles, vbce, udpu, jobs

ENDPOINTS = {
    'ROLES': {
        'list': '/roles',
        'get': '/roles/{id}',
        'create': '/roles',
        'update': '/roles/{id}',
        'delete': '/roles/{id}'
    },
    'VBCE': {
        'list': '/vbce',
        'get': '/vbce/{id}',
        'create': '/vbce',
        'update': '/vbce/{id}',
        'delete': '/vbce/{id}'
    },
    'uDPU': {
        'list': '/udpu',
        'get': '/udpu/{id}',
        'create': '/udpu',
        'update': '/udpu/{id}',
        'delete': '/udpu/{id}'
    },
    'JOBS': {
        'list': '/jobs',
        'get': '/jobs/{id}',
        'create': '/jobs',
        'update': '/jobs/{id}',
        'delete': '/jobs/{id}',
        'run': '/jobs/{id}/run'
    }
}

NOTE_TEXT = 'Обновите ENDPOINTS в app.py после уточнения реальных путей API.'

def ensure_auth_state():
    if 'is_auth' not in st.session_state:
        st.session_state.is_auth = False
    if 'nav' not in st.session_state:
        st.session_state.nav = 'ROLES'
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'


def handle_login():
    st.title('Админ панель')
    st.markdown("""
    <style>
    .login-card{max-width:300px;margin-left:auto;margin-right:auto;padding:24px;border-radius:12px;background-color:rgba(255,255,255,0.85);box-shadow:0 8px 24px rgba(0,0,0,0.08)}
    </style>
    """, unsafe_allow_html=True)
    _, center, _ = st.columns([1,1,1])
    with center:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        login = st.text_input('Логин')
        password = st.text_input('Пароль', type='password')
        if st.button('Войти'):
            if login == 'admin' and password == 'admin':
                st.session_state.is_auth = True
            else:
                st.error('Неверные учетные данные')
        st.markdown('</div>', unsafe_allow_html=True)


def render_nav():
    left, right = st.columns([1, 5])
    with left:
        st.header('Меню')
        options = ['ROLES', 'VBCE', 'uDPU', 'JOBS']
        current_index = options.index(st.session_state.nav) if st.session_state.nav in options else 0
        st.session_state.nav = st.radio('Разделы', options, index=current_index)
        dark = st.toggle('Темная тема', value=st.session_state.theme == 'dark')
        st.session_state.theme = 'dark' if dark else 'light'
        if st.button('Выйти'):
            st.session_state.clear()
            st.session_state.is_auth = False
    with right:
        st.header(st.session_state.nav)
        return right


def apply_theme():
    if st.session_state.theme == 'dark':
        st.markdown("""
        <style>
        .stApp, .main, .block-container{background-color:#0e1117;color:#e0e0e0}
        .stButton>button, .st-radio div[role='radiogroup'] label, .stSelectbox div, .stTextInput input, .stPasswordInput input, .stTextArea textarea{color:#e0e0e0;background-color:#1c2331;border-color:#3a4556}
        .stButton>button:hover{background-color:#263040}
        .st-expander, .stDataFrame{background-color:#151a23;color:#e0e0e0}
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        .stApp, .main, .block-container{background-color:#f7f7f9;color:#1f1f1f}
        .stButton>button, .st-radio div[role='radiogroup'] label, .stSelectbox div, .stTextInput input, .stPasswordInput input, .stTextArea textarea{color:#1f1f1f;background-color:#ffffff;border-color:#d6d6d6}
        .st-expander, .stDataFrame{background-color:#ffffff;color:#1f1f1f}
        </style>
        """, unsafe_allow_html=True)


def main():
    st.set_page_config(layout='wide', page_title='Admin UI')
    ensure_auth_state()
    apply_theme()
    base_url = os.getenv('API_BASE_URL', 'http://localhost:8888')
    client = APIClient(base_url)
    if not st.session_state.is_auth:
        handle_login()
        return
    right = render_nav()
    with right:
        current = st.session_state.nav
        if current == 'ROLES':
            roles.render(client, ENDPOINTS['ROLES'], NOTE_TEXT)
        elif current == 'VBCE':
            vbce.render(client, ENDPOINTS['VBCE'], NOTE_TEXT)
        elif current == 'uDPU':
            udpu.render(client, ENDPOINTS['uDPU'], NOTE_TEXT)
        elif current == 'JOBS':
            jobs.render(client, ENDPOINTS['JOBS'], NOTE_TEXT)


if __name__ == '__main__':
    main()
