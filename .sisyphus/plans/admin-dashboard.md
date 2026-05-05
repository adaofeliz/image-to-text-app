# Admin Dashboard with shadcn/ui

## TL;DR
> Build a shadcn/ui React dashboard served by FastAPI for monitoring OCR job processing.
>
> **Deliverables**:
> - Admin API endpoints (`/admin/api/*`) with token auth
> - React + Vite dashboard (`/dashboard`) displaying job status, history, image previews, and OCR output
> - Protected image serving endpoint
> - Docker multi-stage build integration
>
> **Estimated Effort**: Medium (Backend: ~4h, Frontend: ~4h, Integration: ~2h)
> **Parallel Execution**: YES — Backend and Frontend waves can partially overlap after contract agreement
> **Critical Path**: Admin Auth → Admin API → Frontend Contract Finalized → Frontend Pages → Docker Integration → E2E Verification

---

## Context

### Original Request
Build a simple dashboard using shadcn/ui where the admin can see OCR processing status, job history, image inputs, and OCR outputs. Protected by a simple token configured via `.env` (`DASHBOARD_TOKEN`), entered on a login page, saved to `localStorage`, and sent in the `X-Dashboard-Token` header on every admin request. Token included in `.env.example` and docker-compose files. History kept in Redis only (7-day TTL).

### Interview Summary
**Key Discussions**:
- Token entry style: Password field on login page (not Bearer token header)
- History persistence: Keep Redis only, no SQL/DB changes
- Frontend stack: React + Vite + shadcn/ui (NOT Next.js)
- Docker: Node available locally; multi-stage build preferred

**Research Findings**:
- FastAPI app serves only API + NotFound.html currently
- CORS allows all origins; 404 handler redirects externally (risks breaking SPA routing)
- Redis stores job types at `job:type:{message_id}` with 7-day TTL
- Images stored in `shared_files/` volume (mounted in Docker)
- Node v22 available locally for building

### Metis Review
**Identified Gaps** (addressed):
- Dashboard URL structure → SPA served at `/dashboard`, API at `/admin/api/*`
- Real-time updates → Polling every 5 seconds (manual refresh fallback)
- Admin actions → Read-only (no delete/re-run/download)
- Mobile responsiveness → Basic responsive table
- Job filtering → Status filter (all/pending/finished/failed)
- Token format → Simple string in `DASHBOARD_TOKEN` env var
- SPA routing conflicts → Mount StaticFiles LAST with `html=True` for fallback

---

## Work Objectives

### Core Objective
Add a password-protected admin dashboard to the existing Image-to-Text API that exposes job history, image previews, and OCR results without modifying the existing API or worker behavior.

### Concrete Deliverables
- `app/routes/admin.py` — Admin API router with 4 endpoints
- `app/dependencies/admin_auth.py` — Token validation dependency
- `app/static/dashboard/` — Built React SPA (generated from `app/frontend/`)
- `app/frontend/` — React + Vite source code (3 pages: Login, Dashboard, Job Detail)
- Updated `Dockerfile` — Multi-stage build (Node build + Python serve)
- Updated `docker-compose.yml` and `docker-compose.prod.yml` — Include `DASHBOARD_TOKEN`
- Updated `.env.example` — Include `DASHBOARD_TOKEN`
- Updated `requirements.txt` — Add `python-multipart` (if not present) and verify FastAPI static file support
- `tests/test_admin.py` — Backend admin endpoint tests

### Definition of Done
- [ ] `curl -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/jobs` returns job list
- [ ] `curl -H "X-Dashboard-Token: wrong" http://localhost:8000/admin/api/jobs` returns 403
- [ ] `curl http://localhost:8000/dashboard/login` serves HTML login page
- [ ] `docker-compose up --build` starts all services including built dashboard
- [ ] Existing `/convert/image/text`, `/job/{id}`, and `/health` endpoints remain unchanged

### Must Have
- Token-protected admin API endpoints
- Dashboard login page with token saved to localStorage
- Job list table with status filtering
- Job detail page showing OCR text and image preview
- Image serving endpoint (reads from `shared_files/`)
- Docker multi-stage build
- Polling for real-time status updates (5s interval)

### Must NOT Have (Guardrails)
- No database changes (PostgreSQL, SQLite, etc.) — Redis only
- No modification of existing API endpoints or worker logic
- No Next.js, Remix, or SSR — React + Vite only
- No user management, roles, or multi-user auth
- No admin actions beyond read (no delete, re-run, download)
- No WebSocket or Server-Sent Events
- No metrics collection beyond existing logs

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-asyncio)
- **Automated tests**: YES (Tests-after for backend, manual Playwright for frontend)
- **Framework**: pytest for backend; no existing frontend test framework
- **Agent-Executed QA**: MANDATORY for all tasks

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.
- **Frontend/UI**: Playwright (`playwright` skill) — Navigate, interact, assert DOM, screenshot
- **API/Backend**: Bash (`curl`) — Send requests, assert status + response fields
- **Library/Module**: Bash (`pytest`) — Run test files, assert output

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — Backend Scaffolding):
├── T1: Add DASHBOARD_TOKEN to .env.example + docker-compose files
├── T2: Create admin auth dependency (app/dependencies/admin_auth.py)
├── T3: Create admin API router skeleton (app/routes/admin.py)
├── T4: Add admin router to FastAPI app (app/main.py + app/routes/__init__.py)
└── T5: Create admin endpoint tests (tests/test_admin.py)

Wave 2 (Backend API + Frontend Contract):
├── T6: Implement /admin/api/jobs endpoint (Redis SCAN for job history)
├── T7: Implement /admin/api/jobs/{message_id} endpoint (job details)
├── T8: Implement /admin/api/images/{message_id} endpoint (image streaming)
└── T9: Initialize React + Vite project in app/frontend/

Wave 3 (Frontend Implementation — MAX PARALLEL after contract):
├── T10: Configure Vite build output to app/static/dashboard/
├── T11: Add shadcn/ui components (Table, Card, Badge, Button, Input, Sidebar)
├── T12: Build Login page with localStorage token auth
├── T13: Build Dashboard page with job list table + status filter + polling
└── T14: Build Job Detail page with OCR output + image preview

Wave 4 (Integration + Docker):
├── T15: Configure FastAPI StaticFiles for dashboard SPA fallback
├── T16: Update Dockerfile with multi-stage Node + Python build
├── T17: Update docker-compose.yml and docker-compose.prod.yml
└── T18: Fix 404 handler to allow SPA routing for /dashboard paths

Wave 5 (Testing + Polish):
├── T19: Run backend tests (pytest tests/test_admin.py)
├── T20: Build frontend and verify static files copied correctly
└── T21: Full Docker Compose E2E verification

Wave FINAL (After ALL tasks — 4 parallel reviews, then user okay):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real manual QA (unspecified-high)
└── F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay
```

### Dependency Matrix

| Task | Blocked By | Blocks |
|------|-----------|--------|
| T1 | - | T17, T18 |
| T2 | - | T3, T5 |
| T3 | T2 | T6, T7, T8 |
| T4 | T2, T3 | T19 |
| T5 | T2 | - |
| T6 | T3, T4 | T13, T14, T21 |
| T7 | T3, T4 | T14, T21 |
| T8 | T3, T4 | T14, T21 |
| T9 | - | T10, T11, T12, T13, T14 |
| T10 | T9 | T20 |
| T11 | T9 | T12, T13, T14 |
| T12 | T9, T11 | T13, T14, T21 |
| T13 | T6, T9, T11, T12 | T21 |
| T14 | T7, T8, T9, T11, T12 | T21 |
| T15 | - | T21 |
| T16 | T1, T10, T20 | T21 |
| T17 | T1 | T21 |
| T18 | - | T21 |
| T19 | T4, T5 | T21 |
| T20 | T10 | T16 |
| T21 | T6, T7, T8, T13, T14, T15, T16, T17, T18, T19, T20 | F1-F4 |
| F1-F4 | T21 | - |

### Agent Dispatch Summary

- **Wave 1**: T1-T5 → `quick` (all independent/config changes)
- **Wave 2**: T6-T8 → `unspecified-high` (backend logic), T9 → `quick` (scaffold)
- **Wave 3**: T10-T14 → `visual-engineering` (frontend UI work)
- **Wave 4**: T15-T18 → `unspecified-high` (integration + Docker)
- **Wave 5**: T19-T21 → `unspecified-high` (verification)
- **FINAL**: F1 → `oracle`, F2-F4 → `unspecified-high`

---

## TODOs

> Implementation + Test = ONE Task. EVERY task MUST have QA Scenarios.

### Wave 1: Foundation

- [x] T1. Add `DASHBOARD_TOKEN` env var to .env files and docker-compose

  **What to do**:
  - Add `DASHBOARD_TOKEN=` to `.env.example`
  - Add `DASHBOARD_TOKEN=${DASHBOARD_TOKEN}` to docker-compose.yml env
  - Add `DASHBOARD_TOKEN=${DASHBOARD_TOKEN}` to docker-compose.prod.yml env
  - Verify `DASHBOARD_TOKEN` is loaded by the app (it will be via `load_dotenv()`)

  **Must NOT do**:
  - Do NOT set a default/hardcoded token value
  - Do NOT modify any application code in this task

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple configuration file edits
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T17, T18
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `.env.example` contains `DASHBOARD_TOKEN=`
  - [ ] `docker-compose.yml` passes `DASHBOARD_TOKEN` to web and worker services
  - [ ] `docker-compose.prod.yml` passes `DASHBOARD_TOKEN` to web and worker services

  **QA Scenarios**:
  ```
  Scenario: Verify env var propagation
    Tool: Bash (grep)
    Steps:
      1. grep "DASHBOARD_TOKEN" .env.example docker-compose.yml docker-compose.prod.yml
    Expected Result: All three files contain DASHBOARD_TOKEN reference
    Evidence: .sisyphus/evidence/t1-env-check.txt
  ```

  **Commit**: YES
  - Message: `chore(config): add DASHBOARD_TOKEN env var`
  - Files: `.env.example`, `docker-compose.yml`, `docker-compose.prod.yml`

---

- [x] T2. Create admin authentication dependency

  **What to do**:
  - Create `app/dependencies/admin_auth.py`
  - Implement `verify_admin_token(x_token: str | None = Header(None, alias="X-Dashboard-Token"))` dependency
  - Read `DASHBOARD_TOKEN` from env via `os.getenv("DASHBOARD_TOKEN", "")`
  - Return `True` on valid token
  - Raise `HTTPException(status_code=401)` if token missing
  - Raise `HTTPException(status_code=403)` if token invalid
  - Reject empty/blank tokens (return 403)

  **Must NOT do**:
  - Do NOT use JWT or complex auth
  - Do NOT create sessions or cookies
  - Do NOT hash/compare with bcrypt (simple string equality is enough)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple dependency function
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T3, T5
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] File `app/dependencies/admin_auth.py` exists and exports `verify_admin_token`
  - [ ] `DASHBOARD_TOKEN=secret pytest tests/test_admin_auth.py` passes

  **QA Scenarios**:
  ```
  Scenario: Valid token accepted
    Tool: Bash (python -c)
    Preconditions: DASHBOARD_TOKEN=secret
    Steps:
      1. python -c "from app.dependencies.admin_auth import verify_admin_token; print(verify_admin_token('secret'))"
    Expected Result: Returns True (no exception)
    Evidence: .sisyphus/evidence/t2-valid-token.txt

  Scenario: Missing token rejected
    Tool: Bash (python -c)
    Preconditions: DASHBOARD_TOKEN=secret
    Steps:
      1. python -c "from app.dependencies.admin_auth import verify_admin_token; verify_admin_token(None)" 2>&1 || true
    Expected Result: HTTPException with 401 status code
    Evidence: .sisyphus/evidence/t2-missing-token.txt

  Scenario: Invalid token rejected
    Tool: Bash (python -c)
    Preconditions: DASHBOARD_TOKEN=secret
    Steps:
      1. python -c "from app.dependencies.admin_auth import verify_admin_token; verify_admin_token('wrong')" 2>&1 || true
    Expected Result: HTTPException with 403 status code
    Evidence: .sisyphus/evidence/t2-invalid-token.txt
  ```

  **Commit**: YES
  - Message: `feat(auth): add admin token validation dependency`
  - Files: `app/dependencies/admin_auth.py`, `tests/test_admin_auth.py`

---

- [x] T3. Create admin API router skeleton

  **What to do**:
  - Create `app/routes/admin.py`
  - Create `APIRouter(prefix="/admin/api", tags=["admin"])`
  - Add dependency: `dependencies=[Depends(verify_admin_token)]`
  - Add 3 placeholder endpoints returning `{}`:
    - `GET /admin/api/jobs`
    - `GET /admin/api/jobs/{message_id}`
    - `GET /admin/api/images/{message_id}`
  - Import `verify_admin_token` from `app.dependencies.admin_auth`

  **Must NOT do**:
  - Do NOT implement Redis logic yet (will be in T6-T8)
  - Do NOT serve static files (will be in T15)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Router skeleton with placeholder handlers
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T6, T7, T8
  - **Blocked By**: T2

  **Acceptance Criteria**:
  - [ ] `app/routes/admin.py` exists with all 3 endpoints
  - [ ] Each endpoint has correct path and is protected by token dependency

  **QA Scenarios**:
  ```
  Scenario: Skeleton endpoints return 200 with valid token
    Tool: Bash (curl via FastAPI test client — python -c)
    Steps:
      1. Set DASHBOARD_TOKEN=secret
      2. python -c "from fastapi.testclient import TestClient; from app.main import app; client = TestClient(app); print(client.get('/admin/api/jobs', headers={'X-Dashboard-Token':'secret'}).status_code)"
    Expected Result: 200
    Evidence: .sisyphus/evidence/t3-skeleton-endpoints.txt

  Scenario: Skeleton endpoints reject invalid token
    Tool: Bash (python -c)
    Steps:
      1. python -c "from fastapi.testclient import TestClient; from app.main import app; client = TestClient(app); print(client.get('/admin/api/jobs', headers={'X-Dashboard-Token':'bad'}).status_code)"
    Expected Result: 403
    Evidence: .sisyphus/evidence/t3-invalid-token.txt
  ```

  **Commit**: YES
  - Message: `feat(admin): add admin API router skeleton`
  - Files: `app/routes/admin.py`

---

- [x] T4. Register admin router in FastAPI app

  **What to do**:
  - Modify `app/routes/__init__.py` to import and include `admin_router`
  - Ensure admin router is included in main router
  - Verify `app/main.py` already includes the aggregated router (it does via `app.include_router(api_router)`)
  - Add `DASHBOARD_TOKEN` env var read in `app/main.py` (or let it be read per-request in the dependency)

  **Must NOT do**:
  - Do NOT change existing router imports or order
  - Do NOT remove the 404 handler yet (that is T18)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple import wiring
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T19
  - **Blocked By**: T2, T3

  **Acceptance Criteria**:
  - [ ] Admin endpoints accessible via test client
  - [ ] Existing endpoints still work

  **QA Scenarios**:
  ```
  Scenario: Admin router accessible
    Tool: Bash (python -c with TestClient)
    Steps:
      1. python -c "from fastapi.testclient import TestClient; from app.main import app; client = TestClient(app); r = client.get('/admin/api/jobs', headers={'X-Dashboard-Token':'secret'}); print(r.status_code)"
    Expected Result: 200
    Evidence: .sisyphus/evidence/t4-router-wired.txt

  Scenario: Existing endpoints unchanged
    Tool: Bash (curl)
    Steps:
      1. curl -s http://localhost:8000/health | grep -c '"status"'
    Expected Result: 1 (health endpoint still works)
    Evidence: .sisyphus/evidence/t4-existing-ok.txt
  ```

  **Commit**: YES
  - Message: `feat(admin): register admin router in FastAPI app`
  - Files: `app/routes/__init__.py`

---

- [x] T5. Write backend tests for admin auth and router

  **What to do**:
  - Create `tests/test_admin.py` with tests for:
    - Valid token returns 200 on all admin endpoints
    - Missing token returns 401
    - Invalid token returns 403
    - Empty token returns 403
  - Use existing `conftest.py` fixtures or create a client fixture
  - Set `DASHBOARD_TOKEN=test-token` for tests

  **Must NOT do**:
  - Do NOT test Redis logic yet (will be in T6-T8)
  - Do NOT test image serving yet

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple pytest assertions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: None
  - **Blocked By**: T2

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_admin.py` passes all 4+ tests

  **QA Scenarios**:
  ```
  Scenario: Backend tests pass
    Tool: Bash (pytest)
    Steps:
      1. DASHBOARD_TOKEN=test-token pytest tests/test_admin.py -v
    Expected Result: All tests pass (exit code 0)
    Evidence: .sisyphus/evidence/t5-test-output.txt
  ```

  **Commit**: YES
  - Message: `test(admin): add admin auth and router tests`
  - Files: `tests/test_admin.py`

---

### Wave 2: Backend API + Frontend Scaffold

- [x] T6. Implement `/admin/api/jobs` — list all jobs from Redis

  **What to do**:
  - Use `scan_iter(match="job:type:*")` to find all job type keys
  - For each key, extract the `message_id` from the key name
  - Call `get_job_status(message_id)` for each job
  - Aggregate into a list of job objects:
    ```json
    {
      "message_id": "...",
      "status": "pending|finished|failed|unknown",
      "job_type": "image",
      "filename": "...",
      "email": "...",
      "session_id": "...",
      "created_at": "..." // from Redis key info or omit
    }
    ```
  - Return array sorted by message_id (or reverse chronological)
  - Handle empty result gracefully (return `[]`)
  - Limit to most recent 100 jobs to avoid Redis performance issues

  **Must NOT do**:
  - Do NOT use `KEYS` command (use `SCAN`)
  - Do NOT modify existing job queue logic
  - Do NOT create new Redis key patterns

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Redis SCAN integration + data transformation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: T13
  - **Blocked By**: T3, T4

  **Acceptance Criteria**:
  - [ ] `GET /admin/api/jobs` returns list of jobs with valid token
  - [ ] Returns `[]` when no jobs exist
  - [ ] Returns 403 without token

  **QA Scenarios**:
  ```
  Scenario: List jobs with valid token
    Tool: Bash (curl + jq)
    Preconditions: At least one job exists in Redis
    Steps:
      1. curl -s -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/jobs | jq '. | length'
    Expected Result: >= 0 (array)
    Evidence: .sisyphus/evidence/t6-list-jobs.txt

  Scenario: Empty state
    Tool: Bash (curl + jq)
    Preconditions: No jobs in Redis
    Steps:
      1. curl -s -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/jobs | jq '.'
    Expected Result: "[]"
    Evidence: .sisyphus/evidence/t6-empty-jobs.txt

  Scenario: Missing token rejected
    Tool: Bash (curl)
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/admin/api/jobs
    Expected Result: 401
    Evidence: .sisyphus/evidence/t6-no-token.txt
  ```

  **Commit**: YES
  - Message: `feat(admin): implement job listing endpoint`
  - Files: `app/routes/admin.py`

---

- [x] T7. Implement `/admin/api/jobs/{message_id}` — job detail with OCR output

  **What to do**:
  - Reuse `get_job_status(message_id)` from `app.queues.job_status`
  - Return full job details including OCR text:
    ```json
    {
      "message_id": "...",
      "status": "finished",
      "job_type": "image",
      "filename": "...",
      "email": "...",
      "session_id": "...",
      "content": "Extracted OCR text...",
      "segments_count": 5,
      "error": null
    }
    ```
  - Handle missing job gracefully (return 404 with `{"detail": "Job not found"}`)
  - Include `error` field for failed jobs

  **Must NOT do**:
  - Do NOT modify `get_job_status` logic
  - Do NOT add new Redis lookups beyond status check

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Wrapping existing status logic with HTTP response
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: T14
  - **Blocked By**: T3, T4

  **Acceptance Criteria**:
  - [ ] `GET /admin/api/jobs/{id}` returns job details for valid ID
  - [ ] Returns 404 for unknown job ID

  **QA Scenarios**:
  ```
  Scenario: Get job detail
    Tool: Bash (curl + jq)
    Preconditions: A finished job exists in Redis
    Steps:
      1. JOB_ID=$(curl -s ... create job and get id)
      2. curl -s -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/jobs/$JOB_ID | jq '.status'
    Expected Result: "finished"
    Evidence: .sisyphus/evidence/t7-job-detail.txt

  Scenario: Unknown job returns 404
    Tool: Bash (curl)
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/jobs/nonexistent
    Expected Result: 404
    Evidence: .sisyphus/evidence/t7-unknown-job.txt
  ```

  **Commit**: YES
  - Message: `feat(admin): implement job detail endpoint`
  - Files: `app/routes/admin.py`

---

- [ ] T8. Implement `/admin/api/images/{message_id}` — stream image from shared_files

  **What to do**:
  - Read `image_file_path` from Redis result (or reconstruct from job data)
  - If result doesn't contain `image_file_path`, look up from job type key or return 404
  - Validate the path is within `shared_files/` (prevent path traversal)
  - Use `FileResponse` to stream the image with proper MIME type
  - Set `Content-Disposition: inline` for browser preview
  - Handle missing file gracefully (return 404)
  - Handle file read errors gracefully (return 500 with error detail)

  **Must NOT do**:
  - Do NOT expose the `shared_files/` volume statically
  - Do NOT allow path traversal (e.g., `../../../etc/passwd`)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: File streaming + security path validation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: T14
  - **Blocked By**: T3, T4

  **Acceptance Criteria**:
  - [ ] `GET /admin/api/images/{id}` streams image for valid job
  - [ ] Returns 404 for missing image file
  - [ ] Path traversal attempts return 403 or 404

  **QA Scenarios**:
  ```
  Scenario: Stream valid image
    Tool: Bash (curl)
    Preconditions: A finished job with image in shared_files/
    Steps:
      1. curl -s -o /dev/null -w "%{content_type}" -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/images/$JOB_ID
    Expected Result: image/png or image/jpeg
    Evidence: .sisyphus/evidence/t8-image-stream.txt

  Scenario: Missing image returns 404
    Tool: Bash (curl)
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/images/nonexistent
    Expected Result: 404
    Evidence: .sisyphus/evidence/t8-missing-image.txt

  Scenario: Path traversal blocked
    Tool: Bash (curl)
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/images/../../../etc/passwd
    Expected Result: 403 or 404
    Evidence: .sisyphus/evidence/t8-path-traversal.txt
  ```

  **Commit**: YES
  - Message: `feat(admin): add protected image streaming endpoint`
  - Files: `app/routes/admin.py`

---

- [x] T9. Initialize React + Vite + shadcn/ui frontend project

  **What to do**:
  - Create `app/frontend/` directory
  - Initialize Vite project: `npm create vite@latest app/frontend -- --template react-ts`
  - Install Tailwind CSS: `npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p`
  - Configure `tailwind.config.js` with content paths
  - Add Tailwind directives to `src/index.css`
  - Initialize shadcn/ui: `npx shadcn@latest init -d` (accept defaults)
  - Install key shadcn components: `npx shadcn add button input card badge table sidebar`
  - Install `react-router-dom`, `lucide-react`

  **Must NOT do**:
  - Do NOT use Next.js
  - Do NOT install heavy charting libraries

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Scaffold initialization via CLI
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: T10, T11, T12, T13, T14
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `app/frontend/package.json` exists with react, vite, tailwind, shadcn/ui
  - [ ] `npm run build` inside `app/frontend/` succeeds (initial build)

  **QA Scenarios**:
  ```
  Scenario: Vite dev server starts
    Tool: Bash
    Steps:
      1. cd app/frontend && npm install
      2. timeout 10 npm run dev &
      3. sleep 5
      4. curl -s http://localhost:5173/ | grep -c "Vite + React"
    Expected Result: >= 1
    Evidence: .sisyphus/evidence/t9-vite-dev.txt
  ```

  **Commit**: YES
  - Message: `feat(dashboard): initialize React + Vite + shadcn/ui project`
  - Files: `app/frontend/` (all scaffolded files)

---

### Wave 3: Frontend Implementation

- [ ] T10. Configure Vite build output for FastAPI static serving

  **What to do**:
  - Edit `vite.config.ts`: set `base: './'` for relative asset paths
  - Edit `vite.config.ts`: set `build.outDir` to `../static/dashboard` (or use post-build copy)
  - Verify the build creates `index.html` and `assets/` directory
  - Ensure `index.html` has `<meta charset="utf-8">` and viewport

  **Must NOT do**:
  - Do NOT use absolute paths like `/assets/...` (will break under FastAPI mount)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Config file edit
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: T20
  - **Blocked By**: T9

  **Acceptance Criteria**:
  - [ ] `npm run build` outputs to `app/static/dashboard/index.html`
  - [ ] All asset paths in `index.html` are relative (start with `./`)

  **QA Scenarios**:
  ```
  Scenario: Build outputs to static directory
    Tool: Bash
    Steps:
      1. cd app/frontend && npm run build
      2. ls app/static/dashboard/index.html
    Expected Result: File exists
    Evidence: .sisyphus/evidence/t10-build-output.txt

  Scenario: Asset paths are relative
    Tool: Bash (grep)
    Steps:
      1. grep -c 'src="./assets/' app/static/dashboard/index.html
    Expected Result: >= 1
    Evidence: .sisyphus/evidence/t10-relative-paths.txt
  ```

  **Commit**: YES
  - Message: `chore(dashboard): configure Vite for FastAPI static serving`
  - Files: `app/frontend/vite.config.ts`

---

- [ ] T11. Add shared layout, sidebar, and auth context

  **What to do**:
  - Create `app/frontend/src/context/AuthContext.tsx`:
    - `token: string | null` from localStorage (key: `dashboard_token`)
    - `login(token)` — saves to localStorage + state
    - `logout()` — removes from localStorage + state
  - Create `app/frontend/src/layouts/DashboardLayout.tsx`:
    - Sidebar with links: Dashboard, Job History, Settings (placeholder)
    - Main content area with padding
    - Header with logout button + token indicator (masked)
  - Install and configure `react-router-dom` routes:
    - `/dashboard/login` → LoginPage
    - `/dashboard` → DashboardPage (redirects to login if no token)
    - `/dashboard/jobs/:id` → JobDetailPage

  **Must NOT do**:
  - Do NOT implement actual pages yet
  - Do NOT fetch data from API yet

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: React components + routing + state management
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: T12, T13, T14
  - **Blocked By**: T9, T11

  **Acceptance Criteria**:
  - [ ] AuthContext stores and retrieves token from localStorage
  - [ ] DashboardLayout renders sidebar and main area
  - [ ] Routing works for /dashboard/login, /dashboard, /dashboard/jobs/:id

  **QA Scenarios**:
  ```
  Scenario: Auth context persists token
    Tool: Bash (node)
    Steps:
      1. cd app/frontend && npm run build
      2. python -c "from http.server import HTTPServer, SimpleHTTPRequestHandler; import os; os.chdir('app/static/dashboard'); HTTPServer(('localhost', 8080), SimpleHTTPRequestHandler).serve_forever()" &
      3. sleep 2
      4. playwright screenshot http://localhost:8080/ app/static/test-auth.png
    Expected Result: Screenshot shows login page (or redirect)
    Evidence: .sisyphus/evidence/t11-auth-context.png
  ```

  **Commit**: YES
  - Message: `feat(dashboard): add auth context, layout, and routing`
  - Files: `app/frontend/src/context/`, `app/frontend/src/layouts/`, `app/frontend/src/App.tsx`

---

- [ ] T12. Build Login page

  **What to do**:
  - Create `app/frontend/src/pages/LoginPage.tsx`
  - UI: Centered card with password input + "Login" button
  - On submit: POST to `/admin/api/login` (or just validate client-side against a test endpoint? No — validate by calling any admin endpoint like `/admin/api/jobs` with the token)
  - Better approach: On submit, store token in AuthContext, then redirect to `/dashboard`
  - Actually, since token is just a shared secret, there's no "login" endpoint. Just store it and redirect.
  - BUT: We should validate it first. Add a simple `/admin/api/me` or `/admin/api/verify` endpoint that returns 200 if token is valid.
  - Update T3 to include `GET /admin/api/verify` endpoint (just returns `{"valid": true}`)
  - If verify fails → show error message "Invalid token"
  - Styling: Use shadcn Card, Input, Button components

  **Must NOT do**:
  - Do NOT implement JWT login flow
  - Do NOT store token in cookies

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI page with state and API call
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (backend T6-T8 can run simultaneously)
  - **Parallel Group**: Wave 3
  - **Blocks**: T13, T14
  - **Blocked By**: T9, T11

  **Acceptance Criteria**:
  - [ ] Login page has password input + submit button
  - [ ] Valid token redirects to dashboard
  - [ ] Invalid token shows error

  **QA Scenarios**:
  ```
  Scenario: Valid token login
    Tool: Playwright
    Steps:
      1. Navigate to http://localhost:8000/dashboard/login
      2. Fill input[name="token"] with "secret"
      3. Click button[type="submit"]
      4. Wait for URL to be /dashboard
    Expected Result: URL contains /dashboard
    Evidence: .sisyphus/evidence/t12-login-valid.png

  Scenario: Invalid token shows error
    Tool: Playwright
    Steps:
      1. Navigate to http://localhost:8000/dashboard/login
      2. Fill input with "wrong"
      3. Click submit
      4. Wait for .error-message
    Expected Result: Page shows "Invalid token"
    Evidence: .sisyphus/evidence/t12-login-invalid.png
  ```

  **Commit**: YES
  - Message: `feat(dashboard): build login page with token validation`
  - Files: `app/frontend/src/pages/LoginPage.tsx`

---

- [ ] T13. Build Dashboard page with job list table

  **What to do**:
  - Create `app/frontend/src/pages/DashboardPage.tsx`
  - Fetch jobs from `GET /admin/api/jobs` (with `X-Dashboard-Token` header)
  - Display jobs in shadcn `Table` component:
    - Columns: Status (Badge), Filename, Email, Session ID, Actions
  - Status filter: Dropdown with All / Pending / Finished / Failed
  - Poll every 5 seconds for status updates (use `setInterval`)
  - Loading state while fetching
  - Empty state when no jobs
  - Click on a job row → navigate to `/dashboard/jobs/{id}`
  - Use shadcn Badge for status colors (yellow=pending, green=finished, red=failed)

  **Must NOT do**:
  - Do NOT implement pagination (limit to 100 jobs from backend)
  - Do NOT implement sorting (backend sorts by message_id)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Data table with polling + filtering + routing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: T21
  - **Blocked By**: T6, T9, T11, T12

  **Acceptance Criteria**:
  - [ ] Jobs list fetches and displays
  - [ ] Status filter works
  - [ ] Polling updates job statuses
  - [ ] Clicking row navigates to detail page

  **QA Scenarios**:
  ```
  Scenario: Dashboard displays jobs
    Tool: Playwright
    Preconditions: At least 3 jobs in Redis (pending, finished, failed)
    Steps:
      1. Login with valid token
      2. Wait for table rows to load
      3. Screenshot table
      4. Count visible status badges
    Expected Result: >= 3 rows with different status badges
    Evidence: .sisyphus/evidence/t13-dashboard-jobs.png

  Scenario: Status filter works
    Tool: Playwright
    Steps:
      1. On dashboard page
      2. Select "finished" from status filter dropdown
      3. Wait for table update
    Expected Result: Only "finished" jobs visible
    Evidence: .sisyphus/evidence/t13-status-filter.png

  Scenario: Polling updates status
    Tool: Playwright
    Preconditions: Submit a new job (will be pending)
    Steps:
      1. Submit job via API
      2. Dashboard shows "pending"
      3. Wait 30 seconds for OCR to finish
      4. Status badge changes to "finished"
    Expected Result: Badge color changes from yellow to green
    Evidence: .sisyphus/evidence/t13-polling.png
  ```

  **Commit**: YES
  - Message: `feat(dashboard): build job list page with filtering and polling`
  - Files: `app/frontend/src/pages/DashboardPage.tsx`

---

- [ ] T14. Build Job Detail page with OCR output and image preview

  **What to do**:
  - Create `app/frontend/src/pages/JobDetailPage.tsx`
  - Fetch job details from `GET /admin/api/jobs/{id}`
  - Display in shadcn `Card` layout:
    - CardHeader: Job ID + Status badge
    - CardContent:
      - Filename, Email, Session ID
      - OCR Output (in a scrollable `<pre>` or Card with monospace font)
      - Segments count
      - Image preview: `<img src="/admin/api/images/{id}" alt="Original" />`
  - Handle missing image (show placeholder text "Image not available")
  - Handle error state (show error message)
  - "Back to Dashboard" link

  **Must NOT do**:
  - Do NOT implement image editing or manipulation

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Detail page with API data + image rendering
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: T21
  - **Blocked By**: T7, T8, T9, T11, T12

  **Acceptance Criteria**:
  - [ ] Job detail page shows all job metadata
  - [ ] OCR text is displayed
  - [ ] Image is rendered from protected endpoint
  - [ ] Missing image shows placeholder

  **QA Scenarios**:
  ```
  Scenario: Job detail shows OCR and image
    Tool: Playwright
    Preconditions: A finished job with image and OCR result
    Steps:
      1. Navigate to /dashboard/jobs/{id}
      2. Wait for content to load
      3. Screenshot page
      4. Check OCR text visible
      5. Check image loaded (img.naturalWidth > 0)
    Expected Result: OCR text visible, image loaded
    Evidence: .sisyphus/evidence/t14-job-detail.png

  Scenario: Missing image shows placeholder
    Tool: Playwright
    Preconditions: A job where the image file was deleted
    Steps:
      1. Navigate to /dashboard/jobs/{id}
      2. Wait for page load
      3. Check for placeholder text
    Expected Result: Page shows "Image not available"
    Evidence: .sisyphus/evidence/t14-missing-image.png
  ```

  **Commit**: YES
  - Message: `feat(dashboard): build job detail page with OCR and image`
  - Files: `app/frontend/src/pages/JobDetailPage.tsx`

---

### Wave 4: Integration + Docker

- [ ] T15. Mount dashboard static files in FastAPI

  **What to do**:
  - In `app/main.py`, add:
    ```python
    from fastapi.staticfiles import StaticFiles
    app.mount("/dashboard", StaticFiles(directory="app/static/dashboard", html=True), name="dashboard")
    ```
  - Mount MUST be LAST (after all API routes) so that API routes take precedence
  - Ensure `html=True` enables SPA fallback for client-side routing

  **Must NOT do**:
  - Do NOT mount at root `/` (would override API routes)
  - Do NOT use `CheckStaticFiles` (FastAPI handles it)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single mount call
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocks**: T21
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `GET /dashboard` serves `index.html`
  - [ ] `GET /dashboard/nonexistent` also serves `index.html` (SPA fallback)
  - [ ] `GET /health` still returns JSON (API routes not shadowed)

  **QA Scenarios**:
  ```
  Scenario: Dashboard SPA served
    Tool: Bash (curl)
    Steps:
      1. curl -s http://localhost:8000/dashboard/ | grep -c "Dashboard"
    Expected Result: >= 1 (HTML contains Dashboard text)
    Evidence: .sisyphus/evidence/t15-spa-served.txt

  Scenario: SPA fallback works
    Tool: Bash (curl)
    Steps:
      1. curl -s http://localhost:8000/dashboard/jobs/123 | grep -c "Dashboard"
    Expected Result: >= 1 (returns index.html, not 404)
    Evidence: .sisyphus/evidence/t15-spa-fallback.txt

  Scenario: API routes still work
    Tool: Bash (curl)
    Steps:
      1. curl -s http://localhost:8000/health | grep -c '"status"'
    Expected Result: 1
    Evidence: .sisyphus/evidence/t15-api-routes.txt
  ```

  **Commit**: YES
  - Message: `feat(main): mount dashboard static files for SPA serving`
  - Files: `app/main.py`

---

- [ ] T16. Fix 404 handler to not shadow SPA routes

  **What to do**:
  - Current 404 handler: `RedirectResponse(url="https://ash-speed.hetzner.com/10GB.bin")`
  - Problem: This traps ALL 404s, including SPA client-side routing
  - Solution: Modify the 404 handler:
    ```python
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    @app.exception_handler(404)
    def not_found_handler(request: Request, _exc: HTTPException):
        if request.url.path.startswith("/dashboard"):
            index_path = Path("app/static/dashboard/index.html")
            if index_path.exists():
                return FileResponse(str(index_path))
        return RedirectResponse(url="https://ash-speed.hetzner.com/10GB.bin")
    ```
  - This ensures `/dashboard/jobs/123` (client-side route) gets `index.html`

  **Must NOT do**:
  - Do NOT remove the external redirect for non-dashboard paths

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small conditional in existing handler
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocks**: T21
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `/dashboard/jobs/nonexistent` returns `index.html` (not 404 redirect)
  - [ ] `/nonexistent` still redirects to external URL

  **QA Scenarios**:
  ```
  Scenario: Dashboard 404 serves SPA
    Tool: Bash (curl)
    Steps:
      1. curl -s http://localhost:8000/dashboard/jobs/nonexistent | grep -c "Dashboard"
    Expected Result: >= 1
    Evidence: .sisyphus/evidence/t16-dashboard-404.txt

  Scenario: Non-dashboard 404 still redirects
    Tool: Bash (curl -L)
    Steps:
      1. curl -s -o /dev/null -w "%{url_effective}" http://localhost:8000/nonexistent-path
    Expected Result: Contains "hetzner.com"
    Evidence: .sisyphus/evidence/t16-non-dashboard-404.txt
  ```

  **Commit**: YES
  - Message: `fix(404): serve SPA index.html for dashboard client routes`
  - Files: `app/main.py`

---

- [ ] T17. Update Dockerfile with multi-stage Node + Python build

  **What to do**:
  - Add `FROM node:22-alpine AS frontend-build` stage
  - In Node stage:
    - `WORKDIR /app/frontend`
    - Copy `app/frontend/package*.json`
    - `npm ci`
    - Copy `app/frontend/src`
    - `npm run build` (outputs to `app/static/dashboard/`)
  - In Python stage:
    - Add `COPY --from=frontend-build /app/static/dashboard /app/static/dashboard`
  - Ensure Python stage still installs requirements and copies app code
  - Final image should contain:
    - Python app code
    - Built dashboard static files

  **Must NOT do**:
  - Do NOT make the Node image the final stage
  - Do NOT install Node in the final Python image

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multi-stage Docker build
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocks**: T21
  - **Blocked By**: T1, T10, T20

  **Acceptance Criteria**:
  - [ ] `docker build -t image-to-text-app:latest .` succeeds
  - [ ] Final image contains `/app/static/dashboard/index.html`
  - [ ] Final image does NOT contain node/npm

  **QA Scenarios**:
  ```
  Scenario: Docker build succeeds
    Tool: Bash (docker)
    Steps:
      1. docker build -t image-to-text-app:test .
      2. docker run --rm image-to-text-app:test ls /app/static/dashboard/index.html
    Expected Result: File exists
    Evidence: .sisyphus/evidence/t17-docker-build.txt
  ```

  **Commit**: YES
  - Message: `build(docker): add multi-stage Node build for dashboard`
  - Files: `Dockerfile`

---

- [ ] T18. Update docker-compose files for DASHBOARD_TOKEN

  **What to do**:
  - In `docker-compose.yml`:
    - Add `DASHBOARD_TOKEN=${DASHBOARD_TOKEN}` to both web and worker environment sections
  - In `docker-compose.prod.yml`:
    - Same as above
  - Ensure `.env` file (not tracked in git) contains `DASHBOARD_TOKEN=your-secret-here`
  - Add volume mount for `shared_files/` (already present from existing config — verify)

  **Must NOT do**:
  - Do NOT hardcode token value in compose file

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Env var addition
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocks**: T21
  - **Blocked By**: T1

  **Acceptance Criteria**:
  - [ ] Both compose files pass DASHBOARD_TOKEN to containers
  - [ ] `docker-compose config` shows DASHBOARD_TOKEN interpolation

  **QA Scenarios**:
  ```
  Scenario: Env var propagated
    Tool: Bash (docker-compose config)
    Steps:
      1. DASHBOARD_TOKEN=secret docker-compose config | grep -c "DASHBOARD_TOKEN"
    Expected Result: >= 2 (web + worker)
    Evidence: .sisyphus/evidence/t18-compose-config.txt
  ```

  **Commit**: YES
  - Message: `chore(docker): add DASHBOARD_TOKEN to compose services`
  - Files: `docker-compose.yml`, `docker-compose.prod.yml`

---

### Wave 5: Testing + E2E Verification

- [ ] T19. Run backend tests

  **What to do**:
  - Run `pytest tests/test_admin.py -v`
  - Fix any failing tests
  - Run `pytest tests/test_image_to_text.py tests/test_jobs.py` to verify existing tests still pass

  **Must NOT do**:
  - Do NOT modify existing tests unless broken by changes

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Running existing test suite
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5
  - **Blocks**: T21
  - **Blocked By**: T4, T5, T6, T7, T8

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_admin.py` passes
  - [ ] Existing tests still pass

  **QA Scenarios**:
  ```
  Scenario: All backend tests pass
    Tool: Bash (pytest)
    Steps:
      1. DASHBOARD_TOKEN=test pytest tests/test_admin.py tests/test_image_to_text.py tests/test_jobs.py -v
    Expected Result: Exit code 0, all tests pass
    Evidence: .sisyphus/evidence/t19-test-output.txt
  ```

  **Commit**: NO (tests pass — no code changes needed)

---

- [ ] T20. Build frontend production bundle

  **What to do**:
  - Run `cd app/frontend && npm run build`
  - Verify output in `app/static/dashboard/`:
    - `index.html`
    - `assets/` directory with JS and CSS files
  - Verify asset paths in `index.html` are relative (`./assets/...`)
  - Verify `index.html` has correct `<base href="./">` or relative paths

  **Must NOT do**:
  - Do NOT commit `node_modules/` or build output to git (add to `.gitignore`)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Build step
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5
  - **Blocks**: T21
  - **Blocked By**: T10, T13, T14

  **Acceptance Criteria**:
  - [ ] `app/static/dashboard/index.html` exists
  - [ ] `app/static/dashboard/assets/` contains JS/CSS files
  - [ ] No absolute paths in `index.html`

  **QA Scenarios**:
  ```
  Scenario: Production build succeeds
    Tool: Bash
    Steps:
      1. cd app/frontend && npm run build
      2. ls ../static/dashboard/index.html
      3. ls ../static/dashboard/assets/*.js
    Expected Result: Files exist
    Evidence: .sisyphus/evidence/t20-build-assets.txt
  ```

  **Commit**: YES
  - Message: `build(dashboard): add production frontend build`
  - Files: `app/static/dashboard/` (generated files)
  - Note: Consider adding `app/static/dashboard/` to `.gitignore` and only building in CI/Docker

---

- [ ] T21. Full Docker Compose end-to-end verification

  **What to do**:
  - Run `docker-compose down -v` (clean state)
  - Run `docker-compose up --build -d`
  - Wait for services to start (check `docker-compose ps`)
  - Submit a test job:
    ```bash
    curl -X POST -F "image=@test-image.png" http://localhost:8000/convert/image/text
    ```
  - Wait for job to finish (poll `/job/{message_id}`)
  - Open dashboard: `curl -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/jobs`
  - Verify dashboard shows the job
  - Verify image preview works
  - Verify OCR text is displayed
  - Run all tests inside container:
    ```bash
    docker-compose exec web pytest tests/
    ```

  **Must NOT do**:
  - Do NOT skip the image upload test (critical for verifying the full pipeline)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Full integration verification
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (must run after ALL other tasks)
  - **Blocked By**: T6, T7, T8, T13, T14, T15, T16, T17, T18, T19, T20

  **Acceptance Criteria**:
  - [ ] Docker Compose builds successfully
  - [ ] API endpoints work
  - [ ] Admin endpoints work with token
  - [ ] Dashboard loads in browser
  - [ ] Job list shows correct data
  - [ ] Job detail shows OCR and image

  **QA Scenarios**:
  ```
  Scenario: Full E2E workflow
    Tool: Bash (curl + docker-compose)
    Steps:
      1. docker-compose down -v
      2. DASHBOARD_TOKEN=secret docker-compose up --build -d
      3. sleep 30 (wait for OCR model init)
      4. JOB_RESPONSE=$(curl -s -X POST -F "image=@tests/fixtures/test.png" http://localhost:8000/convert/image/text)
      5. JOB_ID=$(echo $JOB_RESPONSE | jq -r '.message_id')
      6. sleep 10 (wait for OCR)
      7. curl -s -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/jobs | jq '. | length'
      8. curl -s -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/jobs/$JOB_ID | jq '.status'
      9. curl -s -o /dev/null -w "%{http_code}" -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/images/$JOB_ID
    Expected Result: Job count >= 1, status = "finished", image status = 200
    Evidence: .sisyphus/evidence/t21-e2e-full.txt

  Scenario: Dashboard SPA loads
    Tool: Playwright
    Steps:
      1. Navigate to http://localhost:8000/dashboard/login
      2. Screenshot
      3. Fill token and login
      4. Screenshot dashboard
    Expected Result: Login page + Dashboard page visible
    Evidence: .sisyphus/evidence/t21-dashboard-screenshot.png
  ```

  **Commit**: NO (verification only)

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `tsc --noEmit` + `python -m py_compile` + `pytest`. Review all changed files for: `as any`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together, not isolation). Test edge cases: empty state, invalid input, rapid actions. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- T1: `chore(config): add DASHBOARD_TOKEN env var`
- T2: `feat(auth): add admin token validation dependency`
- T3: `feat(admin): add admin API router skeleton`
- T4: `feat(admin): register admin router in FastAPI app`
- T5: `test(admin): add admin auth and router tests`
- T6: `feat(admin): implement job listing endpoint`
- T7: `feat(admin): implement job detail endpoint`
- T8: `feat(admin): add protected image streaming endpoint`
- T9: `feat(dashboard): initialize React + Vite + shadcn/ui project`
- T10: `chore(dashboard): configure Vite for FastAPI static serving`
- T11: `feat(dashboard): add auth context, layout, and routing`
- T12: `feat(dashboard): build login page with token validation`
- T13: `feat(dashboard): build job list page with filtering and polling`
- T14: `feat(dashboard): build job detail page with OCR and image`
- T15: `feat(main): mount dashboard static files for SPA serving`
- T16: `fix(404): serve SPA index.html for dashboard client routes`
- T17: `build(docker): add multi-stage Node build for dashboard`
- T18: `chore(docker): add DASHBOARD_TOKEN to compose services`
- T20: `build(dashboard): add production frontend build`

---

## Success Criteria

### Verification Commands
```bash
# All backend tests pass
DASHBOARD_TOKEN=test pytest tests/test_admin.py tests/test_image_to_text.py tests/test_jobs.py -v
# Expected: all pass

# Admin endpoints accessible
curl -H "X-Dashboard-Token: $DASHBOARD_TOKEN" http://localhost:8000/admin/api/jobs | jq '. | length'
# Expected: >= 0

# Dashboard SPA loads
curl -s http://localhost:8000/dashboard/login | grep -c "Login"
# Expected: >= 1

# Docker Compose E2E
DASHBOARD_TOKEN=secret docker-compose up --build -d
curl -H "X-Dashboard-Token: secret" http://localhost:8000/admin/api/jobs
# Expected: JSON array

# Existing endpoints unchanged
curl http://localhost:8000/health | jq '.status'
# Expected: "ok"
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] Dashboard loads in browser
- [ ] Token auth works
- [ ] Job history displays
- [ ] Image previews load
- [ ] OCR output visible
- [ ] Docker build succeeds
