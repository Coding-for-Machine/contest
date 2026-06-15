from django.contrib import admin
from django.db import models
from django.utils.html import format_html

# ✨ Django Unfold Kutubxonasidan Importlar
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import display

from .models import Problem, Category, Tags, TestCase, ExecutionTestCase, Function, Language, Examples, Like

# ─────────────────────────────────────────────
#  INLINES (Ichma-ich tahrirlash komponentlari)
# ─────────────────────────────────────────────

class ExecutionTestCaseInlineAdmin(TabularInline):
    model = ExecutionTestCase
    extra = 1
    tab = True  # Unfold panelida alohida vizual tab ko'rinishiga o'tkazish


class FunctionInlineAdmin(TabularInline):
    model = Function
    extra = 1
    tab = True


class ExamplesInlineAdmin(StackedInline):
    model = Examples
    extra = 1
    tab = True
    # Inlinedagi TextField maydonlariga ham WYSIWYG muharririni ulaymiz
    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }

# ─────────────────────────────────────────────
#  ADMIN CLASSES (Asosiy boshqaruv panellari)
# ─────────────────────────────────────────────

@admin.register(Problem)
class ProblemAdmin(ModelAdmin):
    """LeetCode uslubidagi masalalar boshqaruv paneli"""
    list_display = ["id", "display_title", "difficulty_label", "created_at_display", "updated_at_display"]
    list_filter = ["difficulty", "category"]
    search_fields = ["title", "description"]
    prepopulated_fields = {"slug": ("title",)}
    list_per_page = 20
    
    # ⚡ N+1 muammosini oldini olish uchun kategoriya munosabatini optimallashtiramiz
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category")
    
    # 📝 Masala ichidagi barcha TextField (tavsif) maydonlarini chiroyli editorga almashtirish
    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }
    
    inlines = [ExamplesInlineAdmin, FunctionInlineAdmin, ExecutionTestCaseInlineAdmin]

    # --- Unfold Vizual Formatlari ---
    @display(description="Masala nomi", header=True)
    def display_title(self, obj):
        return [obj.title, f"Slug: {obj.slug}"]

    @display(description="Qiyinchilik", label={
        "easy": "success",
        "medium": "warning",
        "hard": "danger",
    })
    def difficulty_label(self, obj):
        return obj.get_difficulty_display()

    @display(description="Yaratilgan")
    def created_at_display(self, obj):
        return obj.created_at.strftime("%d.%m.%Y %H:%M")

    @display(description="Yangilangan")
    def updated_at_display(self, obj):
        return obj.updated_at.strftime("%d.%m.%Y %H:%M")


@admin.register(Language)
class LanguageAdmin(ModelAdmin):
    list_display = ["id", "name", "slug", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["id", "name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(TestCase)
class TestCaseAdmin(ModelAdmin):
    list_display = ["id", "problem", "short_input", "short_output"]
    list_filter = ["problem"]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("problem")
        
    # Test keyslari uchun ham katta matn muharriri (Wysiwyg) yuklaymiz
    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }

    @display(description="Kirish ma'lumoti (Input)")
    def short_input(self, obj):
        return obj.input_txt[:50] + "..." if len(obj.input_txt) > 50 else obj.input_txt

    @display(description="Chiqish ma'lumoti (Output)")
    def short_output(self, obj):
        return obj.output_txt[:50] + "..." if len(obj.output_txt) > 50 else obj.output_txt


@admin.register(ExecutionTestCase)
class ExecutionTestCaseAdmin(ModelAdmin):
    list_display = ["id", "problem", "language"]
    list_select_related = ["problem", "language"]


@admin.register(Function)
class FunctionAdmin(ModelAdmin):
    list_display = ["id", "problem", "language", "function"]
    list_per_page = 20
    list_select_related = ["problem", "language"]
    
    # Kod shablonlari uchun matn muharriri
    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }


@admin.register(Tags)
class TagsAdmin(ModelAdmin):
    list_display = ["id", "name"]


@admin.register(Like)
class LikeAdmin(ModelAdmin):
    list_display = ("id", "problem", "user", "status_label")
    list_filter = ("like_or_dislike",)
    search_fields = ("problem__title", "user__username") 
    list_select_related = ("problem", "user")

    @display(description="Munosabat", label={
        True: "success",    # Like bosilsa yashil chiroq
        False: "danger",    # Dislike bosilsa qizil chiroq
    })
    def status_label(self, obj):
        return "Like" if obj.like_or_dislike else "Dislike"
