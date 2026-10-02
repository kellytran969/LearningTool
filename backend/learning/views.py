"""API views for the LearningTool platform.

Read-heavy endpoints (course catalog, lesson detail, dashboard) are cached
in Redis with short TTLs; writes invalidate the affected keys via
learning/signals.py. Querysets use annotations and prefetching so no
endpoint issues N+1 queries.
"""

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from learning import cache_utils
from learning.models import (
    Choice,
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Quiz,
    QuizAnswer,
    QuizAttempt,
)
from learning.recommendations import get_recommendations
from learning.serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
    LessonSerializer,
    QuizAttemptSerializer,
    QuizSerializer,
    QuizSubmitSerializer,
    RegisterSerializer,
    UserSerializer,
)


def _dashboard_cache_key(user_id):
    """Return the cache key for a user's dashboard payload."""
    return cache_utils.cache_key("dashboard", user_id)


def bust_dashboard_cache(user_id):
    """Invalidate a user's cached dashboard (used after progress writes)."""
    cache_utils.delete_key(_dashboard_cache_key(user_id))


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
def _annotated_courses():
    """Courses annotated with lesson/enrollment counts for list views."""
    return Course.objects.filter(is_published=True).annotate(
        lesson_count=Count("lessons", distinct=True),
        enrollment_count=Count("enrollments", distinct=True),
    )


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """Course catalog: list (cached, filterable) and detail (cached)."""

    lookup_field = "slug"
    serializer_class = CourseListSerializer

    def get_queryset(self):
        queryset = _annotated_courses()
        ordering = self.request.query_params.get("ordering", "newest")
        if ordering == "popular":
            queryset = queryset.order_by("-enrollment_count", "title")
        elif ordering == "title":
            queryset = queryset.order_by("title")
        else:  # newest
            queryset = queryset.order_by("-created_at")
        return queryset

    def _filtered_queryset(self):
        """Apply category/difficulty/search filters to the queryset."""
        queryset = self.get_queryset()
        params = self.request.query_params
        category = params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        difficulty = params.get("difficulty")
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        return queryset

    def list(self, request, *args, **kwargs):
        """Paginated course list, cached per distinct query string."""
        params = sorted(request.query_params.items())
        key = cache_utils.cache_key("courses", "list", str(params))

        def _compute():
            queryset = self._filtered_queryset()
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data).data

        data = cache_utils.get_or_set(
            key, _compute, settings.COURSE_LIST_CACHE_TTL
        )
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        """Course detail with lessons, cached per slug."""
        slug = kwargs["slug"]
        key = cache_utils.cache_key("courses", "detail", slug)

        def _compute():
            course = get_object_or_404(
                _annotated_courses()
                .prefetch_related("lessons")
                .select_related("quiz"),
                slug=slug,
            )
            return CourseDetailSerializer(course).data

        return Response(
            cache_utils.get_or_set(
                key, _compute, settings.COURSE_DETAIL_CACHE_TTL
            )
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="enroll",
    )
    def enroll(self, request, slug=None):
        """Enroll the current user in a course (idempotent)."""
        course = get_object_or_404(Course, slug=slug, is_published=True)
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user, course=course
        )
        bust_dashboard_cache(request.user.id)
        total = Lesson.objects.filter(course=course).count()
        completed = LessonProgress.objects.filter(
            user=request.user, lesson__course=course
        ).count()
        progress_pct = round(100 * completed / total) if total else 0
        return Response(
            {
                "id": enrollment.id,
                "enrolled_at": enrollment.enrolled_at,
                "progress_pct": progress_pct,
                "course": {"slug": course.slug, "title": course.title},
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    """Lesson detail (authenticated) and completion tracking."""

    queryset = Lesson.objects.select_related("course").all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        """Lesson detail, cached per lesson id."""
        lesson_id = kwargs["pk"]
        key = cache_utils.cache_key("lessons", "detail", lesson_id)

        def _compute():
            lesson = get_object_or_404(
                Lesson.objects.select_related("course"), pk=lesson_id
            )
            return LessonSerializer(lesson).data

        return Response(
            cache_utils.get_or_set(
                key, _compute, settings.LESSON_DETAIL_CACHE_TTL
            )
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """Mark a lesson complete; requires enrollment in its course."""
        lesson = get_object_or_404(
            Lesson.objects.select_related("course"), pk=pk
        )
        enrolled = Enrollment.objects.filter(
            user=request.user, course=lesson.course
        ).exists()
        if not enrolled:
            return Response(
                {"detail": "Enroll in the course before completing lessons."},
                status=status.HTTP_403_FORBIDDEN,
            )
        LessonProgress.objects.get_or_create(
            user=request.user, lesson=lesson
        )
        bust_dashboard_cache(request.user.id)
        total = Lesson.objects.filter(course=lesson.course).count()
        completed = LessonProgress.objects.filter(
            user=request.user, lesson__course=lesson.course
        ).count()
        progress_pct = round(100 * completed / total) if total else 0
        return Response(
            {
                "completed": True,
                "progress_pct": progress_pct,
                "completed_lessons": completed,
                "total_lessons": total,
            }
        )


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------
class CourseQuizView(APIView):
    """Return a course's quiz with questions/choices (answers hidden)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug, is_published=True)
        quiz = (
            Quiz.objects.filter(course=course)
            .prefetch_related("questions__choices")
            .first()
        )
        if quiz is None:
            return Response(
                {"detail": "This course has no quiz yet."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(QuizSerializer(quiz).data)


class QuizSubmitView(APIView):
    """Grade a quiz submission and store the attempt."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        quiz = get_object_or_404(
            Quiz.objects.prefetch_related("questions__choices"), pk=pk
        )
        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_answers = serializer.validated_data["answers"]

        # Normalize keys to ints; ignore keys that aren't question ids.
        answers = {}
        for key, value in raw_answers.items():
            try:
                answers[int(key)] = value
            except (TypeError, ValueError):
                continue

        questions = list(quiz.questions.all())
        choice_by_id = {
            choice.id: choice
            for question in questions
            for choice in question.choices.all()
        }
        correct_choice_id = {
            question.id: next(
                (c.id for c in question.choices.all() if c.is_correct), None
            )
            for question in questions
        }

        results = []
        quiz_answers = []
        correct_count = 0
        for question in questions:
            selected_id = answers.get(question.id)
            selected = choice_by_id.get(selected_id)
            # A choice only counts if it belongs to this question.
            valid = selected is not None and any(
                c.id == selected.id for c in question.choices.all()
            )
            is_correct = valid and selected.id == correct_choice_id.get(
                question.id
            )
            if is_correct:
                correct_count += 1
            results.append(
                {
                    "question_id": question.id,
                    "selected_choice_id": selected.id if valid else None,
                    "correct_choice_id": correct_choice_id.get(question.id),
                    "is_correct": is_correct,
                    "explanation": question.explanation,
                }
            )
            quiz_answers.append(
                QuizAnswer(
                    question=question,
                    selected_choice=selected if valid else None,
                    is_correct=is_correct,
                )
            )

        total = len(questions)
        score = round(100 * correct_count / total, 1) if total else 0.0
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score=score,
            total_questions=total,
            correct_count=correct_count,
        )
        for quiz_answer in quiz_answers:
            quiz_answer.attempt = attempt
        QuizAnswer.objects.bulk_create(quiz_answers)
        bust_dashboard_cache(request.user.id)

        return Response(
            {
                "attempt_id": attempt.id,
                "score": score,
                "total_questions": total,
                "correct_count": correct_count,
                "passed": score >= 70,
                "results": results,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Dashboard & recommendations
# ---------------------------------------------------------------------------
class DashboardView(APIView):
    """Per-user learning dashboard, cached for 60 seconds."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        key = _dashboard_cache_key(request.user.id)

        def _compute():
            return self._build_dashboard(request.user)

        return Response(
            cache_utils.get_or_set(
                key, _compute, settings.DASHBOARD_CACHE_TTL
            )
        )

    def _build_dashboard(self, user):
        """Assemble the dashboard payload with annotated querysets."""
        enrollments = (
            Enrollment.objects.filter(user=user)
            .select_related("course")
            .annotate(
                total_lessons=Count("course__lessons", distinct=True),
                completed_lessons=Count(
                    "course__lessons__progress",
                    filter=Q(course__lessons__progress__user=user),
                    distinct=True,
                ),
            )
            .order_by("-enrolled_at")
        )

        enrolled_courses = []
        courses_completed = 0
        courses_enrolled = 0
        for enrollment in enrollments:
            courses_enrolled += 1
            total = enrollment.total_lessons
            completed = enrollment.completed_lessons
            pct = round(100 * completed / total) if total else 0
            if total and completed >= total:
                courses_completed += 1
            enrolled_courses.append(
                {
                    "course": {
                        "slug": enrollment.course.slug,
                        "title": enrollment.course.title,
                        "thumbnail_url": enrollment.course.thumbnail_url,
                        "category": enrollment.course.category,
                    },
                    "progress_pct": pct,
                    "completed_lessons": completed,
                    "total_lessons": total,
                    "enrolled_at": enrollment.enrolled_at,
                }
            )

        lessons_completed = LessonProgress.objects.filter(user=user).count()
        attempts = QuizAttempt.objects.filter(user=user)
        quizzes_taken = attempts.count()
        average_score = attempts.aggregate(avg=Avg("score"))["avg"]
        recent_attempts = QuizAttemptSerializer(
            attempts.select_related("quiz__course").order_by(
                "-submitted_at"
            )[:5],
            many=True,
        ).data

        return {
            "enrolled_courses": enrolled_courses,
            "stats": {
                "courses_enrolled": courses_enrolled,
                "courses_completed": courses_completed,
                "lessons_completed": lessons_completed,
                "quizzes_taken": quizzes_taken,
                "average_score": round(average_score, 1)
                if average_score is not None
                else None,
            },
            "recent_attempts": recent_attempts,
        }


class RecommendationsView(APIView):
    """Personalized lesson/course recommendations for the user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_recommendations(request.user))


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class RegisterView(APIView):
    """Create a user account and return JWT tokens."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """Return the current authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
