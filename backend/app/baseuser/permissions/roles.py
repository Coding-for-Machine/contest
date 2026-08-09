# baseuser/permissions/roles.py
"""
Foydalanuvchi rollari konstantalari va kategoriyalari.

MUHIM: Bu faylda Django model/admin import qilinmasligi shart!
Faqat Python primitive (str, list, tuple) ishlatilgan.
"""

# ============================================================
# 1. ASOSIY ROLLAR (DB Group nomlari — aniq shu ko'rinishda)
# ============================================================

DIRECTOR = "Direktor"                       # Barcha markazlar, to'liq CRUD
CENTER_ADMIN = "Markaz Boshlig'i"           # O'z markazi, barcha sohalar
ACADEMIC_MANAGER = "Akademik Menejer"       # Kurs kontenti
TEST_MANAGER = "Test Menejeri"              # Testlar
CONTEST_MANAGER = "Musobaqa Menejeri"       # Musobaqalar
PROBLEM_MANAGER = "Masala Menejeri"         # Masalalar
TEACHER = "O'qituvchi"                      # O'z kurslari (owner)
PROBLEM_AUTHOR = "Masala Muallifi"          # O'z masalalari (owner)
MODERATOR = "Moderator"                     # Hammasini faqat ko'rish


# ============================================================
# 2. ROL KATEGORIYALARI (Tekshirish va filtrlash uchun)
# ============================================================

# Faqat o'z ma'lumotlarini boshqaradi (owner maydoni tekshiriladi)
OWNER_ONLY_ROLES = (
    TEACHER,
    PROBLEM_AUTHOR,
)

# Faqat ko'rish (read-only)
READ_ONLY_ROLES = (
    MODERATOR,
)

# Markaz boshqaruvchilari (o'z markazining barcha ma'lumotlari)
CENTER_MANAGERS = (
    CENTER_ADMIN,
)

# Soha menejerlari (o'z sohasida to'liq CRUD)
FIELD_MANAGERS = (
    ACADEMIC_MANAGER,
    TEST_MANAGER,
    CONTEST_MANAGER,
    PROBLEM_MANAGER,
)

# Barcha markazlarni ko'rish huquqi (cross-center)
CROSS_CENTER_ROLES = (
    DIRECTOR,
)

# Admin panelga kirish huquqiga ega barcha rollar
STAFF_ROLES = (
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


# ============================================================
# 3. ADMIN BO'LIMLARI UCHUN RUXSAT ETILGAN ROLLAR
# ============================================================
# Har bir admin.py o'zining allowed_groups ro'yxatini shu yerdan olishi kerak

# Masalalar bo'limi (problems/admin.py)
PROBLEM_ADMIN_ROLES = (
    DIRECTOR,
    PROBLEM_MANAGER,
    CENTER_ADMIN,
    TEACHER,
    PROBLEM_AUTHOR,
    MODERATOR,
)

# Kurslar bo'limi (courses/admin.py)
COURSE_ADMIN_ROLES = (
    DIRECTOR,
    ACADEMIC_MANAGER,
    CENTER_ADMIN,
    TEACHER,
    MODERATOR,
)

# Testlar bo'limi (quizs/admin.py)
TEST_ADMIN_ROLES = (
    DIRECTOR,
    TEST_MANAGER,
    CENTER_ADMIN,
    MODERATOR,
)

# Musobaqalar bo'limi (contests/admin.py)
CONTEST_ADMIN_ROLES = (
    DIRECTOR,
    CONTEST_MANAGER,
    CENTER_ADMIN,
    MODERATOR,
)

# Video bo'limi (video/admin.py)
VIDEO_ADMIN_ROLES = (
    DIRECTOR,
    ACADEMIC_MANAGER,
    CENTER_ADMIN,
    TEACHER,
    MODERATOR,
)

# Markazlar bo'limi (centers/admin.py) — faqat eng yuqori daraja
CENTER_ADMIN_ROLES_ONLY = (
    DIRECTOR,
    CENTER_ADMIN,
)


# ============================================================
# 4. YORDAMCHI FUNKSIYALAR
# ============================================================

def is_owner_only(role_name: str) -> bool:
    """Faqat o'z ma'lumotlarini boshqaradigan rol-mi?"""
    return role_name in OWNER_ONLY_ROLES


def is_read_only(role_name: str) -> bool:
    """Faqat ko'rish ruxsatiga ega rol-mi?"""
    return role_name in READ_ONLY_ROLES


def is_center_manager(role_name: str) -> bool:
    """Markaz boshqaruvchisi-mi?"""
    return role_name in CENTER_MANAGERS


def is_field_manager(role_name: str) -> bool:
    """Soha menejerimi?"""
    return role_name in FIELD_MANAGERS


def is_cross_center(role_name: str) -> bool:
    """Barcha markazlarni ko'rish huquqiga ega rol-mi?"""
    return role_name in CROSS_CENTER_ROLES


def is_staff_role(role_name: str) -> bool:
    """Admin panelga kira oladigan rol-mi?"""
    return role_name in STAFF_ROLES


def get_all_roles() -> tuple:
    """Barcha rollar ro'yxatini qaytaradi (o'zgartirib bo'lmaydigan)."""
    return STAFF_ROLES


def get_role_display_name(role_key: str) -> str:
    """Rol constantidan ko'rsatiladigan nomni qaytaradi (agar kerak bo'lsa)."""
    mapping = {
        DIRECTOR: "Direktor",
        CENTER_ADMIN: "Markaz Boshlig'i",
        ACADEMIC_MANAGER: "Akademik Menejer",
        TEST_MANAGER: "Test Menejeri",
        CONTEST_MANAGER: "Musobaqa Menejeri",
        PROBLEM_MANAGER: "Masala Menejeri",
        TEACHER: "O'qituvchi",
        PROBLEM_AUTHOR: "Masala Muallifi",
        MODERATOR: "Moderator",
    }
    return mapping.get(role_key, role_key)