# app/unfold.py
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from decouple import config
from datetime import timedelta
from django.utils import timezone

DEBUG = config('DEBUG', default=False, cast=bool)
def get_last_7_days_link():
    date_str = (timezone.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    return f"{reverse_lazy('admin:problems_problem_changelist')}?created_at__gte={date_str}"


def get_last_30_days_link():
    date_str = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    return f"{reverse_lazy('admin:problems_problem_changelist')}?created_at__gte={date_str}"



def environment_callback(request):
    if DEBUG:
        return ["DEVELOPMENT", "warning"]
    return ["PRODUCTION", "success"]


def unfold():
    return {
        "SITE_TITLE": "CfM Contest",
        "SITE_HEADER": "CfM Contest",
        "SITE_SUBHEADER": "Boshqaruv paneli",
        "SITE_SYMBOL":  "trophy",
        "SITE_URL": "/",
        "SHOW_HISTORY": True,
        "SHOW_VIEW_ON_SITE": True,
        "SHOW_LANGUAGES": False,
        "SHOW_BACK_BUTTON": True,
        "SHOW_UI_WARNINGS": True,

        "HIDE_APPS": [
            "auth",
            "authtoken",
            "sessions",
            "contenttypes",
            "admin",
        ],

        "DASHBOARD_CALLBACK": "app.dashboard.get_dashboard_context",
        "ENVIRONMENT": "app.unfold.environment_callback",
        "LOGIN": {
                "image": lambda request: static("img/login-bg.jpg"),
                "title": "Xush kelibsiz",
                "description": "Hisobingizga kiring va bilimingizni sinab ko'ring",
                "redirect_after": lambda request: reverse_lazy("admin:index"),
            },
            "STYLES": [
                lambda request: static("css/output.css"),
            ],
            "COLORS": {
            "base": {   # Neytral ranglar (kulrang)
                "50":  "250 250 250",   # RGB formatda
                "100": "244 244 245",
                "200": "228 228 231",
                "300": "212 212 216",
                "400": "161 161 170",
                "500": "113 113 122",
                "600": "82 82 91",
                "700": "63 63 70",
                "800": "39 39 42",
                "900": "24 24 27",
                "950": "9 9 11",
            },
            "primary": {  # Asosiy rang (tugmalar, linklar, header)
                "50":  "240 249 255",
                "100": "224 242 254",
                "200": "186 230 253",
                "300": "125 211 252",
                "400": "56 189 248",
                "500": "14 165 233",   # ← Asosiy rang
                "600": "2 132 199",
                "700": "3 105 161",
                "800": "7 89 133",
                "900": "12 74 110",
                "950": "8 47 73",
            },
            # Matn ranglari
            "font": {
                "subtle-light":    "var(--color-base-500)",
                "subtle-dark":     "var(--color-base-400)",
                "default-light":   "var(--color-base-600)",
                "default-dark":    "var(--color-base-300)",
                "important-light": "var(--color-base-900)",
                "important-dark":  "var(--color-base-100)",
            },
        },
        "BUTTONS": {
            "save": {"variant": "primary"},
            "save_and_continue": {"variant": "secondary"},
            "save_and_add": {"variant": "secondary"},
            "delete": {"variant": "danger"},
        },
        "FORMS": {
            "classes": {
                "text_input": "border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500",
                # Default sinflarga qo'shimcha Tailwind class qo'shish
            },
        },

       
        "SITE_DROPDOWN": [
            {
                "icon": "admin_panel_settings",
                "title": _("Admin Boshqaruvi"),
                "link": reverse_lazy("admin:index"),
                "attrs": {
                    "target": "_blank",
                },
            },
            {
                "icon": "group",
                "title": _("Foydalanuvchilar"),
                "link": reverse_lazy("admin:baseuser_baseuser_changelist"),
            },
        ],
        
        "TABS": [
            {
                "models": [
                    "problems.problem",
                    "problems.category",
                    "problems.tags",
                    "problems.hint",
                    "problems.challenge",
                    "problems.function",
                    "problems.executiontestcase",
                    "problems.testcase",
                    "problems.like",
                    "problems.language",
                ],
                "items": [
                    {
                        "title": _("📋 Barcha masalalar"),
                        "icon": "list_alt",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist"),
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("🟢 Oson masalalar"),
                        "icon": "emoji_nature",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?difficulty__exact=easy",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("🟡 O'rtacha masalalar"),
                        "icon": "emoji_objects",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?difficulty__exact=medium",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("🔴 Qiyin masalalar"),
                        "icon": "whatshot",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?difficulty__exact=hard",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("✅ Faol masalalar"),
                        "icon": "check_circle",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?is_active__exact=1",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("❌ Nofaol masalalar"),
                        "icon": "cancel",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?is_active__exact=0",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("🏆 Musobaqa masalalari"),
                        "icon": "emoji_events",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?contest__isnull=False",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("📚 Oddiy masalalar"),
                        "icon": "menu_book",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?contest__isnull=True",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("🆕 So'nggi 7 kun"),
                        "icon": "new_releases",
                        "link": lambda request: get_last_7_days_link(),
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("📅 So'nggi 30 kun"),
                        "icon": "date_range",
                        "link": lambda request: get_last_30_days_link(),
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("📖 Darslikka tegishli"),
                        "icon": "school",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?lesson__isnull=False",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("📝 Darsliksiz masalalar"),
                        "icon": "note_add",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?lesson__isnull=True",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("📁 Kategoriyali masalalar"),
                        "icon": "folder",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?category__isnull=False",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("📂 Kategoriyasiz masalalar"),
                        "icon": "folder_open",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?category__isnull=True",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("⭐ Yuqori XP (50+)"),
                        "icon": "stars",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?xp__gte=50",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("⭐ O'rta XP (25-49)"),
                        "icon": "grade",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?xp__gte=25&xp__lte=49",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                    {
                        "title": _("⭐ Past XP (< 25)"),
                        "icon": "star_half",
                        "link": lambda request: reverse_lazy("admin:problems_problem_changelist") + "?xp__lt=25",
                        "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    },
                ],
            }
        ],

        "SIDEBAR": {
            "show_search": True,
            "show_all_applications": False,
            "navigation": [

                # ══════════════════════════════════════
                # 1. ASOSIY — Hamma ko'radi
                # ══════════════════════════════════════
                {
                    "title": _("Asosiy"),
                    "separator": True,
                    "collapsible": False,  # Yig'ib-yoyish
                    "items": [
                        {
                            "title": _("Dashboard"),
                            "icon": "dashboard",
                            "link": reverse_lazy("admin:index"),
                        },
                    ],
                },

                # ══════════════════════════════════════
                # 2. ADMIN BOSHQARUVI — Faqat Superuser
                # ══════════════════════════════════════
                {
                    "title": _("Admin Boshqaruvi"),
                    "icon": "admin_panel_settings",
                    "collapsible": True,
                    "separator": True,     # Chiziq

                    "permission": lambda request: request.user.is_superuser,
                    "items": [
                        {
                            "title": _("Adminlar (Staff)"),
                            "icon": "admin_panel_settings",
                            "link": reverse_lazy("admin:auth_user_changelist"),  # ✅ Django User
                            "permission": lambda request: request.user.is_superuser,
                        },
                        {
                            "title": _("Guruhlar va Rollar"),
                            "icon": "groups",
                            "link": reverse_lazy("admin:auth_group_changelist"),  # ✅ Django Group
                            "permission": lambda request: request.user.is_superuser,
                        },
                    ],
                },
                # ══════════════════════════════════════
                # 3. FOYDALANUVCHILAR
                # O'qituvchi, Moderator, Superuser
                # ══════════════════════════════════════
                {
                    "title": _("Foydalanuvchilar"),
                    "icon": "group",
                    "collapsible": True,
                    "permission": lambda request: (
                        request.user.is_superuser or
                        request.user.has_perm("baseuser.view_baseuser")
                    ),
                    "items": [
                        {
                            "title": _("Foydalanuvchilar"),
                            "icon": "people",
                            "link": reverse_lazy("admin:baseuser_baseuser_changelist"),
                            "permission": lambda request: request.user.has_perm("baseuser.view_baseuser"),
                        },
                        {
                            "title": _("Foydalanuvchi profillari"),
                            "icon": "badge",
                            "link": reverse_lazy("admin:baseuser_profile_changelist"),
                            "permission": lambda request: request.user.has_perm("baseuser.view_profile"),
                        },
                    ],
                },

                # ══════════════════════════════════════
                # 4. TA'LIM
                # O'qituvchi: to'liq
                # Kontent Menejer: faqat ko'rish
                # Moderator: faqat ko'rish
                # ══════════════════════════════════════
                
                {
                    "title": _("Ta'lim"),
                    "icon": "school",
                    "collapsible": True,
                    "permission": lambda request: request.user.has_perm("courses.view_course"),
                    "items": [
                        {
                            "title": _("Kurslar"),
                            "icon": "menu_book",
                            "link": reverse_lazy("admin:courses_course_changelist"),
                            "permission": lambda request: request.user.has_perm("courses.view_course"),
                        },
                        {
                            "title": _("Modullar"),
                            "icon": "folder",
                            "link": reverse_lazy("admin:courses_modul_changelist"),
                            "permission": lambda request: request.user.has_perm("courses.view_modul"),
                        },
                        {
                            "title": _("Darslar"),
                            "icon": "description",
                            "link": reverse_lazy("admin:courses_lesson_changelist"),
                            "permission": lambda request: request.user.has_perm("courses.view_lesson"),
                        },
                        {
                            "title": _("Ma'ruza"),
                            "icon": "play_lesson",
                            "link": reverse_lazy("admin:courses_lecture_changelist"),
                            "permission": lambda request: request.user.has_perm("courses.view_lecture"),
                        },
        
                    ],
                },
                {
                    "title": _("Statistika & Hisobotlar"),
                    "icon": "analytics",
                    "collapsible": True,
                    # BU YERDA: Superuser bo'lsa birdan o'tkazib yuborish
                    "permission": lambda request: request.user.is_superuser or request.user.has_perm("courses.view_enrollment"),
                    "items": [
                        {
                            "title": _("Kursga yozilishlar"),
                            "icon": "assignment_ind",
                            "link": reverse_lazy("admin:courses_enrollment_changelist"),
                            # BU YERDA HAM:
                            "permission": lambda request: request.user.is_superuser or request.user.has_perm("courses.view_enrollment"),
                        },
                        {
                            "title": _("User va Darsliklar statistikasi"),
                            "icon": "finance_mode",
                            "link": reverse_lazy("admin:status_lessonstatus_changelist"),
                            "permission": lambda request: request.user.has_perm("status.view_lessonstatus"),
                        },
                        {
                            "title": _("Ma'ruza progresslari"),
                            "icon": "trending_up",
                            "link": reverse_lazy("admin:status_lecturestatus_changelist"),
                            "permission": lambda request: request.user.has_perm("status.view_lecturestatus"),
                        },
                        {
                            "title": _("Statistika"),
                            "icon": "analytics",
                            "link": reverse_lazy("admin:status_userstats_changelist"),
                            "permission": lambda request: request.user.has_perm("status.view_userstats"),
                        },
                        {
                            "title": _("Kunlik faoliyat"),
                            "icon": "calendar_today",
                            "link": reverse_lazy("admin:status_useractivitydaily_changelist"),
                            "permission": lambda request: request.user.has_perm("status.view_useractivitydaily"),
                        },
                    ],
                },

                # ══════════════════════════════════════
                # 5. MASALALAR
                # Masala Muallifi: to'liq
                # Moderator: faqat ko'rish
                # ══════════════════════════════════════
                {
                    "title": _("Masalalar"),
                    "icon": "code",
                    "collapsible": True,
                    "permission": lambda request: request.user.has_perm("problems.view_problem"),
                    "items": [
                        {
                            "title": _("Masalalar"),
                            "icon": "bug_report",
                            "link": reverse_lazy("admin:problems_problem_changelist"),
                            "permission": lambda request: request.user.has_perm("problems.view_problem"),
                        },
                        {
                            "title": _("Kategoriyalar"),
                            "icon": "category",
                            "link": reverse_lazy("admin:problems_category_changelist"),
                            "permission": lambda request: request.user.has_perm("problems.view_category"),
                        },
                        {
                            "title": _("Teglar"),
                            "icon": "local_offer",
                            "link": reverse_lazy("admin:problems_tags_changelist"),
                            "permission": lambda request: request.user.has_perm("problems.view_tags"),
                        },
                        {
                            "title": _("Dasturlash tillari"),
                            "icon": "computer",
                            "link": reverse_lazy("admin:problems_language_changelist"),
                            "permission": lambda request: request.user.has_perm("problems.view_language"),
                        },
                        {
                            "title": _("Yordamlar"),
                            "icon": "lightbulb",
                            "link": reverse_lazy("admin:problems_hint_changelist"),
                            "permission": lambda request: request.user.has_perm("problems.view_hint"),
                        },
                        {
                            "title": _("Topshiriqlar"),
                            "icon": "flag",
                            "link": reverse_lazy("admin:problems_challenge_changelist"),
                            "permission": lambda request: request.user.has_perm("problems.view_challenge"),
                        },
                        {
                            "title": _("Funksiya shablonlari"),
                            "icon": "functions",
                            "link": reverse_lazy("admin:problems_function_changelist"),
                            "permission": lambda request: request.user.has_perm("problems.view_function"),
                        },
                        {
                            "title": _("Kod testlari"),
                            "icon": "play_circle",
                            "link": reverse_lazy("admin:problems_executiontestcase_changelist"),
                            "permission": lambda request: request.user.has_perm("problems.view_executiontestcase"),
                        },
                        {
                            "title": _("Test caselar"),
                            "icon": "fact_check",
                            "link": reverse_lazy("admin:problems_testcase_changelist"),
                            "permission": lambda request: request.user.has_perm("problems.view_testcase"),
                        },
                        {
                            "title": _("Reaksiyalar"),
                            "icon": "thumb_up",
                            "link": reverse_lazy("admin:problems_like_changelist"),
                            "permission": lambda request: request.user.has_perm("problems.view_like"),
                        },
                    ],
                },

                # ══════════════════════════════════════
                # 6. TEST VA QUIZLAR
                # Kontent Menejer: to'liq
                # Moderator: faqat ko'rish
                # ══════════════════════════════════════
                {
                    "title": _("Test va Quizlar"),
                    "icon": "quiz",
                    "collapsible": True,
                    "permission": lambda request: request.user.has_perm("quizs.view_test"),
                    "items": [
                        {
                            "title": _("Testlar"),
                            "icon": "assignment",
                            "link": reverse_lazy("admin:quizs_test_changelist"),
                            "permission": lambda request: request.user.has_perm("quizs.view_test"),
                        },
                        {
                            "title": _("Savollar"),
                            "icon": "help",
                            "link": reverse_lazy("admin:quizs_question_changelist"),
                            "permission": lambda request: request.user.has_perm("quizs.view_question"),
                        },
                        {
                            "title": _("Varyatlarr"),
                            "icon": "help",
                            "link": reverse_lazy("admin:quizs_choice_changelist"),
                            "permission": lambda request: request.user.has_perm("quizs.view_choice"),
                        },
                        {
                            "title": _("Test natijalari"),
                            "icon": "assessment",
                            "link": reverse_lazy("admin:quizs_testsession_changelist"),
                            "permission": lambda request: request.user.has_perm("quizs.view_testsession"),
                        },
                        {
                            "title": _("Sotib olingan test"),
                            "icon": "credit_card_heart",
                            "link": reverse_lazy("admin:quizs_testenrollment_changelist"),
                            "permission": lambda request: request.user.has_perm("quizs.view_testenrollment"),
                        },
                        # UserResponseAdmin
                        {
                            "title": _("Foydalanovchi javoblari"),
                            "icon": "groups_2",
                            "link": reverse_lazy("admin:quizs_userresponse_changelist"),
                            "permission": lambda request: request.user.has_perm("quizs.view_userresponse"),
                        },
                    ],
                },
                # 
                {
                    "title": _("Sertifikat"),
                    "icon": "workspace_premium",
                    "collapsible": True,
                    "permission": lambda request: request.user.is_superuser,
                    "items": [
                        {
                            "title": _("Sertifikat Shablonlari"),
                            "icon": "auto_awesome_motion",
                            "link": reverse_lazy("admin:certificate_certificatetemplate_changelist"), # 👈 q harfi olib tashlandi
                            "permission": lambda request: request.user.has_perm("certificate.view_certificatetemplate"),
                        },
                        {
                            "title": _("Berilgan Sertifikatlar"),
                            "icon": "workspace_premium",
                            "link": reverse_lazy("admin:certificate_certificate_changelist"), # 👈 q harfi olib tashlandi
                            "permission": lambda request: request.user.has_perm("certificate.view_certificate"),
                        },
                    ]
                },


                # ══════════════════════════════════════
                # 7. MUSOBAQALAR
                # ══════════════════════════════════════
                {
                    "title": _("Musobaqalar"),
                    "icon": "emoji_events",
                    "collapsible": True,
                    "permission": lambda request: request.user.has_perm("contests.view_contest"),
                    "items": [
                        {
                            "title": _("Musobaqalar"),
                            "icon": "emoji_events",
                            "link": reverse_lazy("admin:contests_contest_changelist"),
                            "permission": lambda request: request.user.has_perm("contests.view_contest"),
                        },
                        {
                            "title": _("Musobaqa ro'yxatga olish"),
                            "icon": "how_to_reg",
                            "link": reverse_lazy("admin:contests_contestregistration_changelist"),
                            "permission": lambda request: request.user.has_perm("contests.view_contestregistration"),
                        },
                    ],
                },

                # ══════════════════════════════════════
                # 8. YECHIMLAR
                # Moderator va Superuser ko'radi
                # ══════════════════════════════════════
                {
                    "title": _("Yechimlar"),
                    "icon": "task",
                    "collapsible": True,
                    "permission": lambda request: request.user.has_perm("submissions.view_submission"),
                    "items": [
                        {
                            "title": _("Barcha yechimlar"),
                            "icon": "code",
                            "link": reverse_lazy("admin:submissions_submission_changelist"),
                            "permission": lambda request: request.user.has_perm("submissions.view_submission"),
                        },
                    ],
                },

                # ══════════════════════════════════════
                # 9. VIDEO DARSLIKLAR
                # O'qituvchi: to'liq
                # Moderator: faqat ko'rish
                # ══════════════════════════════════════
                {
                    "title": _("Video darsliklar"),
                    "icon": "video_library",
                    "collapsible": True,
                    "permission": lambda request: request.user.has_perm("video.view_video"),
                    "items": [
                        {
                            "title": _("Videolar"),
                            "icon": "movie",
                            "link": reverse_lazy("admin:video_video_changelist"),
                            "permission": lambda request: request.user.has_perm("video.view_video"),
                        },
                    ],
                },

                # ══════════════════════════════════════
                # 10. TO'LOVLAR
                # Faqat Superuser ko'radi
                # ══════════════════════════════════════
                {
                    "title": _("To'lovlar"),
                    "icon": "payments",
                    "collapsible": True,
                    "permission": lambda request: request.user.has_perm("payment.view_order"),
                    "items": [
                        {
                            "title": _("Buyurtmalar"),
                            "icon": "shopping_cart",
                            "link": reverse_lazy("admin:payment_order_changelist"),
                            "permission": lambda request: request.user.has_perm("payment.view_order"),
                        },
                        {
                            "title": _("Hisob-fakturalar"),
                            "icon": "receipt",
                            "link": reverse_lazy("admin:payment_invoice_changelist"),
                            "permission": lambda request: request.user.has_perm("payment.view_invoice"),
                        },
                    ],
                },
            ],

        },
        "FORMS": {
            "classes": {
                "text_input": "border rounded px-3 py-2 custom-class",
                "checkbox": "custom-checkbox-class",
                "button": "custom-button-class",
                "radio": "custom-radio-class",
                "switch": "custom-switch-class",
                "file": "custom-file-class",
            }
        },

    }