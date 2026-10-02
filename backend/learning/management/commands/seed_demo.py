"""Seed the database with demo courses, lessons, quizzes, and progress.

Creates 6 courses (5 lessons + 1 quiz each), a demo user (demo/learn1234)
enrolled in 3 courses with partial progress and mixed quiz scores, so the
dashboard and recommendations have something interesting to show.

Idempotent: does nothing if the demo courses already exist.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from learning.models import (
    Choice,
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Question,
    Quiz,
    QuizAnswer,
    QuizAttempt,
)

User = get_user_model()

# ---------------------------------------------------------------------------
# Demo content: (title, topic_tags, markdown body) per lesson and
# (text, topic_tag, choices, correct_index, explanation) per question.
# ---------------------------------------------------------------------------
COURSES = [
    {
        "title": "Python for Beginners",
        "slug": "python-basics",
        "description": (
            "Start from zero: variables, loops, functions, and enough "
            "Python to read real code with confidence."
        ),
        "category": "programming",
        "difficulty": "beginner",
        "lessons": [
            (
                "Setting Up Python",
                ["python-setup"],
                "## Setting Up Python\n\nInstall Python 3.12 from python.org "
                "and verify it with `python --version` in your terminal. "
                "You do not need an IDE yet — any text editor works.\n\n"
                "Create a folder for your exercises and run your first "
                "program with `python hello.py`. If you see your message "
                "printed, your environment is ready.",
            ),
            (
                "Variables and Types",
                ["python-basics"],
                "## Variables and Types\n\nVariables in Python need no "
                "declaration: `name = \"Ada\"` just works. The core types "
                "are `int`, `float`, `str`, `bool`, `list`, and `dict`.\n\n"
                "Use `type()` to inspect a value when you are unsure. "
                "Dynamic typing is flexible, but naming things clearly "
                "matters more than ever because of it.",
            ),
            (
                "Control Flow",
                ["python-basics"],
                "## Control Flow\n\n`if`, `elif`, and `else` branch on "
                "conditions. Indentation — not braces — defines blocks, so "
                "consistent 4-space indents are required.\n\n`for` loops "
                "iterate directly over collections, and `while` loops run "
                "until a condition flips. Prefer `for` when you know the "
                "collection up front.",
            ),
            (
                "Functions",
                ["python-functions"],
                "## Functions\n\nFunctions package reusable logic: "
                "`def greet(name):` defines one, `return` sends a value "
                "back. Parameters can have defaults, making call sites "
                "cleaner.\n\nKeep functions short and single-purpose. If a "
                "function needs a comment to explain *what* it does, "
                "consider splitting it.",
            ),
            (
                "Lists and Dictionaries",
                ["python-collections"],
                "## Lists and Dictionaries\n\nLists hold ordered items "
                "(`append`, slicing, comprehensions); dicts map keys to "
                "values and power most real-world Python programs.\n\n"
                "Learn dict `.get()` early — it avoids KeyError crashes "
                "when a key might be missing.",
            ),
        ],
        "quiz_title": "Python Basics Quiz",
        "questions": [
            (
                "Which keyword defines a function in Python?",
                "python-functions",
                ["func", "def", "define", "lambda-def"],
                1,
                "`def` starts a function definition; `lambda` is for "
                "anonymous one-liners.",
            ),
            (
                "What does `len([1, 2, 3])` return?",
                "python-collections",
                ["2", "3", "4", "TypeError"],
                1,
                "`len()` counts the items in the list: three.",
            ),
            (
                "How is a code block delimited in Python?",
                "python-basics",
                ["Braces {}", "Indentation", "Keywords", "Parentheses"],
                1,
                "Indentation defines blocks — consistent 4 spaces.",
            ),
            (
                "Which method safely reads a possibly-missing dict key?",
                "python-collections",
                ["d[key]", "d.fetch(key)", "d.get(key)", "d ?? key"],
                2,
                "`.get()` returns None (or a default) instead of raising.",
            ),
            (
                "What is the result of `bool(0)`?",
                "python-basics",
                ["True", "False", "0", "None"],
                1,
                "Zero is falsy in Python, so `bool(0)` is False.",
            ),
        ],
    },
    {
        "title": "Data Science with Pandas",
        "slug": "pandas-data-science",
        "description": (
            "Clean, reshape, and analyze tabular data with pandas — the "
            "workhorse of Python data science."
        ),
        "category": "data-science",
        "difficulty": "intermediate",
        "lessons": [
            (
                "Reading Data",
                ["pandas-io"],
                "## Reading Data\n\n`pd.read_csv()` turns a CSV into a "
                "DataFrame in one line. Always inspect with `.head()`, "
                "`.info()`, and `.describe()` before doing anything else.\n\n"
                "Watch for parsing traps: wrong separators, date columns "
                "read as strings, and silent NaNs.",
            ),
            (
                "Selecting and Filtering",
                ["pandas-filtering"],
                "## Selecting and Filtering\n\nUse `.loc` for label-based "
                "and `.iloc` for position-based selection. Boolean masks "
                "like `df[df.age > 30]` filter rows expressively.\n\n"
                "Chain carefully: `df[a][b]` can trigger "
                "SettingWithCopyWarning — prefer a single `.loc` call.",
            ),
            (
                "GroupBy Aggregations",
                ["pandas-groupby"],
                "## GroupBy Aggregations\n\n`df.groupby(\"city\").sales"
                ".mean()` splits rows into groups and aggregates each. "
                "This split-apply-combine pattern answers most reporting "
                "questions.\n\nMultiple aggregations go in `.agg({...})`. "
                "Remember the result is indexed by the group keys — call "
                "`.reset_index()` to flatten it.",
            ),
            (
                "Pivots and Reshaping",
                ["pandas-groupby"],
                "## Pivots and Reshaping\n\n`pivot_table()` is groupby in "
                "two dimensions: rows, columns, values, and an aggfunc. "
                "Use it for cross-tab style summaries.\n\n`melt()` does "
                "the reverse, turning wide tables long — the tidy shape "
                "most plotting libraries want.",
            ),
            (
                "Merging DataFrames",
                ["pandas-merge"],
                "## Merging DataFrames\n\n`pd.merge()` joins on shared "
                "keys like SQL: inner, left, right, outer. Validate with "
                "`validate=\"many_to_one\"` to catch unexpected "
                "duplicates.\n\nOverlapping non-key columns get `_x`/`_y` "
                "suffixes — rename them immediately for clarity.",
            ),
        ],
        "quiz_title": "Pandas Quiz",
        "questions": [
            (
                "Which method loads a CSV file into a DataFrame?",
                "pandas-io",
                ["pd.load_csv()", "pd.read_csv()", "pd.open_csv()", "pd.csv()"],
                1,
                "`pd.read_csv()` is the standard entry point.",
            ),
            (
                "What does `df.groupby('city').sales.mean()` return?",
                "pandas-groupby",
                [
                    "A filtered DataFrame",
                    "Mean sales per city",
                    "Total sales",
                    "A sorted DataFrame",
                ],
                1,
                "GroupBy splits by city and averages sales within each.",
            ),
            (
                "How do you flatten a groupby result's index?",
                "pandas-groupby",
                [".flatten()", ".reset_index()", ".unindex()", ".to_frame()"],
                1,
                "`.reset_index()` turns group keys back into columns.",
            ),
            (
                "Which join keeps all rows from the left DataFrame?",
                "pandas-merge",
                ["inner", "outer", "left", "cross"],
                2,
                "A left join keeps every left row, filling NaN on misses.",
            ),
            (
                "What does `pivot_table()` generalize?",
                "pandas-groupby",
                ["Sorting", "Two-dimensional groupby", "Merging", "Sampling"],
                1,
                "It aggregates over row × column groups at once.",
            ),
        ],
    },
    {
        "title": "Machine Learning Fundamentals",
        "slug": "ml-fundamentals",
        "description": (
            "Regression, classification, and validation — the core ideas "
            "behind every ML model, with scikit-learn."
        ),
        "category": "ai-ml",
        "difficulty": "intermediate",
        "lessons": [
            (
                "What Is Machine Learning?",
                ["ml-concepts"],
                "## What Is Machine Learning?\n\nML learns patterns from "
                "data instead of hand-written rules. Supervised learning "
                "maps inputs to labeled outputs; unsupervised learning "
                "finds structure without labels.\n\nEvery project follows "
                "the same loop: data → model → evaluation → iteration.",
            ),
            (
                "Train/Test Splits",
                ["ml-validation"],
                "## Train/Test Splits\n\nEvaluate on data the model never "
                "saw, or your metrics lie. `train_test_split` with a fixed "
                "`random_state` keeps experiments reproducible.\n\n"
                "Leakage — letting test information into training — is the "
                "most common beginner mistake.",
            ),
            (
                "Linear Regression",
                ["ml-regression"],
                "## Linear Regression\n\nFits a line minimizing squared "
                "error. It is simple, fast, and the right baseline for any "
                "regression task.\n\nCheck residuals: patterns in them mean "
                "the relationship is not linear.",
            ),
            (
                "Classification Metrics",
                ["ml-classification"],
                "## Classification Metrics\n\nAccuracy misleads on "
                "imbalanced data. Precision, recall, and F1 describe the "
                "trade-offs; ROC-AUC summarizes ranking quality.\n\n"
                "Always start from a confusion matrix before quoting a "
                "single number.",
            ),
            (
                "Overfitting and Regularization",
                ["ml-validation"],
                "## Overfitting and Regularization\n\nOverfitting memorizes "
                "noise; regularization (L1/L2) penalizes complexity. "
                "Cross-validation estimates true performance honestly.\n\n"
                "If train score >> validation score, simplify the model or "
                "get more data.",
            ),
        ],
        "quiz_title": "ML Fundamentals Quiz",
        "questions": [
            (
                "What is the main risk of evaluating on training data?",
                "ml-validation",
                [
                    "Slow training",
                    "Overly optimistic metrics",
                    "High memory use",
                    "None",
                ],
                1,
                "The model already saw the data, so scores are inflated.",
            ),
            (
                "Linear regression minimizes which loss?",
                "ml-regression",
                ["Hinge", "Cross-entropy", "Squared error", "Huber only"],
                2,
                "Ordinary least squares minimizes squared residuals.",
            ),
            (
                "Which metric suits imbalanced classification?",
                "ml-classification",
                ["Accuracy", "F1 score", "R²", "MSE"],
                1,
                "F1 balances precision and recall when classes skew.",
            ),
            (
                "What does L2 regularization penalize?",
                "ml-validation",
                [
                    "Large weights",
                    "Many features",
                    "Deep trees",
                    "Learning rate",
                ],
                0,
                "L2 shrinks weight magnitudes toward zero.",
            ),
            (
                "Supervised learning requires what?",
                "ml-concepts",
                ["Big data", "Labeled examples", "GPUs", "Streaming data"],
                1,
                "Labels provide the target the model learns to predict.",
            ),
        ],
    },
    {
        "title": "React from Scratch",
        "slug": "react-scratch",
        "description": (
            "Components, state, and effects — build interactive UIs with "
            "modern React and hooks."
        ),
        "category": "web-dev",
        "difficulty": "beginner",
        "lessons": [
            (
                "Thinking in Components",
                ["react-components"],
                "## Thinking in Components\n\nUIs are trees of components: "
                "small functions returning UI. Props flow down; events "
                "flow up.\n\nStart by sketching the component tree on "
                "paper before writing code.",
            ),
            (
                "State with useState",
                ["react-hooks"],
                "## State with useState\n\n`useState` gives a component "
                "memory: `const [count, setCount] = useState(0)`. Calling "
                "the setter re-renders with the new value.\n\nNever mutate "
                "state directly — always go through the setter.",
            ),
            (
                "Effects with useEffect",
                ["react-hooks"],
                "## Effects with useEffect\n\n`useEffect` syncs with the "
                "outside world: fetching, subscriptions, timers. The "
                "dependency array controls when it re-runs.\n\nReturn a "
                "cleanup function to avoid leaks on unmount.",
            ),
            (
                "Lists and Keys",
                ["react-components"],
                "## Lists and Keys\n\nRender lists with `.map()` and give "
                "each item a stable `key`. Keys let React match items "
                "across renders.\n\nNever use array index as key when the "
                "list can reorder.",
            ),
            (
                "Fetching Data",
                ["react-effects"],
                "## Fetching Data\n\nFetch in `useEffect`, track "
                "loading/error states, and cancel stale requests. "
                "Libraries like React Query remove most of this "
                "boilerplate.\n\nRender skeletons or spinners while "
                "waiting — never a blank page.",
            ),
        ],
        "quiz_title": "React Quiz",
        "questions": [
            (
                "How does data flow between components?",
                "react-components",
                [
                    "Props down, events up",
                    "Events down, props up",
                    "Both directions freely",
                    "Through the DOM",
                ],
                0,
                "Props flow down the tree; callbacks send events up.",
            ),
            (
                "What triggers a re-render?",
                "react-hooks",
                ["Mutating state", "Calling a state setter", "console.log", "Imports"],
                1,
                "Only the setter schedules a re-render with new state.",
            ),
            (
                "What controls when useEffect re-runs?",
                "react-hooks",
                ["The return value", "The dependency array", "Props only", "Nothing"],
                1,
                "Effects re-run when a dependency changes.",
            ),
            (
                "Why do list items need keys?",
                "react-components",
                [
                    "For CSS",
                    "To match items across renders",
                    "For SEO",
                    "They don't",
                ],
                1,
                "Keys let React reconcile list changes efficiently.",
            ),
            (
                "Where should data fetching happen?",
                "react-effects",
                ["In render", "In useEffect", "In the return", "In props"],
                1,
                "Effects are the sanctioned place for side effects.",
            ),
        ],
    },
    {
        "title": "Statistics for Programmers",
        "slug": "stats-programmers",
        "description": (
            "Distributions, hypothesis testing, and confidence intervals — "
            "the stats you actually use in engineering."
        ),
        "category": "math",
        "difficulty": "beginner",
        "lessons": [
            (
                "Mean, Median, Mode",
                ["stats-central-tendency"],
                "## Mean, Median, Mode\n\nThe mean is sensitive to "
                "outliers; the median resists them. Report both when data "
                "skews.\n\nThe mode matters most for categorical data.",
            ),
            (
                "Variance and Standard Deviation",
                ["stats-dispersion"],
                "## Variance and Standard Deviation\n\nSpread matters as "
                "much as center. Standard deviation is in the data's own "
                "units, making it interpretable.\n\nThe 68-95-99.7 rule "
                "gives quick intuition for normal-ish data.",
            ),
            (
                "The Normal Distribution",
                ["stats-distributions"],
                "## The Normal Distribution\n\nBell-shaped, defined by "
                "mean and sd. Many natural measurements approximate it, "
                "and the Central Limit Theorem explains why averages do.\n\n"
                "Always plot before assuming normality.",
            ),
            (
                "Hypothesis Testing",
                ["stats-testing"],
                "## Hypothesis Testing\n\nA p-value is P(data this "
                "extreme | H0), not P(H0 is false). Significance at 0.05 "
                "is a convention, not a law.\n\nPre-register hypotheses to "
                "avoid p-hacking.",
            ),
            (
                "Confidence Intervals",
                ["stats-testing"],
                "## Confidence Intervals\n\nA 95% CI is a range from a "
                "procedure that covers the truth 95% of the time. Wider "
                "intervals mean more uncertainty, not less confidence.\n\n"
                "Bigger n shrinks intervals — there is no free lunch.",
            ),
        ],
        "quiz_title": "Statistics Quiz",
        "questions": [
            (
                "Which measure resists outliers best?",
                "stats-central-tendency",
                ["Mean", "Median", "Sum", "Range"],
                1,
                "The median ignores extreme values.",
            ),
            (
                "Standard deviation is expressed in what units?",
                "stats-dispersion",
                ["Squared units", "The data's units", "Percent", "Z-scores"],
                1,
                "Taking the square root of variance restores units.",
            ),
            (
                "What does the Central Limit Theorem say about averages?",
                "stats-distributions",
                [
                    "They are always normal",
                    "They approach normality as n grows",
                    "They equal the median",
                    "They need no data",
                ],
                1,
                "Sample means converge to normal regardless of the source.",
            ),
            (
                "A p-value of 0.03 means what?",
                "stats-testing",
                [
                    "H0 is 3% likely",
                    "Such extreme data is 3% likely under H0",
                    "The effect is large",
                    "H1 is proven",
                ],
                1,
                "It conditions on H0 being true — a common misreading.",
            ),
            (
                "What shrinks a confidence interval?",
                "stats-testing",
                ["More data", "Higher confidence", "Outliers", "Nothing"],
                0,
                "Larger n reduces standard error and narrows the interval.",
            ),
        ],
    },
    {
        "title": "Deep Learning with PyTorch",
        "slug": "deep-learning-pytorch",
        "description": (
            "Tensors, autograd, and training loops — build neural networks "
            "with PyTorch."
        ),
        "category": "ai-ml",
        "difficulty": "advanced",
        "lessons": [
            (
                "Tensors",
                ["pytorch-tensors"],
                "## Tensors\n\nTensors are n-dimensional arrays with GPU "
                "support. `torch.tensor`, `.shape`, and broadcasting cover "
                "90% of daily use.\n\nKeep dtype and device consistent or "
                "operations will complain.",
            ),
            (
                "Autograd",
                ["pytorch-autograd"],
                "## Autograd\n\nPyTorch records operations on tensors with "
                "`requires_grad=True` into a graph; `.backward()` "
                "differentiates it.\n\nZero grads each step or they "
                "accumulate silently.",
            ),
            (
                "Building a Model",
                ["pytorch-modules"],
                "## Building a Model\n\nSubclass `nn.Module`, define "
                "layers in `__init__`, wire them in `forward`. "
                "`nn.Sequential` suffices for simple stacks.\n\nMove the "
                "model and the data to the same device.",
            ),
            (
                "The Training Loop",
                ["pytorch-training"],
                "## The Training Loop\n\nForward pass → loss → backward → "
                "optimizer step → zero grad. Loop over epochs and track "
                "both train and validation loss.\n\nDiverging validation "
                "loss means stop or regularize.",
            ),
            (
                "Saving and Loading",
                ["pytorch-training"],
                "## Saving and Loading\n\nSave `model.state_dict()`, not "
                "the whole model — it is portable across code changes. "
                "Use `map_location` when loading across devices.\n\n"
                "Version your checkpoints with the epoch and metric.",
            ),
        ],
        "quiz_title": "PyTorch Quiz",
        "questions": [
            (
                "What does `requires_grad=True` enable?",
                "pytorch-autograd",
                ["GPU use", "Gradient tracking", "Faster math", "Less memory"],
                1,
                "It tells autograd to record ops for differentiation.",
            ),
            (
                "Why call `optimizer.zero_grad()` each step?",
                "pytorch-training",
                [
                    "To save memory",
                    "Gradients accumulate otherwise",
                    "To shuffle data",
                    "It is optional",
                ],
                1,
                "PyTorch sums gradients into `.grad` unless cleared.",
            ),
            (
                "What should you save for portability?",
                "pytorch-training",
                ["The whole model", "state_dict()", "The optimizer", "The data"],
                1,
                "`state_dict()` survives refactors; pickled models do not.",
            ),
            (
                "Where is the network wired together?",
                "pytorch-modules",
                ["__init__", "forward", "backward", "state_dict"],
                1,
                "`forward` defines the computation graph.",
            ),
            (
                "What does broadcasting do?",
                "pytorch-tensors",
                [
                    "Streams video",
                    "Aligns mismatched shapes",
                    "Sends to GPU",
                    "Prints tensors",
                ],
                1,
                "Smaller tensors expand to match larger ones elementwise.",
            ),
        ],
    },
]


class Command(BaseCommand):
    """Seed demo content and demo-user progress."""

    help = "Create demo courses, lessons, quizzes, and demo user progress."

    def handle(self, *args, **options):
        if Course.objects.filter(slug="python-basics").exists():
            self.stdout.write("Demo content already exists — nothing to do.")
            return

        with transaction.atomic():
            for spec in COURSES:
                course = Course.objects.create(
                    title=spec["title"],
                    slug=spec["slug"],
                    description=spec["description"],
                    category=spec["category"],
                    difficulty=spec["difficulty"],
                    is_published=True,
                )
                for order, (title, tags, body) in enumerate(
                    spec["lessons"], start=1
                ):
                    Lesson.objects.create(
                        course=course,
                        title=title,
                        order=order,
                        content=body,
                        duration_minutes=10,
                        topic_tags=tags,
                    )
                quiz = Quiz.objects.create(
                    course=course,
                    title=spec["quiz_title"],
                    description=f"Check your understanding of {spec['title']}.",
                )
                for order, (
                    text,
                    tag,
                    choices,
                    correct_idx,
                    explanation,
                ) in enumerate(spec["questions"], start=1):
                    question = Question.objects.create(
                        quiz=quiz,
                        text=text,
                        order=order,
                        topic_tag=tag,
                        explanation=explanation,
                    )
                    for i, choice_text in enumerate(choices):
                        Choice.objects.create(
                            question=question,
                            text=choice_text,
                            is_correct=(i == correct_idx),
                        )

            self._seed_demo_progress()

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded 6 courses, 30 lessons, 6 quizzes, and demo progress "
                "(login: demo / learn1234)."
            )
        )

    def _seed_demo_progress(self):
        """Enroll the demo user with realistic partial progress."""
        user, _ = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@example.com"},
        )
        user.set_password("learn1234")
        user.save()

        by_slug = {c.slug: c for c in Course.objects.all()}

        def enroll(slug):
            enrollment, _ = Enrollment.objects.get_or_create(
                user=user, course=by_slug[slug]
            )
            return enrollment

        def complete(course_slug, orders):
            course = by_slug[course_slug]
            for order in orders:
                lesson = course.lessons.get(order=order)
                LessonProgress.objects.get_or_create(
                    user=user, lesson=lesson
                )

        def attempt(course_slug, correct_question_orders):
            """Record a quiz attempt with given questions answered correctly."""
            course = by_slug[course_slug]
            quiz = course.quiz
            questions = list(quiz.questions.order_by("order"))
            attempt = QuizAttempt.objects.create(
                user=user,
                quiz=quiz,
                score=0,
                total_questions=len(questions),
                correct_count=0,
            )
            correct = 0
            answers = []
            for i, question in enumerate(questions, start=1):
                want_correct = i in correct_question_orders
                choice = question.choices.filter(
                    is_correct=want_correct
                ).first()
                if want_correct:
                    correct += 1
                answers.append(
                    QuizAnswer(
                        attempt=attempt,
                        question=question,
                        selected_choice=choice,
                        is_correct=want_correct,
                    )
                )
            QuizAnswer.objects.bulk_create(answers)
            attempt.correct_count = correct
            attempt.score = round(100 * correct / len(questions), 1)
            attempt.save()

        # Course 1: 3/5 lessons done, quiz 4/5 (80%).
        enroll("python-basics")
        complete("python-basics", [1, 2, 3])
        attempt("python-basics", [1, 2, 3, 4])

        # Course 2: 2/5 lessons done, quiz 2/5 (40%) — weak on groupby
        # (questions 2, 3, 5 are groupby; 0/3 right -> 0%).
        enroll("pandas-data-science")
        complete("pandas-data-science", [1, 2])
        attempt("pandas-data-science", [1, 4])

        # Course 3: enrolled, quiz aced 5/5 (100%), no lessons completed.
        enroll("ml-fundamentals")
        attempt("ml-fundamentals", [1, 2, 3, 4, 5])
