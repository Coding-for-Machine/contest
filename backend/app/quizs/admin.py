import json
from django.contrib import admin
from django.db import models
from django.db.models import Count
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline, StackedInline
# from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import display
from mdeditor.widgets import MDEditorWidget 

from .models import (
    Test, Question, Choice, TestSession, 
    UserResponse, CertificateTemplate, UserRank, Certificate
)


# ─────────────────────────────────────────────
#  INLINES
# ─────────────────────────────────────────────

class ChoiceInline(TabularInline):
    model = Choice
    extra = 4
    tab = True
    # 📝 Javob variantlari matni uchun WYSIWYG editor
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }


class QuestionInline(StackedInline):
    model = Question
    extra = 1
    tab = True
    show_change_link = True
    fields = ["text", "difficulty", "xp", "order"]
    # 📝 Test ichida savollarni tezkor yaratishda ham WYSIWYG ishlasa qulay bo'ladi
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }
@admin.register(Certificate)
class CertificateAdmin(ModelAdmin):
    pass

class UserResponseInline(TabularInline):
    model = UserResponse
    extra = 0
    readonly_fields = ["question", "selected_choice", "get_is_correct"]
    can_delete = False
    tab = True
    
    def has_add_permission(self, request, obj=None):
        return False

    @display(description="To'g'riligi")
    def get_is_correct(self, obj):
        if not obj.selected_choice:
            return "Javob berilmagan"
        return "To'g'ri" if obj.selected_choice.is_correct else "Xato"


# ─────────────────────────────────────────────
#  ADMIN CLASSES
# ─────────────────────────────────────────────

@admin.register(UserRank)
class UserRankAdmin(ModelAdmin):
    list_display = ["user", "total_xp_display", "level_label", "updated_at"]
    list_filter = ["level", "updated_at"]
    search_fields = ["user__username", "user__phone", "user__full_name"]
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    @display(description="Jami Ball", header=True)
    def total_xp_display(self, obj):
        return [f"✨ {obj.total_xp} XP", "To'plangan umumiy ball"]

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
    list_display = [
        "title", "get_context_display", "duration_minutes", 
        "penalty_label", "min_pass_label", "time_status", "is_active_status"
    ]
    list_filter = ["is_active", "start_time", "end_time", "created_at"]
    search_fields = ["title", "lesson__title", "lesson__course__title"]
    inlines = [QuestionInline]
    
    # 📝 Agar test modelida qandaydir qo'shimcha TextField bo'lsa editor ishlaydi
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("lesson__modul__course")

    @display(description="Turi / Joylashuvi")
    def get_context_display(self, obj):
        if obj.lesson:
            if obj.lesson.modul and obj.lesson.modul.course:
                return f"📖 {obj.lesson.modul.course.title} ↳ {obj.lesson.title}"
            return f"📖 {obj.lesson.title}"
        return "🌍 Mustaqil Umumiy Test"

    @display(description="Jarima (K)")
    def penalty_label(self, obj):
        penalty_pct = int(getattr(obj, 'penalty_coefficient', 0) * 100)
        return f"⚠️ {penalty_pct}% jarima"

    @display(description="O'tish chegarasi")
    def min_pass_label(self, obj):
        return f"🎯 {obj.min_pass_percentage}%"

    @display(description="Muddati")
    def time_status(self, obj):
        start_str = obj.start_time.strftime("%d.%m.%Y %H:%M") if obj.start_time else "-"
        end_str = obj.end_time.strftime("%d.%m.%Y %H:%M") if obj.end_time else "-"
        return [f"⏳ {start_str}", f"⌛ {end_str}"]

    @display(description="Holat", label=True)
    def is_active_status(self, obj):
        return ("Faol", "success") if obj.is_active else ("Nofaol", "danger")


from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Question, Choice
from video.models import Video

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    list_display = ["id", "text_preview", "problem", "test", "difficulty"]
    list_filter = ["difficulty", "created_at"]
    search_fields = ["text"]
    inlines = [ChoiceInline]
    
    # Videoni qidirib topish select2 bo'lishi shart
    autocomplete_fields = ["explanation_video", "problem", "test"]
    
    # Pleyer maydonini faqat o'qish rejimi qilamiz
    readonly_fields = ["side_video_player"]

    # 🎛 Tahrirlash oynasini 2 ta ustunga (Grid) ajratamiz: Chapda formalar, O'ngda pleyer!
    fieldsets = (
        ("Asosiy sozlamalar", {
            "fields": (
                "text", 
                "difficulty", 
                "xp", 
                "order", 
                ("problem", "test"),  # Yonma-yon chiqishi uchun tuple
                "explanation_video",
                "side_video_player"   # 🎥 Pleyer shu yerda yonida chiqadi
            ),
        }),
    )

    # 🚀 YONMA-YON CHIQADIGAN JONLI PLEYER (Tailwind Grid bilan o'ng tomonga suriladi)
    def side_video_player(self, obj):
        video_url = ""
        video_title = "📺 Video tanlanmagan"
        
        if obj and obj.explanation_video:
            video_url = obj.explanation_video.mp4_url or (obj.explanation_video.video.url if obj.explanation_video.video else "")
            video_title = obj.explanation_video.title

        return format_html(
            '''
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4" style="margin-top: 15px; background: #f9fafb; padding: 15px; border-radius: 12px; border: 1px solid #e5e7eb;">
                <div class="md:col-span-2">
                    <h4 style="margin: 0 0 8px 0; color: #374151; font-weight: 600;">{title}</h4>
                    <video id="side-live-player" width="100%" height="auto" controls style="border-radius: 8px; background: #000; {display}">
                        <source src="{url}" type="video/mp4">
                    </video>
                    <p id="side-no-video" style="color: #9ca3af; font-style: italic; margin: 10px 0 0 0; {placeholder_display}">Savol uchun video tahlil biriktirilsa, pleyer shu yerda faollashadi.</p>
                </div>
                <div class="md:col-span-1" style="border-left: 1px solid #e5e7eb; padding-left: 15px; display: flex; flex-direction: column; justify-content: center;">
                    <span style="font-size: 12px; color: #6b7280; font-weight: bold; text-transform: uppercase;">Holat:</span>
                    <p style="font-size: 14px; margin: 4px 0 0 0; color: #10b981; font-weight: 600;">{status_text}</p>
                </div>
            </div>
            ''',
            url=video_url,
            title=video_title,
            display="display: block;" if video_url else "display: none;",
            placeholder_display="display: none;" if video_url else "display: block;",
            status_text="✅ Biriktirilgan (Tayyor)" if video_url else "⏳ Video kutilmoqda"
        )
    side_video_player.short_description = "Video preview"

    # 🤖 AVTOMATIK TANLASH (Saqlashdan oldin Masala yoki Test videosini o'zi bog'lab ketadi)
    def save_model(self, request, obj, form, change):
        # Agar administrator videoni qo'lda tanlamagan bo'lsa, avtomat qidiramiz
        if not obj.explanation_video:
            # 1. Agar savol biror Masalaga (Problem) tegishli bo'lsa, masalaning videosini olamiz
            if obj.problem and obj.problem.solution_video:
                obj.explanation_video = obj.problem.solution_video
            # 2. Agar savol biror Testga tegishli bo'lsa, testning intro videosini olamiz
            elif obj.test and obj.test.intro_video:
                obj.explanation_video = obj.test.intro_video
                
        super().save_model(request, obj, form, change)

    @display(description="Savol matni")
    def text_preview(self, obj):
        return obj.text[:40] + "..." if len(obj.text) > 40 else obj.text

@admin.register(TestSession)
class TestSessionAdmin(ModelAdmin):
    list_display = [
        "user", "get_target_display", "score_display", 
        "stats_display", "status_label", "started_at"
    ]
    list_filter = ["status", "test", "started_at"]
    search_fields = ["user__username", "user__phone", "test__title"]
    
    # readonly_fields = [
    #     "id", "user", "test", "status", "score", 
    #     "correct_count", "wrong_count", "unanswered_count", 
    #     "started_at", "completed_at"
    # ]
    inlines = [UserResponseInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "test")
    
    @display(description="Imtihon", header=True)
    def get_target_display(self, obj):
        return [f"📝 {obj.test.title}", "Test imtihoni"]

    @display(description="Olimpiada Balli", header=True)
    def score_display(self, obj):
        return [f"📊 {obj.score} Ball", "Sof matematika natijasi"]

    @display(description="Statistika (C / W / U)")
    def stats_display(self, obj):
        return format_html(
            '<span style="color: #10b981;">💚 {} ta</span> / <span style="color: #ef4444;">❤️ {} ta</span> / <span style="color: #6b7280;">📁 {} ta</span>',
            getattr(obj, 'correct_count', 0),
            getattr(obj, 'wrong_count', 0),
            getattr(obj, 'unanswered_count', 0)
        )

    @display(description="Sessiya Holati", label={
        "in_progress": "info",
        "completed": "success",
        "expired": "danger",
    })
    def status_label(self, obj):
        return obj.get_status_display()

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(ModelAdmin):
    # Olib tashlangan "min_percentage" list_display'dan ham o'chirildi
    list_display = ["name", "organization_name", "mentor_name"]
    search_fields = ["name", "mentor_name", "organization_name"]
    
    # Guruhlar (Fieldsets) ichidan ham o'chirilgan maydonlar olib tashlandi
    fieldsets = [
        ("Asosiy sozlamalar", {
            "fields": ["name"]
        }),
        ("Kompaniya (Platforma) ma'lumotlari", {
            "fields": ["organization_name", "verify_domain", "logo_image"]
        }),
        ("Sertifikat matnlari", {
            "fields": ["congratulation_text"]
        }),
        ("Mentor (O'qituvchi) ma'lumotlari", {
            "fields": ["mentor_name", "mentor_status", "mentor_signature", "illustration_image"]
        }),
    ]
