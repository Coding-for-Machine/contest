# app/dashboard.py

from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


def dashboard_callback(request, context):
    """Unfold dashboard uchun callback"""
    
    # ============================================================
    # MODELLARNI IMPORT QILISH
    # ============================================================
    try:
        from submissions.models import Submission
    except ImportError:
        Submission = None
    
    try:
        from baseuser.models import BaseUser
        UserModel = BaseUser
    except ImportError:
        UserModel = User
    
    try:
        from courses.models import Course
    except ImportError:
        Course = None
    
    # ============================================================
    # VAQT
    # ============================================================
    today = timezone.now()
    last_30 = today - timedelta(days=30)
    last_7 = today - timedelta(days=7)
    last_90 = today - timedelta(days=90)
    
    # ============================================================
    # KPI MA'LUMOTLARI
    # ============================================================
    
    # Foydalanuvchilar
    if UserModel:
        total_users = UserModel.objects.count()
        new_users_30d = UserModel.objects.filter(
            created_at__gte=last_30
        ).count() if hasattr(UserModel, 'created_at') else 0
        new_users_7d = UserModel.objects.filter(
            created_at__gte=last_7
        ).count() if hasattr(UserModel, 'created_at') else 0
    else:
        total_users = 0
        new_users_30d = 0
        new_users_7d = 0
    
    # Kurslar
    if Course:
        total_courses = Course.objects.count()
    else:
        total_courses = 0
    
    # Yechimlar
    if Submission and Submission.objects.exists():
        total_submissions = Submission.objects.count()
        accepted_count = Submission.objects.filter(status=True).count()
        rejected_count = Submission.objects.filter(status=False).count()
        
        recent_submissions = Submission.objects.filter(
            created_at__gte=last_30
        ).count() if hasattr(Submission, 'created_at') else 0
        
        recent_accepted = Submission.objects.filter(
            status=True,
            created_at__gte=last_30
        ).count() if hasattr(Submission, 'created_at') else 0
        
        if total_submissions > 0:
            acceptance_rate = round((accepted_count / total_submissions) * 100, 1)
        else:
            acceptance_rate = 0
        
        if recent_submissions > 0:
            recent_acceptance_rate = round((recent_accepted / recent_submissions) * 100, 1)
        else:
            recent_acceptance_rate = 0
        
        if hasattr(Submission, 'time_spent_seconds'):
            avg_time = Submission.objects.aggregate(
                avg=Avg('time_spent_seconds')
            )['avg'] or 0
            avg_time_minutes = round(avg_time / 60, 1) if avg_time > 0 else 0
        else:
            avg_time_minutes = 0
            
    else:
        total_submissions = 0
        accepted_count = 0
        rejected_count = 0
        recent_submissions = 0
        recent_accepted = 0
        acceptance_rate = 0
        recent_acceptance_rate = 0
        avg_time_minutes = 0
    
    # ============================================================
    # 1️⃣ YECHIM HOLATI (DOUGHNUT CHART)
    # ============================================================
    if Submission and Submission.objects.exists():
        submission_status_chart = {
            "labels": ["✅ Qabul qilingan", "❌ Qabul qilinmagan"],
            "datasets": [{
                "data": [accepted_count, rejected_count],
                "backgroundColor": [
                    "rgba(34, 197, 94, 0.8)",
                    "rgba(239, 68, 68, 0.8)"
                ],
                "borderColor": [
                    "rgba(34, 197, 94, 1)",
                    "rgba(239, 68, 68, 1)"
                ],
                "borderWidth": 3,
                "hoverOffset": 15,
            }],
        }
    else:
        submission_status_chart = {
            "labels": ["Ma'lumot yo'q"],
            "datasets": [{
                "data": [1],
                "backgroundColor": ["rgba(107, 114, 128, 0.3)"],
                "borderColor": ["rgba(107, 114, 128, 0.5)"],
                "borderWidth": 2,
            }],
        }
    
    # ============================================================
    # 2️⃣ FOYDALANUVCHI O'SHISHI (LINE CHART)
    # ============================================================
    if UserModel and hasattr(UserModel, 'created_at'):
        users_per_day = (
            UserModel.objects
            .filter(created_at__gte=last_30)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        
        date_range = [last_30 + timedelta(days=i) for i in range(31)]
        users_dict = {item["day"]: item["count"] for item in users_per_day}
        
        labels = []
        cumulative = []
        daily = []
        total = 0
        
        for date in date_range:
            labels.append(date.strftime("%d.%m"))
            count = users_dict.get(date.date(), 0)
            total += count
            cumulative.append(total)
            daily.append(count)
        
        users_growth_chart = {
            "labels": labels,
            "datasets": [
                {
                    "label": "Kumulyativ o'sish",
                    "data": cumulative,
                    "borderColor": "#3b82f6",
                    "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    "fill": True,
                    "tension": 0.4,
                    "pointRadius": 3,
                    "borderWidth": 3,
                },
                {
                    "label": "Kunlik yangi userlar",
                    "data": daily,
                    "borderColor": "#8b5cf6",
                    "backgroundColor": "rgba(139, 92, 246, 0.1)",
                    "fill": True,
                    "tension": 0.4,
                    "pointRadius": 2,
                    "borderWidth": 2,
                    "borderDash": [5, 5],
                }
            ],
        }
    else:
        users_growth_chart = {
            "labels": ["Ma'lumot yo'q"],
            "datasets": [{
                "label": "O'sish",
                "data": [0],
                "borderColor": "#6b7280",
            }],
        }
    
    # ============================================================
    # 3️⃣ YECHIM DINAMIKASI (BAR CHART)
    # ============================================================
    if Submission and hasattr(Submission, 'created_at'):
        submissions_per_day = (
            Submission.objects
            .filter(created_at__gte=last_30)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                total=Count("id"),
                accepted=Count("id", filter=Q(status=True)),
                rejected=Count("id", filter=Q(status=False))
            )
            .order_by("day")
        )
        
        date_range = [last_30 + timedelta(days=i) for i in range(31)]
        sub_dict = {item["day"]: item for item in submissions_per_day}
        
        labels = []
        total_data = []
        accepted_data = []
        rejected_data = []
        
        for date in date_range:
            labels.append(date.strftime("%d.%m"))
            data = sub_dict.get(date.date(), {})
            total_data.append(data.get("total", 0))
            accepted_data.append(data.get("accepted", 0))
            rejected_data.append(data.get("rejected", 0))
        
        submissions_dynamics_chart = {
            "labels": labels,
            "datasets": [
                {
                    "label": "Jami yechimlar",
                    "data": total_data,
                    "backgroundColor": "rgba(59, 130, 246, 0.6)",
                    "borderColor": "#3b82f6",
                    "borderWidth": 2,
                    "borderRadius": 4,
                },
                {
                    "label": "Qabul qilingan",
                    "data": accepted_data,
                    "backgroundColor": "rgba(34, 197, 94, 0.6)",
                    "borderColor": "#22c55e",
                    "borderWidth": 2,
                    "borderRadius": 4,
                },
                {
                    "label": "Qabul qilinmagan",
                    "data": rejected_data,
                    "backgroundColor": "rgba(239, 68, 68, 0.6)",
                    "borderColor": "#ef4444",
                    "borderWidth": 2,
                    "borderRadius": 4,
                },
            ],
        }
    else:
        submissions_dynamics_chart = {
            "labels": ["Ma'lumot yo'q"],
            "datasets": [{
                "label": "Yechimlar",
                "data": [0],
                "backgroundColor": ["rgba(107, 114, 128, 0.3)"],
            }],
        }
    
    # ============================================================
    # 4️⃣ QABUL FOIZI TRENDI (LINE CHART)
    # ============================================================
    if Submission and hasattr(Submission, 'created_at'):
        weekly_data = []
        for i in range(30, 0, -7):
            start = today - timedelta(days=i)
            end = start + timedelta(days=7)
            
            week_submissions = Submission.objects.filter(
                created_at__gte=start,
                created_at__lte=end
            ).count()
            
            week_accepted = Submission.objects.filter(
                status=True,
                created_at__gte=start,
                created_at__lte=end
            ).count()
            
            rate = round((week_accepted / week_submissions) * 100, 1) if week_submissions > 0 else 0
            weekly_data.append({
                'week': start.strftime("%d.%m"),
                'rate': rate,
            })
        
        acceptance_trend_chart = {
            "labels": [item['week'] for item in weekly_data],
            "datasets": [{
                "label": "Qabul qilish foizi",
                "data": [item['rate'] for item in weekly_data],
                "borderColor": "#22c55e",
                "backgroundColor": "rgba(34, 197, 94, 0.2)",
                "fill": True,
                "tension": 0.4,
                "pointRadius": 5,
                "pointBackgroundColor": "#22c55e",
                "borderWidth": 3,
            }],
        }
    else:
        acceptance_trend_chart = {
            "labels": ["Ma'lumot yo'q"],
            "datasets": [{
                "label": "Qabul foizi",
                "data": [0],
                "borderColor": "#6b7280",
            }],
        }
    
    # ============================================================
    # 5️⃣ OYLIK STATISTIKA (RADAR CHART)
    # ============================================================
    if Submission and hasattr(Submission, 'created_at'):
        monthly_data = (
            Submission.objects
            .filter(created_at__gte=last_90)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(
                total=Count("id"),
                accepted=Count("id", filter=Q(status=True))
            )
            .order_by("month")
        )
        
        monthly_labels = []
        monthly_rates = []
        monthly_counts = []
        
        for item in monthly_data:
            month = item['month'].strftime("%B %Y")
            monthly_labels.append(month)
            rate = round((item['accepted'] / item['total']) * 100, 1) if item['total'] > 0 else 0
            monthly_rates.append(rate)
            monthly_counts.append(item['total'])
        
        monthly_chart = {
            "labels": monthly_labels if monthly_labels else ["Ma'lumot yo'q"],
            "datasets": [
                {
                    "label": "Qabul foizi",
                    "data": monthly_rates if monthly_rates else [0],
                    "backgroundColor": "rgba(139, 92, 246, 0.2)",
                    "borderColor": "#8b5cf6",
                    "borderWidth": 2,
                    "pointBackgroundColor": "#8b5cf6",
                },
                {
                    "label": "Jami yechimlar",
                    "data": monthly_counts if monthly_counts else [0],
                    "backgroundColor": "rgba(59, 130, 246, 0.2)",
                    "borderColor": "#3b82f6",
                    "borderWidth": 2,
                    "pointBackgroundColor": "#3b82f6",
                },
            ],
        }
    else:
        monthly_chart = {
            "labels": ["Ma'lumot yo'q"],
            "datasets": [{
                "label": "Ma'lumot",
                "data": [0],
                "borderColor": "#6b7280",
            }],
        }
    
    # ============================================================
    # 📋 TABLE DATA - Unfold Table komponenti uchun
    # ============================================================
    table_data = {
        "headers": ["Ko'rsatkich", "Qiymat", "O'zgarish"],
        "rows": [
            ["Jami foydalanuvchilar", total_users, f"+{new_users_30d}"],
            ["Jami yechimlar", total_submissions, f"{accepted_count} qabul"],
            ["Qabul qilish foizi", f"{acceptance_rate}%", f"{recent_acceptance_rate}% oxirgi 30 kun"],
            ["O'rtacha vaqt", f"{avg_time_minutes} min", "Yechim uchun"],
        ]
    }
    
    # ============================================================
    # 📊 PROGRESS DATA - Unfold Progress komponenti uchun
    # ============================================================
    progress_data = [
        {
            "value": acceptance_rate,
            "title": "Qabul qilish foizi",
            "description": f"{accepted_count} ta qabul qilingan"
        },
        {
            "value": min(100, round((total_users / 1000) * 100)) if total_users > 0 else 0,
            "title": "Foydalanuvchi bazasi",
            "description": f"{total_users} ta foydalanuvchi"
        },
        {
            "value": min(100, round((total_submissions / 500) * 100)) if total_submissions > 0 else 0,
            "title": "Yechimlar soni",
            "description": f"{total_submissions} ta yechim"
        },
    ]
    
    # ============================================================
    # CONTEXT YANGILASH
    # ============================================================
    
    context.update({
        "kpi": [
            {
                "title": "Jami foydalanuvchilar",
                "metric": total_users,
                "icon": "group",
                "footer": f"+{new_users_30d} so'nggi 30 kunda",
                "change": f"+{new_users_7d} bu hafta",
            },
            {
                "title": "Jami yechimlar",
                "metric": total_submissions,
                "icon": "assignment",
                "footer": f"{accepted_count} ta qabul qilingan ({acceptance_rate}%)",
                "change": f"{recent_submissions} ta oxirgi 30 kunda",
            },
            {
                "title": "Qabul qilish foizi",
                "metric": f"{acceptance_rate}%",
                "icon": "trending_up",
                "footer": f"Oxirgi 30 kun: {recent_acceptance_rate}%",
                "change": "📊 " + ("Yuqori" if acceptance_rate > 50 else "Past"),
            },
            {
                "title": "O'rtacha vaqt",
                "metric": f"{avg_time_minutes} min",
                "icon": "timer",
                "footer": "Yechim uchun o'rtacha vaqt",
                "change": "⏱️ " + ("Tez" if avg_time_minutes < 10 else "O'rtacha"),
            },
        ],
        
        # Grafiklar
        "users_growth_chart": users_growth_chart,
        "submission_status_chart": submission_status_chart,
        "submissions_dynamics_chart": submissions_dynamics_chart,
        "acceptance_trend_chart": acceptance_trend_chart,
        "monthly_chart": monthly_chart,
        
        # Unfold komponentlar uchun ma'lumotlar
        "table_data": table_data,
        "progress_data": progress_data,
        
        "statistics": {
            "total_users": total_users,
            "new_users_30d": new_users_30d,
            "total_submissions": total_submissions,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "acceptance_rate": acceptance_rate,
            "recent_acceptance_rate": recent_acceptance_rate,
            "avg_time_minutes": avg_time_minutes,
            "total_courses": total_courses,
        },
        
        "title": "🏆 Musobaqalar Dashboard",
    })
    
    return context