"""URL routes for the learning API (all under /api/)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from learning import views

router = DefaultRouter()
router.register(r"courses", views.CourseViewSet, basename="course")
router.register(r"lessons", views.LessonViewSet, basename="lesson")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "courses/<slug:slug>/quiz/",
        views.CourseQuizView.as_view(),
        name="course-quiz",
    ),
    path(
        "quizzes/<int:pk>/submit/",
        views.QuizSubmitView.as_view(),
        name="quiz-submit",
    ),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path(
        "recommendations/",
        views.RecommendationsView.as_view(),
        name="recommendations",
    ),
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", views.MeView.as_view(), name="me"),
]
