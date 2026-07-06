from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from courses.models import Course, Modul, Lesson, Enrollment
from problems.models import Problem, Hint, Challenge, Function, ExecutionTestCase
from quizs.models import Test, Choice, Question, TestSession, UserResponse
from video.models import Video
from status.models import UserActivityDaily, UserStats
from contests.models import Contest


def assign(group, model_list, actions=None):
    """Guruhga faqat tanlangan modellar va actionlar bo'yicha huquq biriktiradi"""
    content_types = [ContentType.objects.get_for_model(m) for m in model_list]
    
    # Ham model turi, ham action bo'yicha to'g'ri filtrlash
    perms = Permission.objects.filter(content_type__in=content_types)

    if actions:
        q = Q()
        for action in actions:
            q |= Q(codename__startswith=f"{action}_")
        perms = perms.filter(q)

    # Mavjud huquqlarni o'chirib yubormaslik uchun .add() ishlatgan ma'qul
    group.permissions.add(*perms)
    print(f"  ✅ {group.name}: {perms.count()} ta huquq biriktirildi")


def create_groups(sender=None, **kwargs):
    """
    Barcha guruhlarni yaratadi va huquqlarini belgilaydi.
    """
    print("\nGuruhlar va huquqlarni sozlash boshlandi...")

    # Guruhlarni yaratish
    oqituvchi,   _ = Group.objects.get_or_create(name="O'qituvchi")
    muallif,     _ = Group.objects.get_or_create(name="Masala Muallifi")
    menejer,     _ = Group.objects.get_or_create(name="Kontent Menejer")
    moderator,   _ = Group.objects.get_or_create(name="Moderator")

    # Har safar migratsiyada dublikat bo'lmasligi uchun tozalab olish (ixtiyoriy)
    oqituvchi.permissions.clear()
    muallif.permissions.clear()
    menejer.permissions.clear()
    moderator.permissions.clear()

    # 1. O'QITUVCHI (To'liq huquq)
    oqituvchi_modellar = [Course, Modul, Lesson, Enrollment, Video, UserActivityDaily, UserStats]
    assign(oqituvchi, oqituvchi_modellar)

    # 2. MASALA MUALLIFI (To'liq huquq)
    muallif_modellar = [Problem, Hint, Challenge, Function, ExecutionTestCase, Contest]
    assign(muallif, muallif_modellar)

    # 3. KONTENT MENEJER 
    # Quiz — to'liq huquq
    quiz_modellar = [Test, Choice, Question, TestSession, UserResponse]
    assign(menejer, quiz_modellar, actions=['view', 'add', 'change', 'delete'])
    # Kurs — faqat ko'rish
    kurs_modellar = [Course, Modul, Lesson]
    assign(menejer, kurs_modellar, actions=['view'])

    # 4. MODERATOR (Faqat ko'rish)
    moderator_modellar = [
        Course, Modul, Lesson, Enrollment, Video,
        Problem, Hint, Challenge, Test, Question, 
        TestSession, Contest, UserActivityDaily, UserStats
    ]
    assign(moderator, moderator_modellar, actions=['view'])

    print("✅ Guruhlar muvaffaqiyatli yakunlandi!\n")


from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import BaseUser, Profile

# 1. Django Default User (Admin/Teacher) yaratilganda avtomatik profil ochish
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_save_django_user_profile(sender, instance, created, **kwargs):
    if created:
        # Yangi admin/o'qituvchi yaratilsa, faqat unga bog'langan profil ochiladi
        # save() metodidagi constraints bu yerda xavfsizlikni ta'minlaydi
        Profile.objects.create(django_user=instance)
    else:
        # Profil allaqachon bor bo'lsa, shunchaki profilni ham qayta saqlab qo'yamiz (ixtiyoriy)
        if hasattr(instance, 'profile'):
            instance.profile.save()

# 2. BaseUser (Talaba) yaratilganda avtomatik profil ochish
@receiver(post_save, sender=BaseUser)
def create_or_save_student_user_profile(sender, instance, created, **kwargs):
    if created:
        # Yangi talaba Telegramdan ro'yxatdan o'tsa, unga bog'langan profil ochiladi
        Profile.objects.create(student_user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
