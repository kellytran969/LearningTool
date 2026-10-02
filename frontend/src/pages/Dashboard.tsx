import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  apiErrorMessage,
  getDashboard,
  getRecommendations,
} from "../api/client";
import type { Dashboard as DashboardType, Recommendation } from "../api/types";
import ProgressBar from "../components/ProgressBar";
import Spinner from "../components/Spinner";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString();
}

export default function Dashboard() {
  const [dashboard, setDashboard] = useState<DashboardType | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dash, recs] = await Promise.all([
        getDashboard(),
        getRecommendations().catch(() => [] as Recommendation[]),
      ]);
      setDashboard(dash);
      setRecommendations(recs ?? []);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  if (loading) {
    return (
      <div className="container page-center">
        <Spinner label="Loading dashboard…" />
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="container">
        <div className="alert alert-error" role="alert">
          {error ?? "Could not load your dashboard."}{" "}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void fetchAll()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const stats = dashboard.stats;
  const statCards = [
    { label: "Courses enrolled", value: stats.courses_enrolled },
    { label: "Courses completed", value: stats.courses_completed },
    { label: "Lessons completed", value: stats.lessons_completed },
    { label: "Quizzes taken", value: stats.quizzes_taken },
    {
      label: "Average quiz score",
      value: `${Math.round(stats.average_score)}%`,
    },
  ];

  return (
    <div className="container">
      <h1 className="page-title">Your dashboard</h1>

      <section className="stat-grid" aria-label="Learning statistics">
        {statCards.map((s) => (
          <div key={s.label} className="card stat-card">
            <div className="card-body">
              <span className="stat-value">{s.value}</span>
              <span className="stat-label">{s.label}</span>
            </div>
          </div>
        ))}
      </section>

      <div className="detail-grid">
        <section className="card" aria-label="Enrolled courses">
          <div className="card-body">
            <h2>My courses</h2>
            {dashboard.enrolled_courses.length === 0 ? (
              <div className="empty-state">
                <p>You haven't enrolled in any courses yet.</p>
                <Link to="/" className="btn btn-primary btn-sm">
                  Browse courses
                </Link>
              </div>
            ) : (
              <ul className="enrolled-list">
                {dashboard.enrolled_courses.map((e) => (
                  <li key={e.course.slug} className="enrolled-row">
                    <Link
                      to={`/courses/${e.course.slug}`}
                      className="enrolled-title"
                    >
                      {e.course.title}
                    </Link>
                    <div className="enrolled-progress">
                      <ProgressBar pct={e.progress_pct} />
                      <span className="enrolled-meta">
                        {Math.round(e.progress_pct)}% · {e.completed_lessons}/
                        {e.total_lessons} lessons
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <div className="side-stack">
          <section className="card" aria-label="Recommended for you">
            <div className="card-body">
              <h2>Recommended for you</h2>
              {recommendations.length === 0 ? (
                <p className="muted">
                  Enroll in a course and take quizzes — we'll suggest what to
                  learn next.
                </p>
              ) : (
                <ul className="rec-list">
                  {recommendations.map((rec, i) => (
                    <li key={`${rec.kind}-${i}`} className="rec-row">
                      <span
                        className="rec-icon"
                        aria-hidden="true"
                        title={rec.kind === "lesson" ? "Lesson" : "Course"}
                      >
                        {rec.kind === "lesson" ? "📖" : "🎓"}
                      </span>
                      <div className="rec-body">
                        <Link to={rec.url} className="rec-title">
                          {rec.title}
                        </Link>
                        <p className="rec-reason">{rec.reason}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="card" aria-label="Recent quiz attempts">
            <div className="card-body">
              <h2>Recent quiz attempts</h2>
              {dashboard.recent_attempts.length === 0 ? (
                <p className="muted">No quiz attempts yet.</p>
              ) : (
                <table className="attempt-table">
                  <thead>
                    <tr>
                      <th scope="col">Quiz</th>
                      <th scope="col">Score</th>
                      <th scope="col">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.recent_attempts.map((a, i) => (
                      <tr key={`${a.quiz_title}-${i}`}>
                        <td>
                          <Link to={`/courses/${a.course_slug}`}>
                            {a.quiz_title}
                          </Link>
                        </td>
                        <td>{Math.round(a.score)}%</td>
                        <td>{formatDate(a.submitted_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
