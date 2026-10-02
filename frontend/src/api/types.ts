// TypeScript interfaces mirroring the LearningTool backend API contract.
// Fields are kept tolerant (optional chaining in consumers) in case of minor
// drift between frontend and backend.

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface RegisterResponse extends AuthTokens {
  user: User;
}

export interface LoginResponse extends AuthTokens {}

export type Category =
  | "programming"
  | "data-science"
  | "ai-ml"
  | "web-dev"
  | "math";

export type Difficulty = "beginner" | "intermediate" | "advanced";

export type Ordering = "newest" | "popular" | "title";

export interface CourseSummary {
  id: number;
  slug: string;
  title: string;
  category: Category | string;
  difficulty: Difficulty | string;
  thumbnail_url: string | null;
  lesson_count: number;
  enrollment_count: number;
}

export interface LessonSummary {
  id: number;
  title: string;
  order: number;
  duration_minutes: number;
  topic_tags: string[];
}

export interface CourseDetail extends CourseSummary {
  description: string;
  lessons: LessonSummary[];
  quiz_id: number | null;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CourseListParams {
  search?: string;
  category?: string;
  difficulty?: string;
  ordering?: Ordering | string;
  page?: number;
  page_size?: number;
}

export interface CourseRef {
  slug: string;
  title: string;
  thumbnail_url?: string | null;
}

export interface EnrollResponse {
  id: number;
  enrolled_at: string;
  progress_pct: number;
  course: { slug: string; title: string };
}

export interface LessonDetail {
  id: number;
  title: string;
  order: number;
  duration_minutes: number;
  topic_tags: string[];
  content: string;
  course: { slug: string; title: string };
}

export interface CompleteLessonResponse {
  completed: boolean;
  progress_pct: number;
}

export interface Choice {
  id: number;
  text: string;
}

export interface Question {
  id: number;
  text: string;
  order: number;
  topic_tag: string;
  choices: Choice[];
}

export interface Quiz {
  id: number;
  title: string;
  description: string;
  questions: Question[];
}

export interface QuizResultItem {
  question_id: number;
  selected_choice_id: number | null;
  correct_choice_id: number;
  is_correct: boolean;
  explanation: string;
}

export interface QuizSubmitResponse {
  score: number;
  total_questions: number;
  correct_count: number;
  passed: boolean;
  results: QuizResultItem[];
}

export interface EnrolledCourse {
  course: CourseRef;
  progress_pct: number;
  completed_lessons: number;
  total_lessons: number;
  enrolled_at: string;
}

export interface DashboardStats {
  courses_enrolled: number;
  courses_completed: number;
  lessons_completed: number;
  quizzes_taken: number;
  average_score: number;
}

export interface RecentAttempt {
  quiz_title: string;
  course_slug: string;
  score: number;
  submitted_at: string;
}

export interface Dashboard {
  enrolled_courses: EnrolledCourse[];
  stats: DashboardStats;
  recent_attempts: RecentAttempt[];
}

export interface Recommendation {
  kind: "lesson" | "course";
  title: string;
  reason: string;
  url: string;
  course_slug: string;
  lesson_id: number | null;
}
