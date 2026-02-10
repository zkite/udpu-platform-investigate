# API Service - Documentation

This README provides an overview of the **api-service** for the UDPU platform. It focuses on environment variables, Redis configuration, event handling, and the business logic of each domain.

---

## Table of Contents

1. [Overview](#overview)  
2. [Environment Variables](#environment-variables)  
3. [Redis Configuration](#redis-configuration)  
4. [Startup & Shutdown Events](#startup--shutdown-events)  
5. [Domain Business Logic](#domain-business-logic)  
   - [Authentication (Stamps)](#authentication-stamps)  
   - [Job Logs](#job-logs)  
   - [Jobs Management](#jobs-management)  
   - [VBCE (Virtual Broadband CE)](#vbce-virtual-broadband-ce)  
   - [VBUser (Subscriber Devices)](#vbuser-subscriber-devices)  
   - [Northbound (Device Onboarding)](#northbound-device-onboarding)  
   - [Roles & Permissions](#roles--permissions)  
   - [WireGuard Management](#wireguard-management)  
   - [WebSocket Pub/Sub](#websocket-pubsub)  
   - [Health Check](#health-check)  
6. [Build & Run](#build--run)  
7. [Next Steps & Best Practices](#next-steps--best-practices)  

---

## Overview

**api-service** is the gateway of the UDPU platform:

- Exposes HTTP endpoints (and WebSocket)  
- Handles security (JWT stamping)  
- Orchestrates workflows across microservices (repository, discovery)  
- Uses Redis for caching, state, Pub/Sub, and scheduling  
- Emits business events and metrics  

---

## Environment Variables

All settings are loaded via Pydantic `BaseSettings`. Variables can be set in `.env` files or via CI/CD.

| Variable                   | Description                                                        | Example                   | Required |
|----------------------------|--------------------------------------------------------------------|---------------------------|----------|
| `UDPU_ENVIRONMENT`         | Runtime environment (`dev`, `test`, `prod`)                       | `dev`                     | Yes      |
| `SERVER_HOST`              | Host/IP where api-service runs                                     | `0.0.0.0` or `api-service`| Yes      |
| `SERVER_PORT`              | Port for HTTP server                                               | `8888`                    | Yes      |
| `REDIS_HOST`               | Redis hostname/IP                                                  | `redis`                   | Yes      |
| `REDIS_PORT`               | Redis port                                                         | `6379`                    | Yes      |
| `REDIS_USER`               | Redis username (if ACL enabled)                                    |                           | No       |
| `REDIS_PASS`               | Redis password (if ACL enabled)                                    |                           | No       |
| `DISCOVERY_SERVICE_HOST`   | Host/IP of discovery-service                                       | `discovery-service`       | Yes      |
| `DISCOVERY_SERVICE_PORT`   | Port of discovery-service                                          | `8886`                    | Yes      |
| `LOG_LEVEL`                | Application logging level (`DEBUG`, `INFO`, etc.)                 | `INFO`                    | No       |
| `DOCS_URL`                 | FastAPI docs URL path                                              | `/docs`                   | No       |
| `OPENAPI_URL`              | FastAPI OpenAPI JSON URL                                           | `/openapi.json`           | No       |
| `REDOC_URL`                | Redoc UI URL path                                                  | `/redoc`                  | No       |
| `TITLE`                    | Swagger UI title                                                   | `uDPU API Service`        | No       |
| `VERSION`                  | API version                                                        | `0.1.0`                   | No       |
| `MAX_CONNECTION_COUNT`     | Max DB/Redis pool connections                                      | `10`                      | No       |
| `MIN_CONNECTION_COUNT`     | Min DB/Redis pool connections                                      | `10`                      | No       |
| `ALLOWED_HOSTS`            | CORS allowed hosts                                                  | `*`                       | No       |
| **WireGuard Settings:**    |                                                                    |                           |          |
| `WG_SERVER_IP`             | WireGuard server IP/CIDR                                           | `10.66.0.1/16`            | No       |
| `WG_SERVER_PORT`           | WireGuard UDP port                                                 | `51820`                   | No       |
| `DEFAULT_POOL`             | IP pools for new clients                                           | `10.66.0.0/24,10.66.1.0/24`| No       |
| `WG_ROUTES`                | Allowed WireGuard routes                                           | `["10.250.0.0/16",...]`   | No       |
| `FREE_CLIENT_IPS_KEY`      | Redis key for free WG IPs                                          |                           | No       |
| `ALLOCATED_CLIENT_IPS_KEY` | Redis key for allocated WG IPs                                     |                           | No       |
| `WG_MAX_RETRIES`           | Retry attempts for WG operations                                   | `5`                       | No       |
| `WG_BACKOFF_FACTOR`        | Backoff factor between WG retries                                  | `0.2`                     | No       |
| `LOGGERS`                  | Tuple of loggers for third-party libs                              | `("uvicorn.asgi",...)`    | No       |

---

## Redis Configuration

- **Connection URL:** constructed as `redis://[user:pass@]host:port`  
- **Connection Pool:** max 200 simultaneous connections  
- **Databases Usage:**  
  - DB 0: general cache & key‐value state  
- **Pub/Sub Channels:**  
  - `udpu-events`: domain events (e.g., router_created, config_updated)  
- **Key Naming Patterns:**  
  - Stamps: `STAMP:<mac_address>`  
  - VBCE entities: `VBCE:<name>`  
  - VBUser entities: `VBUSER:<uid>`  
  - Jobs: `JOB:<uid>`  
  - Job Logs: `JOB:LOGS_<job_name>_<timestamp>`  
  - WireGuard status: `WG:STATUS`  

---

## Startup & Shutdown Events

On FastAPI startup:

1. **Connect to Redis** with timeout and pool settings  
2. **Register** to discovery-service (via HTTP POST)  
3. **Start schedulers:**  
   - **Generic scheduler** triggers every 30 seconds  
   - **VBCE scheduler** triggers every 2 minutes for rate calculations  

On shutdown:

- Close Redis connections  
- Shutdown scheduler gracefully  

---

## Domain Business Logic

### Authentication (Stamps)

- **Purpose:** Secure initial device registration via a one-time stamp.  
- **Flow:**  
  1. Client requests a stamp → `POST /stamps` → StampService creates entry in Redis if not exists.  
  2. Client retrieves stamp → `GET /stamps/{mac}` → StampService returns stored body.  
  3. Stamp is deleted after use → `DELETE /stamps/{mac}`.  
- **Storage:** Redis key `STAMP:<mac_address>` with TTL matching stamp validity.

### Job Logs

- **Purpose:** Capture stdout/stderr of background jobs.  
- **Flow:**  
  1. Job execution writes log data via JobLogService (`append` model).  
  2. Logs stored in Redis list or hash under key `JOB:LOGS:<job>:<timestamp>`.  
  3. Retrieval endpoints:  
     - `POST /logs/jobs` to create a log entry.  
     - `GET /logs/jobs/{job_name}` to list logs for a job.  

### Jobs Management

- **Purpose:** Define and schedule recurring tasks.  
- **Flow:**  
  1. CRUD on jobs via REST: `POST /jobs`, `GET /jobs/{id}`, `PATCH /jobs/{id}`, `DELETE /jobs/{id}`.  
  2. Jobs have properties: name, command (shell to execute), frequency (e.g., on first_boot), role, etc.  
  3. Scheduler picks jobs by role & frequency (`get_by_role`) and triggers execution.  

### VBCE

- **Purpose:** Manage CE (Concentrator Equipment) capacity and metrics.  
- **Data Model:** name, description, max_users, current_users, available_users, IP address.  
- **Flow:**  
  1. CRUD endpoints: `POST /vbces`, `GET /vbces/{name}`, etc.  
  2. On create/update, maintain a Redis Set `vbce_locations_list` of locations.  
  3. Every 2 minutes, VBCE scheduler recalculates per-CE metrics:  
     - Minimum, maximum, mean rates across associated VBUsers.  
     - Updates Redis hash `VBCE:<name>` with new metrics.

### VBUser

- **Purpose:** Represent subscriber endpoints connected to VBCE.  
- **Flow:**  
  1. Assign a unique UID (UUID5) on creation.  
  2. Endpoints: `POST /vbusers`, `GET /vbusers/{id}`, `GET /vbusers`.  
  3. On creation: validate location existence, update VBCE current_users count.

### Northbound (Device Onboarding)

- **Purpose:** “Northbound” API for routers to register/connect.  
- **Flow:**  
  1. Router calls `POST /northbound` with subscriber info.  
  2. Service checks existing VBUser; if missing → creates VBUser and assigns a VBCE.  
  3. If no VBCE has capacity → error or unregistered branch.  
  4. Stores device data under `unregistered:<subscriber_uid>` if not onboarded.  
  5. Provides `GET /unregistered_devices` to review failed registrations.

### Roles

- **Purpose:** Define network roles (e.g., VLANs, port settings).  
- **Flow:**  
  1. `POST /roles` to create a role.  
  2. `GET /roles`, `GET /roles/{name}` to list and retrieve.  
  3. `POST /roles/{name}/clone` to clone settings to a new role.  
  4. `DELETE /roles/{name}`, `PATCH /roles/{name}` to manage definitions.  
  5. Used by Northbound & VBUser domains to validate and apply role settings.

### WireGuard Management

- **Purpose:** Manage WireGuard VPN interface and peers.  
- **Flow:**  
  1. `GET /wireguard/status` reports interface status.  
  2. `POST /wireguard/peers` to add a peer: generates config, updates `/etc/wireguard/wg0.conf`.  
  3. `DELETE /wireguard/peers` to remove a peer.  
  4. Peer list via `GET /wireguard/peers`.  
- **State Persistence:**  
  - Peer public/private keys stored in Redis under `wireguard:server:public:key` etc.  
  - Interface up/down status in Redis key `WG:STATUS`.

### WebSocket Pub/Sub

- **Purpose:** Real-time updates for clients.  
- **Flow:**  
  1. WebSocket endpoint at `/pubsub`.  
  2. Clients subscribe with query params (queue name or ID).  
  3. Server listens to job queue events (via Redis Pub/Sub) and pushes JSON updates.  
  4. Heartbeat and reconnection logic handle disconnects.

### Health Check

- **Endpoint:** `GET /health`  
- **Response:** `{ "status": "success" }`  
- **Usage:** Basic readiness probe for orchestrators.

---

## Build & Run

```bash
# Build Docker image
cd api-service/docker
docker build -t udpu-api:latest .

# Run locally
docker run --env-file .env.api.dev -p 8888:8888 udpu-api:latest

# Via Docker Compose
# Add api service to root docker-compose.yml, then:
docker-compose up -d api
```

