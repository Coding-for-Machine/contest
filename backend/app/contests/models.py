import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from baseuser.models import BaseUser
from video.models import Video
from mdeditor.fields import MDTextField


class Contest(models.Model):
    """
    Tanlov / Musobaqa asosiy modeli.

    Tanlov ochiq (hammaga) yoki yopiq (faqat kalit bilganlarga) bo'lishi mumkin.
    Turi `access_key` maydoniga qarab `save()` ichida avtomat aniqlanadi,
    shuning uchun admin panelda `type` maydoni faqat o'qish uchun (readonly).
    """

    CONTEST_TYPES = [
        ('open', 'Ochiq Tanlov (Public)'),
        ('private', 'Yopiq Tanlov (Private)'),
    ]

    CONTEST_STATUS = [
        ('upcoming', 'Kutilmoqda'),
        ('ongoing', 'Davom etmoqda'),
        ('ended', 'Yakunlangan'),
    ]

    # ---------------------------------------------------------------------
    # Asosiy maydonlar
    # ---------------------------------------------------------------------
    title = models.CharField(
        max_length=200,
        verbose_name="Tanlov nomi",
        help_text="Tanlovning to'liq, foydalanuvchilarga ko'rinadigan nomi. Masalan: «Matematika Olimpiadasi 2026».",
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name="URL nomi (slug)",
        help_text="Lotin harflarida, bo'sh joysiz manzil qismi. Bo'sh qoldirilsa, tanlov nomidan avtomat hosil qilinadi.",
        blank=True,
    )
    description = MDTextField(
        verbose_name="Tavsif",
        help_text="Markdown formatida yozilgan to'liq tavsif: qoidalar, talablar, mukofotlar haqida umumiy ma'lumot.",
        blank=True,
        null=True,
    )
    cover_image = models.ImageField(
        upload_to='contests/covers/%Y/%m/',
        verbose_name="Muqova rasmi",
        help_text="Tanlov kartochkasi va sahifa boshida ko'rsatiladigan banner rasm (tavsiya etiladi: 1200x630px).",
        blank=True,
        null=True,
    )

    # Kalit bor-yo'qligiga qarab avtomat saqlanadi, admin panelda readonly bo'ladi
    type = models.CharField(
        max_length=10,
        choices=CONTEST_TYPES,
        default='open',
        db_index=True,
        editable=False,
        verbose_name="Tanlov turi",
        help_text="Avtomat hisoblanadi: agar «Kirish kaliti» kiritilgan bo'lsa — Yopiq, aks holda — Ochiq.",
    )
    status = models.CharField(
        max_length=10,
        choices=CONTEST_STATUS,
        default='upcoming',
        db_index=True,
        verbose_name="Holati",
        help_text="Boshlanish/tugash vaqtiga qarab `save()` chaqirilganda avtomat yangilanadi.",
    )

    # ---------------------------------------------------------------------
    # Vaqt parametrlari
    # ---------------------------------------------------------------------
    start_time = models.DateTimeField(
        verbose_name="Boshlanish vaqti",
        help_text="Tanlov aynan shu vaqtda boshlanadi va ishtirokchilar testga kira oladi.",
    )
    end_time = models.DateTimeField(
        verbose_name="Tugash vaqti",
        help_text="Bu vaqtdan keyin tanlov avtomat ravishda yakunlangan deb belgilanadi va kirish yopiladi.",
    )
    registration_deadline = models.DateTimeField(
        verbose_name="Ro'yxatdan o'tish muddati",
        help_text="Ishtirokchilar shu vaqtgacha ro'yxatdan o'tishi shart. Bo'sh qoldirilsa, boshlanish vaqti bilan teng deb hisoblanadi.",
        blank=True,
        null=True,
    )

    # ---------------------------------------------------------------------
    # Ishtirokchilar va cheklovlar
    # ---------------------------------------------------------------------
    max_participants = models.PositiveIntegerField(
        verbose_name="Maksimal ishtirokchilar soni",
        help_text="0 yoki bo'sh — chegara yo'q, istalgancha kishi qatnashishi mumkin.",
        default=0,
        blank=True,
    )
    questions_count = models.PositiveIntegerField(
        verbose_name="Savollar soni",
        help_text="Ushbu tanlovda ishtirokchiga taqdim etiladigan savollarning umumiy soni.",
        default=0,
    )
    pass_score_percent = models.PositiveIntegerField(
        verbose_name="O'tish balli (%)",
        help_text="Sertifikat olish yoki «muvaffaqiyatli» deb hisoblanish uchun zarur bo'lgan eng kam foiz (0-100).",
        default=50,
    )

    # Yopiq tanlov kaliti (Agar yozilsa musobaqa private bo'ladi)
    access_key = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Kirish kaliti",
        help_text="Faqat yopiq tanlovlar uchun. Kiritilsa, tanlov turi avtomat «Yopiq»ga o'zgaradi va shu kalitni bilganlar kira oladi.",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol",
        help_text="O'chirilsa, tanlov hech qayerda (status «ended» bo'lsa ham) foydalanuvchilarga ko'rsatilmaydi.",
    )

    # Tashkilotchi (Django Staff/Admin User)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contests',
        verbose_name="Tashkilotchi (admin)",
        help_text="Ushbu tanlovni yaratgan va boshqaradigan staff foydalanuvchi.",
    )
    intro_video = models.ForeignKey(
        Video, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tests",
        verbose_name="Kirish yoki qoidalar videosi",
        help_text="Ishtirokchilar tanlovga kirishdan oldin ko'radigan tushuntirish/qoidalar videosi (ixtiyoriy).",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Oxirgi o'zgartirilgan sana")

    class Meta:
        verbose_name = "🏆 Musobaqa"
        verbose_name_plural = "🏁 Musobaqalar"
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['status', 'start_time']),
            models.Index(fields=['type']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.title

    # ------------------------------------------------------------------
    # Hisoblanadigan xususiyatlar (properties)
    # ------------------------------------------------------------------
    @property
    def duration_minutes(self):
        """Turnir davomiyligini minutlarda hisoblash."""
        if self.end_time and self.start_time:
            diff = self.end_time - self.start_time
            return int(diff.total_seconds() / 60)
        return 0

    @property
    def is_registration_open(self):
        """Ro'yxatdan o'tish hali ochiqmi (boshlanmagan va muddat o'tmagan)."""
        now = timezone.now()
        deadline = self.registration_deadline or self.start_time
        return self.status == 'upcoming' and now <= deadline

    @property
    def can_join(self):
        """Foydalanuvchi hozir tanlovga (testga) kira oladimi."""
        now = timezone.now()
        return self.is_active and self.status == 'ongoing' and self.start_time <= now <= self.end_time

    @property
    def participants_count(self):
        """Hozircha ro'yxatdan o'tgan ishtirokchilar soni."""
        return self.registrations.count()

    @property
    def is_full(self):
        """Maksimal ishtirokchilar soniga yetib bo'lganmi."""
        if not self.max_participants:
            return False
        return self.participants_count >= self.max_participants

    @property
    def completion_rate_percent(self):
        """Ro'yxatdan o'tganlardan nechta foizi testni yakunlagani."""
        total = self.participants_count
        if not total:
            return 0
        completed = self.registrations.filter(status=ContestRegistration.Status.COMPLETED).count()
        return round((completed / total) * 100, 1)

    # ------------------------------------------------------------------
    # Validatsiya va saqlash
    # ------------------------------------------------------------------
    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Tugash vaqti boshlanish vaqtidan oldin bo'lishi mumkin emas!")
        if self.registration_deadline and self.start_time and self.registration_deadline > self.start_time:
            raise ValidationError("Ro'yxatdan o'tish muddati tanlov boshlanishidan keyin bo'lishi mumkin emas!")
        if not (0 <= self.pass_score_percent <= 100):
            raise ValidationError("O'tish balli 0 dan 100 gacha bo'lishi kerak!")

    def save(self, *args, **kwargs):
        # Slug bo'sh bo'lsa, nomdan avtomat hosil qilamiz
        if not self.slug:
            base_slug = slugify(self.title)[:190]
            slug_candidate = base_slug
            counter = 1
            while Contest.objects.exclude(pk=self.pk).filter(slug=slug_candidate).exists():
                counter += 1
                slug_candidate = f"{base_slug}-{counter}"
            self.slug = slug_candidate

        # Kalit kiritilganiga qarab turnir turini avtomat belgilash
        if self.access_key and self.access_key.strip():
            self.type = 'private'
        else:
            self.type = 'open'
            self.access_key = None

        # Vaqtga qarab statusni avtomat yangilash
        now = timezone.now()
        if now < self.start_time:
            self.status = 'upcoming'
        elif now <= self.end_time:
            self.status = 'ongoing'
        else:
            self.status = 'ended'

        super().save(*args, **kwargs)


class ContestPrize(models.Model):
    """Mukofotlar uchun alohida mustaqil jadval."""

    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name='prizes',
        verbose_name="Musobaqa",
        help_text="Mukofot tegishli bo'lgan tanlov.",
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Mukofot nomi",
        help_text="Masalan: Noutbuk, Sertifikat, Oltin medal.",
    )
    rank_target = models.PositiveIntegerField(
        verbose_name="Munosib o'rin",
        help_text="Ushbu mukofot nechanchi o'rin egasiga beriladi (masalan: 1).",
        validators=[MinValueValidator(1)],
    )
    monetary_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Taxminiy qiymati (so'm)",
        help_text="Mukofotning pul ko'rinishidagi taxminiy qiymati. Statistik hisobotlar uchun, ixtiyoriy.",
        blank=True,
        null=True,
    )
    image = models.ImageField(
        upload_to='contests/prizes/%Y/%m/',
        verbose_name="Mukofot rasmi",
        help_text="Mukofotning rasmi (masalan, noutbuk yoki sertifikat namunasi).",
        blank=True,
        null=True,
    )
    description = MDTextField(
        blank=True,
        null=True,
        verbose_name="Qo'shimcha tavsif",
        help_text="Mukofot haqida batafsil ma'lumot, shartlar yoki izohlar.",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prizes',
        verbose_name="Qo'shgan admin",
        help_text="Mukofotni tizimga kiritgan staff foydalanuvchi.",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan sana")

    class Meta:
        verbose_name = "🎁 Mukofot"
        verbose_name_plural = "🎁 Mukofotlar"
        ordering = ['rank_target']
        unique_together = ['contest', 'rank_target']

    def __str__(self):
        return f"{self.contest.title} - {self.title} ({self.rank_target}-o'rin)"


class ContestRegistration(models.Model):
    """Tanlovga ro'yxatdan o'tish va seans natijalari jadvali."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Jarayonda"
        COMPLETED = "completed", "Yakunlangan"
        EXPIRED = "expired", "Muddati o'tgan"
        DISQUALIFIED = "disqualified", "Diskvalifikatsiya qilingan"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Identifikator",
        help_text="Har bir seans uchun noyob UUID identifikator.",
    )
    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        related_name='contest_registrations',
        verbose_name="Ishtirokchi",
        help_text="Tanlovga ro'yxatdan o'tgan foydalanuvchi (Telegram bot foydalanuvchisi).",
    )
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="registrations",
        db_index=True,
        verbose_name="Tegishli musobaqa",
        help_text="Ushbu ro'yxatdan o'tish qaysi tanlovga tegishli ekanligi.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        db_index=True,
        verbose_name="Holati",
        help_text="Seans hozirgi holati: jarayonda, yakunlangan, muddati o'tgan yoki diskvalifikatsiya qilingan.",
    )

    # Statistika parametrlari
    correct_count = models.PositiveIntegerField(
        "To'g'ri javoblar soni",
        default=0,
        help_text="Ishtirokchi to'g'ri javob bergan savollar soni.",
    )
    wrong_count = models.PositiveIntegerField(
        "Noto'g'ri javoblar soni",
        default=0,
        help_text="Ishtirokchi noto'g'ri javob bergan savollar soni.",
    )
    unanswered_count = models.PositiveIntegerField(
        "Javobsiz qoldirilgan savollar soni",
        default=0,
        help_text="Ishtirokchi umuman javob bermagan savollar soni.",
    )
    time_spent_seconds = models.PositiveIntegerField(
        "Sarflangan vaqt (soniya)",
        default=0,
        help_text="Ishtirokchi testni yechishga sarflagan umumiy vaqt, soniyalarda.",
    )

    # Reyting uchun asosiy maydonlar
    total_xp_earned = models.PositiveIntegerField(
        "Ushbu musobaqa jami XP balli",
        default=0,
        db_index=True,
        help_text="Foydalanuvchi ushbu testdan ishlagan toza XP ballari. Reyting shu maydon bo'yicha tuziladi.",
    )
    rank = models.PositiveIntegerField(
        "Musobaqadagi o'rni",
        null=True,
        blank=True,
        db_index=True,
        help_text="Tanlov yakunlangach hisoblangan, ushbu ishtirokchining umumiy reytingdagi o'rni (1 — birinchi o'rin).",
    )
    ip_address = models.GenericIPAddressField(
        "IP manzil",
        null=True,
        blank=True,
        help_text="Ishtirokchi testni boshlagan paytdagi IP manzili. Firibgarlikni aniqlash uchun foydali.",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='contests_registration',
        verbose_name="Qayd etgan admin",
        help_text="Ushbu yozuvni tizimga kiritgan/nazorat qiluvchi staff foydalanuvchi.",
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Boshlangan sana",
        help_text="Foydalanuvchi tanlovga ro'yxatdan o'tib, testni boshlagan vaqt.",
    )
    xp_awarded = models.PositiveIntegerField(default=0)

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Yakunlangan sana",
        help_text="Test yakunlangan yoki muddati tugagan payt. Avtomat to'ldiriladi.",
    )


    class Meta:
        unique_together = ['user', 'contest']
        ordering = ['rank', '-total_xp_earned']
        verbose_name = "🪪 Ro'yxatdan o'tish"
        verbose_name_plural = "👥 Ro'yxatdan o'tganlar"
        indexes = [
            models.Index(fields=['contest', 'rank']),
            models.Index(fields=['contest', '-total_xp_earned']),
        ]

    def __str__(self):
        user_identifier = getattr(self.user, 'username', None) or getattr(self.user, 'telegram_id', "Noma'lum")
        return f"{user_identifier} - {self.contest.title} (+{self.total_xp_earned} XP)"

    # ------------------------------------------------------------------
    # Hisoblanadigan xususiyatlar
    # ------------------------------------------------------------------
    @property
    def total_questions_answered(self):
        """Javob berilgan savollarning umumiy soni (to'g'ri + noto'g'ri)."""
        return self.correct_count + self.wrong_count

    @property
    def accuracy_percent(self):
        """To'g'ri javoblarning foizi, faqat javob berilgan savollar asosida."""
        total = self.total_questions_answered
        if not total:
            return 0
        return round((self.correct_count / total) * 100, 1)

    @property
    def medal(self):
        """1, 2, 3-o'rinlar uchun medal emoji qaytaradi, aks holda bo'sh string."""
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        return medals.get(self.rank, "")

    def save(self, *args, **kwargs):
        """Musobaqa/Seans yopilganda vaqtni avtomat belgilash."""
        if self.status in [self.Status.COMPLETED, self.Status.EXPIRED, self.Status.DISQUALIFIED] and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "contest"],
                condition=models.Q(xp_awarded__gt=0),
                name="unique_xp_award_per_user_contest",
            )
        ]