# Draft: shadcn/ui Admin Dashboard

## Requirements (Confirmed)
- Build a simple shadcn/ui dashboard for monitoring OCR processing
- Dashboard frontend built with React + Vite + shadcn/ui
- Should display: processing status, job history, image input preview, OCR output
- Protected by a simple token configured via `.env` (`DASHBOARD_TOKEN`)
- Token is entered on a login page and saved to `localStorage`
- All admin API endpoints require the token header
- Token must be included in `.env.example`, `.env`, and docker-compose files
- History kept in Redis only (7-day TTL, no SQL/DB changes)

## Technical Decisions
- **Frontend**: React 18 + Vite + Tailwind CSS + shadcn/ui
- **Backend**: New FastAPI admin router with token-auth dependency
- **Static Files**: Build output copied to `app/static/dashboard/` and served by FastAPI `StaticFiles`
- **Image Serving**: Protected admin endpoint streams images from `shared_files/`
- **Job List**: Scan Redis for `job:type:*` keys to reconstruct history
- **No persistent DB** — keep Redis-only as user requested

## Scope Boundaries
- **INCLUDE**: Admin endpoints, React dashboard, token auth, image serving, docker updates
- **EXCLUDE**: SQL/DB changes, user management, real-time WebSocket updates, metrics collection beyond existing logs
