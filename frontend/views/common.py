import json
import streamlit as st
from api_client import parse_json

def ensure_state(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default

def normalize_data(data):
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]

def build_path(path, item_id=None):
    if item_id is None:
        return path
    return path.replace('{id}', str(item_id))

def render_list(key, client, path, label):
    ensure_state(key, [])
    if st.button('Обновить', key=f'{key}_refresh') or not st.session_state[key]:
        ok, data = client.get(path)
        if ok:
            st.session_state[key] = data if data is not None else []
        else:
            st.error(data)
    data = normalize_data(st.session_state[key])
    st.caption(label)
    if data:
        st.dataframe(data)
    else:
        st.info('Нет данных')
    return data

def render_create(client, path, prefix):
    with st.expander('Создать'):
        text = st.text_area('Данные JSON', height=150, key=f'{prefix}_create_text')
        if st.button('Отправить', key=f'{prefix}_create_btn'):
            valid, payload = parse_json(text)
            if not valid:
                st.error(payload)
            else:
                ok, data = client.post(path, payload=payload)
                if ok:
                    st.success('Успешно')
                else:
                    st.error(data)

def render_update(client, path, prefix, ids=None):
    with st.expander('Обновить'):
        options = ids if ids else []
        selected = st.selectbox('Идентификатор', options, key=f'{prefix}_update_select') if options else st.text_input('Идентификатор', key=f'{prefix}_update_input')
        text = st.text_area('Данные JSON', height=150, key=f'{prefix}_update_text')
        if st.button('Сохранить', key=f'{prefix}_update_btn'):
            target = selected if selected else st.session_state.get(f'{prefix}_update_input', '')
            if not target:
                st.error('Требуется идентификатор')
            else:
                valid, payload = parse_json(text)
                if not valid:
                    st.error(payload)
                else:
                    ok, data = client.put(build_path(path, target), payload=payload)
                    if ok:
                        st.success('Успешно')
                    else:
                        st.error(data)

def render_delete(client, path, prefix, ids=None):
    with st.expander('Удалить'):
        options = ids if ids else []
        selected = st.selectbox('Идентификатор', options, key=f'{prefix}_delete_select') if options else st.text_input('Идентификатор', key=f'{prefix}_delete_input')
        if st.button('Удалить', key=f'{prefix}_delete_btn'):
            target = selected if selected else st.session_state.get(f'{prefix}_delete_input', '')
            if not target:
                st.error('Требуется идентификатор')
            else:
                ok, data = client.delete(build_path(path, target))
                if ok:
                    st.success('Удалено')
                else:
                    st.error(data)

def extract_ids(data):
    ids = []
    for item in normalize_data(data):
        if isinstance(item, dict):
            value = item.get('id')
            if value is not None:
                ids.append(value)
    return ids
