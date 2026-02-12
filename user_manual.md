# uDPU Platform User Manual

## 1. Purpose and Audience

This document provides a complete, business-oriented description of the current uDPU platform implementation across:

- `api-service`
- `discovery-service`
- `repository-service`
- `docker-compose.yml` runtime setup

Primary audience:

- QA engineers validating business behavior and API workflows
- Business/System analysts working with platform capabilities and data contracts

The manual includes:

- product/service overview
- endpoint catalogs
- data models
- essential technical context required for testing and analysis

---

## 2. Platform Overview

### 2.1 What the platform does

uDPU platform provides centralized management of network devices and supporting operational services:

- device lifecycle management (registration, updates, assignment, status tracking)
- role/profile management for provisioning behavior
- job and queue orchestration metadata
- stamp management for MAC-based identity records
- WireGuard control APIs
- real-time command/event exchange over WebSocket
- service discovery registry
- software repository metadata registry

### 2.2 Main services

1. `api-service`
- Core business API for UDPU, roles, VBCE/VBUser, jobs/queues, logs, stamps, WireGuard, websocket flows.

2. `discovery-service`
- Service registry for platform services (host/port/type records).

3. `repository-service`
- Metadata registry for downloadable software artifacts.

4. `redis`
- Shared data store used by all backend services.

5. `frontend`
- UI client consuming `api-service`.

---

## 3. Deployment and Runtime

### 3.1 Docker Compose model

Runtime file: `docker-compose.yml`

Key characteristics:

- all backend services run in `network_mode: "host"`
- Redis persists data in volume `redis-data` mounted at `/data`
- `api-service` runs privileged and mounts `/lib/modules` for WireGuard-related operations
- `frontend` points to `API_BASE_URL=http://localhost:8888`

### 3.2 Environment profiles

Supported environment profiles in repository:

- `local`
- `dev`
- `stage`

Each profile has service-specific env files:

- `api-service/.env.api.<env>`
- `discovery-service/.env.discovery.<env>`
- `repository-service/.env.repo.<env>`

### 3.3 Standard run commands

Start:

```bash
cd <project_root>
ENV=<environment> docker compose up --build -d
```

Stop:

```bash
cd <project_root>
ENV=<environment> docker compose down -v --remove-orphans
```

---

## 4. API Conventions

### 4.1 Base path

All HTTP APIs are exposed under:

- `/api/v1.0`

### 4.2 General behavior

- JSON request bodies in `api-service` are normalized by middleware (whitespace collapse + minification) before endpoint processing.
- CORS is enabled with service settings (`allowed_hosts`, default permissive).
- Health endpoints are available in all three backend services.

### 4.3 Error envelope

Error payload style is domain/service-specific:

- some domains return `{"message": "..."}`
- services with custom exception handlers return `{"errors": [...]}`

---

## 5. api-service

### 5.1 Service mission

`api-service` is the main business API for network device provisioning and operations.

### 5.2 Startup behavior

On startup:

- connects to Redis
- starts scheduler for periodic service registration to `discovery-service` (every 30 seconds)

On shutdown:

- closes Redis connection
- stops scheduler

### 5.3 Domain map

`api-service` includes the following API domains:

1. Health Check
2. UDPU (Northbound)
3. Roles
4. VBCE
5. VBUser
6. Jobs
7. Job Queues
8. Stamps (Authentication)
9. Job Logs
10. WireGuard
11. Real-Time WebSocket

---

## 6. api-service Domain Details

### 6.1 Health Check

Endpoint:

- `GET /api/v1.0/health`

Response:

- `{"status": "success"}`

---

### 6.2 UDPU (Northbound Domain)

#### Business overview

Manages uDPU subscriber/device lifecycle, provisioning context, location assignment, role association, and runtime status.

#### API endpoints

- `POST /api/v1.0/udpu`
- `GET /api/v1.0/udpu/locations`
- `GET /api/v1.0/{location_id}/udpu_list`
- `PUT /api/v1.0/udpu_bulk/{location_id}`
- `GET /api/v1.0/subscriber/{subscriber_uid}/udpu`
- `GET /api/v1.0/adapter/{mac_address}/udpu`
- `PUT /api/v1.0/subscriber/{subscriber_uid}/udpu`
- `PUT /api/v1.0/adapter/{mac_address}/udpu`
- `DELETE /api/v1.0/subscriber/{subscriber_uid}/udpu`
- `DELETE /api/v1.0/adapter/{mac_address}/udpu`
- `POST /api/v1.0/unregistered_device`
- `GET /api/v1.0/unregistered_devices`
- `GET /api/v1.0/udpu/{subscriber_uid}/status`
- `POST /api/v1.0/udpu/status`
- `GET /api/v1.0/udpu/status`

#### Data models

`Udpu` key fields:

- `subscriber_uid`
- `location`
- `mac_address`
- `role`
- `upstream_qos`
- `downstream_qos`
- `hostname`
- `pppoe_username`
- `pppoe_password`
- `wg_server_public_key`
- `wg_interface`
- `wg_server_port`
- `wg_server_ip`
- `wg_client_ip`
- `wg_routes`
- `wg_allowed_ips`
- `endpoint`

`UdpuUpdate` key fields:

- `subscriber_uid`
- `location`
- `mac_address`
- `role`
- `upstream_qos`
- `downstream_qos`
- `provisioned_last_date`

`UnregisteredDevice`:

- `subscriber_uid`
- `last_call_home_dt`
- `ip_address`

`UdpuStatus`:

- `subscriber_uid`
- `state`
- `status`
- `created_at`

#### Business rules

- validates MAC/hostname formats
- validates role existence
- checks uniqueness for subscriber/mac/hostname on create flow
- supports location-based bulk updates
- supports status ingestion and status listing

#### Technical aspects (for QA/BA context)

- Redis is used for entity storage and index sets/maps:
  - `UDPU:{subscriber_uid}`
  - `MA:{mac_address}`
  - location and per-location sets
- WireGuard client IPs are allocated from Redis-backed pools.
- status freshness logic marks stale statuses as offline based on threshold timing.

---

### 6.3 Roles

#### Business overview

Provides reusable role templates used by provisioning and interface mapping.

#### API endpoints

- `POST /api/v1.0/roles`
- `GET /api/v1.0/roles/{name}`
- `GET /api/v1.0/roles`
- `PATCH /api/v1.0/roles/{name}`
- `POST /api/v1.0/roles/clone`
- `DELETE /api/v1.0/roles/{name}`

#### Data model

`UdpuRole`:

- `name`
- `description`
- `wireguard_tunnel`
- `job_control`
- `interfaces`

`interfaces` structure:

- `management_vlan.interface`
- `ghn_ports[]`:
  - `ghn_interface`
  - `lcmp_interface`
  - `vb`

#### Business rules

- unique role naming
- role clone from source to new target name
- role update and delete by role name

#### Technical aspects

- role rename workflow updates role references in related domain entities.

---

### 6.4 VBCE

#### Business overview

Represents endpoint capacity objects tied to location usage and user assignment context.

#### API endpoints

- `POST /api/v1.0/vbce`
- `GET /api/v1.0/vbce/{vbce_name}`
- `PATCH /api/v1.0/vbce/{vbce_name}`
- `DELETE /api/v1.0/vbce/{vbce_name}`
- `GET /api/v1.0/vbces`
- `GET /api/v1.0/vbce/locations`

#### Data model

`Vbce` key fields:

- `name`
- `description`
- `max_users`
- `current_users`
- `available_users`
- `ip_address`
- `tcp_port`
- `location_id`
- `is_empty`
- `is_full`
- `force_local`
- `lq_min_rate`
- `lq_max_rate`
- `lq_mean_rate`
- `seed_idx_used`

#### Business rules

- unique VBCE name
- location uniqueness checks during registration
- max/current/available users managed through create/patch workflows
- IP/port validation in request models

---

### 6.5 VBUser

#### Business overview

Provides VBUser retrieval and update flows, including interface enrichment tied to role definitions.

#### API endpoints

- `GET /api/v1.0/vbuser/{vb_uid}`
- `PATCH /api/v1.0/vbuser/{vbu_uid}`
- `GET /api/v1.0/vbusers`

#### Data model

`VBUser` key fields:

- `udpu`
- `ghn_interface`
- `lcmp_interface`
- `location_id`
- `upstream_qos`
- `downstream_qos`
- `seed_idx`
- `lq_min_rate`
- `lq_max_rate`
- `lq_current_rate`
- `force_local`
- `ghn_password`
- `ghn_dm_mac`
- `ghn_ep_mac`
- `ghn_firmware`
- `ghn_profile`
- computed `vb_uid`

#### Technical aspects

- VBUser details can be enriched using role-derived primary interfaces.
- location-related seed index is used for assignment context.

---

### 6.6 Jobs

#### Business overview

Stores and manages executable job definitions used in operational command workflows.

#### API endpoints

- `GET /api/v1.0/jobs`
- `POST /api/v1.0/jobs`
- `GET /api/v1.0/jobs/{identifier}`
- `PATCH /api/v1.0/jobs/{identifier}`
- `DELETE /api/v1.0/jobs/{identifier}`
- `GET /api/v1.0/roles/{role_name}/jobs`
- `GET /api/v1.0/jobs/frequency/{frequency}`

#### Data model

`JobSchema` key fields:

- `name`
- `description`
- `command`
- `require_output`
- `required_software`
- `frequency`
- `locked`
- `role`
- `type`
- `vbuser_id`
- computed `uid`

`JobFrequency` values:

- `1`
- `15`
- `60`
- `1440`
- `first_boot`
- `every_boot`
- `once`

#### Business rules

- unique job name on creation
- retrieve by identifier (name or UID)
- role-based and frequency-based job filtering

---

### 6.7 Job Queues

#### Business overview

Manages grouped collections of jobs for queue-based execution scenarios.

#### API endpoints

- `GET /api/v1.0/queues`
- `POST /api/v1.0/queues`
- `GET /api/v1.0/queues/{identifier}`
- `PATCH /api/v1.0/queues/{identifier}`
- `DELETE /api/v1.0/queues/{identifier}`
- `GET /api/v1.0/roles/{role_name}/queues`

#### Data model

`JobQueueSchema` key fields:

- `name`
- `description`
- `queue`
- `role`
- `require_output`
- `locked`
- `frequency`
- computed `uid`

---

### 6.8 Stamps (Authentication Domain)

#### Business overview

Stores per-device stamp payloads indexed by MAC address for identity-oriented workflows.

#### API endpoints

- `POST /api/v1.0/stamps`
- `GET /api/v1.0/stamps`
- `GET /api/v1.0/stamps/{mac_address}`
- `DELETE /api/v1.0/stamps/{mac_address}`

#### Data model

`Stamp`:

- `mac_address`
- `body`

#### Business rules

- MAC address is validated by schema pattern.
- one stamp record per MAC key.

---

### 6.9 Job Logs

#### Business overview

Persists structured job execution logs for audit and troubleshooting.

#### API endpoints

- `GET /api/v1.0/logs/jobs`
- `POST /api/v1.0/logs/jobs`
- `GET /api/v1.0/logs/jobs/{job_name}`

#### Data model

`JobLogSchema`:

- `client`
- `name`
- `command`
- `std_err`
- `std_out`
- `status_code`
- `timestamp`

---

### 6.10 WireGuard

#### Business overview

Provides API-based interface and peer management for WireGuard operations.

#### API endpoints

- `GET /api/v1.0/wireguard/status`
- `POST /api/v1.0/wireguard/up`
- `POST /api/v1.0/wireguard/down`
- `GET /api/v1.0/wireguard/peers`
- `POST /api/v1.0/wireguard/peer/add`
- `POST /api/v1.0/wireguard/peer/remove`

#### Data models

`InterfaceStatus`:

- `interface`
- `active`

`Peer`:

- `public_key`
- `allowed_ips`
- `endpoint`
- `persistent_keepalive`

`PeerRemove`:

- `public_key`

#### Technical aspects

- operations are executed through system tools (`systemctl`, `wg`, `wg-quick`) via backend manager logic
- peer changes are persisted with `wg-quick save`

---

### 6.11 Real-Time WebSocket

#### Business overview

Enables bidirectional real-time command/event exchange through Redis streams.

#### WebSocket endpoints

- `WS /api/v1.0/pubsub?channel=<client_id>`
- `WS /api/v1.0/pub?channel=<client_id>`

#### Supported command patterns

- `run queue <identifier>`
- `run job <identifier>`
- `run job status`

#### Technical aspects

- stream operations use Redis `XREAD`/`XADD`/`XDEL`
- `/pubsub` and `/pub` separate client-facing and UI-facing interaction paths

---

## 7. discovery-service

### 7.1 Service mission

`discovery-service` is the service registry of the platform.

It stores and returns service instances by type to support runtime service visibility.

### 7.2 API endpoints

- `GET /api/v1.0/health`
- `GET /api/v1.0/services?service_type={service_type}`
- `POST /api/v1.0/services`

### 7.3 Data model

`ServiceDiscoverySchema`:

- `host`
- `port`
- `service_type`

### 7.4 Business behavior

- register service instance records
- retrieve all records for a given `service_type`
- provide health response for operational checks

### 7.5 Technical aspects

- Redis key prefix: `SERVICE_DISCOVERY`
- key format: `SERVICE_DISCOVERY_{service_type}_{host}_{port}`
- startup/shutdown hooks manage Redis connection lifecycle
- API and repository services periodically register themselves in this registry

---

## 8. repository-service

### 8.1 Service mission

`repository-service` manages software artifact metadata and supports retrieval by deterministic software UID.

### 8.2 API endpoints

- `GET /api/v1.0/health`
- `POST /api/v1.0/repo`
- `GET /api/v1.0/repo/{software_uid}`
- `PATCH /api/v1.0/repo/{software_uid}`
- `DELETE /api/v1.0/repo/{software_uid}`

### 8.3 Data model

`Repository`:

- `description`
- `locked`
- `url`
- `password`
- `software_uid`
- `sha256_checksum`
- `number_of_downloads`

### 8.4 Core business flow

1. Create repository metadata:
- compute `software_uid` from URL/password
- compute SHA-256 checksum of downloaded content
- store metadata in Redis

2. Retrieve repository metadata:
- read by `software_uid`
- update `number_of_downloads`

3. Patch metadata:
- update selected fields of existing repository record

4. Delete lifecycle endpoint:
- provides deletion flow endpoint for repository entity lifecycle

### 8.5 Technical aspects

- Redis key prefix: `SERVICE_REPOSITORY`
- key format: `SERVICE_REPOSITORY_{software_uid}`
- scheduler registers repository-service in discovery-service every 30 seconds with `service_type="repo"`

---

## 9. Cross-Service Integration Overview

### 9.1 Registration and discovery

- `api-service` registration payload:
  - `service_type: "server"`
  - target: `/api/v1.0/services` of discovery-service
- `repository-service` registration payload:
  - `service_type: "repo"`
  - target: `/api/v1.0/services` of discovery-service

### 9.2 Shared storage pattern

- all three services use Redis as operational datastore
- each domain uses own key prefixes to separate data spaces

### 9.3 API path consistency

- all service APIs use `/api/v1.0` base prefix

---

## 10. QA/BA Validation Guide

### 10.1 Smoke checks

Validate health endpoints:

- `/api/v1.0/health` on api-service
- `/api/v1.0/health` on discovery-service
- `/api/v1.0/health` on repository-service

### 10.2 Core business scenarios

1. UDPU lifecycle
- create, fetch, update, delete
- fetch by MAC and by subscriber UID
- status update and status listing

2. Role and profile management
- create/list/get/update/clone/delete role
- verify downstream behavior where roles are referenced

3. Capacity and assignment
- VBCE create/update/list
- VBUser get/patch/list

4. Job orchestration metadata
- Jobs and queues CRUD-style API flows
- role/frequency-based job reads

5. Security and identity records
- stamps create/read/list/delete
- MAC validation behavior

6. Artifact metadata management
- repository create/get/patch/delete flow
- download counter progression

7. Real-time communication
- websocket `/pub` and `/pubsub` command cycle

8. Service discovery
- periodic registration visibility by `service_type`
- GET filtering for `server` and `repo`

### 10.3 Data contract verification

For each domain, verify:

- request body shape matches documented model fields
- response shape contains expected business fields
- identifier-based retrieval behaves consistently (`uid`, `name`, `software_uid`, `mac_address`)

---

## 11. Quick Endpoint Index

### api-service

- Health: `/api/v1.0/health`
- UDPU/Northbound: `/api/v1.0/udpu*`, `/api/v1.0/subscriber/*`, `/api/v1.0/adapter/*`, `/api/v1.0/unregistered_*`
- Roles: `/api/v1.0/roles*`
- VBCE: `/api/v1.0/vbce*`, `/api/v1.0/vbces`
- VBUser: `/api/v1.0/vbuser*`, `/api/v1.0/vbusers`
- Jobs: `/api/v1.0/jobs*`, `/api/v1.0/roles/{role_name}/jobs`
- Queues: `/api/v1.0/queues*`, `/api/v1.0/roles/{role_name}/queues`
- Stamps: `/api/v1.0/stamps*`
- Logs: `/api/v1.0/logs/jobs*`
- WireGuard: `/api/v1.0/wireguard*`
- WebSocket: `/api/v1.0/pub`, `/api/v1.0/pubsub`

### discovery-service

- Health: `/api/v1.0/health`
- Services: `/api/v1.0/services`

### repository-service

- Health: `/api/v1.0/health`
- Repository: `/api/v1.0/repo*`

