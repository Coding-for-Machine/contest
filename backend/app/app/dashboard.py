# app/dashboard.py - TO'G'RILANGAN VERSION

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

def dashboard_callback(request, context):
    # Importlarni funksiya ichida qilish
    from submissions.models import Submission
    from baseuser.models import BaseUser
    
    today = timezone.now()
    last_30 = today - timedelta(days=30)

    total_users = BaseUser.objects.count()
    total_submissions = Submission.objects.count()
    new_users_30d = BaseUser.objects.filter(created_at__gte=last_30).count()
    
    # STATUS BOOLEAN FIELD - to'g'rilandi
    # Agar status BooleanField bo'lsa: True = qabul qilingan, False = qabul qilinmagan
    accepted_count = Submission.objects.filter(status=True).count()  # <-- O'ZGARTIRILDI
    
    # YOKI agar status String bo'lsa (CharField) va "AC" qiymati bor bo'lsa:
    # accepted_count = Submission.objects.filter(status="AC").count()
    
    # Xatolikni oldini olish uchun tekshiruv
    if Submission.objects.exists():
        acceptance_rate = round(accepted_count / total_submissions * 100, 1)
    else:
        acceptance_rate = 0

    # Status bo'yicha taqsimot - Boolean uchun to'g'rilandi
    status_qs = (
        Submission.objects.values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    
    # Boolean qiymatlarni o'qiladigan matnga aylantirish
    status_labels = {
        True: "Qabul qilingan",
        False: "Qabul qilinmagan"
    }
    
    submission_status_chart = {
        "labels": [status_labels.get(item["status"], str(item["status"])) for item in status_qs],
        "datasets": [
            {
                "data": [item["count"] for item in status_qs],
                "backgroundColor": ["#22c55e", "#ef4444"],  # Yashil = True, Qizil = False
            }
        ],
    }

    # Oxirgi 30 kunlik yangi userlar
    users_per_day = (
        BaseUser.objects.filter(created_at__gte=last_30)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    
    users_growth_chart = {
        "labels": [item["day"].strftime("%d-%m") for item in users_per_day],
        "datasets": [
            {
                "label": "Yangi userlar",
                "data": [item["count"] for item in users_per_day],
                "borderColor": "#0ea5e9",
                "backgroundColor": "rgba(14, 165, 233, 0.15)",
                "fill": True,
                "tension": 0.4,
            }
        ],
    }

    context.update({
        "kpi": [
            {
                "title": "Jami foydalanuvchilar",
                "metric": total_users,
                "icon": "group",
                "footer": f"+{new_users_30d} so'nggi 30 kunda",
            },
            {
                "title": "Jami yechimlar",
                "metric": total_submissions,
                "icon": "task",
                "footer": f"{accepted_count} ta qabul qilingan",
            },
            {
                "title": "Yangi userlar (30 kun)",
                "metric": new_users_30d,
                "icon": "trending_up",
                "footer": "Oxirgi 30 kun",
            },
            {
                "title": "Qabul qilish foizi",
                "metric": f"{acceptance_rate}%",
                "icon": "check_circle",
                "footer": "Qabul qilingan / jami yechimlar",
            },
        ],
        "submission_status_chart": submission_status_chart,
        "users_growth_chart": users_growth_chart,
    })
    return context