from django.shortcuts import get_object_or_404
from django.db.models import Prefetch # Buni import qilish shart
from ninja import Router
from ninja.errors import HttpError

from problems.models import Problem
from .models import Course, Enrilliment, Modul, Lesson
from baseuser.authenticate import JWTAuth

course_api = Router()

def get_authenticated_user(request):
    user = getattr(request, "auth", None)
    return user if (user and user is not True) else None

@course_api.get("/", auth=[JWTAuth(), lambda request: True])
def all_course_api(request):
    user = get_authenticated_user(request)
    
    # 1. N+1 YECHIMI: Kurslarni is_active bo'yicha filterlash
    courses_qs = Course.objects.filter(is_active=True)
    
    enrolled_ids = []
    if user:
        # Faqat kerakli ID'larni bitta so'rovda olamiz
        enrolled_ids = Enrilliment.objects.filter(user=user).values_list('course_id', flat=True)

    data = []
    for course in courses_qs:
        data.append({
            "id": course.id,
            "title": course.title,
            "slug": course.slug,
            "image": course.image.url if course.image else None,
            "is_enrolled": course.id in enrolled_ids,
            "price": course.price,
            "discount_price": course.discount_price,
        })
    return data

@course_api.get("/{slug}", auth=[JWTAuth(), lambda request: True])
def get_course_detail(request, slug: str):
    # 2. N+1 YECHIMI (ENG MUHIMI): 
    # Prefetch yordamida Modul va uning ichidagi Lesson'larni bitta (yoki ikkita) so'rovda yuklaymiz.
    # 'lesson' — bu sizning Lesson modelidagi related_name'ingiz.
    
    optimized_modullar = Prefetch(
        'modullar', 
        queryset=Modul.objects.order_by('order').prefetch_related(
            Prefetch('lesson', queryset=Lesson.objects.order_by('order'))
        )
    )

    course = get_object_or_404(
        Course.objects.prefetch_related(optimized_modullar), 
        slug=slug, 
        is_active=True
    )
    
    user = get_authenticated_user(request)
    is_enrolled = False
    if user:
        is_enrolled = Enrilliment.objects.filter(user=user, course=course).exists()

    modullar_data = []
    # Endi bu yerda .all() bazaga qayta so'rov yubormaydi, chunki prefetch qilingan!
    for modul in course.modullar.all():
        lessons_data = []
        for lesson in modul.lesson.all():
            lessons_data.append({
                "id": lesson.id,
                "title": lesson.title,
                "slug": lesson.slug,
                "is_locked": not is_enrolled 
            })
            
        modullar_data.append({
            "id": modul.id,
            "title": modul.title,
            "lessons": lessons_data
        })

    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "is_enrolled": is_enrolled,
        "price": course.price,
        "discount_price": course.discount_price,
        "content": modullar_data
    }



@course_api.get("/lesson/{lesson_slug}", auth=[JWTAuth(), lambda request: True])
def get_lesson_detail(request, lesson_slug: str):
    problem_with_videos = Prefetch(
        'problems', 
        queryset=Problem.objects.prefetch_related('problem_videos')
    )

    # 2. Lesson -> Problems -> Videos zanjiri
    lesson = get_object_or_404(
        Lesson.objects.select_related('modul__course').prefetch_related(
            problem_with_videos
        ),
        slug=lesson_slug
    )

    # A'zolikni tekshirish
    user = getattr(request, "auth", None)
    is_enrolled = False
    if user and user is not True:
        is_enrolled = Enrilliment.objects.filter(user=user, course=lesson.modul.course).exists()

    # if not is_enrolled:
    #     # 1-usul: HttpError orqali (Tavsiya etiladi)
    #     raise HttpError(403, "Ushbu darsni ko'rish uchun kursga a'zo bo'ling")

    # Ma'lumotlarni yig'ish
    problems_data = []
    for prob in lesson.problems.all():
        # Har bir masalaning birinchi videosini olamiz (agar bo'lsa)
        video_obj = prob.problem_videos.first() 
        
        problems_data.append({
            "id": prob.id,
            "title": prob.title,
            "description": prob.description,
            "video": {
                "hls": video_obj.hls_url if video_obj else None,
                "duration": video_obj.duration if video_obj else None,
            } if video_obj else None
        })

    return {
        "title": lesson.title,
        "course": lesson.modul.course.title,
        "problems": problems_data
    }

@course_api.get("/progress/{course_slug}")
def progress_course(request):
    return {}