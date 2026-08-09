# courses/access.py
from django_bolt.exceptions import HTTPException
from courses.models import Course, Enrollment


async def ensure_course_access(user_id: int, course: Course) -> Enrollment:
    """
    Foydalanuvchi ushbu kurs kontentiga (dars/ma'ruza/quiz) kira olishini
    tekshiradi. Barcha content endpointlar (lesson, lecture, quiz) shu orqali
    tekshirilishi SHART.

    - Bepul kurs: Enrollment yo'q bo'lsa, avtomatik yaratiladi.
    - Pullik kurs: is_paid=True Enrollment bo'lmasa, 402 qaytaradi.
    """
    enrollment = await Enrollment.objects.filter(
        user_id=user_id, course_id=course.id
    ).only("id", "is_paid").afirst()

    if enrollment and enrollment.is_paid:
        return enrollment

    if course.current_price <= 0:
        if enrollment:
            return enrollment
        enrollment, _ = await Enrollment.objects.aget_or_create(
            user_id=user_id,
            course_id=course.id,
            defaults={"is_paid": True},
        )
        return enrollment

    # Pullik kurs va to'lanmagan — kirish taqiqlanadi
    raise HTTPException(
        402,
        f"Bu kursga kirish uchun to'lov talab qilinadi (amount={course.current_price})",
    )