# LearningTool — Backend

Django REST Framework API for the LearningTool AI-based learning platform.
Serves the course catalog, lessons, quizzes, progress tracking, dashboard,
and a deterministic recommendation engine.

## Performance design

- **Redis caching** (via `django-redis`) on the read-heavy endpoints:
  course list (120s), course detail (300s), lesson detail (300s),
  per-user dashboard (60s). Without `REDIS_URL` it falls back to
  local-memory caching so everything still works.
- **Database indexing**: `slug`, `category`, `is_published`, `topic_tag`,
  `(course, order)`, and `(user, quiz)` are indexed; querysets use
  `select_related` / `prefetch_related` and `Count` annotations —
  no endpoint issues N+1 queries.
- **Cache invalidation** in `learning/signals.py`: catalog writes bust
  `courses:*` keys, progress writes bust that user's dashboard key.
- Pagination (12/page) and throttling (60 req/min anon, 600 req/hour authed).

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional; defaults work out of the box
python manage.py migrate
python manage.py seed_demo   # 6 courses, 30 lessons, 6 quizzes + demo user
python manage.py runserver   # http://127.0.0.1:8000
```

Demo login: `demo` / `learn1234`.

### Environment variables

| Variable       | Default    | Description                                  |
|----------------|------------|----------------------------------------------|
| `SECRET_KEY`   | dev-only   | Django secret key                            |
| `DEBUG`        | `True`     | Debug mode                                   |
| `DATABASE_URL` | *(unset)*  | e.g. `postgres://user:pass@localhost:5432/learningtool`; unset → SQLite |
| `REDIS_URL`    | *(unset)*  | e.g. `redis://localhost:6379/1`; unset → local-memory cache |

Run the tests with `python manage.py test` (25 tests, SQLite).

## API reference

Base path: `/api/`. Auth is JWT (`Authorization: Bearer <access>`).

| Method | Endpoint                          | Auth | Description                                              |
|--------|-----------------------------------|------|----------------------------------------------------------|
| POST   | `/auth/register/`                 | –    | Register; returns `{user, access, refresh}`               |
| POST   | `/auth/login/`                    | –    | Login; returns `{access, refresh}`                        |
| POST   | `/auth/refresh/`                  | –    | Refresh access token                                      |
| GET    | `/auth/me/`                       | ✓    | Current user                                              |
| GET    | `/courses/`                       | –    | Paginated catalog; `?search=&category=&difficulty=&ordering=(newest\|popular\|title)&page=` |
| GET    | `/courses/<slug>/`                | –    | Course detail with lessons + `quiz_id`                    |
| POST   | `/courses/<slug>/enroll/`         | ✓    | Enroll (idempotent); returns `progress_pct`               |
| GET    | `/lessons/<id>/`                  | ✓    | Lesson detail (Markdown content)                          |
| POST   | `/lessons/<id>/complete/`         | ✓    | Mark complete (requires enrollment)                       |
| GET    | `/courses/<slug>/quiz/`           | ✓    | Quiz with questions/choices (answers hidden)              |
| POST   | `/quizzes/<id>/submit/`           | ✓    | Grade submission; returns score + per-question review    |
| GET    | `/dashboard/`                     | ✓    | Enrolled courses, progress, stats, recent attempts        |
| GET    | `/recommendations/`               | ✓    | Personalized lesson/course recommendations                |

### Recommendation engine (`learning/recommendations.py`)

Pure-Python, deterministic, no ML dependencies:

1. **Weak topics** — quiz answers aggregated per `topic_tag`; topics with
   ≥3 answers and accuracy < 70% recommend the first incomplete lesson
   tagged with that topic.
2. **Continue learning** — first incomplete lesson of the most recent
   enrollment.
3. **Popular courses** — most-enrolled courses the user hasn't joined.

## Project layout

```
backend/
├── config/                 # settings (env-driven), urls, wsgi
├── learning/
│   ├── models.py           # Course, Lesson, Quiz, Question, Choice,
│   │                       # Enrollment, LessonProgress, QuizAttempt, QuizAnswer
│   ├── views.py            # viewsets + API views (cached reads)
│   ├── serializers.py
│   ├── recommendations.py  # deterministic recommendation engine
│   ├── signals.py          # cache invalidation on writes
│   ├── cache_utils.py
│   ├── tests.py            # 25 API tests
│   └── management/commands/seed_demo.py
└── requirements.txt
```
