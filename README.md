# uDPU Platform – Quick Start & Overview

This document describes the overall UDPU platform for home router management. It explains service interactions, Docker Compose orchestration, and common Docker commands for development and troubleshooting.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)  
2. [Docker Compose Configuration](#docker-compose-configuration)  
3. [Environment & Startup Commands](#environment--startup-commands)  
4. [Managing Containers](#managing-containers)  
   - [List Running Containers](#list-running-containers)  
   - [Inspect Logs](#inspect-logs)  
   - [Execute Commands Inside Containers](#execute-commands-inside-containers)  
   - [Stop & Remove Containers](#stop--remove-containers)  
5. [Service Details](#service-details)  
6. [Next Steps](#next-steps)  

---

## Architecture Overview

The UDPU platform consists of the following microservices and components:

- **api-service**  
  - Gateway API for client interactions.  
  - Handles authentication, routing, and event orchestration.

- **discovery-service**  
  - Scans configured subnets to discover routers and devices.  
  - Polls device status and emits discovery/status events.

- **repository-service**  
  - Stores metadata about software repositories and router configurations.  
  - Provides CRUD operations and simple analytics (download counts).

- **Redis**  
  - Central data store for caching, Pub/Sub events, and simple key–value persistence.  
  - Shared by all services via the `backend` network.

All services communicate over an internal Docker network (`backend`). Discovery and repository services publish events on a Redis Pub/Sub channel (`udpu-events` by default), which `api-service` subscribes to for orchestration.

---

## Environment & Startup Commands

Set the desired environment before running Compose. For example, to use the `test` configuration:

```bash
sudo env ENV=test docker compose up --build
```

- **`ENV=test`**  
  - Used by each service to load `.env.*` files (e.g. `.env.api.test`, `.env.discovery.test`, `.env.repo.test`).
- **`--build`**  
  - Forces rebuild of service images before starting.

To stop and remove containers, networks, and volumes:

```bash
sudo env ENV=test docker compose down -v
```

- **`-v`**  
  - Removes associated volumes (e.g. `redis-data`).

---

## Managing Containers

### List Running Containers

```bash
docker ps
```

- Shows container ID, name, image, status, and exposed ports.
- Example output:
  ```
  CONTAINER ID   IMAGE              NAMES              STATUS          PORTS
  abcd1234efgh   udpu-api:dev       api-service        Up 5 seconds    0.0.0.0:8888->8888/tcp
  ijkl5678mnop   udpu-discovery:dev discovery-service  Up 5 seconds    0.0.0.0:8886->8886/tcp
  wxyz3456qrst   udpu-repo:dev      repository-service Up 5 seconds    0.0.0.0:8887->8887/tcp
  ```

### Inspect Logs

```bash
docker logs <container_name>
```

- E.g. `docker logs api-service`
- For real-time logs: `docker logs -f api-service`

### Execute Commands Inside Containers

```bash
docker exec -it <container_name> /bin/bash
```

- Opens an interactive shell in the container.
- Useful for debugging, inspecting files, or running service commands.

### Stop & Remove Containers

- **Stop a single container:**
  ```bash
  docker stop <container_name>
  ```
- **Remove a container:**
  ```bash
  docker rm <container_name>
  ```

---

## Service Details

| Service                | Port  | Purpose                                         |
|------------------------|-------|-------------------------------------------------|
| `api-service`          | 8888  | REST gateway, authentication, event routing     |
| `discovery-service`    | 8886  | Network scanning, status polling, event emit    |
| `repository-service`   | 8887  | Metadata storage, CRUD operations, analytics    |
| `redis`                | 6379  | Caching, Pub/Sub, key-value persistence         |

Each service reads its specific environment file:
- `api-service/.env.api.${ENV}`
- `discovery-service/.env.discovery.${ENV}`
- `repository-service/.env.repo.${ENV}`

They connect to Redis at `redis:6379` on network `backend`.

---

