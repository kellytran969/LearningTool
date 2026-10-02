"""Database models for the LearningTool platform.

Courses contain ordered lessons and one quiz. Users enroll in courses,
complete lessons, and submit quiz attempts. Indexes are placed on the
columns the API filters/sorts on (slug, category, topic_tag, ordering
pairs) so catalog and dashboard queries stay fast at scale.
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Course(models.Model):
    """A published learning course (e.g. 'Python for Beginners')."""

    CATEGORY_CHOICES = [
        ("programming", "Programming"),
        ("data-science", "Data Science"),
        ("ai-ml", "AI / Machine Learning"),
        ("web-dev", "Web Development"),
        ("math", "Math"),
    ]
    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=32, choices=CATEGORY_CHOICES, db_index=True
    )
    difficulty = models.CharField(
        max_length=16, choices=DIFFICULTY_CHOICES, default="beginner"
    )
    thumbnail_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Lesson(models.Model):
    """An ordered lesson inside a course; content is Markdown."""

    course = models.ForeignKey(
        Course, related_name="lessons", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField()
    content = models.TextField()
    duration_minutes = models.PositiveIntegerField(default=10)
    topic_tags = models.JSONField(default=list)

    class Meta:
        ordering = ["order"]
        unique_together = ("course", "order")
        indexes = [models.Index(fields=["course", "order"])]

    def __str__(self):
        return f"{self.course.title} — {self.order}. {self.title}"


class Quiz(models.Model):
    """One quiz per course, covering its lessons."""

    course = models.OneToOneField(
        Course, related_name="quiz", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    """A multiple-choice question; topic_tag powers weak-topic analysis."""

    quiz = models.ForeignKey(
        Quiz, related_name="questions", on_delete=models.CASCADE
    )
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    topic_tag = models.CharField(max_length=50, db_index=True)
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"


class Choice(models.Model):
    """One answer option for a question; exactly one should be correct."""

    question = models.ForeignKey(
        Question, related_name="choices", on_delete=models.CASCADE
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:60]


class Enrollment(models.Model):
    """A user enrolled in a course."""

    user = models.ForeignKey(
        User, related_name="enrollments", on_delete=models.CASCADE
    )
    course = models.ForeignKey(
        Course, related_name="enrollments", on_delete=models.CASCADE
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "course")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.user.username} → {self.course.title}"


class LessonProgress(models.Model):
    """Marks a lesson completed by a user."""

    user = models.ForeignKey(
        User, related_name="lesson_progress", on_delete=models.CASCADE
    )
    lesson = models.ForeignKey(
        Lesson, related_name="progress", on_delete=models.CASCADE
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "lesson")

    def __str__(self):
        return f"{self.user.username} completed {self.lesson}"


class QuizAttempt(models.Model):
    """One graded submission of a quiz."""

    user = models.ForeignKey(
        User, related_name="quiz_attempts", on_delete=models.CASCADE
    )
    quiz = models.ForeignKey(
        Quiz, related_name="attempts", on_delete=models.CASCADE
    )
    score = models.FloatField(help_text="0–100")
    total_questions = models.PositiveIntegerField()
    correct_count = models.PositiveIntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [models.Index(fields=["user", "quiz"])]

    def __str__(self):
        return f"{self.user.username}: {self.quiz.title} = {self.score:.0f}"


class QuizAnswer(models.Model):
    """A single answered question inside a quiz attempt."""

    attempt = models.ForeignKey(
        QuizAttempt, related_name="answers", on_delete=models.CASCADE
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(
        Choice, null=True, blank=True, on_delete=models.SET_NULL
    )
    is_correct = models.BooleanField(default=False)
