# views/api.py — misol
from django.db import IntegrityError

async def complete_lecture(request, lecture_id: int):
    try:
        status, created = await LectureStatus.objects.aget_or_create(
            user=request.user, lecture_id=lecture_id
        )
    except IntegrityError:
        created = False
        status = await LectureStatus.objects.aget(user=request.user, lecture_id=lecture_id)

    return {"already_completed": not created, "xp": status.lecture.xp if created else 0}