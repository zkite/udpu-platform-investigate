# Discovery Service – Detailed Documentation

This README provides an overview of the **discovery-service** component of the UDPU platform. It focuses on environment variables, scanning and scheduling configuration, Redis usage, event handling, and the business logic of device discovery and status monitoring.

---

## Table of Contents

1. [Overview](#overview)  
2. [Environment Variables](#environment-variables)  
3. [Scanning & Scheduling Configuration](#scanning--scheduling-configuration)  
4. [Redis Configuration](#redis-configuration)  
5. [Event Handling](#event-handling)  
6. [Domain Business Logic](#domain-business-logic)  
   - [Device Discovery](#device-discovery)  
   - [Status Monitoring](#status-monitoring)  
   - [Platform Health](#platform-health)  
7. [API Endpoints](#api-endpoints)  
8. [Build & Run](#build--run)  
9. [Next Steps & Best Practices](#next-steps--best-practices)  

---

## Overview

**discovery-service** is responsible for:

- Scanning the network to detect routers and devices  
- Periodically polling device status
- Recording discovery results and status changes  
- Caching discovery data for fast lookup  
- Emitting domain events for new devices or status changes  
- Exposing REST endpoints for inventory and status queries  

Built with **Python 3.11**, **FastAPI**, using **APScheduler** for scheduling tasks, and **Redis** for caching and Pub/Sub.

---

## Environment Variables

All settings are loaded via Pydantic in `app/core/settings.py`. Variables can be set in `.env` files or via CI/CD.

| Variable                       | Description                                                     | Example                   | Required |
|--------------------------------|-----------------------------------------------------------------|---------------------------|----------|
| `UDPU_ENVIRONMENT`             | Environment (`dev`, `test`, `prod`)                            | `dev`                     | Yes      |
| `DISCOVERY_HOST`               | Host to bind the REST server                                    | `0.0.0.0`                 | Yes      |
| `DISCOVERY_PORT`               | Port for the REST server                                        | `8886`                    | Yes      |
| `REDIS_HOST`                   | Redis hostname/IP                                               | `redis`                   | Yes      |
| `REDIS_PORT`                   | Redis port                                                      | `6379`                    | Yes      |
| `REDIS_DB`                     | Redis database index                                            | `2`                       | No (default: 0) |
| `REDIS_SCAN_KEY`               | Redis key prefix for discovered devices                         | `discovery:devices`       | No       |
| `PING_TIMEOUT`                 | Timeout, in seconds, for ICMP ping                              | `1`                       | No       |
| `SNMP_RETRIES`                 | Number of SNMP retry attempts                                   | `2`                       | No       |
| `SNMP_TIMEOUT`                 | Timeout, in seconds, for SNMP queries                            | `2`                       | No       |
| `HTTP_RETRY_COUNT`             | HTTP retry attempts for custom probes                           | `3`                       | No       |
| `SCAN_INTERVAL_SECONDS`        | Interval, in seconds, between full network scans                | `300`                     | No       |
| `STATUS_POLL_INTERVAL_SECONDS` | Interval, in seconds, for status polling of known devices       | `60`                      | No       |
| `MAX_THREADS`                  | Max threads for parallel scanning                               | `10`                      | No       |
| `LOG_LEVEL`                    | Logging level (`DEBUG`, `INFO`, etc.)                           | `INFO`                    | No       |
| `EVENT_CHANNEL`                | Redis Pub/Sub channel for emitted discovery events              | `udpu-events`             | No       |
| `HEALTH_CHECK_PATH`            | Path for health endpoint                                        | `/health`                 | No       |
| `DOCS_URL`                     | FastAPI docs URL path                                           | `/docs`                   | No       |
| `OPENAPI_URL`                  | FastAPI OpenAPI JSON URL                                        | `/openapi.json`           | No       |
| `REDOC_URL`                    | Redoc UI URL path                                               | `/redoc`                  | No       |
| `TITLE`                        | Swagger UI title                                                | `uDPU Discovery Service`  | No       |
| `VERSION`                      | API version                                                     | `0.1.0`                   | No       |

---

## Scanning & Scheduling Configuration

- **Full Network Scan** (`SCAN_INTERVAL_SECONDS`):  
  - Discovers new devices periodically (default every 5 minutes).  
  - Uses ICMP ping first, then SNMP/HTTP probes for detailed info.  
- **Status Polling** (`STATUS_POLL_INTERVAL_SECONDS`):  
  - Monitors known devices at shorter intervals (default every 60 seconds).  
  - Updates status, uptime, CPU/memory via SNMP or REST API.  
- **Concurrency**:  
  - Scans run in parallel using a thread pool (`MAX_THREADS`).  
- **Scheduler**:  
  - Implemented with APScheduler on FastAPI startup.  
  - Schedules two jobs: `full_scan_job` and `status_poll_job`.  
- **Dynamic Adjustment**:  
  - Service can reload intervals at runtime via `PATCH /config` endpoint.  

---

## Redis Configuration

- **Connection URL:** `redis://host:port/db`  
- **Caching:**  
  - Discovered device details stored under key `discovery:devices:<ip>` (hash with metadata).  
  - Status history lists: `discovery:status:<ip>` stores timestamped status.  
- **Pub/Sub:**  
  - Publishes events on `EVENT_CHANNEL` when new device found or status changes.  
- **TTL & Expiry:**  
  - Device cache entries expire after 24 hours unless refreshed.  
  - Status history trimmed to last 100 entries per device.  

---

## Event Handling

- **Published Events:**  
  - `device_discovered` (on new device detection)  
  - `device_status_changed` (when status differs from last poll)
  
- **Subscribers:**  
  - `api-service` listens to react on discovery events  
  - `repository-service` persists inventory data  

---

## Domain Business Logic

### Device Discovery

- **Objective:** Identify active routers and devices on the network.  
- **Flow:**  
  1. **Full Scan Job** runs: ping each IP in subnet list.  
  2. On ping reply, perform SNMP/HTTP probe to gather metadata (model, firmware).  
  3. Store metadata in Redis and emit `device_discovered` if new.  

### Status Monitoring

- **Objective:** Track uptime and health of known devices.  
- **Flow:**  
  1. **Status Poll Job** runs: iterate devices from Redis.  
  2. Poll SNMP for CPU, memory, interface stats; HTTP for custom endpoints.  
  3. Compare with last status; if changed, emit `device_status_changed`.  
  4. Append entry to status history in Redis.  

### Platform Health

- **Self-check:**  
  - `GET /health` returns service status and last successful scan timestamps.  

---


## Build & Run

```bash
# Build Docker image
cd discovery-service/docker
docker build -t udpu-discovery:latest .

# Run locally
docker run --env-file .env.discovery.dev -p 8886:8886 udpu-discovery:latest

# Via Docker Compose
# Add discovery service to root docker-compose.yml, then:
docker-compose up -d discovery
```


