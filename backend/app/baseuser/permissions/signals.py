# baseuser/permissions/signals.py

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group

from .assign import assign
from .roles import (
    DIRECTOR,
    CENTER_ADMIN,
    ACADEMIC_MANAGER,
    TEST_MANAGER,
    CONTEST_MANAGER,
    PROBLEM_MANAGER,
    TEACHER,
    PROBLEM_AUTHOR,
    MODERATOR,
)
from .registry import (
    get_center_admin_models,
    get_academic_models,
    get_test_manager_models,
    get_test_view_models,
    get_contest_manager_models,
    get_contest_view_models,
    get_problem_manager_models,
    get_teacher_models,
    get_author_models,
    get_moderator_models,
)


def get_group(name):
    """Guruhni yaratadi, eski permissionlarni tozalaydi."""
    group, _ = Group.objects.get_or_create(name=name)
    group.permissions.clear()
    return group


@receiver(post_migrate)
def create_roles(sender, **kwargs):
    print("\n🚀 Role sozlash boshlandi...")

    # 1. Guruhlarni yaratish
    director = get_group(DIRECTOR)
    center_admin = get_group(CENTER_ADMIN)
    academic = get_group(ACADEMIC_MANAGER)
    test = get_group(TEST_MANAGER)
    contest = get_group(CONTEST_MANAGER)
    problem = get_group(PROBLEM_MANAGER)
    teacher = get_group(TEACHER)
    author = get_group(PROBLEM_AUTHOR)
    moderator = get_group(MODERATOR)

    # 2. Direktor - BARCHA markazlarning BARCHA modellari (superuser kabi)
    assign(director, get_moderator_models())  # moderator_models = barcha modellar

    # 3. Markaz Boshlig'i - BARCHA modellarga to'liq CRUD (faqat o'z markazi)
    assign(center_admin, get_center_admin_models())

    # 4. Akademik Menejer - Kurs bo'limi
    assign(academic, get_academic_models())

    # 5. Test Menejeri - Testlarga CRUD, natijalarga faqat VIEW
    assign(test, get_test_manager_models())
    assign(test, get_test_view_models(), actions=['view'])

    # 6. Musobaqa Menejeri - Contestlarga CRUD, natijalarga faqat VIEW
    assign(contest, get_contest_manager_models())
    assign(contest, get_contest_view_models(), actions=['view'])

    # 7. Masala Menejeri
    assign(problem, get_problem_manager_models())

    # 8. O'qituvchi - o'z yaratganiga CRU (DELETE yo'q)
    assign(teacher, get_teacher_models(), actions=['add', 'change', 'view'])

    # 9. Masala Muallifi - o'z yaratganiga CRU (DELETE yo'q)
    assign(author, get_author_models(), actions=['add', 'change', 'view'])

    # 10. Moderator - hammasini faqat ko'rish
    assign(moderator, get_moderator_models(), actions=['view'])

    print("✅ Role sozlash tugadi")