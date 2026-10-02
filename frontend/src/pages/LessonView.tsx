import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import {
  apiErrorMessage,
  completeLesson,
  getCourse,
  getLesson,
} from "../api/client";
import type {
  LessonDetail,
  LessonSummary,
} from "../api/types";
import Spinner from "../components/Spinner";

export default function LessonView() {
  const { id } = useParams<{ id: string }>();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [siblings, setSiblings] = useState<LessonSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [completing, setCompleting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [completeError, setCompleteError] = useState<string | null>(null);
  const [progressPct, setProgressPct] = useState<number | null>(null);

  const fetchLesson = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    setCompleted(false);
    setProgressPct(null);
    try {
      const data = await getLesson(id);
      setLesson(data);
      // Pull the course to get lesson ordering for prev/next navigation.
      if (data.course?.slug) {
        try {
          const course = await getCourse(data.course.slug);
          setSiblings(
            [...(course.lessons ?? [])].sort((a, b) => a.order - b.order),
          );
        } catch {
          setSiblings([]);
        }
      }
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void fetchLesson();
  }, [fetchLesson]);

  async function handleComplete() {
    if (!id) return;
    setCompleting(true);
    setCompleteError(null);
    try {
      const res = await completeLesson(id);
      setCompleted(res.completed);
      setProgressPct(res.progress_pct);
    } catch (err) {
      setCompleteError(apiErrorMessage(err));
    } finally {
      setCompleting(false);
    }
  }

  if (loading) {
    return (
      <div className="container page-center">
        <Spinner label="Loading lesson…" />
      </div>
    );
  }

  if (error || !lesson) {
    return (
      <div className="container">
        <div className="alert alert-error" role="alert">
          {error ?? "Lesson not found."}{" "}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void fetchLesson()}
          >
            Retry
          </button>
        </div>
        <Link to="/" className="btn btn-ghost">
          ← Back to courses
        </Link>
      </div>
    );
  }

  const idx = siblings.findIndex((l) => l.id === lesson.id);
  const prev = idx > 0 ? siblings[idx - 1] : null;
  const next = idx >= 0 && idx < siblings.length - 1 ? siblings[idx + 1] : null;

  return (
    <div className="container container-narrow">
      <Link to={`/courses/${lesson.course.slug}`} className="back-link">
        ← {lesson.course.title}
      </Link>

      <article className="card lesson-article">
        <div className="card-body">
          <p className="lesson-kicker">
            Lesson {lesson.order} · {lesson.duration_minutes} min
          </p>
          <h1>{lesson.title}</h1>
          {lesson.topic_tags?.length > 0 && (
            <div className="badge-row" aria-label="Topics">
              {lesson.topic_tags.map((tag) => (
                <span key={tag} className="badge badge-outline">
                  {tag}
                </span>
              ))}
            </div>
          )}
          <div className="markdown-body">
            <ReactMarkdown>{lesson.content}</ReactMarkdown>
          </div>

          {completeError && (
            <div className="alert alert-error" role="alert">
              {completeError}
            </div>
          )}

          <div className="lesson-actions">
            {completed || progressPct !== null ? (
              <span className="enrolled-pill" role="status">
                ✓ Completed
                {progressPct !== null && ` — course progress ${Math.round(progressPct)}%`}
              </span>
            ) : (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void handleComplete()}
                disabled={completing}
              >
                {completing ? "Saving…" : "Mark as complete"}
              </button>
            )}
          </div>
        </div>
      </article>

      <nav className="pager" aria-label="Lesson navigation">
        {prev ? (
          <Link to={`/lessons/${prev.id}`} className="btn btn-ghost">
            ← {prev.title}
          </Link>
        ) : (
          <span />
        )}
        {next ? (
          <Link to={`/lessons/${next.id}`} className="btn btn-ghost">
            {next.title} →
          </Link>
        ) : (
          <Link to={`/courses/${lesson.course.slug}`} className="btn btn-ghost">
            Back to course →
          </Link>
        )}
      </nav>
    </div>
  );
}
