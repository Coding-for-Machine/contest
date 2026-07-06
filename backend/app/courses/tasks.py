import logging
from celery import shared_task
from django.apps import apps
from courses.cache import delete_course_list_static, delete_course_static, delete_lesson_static

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    name='courses.sync_all_counters',
)
def sync_all_counters_task(self, lesson_id: int | None = None, course_id: int | None = None) -> None:
    """
    Barcha counterlarni qayta hisoblaydi va jarayon yakunida keshni majburiy o'chiradi.
    """
    Lesson   = apps.get_model('courses',  'Lesson')
    Course   = apps.get_model('courses',  'Course')
    Problem  = apps.get_model('problems', 'Problem')
    Question = apps.get_model('quizs',    'Question')
    Lecture  = apps.get_model('courses',  'Lecture')
    Test     = apps.get_model('quizs',    'Test')

    try:
        # ── LESSON_ID berilgan bo'lsa ──────────────────────────────────────
        if lesson_id:
            lesson = Lesson.objects.filter(id=lesson_id).select_related('modul__course').first()
            if not lesson:
                logger.warning(f"sync_task: lesson_id={lesson_id} topilmadi.")
                return

            # 1. Lesson counterlarini hisoblash
            problems_count  = Problem.objects.filter(lesson_id=lesson_id, is_active=True).count()
            questions_count = Question.objects.filter(lesson_id=lesson_id).count()
            lectures_count  = Lecture.objects.filter(lesson_id=lesson_id).count()
            total_tasks     = problems_count + questions_count + lectures_count

            # Bazani yangilash
            Lesson.objects.filter(id=lesson_id).update(total_tasks_count=total_tasks)

            # ── [KESH] Dars keshini task ichida o'chirish ──
            if hasattr(lesson, 'slug') and lesson.slug:
                delete_lesson_static(lesson.slug)

            logger.info(f"Lesson id={lesson_id} counter yangilandi va keshi o'chirildi.")

            # Kurs ID sini aniqlab keyingi blokga uzatamiz
            course_id = lesson.modul.course_id if lesson.modul else None

        # ── COURSE_ID mavjud bo'lsa ────────────────────────────────────────
        if course_id:
            course = Course.objects.filter(id=course_id).first()
            if not course:
                logger.warning(f"sync_task: course_id={course_id} topilmadi.")
                return

            # 2. Kurs counterlarini hisoblash
            total_lessons = Lesson.objects.filter(modul__course_id=course_id).count()
            total_tests = Test.objects.filter(modul__course_id=course_id).count()

            # Bazani yangilash
            Course.objects.filter(id=course_id).update(
                total_lessons_count=total_lessons,
                total_test_count=total_tests,
            )

            # ── [KESH] Kurs va ro'yxat keshini task ichida o'chirish ──
            delete_course_list_static()
            if course.slug:
                delete_course_static(course.slug)

            logger.info(f"Course id={course_id} counterlari yangilandi va keshlar tozalandi.")

    except Exception as exc:
        logger.error(f"sync_all_counters_task XATO: {exc}", exc_info=True)
        raise self.retry(exc=exc)
