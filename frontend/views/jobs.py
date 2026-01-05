import streamlit as st
from .common import render_list, render_create, render_update, render_delete, extract_ids, build_path

def render(client, endpoints, note):
    st.subheader('Задания')
    st.info(note)
    data = render_list('jobs_data', client, endpoints['list'], 'Список заданий')
    ids = extract_ids(data)
    render_create(client, endpoints['create'], 'jobs')
    render_update(client, endpoints['update'], 'jobs', ids)
    render_delete(client, endpoints['delete'], 'jobs', ids)
    with st.expander('Запустить задание'):
        options = ids if ids else []
        selected = st.selectbox('Идентификатор', options, key='jobs_run_select') if options else st.text_input('Идентификатор', key='jobs_run_input')
        if st.button('Запустить', key='jobs_run_btn'):
            target = selected if selected else st.session_state.get('jobs_run_input', '')
            if not target:
                st.error('Требуется идентификатор')
            else:
                ok, data = client.post(build_path(endpoints.get('run', ''), target))
                if ok:
                    st.success('Отправлено')
                else:
                    st.error(data)
