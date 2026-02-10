# Repository Service – Project Documentation

This README provides a detailed overview of the **repository-service** component of the UDPU platform. It focuses on environment variables, Redis configuration, service registration, API behavior, and core business logic.

---

## Table of Contents

1. [Overview](#overview)  
2. [Environment Variables](#environment-variables)  
3. [Configuration & Startup](#configuration--startup)  
4. [Redis Connection](#redis-connection)  
5. [Service Registration](#service-registration)  
6. [API Endpoints](#api-endpoints)  
7. [Business Logic](#business-logic)  
8. [Dockerfile & Deployment](#dockerfile--deployment)  
9. [Next Steps & Best Practices](#next-steps----best-practices)  

---

## Overview

The **repository-service** is responsible for:

- Persisting metadata about software packages (repositories) used by routers.  
- Providing CRUD operations over HTTP (FastAPI).  
- Storing data in Redis hashes for quick access.  
- Tracking download counts for analytics.  
- Registering itself with the discovery-service.  
- Exposing a health check endpoint.

Built with **Python 3.11**, **FastAPI**, and **Redis**, running under **Uvicorn**.

---

## Environment Variables

Variables can be set in an `.env` file or via CI/CD:

| Variable                      | Description                                                       | Example                   | Required |
|-------------------------------|-------------------------------------------------------------------|---------------------------|----------|
| `UDPU_ENVIRONMENT`            | Runtime environment (`dev`, `test`, `prod`)                      | `dev`                     | Yes      |
| `SERVER_HOST`                 | Hostname or IP where this service is reachable                    | `repository-service`      | Yes      |
| `SERVER_PORT`                 | Port number for incoming HTTP requests                            | `8887`                    | Yes      |
| `DISCOVERY_SERVICE_HOST`      | Hostname or IP of the discovery-service                           | `discovery-service`       | Yes      |
| `DISCOVERY_SERVICE_PORT`      | Port number of the discovery-service                              | `8886`                    | Yes      |
| `REDIS_HOST`                  | Redis server hostname/IP                                          | `redis`                   | Yes      |
| `REDIS_PORT`                  | Redis server port                                                | `6379`                    | Yes      |
| `REDIS_USER`                  | Redis ACL username (if used)                                      | —                         | No       |
| `REDIS_PASS`                  | Redis ACL password (if used)                                      | —                         | No       |
| `LOG_LEVEL`                   | Python logging level (`DEBUG`, `INFO`, etc.)                     | `INFO`                    | No       |

---

## Configuration & Startup

- Settings are loaded via Pydantic classes in `app/settings/`.  
- On **startup** (`events.create_start_app_handler`):
  1. Connect to Redis (`services.redis.connect_to_redis`).  
  2. Start the scheduler (`services.scheduler.start_scheduler`) to run `register_service` every 30 seconds.  
- On **shutdown** (`events.create_stop_app_handler`):
  - Close Redis connection.  
  - Stop the scheduler.

---

## Redis Connection

- Built from `redis://[user:pass@]host:port` via `settings.redis_url`.  
- Connection created in `app.state.redis` (accessible from request handlers).  
- Data stored as Redis **hashes**:
  - Key pattern: `SERVICE_REPOSITORY_<software_uid>`  
  - Fields: all properties from the `Repository` model (description, url, password, sha256_checksum, number_of_downloads, etc.).  

---

## Service Registration

Every 30 seconds, this service announces itself to discovery-service by:

```http
POST http://<DISCOVERY_SERVICE_HOST>:<DISCOVERY_SERVICE_PORT>/register
Content-Type: application/json

{
  "host": "<SERVER_HOST>",
  "port": <SERVER_PORT>,
  "service_type": "repo"
}
```

Discovery-service can then route requests or display available services dynamically.

---

## API Endpoints

All endpoints are prefixed with `/api/v1.0`:

| Method | Path                           | Description                                       |
|--------|--------------------------------|---------------------------------------------------|
| GET    | `/api/v1.0/health`             | Health check (returns `{ "status": "success" }`) |
| POST   | `/api/v1.0/repo`               | Create a new repository entry                     |
| GET    | `/api/v1.0/repo/{software_uid}`| Retrieve metadata for a specific repository       |
| PATCH  | `/api/v1.0/repo/{software_uid}`| Update fields of an existing repository           |
| DELETE | `/api/v1.0/repo/{software_uid}`| Delete a repository entry (currently a mock)      |

---

## Business Logic

### Create (POST /repo)

1. **Compute identifiers**  
   - `software_uid` generated from URL & password (`get_hashed_software_uid`).  
   - `sha256_checksum` computed from remote file (`get_sha256_checksum`).  
2. **Uniqueness check**  
   - If an entry with the same `software_uid` exists → HTTP 400.  
3. **Persistence**  
   - Store all fields and computed values in a Redis hash.  
4. **Error handling**  
   - If checksum cannot be computed (file not found) → HTTP 404.

### Retrieve (GET /repo/{software_uid})

1. Fetch Redis hash by key.  
2. If not found → HTTP 404.  
3. Increment `number_of_downloads` in Redis (`HINCRBY`) and in response.  
4. Return the full repository metadata.

### Update (PATCH /repo/{software_uid})

1. Fetch existing hash.  
2. If not found → HTTP 404.  
3. Merge provided fields into the existing model.  
4. Overwrite the Redis hash with updated data.  
5. Return updated metadata.

### Delete (DELETE /repo/{software_uid})

- **Stub implementation**: returns HTTP 200 with a message.  
- **To do**: implement actual `HDEL` to remove Redis key and associated data.

---

## Dockerfile & Deployment

**Dockerfile** (located in `docker/Dockerfile`):

```dockerfile
FROM python:3.11.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install OS dependencies
RUN apt-get update &&     apt-get install -y procps redis-tools netcat-openbsd build-essential python3-dev libffi-dev linux-libc-dev &&     rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY ../requirements/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY ../app .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8887", "--reload"]
```

**Build & run locally**:

```bash
cd repository-service/docker
docker build -t udpu-repo:dev .
docker run --env-file ../.env.repo.dev -p 8887:8887 udpu-repo:dev
```

**Using Docker Compose** (add to root `docker-compose.yml`):

```yaml
repository:
  build: ./repository-service/docker
  env_file: ./repository-service/.env.repo.dev
  ports:
    - "8887:8887"
  depends_on:
    - redis
    - discovery
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8887/api/v1.0/health"]
  restart: unless-stopped
```

