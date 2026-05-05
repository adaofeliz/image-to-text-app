# Admin Dashboard Notepad

## Conventions
- Token header: `X-Dashboard-Token`
- Redis job type keys: `job:type:{message_id}`
- Static files path: `app/static/dashboard/`
- Frontend source: `app/frontend/`
- Admin API prefix: `/admin/api`
- Dashboard SPA path: `/dashboard`

## Decisions
- Multi-stage Docker build (Node 22 alpine + Python 3.11 slim)
- React + Vite + shadcn/ui (NOT Next.js)
- Redis-only history (7-day TTL, no SQL)
- Simple string token comparison (no JWT, no bcrypt)
- Polling every 5 seconds for real-time updates
- Status filter: All / Pending / Finished / Failed

## Gotchas
- StaticFiles must be mounted LAST in FastAPI (after API routes)
- 404 handler must serve index.html for /dashboard paths
- Vite build must use relative paths (`base: './'`)
- Image endpoint must validate path within shared_files/ (prevent traversal)
- Redis SCAN not KEYS for production safety

## Patterns
- FastAPI router pattern: `app/routes/__init__.py` aggregates all routers
- Auth dependency pattern: `Depends(verify_admin_token)` on router
- Job status reuse: `get_job_status()` from `app.queues.job_status`
- When using shadcn-ui components with `@base-ui/react`, the `asChild` prop is replaced by the `render` prop (e.g., `render={<Link to="..." />}`).
- The shadcn CLI might create the `@` directory at the root of the project instead of inside `src`. It's important to move it to `src` and update imports if `tsconfig.json` expects it to be in `src`.
