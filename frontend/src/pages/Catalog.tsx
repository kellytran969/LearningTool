import { useCallback, useEffect, useRef, useState } from "react";
import { apiErrorMessage, listCourses } from "../api/client";
import type { CourseSummary, Paginated } from "../api/types";
import CourseCard from "../components/CourseCard";
import Spinner from "../components/Spinner";

const CATEGORIES = [
  { value: "", label: "All categories" },
  { value: "programming", label: "Programming" },
  { value: "data-science", label: "Data Science" },
  { value: "ai-ml", label: "AI / ML" },
  { value: "web-dev", label: "Web Dev" },
  { value: "math", label: "Math" },
];

const DIFFICULTIES = [
  { value: "", label: "All levels" },
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

const ORDERINGS = [
  { value: "newest", label: "Newest" },
  { value: "popular", label: "Most popular" },
  { value: "title", label: "Title A–Z" },
];

const PAGE_SIZE = 12;

export default function Catalog() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [ordering, setOrdering] = useState("newest");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paginated<CourseSummary> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<number | undefined>(undefined);

  // Debounce the search box so we don't fire a request per keystroke.
  useEffect(() => {
    window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 400);
    return () => window.clearTimeout(debounceRef.current);
  }, [searchInput]);

  const fetchCourses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listCourses({
        search: search || undefined,
        category: category || undefined,
        difficulty: difficulty || undefined,
        ordering,
        page,
        page_size: PAGE_SIZE,
      });
      setData(result);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [search, category, difficulty, ordering, page]);

  useEffect(() => {
    void fetchCourses();
  }, [fetchCourses]);

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  return (
    <div className="container">
      <section className="hero">
        <h1>Learn something new today</h1>
        <p>
          Interactive courses with lessons and quizzes, tuned to how you learn.
        </p>
      </section>

      <section className="filters" aria-label="Course filters">
        <div className="filter-group filter-search">
          <label htmlFor="catalog-search" className="sr-only">
            Search courses
          </label>
          <input
            id="catalog-search"
            type="search"
            placeholder="Search courses…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="input"
          />
        </div>
        <div className="filter-group">
          <label htmlFor="catalog-category" className="sr-only">
            Category
          </label>
          <select
            id="catalog-category"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
            className="input"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="catalog-difficulty" className="sr-only">
            Difficulty
          </label>
          <select
            id="catalog-difficulty"
            value={difficulty}
            onChange={(e) => {
              setDifficulty(e.target.value);
              setPage(1);
            }}
            className="input"
          >
            {DIFFICULTIES.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="catalog-ordering" className="sr-only">
            Sort order
          </label>
          <select
            id="catalog-ordering"
            value={ordering}
            onChange={(e) => {
              setOrdering(e.target.value);
              setPage(1);
            }}
            className="input"
          >
            {ORDERINGS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </section>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}{" "}
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void fetchCourses()}>
            Retry
          </button>
        </div>
      )}

      {loading && !data ? (
        <Spinner label="Loading courses…" />
      ) : data && data.results.length > 0 ? (
        <>
          <p className="result-count" aria-live="polite">
            {data.count} course{data.count === 1 ? "" : "s"}
          </p>
          <div className="course-grid">
            {data.results.map((course) => (
              <CourseCard key={course.id} course={course} />
            ))}
          </div>
          {totalPages > 1 && (
            <nav className="pager" aria-label="Pagination">
              <button
                type="button"
                className="btn btn-ghost"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ← Previous
              </button>
              <span className="pager-info" aria-live="polite">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next →
              </button>
            </nav>
          )}
        </>
      ) : (
        !loading && (
          <div className="empty-state">
            <p>No courses found.</p>
            <p className="muted">Try a different search or clear the filters.</p>
          </div>
        )
      )}
    </div>
  );
}
