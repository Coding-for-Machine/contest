from django_bolt.serializers import Serializer, computed_field


# ─────────────────────────────────────────
# LESSON
# ─────────────────────────────────────────
class LessonList(Serializer):
    t: str
    s: str
    total_tasks_count: int
    finished_tasks: int = 0
    is_completed: bool = False
    completed_at: int = 0


# ─────────────────────────────────────────
# TEST
# ─────────────────────────────────────────
class TestList(Serializer):
    t: str
    s: str
    duration: int
    q_count: int
    is_available: bool
    best_score: float = 0.0
    attempts: int = 0
    is_passed: bool = False
    correct_count: int = 0
    wrong_count: int = 0
    last_completed_at: int = 0


# ─────────────────────────────────────────
# MODUL
# ─────────────────────────────────────────
class ModulList(Serializer):
    t: str
    s: str
    lesson: list[LessonList] = []
    tests: list[TestList] = []


# ─────────────────────────────────────────
# COURSE
# ─────────────────────────────────────────
class CourseSerializer(Serializer):
    id: int
    t: str
    d: str | None
    s: str
    price: float
    discount_price: float | None

    is_purchased: bool = False
    is_paid: bool = False
    is_completed: bool = False
    completed_at: int = 0

    total_lessons: int = 0
    finished_lessons: int = 0
    
    total_tests: int = 0
    finished_tests: int = 0


class CourseModuleLesson(CourseSerializer):
    modul: list[ModulList] = []

    class Config:
        field_sets = {
            # Ro'yxat — minimal ma'lumot
            "list": [
                "id", "t", "s",
                "price", "discount_price",
                "is_purchased", "is_paid",
                "lesson_percentage", "test_percentage",
            ],
            # Detail — to'liq ma'lumot, modulsiz
            "detail": [
                "id", "t", "d", "s",
                "price", "discount_price",
                "is_purchased", "is_paid",
                "is_completed", "completed_at",
                "total_lessons", "finished_lessons",
                "total_tests", "finished_tests",
            ],
            # Modullar — to'liq + modul/dars/test
            "modules": [
                "id", "t", "d", "s",
                "price", "discount_price",
                "is_purchased", "is_paid",
                "is_completed", "completed_at",
                "total_lessons", "finished_lessons",
                "total_tests", "finished_tests",
                "modul",
            ],
        }


CourseListSerializer    = CourseModuleLesson.fields("list")
CourseDetailSerializer  = CourseModuleLesson.fields("detail")
CourseModulesSerializer = CourseModuleLesson.fields("modules")