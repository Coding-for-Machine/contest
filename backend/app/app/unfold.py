from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from .settings import DEBUG

def environment_callback(request):
    """Sidebar yuqorisida muhit (dev/prod) belgisini ko'rsatadi."""
    if DEBUG:
        return ["DEVELOPMENT", "warning"]
    return ["PRODUCTION", "success"]


def unfold():
    return {
        "SITE_TITLE": "CfM Contest",
        "SITE_HEADER": "CfM Contest",
        "SITE_SUBHEADER": "Boshqaruv paneli",
        "SITE_URL": "/",
        "SHOW_HISTORY": True,
        "SHOW_VIEW_ON_SITE": True,
        "SHOW_LANGUAGES": False,
        
        
        # 2. DASHBOARD CALLBACK (Statistika paneli ulanishi)
        "DASHBOARD_CALLBACK": "app.dashboard.get_dashboard_context",
        
        "ENVIRONMENT": "app.unfold.environment_callback",
        
        # 3. LOGIN OUT (Kirish oynasi konfiguratsiyasi)
        "LOGIN": {
            "image": lambda request: static("img/login-bg.jpg"),
            "title": "Xush kelibsiz",
            "description": "Hisobingizga kiring va bilimingizni sinab ko'ring",
            "redirect_after": lambda request: reverse_lazy("admin:index"),
        },
        
        "COLORS": {
            "primary": {
                "50": "240 249 255",
                "100": "224 242 254",
                "200": "186 230 253",
                "300": "125 211 252",
                "400": "56 189 248",
                "500": "14 165 233",
                "600": "2 132 199",
                "700": "3 105 161",
                "800": "7 89 133",
                "900": "12 74 110",
                "950": "8 47 73",
            },
        },
        
        "SIDEBAR": {
            "show_search": True,
            "show_all_applications": False, # Ortiqcha modellar chiqib ketmasligi uchun False qilingan
            "navigation": [
                # ========== 1. ASOSIY ==========
                {
                    "title": _("Asosiy"),
                    "separator": True,
                    "items": [
                        {
                            "title": _("Dashboard"),
                            "icon": "dashboard",
                            "link": reverse_lazy("admin:index"),
                        },
                    ],
                },
                
                # ========== 2. FOYDALANUVCHILAR ==========
                {
                    "title": _("Foydalanuvchilar"),
                    "icon": "group",
                    "collapsible": True,
                    "items": [
                        {
                            "title": _("Foydalanuvchilar"),
                            "icon": "people",
                            "link": reverse_lazy("admin:baseuser_baseuser_changelist"),
                        },
                        {
                            "title": _("Statistika"),
                            "icon": "analytics",
                            "link": reverse_lazy("admin:status_userstats_changelist"),
                        },
                        {
                            "title": _("Kunlik faoliyat"),
                            "icon": "calendar_today",
                            "link": reverse_lazy("admin:status_useractivitydaily_changelist"),
                        },
                    ],
                },
                
                # ========== 3. TA'LIM ==========
                {
                    "title": _("Ta'lim"),
                    "icon": "school",
                    "collapsible": True,
                    "items": [
                        {
                            "title": _("Kurslar"),
                            "icon": "menu_book",
                            "link": reverse_lazy("admin:courses_course_changelist"),
                        },
                        {
                            "title": _("Modullar"),
                            "icon": "folder",
                            "link": reverse_lazy("admin:courses_modul_changelist"),
                        },
                        {
                            "title": _("Darslar"),
                            "icon": "description",
                            "link": reverse_lazy("admin:courses_lesson_changelist"),
                        },
                        {
                            "title": _("Kursga yozilishlar"),
                            "icon": "assignment_ind",
                            "link": reverse_lazy("admin:courses_enrilliment_changelist"),
                        },
                    ],
                },
                
                # ========== 4. MASALALAR ==========
                {
                    "title": _("Masalalar"),
                    "icon": "code",
                    "collapsible": True,
                    "items": [
                        {
                            "title": _("Masalalar"),
                            "icon": "bug_report",
                            "link": reverse_lazy("admin:problems_problem_changelist"),
                        },
                        {
                            "title": _("Kategoriyalar"),
                            "icon": "category",
                            "link": reverse_lazy("admin:problems_category_changelist"),
                        },
                        {
                            "title": _("Teglar"),
                            "icon": "local_offer",
                            "link": reverse_lazy("admin:problems_tags_changelist"),
                        },
                        {
                            "title": _("Dasturlash tillari"),
                            "icon": "computer",
                            "link": reverse_lazy("admin:problems_language_changelist"),
                        },
                    ],
                },
                
                # ========== 5. TEST VA QUIZLAR ==========
                {
                    "title": _("Test va Quizlar"),
                    "icon": "quiz",
                    "collapsible": True,
                    "items": [
                        {
                            "title": _("Testlar"),
                            "icon": "assignment",
                            "link": reverse_lazy("admin:quizs_test_changelist"),
                        },
                        {
                            "title": _("Savollar"),
                            "icon": "help",
                            "link": reverse_lazy("admin:quizs_question_changelist"),
                        },
                        {
                            "title": _("Test natijalari"),
                            "icon": "assessment",
                            "link": reverse_lazy("admin:quizs_testsession_changelist"),
                        },
                        {
                            "title": _("Foydalanuvchi reytingi"),
                            "icon": "leaderboard",
                            "link": reverse_lazy("admin:quizs_userrank_changelist"),
                        },
                        {
                            "title": _("Sertifikatlar"),
                            "icon": "verified",
                            "link": reverse_lazy("admin:quizs_certificate_changelist"),
                        },
                    ],
                },
                
                # ========== 6. MUSOBAQALAR ==========
                {
                    "title": _("Musobaqalar"),
                    "icon": "emoji_events",
                    "collapsible": True,
                    "items": [
                        {
                            "title": _("Musobaqalar"),
                            "icon": "trophy",
                            "link": reverse_lazy("admin:contests_contest_changelist"),
                        },
                        {
                            "title": _("Musobaqa registratsiyasi"),
                            "icon": "how_to_reg",
                            "link": reverse_lazy("admin:contests_contestregistration_changelist"),
                        },
                    ],
                },
                
                               # ========== 7. YECHIMLAR ==========
                {
                    "title": _("Yechimlar"),
                    "icon": "task",
                    "collapsible": True,
                    "items": [
                        {
                            "title": _("Barcha yechimlar"),
                            "icon": "code",
                            "link": reverse_lazy("admin:submissions_submission_changelist"),
                        },
                    ],
                },
                
                # ========== 8. VIDEO ==========
                {
                    "title": _("Video"),
                    "icon": "video_library",
                    "collapsible": True,
                    "items": [
                        {
                            "title": _("Videolar"),
                            "icon": "smart_display",
                            "link": reverse_lazy("admin:video_video_changelist"),
                        },
                    ],
                },
                
                # ========== 9. TO'LOVLAR ==========
                {
                    "title": _("To'lovlar"),
                    "icon": "payments",
                    "collapsible": True,
                    "items": [
                        {
                            "title": _("Buyurtmalar"),
                            "icon": "shopping_cart",
                            "link": reverse_lazy("admin:payment_order_changelist"),
                        },
                        {
                            "title": _("Hisob-fakturalar"),
                            "icon": "receipt",
                            "link": reverse_lazy("admin:payment_invoice_changelist"),
                        },
                    ],
                },
            ],  # navigation ro'yxatining yopilishi
        },  # SIDEBAR lug'atining yopilishi
    }  # unfold() funksiyasi qaytaradigan asosiy lug'atning yopilishi
