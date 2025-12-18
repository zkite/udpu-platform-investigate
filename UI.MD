# Streamlit UI Overview

## Purpose
Adds a Streamlit-based administrative console for Roles, uDPU (northbound), and Jobs management without altering backend business logic.

## Tech Stack
- Streamlit >= 1.52
- Python 3.11
- Requests for HTTP calls
- Docker / docker-compose

## Running the UI
- **Docker Compose (default)**
  - `ENV=test` or desired profile if needed by other services.
  - `docker compose up --build ui api-service discovery-service repository-service redis` (or simply `docker compose up --build`).
  - UI available at `http://localhost:8501`.
  - Backend base URL provided via `BACKEND_BASE_URL` (defaults set per compose files).
- **Local (without Compose)**
  - `cd ui/streamlit_app`
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
  - `BACKEND_BASE_URL=http://localhost:8888/api/v1.0 streamlit run app.py`

## Authentication
- Login required for all tabs.
- Credentials: `admin` / `admin`.
- Session state keeps `auth` flag and username; logout clears session state.

## UI Structure & Navigation
- Single-page Streamlit app with tab navigation: **Roles** (default), **uDPU**, **Jobs**.
- Tabs rendered only after successful login; login screen blocks other content.
- Header shows current user and logout button.

### Login Screen Layout
1. Page title "Login".
2. Form fields stacked vertically: username input, password input.
3. Submit button "Войти" beneath inputs; error message inline on failure.

### Roles Tab
- Header controls: expandable **Создать роль** form at top.
- Below form: list of roles as expandable panels (one per role).
- Inside each panel:
  - Read-only summary rows for description and flags.
  - Edit form with description and boolean toggles.
  - Delete row with two-step confirmation ("Удалить" then "Подтвердить удаление").

### uDPU Tab
- Header controls: expandable **Создать uDPU** form at top, followed by **Обновить uDPU** button.
- List of uDPU records (grouped across all locations) as expandable panels showing key fields.
- Each panel contains an edit form for location/role/QoS/MAC/hostname and delete confirmation buttons.

### Jobs Tab
- Header controls: expandable **Создать задание** form at top.
- Job list as expandable panels displaying description, command, frequency, and role.
- Each panel includes an edit form and delete confirmation buttons.

## Styling Rules
- Layout: wide page, clear separators via expanders and dividers.
- Typography: bold labels for summaries; body text for values.
- Spacing: default Streamlit padding; forms stacked vertically; actions grouped in two-column confirmation rows.
- Colors: Streamlit defaults; success/error messaging through `st.success` / `st.error` / `st.warning` / `st.info`.
- Buttons: consistent labels ("Создать", "Сохранить", "Удалить", "Подтвердить удаление", "Выйти", "Обновить uDPU").

## CRUD Flows & Validation
- Required fields enforced before submission:
  - Roles: name and description when creating; description on edit.
  - uDPU: location, role, upstream_qos, downstream_qos for create/edit; optional MAC and hostname.
  - Jobs: name and command for create; command for edit; frequency optional.
- Empty states: `st.info` messages such as "Нет ролей", "Нет записей", "Нет заданий" with create expanders always visible.
- Error states: API errors displayed via `st.error`; warnings for partial list fetches.
- Delete requires two clicks: initial "Удалить" sets a pending target; "Подтвердить удаление" executes.
- Refresh: after successful mutations the app triggers `st.experimental_rerun`; manual refresh button on uDPU tab.

## Backend Communication
- Base URL from `BACKEND_BASE_URL` env (defaults: `http://localhost:8888/api/v1.0` for host-mode compose; `http://api-service:8888/api/v1.0` for bridge compose).
- HTTP client uses `requests` with short timeout (`UI_REQUEST_TIMEOUT`, default 5s).
- Endpoints used:
  - Roles: `GET /roles`, `POST /roles`, `PATCH /roles/{name}`, `DELETE /roles/{name}`.
  - uDPU: `GET /udpu/locations`, `GET /{location}/udpu_list`, `POST /udpu`, `PUT /subscriber/{subscriber_uid}/udpu`, `DELETE /subscriber/{subscriber_uid}/udpu`.
  - Jobs: `GET /jobs`, `POST /jobs`, `PATCH /jobs/{identifier}`, `DELETE /jobs/{identifier}`.
- Payloads (examples):
  - Role create/update: `{ "name": "edge", "description": "Edge role", "wireguard_tunnel": false, "job_control": true }`.
  - uDPU create/update: `{ "location": "loc-1", "role": "edge", "upstream_qos": "100m", "downstream_qos": "200m", "mac_address": "aa:bb:cc:dd:ee:ff", "hostname": "udpu-1" }` (MAC/hostname optional).
  - Job create: `{ "name": "init", "description": "setup", "command": "echo hi", "frequency": "first_boot", "role": "edge", "require_output": "false", "required_software": "", "locked": "", "type": "common", "vbuser_id": "" }`; update uses partial fields.
- Responses: success handled when HTTP 2xx; non-2xx surfaces `message`/`detail` if present or a generic HTTP code.

