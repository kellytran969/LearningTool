"""DRF serializers for the LearningTool API."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from learning.models import (
    Choice,
    Course,
    Enrollment,
    Lesson,
    Question,
    Quiz,
    QuizAttempt,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    """Public user representation."""

    class Meta:
        model = User
        fields = ("id", "username", "email")


class RegisterSerializer(serializers.ModelSerializer):
    """Validates registration input and creates the user."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
class CourseListSerializer(serializers.ModelSerializer):
    """Compact course card; counts come from queryset annotations."""

    lesson_count = serializers.IntegerField(read_only=True)
    enrollment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "slug",
            "title",
            "description",
            "category",
            "difficulty",
            "thumbnail_url",
            "lesson_count",
            "enrollment_count",
            "created_at",
        )


class LessonSummarySerializer(serializers.ModelSerializer):
    """Lesson entry inside a course detail payload."""

    class Meta:
        model = Lesson
        fields = (
            "id",
            "title",
            "order",
            "duration_minutes",
            "topic_tags",
        )


class CourseDetailSerializer(serializers.ModelSerializer):
    """Full course payload with its ordered lessons and quiz id."""

    lessons = LessonSummarySerializer(many=True, read_only=True)
    lesson_count = serializers.IntegerField(read_only=True)
    enrollment_count = serializers.IntegerField(read_only=True)
    quiz_id = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "slug",
            "title",
            "description",
            "category",
            "difficulty",
            "thumbnail_url",
            "lesson_count",
            "enrollment_count",
            "lessons",
            "quiz_id",
            "created_at",
        )

    def get_quiz_id(self, obj):
        quiz = getattr(obj, "quiz", None)
        return quiz.id if quiz is not None else None


class LessonSerializer(serializers.ModelSerializer):
    """Full lesson payload."""

    course_slug = serializers.SlugField(source="course.slug", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    course = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            "id",
            "title",
            "order",
            "content",
            "duration_minutes",
            "topic_tags",
            "course",
            "course_slug",
            "course_title",
        )

    def get_course(self, obj):
        return {"slug": obj.course.slug, "title": obj.course.title}


class EnrollmentSerializer(serializers.ModelSerializer):
    """Enrollment payload."""

    course_slug = serializers.SlugField(source="course.slug", read_only=True)

    class Meta:
        model = Enrollment
        fields = ("id", "course", "course_slug", "enrolled_at")
        read_only_fields = ("enrolled_at",)


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------
class ChoiceSerializer(serializers.ModelSerializer):
    """A choice as shown to learners (no correctness flag)."""

    class Meta:
        model = Choice
        fields = ("id", "text")


class QuestionSerializer(serializers.ModelSerializer):
    """A question with its choices (no correctness flags)."""

    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ("id", "text", "order", "topic_tag", "choices")


class QuizSerializer(serializers.ModelSerializer):
    """A quiz for taking: questions and choices, answers hidden."""

    questions = QuestionSerializer(many=True, read_only=True)
    course_slug = serializers.SlugField(source="course.slug", read_only=True)

    class Meta:
        model = Quiz
        fields = ("id", "title", "description", "course_slug", "questions")


class QuizSubmitSerializer(serializers.Serializer):
    """Validates a quiz submission payload."""

    answers = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="Map of question_id -> choice_id.",
    )


class QuizAttemptSerializer(serializers.ModelSerializer):
    """A graded quiz attempt."""

    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    course_slug = serializers.SlugField(
        source="quiz.course.slug", read_only=True
    )

    class Meta:
        model = QuizAttempt
        fields = (
            "id",
            "quiz",
            "quiz_title",
            "course_slug",
            "score",
            "total_questions",
            "correct_count",
            "submitted_at",
        )
