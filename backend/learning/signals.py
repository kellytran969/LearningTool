"""Cache invalidation signals.

Catalog content (courses, lessons, quizzes) is cached aggressively, so
any write to it busts the 'courses:*' keyspace. Per-user dashboard data
is cached per user id and busted when that user enrolls, completes a
lesson, or submits a quiz.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from learning import cache_utils
from learning.models import (
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Question,
    Quiz,
    QuizAttempt,
)


def _bust_catalog_cache(sender, **kwargs):
    """Invalidate cached catalog responses after a content write."""
    cache_utils.safe_delete_pattern("learningtool:courses:*")


for _model in (Course, Lesson, Quiz, Question):
    post_save.connect(_bust_catalog_cache, sender=_model)
    post_delete.connect(_bust_catalog_cache, sender=_model)


def _bust_dashboard_cache(user_id):
    """Invalidate one user's cached dashboard."""
    cache_utils.delete_key(cache_utils.cache_key("dashboard", user_id))


@receiver(post_save, sender=Enrollment)
def _enrollment_saved(sender, instance, **kwargs):
    _bust_dashboard_cache(instance.user_id)


@receiver(post_save, sender=LessonProgress)
def _progress_saved(sender, instance, **kwargs):
    _bust_dashboard_cache(instance.user_id)


@receiver(post_save, sender=QuizAttempt)
def _attempt_saved(sender, instance, **kwargs):
    _bust_dashboard_cache(instance.user_id)
