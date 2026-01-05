import streamlit as st
from .common import render_list, render_create, render_update, render_delete, extract_ids

def render(client, endpoints, note):
    st.subheader('VBCE')
    st.info(note)
    data = render_list('vbce_data', client, endpoints['list'], 'Список VBCE')
    ids = extract_ids(data)
    render_create(client, endpoints['create'], 'vbce')
    render_update(client, endpoints['update'], 'vbce', ids)
    render_delete(client, endpoints['delete'], 'vbce', ids)
