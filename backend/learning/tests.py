"""API tests for the LearningTool platform.

Covers auth, the cached course catalog, enrollment, lesson completion,
quiz grading, the recommendation engine, and dashboard math.
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from learning import cache_utils
from learning.models import (
    Choice,
    Course,
    Enrollment,
    Lesson,
    Question,
    Quiz,
)
from learning.recommendations import get_recommendations

User = get_user_model()


def make_user(username="learner", password="testpass123"):
    """Create a regular user."""
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=password,
    )


def make_course(
    slug="python-basics",
    n_lessons=3,
    with_quiz=True,
    title="Python Basics",
    category="programming",
    description="Learn Python from zero.",
):
    """Create a course with lessons and (optionally) a 2-question quiz."""
    course = Course.objects.create(
        title=title,
        slug=slug,
        description=description,
        category=category,
        difficulty="beginner",
        is_published=True,
    )
    lessons = [
        Lesson.objects.create(
            course=course,
            title=f"Lesson {i + 1}",
            order=i + 1,
            content="# Lesson\n\nSome content.",
            duration_minutes=10,
            topic_tags=["python-basics"],
        )
        for i in range(n_lessons)
    ]
    quiz = None
    if with_quiz:
        quiz = Quiz.objects.create(course=course, title="Python Quiz")
        for qi in range(2):
            question = Question.objects.create(
                quiz=quiz,
                text=f"Question {qi + 1}?",
                order=qi + 1,
                topic_tag="python-basics",
                explanation="Because it is.",
            )
            Choice.objects.create(
                question=question, text="Right", is_correct=True
            )
            Choice.objects.create(
                question=question, text="Wrong", is_correct=False
            )
    return course, lessons, quiz


def auth_client(testcase, user):
    """Authenticate the APITestCase client as user via JWT."""
    resp = testcase.client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "testpass123"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK, resp.data
    testcase.client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}"
    )


class AuthTests(APITestCase):
    """Registration, login, and the /me endpoint."""

    def test_register_returns_tokens(self):
        resp = self.client.post(
            "/api/auth/register/",
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "strongpass1",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["username"], "newuser")

    def test_register_duplicate_username_fails(self):
        make_user("taken")
        resp = self.client.post(
            "/api/auth/register/",
            {
                "username": "taken",
                "email": "other@example.com",
                "password": "strongpass1",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_and_me(self):
        make_user("learner")
        resp = self.client.post(
            "/api/auth/login/",
            {"username": "learner", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)

        # /me requires auth
        self.client.credentials()  # clear
        resp = self.client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

        user = User.objects.get(username="learner")
        auth_client(self, user)
        resp = self.client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "learner")


class CatalogTests(APITestCase):
    """Course list/detail, filters, and Redis caching."""

    def setUp(self):
        cache.clear()
        self.course, self.lessons, self.quiz = make_course()

    def list_cache_key(self, params=()):
        return cache_utils.cache_key("courses", "list", str(sorted(params)))

    def test_list_includes_counts(self):
        resp = self.client.get("/api/courses/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        row = resp.data["results"][0]
        self.assertEqual(row["slug"], "python-basics")
        self.assertEqual(row["lesson_count"], 3)
        self.assertEqual(row["enrollment_count"], 0)

    def test_list_is_cached(self):
        key = self.list_cache_key()
        self.assertIsNone(cache.get(key))
        first = self.client.get("/api/courses/")
        self.assertIsNotNone(cache.get(key))
        second = self.client.get("/api/courses/")
        self.assertEqual(first.data, second.data)

    def test_list_cache_busted_on_course_save(self):
        key = self.list_cache_key()
        self.client.get("/api/courses/")
        self.assertIsNotNone(cache.get(key))
        Course.objects.create(
            title="Math 101",
            slug="math-101",
            description="Numbers.",
            category="math",
            difficulty="beginner",
            is_published=True,
        )
        # The save signal clears catalog keys (locmem fallback clears all).
        self.assertIsNone(cache.get(key))
        resp = self.client.get("/api/courses/")
        self.assertEqual(resp.data["count"], 2)

    def test_filter_search_ordering(self):
        make_course(
            slug="math-101",
            n_lessons=1,
            with_quiz=False,
            title="Math 101",
            category="math",
            description="Numbers and proofs.",
        )

        resp = self.client.get("/api/courses/", {"category": "math"})
        self.assertEqual(resp.data["count"], 1)

        resp = self.client.get("/api/courses/", {"search": "python"})
        self.assertEqual(resp.data["count"], 1)

        resp = self.client.get("/api/courses/", {"difficulty": "advanced"})
        self.assertEqual(resp.data["count"], 0)

    def test_detail_includes_lessons_and_quiz(self):
        key = cache_utils.cache_key("courses", "detail", "python-basics")
        resp = self.client.get("/api/courses/python-basics/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["lessons"]), 3)
        self.assertEqual(resp.data["quiz_id"], self.quiz.id)
        self.assertIsNotNone(cache.get(key))

    def test_detail_404_for_unknown_slug(self):
        resp = self.client.get("/api/courses/nope/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class EnrollmentTests(APITestCase):
    """Enrolling and completing lessons."""

    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.course, self.lessons, self.quiz = make_course()
        auth_client(self, self.user)

    def test_enroll_is_idempotent(self):
        url = "/api/courses/python-basics/enroll/"
        first = self.client.post(url)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data["course"]["slug"], "python-basics")
        self.assertEqual(first.data["progress_pct"], 0)

        second = self.client.post(url)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Enrollment.objects.filter(
                user=self.user, course=self.course
            ).count(),
            1,
        )

    def test_enroll_requires_auth(self):
        self.client.credentials()  # clear
        resp = self.client.post("/api/courses/python-basics/enroll/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_complete_requires_enrollment(self):
        resp = self.client.post(
            f"/api/lessons/{self.lessons[0].id}/complete/"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_complete_marks_progress(self):
        self.client.post("/api/courses/python-basics/enroll/")
        resp = self.client.post(
            f"/api/lessons/{self.lessons[0].id}/complete/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["completed"])
        # 1 of 3 lessons -> 33%.
        self.assertEqual(resp.data["progress_pct"], 33)
        self.assertEqual(resp.data["completed_lessons"], 1)

    def test_lesson_detail_shape(self):
        resp = self.client.get(f"/api/lessons/{self.lessons[0].id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["course"]["slug"], "python-basics")
        self.assertIn("content", resp.data)


class QuizTests(APITestCase):
    """Quiz fetching (answers hidden) and grading."""

    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.course, self.lessons, self.quiz = make_course()
        auth_client(self, self.user)
        self.questions = list(self.quiz.questions.all())

    def _answers(self, correct_mask):
        payload = {}
        for question, want_correct in zip(self.questions, correct_mask):
            choice = question.choices.get(is_correct=want_correct)
            payload[str(question.id)] = choice.id
        return payload

    def test_quiz_hides_correct_flags(self):
        resp = self.client.get("/api/courses/python-basics/quiz/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for question in resp.data["questions"]:
            for choice in question["choices"]:
                self.assertNotIn("is_correct", choice)

    def test_submit_all_correct(self):
        resp = self.client.post(
            f"/api/quizzes/{self.quiz.id}/submit/",
            {"answers": self._answers([True, True])},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["score"], 100.0)
        self.assertEqual(resp.data["correct_count"], 2)
        self.assertTrue(resp.data["passed"])
        for item in resp.data["results"]:
            self.assertTrue(item["is_correct"])
            self.assertEqual(
                item["selected_choice_id"], item["correct_choice_id"]
            )
            self.assertTrue(item["explanation"])

    def test_submit_partial_score(self):
        resp = self.client.post(
            f"/api/quizzes/{self.quiz.id}/submit/",
            {"answers": self._answers([True, False])},
            format="json",
        )
        self.assertEqual(resp.data["score"], 50.0)
        self.assertEqual(resp.data["correct_count"], 1)
        self.assertFalse(resp.data["passed"])

    def test_submit_ignores_foreign_choice(self):
        # A choice from question 1 submitted for question 2 is invalid.
        q1, q2 = self.questions
        foreign = q1.choices.get(is_correct=True)
        payload = {
            str(q1.id): q1.choices.get(is_correct=True).id,
            str(q2.id): foreign.id,
        }
        resp = self.client.post(
            f"/api/quizzes/{self.quiz.id}/submit/",
            {"answers": payload},
            format="json",
        )
        self.assertEqual(resp.data["correct_count"], 1)
        by_q = {r["question_id"]: r for r in resp.data["results"]}
        self.assertIsNone(by_q[q2.id]["selected_choice_id"])
        self.assertFalse(by_q[q2.id]["is_correct"])

    def test_quiz_404_when_missing(self):
        make_course(slug="no-quiz", with_quiz=False)
        resp = self.client.get("/api/courses/no-quiz/quiz/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class RecommendationTests(APITestCase):
    """Weak-topic and popular-course recommendations."""

    def setUp(self):
        cache.clear()
        self.user = make_user()
        auth_client(self, self.user)

    def _course_with_tagged_quiz(self):
        course = Course.objects.create(
            title="Pandas Deep Dive",
            slug="pandas-deep-dive",
            description="Pandas.",
            category="data-science",
            difficulty="intermediate",
            is_published=True,
        )
        lessons = [
            Lesson.objects.create(
                course=course,
                title=f"Lesson {i + 1}",
                order=i + 1,
                content="Content.",
                topic_tags=["pandas-groupby"] if i >= 2 else ["pandas-io"],
            )
            for i in range(4)
        ]
        quiz = Quiz.objects.create(course=course, title="Pandas Quiz")
        questions = []
        for qi in range(4):
            question = Question.objects.create(
                quiz=quiz,
                text=f"Q{qi}?",
                order=qi + 1,
                topic_tag="pandas-groupby",
                explanation="Groupby groups.",
            )
            Choice.objects.create(
                question=question, text="Right", is_correct=True
            )
            Choice.objects.create(
                question=question, text="Wrong", is_correct=False
            )
            questions.append(question)
        return course, lessons, quiz, questions

    def test_weak_topic_recommends_lesson(self):
        course, lessons, quiz, questions = self._course_with_tagged_quiz()
        self.client.post(f"/api/courses/{course.slug}/enroll/")
        # Complete the first two lessons; answer 1/4 groupby correctly.
        for lesson in lessons[:2]:
            self.client.post(f"/api/lessons/{lesson.id}/complete/")
        answers = {}
        for i, question in enumerate(questions):
            want = i == 0  # only the first correct -> 25% accuracy
            answers[str(question.id)] = question.choices.get(
                is_correct=want
            ).id
        self.client.post(
            f"/api/quizzes/{quiz.id}/submit/",
            {"answers": answers},
            format="json",
        )

        recs = get_recommendations(self.user)
        kinds = [r["kind"] for r in recs]
        self.assertIn("lesson", kinds)
        weak = [r for r in recs if "pandas-groupby" in r["reason"]]
        self.assertTrue(weak)
        # The recommended lesson must be incomplete and tagged.
        self.assertEqual(weak[0]["lesson_id"], lessons[2].id)

        # Same via the API as a bare list.
        resp = self.client.get("/api/recommendations/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)
        self.assertTrue(any("pandas-groupby" in r["reason"] for r in resp.data))

    def test_no_enrollments_returns_popular_courses(self):
        make_course(slug="c1")
        make_course(slug="c2")
        fresh = make_user("fresh")
        auth_client(self, fresh)
        resp = self.client.get("/api/recommendations/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(all(r["kind"] == "course" for r in resp.data))
        self.assertLessEqual(len(resp.data), 3)


class DashboardTests(APITestCase):
    """Dashboard payload math and caching."""

    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.course, self.lessons, self.quiz = make_course(n_lessons=4)
        auth_client(self, self.user)

    def test_dashboard_math(self):
        self.client.post("/api/courses/python-basics/enroll/")
        self.client.post(f"/api/lessons/{self.lessons[0].id}/complete/")
        questions = list(self.quiz.questions.all())
        answers = {
            str(q.id): q.choices.get(is_correct=True).id for q in questions
        }
        self.client.post(
            f"/api/quizzes/{self.quiz.id}/submit/",
            {"answers": answers},
            format="json",
        )

        resp = self.client.get("/api/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        enrolled = resp.data["enrolled_courses"]
        self.assertEqual(len(enrolled), 1)
        self.assertEqual(enrolled[0]["progress_pct"], 25)  # 1 of 4
        self.assertEqual(enrolled[0]["completed_lessons"], 1)
        self.assertEqual(enrolled[0]["total_lessons"], 4)

        stats = resp.data["stats"]
        self.assertEqual(stats["courses_enrolled"], 1)
        self.assertEqual(stats["courses_completed"], 0)
        self.assertEqual(stats["lessons_completed"], 1)
        self.assertEqual(stats["quizzes_taken"], 1)
        self.assertEqual(stats["average_score"], 100.0)
        self.assertEqual(len(resp.data["recent_attempts"]), 1)
        self.assertEqual(
            resp.data["recent_attempts"][0]["course_slug"], "python-basics"
        )

    def test_dashboard_is_cached_per_user(self):
        key = cache_utils.cache_key("dashboard", self.user.id)
        self.assertIsNone(cache.get(key))
        self.client.get("/api/dashboard/")
        self.assertIsNotNone(cache.get(key))

    def test_dashboard_cache_busted_on_progress(self):
        key = cache_utils.cache_key("dashboard", self.user.id)
        self.client.post("/api/courses/python-basics/enroll/")
        self.client.get("/api/dashboard/")
        self.assertIsNotNone(cache.get(key))
        self.client.post(f"/api/lessons/{self.lessons[0].id}/complete/")
        self.assertIsNone(cache.get(key))

    def test_dashboard_requires_auth(self):
        self.client.credentials()  # clear
        resp = self.client.get("/api/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
