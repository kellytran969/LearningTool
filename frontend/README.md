# LearningTool — Frontend

React + TypeScript + Vite frontend for **LearningTool**, an AI-based learning
platform. Browse the course catalog, enroll, read lessons, take quizzes, and
track progress on a personal dashboard with AI-style recommendations.

## Prerequisites

- Node.js 18+ (tested with Node 24) and npm 10+
- The LearningTool backend running (see `../backend/README.md`)

## Setup

```bash
cd frontend
cp .env.example .env   # then set VITE_API_URL to your backend URL
npm install
```

## Scripts

| Command          | What it does                              |
| ---------------- | ----------------------------------------- |
| `npm run dev`    | Start the Vite dev server (http://localhost:5173) |
| `npm run build`  | Type-check (`tsc --noEmit`) and build for production into `dist/` |
| `npm run preview`| Serve the production build locally        |

## Configuration

| Variable       | Default                 | Description                        |
| -------------- | ----------------------- | ---------------------------------- |
| `VITE_API_URL` | `http://localhost:8000` | Base URL of the Django API (no trailing slash) |

## Code splitting

Every page except the course catalog is loaded with `React.lazy()`, so the
initial bundle only ships what's needed for first paint — this is the same
technique that cut the original platform's initial load time roughly in half.

`vite.config.ts` additionally splits vendor code into long-lived cacheable
chunks (`react-vendor`, `axios-vendor`, `markdown-vendor`), and each lazy page
gets its own chunk. A production build emits, among others:

- `Login-*.js`, `Register-*.js`, `CourseDetail-*.js`, `LessonView-*.js`,
  `QuizView-*.js`, `Dashboard-*.js` — one chunk per lazy route
- `react-vendor-*.js`, `axios-vendor-*.js`, `markdown-vendor-*.js` — vendor chunks
- `index-*.js` — the entry (catalog + shared components)

## Project structure

```
src/
  main.tsx            # React root
  App.tsx             # Router + lazy route definitions
  index.css           # All styling (no UI framework)
  vite-env.d.ts
  api/
    types.ts          # TS interfaces for every API payload
    client.ts         # axios instance, JWT refresh, typed API functions
  auth/
    AuthContext.tsx   # user session, login/register/logout, token persistence
  components/
    Navbar.tsx  CourseCard.tsx  ProtectedRoute.tsx  Spinner.tsx  ProgressBar.tsx
  pages/
    Catalog.tsx       # eagerly loaded: search, filters, pagination
    CourseDetail.tsx  # lazy
    LessonView.tsx    # lazy (markdown lessons, mark-complete, prev/next)
    QuizView.tsx      # lazy (submit, score, per-question review, retake)
    Dashboard.tsx     # lazy (stats, progress, recommendations, attempts)
    Login.tsx         # lazy
    Register.tsx      # lazy
```

## Auth flow

Access/refresh JWTs are stored in `localStorage`. Every request carries the
access token; on a 401 the client refreshes once via
`POST /api/auth/refresh/` and retries. If refresh fails, tokens are cleared
and the user is redirected to `/login`.
