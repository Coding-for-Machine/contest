# baseuser/permissions/registry.py
# Har bir rol uchun modellar ro'yxati
# Funksiya ichida import -> AppRegistryNotReady xatosidan xalos


def get_center_admin_models():
    from courses.models import Course, Modul, Lesson, Lecture, Enrollment
    from video.models import Video
    from problems.models import (
        Problem, Hint, Challenge, Function,
        ExecutionTestCase, TestCase, Category, Tags, Language
    )
    from quizs.models import Test, Question, Choice, TestEnrollment
    from contests.models import Contest, ContestProblem, ContestPrize
    from centers.models import Center

    return [
        Course, Modul, Lesson, Lecture, Enrollment,
        Video,
        Problem, Hint, Challenge, Function, ExecutionTestCase, TestCase,
        Category, Tags, Language,
        Test, Question, Choice, TestEnrollment,
        Contest, ContestProblem, ContestPrize,
        Center,
    ]


def get_academic_models():
    from courses.models import Course, Modul, Lesson, Lecture, Enrollment
    from video.models import Video

    return [
        Course, Modul, Lesson, Lecture, Enrollment,
        Video,
    ]


def get_test_manager_models():
    from quizs.models import Test, Question, Choice, TestEnrollment

    return [
        Test, Question, Choice, TestEnrollment,
    ]


def get_test_view_models():
    from quizs.models import TestSession, UserResponse

    return [
        TestSession, UserResponse,
    ]


def get_contest_manager_models():
    from contests.models import Contest, ContestProblem, ContestPrize

    return [
        Contest, ContestProblem, ContestPrize,
    ]


def get_contest_view_models():
    from contests.models import ContestRegistration, ContestAnswer, CheatFlag

    return [
        ContestRegistration, ContestAnswer, CheatFlag,
    ]


def get_problem_manager_models():
    from problems.models import (
        Problem, Hint, Challenge, Function,
        ExecutionTestCase, TestCase, Category, Tags, Language
    )

    return [
        Problem, Hint, Challenge, Function, ExecutionTestCase, TestCase,
        Category, Tags, Language,
    ]


def get_teacher_models():
    from courses.models import Course, Modul, Lesson, Lecture, Enrollment
    from video.models import Video

    return [
        Course, Modul, Lesson, Lecture, Enrollment,
        Video,
    ]


def get_author_models():
    from problems.models import (
        Problem, Hint, Challenge, Function,
        ExecutionTestCase, TestCase
    )

    return [
        Problem, Hint, Challenge, Function, ExecutionTestCase, TestCase,
    ]


def get_moderator_models():
    from courses.models import Course, Modul, Lesson, Lecture, Enrollment
    from video.models import Video
    from problems.models import (
        Problem, Hint, Challenge, Function,
        ExecutionTestCase, TestCase, Category, Tags, Language
    )
    from quizs.models import (
        Test, Question, Choice, TestEnrollment,
        TestSession, UserResponse
    )
    from contests.models import (
        Contest, ContestProblem, ContestPrize,
        ContestRegistration, ContestAnswer, CheatFlag
    )
    from centers.models import Center

    return [
        Course, Modul, Lesson, Lecture, Enrollment,
        Video,
        Problem, Hint, Challenge, Function, ExecutionTestCase, TestCase,
        Category, Tags, Language,
        Test, Question, Choice, TestEnrollment,
        TestSession, UserResponse,
        Contest, ContestProblem, ContestPrize,
        ContestRegistration, ContestAnswer, CheatFlag,
        Center,
    ]