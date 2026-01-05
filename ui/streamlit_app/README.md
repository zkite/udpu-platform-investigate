# Streamlit UI

## Быстрый старт локально
```
cd ui/streamlit_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
API_BASE_URL=http://localhost:8888/api/v1.0 streamlit run app.py
```

## Запуск в Docker Compose
```
ENV=local docker compose -f docker-compose.local.yml up --build
```
- Профиль `ENV=local` включает API на порту `8888`, поэтому ошибка `Connection refused` исчезнет после поднятия `api-service`.
- UI доступен на `http://localhost:8501`.
- Переменная `BACKEND_BASE_URL` для UI берется из `docker-compose.local.yml` (по умолчанию `http://api-service:8888/api/v1.0`).

## Конфигурация
- `API_BASE_URL` или `BACKEND_BASE_URL` — базовый URL бекенда (приоритет у `API_BASE_URL`).
- `API_TIMEOUT` — таймаут HTTP, сек.
- `WS_TIMEOUT` — таймаут WS, сек.

## Навигация
- Логин admin/admin.
- Вкладки: Roles, VBCE, Jobs, Execute, Environment.
- Переключение темы (dark/light) в сайдбаре, по умолчанию dark.

## Styling contract
- Цвета и отступы в `ui/theme.py`.
- CSS в `ui/styles.css`, подключение через `inject_css()`.
- Компоненты в `ui/components.py`.
- Менять токены можно только в theme.py, layout — в styles.css.
