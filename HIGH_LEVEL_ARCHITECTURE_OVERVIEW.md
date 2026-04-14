# High-Level Architecture Overview

## 1. Architecture Goals

- Privacy first: Minimize transmission of raw biometric data over public internet.
- Low latency: Target sub-second identification to prevent hallway congestion.
- Offline resilience: Keep attendance operations running even when external internet is unavailable.

## 2. Architecture Style

Distributed microservices with edge intelligence:

- Localized edge nodes perform AI inference close to cameras.
- A centralized cloud hub orchestrates data, policy, and reporting.

## 3. High-Level Layers

- Perception / Device Layer (hardware and sensing)
- Edge Computing Layer (local processing)
- Presentation Layer (web/mobile/kiosk)
- API Gateway / Access Layer
- Application / Service Layer
- AI and Analytics Layer
- Data Layer (SQL plus vector capabilities)
- Security and Compliance Layer
- Integration Layer (SIS and identity connectors)

## 4. Layer Descriptions

### 4.1 Perception / Device Layer

- RTSP IP cameras.
- Edge nodes per building (for example NUC/Jetson).
- Local preprocessing (frame capture and basic filtering).

### 4.2 Edge Computing Layer

- Real-time inference pipeline: face detection -> liveness -> ArcFace embedding -> comparison against cached active student subset.
- Local caching of active semester embeddings.
- Local logging of rejected attempts.
- Attendance decision and deduplication within a configurable time window.
- Offline-first behavior with delayed cloud sync.

### 4.3 Presentation Layer

- Admin dashboard (React web app) for roster and report management.
- Security app (Flutter mobile app) for real-time alerts.
- Check-in kiosk for visitor self-registration.
- Web/mobile portals for admin/teacher/parent/student views.
- Push/email/SMS notifications.

### 4.4 API Gateway / Access Layer

- Technology target: NGINX or Kong.
- Single entry point.
- SSL termination.
- Rate limiting and request routing to internal services.

### 4.5 Application / Service Layer

- Attendance Service.
- Enrollment Service.
- Notification Service.
- Business logic (example: late policy after 8:15 AM).

### 4.6 AI and Analytics Layer

- Edge inference with Python (PyTorch/TensorFlow compatible stack).
- Local AI runtime on edge hardware.
- Face detection, liveness checks, and 512-dimension ArcFace embeddings.

### 4.7 Data Layer

- Cloud SQL (PostgreSQL) for student metadata, schedules, attendance logs, watchlists, and audits.
- Encrypted embeddings at rest (pgcrypto).
- Vector search support via vector DB (Milvus/Pinecone) or indexed SQL approaches for cosine similarity.

### 4.8 Security and Compliance Layer

- IdP target: Auth0 or Keycloak with MFA.
- Secret management target: Vault-backed keys and SIS credentials.

### 4.9 Integration Layer

- SIS and identity connectors (for example PowerSchool, Google Classroom, and Microsoft Active Directory).

## 5. Data Flow Overview

1. Capture: IP camera streams RTSP video to local edge node.
2. Inference: Edge node detects face, produces embedding, and compares against local cache.
3. Action: On match, edge sends lightweight JSON event (identity plus timestamp) to cloud backend.
4. Notification: Cloud backend persists event and pushes updates to presentation layer.

## 6. Deployment Concept

- Edge: containerized services on-site (K3s target).
- Cloud: AWS or Azure GovCloud for compliance-focused hosting.

## 7. Scalability Strategy

- Horizontal scaling: add edge nodes per building/camera growth.
- Data partitioning/sharding by district or tenant for sustained query performance.

## 8. Performance Optimization Plan

- Model quantization for faster inference on cost-effective edge hardware.
- Edge RAM cache for current roster embeddings.

## 9. Fault Tolerance and Reliability

- Local buffer and retry sync when cloud connection is unavailable.
- High availability with load balancing across cloud instances.

## 10. Accessibility and Inclusivity Planning

- Bias auditing and fairness monitoring across demographic groups.
- Height-adaptive camera positioning for K-12 range.

## 11. Monitoring and Logging Architecture

- Prometheus for metrics.
- Grafana for visualization.
- Alerting on camera offline and high edge node CPU utilization.

## 12. Future Architecture Extensions

- Thermal sensor integration.
- Multi-modal biometrics (face plus voice) for higher-security zones.

## Summary Insight

This architecture balances the speed of local inference with centralized cloud governance. Keeping biometric vectors local and sending only lightweight match events reduces breach blast radius while preserving operations during external network outages.

---

## Current Project Alignment Inspection (as of 2026-03-24)

### Alignment Snapshot

- Aligned: AI inference pipeline, modular services, PostgreSQL persistence, edge node management primitives, React dashboard.
- Partially aligned: API gateway, offline resilience, vector strategy, security hardening, deployment model, monitoring.
- Not yet implemented: SIS connectors, dedicated mobile app, K3s manifests, Prometheus/Grafana stack.

### Layer-by-Layer Assessment

1. Perception / Device Layer: `Partially Aligned`
- Evidence: RTSP camera credential and verification APIs exist in `backend/src/routes/camera-credentials.js`.
- Evidence: edge-to-camera assignment exists in `backend/src/routes/edge-nodes.js`.
- Gap: real RTSP stream validation is still marked TODO/simulated in `backend/src/routes/camera-credentials.js`.

2. Edge Computing Layer: `Partially Aligned`
- Evidence: edge node registration, heartbeat, camera mapping, and cache configuration are implemented in `backend/src/routes/edge-nodes.js`.
- Evidence: deduplication service and config are implemented in `backend/src/services/deduplication-service.js`.
- Gap: local offline event queue + replay sync mechanism is not concretely implemented in runtime code (no durable edge-side buffer worker/process found).

3. Presentation Layer: `Partially Aligned`
- Evidence: React dashboard exists (`frontend/src/App.jsx`, `frontend/src/pages/Dashboard.jsx`, `frontend/src/components/*`).
- Evidence: local face demo/kiosk-like pages exist (`backend/public/face-ui.html`, `backend/public/arcface-capture.html`).
- Gap: no Flutter mobile app code or Dart project was found.

4. API Gateway / Access Layer: `Partially Aligned`
- Evidence: backend is a single API entry point via Express route mounting in `backend/src/server.js`.
- Gap: no dedicated NGINX/Kong gateway configuration is deployed in `docker-compose.yml`.

5. Application / Service Layer: `Aligned`
- Evidence: clear service and route modularization across enrollment, recognition, attendance, watchlist, analytics, overrides, edge nodes, and camera credentials in `backend/src/routes/*` and `backend/src/services/*`.

6. AI and Analytics Layer: `Aligned`
- Evidence: AI engine exposes `/extract-embedding`, `/compare-faces`, `/process-frame` with 512-d ArcFace embeddings and liveness outputs in `ai-engine/src/main.py`.
- Evidence: ArcFace + liveness implementation exists in `ai-engine/src/arcface_engine.py`.
- Evidence: analytics APIs exist in `backend/src/routes/analytics.js`.

7. Data Layer: `Partially Aligned`
- Evidence: PostgreSQL schema includes student/template/attendance/watchlist/audit tables in `database/schema.sql`.
- Evidence: encryption-related schema/services exist in `database/migrations/002_rtsp_edge_nodes_encryption_refinements.sql` and `backend/src/services/encryption-service.js`.
- Gap: production vector DB is not active in current runtime path; recognition currently does application-layer cosine comparison because pgvector is unavailable (`backend/src/routes/recognition.js`).

8. Security and Compliance Layer: `Partially Aligned`
- Evidence: API key/role middleware exists in `backend/src/middleware/auth.js`.
- Evidence: privacy and audit endpoints exist in `backend/src/routes/privacy.js`.
- Gap: `backend/src/server.js` does not mount `/api/privacy` routes (present in `server-updated.js`, but runtime entrypoint in `backend/package.json` is `src/server.js`).
- Gap: Auth0/Keycloak/MFA and external vault integration are not yet implemented in runtime.

9. Integration Layer: `Not Yet Implemented`
- Evidence: no runtime connectors for PowerSchool, Google Classroom, or Microsoft Active Directory were found in backend source.

10. Deployment and Operations: `Partially Aligned`
- Evidence: dockerized services for postgres, redis, backend, and ai-engine exist in `docker-compose.yml`.
- Gap: no Kubernetes/K3s manifests found.
- Gap: no Prometheus/Grafana deployment found.

### Notable Consistency Risks

- Some docs mention capabilities that are not active in runtime (for example full pgvector/gateway/advanced auth posture), while code paths still indicate fallback or planned state.
- There is a route registration drift between `backend/src/server.js` and `backend/src/server-updated.js` (privacy route mount).

### Recommended Next Steps to Improve Alignment

1. Add and enable a dedicated API gateway service (NGINX/Kong) in `docker-compose.yml`, with TLS termination and rate limiting policies.
2. Implement edge-side durable offline queue and cloud replay worker (with idempotent event keys).
3. Standardize vector search path: enable pgvector (or dedicated vector DB) and remove mixed fallback assumptions.
4. Switch runtime to mount privacy/auth-protected routes from `src/server.js` (or merge `server-updated.js` changes).
5. Add monitoring stack (Prometheus/Grafana) and health SLO dashboards.
6. Create SIS connector service boundaries (PowerSchool/Google Classroom/AD) and explicit sync contracts.
