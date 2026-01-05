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


def handle_login():
    st.title('Админ панель')
    login = st.text_input('Логин')
    password = st.text_input('Пароль', type='password')
    if st.button('Войти'):
        if login == 'admin' and password == 'admin':
            st.session_state.is_auth = True
        else:
            st.error('Неверные учетные данные')


def render_nav():
    left, right = st.columns([1, 2])
    with left:
        st.header('Меню')
        options = ['ROLES', 'VBCE', 'uDPU', 'JOBS']
        current_index = options.index(st.session_state.nav) if st.session_state.nav in options else 0
        st.session_state.nav = st.radio('Разделы', options, index=current_index)
        if st.button('Выйти'):
            st.session_state.clear()
            st.session_state.is_auth = False
    with right:
        st.header(st.session_state.nav)
        return right


def main():
    st.set_page_config(layout='wide', page_title='Admin UI')
    ensure_auth_state()
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
