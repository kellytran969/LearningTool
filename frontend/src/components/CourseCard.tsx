import { Link } from "react-router-dom";
import type { CourseSummary } from "../api/types";

function pretty(value: string): string {
  return value
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function CourseCard({ course }: { course: CourseSummary }) {
  return (
    <Link
      to={`/courses/${course.slug}`}
      className="card course-card"
      aria-label={`View course: ${course.title}`}
    >
      <div className="course-thumb" aria-hidden="true">
        {course.thumbnail_url ? (
          <img src={course.thumbnail_url} alt="" loading="lazy" />
        ) : (
          <span className="course-thumb-fallback">
            {(course.title || "?").charAt(0).toUpperCase()}
          </span>
        )}
      </div>
      <div className="card-body">
        <div className="badge-row">
          <span className="badge">{pretty(String(course.category))}</span>
          <span className="badge badge-outline">
            {pretty(String(course.difficulty))}
          </span>
        </div>
        <h3 className="course-title">{course.title}</h3>
        <p className="course-meta">
          {course.lesson_count} lesson{course.lesson_count === 1 ? "" : "s"} ·{" "}
          {course.enrollment_count.toLocaleString()} learner
          {course.enrollment_count === 1 ? "" : "s"}
        </p>
      </div>
    </Link>
  );
}
