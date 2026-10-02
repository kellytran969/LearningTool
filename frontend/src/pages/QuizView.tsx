import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiErrorMessage, getQuiz, submitQuiz } from "../api/client";
import type { Quiz, QuizSubmitResponse } from "../api/types";
import Spinner from "../components/Spinner";

export default function QuizView() {
  const { slug } = useParams<{ slug: string }>();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<QuizSubmitResponse | null>(null);

  const fetchQuiz = useCallback(async () => {
    if (!slug) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setAnswers({});
    try {
      const data = await getQuiz(slug);
      setQuiz(data);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void fetchQuiz();
  }, [fetchQuiz]);

  const questions = useMemo(
    () => [...(quiz?.questions ?? [])].sort((a, b) => a.order - b.order),
    [quiz],
  );

  const answeredCount = questions.filter((q) => answers[q.id] !== undefined).length;
  const allAnswered = questions.length > 0 && answeredCount === questions.length;

  function selectChoice(questionId: number, choiceId: number) {
    setAnswers((prev) => ({ ...prev, [questionId]: choiceId }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!quiz || !allAnswered) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await submitQuiz(quiz.id, answers);
      setResult(res);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setSubmitError(apiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handleRetake() {
    setResult(null);
    setAnswers({});
    window.scrollTo({ top: 0 });
  }

  if (loading) {
    return (
      <div className="container page-center">
        <Spinner label="Loading quiz…" />
      </div>
    );
  }

  if (error || !quiz) {
    return (
      <div className="container">
        <div className="alert alert-error" role="alert">
          {error ?? "Quiz not found."}{" "}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void fetchQuiz()}
          >
            Retry
          </button>
        </div>
        {slug && (
          <Link to={`/courses/${slug}`} className="btn btn-ghost">
            ← Back to course
          </Link>
        )}
      </div>
    );
  }

  const resultByQuestion = new Map(
    (result?.results ?? []).map((r) => [r.question_id, r]),
  );

  return (
    <div className="container container-narrow">
      {slug && (
        <Link to={`/courses/${slug}`} className="back-link">
          ← Back to course
        </Link>
      )}

      <section className="card">
        <div className="card-body">
          <h1>{quiz.title}</h1>
          {quiz.description && <p className="muted">{quiz.description}</p>}

          {result && (
            <div
              className={`score-banner ${result.passed ? "score-pass" : "score-fail"}`}
              role="status"
              aria-live="polite"
            >
              <span className="score-big">
                {result.correct_count}/{result.total_questions}
              </span>
              <span className="score-detail">
                Score: {Math.round(result.score)}% ·{" "}
                {result.passed ? "Passed — nice work!" : "Not passed yet — review and retake."}
              </span>
              <div className="score-actions">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleRetake}
                >
                  Retake quiz
                </button>
                {slug && (
                  <Link to={`/courses/${slug}`} className="btn btn-ghost btn-sm">
                    Back to course
                  </Link>
                )}
              </div>
            </div>
          )}

          {submitError && (
            <div className="alert alert-error" role="alert">
              {submitError}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <ol className="quiz-list">
              {questions.map((q, qi) => {
                const r = resultByQuestion.get(q.id);
                return (
                  <li
                    key={q.id}
                    className={`quiz-question ${r ? (r.is_correct ? "q-correct" : "q-wrong") : ""}`}
                  >
                    <fieldset disabled={result !== null}>
                      <legend>
                        <span className="q-num">{qi + 1}.</span> {q.text}
                      </legend>
                      <div className="choice-list">
                        {q.choices.map((c) => {
                          const selected = answers[q.id] === c.id;
                          const isCorrectChoice = r?.correct_choice_id === c.id;
                          const isWrongPick =
                            r !== undefined && selected && !r.is_correct;
                          return (
                            <label
                              key={c.id}
                              className={`choice ${selected ? "choice-selected" : ""} ${isCorrectChoice && r ? "choice-correct" : ""} ${isWrongPick ? "choice-wrong" : ""}`}
                            >
                              <input
                                type="radio"
                                name={`question-${q.id}`}
                                value={c.id}
                                checked={selected}
                                onChange={() => selectChoice(q.id, c.id)}
                                aria-label={c.text}
                              />
                              <span>{c.text}</span>
                              {r && isCorrectChoice && (
                                <span className="choice-mark" aria-label="Correct answer">✓</span>
                              )}
                              {isWrongPick && (
                                <span className="choice-mark" aria-label="Your answer was wrong">✗</span>
                              )}
                            </label>
                          );
                        })}
                      </div>
                      {r && r.explanation && (
                        <p className={`q-explain ${r.is_correct ? "" : "q-explain-wrong"}`}>
                          {r.is_correct ? "Correct. " : "Not quite. "}
                          {r.explanation}
                        </p>
                      )}
                    </fieldset>
                  </li>
                );
              })}
            </ol>

            {!result && (
              <div className="quiz-submit">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={!allAnswered || submitting}
                >
                  {submitting
                    ? "Submitting…"
                    : `Submit quiz (${answeredCount}/${questions.length} answered)`}
                </button>
                {!allAnswered && (
                  <p className="muted">Answer all questions to submit.</p>
                )}
              </div>
            )}
          </form>
        </div>
      </section>
    </div>
  );
}
