# Streamlit UI

## Запуск
```
cd ui/streamlit_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
API_BASE_URL=http://localhost:8888/api/v1.0 streamlit run app.py
```

## Конфигурация
- `API_BASE_URL` — базовый URL бекенда.
- `API_TIMEOUT` — таймаут HTTP, сек.
- `WS_TIMEOUT` — таймаут WS, сек.

## Навигация
- Логин admin/admin.
- Вкладки: Roles, VBCE, Jobs, Execute.

## Styling contract
- Цвета и отступы в `ui/theme.py`.
- CSS в `ui/styles.css`, подключение через `inject_css()`.
- Компоненты в `ui/components.py`.
- Менять токены можно только в theme.py, layout — в styles.css.
