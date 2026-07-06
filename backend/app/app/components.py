# app/components.py

import json
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta
from unfold.components import BaseComponent
from unfold.decorators import register_component


@register_component
class UsersGrowthChartComponent(BaseComponent):
    """Foydalanuvchi o'sishi grafigi"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            from baseuser.models import BaseUser
            UserModel = BaseUser
        except ImportError:
            from django.contrib.auth import get_user_model
            UserModel = get_user_model()
        
        today = timezone.now()
        last_30 = today - timedelta(days=30)
        
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
            
            context.update({
                "height": 280,
                "data": json.dumps({
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
                    ]
                })
            })
        else:
            context.update({
                "height": 280,
                "data": json.dumps({
                    "labels": ["Ma'lumot yo'q"],
                    "datasets": [{
                        "label": "O'sish",
                        "data": [0],
                        "borderColor": "#6b7280",
                    }]
                })
            })
        
        return context


@register_component
class SubmissionStatusChartComponent(BaseComponent):
    """Yechim holati (Doughnut chart)"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            from submissions.models import Submission
        except ImportError:
            Submission = None
        
        if Submission and Submission.objects.exists():
            accepted = Submission.objects.filter(status=True).count()
            rejected = Submission.objects.filter(status=False).count()
            
            context.update({
                "height": 220,
                "data": json.dumps({
                    "labels": ["✅ Qabul qilingan", "❌ Qabul qilinmagan"],
                    "datasets": [{
                        "data": [accepted, rejected],
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
                    }]
                })
            })
        else:
            context.update({
                "height": 220,
                "data": json.dumps({
                    "labels": ["Ma'lumot yo'q"],
                    "datasets": [{
                        "data": [1],
                        "backgroundColor": ["rgba(107, 114, 128, 0.3)"],
                        "borderColor": ["rgba(107, 114, 128, 0.5)"],
                        "borderWidth": 2,
                    }]
                })
            })
        
        return context


@register_component
class SubmissionsDynamicsChartComponent(BaseComponent):
    """Yechim dinamikasi (Bar chart)"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            from submissions.models import Submission
        except ImportError:
            Submission = None
        
        today = timezone.now()
        last_30 = today - timedelta(days=30)
        
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
            
            context.update({
                "height": 280,
                "data": json.dumps({
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
                    ]
                })
            })
        else:
            context.update({
                "height": 280,
                "data": json.dumps({
                    "labels": ["Ma'lumot yo'q"],
                    "datasets": [{
                        "label": "Yechimlar",
                        "data": [0],
                        "backgroundColor": ["rgba(107, 114, 128, 0.3)"],
                    }]
                })
            })
        
        return context


@register_component
class AcceptanceTrendChartComponent(BaseComponent):
    """Qabul foizi trendi (Line chart)"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            from submissions.models import Submission
        except ImportError:
            Submission = None
        
        today = timezone.now()
        
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
            
            context.update({
                "height": 280,
                "data": json.dumps({
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
                    }]
                })
            })
        else:
            context.update({
                "height": 280,
                "data": json.dumps({
                    "labels": ["Ma'lumot yo'q"],
                    "datasets": [{
                        "label": "Qabul foizi",
                        "data": [0],
                        "borderColor": "#6b7280",
                    }]
                })
            })
        
        return context


@register_component
class MonthlyChartComponent(BaseComponent):
    """Oylik statistika (Bar chart)"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            from submissions.models import Submission
        except ImportError:
            Submission = None
        
        today = timezone.now()
        last_90 = today - timedelta(days=90)
        
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
            
            context.update({
                "height": 280,
                "data": json.dumps({
                    "labels": monthly_labels if monthly_labels else ["Ma'lumot yo'q"],
                    "datasets": [
                        {
                            "label": "Qabul foizi",
                            "data": monthly_rates if monthly_rates else [0],
                            "backgroundColor": "rgba(139, 92, 246, 0.6)",
                            "borderColor": "#8b5cf6",
                            "borderWidth": 2,
                        },
                        {
                            "label": "Jami yechimlar",
                            "data": monthly_counts if monthly_counts else [0],
                            "backgroundColor": "rgba(59, 130, 246, 0.6)",
                            "borderColor": "#3b82f6",
                            "borderWidth": 2,
                        },
                    ]
                })
            })
        else:
            context.update({
                "height": 280,
                "data": json.dumps({
                    "labels": ["Ma'lumot yo'q"],
                    "datasets": [{
                        "label": "Ma'lumot",
                        "data": [0],
                        "borderColor": "#6b7280",
                    }]
                })
            })
        
        return context