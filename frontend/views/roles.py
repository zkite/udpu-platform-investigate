import streamlit as st
from .common import render_list, render_create, render_update, render_delete, extract_ids

def render(client, endpoints, note):
    st.subheader('Роли')
    st.info(note)
    data = render_list('roles_data', client, endpoints['list'], 'Список ролей')
    ids = extract_ids(data)
    render_create(client, endpoints['create'], 'roles')
    render_update(client, endpoints['update'], 'roles', ids)
    render_delete(client, endpoints['delete'], 'roles', ids)
