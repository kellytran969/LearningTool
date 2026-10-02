import { Suspense, lazy } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Spinner from "./components/Spinner";
import Catalog from "./pages/Catalog";

// Code splitting: every page except the Catalog is lazy-loaded, so the
// initial bundle only contains what's needed for the first paint. Vite emits
// a separate chunk per lazy page, fetched on demand when the route renders.
const CourseDetail = lazy(() => import("./pages/CourseDetail"));
const LessonView = lazy(() => import("./pages/LessonView"));
const QuizView = lazy(() => import("./pages/QuizView"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));

function NotFound() {
  return (
    <div className="container page-center">
      <div className="empty-state">
        <h1>404</h1>
        <p className="muted">This page doesn't exist.</p>
        <Link to="/" className="btn btn-primary btn-sm">
          Back to courses
        </Link>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Navbar />
        <main className="main">
          <Suspense
            fallback={
              <div className="container page-center">
                <Spinner />
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<Catalog />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/courses/:slug" element={<CourseDetail />} />
              <Route
                path="/lessons/:id"
                element={
                  <ProtectedRoute>
                    <LessonView />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/courses/:slug/quiz"
                element={
                  <ProtectedRoute>
                    <QuizView />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </main>
        <footer className="footer">
          <div className="container">
            <p className="muted">
              LearningTool — an AI-based learning platform.
            </p>
          </div>
        </footer>
      </AuthProvider>
    </BrowserRouter>
  );
}
