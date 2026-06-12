# status/models.py
from datetime import timedelta
from django.db import models, transaction
from django.utils import timezone
from django.db.models import F
from baseuser.models import BaseUser
from courses.models import Lesson

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class UserStats(TimeStampedModel):
    user = models.OneToOneField('baseuser.BaseUser', on_delete=models.CASCADE, related_name='stats')
    xp = models.PositiveIntegerField(default=0, db_index=True)
    level = models.PositiveIntegerField(default=1)
    
    # Statistika (Bularni Go orqali oshirib borishingiz mumkin)
    easy_count = models.PositiveIntegerField(default=0)
    medium_count = models.PositiveIntegerField(default=0)
    hard_count = models.PositiveIntegerField(default=0)
    test_count = models.PositiveIntegerField(default=0)
    total_solved = models.PositiveIntegerField(default=0)

    # Streak - buni signallar emas, mantiq orqali boshqaring
    current_streak = models.PositiveIntegerField(default=0)
    last_activity = models.DateField(null=True, blank=True)

class LessonStatus(TimeStampedModel):
    user = models.ForeignKey('baseuser.BaseUser', on_delete=models.CASCADE)
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'lesson') # Bir foydalanuvchi bir darsni bir marta tugatadi



class UserActivityDaily(models.Model):
    user = models.ForeignKey('baseuser.BaseUser', on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    xp_earned = models.PositiveIntegerField(default=0)
    problems_count = models.PositiveIntegerField(default=0)
    total_duration = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')