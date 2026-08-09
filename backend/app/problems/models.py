from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from mdeditor.fields import MDTextField
from baseuser.models import BaseUser
from video.models import Video
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

from django.contrib.postgres.fields import ArrayField
from centers.models import CenterScopedMixin


# -------------------- Category --------------------
class Category(models.Model):
    name = models.CharField(
        max_length=250, 
        unique=True, 
        verbose_name="Kategoriya nomi", 
        help_text="Masalalar guruhlanadigan kategoriya nomi (masalan: Algoritmlar)"
    )
    slug = models.SlugField(
        max_length=500, 
        unique=True, 
        verbose_name="Slug", 
        help_text="URL manzili uchun avtomatik hosil bo'ladi"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name="Yaratuvchi admin"
    )
    class Meta:
        ordering = ["name"]
        verbose_name = "📁 Kategoriya"
        verbose_name_plural = "📂 Kategoriyalar"

    def __str__(self):
        return self.name


# -------------------- Tags --------------------
class Tags(models.Model):
    name = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Teg nomi", 
        help_text="Qidiruvni osonlashtirish uchun kalit so'z (masalan: arrays, string)"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tags',
        verbose_name="Yaratuvchi admin"
    )
    
    class Meta:
        ordering = ["name"]
        verbose_name = "🏷️ Teg"
        verbose_name_plural = "🔖 Teglar"

    def __str__(self):
        return self.name




class Language(models.Model):
    name = models.CharField(
        max_length=250, 
        unique=True, 
        verbose_name="Til nomi", 
        help_text="Piston API qabul qiladigan til nomi (masalan: python, csharp, cpp)"
    )
    version = models.CharField(
        max_length=50,
        verbose_name="Versiyasi",
        help_text="Piston API dagi aniq versiyasi (masalan: 3.12.0, 10.2.0)"
    )
    # null=True (Katta harf bilan) va ArrayField to'g'rilandi
    aliases = ArrayField(
        models.CharField(max_length=50), 
        blank=True, 
        null=True,
        verbose_name="Taxalluslar"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "💻 Dasturlash tili"
        verbose_name_plural = "⚙️ Dasturlash tillari"

    def __str__(self):
        return f"{self.name} ({self.version})" # Admin panelda versiyasi bilan ko'rinishi qulay



# -------------------- Problem --------------------
class Problem(CenterScopedMixin, models.Model):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Oson"
        MEDIUM = "medium", "O'rtacha"
        HARD = "hard", "Qiyin"

    DEFAULT_XP_BY_DIFFICULTY = {
        Difficulty.EASY: 10,
        Difficulty.MEDIUM: 25,
        Difficulty.HARD: 50,
    }
    
    lesson = models.ForeignKey(
        "courses.Lesson", 
        on_delete=models.SET_NULL, 
        related_name="problems", 
        null=True, 
        blank=True,
        verbose_name="Darslik",
        help_text="Ushbu masala qaysi darsga tegishli ekanligini tanlang."
    )
    tags = models.ManyToManyField(
        Tags, 
        related_name="problems", 
        blank=True,  # Faqat blank=True qoladi
        verbose_name="Teglar",
        help_text="Masalaga mos keluvchi teglar yoki mavzularni kiriting."
    )
    language = models.ManyToManyField(
        Language, 
        related_name="problems", 
        blank=True,  # Faqat blank=True qoladi
        verbose_name="Ruxsat berilgan tillar", 
        help_text="Ushbu masalani qaysi dasturlash tillarida yechish mumkin?"
    )

    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        related_name="problems", 
        null=True, 
        blank=True,
        verbose_name="Kategoriya",
        help_text="Masala qaysi ruknga tegishli?"
    )
    title = models.CharField(
        max_length=200, 
        verbose_name="Masala sarlavhasi", 
        help_text="Masalaning qisqa va aniq nomi."
    )
    slug = models.SlugField(
        max_length=250, 
        blank=True, 
        unique=True, 
        verbose_name="Slug", 
        help_text="URL manzili uchun avtomatik shakllanadi."
    )
    description = MDTextField(
        verbose_name="Masala sharti (Matn)", 
        help_text="Markdown formatida masalaning to'liq shartini yozing."
    )
    is_active = models.BooleanField(
        default=True, 
        db_index=True, 
        verbose_name="Aktivlik holati", 
        help_text="Saytda talabalarga ko'rinishi yoki yashirin bo'lishi."
    )
    difficulty = models.CharField(
        max_length=10, choices=Difficulty.choices, default=Difficulty.EASY,
        verbose_name="Qiyinchilik darajasi",
        help_text="Masalaning murakkablik darajasini belgilang."
    )
    solution_video = models.ForeignKey(
        Video, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="problems",
        verbose_name="Yechim video tahlili",
        help_text="Masalaning kodli yoki g'oyaviy yechimi tushuntirilgan videoni biriktiring."
    )

    time_limit = models.IntegerField(
        default=2000,
        verbose_name="Vaqt cheklovi",
        help_text="Millisekundlarda belgilang (100 ms dan 3000 ms gacha). Piston API maksimal 3000 ms qabul qiladi. Masalan: 2000 = 2 sekund.",
        validators=[
            MinValueValidator(100, message="Vaqt cheklovi kamida 100 ms bo'lishi kerak."),
            MaxValueValidator(3000, message="Vaqt cheklovi Piston API limiti sababli 3000 ms dan oshmasligi kerak."),
        ]
    )

    memory_limit = models.IntegerField(
        default=256,
        verbose_name="Xotira cheklovi",
        help_text="Megabaytlarda belgilang (1 MB dan 512 MB gacha). Piston API xotira limitini qo'llab-quvvatlaydi. Masalan: 256 = 256 MB.",
        validators=[
            MinValueValidator(1, message="Xotira cheklovi kamida 1 MB bo'lishi kerak."),
            MaxValueValidator(512, message="Xotira cheklovi 512 MB dan oshmasligi kerak."),
        ]
    )
    likes_count = models.PositiveIntegerField(default=0, editable=False, verbose_name="Layklar soni")
    dislikes_count = models.PositiveIntegerField(default=0, editable=False, verbose_name="Dislayklar soni")
    xp = models.PositiveIntegerField(
        verbose_name="XP mukofoti",
        help_text=(
            "Ushbu masala birinchi marta to'g'ri (Accepted) yechilganda "
            "foydalanuvchiga beriladigan XP miqdori. Agar masala biror "
            "Contest doirasida yechilsa, bu qiymat ContestRegistration."
            "total_xp_earned ga FAQAT birinchi to'g'ri yechim uchun "
            "qo'shiladi (qayta yechilsa, qo'shimcha XP berilmaydi)." \
            "10<=xp<=100"
        ),
        default=10, validators=[MinValueValidator(10), MaxValueValidator(100)]
    )
    # yangi
    # Global statistika — barcha contestlar bo'yicha yig'iladi
    solved_count = models.PositiveIntegerField(default=0, verbose_name="Yechilgan marta")
    attempt_count = models.PositiveIntegerField(default=0, verbose_name="Urinishlar soni")
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='problems',
        verbose_name="Yaratuvchi admin"
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "💡 Masala"
        verbose_name_plural = "🧠 Masalalar"
        indexes = [
            models.Index(fields=["is_active", "difficulty"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    
    def clean(self):
        super().clean()
        if self.time_limit and self.time_limit > 3000:
            raise ValidationError({
                "time_limit": "Vaqt cheklovi 3000 ms dan oshmasligi kerak."
            })
       
        if self.memory_limit and self.memory_limit < 1:
            self.memory_limit = 1

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Problem.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        if not self.xp or self.xp == 0:
            xp_mapping = {
                'easy': 10,
                'medium': 25,
                'hard': 50,
            }
            self.xp = xp_mapping.get(self.difficulty, 10)

        super().save(*args, **kwargs)


# -------------------- Hint --------------------
class Hint(models.Model):
    problem = models.ForeignKey(
        Problem, 
        related_name="hints", 
        on_delete=models.CASCADE, 
        verbose_name="Masala"
    )
    text = MDTextField(
        verbose_name="Yordam matni", 
        help_text="Talaba qiynalganda ko'rinadigan qisqa ko'rsatma yoki shama."
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hints',
        verbose_name="Yaratuvchi admin"
    )
    class Meta:
        verbose_name = "🔑 Yordam"
        verbose_name_plural = "💡 Yordamlar"

    def __str__(self):
        return f"Hint: {self.problem.title}"


# -------------------- Challenge --------------------
class Challenge(models.Model):
    problem = models.ForeignKey(
        Problem, 
        related_name="challenges", 
        on_delete=models.CASCADE, 
        verbose_name="Masala"
    )
    text = MDTextField(
        verbose_name="Qo'shimcha shart", 
        help_text="Masalani yanada optimallashtirish uchun qo'shimcha vazifa (Follow-up)."
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='challenges',
        verbose_name="Yaratuvchi admin"
    )
    
    class Meta:
        verbose_name = "🎯 Topshiriq"
        verbose_name_plural = "⚔️ Topshiriqlar"

    def __str__(self):
        return f"Challenge: {self.problem.title}"


# -------------------- Function --------------------
class Function(models.Model):
    language = models.ForeignKey(
        Language, 
        on_delete=models.CASCADE, 
        verbose_name="Dasturlash tili"
    )
    problem = models.ForeignKey(
        Problem, 
        related_name="functions", 
        on_delete=models.CASCADE, 
        verbose_name="Masala"
    )
    function = models.TextField(
        verbose_name="Funksiya shabloni", 
        help_text="Foydalanuvchi kod yozishni boshlashi uchun tayyor funksiya strukturasi (LeetCode kabi)."
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='functions',
        verbose_name="Yaratuvchi admin"
    )
    class Meta:
        unique_together = ("problem", "language")
        verbose_name = "🧩 Funksiya shabloni"
        verbose_name_plural = "🛠️ Funksiya shablonlari"

    def __str__(self):
        return f"{self.language.name} - {self.problem.title}"


# -------------------- ExecutionTestCase --------------------
class ExecutionTestCase(models.Model):
    problem = models.ForeignKey(
        Problem, 
        related_name="execution_problem", 
        on_delete=models.CASCADE, 
        verbose_name="Masala"
    )
    language = models.ForeignKey(
        Language, 
        related_name="execution_language", 
        on_delete=models.CASCADE, 
        verbose_name="Dasturlash tili"
    )
    top_code = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="Tepa qism kodi (Header)", 
        help_text="Foydalanuvchi kodiga yashirincha tepadan qo'shiladigan kutubxonalar yoki driver kod."
    )
    bottom_code = models.TextField(
        verbose_name="Pastki qism kodi (Footer/Main)", 
        help_text="Foydalanuvchi yozgan funksiyani chaqirib, test qiluvchi main kod qismi."
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name="Yaratuvchi admin"
    )

    class Meta:
        unique_together = ("problem", "language")
        verbose_name = "🚀 Kod testi"
        verbose_name_plural = "⚙️ Kod testlari"

    def __str__(self):
        return f"{self.language.name} - {self.problem.title}"


# -------------------- TestCase --------------------

class TestCase(models.Model):
    problem = models.ForeignKey(
        Problem, 
        related_name="test_cases", 
        on_delete=models.CASCADE, 
        verbose_name="Masala"
    )
    input_txt = models.TextField(
        verbose_name="Test Input", 
        help_text="Yashirin tekshiruv uchun kirish ma'lumotlari."
    )
    output_txt = models.TextField(
        verbose_name="Test Output", 
        help_text="Ushbu kirish ma'lumotiga mos keluvchi aniq to'g'ri javob."
    )
    explanation = models.TextField(
        verbose_name="Izoh", 
        blank=True, 
        null=True,
        help_text="Ushbu test qanday ishlashi haqida ixtiyoriy tushuntirish."
    )
    is_sample = models.BooleanField(
        default=False,
        verbose_name="Namuna testmi?",
        help_text="Agar true bo'lsa, bu test foydalanuvchiga masala shartida ko'rinadi."
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Tartib raqami",
        help_text="Testlarni ketma-ketlikda tekshirish uchun tartib raqam."
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_test_cases',
        verbose_name="Yaratuvchi admin"
    )


    class Meta:
        # Indeksni 'problem' va 'order' bo'yicha birga qilish qidiruvni juda tezlashtiradi
        indexes = [
            models.Index(fields=["problem", "order"]),
            models.Index(fields=["is_sample"]),
        ]
        ordering = ["order", "id"]
        verbose_name = "🧪 Test case"
        verbose_name_plural = "✅ Test caselar"

    def __str__(self):
        prefix = "Namuna" if self.is_sample else "Yashirin"
        return f"{self.problem.title} | {prefix} #{self.order if self.order else self.id}"

    def clean(self):
        """Matnlarning boshidagi va oxiridagi keraksiz probel/enterlarni tozalash"""
        super().clean()
        if self.input_txt:
            self.input_txt = self.input_txt.strip()
        if self.output_txt:
            self.output_txt = self.output_txt.strip()



# -------------------- Like --------------------
class Like(models.Model):
    problem = models.ForeignKey(
        Problem, 
        on_delete=models.CASCADE, 
        related_name="problem_likes", 
        verbose_name="Masala"
    )
    user = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE, 
        related_name="user_likes", 
        verbose_name="Foydalanuvchi"
    )
    like_or_dislike = models.BooleanField(
        default=True, 
        verbose_name="Reaksiya turi", 
        help_text="Belgilansa 👍 (Like), belgilanmasa 👎 (Dislike) hisoblanadi."
    )

    class Meta:
        unique_together = ("problem", "user")
        verbose_name = "👍 Reaksiya"
        verbose_name_plural = "👍 Reaksiyalar"

    def __str__(self):
        status = "Like" if self.like_or_dislike else "Dislike"
        return f"User {self.user.telegram_id} - {self.problem.title} ({status})"
