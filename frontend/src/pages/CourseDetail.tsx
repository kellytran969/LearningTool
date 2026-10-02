import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  apiErrorMessage,
  enrollCourse,
  getCourse,
} from "../api/client";
import type { CourseDetail as CourseDetailType } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import Spinner from "../components/Spinner";

function pretty(value: string): string {
  return value
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function CourseDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { user } = useAuth();
  const [course, setCourse] = useState<CourseDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [enrolling, setEnrolling] = useState(false);
  const [enrolled, setEnrolled] = useState(false);
  const [enrollError, setEnrollError] = useState<string | null>(null);

  const fetchCourse = useCallback(async () => {
    if (!slug) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getCourse(slug);
      setCourse(data);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void fetchCourse();
  }, [fetchCourse]);

  async function handleEnroll() {
    if (!slug || !user) return;
    setEnrolling(true);
    setEnrollError(null);
    try {
      await enrollCourse(slug);
      setEnrolled(true);
    } catch (err) {
      setEnrollError(apiErrorMessage(err));
    } finally {
      setEnrolling(false);
    }
  }

  if (loading) {
    return (
      <div className="container page-center">
        <Spinner label="Loading course…" />
      </div>
    );
  }

  if (error || !course) {
    return (
      <div className="container">
        <div className="alert alert-error" role="alert">
          {error ?? "Course not found."}{" "}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void fetchCourse()}
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

  const lessons = [...(course.lessons ?? [])].sort((a, b) => a.order - b.order);

  return (
    <div className="container">
      <Link to="/" className="back-link">
        ← All courses
      </Link>

      <section className="course-header card">
        <div className="card-body">
          <div className="badge-row">
            <span className="badge">{pretty(String(course.category))}</span>
            <span className="badge badge-outline">
              {pretty(String(course.difficulty))}
            </span>
          </div>
          <h1>{course.title}</h1>
          <p className="course-meta">
            {course.lesson_count} lesson{course.lesson_count === 1 ? "" : "s"} ·{" "}
            {course.enrollment_count.toLocaleString()} learner
            {course.enrollment_count === 1 ? "" : "s"}
          </p>
          <p className="course-description">{course.description}</p>

          {enrollError && (
            <div className="alert alert-error" role="alert">
              {enrollError}
            </div>
          )}

          {user ? (
            enrolled ? (
              <span className="enrolled-pill" role="status">
                ✓ Enrolled — happy learning!
              </span>
            ) : (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void handleEnroll()}
                disabled={enrolling}
              >
                {enrolling ? "Enrolling…" : "Enroll now"}
              </button>
            )
          ) : (
            <p className="muted">
              <Link to="/login">Log in</Link> to enroll and track your progress.
            </p>
          )}
        </div>
      </section>

      <div className="detail-grid">
        <section className="card" aria-label="Lessons">
          <div className="card-body">
            <h2>Lessons</h2>
            {lessons.length === 0 ? (
              <p className="muted">Lessons are on their way.</p>
            ) : (
              <ol className="lesson-list">
                {lessons.map((lesson) => (
                  <li key={lesson.id} className="lesson-row">
                    {user ? (
                      <Link
                        to={`/lessons/${lesson.id}`}
                        className="lesson-link"
                      >
                        <span className="lesson-order">{lesson.order}</span>
                        <span className="lesson-info">
                          <span className="lesson-title">{lesson.title}</span>
                          <span className="lesson-meta">
                            {lesson.duration_minutes} min
                            {lesson.topic_tags?.length > 0 &&
                              ` · ${lesson.topic_tags.join(", ")}`}
                          </span>
                        </span>
                      </Link>
                    ) : (
                      <span className="lesson-link lesson-locked">
                        <span className="lesson-order">{lesson.order}</span>
                        <span className="lesson-info">
                          <span className="lesson-title">{lesson.title}</span>
                          <span className="lesson-meta">
                            {lesson.duration_minutes} min ·{" "}
                            <Link to="/login">log in to view</Link>
                          </span>
                        </span>
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>

        <aside className="card" aria-label="Quiz">
          <div className="card-body">
            <h2>Test yourself</h2>
            {course.quiz_id ? (
              <>
                <p className="muted">
                  Take the course quiz to check what you've learned.
                </p>
                {user ? (
                  <Link
                    to={`/courses/${course.slug}/quiz`}
                    className="btn btn-primary"
                  >
                    Start quiz
                  </Link>
                ) : (
                  <p className="muted">
                    <Link to="/login">Log in</Link> to take the quiz.
                  </p>
                )}
              </>
            ) : (
              <p className="muted">No quiz for this course yet.</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
