"""Deterministic recommendation engine (no ML dependencies).

Recommendations are derived from the learner's own data:

1. Weak topics — quiz answers are aggregated per topic_tag. Topics with
   at least 3 answered questions and accuracy below 70% trigger a
   recommendation for the first incomplete lesson tagged with that topic.
2. Continue learning — the first incomplete lesson of the most recently
   enrolled course.
3. Popular courses — published courses the user hasn't enrolled in,
   ordered by enrollment count.

The result is a capped, deterministically ordered list of dicts the API
serializes directly.
"""

from django.db.models import Count, Q

from learning.models import Course, Enrollment, Lesson, LessonProgress

MAX_RECOMMENDATIONS = 6
WEAK_TOPIC_MIN_ANSWERS = 3
WEAK_TOPIC_MAX_ACCURACY = 0.7


def _weak_topics(user):
    """Return [(topic_tag, accuracy)] for topics the user struggles with.

    Topics need at least WEAK_TOPIC_MIN_ANSWERS answered questions and
    accuracy below WEAK_TOPIC_MAX_ACCURACY. Ordered by accuracy ascending
    (weakest first) for deterministic output.
    """
    from learning.models import QuizAnswer

    rows = (
        QuizAnswer.objects.filter(attempt__user=user)
        .values("question__topic_tag")
        .annotate(
            total=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
        )
        .filter(total__gte=WEAK_TOPIC_MIN_ANSWERS)
    )
    weak = []
    for row in rows:
        accuracy = row["correct"] / row["total"]
        if accuracy < WEAK_TOPIC_MAX_ACCURACY:
            weak.append((row["question__topic_tag"], accuracy))
    weak.sort(key=lambda item: item[1])
    return weak


def _completed_lesson_ids(user):
    """Return the set of lesson ids the user has completed."""
    return set(
        LessonProgress.objects.filter(user=user).values_list(
            "lesson_id", flat=True
        )
    )


def _enrolled_course_ids(user):
    """Return the set of course ids the user is enrolled in."""
    return set(
        Enrollment.objects.filter(user=user).values_list(
            "course_id", flat=True
        )
    )


def _first_incomplete_lesson(user, course, completed_ids):
    """Return the first incomplete lesson of a course, or None."""
    return (
        Lesson.objects.filter(course=course)
        .exclude(id__in=completed_ids)
        .order_by("order")
        .first()
    )


def _lesson_payload(lesson, reason):
    """Serialize a lesson recommendation."""
    return {
        "kind": "lesson",
        "title": lesson.title,
        "reason": reason,
        "url": f"/lessons/{lesson.id}",
        "course_slug": lesson.course.slug,
        "lesson_id": lesson.id,
    }


def _course_payload(course, reason):
    """Serialize a course recommendation."""
    return {
        "kind": "course",
        "title": course.title,
        "reason": reason,
        "url": f"/courses/{course.slug}",
        "course_slug": course.slug,
        "lesson_id": None,
    }


def get_recommendations(user):
    """Build up to MAX_RECOMMENDATIONS recommendations for a user.

    Args:
        user: The learner to recommend content for.

    Returns:
        A list of dicts with keys: kind ('lesson'|'course'), title,
        reason, url, course_slug, lesson_id.
    """
    recommendations = []
    enrolled_ids = _enrolled_course_ids(user)
    completed_ids = _completed_lesson_ids(user)

    if not enrolled_ids:
        popular = (
            Course.objects.filter(is_published=True)
            .annotate(enrollment_count=Count("enrollments", distinct=True))
            .order_by("-enrollment_count", "title")[:3]
        )
        return [
            _course_payload(course, "Popular with learners")
            for course in popular
        ]

    enrolled_courses = (
        Course.objects.filter(id__in=enrolled_ids)
        .select_related()
        .order_by("title")
    )
    course_by_id = {course.id: course for course in enrolled_courses}

    # 1. Weak topics -> targeted lessons.
    # NOTE: topic tag matching is done in Python (not via a JSONField
    # `contains` lookup) so it works on both Postgres and SQLite.
    candidates = list(
        Lesson.objects.filter(course_id__in=enrolled_ids)
        .exclude(id__in=completed_ids)
        .select_related("course")
        .order_by("course__title", "order")
    )
    for tag, accuracy in _weak_topics(user):
        if len(recommendations) >= MAX_RECOMMENDATIONS:
            break
        lesson = next(
            (
                l
                for l in candidates
                if tag in (l.topic_tags or [])
                and all(r.get("lesson_id") != l.id for r in recommendations)
            ),
            None,
        )
        if lesson is not None:
            pct = round(accuracy * 100)
            recommendations.append(
                _lesson_payload(
                    lesson,
                    f"Your quiz accuracy on '{tag}' is {pct}% — "
                    "strengthen it with this lesson.",
                )
            )

    # 2. Continue learning: first incomplete lesson of the most recent
    # enrollment.
    recent_enrollment = (
        Enrollment.objects.filter(user=user)
        .select_related("course")
        .order_by("-enrolled_at")
        .first()
    )
    if recent_enrollment is not None and len(recommendations) < MAX_RECOMMENDATIONS:
        lesson = _first_incomplete_lesson(
            user, recent_enrollment.course, completed_ids
        )
        if lesson is not None and all(
            r.get("lesson_id") != lesson.id for r in recommendations
        ):
            recommendations.append(
                _lesson_payload(
                    lesson,
                    f"Pick up where you left off in "
                    f"'{recent_enrollment.course.title}'.",
                )
            )

    # 3. Popular courses the user hasn't enrolled in.
    if len(recommendations) < MAX_RECOMMENDATIONS:
        popular = (
            Course.objects.filter(is_published=True)
            .exclude(id__in=enrolled_ids)
            .annotate(enrollment_count=Count("enrollments", distinct=True))
            .order_by("-enrollment_count", "title")
        )
        for course in popular:
            if len(recommendations) >= MAX_RECOMMENDATIONS:
                break
            recommendations.append(
                _course_payload(course, "Popular with learners.")
            )

    return recommendations[:MAX_RECOMMENDATIONS]
