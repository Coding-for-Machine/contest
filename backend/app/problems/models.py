from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from baseuser.models import BaseUser
from contests.models import Contest
from courses.models import TimeStampedModel


# -------------------- Category --------------------
class Category(models.Model):
    name = models.CharField(max_length=250, unique=True)
    slug = models.SlugField(max_length=500, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "📁 Kategoriya"
        verbose_name_plural = "📂 Kategoriyalar"

    def __str__(self):
        return self.name


# -------------------- Tags --------------------
class Tags(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "🏷️ Teg"
        verbose_name_plural = "🔖 Teglar"

    def __str__(self):
        return self.name


# -------------------- Language --------------------
class Language(TimeStampedModel):
    name = models.CharField(max_length=250, unique=True)
    slug = models.SlugField(blank=True, null=True, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "💻 Dasturlash tili"
        verbose_name_plural = "⚙️ Dasturlash tillari"

    def __str__(self):
        return self.name


# -------------------- Problem --------------------
class Problem(TimeStampedModel):
    DIFFICULTIES = [
        ('easy', 'Oson'),
        ('medium', "O'rtacha"),
        ('hard', 'Qiyin'),
    ]
    
    PROBLEM_TYPES = [
        ('darslik', 'darslik'), 
        ('test', 'test'), 
        ('problem', 'problem')
    ]

    lesson = models.ForeignKey(
        "courses.Lesson", 
        on_delete=models.SET_NULL, 
        related_name="problems", 
        null=True, 
        blank=True
    )
    tags = models.ManyToManyField(Tags, related_name="problems", blank=True)
    language = models.ManyToManyField(Language, related_name="problems", blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, related_name="problems", null=True, blank=True
    )
    problem_type = models.CharField(
        max_length=50, 
        choices=PROBLEM_TYPES,
        default='problem', # TUZATILDI: False o'rniga default qiymat berildi
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, blank=True, unique=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTIES, default='easy')

    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name='problems',
        null=True,
        blank=True
    )
    xp = models.PositiveIntegerField(
        default=10, # TUZATILDI: validator bilan ziddiyatni yo'qotish uchun MinValueValidator(0) qilindi
        validators=[
            MinValueValidator(0), 
            MaxValueValidator(100)
        ],
        help_text=_(
            "Ushbu masalani yechgan foydalanuvchiga beriladigan ball (XP). "
            "Agar 0 qoldirilsa, qiyinchilikka qarab avtomat belgilanadi: "
            "Oson: 100, O'rtacha: 250, Qiyin: 500."
        ),
        verbose_name="Tajriba ochkosi (XP)"
    )

    time_limit = models.IntegerField(default=2000, null=True, blank=True, help_text="Millisekundlarda")
    memory_limit = models.IntegerField(default=256, null=True, blank=True, help_text="Megabaytlarda")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")

    class Meta:
        ordering = ["id"]
        verbose_name = "💡 Masala" # TUZATILDI: Takroriy Meta qatorlari o'chirildi
        verbose_name_plural = "🧠 Masalalar"
        indexes = [
            models.Index(fields=["is_active", "difficulty"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        if not self.xp or self.xp == 0:
            xp_mapping = {
                'easy': 10,
                'medium': 25,
                'hard': 50,
            }
            self.xp = xp_mapping.get(self.difficulty, 100)

        super().save(*args, **kwargs)


# -------------------- Hint --------------------
class Hint(models.Model):
    problem = models.ForeignKey(Problem, related_name="hints", on_delete=models.CASCADE)
    text = models.TextField()

    class Meta:
        verbose_name = "🔑 Yordam"
        verbose_name_plural = "💡 Yordamlar"

    def __str__(self):
        return f"Hint: {self.problem.title}"


# -------------------- Challenge --------------------
class Challenge(models.Model):
    problem = models.ForeignKey(Problem, related_name="challenges", on_delete=models.CASCADE)
    text = models.TextField()
    
    class Meta:
        verbose_name = "🎯 Topshiriq"
        verbose_name_plural = "⚔️ Topshiriqlar"

    def __str__(self):
        return f"Challenge: {self.problem.title}"


# -------------------- Examples --------------------
class Examples(models.Model):
    problem = models.ForeignKey(Problem, related_name="examples", on_delete=models.CASCADE)
    input_txt = models.TextField(help_text="Kirish ma'lumotlari, masalan: '[2,7,11,15]\\n9'")
    output_txt = models.TextField(help_text="Chiqish ma'lumotlari, masalan: '[0,1]'")
    explanation = models.TextField(help_text="Tushuntirish matni")

    class Meta:
        verbose_name = "📝 Misol"
        verbose_name_plural = "📋 Misollar"

    def __str__(self):
        return f"Example: {self.problem.title}"


# -------------------- Function --------------------
class Function(models.Model):
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, related_name="functions", on_delete=models.CASCADE)
    function = models.TextField()

    class Meta:
        unique_together = ("problem", "language")
        verbose_name = "🧩 Funksiya shabloni"
        verbose_name_plural = "🛠️ Funksiya shablonlari"

    def __str__(self):
        return f"{self.language.name} - {self.problem.title}"


# -------------------- ExecutionTestCase --------------------
class ExecutionTestCase(models.Model):
    problem = models.ForeignKey(Problem, related_name="execution_problem", on_delete=models.CASCADE)
    language = models.ForeignKey(Language, related_name="execution_language", on_delete=models.CASCADE)
    top_code = models.TextField(null=True, blank=True)
    bottom_code = models.TextField()

    class Meta:
        unique_together = ("problem", "language")
        verbose_name = "🚀 Kod testi"
        verbose_name_plural = "⚙️ Kod testlari"


# -------------------- TestCase --------------------
class TestCase(models.Model):
    problem = models.ForeignKey(Problem, related_name="test_cases", on_delete=models.CASCADE)
    input_txt = models.TextField(help_text="Test Input") # TUZATILDI: CharField dan TextField ga o'tkazildi
    output_txt = models.TextField(help_text="Chiqish Output") # TUZATILDI: CharField dan TextField ga o'tkazildi

    class Meta:
        indexes = [models.Index(fields=["problem"])]
        verbose_name = "🧪 Test case"
        verbose_name_plural = "✅ Test caselar"

    def __str__(self):
        return f"Test: {self.problem.title}"
    

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
        help_text="True = Like, False = Dislike"
    )

    class Meta:
        unique_together = ("problem", "user") # TUZATILDI: Bitta foydalanuvchi bitta masalaga faqat bir marta reaksiya bildira oladi
        verbose_name = "👍 Reaksiya"
        verbose_name_plural = "👍 Reaksiyalar"

    def __str__(self):
        status = "Like" if self.like_or_dislike else "Dislike"
        return f"{self.user.username} - {self.problem.title} ({status})"
