import streamlit as st
from .common import render_list, render_create, render_update, render_delete, extract_ids

def render(client, endpoints, note):
    st.subheader('uDPU')
    st.info(note)
    data = render_list('udpu_data', client, endpoints['list'], 'Список uDPU')
    ids = extract_ids(data)
    render_create(client, endpoints['create'], 'udpu')
    render_update(client, endpoints['update'], 'udpu', ids)
    render_delete(client, endpoints['delete'], 'udpu', ids)
