# courses/signals/_base.py
"""
Barcha signallar uchun umumiy helper funksiyalar.
Bir xil query ni har joyda yozmaslik uchun.
"""
from courses.models import Course


def get_course_slug_by_id(course_id: int) -> str | None:
    """course_id → slug (1 query)"""
    return (
        Course.objects
        .filter(id=course_id)
        .values_list('slug', flat=True)
        .first()
    )


def get_course_data_by_modul(modul_id: int) -> dict | None:
    """modul_id → {id, slug} (1 query, JOIN yo'q)"""
    return (
        Course.objects
        .filter(modullar__id=modul_id)
        .values('id', 'slug')
        .first()
    )


def get_course_data_by_lesson(lesson_id: int) -> dict | None:
    """lesson_id → {id, slug, total_lessons_count, total_test_count} (1 query)"""
    return (
        Course.objects
        .filter(modullar__lessons__id=lesson_id)
        .values('id', 'slug', 'total_lessons_count', 'total_test_count')
        .first()
    )


def get_course_data_by_test_id(test_id: int) -> dict | None:
    """test_id → {id, slug, total_lessons_count, total_test_count} (1 query)"""
    return (
        Course.objects
        .filter(modullar__tests__id=test_id)
        .values('id', 'slug', 'total_lessons_count', 'total_test_count')
        .first()
    )