# Task 2: Webhook Integration Learnings

## Implementation Pattern

### Finally Block for Side Effects
- Use `finally` block to ensure webhook fires on both success and failure
- Track `result` and `error` variables before try/except
- Webhook dispatch is non-blocking (send_webhook uses daemon thread)

### Error Isolation
- Wrap webhook call in its own try/except to prevent webhook failures from crashing the actor
- Log webhook errors with `logger.exception()` for full stack trace

### Payload Structure
```python
{
    "message_id": str | None,
    "status": "finished" | "failed",
    "result": dict | None,
    "error": str | None,
    "email": str | None,  # optional
    "session_id": str | None,  # optional
    "filename": str | None,  # optional
}
```

### CurrentMessage Middleware
- Dramatiq's `CurrentMessage` middleware must be added to broker
- Access via `CurrentMessage.get_current_message()` in finally block
- Returns message object with `message_id` attribute

## Key Files
- `app/queues/job_queue.py`: Modified `process_image_job` actor
- `app/utils/webhook.py`: `send_webhook()` function (unchanged)
