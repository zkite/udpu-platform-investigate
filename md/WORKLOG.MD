Добавлен интерфейс Jobs по аналогии с Roles: список, карточка действий, формы создания и редактирования, детальный просмотр, удаление, выбор частоты, а также интеграция в навигацию.【F:frontend/app.py†L230-L1480】
Добавлены обновления логики ролей и консистентности UDPU↔VBUser, нормализация interfaces и эндпоинт уникальных локаций VBCE.【F:api-service/app/domain/api/roles/dependencies.py†L1-L162】【F:api-service/app/domain/api/northbound/view.py†L1-L450】【F:api-service/app/domain/api/northbound/dependencies.py†L1-L143】【F:api-service/app/domain/api/vbuser/dependencies.py†L1-L149】【F:api-service/app/domain/api/vbce/dependencies.py†L1-L26】【F:api-service/app/domain/api/vbce/view.py†L1-L116】
Добавлен выбор локации для списка UDPU и унификация обработки локаций, чтобы список, просмотр и фильтрация работали для строковых и объектных данных.【F:frontend/app.py†L1011-L1244】
Расширен UI uDPU: добавлены поиск по MAC, массовое обновление по локации, отправка статуса и форма добавления незарегистрированных устройств, а также вспомогательные API-вызовы и состояние интерфейса.【F:frontend/app.py†L247-L1450】

## Обновление
- Исправлено дублирование ключей контейнеров в списке uDPU.
- Добавлена проверка обязательности MAC-адреса перед поиском.
