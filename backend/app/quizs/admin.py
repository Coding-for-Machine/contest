from django.contrib import admin
from django.db import models
from django.db.models import Count
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import display
from .models import (
    Test, Question, Choice, TestSession, 
    UserAnswer, CertificateTemplate, Certificate, UserRank
)

# ─────────────────────────────────────────────
#  INLINES (Ichma-ich tahrirlash komponentlari)
# ─────────────────────────────────────────────

class ChoiceInline(TabularInline):
    """Savol ichida javob variantlarini chiqarish"""
    model = Choice
    extra = 4
    tab = True


class QuestionInline(StackedInline):
    """Test ichida savollarni blok shaklida ko'rsatish"""
    model = Question
    extra = 1
    tab = True
    show_change_link = True
    fields = ["text", "difficulty", "xp", "image", "order"]


class UserAnswerInline(TabularInline):
    """Sessiya ichida talaba bergan javoblar ro'yxati (Faqat ko'rish uchun)"""
    model = UserAnswer
    extra = 0
    readonly_fields = ["question", "choice", "created_at"]
    can_delete = False


# ─────────────────────────────────────────────
#  ADMIN CLASSES (Asosiy boshqaruv panellari)
# ─────────────────────────────────────────────

@admin.register(UserRank)
class UserRankAdmin(ModelAdmin):
    """Foydalanuvchilar reyting tizimi paneli"""
    list_display = ["user", "total_xp_display", "level_label", "updated_at"]
    list_filter = ["level", "updated_at"]
    search_fields = ["user__username", "user__email", "user__first_name", "user__last_name"]

    @display(description="Jami Ball", header=True)
    def total_xp_display(self, obj):
        return [f"✨ {obj.total_xp} XP", "To'plangan ball"]

    @display(description="Unvon / Daraja", label={
        "beginner": "info",
        "bronze": "neutral",
        "silver": "none",
        "gold": "warning",
        "pro": "success",
    })
    def level_label(self, obj):
        return obj.get_level_display()


@admin.register(Test)
class TestAdmin(ModelAdmin):
    """Mustaqil va Kurs ichidagi Testlar paneli"""
    list_display = ["title", "get_context_display", "duration_minutes", "min_pass_label", "is_active_status"]
    
    # ✅ TUZATILDI: 'lesson__course' xatosi olib tashlandi, o'rniga to'g'ri bog'liqliklar qo'yildi
    list_filter = ["is_active", "lesson", "deadline", "created_at"]
    
    search_fields = ["title", "lesson__title", "lesson__course__title"]
    inlines = [QuestionInline]

    @display(description="Turi / Joylashuvi")
    def get_context_display(self, obj):
        if obj.lesson:
            return f"📖 {obj.lesson.course.title} -> {obj.lesson.title}"
        return "🌍 Mustaqil Umumiy Test"

    @display(description="O'tish chegarasi", label=True)
    def min_pass_label(self, obj):
        return f"🎯 {obj.min_pass_percentage}%"

    @display(description="Holat", label=True)
    def is_active_status(self, obj):
        return ("Faol", "success") if obj.is_active else ("Nofaol", "danger")


@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    """Savollar va ularga mos variantlar boshqaruvi"""
    list_display = ["display_header", "get_destination", "difficulty_label", "xp_display", "choices_count_display"]
    list_filter = ["difficulty", "test", "problem", "created_at"]
    search_fields = ["text"]
    inlines = [ChoiceInline]
    
    def get_queryset(self, request):
        """N+1 SQL so'rovlar muammosini oldini olish uchun optimizatsiya (Annotate)"""
        qs = super().get_queryset(request)
        return qs.annotate(collected_choices=Count('choices'))

    @display(header=True)
    def display_header(self, obj):
        return [obj.text[:60] + "..." if len(obj.text) > 60 else obj.text, f"ID: {obj.id} | Tartib: {obj.order}"]

    @display(description="Bog'langan Manba")
    def get_destination(self, obj):
        if obj.test: return f"📝 Test: {obj.test.title}"
        if obj.problem: return f"💻 Problem #{obj.problem_id}"
        return "⚠️ Bog'lanmagan"

    @display(description="Qiyinchilik", label={
        "easy": "success",
        "medium": "warning",
        "hard": "danger",
    })
    def difficulty_label(self, obj):
        return obj.get_difficulty_display()

    @display(description="Qiymati")
    def xp_display(self, obj):
        return f"{obj.xp} XP"

    @display(description="Variantlar")
    def choices_count_display(self, obj):
        return f"{obj.collected_choices} ta variant"


@admin.register(TestSession)
class TestSessionAdmin(ModelAdmin):
    """Talabalarning jonli test topshirish sessiyalari logi"""
    list_display = ["user", "get_target_display", "score_display", "percentage_label", "total_xp_earned", "status_label", "started_at"]
    list_filter = ["status", "test", "started_at"]
    search_fields = ["user__username", "user__email", "test__title", "problem__id"]
    readonly_fields = ["score", "total_questions", "percentage", "total_xp_earned", "certificate_id", "started_at", "ended_at", "finish"]
    inlines = [UserAnswerInline]
    
    @display(description="Imtihon / Mashq", header=True)
    def get_target_display(self, obj):
        if obj.test: return [f"📝 {obj.test.title}", "Test imtihoni"]
        if obj.problem: return [f"💻 Problem #{obj.problem_id}", "Darslik mashqi"]
        return ["Noma'lum", "-"]

    @display(description="Natija (To'g'ri / Jami)", header=True)
    def score_display(self, obj):
        return [f"{obj.score} / {obj.total_questions}", "To'g'ri topildi"]

    @display(description="Foiz", label=True)
    def percentage_label(self, obj):
        if obj.percentage >= 80: return (f"{obj.percentage}%", "success")
        if obj.percentage >= 50: return (f"{obj.percentage}%", "warning")
        return (f"{obj.percentage}%", "danger")

    @display(description="Sessiya Holati", label={
        "in_progress": "info",
        "completed": "success",
        "expired": "danger",
    })
    def status_label(self, obj):
        return obj.get_status_display()


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(ModelAdmin):
    """Sertifikatlar uchun vizual HTML dizayn shablonlari paneli"""
    list_display = ["name", "get_bound_to", "min_percentage_label"]
    search_fields = ["name", "course__title", "test__title"]
    
    # ✅ HTML shablon maydonini Unfold-ning maxsus vizual (WYSIWYG) muharririga o'tkazish
    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }

    @display(description="Sertifikat turi")
    def get_bound_to(self, obj):
        if obj.course: return f"🎓 Kurs uchun: {obj.course.title}"
        if obj.test: return f"📝 Mustaqil test uchun: {obj.test.title}"
        return "⚠️ Sozlanmagan"

    @display(description="Minimal o'tish foizi", label=True)
    def min_percentage_label(self, obj):
        return f"{obj.min_percentage}%"


@admin.register(Certificate)
class CertificateAdmin(ModelAdmin):
    """Talabalarga berilgan haqiqiy sertifikatlar arxivi"""
    list_display = ["user", "certificate_code", "get_source_display", "view_pdf_button", "issued_at"]
    list_filter = ["issued_at", "template"]
    search_fields = ["user__username", "user__email", "certificate_code", "course__title", "test_session__test__title"]
    readonly_fields = ["certificate_code", "qr_code_image", "pdf_file", "issued_at"]

    @display(description="Berilish Asosi")
    def get_source_display(self, obj):
        if obj.course:
            return f"🎓 Kurs: {obj.course.title}"
        return f"📝 Test: {obj.test_session.test.title}"

    @display(description="PDF Fayl")
    def view_pdf_button(self, obj):
        if obj.pdf_file:
            return admin.utils.format_html(
                '<a href="{}" target="_blank" class="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 rounded text-xs font-semibold inline-block">📄 PDF-ni ochish</a>',
                obj.pdf_file.url
            )
        return "Generatsiya qilinmoqda..."


@admin.register(Choice)
class ChoiceAdmin(ModelAdmin):
    """Javob variantlarini qidirish va boshqarish paneli"""
    list_display = ["text", "question", "is_correct", "order"]
    list_filter = ["is_correct"]
    search_fields = ["text", "question__text"]


@admin.register(UserAnswer)
class UserAnswerAdmin(ModelAdmin):
    """Talaba loglarini alohida tekshirish paneli"""
    list_display = ["session", "question", "choice", "created_at"]
    search_fields = ["session__user__username", "question__text"]
