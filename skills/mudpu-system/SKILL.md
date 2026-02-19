---
name: mudpu-system
description: Investigate the mUDPU platform architecture and contracts across api-service, udpu-client-golang, repository-service, discovery-service, frontend, and Redis. Use when auditing API/WebSocket contracts, Redis key-space, entity relations, bootstrap and execution flows, documentation-vs-code mismatches, operational risks, or before making cross-service contract changes.
---

# mUDPU System Investigation

## Quick Start

1. Read `references/mudpu-system-investigation.md` before making architectural claims.
2. Define the investigation scope: endpoint, flow, entity, key-space, or operational risk.
3. Run repo-wide symbol search for all related contracts and call sites.
4. Record limitations when runtime checks or full workspace access are unavailable.

## Investigation Workflow

### 1. Determine the contract surface

- Identify impacted interfaces: HTTP endpoints, WebSocket messages, Redis key patterns, schema fields, and cross-service dependencies.
- Build a checklist of direct and transitive consumers across:
  - `api-service`
  - `udpu-client-golang`
  - `repository-service`
  - `discovery-service`
  - `frontend`

### 2. Validate against code and reference

- Use `references/mudpu-system-investigation.md` as baseline map:
  - Section 3 for endpoint contracts
  - Section 4 for WebSocket protocol
  - Section 5 for Redis model
  - Sections 6-7 for entity links and end-to-end flows
  - Sections 8-9 for contradictions and operational risks
- Confirm each claim in current code.
- Treat source code as the source of truth when documentation conflicts with implementation.

### 3. Evaluate impact and cascade

- Track contract changes through all consumer call sites.
- Synchronize serialization, field names, key naming, and error-path behavior.
- Detect dynamic usage in strings/configs/DI and include it in impact analysis.

### 4. Report only verified facts

- Separate output into:
  - confirmed facts
  - unconfirmed items
  - blockers
- List executed commands/checks with actual results only.
- Mark assumptions as assumptions and avoid presenting them as facts.

## Constraints

- Keep edits minimal and avoid unrelated formatting churn.
- Do not claim runtime validation without actually running services/tests.
- Repeat repo-wide search after changes to confirm no stale patterns remain.

## Resources

- `references/mudpu-system-investigation.md`: canonical technical investigation baseline for mUDPU.
