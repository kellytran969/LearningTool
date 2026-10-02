import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  InternalAxiosRequestConfig,
} from "axios";
import type {
  CompleteLessonResponse,
  CourseDetail,
  CourseListParams,
  CourseSummary,
  Dashboard,
  EnrollResponse,
  LessonDetail,
  LoginResponse,
  Paginated,
  Quiz,
  QuizSubmitResponse,
  Recommendation,
  RegisterResponse,
  User,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ??
  "http://localhost:8000";

const ACCESS_KEY = "lt_access_token";
const REFRESH_KEY = "lt_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE.replace(/\/$/, "")}/api`,
  headers: { "Content-Type": "application/json" },
});

// Attach the access token to every request.
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

// On 401, try the refresh token once, then retry the original request.
// If refresh fails, drop tokens and send the user to /login.
let refreshPromise: Promise<string> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (AxiosRequestConfig & { _retried?: boolean }) | undefined;
    const status = error.response?.status;
    const url = original?.url ?? "";

    const isAuthEndpoint =
      url.includes("/auth/login/") ||
      url.includes("/auth/register/") ||
      url.includes("/auth/refresh/");

    if (status === 401 && original && !original._retried && !isAuthEndpoint) {
      original._retried = true;
      const refresh = getRefreshToken();
      if (!refresh) {
        clearTokens();
        window.location.assign("/login");
        return Promise.reject(error);
      }
      try {
        if (!refreshPromise) {
          refreshPromise = axios
            .post<{ access: string }>(`${API_BASE.replace(/\/$/, "")}/api/auth/refresh/`, {
              refresh,
            })
            .then((res) => {
              const access = res.data.access;
              localStorage.setItem(ACCESS_KEY, access);
              return access;
            })
            .finally(() => {
              refreshPromise = null;
            });
        }
        const access = await refreshPromise;
        original.headers = original.headers ?? {};
        (original.headers as Record<string, string>)["Authorization"] = `Bearer ${access}`;
        return api.request(original);
      } catch {
        clearTokens();
        window.location.assign("/login");
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  },
);

/** Extract a human-readable message from a DRF error payload. */
export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as unknown;
    if (typeof data === "string" && data.length > 0) return data;
    if (data && typeof data === "object") {
      const obj = data as Record<string, unknown>;
      for (const key of ["detail", "non_field_errors", "message"]) {
        const v = obj[key];
        if (typeof v === "string") return v;
        if (Array.isArray(v) && typeof v[0] === "string") return v[0];
      }
      const first = Object.values(obj)[0];
      if (typeof first === "string") return first;
      if (Array.isArray(first) && typeof first[0] === "string") return first[0];
    }
    if (error.message) return error.message;
  }
  return "Something went wrong. Please try again.";
}

// ---------------------------------------------------------------------------
// Typed API functions
// ---------------------------------------------------------------------------

export async function register(
  username: string,
  email: string,
  password: string,
): Promise<RegisterResponse> {
  const { data } = await api.post<RegisterResponse>("/auth/register/", {
    username,
    email,
    password,
  });
  return data;
}

export async function login(
  username: string,
  password: string,
): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>("/auth/login/", {
    username,
    password,
  });
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me/");
  return data;
}

export async function listCourses(
  params: CourseListParams = {},
): Promise<Paginated<CourseSummary>> {
  const { data } = await api.get<Paginated<CourseSummary>>("/courses/", {
    params,
  });
  return data;
}

export async function getCourse(slug: string): Promise<CourseDetail> {
  const { data } = await api.get<CourseDetail>(`/courses/${slug}/`);
  return data;
}

export async function enrollCourse(slug: string): Promise<EnrollResponse> {
  const { data } = await api.post<EnrollResponse>(`/courses/${slug}/enroll/`);
  return data;
}

export async function getLesson(id: number | string): Promise<LessonDetail> {
  const { data } = await api.get<LessonDetail>(`/lessons/${id}/`);
  return data;
}

export async function completeLesson(
  id: number | string,
): Promise<CompleteLessonResponse> {
  const { data } = await api.post<CompleteLessonResponse>(
    `/lessons/${id}/complete/`,
  );
  return data;
}

export async function getQuiz(courseSlug: string): Promise<Quiz> {
  const { data } = await api.get<Quiz>(`/courses/${courseSlug}/quiz/`);
  return data;
}

export async function submitQuiz(
  quizId: number | string,
  answers: Record<number, number>,
): Promise<QuizSubmitResponse> {
  const { data } = await api.post<QuizSubmitResponse>(
    `/quizzes/${quizId}/submit/`,
    { answers },
  );
  return data;
}

export async function getDashboard(): Promise<Dashboard> {
  const { data } = await api.get<Dashboard>("/dashboard/");
  return data;
}

export async function getRecommendations(): Promise<Recommendation[]> {
  const { data } = await api.get<Recommendation[]>("/recommendations/");
  return data;
}
