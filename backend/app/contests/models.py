# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from baseuser.models import BaseUser

class Contest(models.Model):
    CONTEST_TYPES = [
        ('open', 'Ochiq Tanlov'),
        ('private', 'Yopiq Tanlov'),
    ]
    
    CONTEST_STATUS = [
        ('upcoming', 'Kutilmoqda'),
        ('ongoing', 'Davom etmoqda'),
        ('ended', 'Yakunlangan'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('easy', 'Oson'),
        ('medium', "O'rtacha"),
        ('hard', 'Qiyin'),
    ]
    
    # Asosiy maydonlar
    title = models.CharField(max_length=200, verbose_name="Tanlov nomi")
    description = models.TextField(verbose_name="Tavsif", blank=True, null=True)
    type = models.CharField(max_length=10, choices=CONTEST_TYPES, default='open')
    status = models.CharField(max_length=10, choices=CONTEST_STATUS, default='upcoming')
    
    # Vaqt maydonlari
    start_time = models.DateTimeField(verbose_name="Boshlanish vaqti")
    end_time = models.DateTimeField(verbose_name="Tugash vaqti")
    duration = models.CharField(max_length=50, verbose_name="Davomiylik", help_text="Masalan: 3 soat")
    
    # Ishtirokchilar
    participants = models.ManyToManyField(
        BaseUser, 
        through='ContestRegistration',
        related_name='registered_contests'
    )
    max_participants = models.IntegerField(default=1000, verbose_name="Maksimum ishtirokchilar")
    
    # Qiyinlik darajasi va mukofotlar
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='medium')
    prizes = models.JSONField(default=list, verbose_name="Mukofotlar", 
                             help_text='["1-o‘rin: $500", "2-o‘rin: $300"]')
    
    # Yopiq tanlov uchun
    access_key = models.CharField(max_length=100, blank=True, null=True, verbose_name="Kirish kaliti")
    
    # Statistika
    is_featured = models.BooleanField(default=False, verbose_name="Tanlangan")
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name="Kategoriya")
    
    # Auto timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "🏆 Musobaqa"
        verbose_name_plural = "🏁 Musobaqalar"
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['status', 'start_time']),
            models.Index(fields=['type', 'difficulty']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_registration_open(self):
        """Ro'yxatdan o'tish ochiqmi?"""
        return self.status == 'upcoming'
    
    @property
    def can_join(self):
        """Hozir ishtirok etish mumkinmi?"""
        now = timezone.now()
        return self.status == 'ongoing' and now >= self.start_time and now <= self.end_time
    
    def update_status(self):
        """Tanlov holatini yangilash"""
        now = timezone.now()
        if now < self.start_time:
            self.status = 'upcoming'
        elif now <= self.end_time:
            self.status = 'ongoing'
        else:
            self.status = 'ended'
        self.save()

class ContestRegistration(models.Model):
    """Tanlovga ro'yxatdan o'tish jadvali"""
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='contest_registrations')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # Yarash nuqtalari va reyting
    total_score = models.IntegerField(default=0)
    rank = models.IntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'contest']
        ordering = ['rank', '-total_score']
        verbose_name = "🪪 Ro'yxatdan o'tish"
        verbose_name_plural = "👥 Ro'yxatdan o'tganlar"
    
    def __str__(self):
        return f"{self.user.username} - {self.contest.title}"