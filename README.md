# LearningTool

An AI-based learning platform: browse courses, work through lessons, take
quizzes, track progress on a personal dashboard, and get lesson
recommendations driven by quiz performance.

**Stack:** Django REST Framework · PostgreSQL (SQLite for zero-config dev) ·
Redis caching · React + TypeScript + Vite

## Quickstart

You need Python 3.12+ and Node 18+.

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo     # demo content + user demo/learn1234
python manage.py runserver      # http://127.0.0.1:8000

# 2. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env           # VITE_API_URL defaults to http://localhost:8000
npm run dev                    # http://127.0.0.1:5173
```

Log in with `demo` / `learn1234` to see an enrolled learner's dashboard,
or register a fresh account.

### With Postgres + Redis (Docker, optional)

```bash
docker compose up -d db redis   #Postgres 16 + Redis 7
cd backend
DATABASE_URL=postgres://learning:learning@localhost:5432/learningtool \
REDIS_URL=redis://localhost:6379/1 \
python manage.py migrate && python manage.py seed_demo
```

The app runs identically on SQLite/local-memory cache without them.

## What's inside

- `backend/` — Django REST API: JWT auth, cached catalog endpoints,
  quiz grading, progress tracking, deterministic recommendation engine,
  25 API tests. See `backend/README.md` for the full API table.
- `frontend/` — React + TypeScript SPA: catalog with search/filters,
  course pages, Markdown lessons, quizzes with instant review, dashboard
  with progress bars and recommendations. Route-level code splitting
  (`React.lazy`) keeps the initial bundle small; vendor chunks are split
  in `vite.config.ts`.

## Performance work

This project was built around the performance story:

- **Backend:** Redis caching on read-heavy endpoints with
  write-through invalidation, DB indexes on filtered columns,
  annotation-based counts (no N+1), pagination + throttling.
- **Frontend:** lazy-loaded routes so only the catalog loads up front;
  `npm run build` emits a separate chunk per page.
