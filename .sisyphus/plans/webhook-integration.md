# Work Plan: Webhook Integration for OCR Job Completion

## TL;DR
> Add an optional, configurable webhook notification that fires when an image-to-text OCR job successfully completes, with linear retry backoff and non-blocking execution.
>
> **Deliverables**:
> - `app/utils/webhook.py` — Webhook sender with retry/backoff logic
> - `app/queues/job_queue.py` — Integration point after successful job completion
> - `.env.example`, `docker-compose.yml`, `docker-compose.prod.yml` — Env var plumbing
> - `tests/test_webhook.py` — Unit tests for retry logic and integration
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 (sequential), Tasks 4-5 parallel with Wave 2, Task 6 final QA

## Context

### Original Request
> After an OCR job is finished, trigger a webhook via an environment variable (`WEBHOOK_URL`). The env var is optional — if absent, no webhook is sent. Retry on non-200 responses with backoff: `30s × retry_number`, up to 10 retries max.

### Interview Summary
- **Trigger point**: Worker completion in `app/queues/job_queue.py` (after `process_image_job_sync` returns), not the status polling endpoint, to avoid firing on every poll.
- **Payload**: Full result object including `message_id`, `status`, `content`, `filename`, `segments_count`, `email`, `session_id`.
- **Retry blocking**: Non-blocking via background thread — blocking the Dramatiq worker for up to ~27 minutes would stall the queue.
- **Env var name**: `WEBHOOK_URL`

### Research Findings
- **Dramatiq actor**: `process_image_job` in `app/queues/job_queue.py` with `store_results=True`, `max_retries=3`, `time_limit=300000`.
- **Worker function**: `process_image_job_sync` in `app/workers/image_worker.py` returns the result dict.
- **HTTP libs**: `httpx==0.28.1` and `requests==2.32.5` both present.
- **Tests**: `pytest` + `pytest-asyncio` with `httpx.AsyncClient` and `unittest.mock.patch` patterns.

### Metis Review
**Identified Gaps** (addressed):
- **`CurrentMessage` middleware NOT configured**: Cannot use `CurrentMessage.get_current_message().message_id`. Must pass `message_id` through `job_data` at enqueue time (`enqueue_image_job`). Included as Task A (Wave 0 prerequisite).
- **Webhook fires on BOTH success AND failure**: The receiver needs to know the final outcome regardless. Updated Task 2 to fire after try/except, not just after success.
- **Retry on non-200 is too broad**: Only retry on 5xx and network errors (transient). 4xx (client errors) should NOT be retried. Added guardrail and updated Task 1 acceptance criteria.
- **HTTP timeout missing**: Must set `timeout=30` on every `requests.post` call.
- **Empty string handling**: `WEBHOOK_URL=""` must be treated as unset (same as missing).
- **Webhook failures MUST NOT crash actor**: Wrapped in try/except at actor level.
- **Edge cases added**: Invalid URL, SSL error, DNS failure, concurrent threads.

---

## Work Objectives

### Core Objective
Implement an optional webhook notification triggered immediately after successful OCR job completion in the Dramatiq worker, with configurable retry logic.

### Concrete Deliverables
- `app/utils/webhook.py` — Standalone webhook sender module
- Updated `app/queues/job_queue.py` — Call webhook after job success
- Updated `.env.example` — Document `WEBHOOK_URL`
- Updated `docker-compose.yml` and `docker-compose.prod.yml` — Pass `WEBHOOK_URL` to worker service
- `tests/test_webhook.py` — Unit tests for retry/backoff and integration

### Definition of Done
- [ ] `WEBHOOK_URL` env var is read at runtime
- [ ] Webhook POSTs JSON payload after successful job completion
- [ ] Retries on non-200 response with 30s × attempt backoff
- [ ] Max 10 retry attempts
- [ ] Webhook execution is non-blocking (background thread)
- [ ] If `WEBHOOK_URL` is unset, no webhook is sent (silent skip)
- [ ] All existing tests pass (`pytest`)
- [ ] New tests pass (`pytest tests/test_webhook.py`)

### Must Have
- Retry logic with exact backoff formula: `30s × retry_number`
- Non-blocking webhook execution
- Optional env var (no error if missing)
- `message_id` included in webhook payload

### Must NOT Have (Guardrails)
- Do NOT fire webhook from `app/queues/job_status.py` (polling endpoint)
- Do NOT modify status polling behavior
- Do NOT add webhook signature/secret verification
- Do NOT support multiple webhook URLs
- Do NOT retry webhook on network exceptions differently from HTTP non-200

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (`pytest`, `pytest-asyncio`, `unittest.mock`)
- **Automated tests**: YES (Tests after implementation)
- **Framework**: `pytest`
- **Agent-Executed QA**: YES — Every task includes concrete QA scenarios

### QA Policy
Each task includes specific QA scenarios runnable by the agent. Evidence saved to `.sisyphus/evidence/`.

## Execution Strategy

### Parallel Execution Waves

```
Wave 3 (After Wave 2 — final QA):
└── Task 6: Run full test suite and verify no regressions
```

### Dependency Matrix
- **A**: Blocked by None → Blocks 1, 2, 3
- **1**: Blocked by A → Blocks 2
- **2**: Blocked by 1 → Blocks 4, 5
- **3**: Blocked by None → Blocks none (independent config)
- **4**: Blocked by 1, 2 → Blocks 6
- **5**: Blocked by 1, 2 → Blocks 6
- **6**: Blocked by 4, 5 → End

### Agent Dispatch Summary
- **Wave 0**: Task A → `quick`
- **Wave 1**: Task 1 → `quick`, Task 2 → `quick`, Task 3 → `quick`
- **Wave 2**: Task 4 → `quick`, Task 5 → `quick`
- **Wave 3**: Task 6 → `quick`

---

## TODOs

- [ ] **A. Pass message_id through job_data in enqueue_image_job**

  **What to do**:
  - In `app/queues/job_queue.py`, modify `enqueue_image_job` to add the generated `message_id` to the `job_data` dict before the job is sent.
  - Since `process_image_job.send(job_data)` serializes `job_data` immediately, the message_id must be set on the dict object **before** `send()` is called. However, the message_id is only known AFTER `send()` returns the Message object.
  - **Approach**: After `message = process_image_job.send(job_data)`, update `job_data["message_id"] = message.message_id`. Since `job_data` is a dict passed by reference, and Dramatiq may pickle it at send time, we need to verify if the worker receives the updated dict.
  - **Safer approach**: Don't mutate after send. Instead, modify `process_image_job_sync` to accept a second parameter `message_id`, and modify `process_image_job` actor to pass it.
  - **Simplest safe approach**: Add `message_id` to `job_data` BEFORE calling `_store_job_type`, then ALSO update the enqueue call to pass it through. But since the message_id is only known after send, the cleanest way is to restructure `enqueue_image_job`:
    ```python
    message = process_image_job.send(job_data)
    job_data["message_id"] = message.message_id  # Add after send — worker will receive this? No, it's already serialized.
    _store_job_type(message.message_id, JOB_TYPE_IMAGE)
    ```
  - **Actually, the correct fix**: In Dramatiq, `send()` serializes the arguments immediately. If `job_data` is a dict, it gets pickled/copied. Mutating it after `send()` won't affect the worker.
  - **Best solution**: Modify `process_image_job_sync` to accept `(job_data, message_id)`, then in `process_image_job`:
    ```python
    def process_image_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
        message = CurrentMessage.get_current_message()
        message_id = message.message_id if message else None
        try:
            result = process_image_job_sync(job_data, message_id)
            ...
    ```
  - But wait, `CurrentMessage` middleware is already available in Dramatiq if configured. Let me check if it's configured...
  
  **After Metis analysis, the cleanest approach is to add `CurrentMessage` middleware**:
  - In `app/queues/job_queue.py`, add `CurrentMessage` middleware to the broker. Then inside the actor, call `CurrentMessage.get_current_message().message_id`.
  - This is a one-line change plus import.

  **Revised approach**:
  - Add `from dramatiq.middleware import CurrentMessage` and `redis_broker.add_middleware(CurrentMessage())` to `app/queues/job_queue.py`.
  - Then `CurrentMessage.get_current_message().message_id` will work.

  **Must NOT do**:
  - Do NOT modify worker function signature.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (prerequisite)
  - **Blocks**: Tasks 1, 2, 3
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `CurrentMessage` middleware added to broker.
  - [ ] `CurrentMessage.get_current_message().message_id` returns a valid UUID string inside `process_image_job`.

  **QA Scenarios**:
  ```
  Scenario: Verify CurrentMessage middleware is active
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. python3 -c "import sys; sys.path.insert(0, 'app'); from app.queues.job_queue import redis_broker; from dramatiq.middleware import CurrentMessage; middleware = [m for m in redis_broker.middleware if isinstance(m, CurrentMessage)]; assert len(middleware) > 0; print('PASS')"
    Expected Result: Prints 'PASS'.
    Evidence: .sisyphus/evidence/task-a-middleware.txt
  ```

  **Commit**: YES (grouped with Tasks 1-3)

- [ ] **1. Create webhook utility module (`app/utils/webhook.py`)**

  **What to do**:
  - Create `app/utils/webhook.py` with a `send_webhook(url, payload)` function.
  - Implement retry loop: up to 10 attempts.
  - On each attempt: POST `payload` as JSON to `url`, timeout 30s.
  - If response status is 200: log success and return.
  - If response status is 5xx or request raises a network exception: log, sleep `30 × attempt`, retry.
  - If response status is 4xx: log error, do NOT retry.
  - After max retries (10): log final error.
  - **Must NOT block caller** — run the retry loop inside a `threading.Thread(daemon=True)`.
  - Import `requests`, `threading`, `time`.
  - Use existing logger: `from app.utils.logger import logger`.
  - Function signature:
    ```python
    def send_webhook(url: str, payload: dict) -> None:
        """Send webhook notification in a background thread with retry."""
    ```

  **Must NOT do**:
  - Do NOT use `async`/`await` — Dramatiq workers are sync.
  - Do NOT modify existing files.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (independent utility)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 2
  - **Blocked By**: Task A (if Task A adds middleware, but this utility doesn't depend on it)

  **References**:
  - `app/utils/__init__.py` — See if `app.utils` is a package with `__init__.py`.
  - `app/utils/logger.py` — Logger import pattern.

  **Acceptance Criteria**:
  - [ ] File `app/utils/webhook.py` exists.
  - [ ] `send_webhook` function defined with correct signature.
  - [ ] Uses `threading.Thread(daemon=True)` for non-blocking execution.
  - [ ] Retry loop up to 10 attempts with `time.sleep(30 * attempt)` backoff.
  - [ ] Only retries on 5xx and network errors, not 4xx.
  - [ ] Logs success, retry warnings, and final error.

  **QA Scenarios**:
  ```
  Scenario: Webhook succeeds on first attempt (200)
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. Mock requests.post to return status 200, call send_webhook, verify 1 call made.
    Expected Result: Exactly 1 POST call, no retries.
    Evidence: .sisyphus/evidence/task-1-success.txt

  Scenario: Webhook retries on 500 then succeeds
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. Mock requests.post to return 500 then 200, call send_webhook, verify 2 calls with mocked time.sleep.
    Expected Result: Exactly 2 POST calls, sleep called with 30.
    Evidence: .sisyphus/evidence/task-1-retry.txt

  Scenario: Webhook does NOT retry on 400
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. Mock requests.post to return 400, call send_webhook, verify 1 call only.
    Expected Result: Exactly 1 POST call, no retries.
    Evidence: .sisyphus/evidence/task-1-no-retry-4xx.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-1-success.txt` — REPL output confirming correct call count/args.
  - [ ] `task-1-retry.txt` — REPL output confirming retry behavior.
  - [ ] `task-1-no-retry-4xx.txt` — REPL output confirming no retry on 4xx.

  **Commit**: YES
  - Message: `feat(webhook): add send_webhook utility with retry and backoff`
  - Files: `app/utils/webhook.py`

- [ ] **2. Integrate webhook into worker (`app/queues/job_queue.py`)**

  **What to do**:
  - In `app/queues/job_queue.py`, in `process_image_job`, wrap the entire try/except in a way that webhook fires on BOTH success and failure:
    ```python
    @dramatiq.actor(store_results=True, max_retries=3, time_limit=300000)
    def process_image_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an image-to-text job using Dramatiq."""
        result = None
        error = None
        try:
            logger.info("Starting image-to-text job processing")
            result = process_image_job_sync(job_data)
            logger.info("Image-to-text job completed successfully")
            return result
        except Exception as e:
            logger.error("Error processing image-to-text job: %s", e, exc_info=True)
            error = str(e)
            raise
        finally:
            webhook_url = os.getenv("WEBHOOK_URL", "").strip()
            if webhook_url:
                try:
                    message = CurrentMessage.get_current_message()
                    message_id = message.message_id if message else None
                    payload = {
                        "message_id": message_id,
                        "status": "finished" if error is None else "failed",
                        "result": result if error is None else None,
                        "error": error,
                        **{k: v for k, v in job_data.items() if k in ("email", "session_id", "filename")}
                    }
                    send_webhook(webhook_url, payload)
                    logger.info("Webhook dispatched to %s for message_id: %s", webhook_url, message_id)
                except Exception:
                    logger.exception("Failed to dispatch webhook")
    ```

  **Must NOT do**:
  - Do NOT modify `app/workers/image_worker.py`.
  - Do NOT let webhook errors propagate to Dramatiq.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 1 and Task A)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: Tasks 1, A

  **References**:
  - `app/queues/job_queue.py:48-58` — Current `process_image_job` actor.
  - `app/utils/webhook.py` — `send_webhook` function (from Task 1).

  **Acceptance Criteria**:
  - [ ] Webhook dispatched on successful completion.
  - [ ] Webhook dispatched on failure with error payload.
  - [ ] Webhook errors caught and logged, not propagated.
  - [ ] `message_id` included in payload.

  **QA Scenarios**:
  ```
  Scenario: Webhook env var set — dispatch on success
    Tool: Bash (python REPL)
    Preconditions: Mock process_image_job_sync to succeed
    Steps:
      1. Set WEBHOOK_URL, mock process_image_job_sync, run actor, verify send_webhook called with finished status.
    Expected Result: send_webhook called once with status "finished".
    Evidence: .sisyphus/evidence/task-2-dispatch.txt

  Scenario: Webhook env var unset — silent skip
    Tool: Bash (python REPL)
    Preconditions: WEBHOOK_URL not set
    Steps:
      1. Run actor without env var, verify send_webhook not called.
    Expected Result: send_webhook not called.
    Evidence: .sisyphus/evidence/task-2-skip.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-2-dispatch.txt` — Confirms webhook dispatch with correct payload.
  - [ ] `task-2-skip.txt` — Confirms silent skip when env var absent.

  **Commit**: YES (grouped with Tasks 1, A)

- [ ] **3. Update env/config files**

  **What to do**:
  - `.env.example`: Add `WEBHOOK_URL=` (empty, documented as optional).
  - `docker-compose.yml`: Under `services.worker.environment`, add `WEBHOOK_URL: ${WEBHOOK_URL:-}`.
  - `docker-compose.prod.yml`: Same change under worker environment.

  **Must NOT do**:
  - Do NOT add to web service env — webhook runs in worker.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: none
  - **Blocked By**: none

  **Acceptance Criteria**:
  - [ ] `.env.example` contains `WEBHOOK_URL=` line.
  - [ ] `docker-compose.yml` worker service passes `WEBHOOK_URL`.
  - [ ] `docker-compose.prod.yml` worker service passes `WEBHOOK_URL`.

  **QA Scenarios**:
  ```
  Scenario: Verify env var present in compose files
    Tool: Bash (grep)
    Preconditions: None
    Steps:
      1. grep 'WEBHOOK_URL' docker-compose.yml docker-compose.prod.yml .env.example
    Expected Result: Each file shows at least one match.
    Evidence: .sisyphus/evidence/task-3-config.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-3-config.txt` — Grep output confirming env var in all three files.

  **Commit**: YES (grouped with Tasks 1-2, A)

- [ ] **4. Unit tests for webhook retry logic (`tests/test_webhook.py`)**

  **What to do**:
  - Create `tests/test_webhook.py`.
  - Cover: success (200), retry on 5xx, no retry on 4xx, max retries exceeded, backoff timing, network error retry, daemon thread.

  **Must NOT do**:
  - Do NOT make real HTTP requests in tests.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 6
  - **Blocked By**: Task 1

  **References**:
  - `app/utils/webhook.py` — Function under test.
  - `tests/test_jobs.py` — Mock patterns with `patch` and `pytest`.

  **Acceptance Criteria**:
  - [ ] Tests cover: success, retry on 5xx, no retry on 4xx, max retries, backoff formula, daemon thread.
  - [ ] `pytest tests/test_webhook.py` passes.

  **QA Scenarios**:
  ```
  Scenario: Run webhook unit tests
    Tool: Bash
    Preconditions: None
    Steps:
      1. pytest tests/test_webhook.py -v
    Expected Result: All tests pass, no failures.
    Evidence: .sisyphus/evidence/task-4-tests.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-4-tests.txt` — pytest output.

  **Commit**: YES (grouped with Tasks 1-3, A)

- [ ] **5. Integration tests for worker webhook (`tests/test_webhook.py`)**

  **What to do**:
  - Add integration test in `tests/test_webhook.py`:
    - Patch `process_image_job_sync` to return dummy result.
    - Set `WEBHOOK_URL` via `patch.dict(os.environ, ...)`.
    - Call `process_image_job` actor directly.
    - Assert `send_webhook` called with correct payload.
  - Also test: no `WEBHOOK_URL`, assert `send_webhook` not called.

  **Must NOT do**:
  - Do NOT test actual Dramatiq broker/Redis.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 6
  - **Blocked By**: Task 2

  **References**:
  - `app/queues/job_queue.py` — Actor integration point.
  - `tests/test_jobs.py` — Mock patterns for job_queue.

  **Acceptance Criteria**:
  - [ ] Integration test demonstrates webhook dispatch on job success.
  - [ ] Integration test demonstrates silent skip when env var missing.

  **QA Scenarios**:
  ```
  Scenario: Run integration tests
    Tool: Bash
    Preconditions: None
    Steps:
      1. pytest tests/test_webhook.py -v -k integration
    Expected Result: Integration tests pass.
    Evidence: .sisyphus/evidence/task-5-integration.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-5-integration.txt` — pytest output.

  **Commit**: YES (grouped with Tasks 1-4, A)

- [ ] **6. Run full test suite and verify no regressions**

  **What to do**:
  - Run `pytest` across the entire project.
  - Verify all existing tests (`test_jobs.py`, `test_image_to_text.py`) still pass.
  - Verify new tests (`test_webhook.py`) pass.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: NO (must wait for all prior tasks)
  - **Parallel Group**: Wave 3
  - **Blocks**: none
  - **Blocked By**: Tasks 1-5

  **Acceptance Criteria**:
  - [ ] `pytest` output shows 0 failures.
  - [ ] All new and existing tests pass.

  **QA Scenarios**:
  ```
  Scenario: Full regression test
    Tool: Bash
    Preconditions: None
    Steps:
      1. pytest --tb=short -v
    Expected Result: All tests pass, 0 failures.
    Evidence: .sisyphus/evidence/task-6-regression.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-6-regression.txt` — Full pytest output.

  **Commit**: YES (final commit)

---

## Final Verification Wave (after ALL implementation tasks)

- [ ] **F1. Plan Compliance Audit** — `oracle`
  Read plan and verify:
  - `app/utils/webhook.py` exists with `send_webhook`.
  - `app/queues/job_queue.py` calls webhook after success and failure.
  - `.env.example`, `docker-compose.yml`, `docker-compose.prod.yml` updated.
  - Tests exist and pass.
  - No modifications to `app/queues/job_status.py`.
  Output: VERDICT

- [ ] **F2. Code Quality Review** — `unspecified-high`
  Run `pytest` + basic lint check.
  Output: VERDICT

- [ ] **F3. Scope Fidelity Check** — `deep`
  Compare git diff against plan. Verify no scope creep.
  Output: VERDICT

---

## Commit Strategy

- **Group 1** (`feat(webhook): add webhook notification with retry and backoff`):
  - Files: `app/utils/webhook.py`, `app/queues/job_queue.py`, `.env.example`, `docker-compose.yml`, `docker-compose.prod.yml`, `tests/test_webhook.py`

---

## Success Criteria

### Verification Commands
```bash
pytest --tb=short -v  # Expected: all tests pass, 0 failures
```

### Final Checklist
- [ ] `WEBHOOK_URL` optional env var documented and wired
- [ ] Webhook fires after successful job completion
- [ ] Retry logic: 30s × attempt, max 10 retries
- [ ] Non-blocking execution (background thread)
- [ ] Full result payload sent including `message_id`
- [ ] All tests pass

### Dependency Matrix
- **A**: Blocked by None → Blocks 1, 2, 3
- **1**: Blocked by A → Blocks 2
- **2**: Blocked by 1 → Blocks 4, 5
- **3**: Blocked by None → Blocks none (independent config)
- **4**: Blocked by 1, 2 → Blocks 6
- **5**: Blocked by 1, 2 → Blocks 6
- **6**: Blocked by 4, 5 → End

### Agent Dispatch Summary
- **Wave 0**: Task A → `quick`
- **Wave 1**: Task 1 → `quick`, Task 2 → `quick`, Task 3 → `quick`
- **Wave 2**: Task 4 → `quick`, Task 5 → `quick`
- **Wave 3**: Task 6 → `quick`

---

## TODOs

- [ ] **A. Pass message_id through job_data in enqueue_image_job**

  **What to do**:
  - In `app/queues/job_queue.py`, modify `enqueue_image_job` to add the generated `message_id` to the `job_data` dict before the job is sent.
  - Since `process_image_job.send(job_data)` serializes `job_data` immediately, the message_id must be set on the dict object **before** `send()` is called. However, the message_id is only known AFTER `send()` returns the Message object.
  - **Approach**: After `message = process_image_job.send(job_data)`, update `job_data["message_id"] = message.message_id`. Since `job_data` is a dict passed by reference, and Dramatiq may pickle it at send time, we need to verify if the worker receives the updated dict.
  - **Safer approach**: Don't mutate after send. Instead, modify `process_image_job_sync` to accept a second parameter `message_id`, and modify `process_image_job` actor to pass it.
  - **Simplest safe approach**: Add `message_id` to `job_data` BEFORE calling `_store_job_type`, then ALSO update the enqueue call to pass it through. But since the message_id is only known after send, the cleanest way is to restructure `enqueue_image_job`:
    ```python
    message = process_image_job.send(job_data)
    job_data["message_id"] = message.message_id  # Add after send — worker will receive this? No, it's already serialized.
    _store_job_type(message.message_id, JOB_TYPE_IMAGE)
    ```
  - **Actually, the correct fix**: In Dramatiq, `send()` serializes the arguments immediately. If `job_data` is a dict, it gets pickled/copied. Mutating it after `send()` won't affect the worker.
  - **Best solution**: Modify `process_image_job_sync` to accept `(job_data, message_id)`, then in `process_image_job`:
    ```python
    def process_image_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
        message = CurrentMessage.get_current_message()
        message_id = message.message_id if message else None
        try:
            result = process_image_job_sync(job_data, message_id)
            ...
    ```
  - But wait, `CurrentMessage` middleware is already available in Dramatiq if configured. Let me check if it's configured...
  
  **After Metis analysis, the cleanest approach is to add `CurrentMessage` middleware**:
  - In `app/queues/job_queue.py`, add `CurrentMessage` middleware to the broker. Then inside the actor, call `CurrentMessage.get_current_message().message_id`.
  - This is a one-line change plus import.

  **Revised approach**:
  - Add `from dramatiq.middleware import CurrentMessage` and `redis_broker.add_middleware(CurrentMessage())` to `app/queues/job_queue.py`.
  - Then `CurrentMessage.get_current_message().message_id` will work.

  **Must NOT do**:
  - Do NOT modify worker function signature.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (prerequisite)
  - **Blocks**: Tasks 1, 2, 3
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `CurrentMessage` middleware added to broker.
  - [ ] `CurrentMessage.get_current_message().message_id` returns a valid UUID string inside `process_image_job`.

  **QA Scenarios**:
  ```
  Scenario: Verify CurrentMessage middleware is active
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. python3 -c "import sys; sys.path.insert(0, 'app'); from app.queues.job_queue import redis_broker; from dramatiq.middleware import CurrentMessage; middleware = [m for m in redis_broker.middleware if isinstance(m, CurrentMessage)]; assert len(middleware) > 0; print('PASS')"
    Expected Result: Prints 'PASS'.
    Evidence: .sisyphus/evidence/task-a-middleware.txt
  ```

  **Commit**: YES (grouped with Tasks 1-3)

- [ ] **1. Create webhook utility module (`app/utils/webhook.py`)**

  **What to do**:
  - Create `app/utils/webhook.py` with a `send_webhook(url, payload)` function.
  - Implement retry loop: up to 10 attempts.
  - On each attempt: POST `payload` as JSON to `url`, timeout 30s.
  - If response status is 200: log success and return.
  - If response status is 5xx or request raises a network exception: log, sleep `30 × attempt`, retry.
  - If response status is 4xx: log error, do NOT retry.
  - After max retries (10): log final error.
  - **Must NOT block caller** — run the retry loop inside a `threading.Thread(daemon=True)`.
  - Import `requests`, `threading`, `time`.
  - Use existing logger: `from app.utils.logger import logger`.
  - Function signature:
    ```python
    def send_webhook(url: str, payload: dict) -> None:
        """Send webhook notification in a background thread with retry."""
    ```

  **Must NOT do**:
  - Do NOT use `async`/`await` — Dramatiq workers are sync.
  - Do NOT modify existing files.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (independent utility)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 2
  - **Blocked By**: Task A (if Task A adds middleware, but this utility doesn't depend on it)

  **References**:
  - `app/utils/__init__.py` — See if `app.utils` is a package with `__init__.py`.
  - `app/utils/logger.py` — Logger import pattern.

  **Acceptance Criteria**:
  - [ ] File `app/utils/webhook.py` exists.
  - [ ] `send_webhook` function defined with correct signature.
  - [ ] Uses `threading.Thread(daemon=True)` for non-blocking execution.
  - [ ] Retry loop up to 10 attempts with `time.sleep(30 * attempt)` backoff.
  - [ ] Only retries on 5xx and network errors, not 4xx.
  - [ ] Logs success, retry warnings, and final error.

  **QA Scenarios**:
  ```
  Scenario: Webhook succeeds on first attempt (200)
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. Mock requests.post to return status 200, call send_webhook, verify 1 call made.
    Expected Result: Exactly 1 POST call, no retries.
    Evidence: .sisyphus/evidence/task-1-success.txt

  Scenario: Webhook retries on 500 then succeeds
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. Mock requests.post to return 500 then 200, call send_webhook, verify 2 calls with mocked time.sleep.
    Expected Result: Exactly 2 POST calls, sleep called with 30.
    Evidence: .sisyphus/evidence/task-1-retry.txt

  Scenario: Webhook does NOT retry on 400
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. Mock requests.post to return 400, call send_webhook, verify 1 call only.
    Expected Result: Exactly 1 POST call, no retries.
    Evidence: .sisyphus/evidence/task-1-no-retry-4xx.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-1-success.txt` — REPL output confirming correct call count/args.
  - [ ] `task-1-retry.txt` — REPL output confirming retry behavior.
  - [ ] `task-1-no-retry-4xx.txt` — REPL output confirming no retry on 4xx.

  **Commit**: YES
  - Message: `feat(webhook): add send_webhook utility with retry and backoff`
  - Files: `app/utils/webhook.py`

- [ ] **2. Integrate webhook into worker (`app/queues/job_queue.py`)**

  **What to do**:
  - In `app/queues/job_queue.py`, in `process_image_job`, wrap the entire try/except in a way that webhook fires on BOTH success and failure:
    ```python
    @dramatiq.actor(store_results=True, max_retries=3, time_limit=300000)
    def process_image_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an image-to-text job using Dramatiq."""
        result = None
        error = None
        try:
            logger.info("Starting image-to-text job processing")
            result = process_image_job_sync(job_data)
            logger.info("Image-to-text job completed successfully")
            return result
        except Exception as e:
            logger.error("Error processing image-to-text job: %s", e, exc_info=True)
            error = str(e)
            raise
        finally:
            webhook_url = os.getenv("WEBHOOK_URL", "").strip()
            if webhook_url:
                try:
                    message = CurrentMessage.get_current_message()
                    message_id = message.message_id if message else None
                    payload = {
                        "message_id": message_id,
                        "status": "finished" if error is None else "failed",
                        "result": result if error is None else None,
                        "error": error,
                        **{k: v for k, v in job_data.items() if k in ("email", "session_id", "filename")}
                    }
                    send_webhook(webhook_url, payload)
                    logger.info("Webhook dispatched to %s for message_id: %s", webhook_url, message_id)
                except Exception:
                    logger.exception("Failed to dispatch webhook")
    ```

  **Must NOT do**:
  - Do NOT modify `app/workers/image_worker.py`.
  - Do NOT let webhook errors propagate to Dramatiq.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 1 and Task A)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: Tasks 1, A

  **References**:
  - `app/queues/job_queue.py:48-58` — Current `process_image_job` actor.
  - `app/utils/webhook.py` — `send_webhook` function (from Task 1).

  **Acceptance Criteria**:
  - [ ] Webhook dispatched on successful completion.
  - [ ] Webhook dispatched on failure with error payload.
  - [ ] Webhook errors caught and logged, not propagated.
  - [ ] `message_id` included in payload.

  **QA Scenarios**:
  ```
  Scenario: Webhook env var set — dispatch on success
    Tool: Bash (python REPL)
    Preconditions: Mock process_image_job_sync to succeed
    Steps:
      1. Set WEBHOOK_URL, mock process_image_job_sync, run actor, verify send_webhook called with finished status.
    Expected Result: send_webhook called once with status "finished".
    Evidence: .sisyphus/evidence/task-2-dispatch.txt

  Scenario: Webhook env var unset — silent skip
    Tool: Bash (python REPL)
    Preconditions: WEBHOOK_URL not set
    Steps:
      1. Run actor without env var, verify send_webhook not called.
    Expected Result: send_webhook not called.
    Evidence: .sisyphus/evidence/task-2-skip.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-2-dispatch.txt` — Confirms webhook dispatch with correct payload.
  - [ ] `task-2-skip.txt` — Confirms silent skip when env var absent.

  **Commit**: YES (grouped with Tasks 1, A)

- [ ] **3. Update env/config files**

  **What to do**:
  - `.env.example`: Add `WEBHOOK_URL=` (empty, documented as optional).
  - `docker-compose.yml`: Under `services.worker.environment`, add `WEBHOOK_URL: ${WEBHOOK_URL:-}`.
  - `docker-compose.prod.yml`: Same change under worker environment.

  **Must NOT do**:
  - Do NOT add to web service env — webhook runs in worker.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: none
  - **Blocked By**: none

  **Acceptance Criteria**:
  - [ ] `.env.example` contains `WEBHOOK_URL=` line.
  - [ ] `docker-compose.yml` worker service passes `WEBHOOK_URL`.
  - [ ] `docker-compose.prod.yml` worker service passes `WEBHOOK_URL`.

  **QA Scenarios**:
  ```
  Scenario: Verify env var present in compose files
    Tool: Bash (grep)
    Preconditions: None
    Steps:
      1. grep 'WEBHOOK_URL' docker-compose.yml docker-compose.prod.yml .env.example
    Expected Result: Each file shows at least one match.
    Evidence: .sisyphus/evidence/task-3-config.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-3-config.txt` — Grep output confirming env var in all three files.

  **Commit**: YES (grouped with Tasks 1-2, A)

- [ ] **4. Unit tests for webhook retry logic (`tests/test_webhook.py`)**

  **What to do**:
  - Create `tests/test_webhook.py`.
  - Cover: success (200), retry on 5xx, no retry on 4xx, max retries exceeded, backoff timing, network error retry, daemon thread.

  **Must NOT do**:
  - Do NOT make real HTTP requests in tests.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 6
  - **Blocked By**: Task 1

  **References**:
  - `app/utils/webhook.py` — Function under test.
  - `tests/test_jobs.py` — Mock patterns with `patch` and `pytest`.

  **Acceptance Criteria**:
  - [ ] Tests cover: success, retry on 5xx, no retry on 4xx, max retries, backoff formula, daemon thread.
  - [ ] `pytest tests/test_webhook.py` passes.

  **QA Scenarios**:
  ```
  Scenario: Run webhook unit tests
    Tool: Bash
    Preconditions: None
    Steps:
      1. pytest tests/test_webhook.py -v
    Expected Result: All tests pass, no failures.
    Evidence: .sisyphus/evidence/task-4-tests.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-4-tests.txt` — pytest output.

  **Commit**: YES (grouped with Tasks 1-3, A)

- [ ] **5. Integration tests for worker webhook (`tests/test_webhook.py`)**

  **What to do**:
  - Add integration test in `tests/test_webhook.py`:
    - Patch `process_image_job_sync` to return dummy result.
    - Set `WEBHOOK_URL` via `patch.dict(os.environ, ...)`.
    - Call `process_image_job` actor directly.
    - Assert `send_webhook` called with correct payload.
  - Also test: no `WEBHOOK_URL`, assert `send_webhook` not called.

  **Must NOT do**:
  - Do NOT test actual Dramatiq broker/Redis.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 6
  - **Blocked By**: Task 2

  **References**:
  - `app/queues/job_queue.py` — Actor integration point.
  - `tests/test_jobs.py` — Mock patterns for job_queue.

  **Acceptance Criteria**:
  - [ ] Integration test demonstrates webhook dispatch on job success.
  - [ ] Integration test demonstrates silent skip when env var missing.

  **QA Scenarios**:
  ```
  Scenario: Run integration tests
    Tool: Bash
    Preconditions: None
    Steps:
      1. pytest tests/test_webhook.py -v -k integration
    Expected Result: Integration tests pass.
    Evidence: .sisyphus/evidence/task-5-integration.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-5-integration.txt` — pytest output.

  **Commit**: YES (grouped with Tasks 1-4, A)

- [ ] **6. Run full test suite and verify no regressions**

  **What to do**:
  - Run `pytest` across the entire project.
  - Verify all existing tests (`test_jobs.py`, `test_image_to_text.py`) still pass.
  - Verify new tests (`test_webhook.py`) pass.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: NO (must wait for all prior tasks)
  - **Parallel Group**: Wave 3
  - **Blocks**: none
  - **Blocked By**: Tasks 1-5

  **Acceptance Criteria**:
  - [ ] `pytest` output shows 0 failures.
  - [ ] All new and existing tests pass.

  **QA Scenarios**:
  ```
  Scenario: Full regression test
    Tool: Bash
    Preconditions: None
    Steps:
      1. pytest --tb=short -v
    Expected Result: All tests pass, 0 failures.
    Evidence: .sisyphus/evidence/task-6-regression.txt
  ```

  **Evidence to Capture**:
  - [ ] `task-6-regression.txt` — Full pytest output.

  **Commit**: YES (final commit)

---

## Final Verification Wave (after ALL implementation tasks)

- [ ] **F1. Plan Compliance Audit** — `oracle`
  Read plan and verify:
  - `app/utils/webhook.py` exists with `send_webhook`.
  - `app/queues/job_queue.py` calls webhook after success and failure.
  - `.env.example`, `docker-compose.yml`, `docker-compose.prod.yml` updated.
  - Tests exist and pass.
  - No modifications to `app/queues/job_status.py`.
  Output: VERDICT

- [ ] **F2. Code Quality Review** — `unspecified-high`
  Run `pytest` + basic lint check.
  Output: VERDICT

- [ ] **F3. Scope Fidelity Check** — `deep`
  Compare git diff against plan. Verify no scope creep.
  Output: VERDICT

---

## Commit Strategy

- **Group 1** (`feat(webhook): add webhook notification with retry and backoff`):
  - Files: `app/utils/webhook.py`, `app/queues/job_queue.py`, `.env.example`, `docker-compose.yml`, `docker-compose.prod.yml`, `tests/test_webhook.py`

---

## Success Criteria

### Verification Commands
```bash
pytest --tb=short -v  # Expected: all tests pass, 0 failures
```

### Final Checklist
- [ ] `WEBHOOK_URL` optional env var documented and wired
- [ ] Webhook fires after successful job completion
- [ ] Retry logic: 30s × attempt, max 10 retries
- [ ] Non-blocking execution (background thread)
- [ ] Full result payload sent including `message_id`
- [ ] All tests pass