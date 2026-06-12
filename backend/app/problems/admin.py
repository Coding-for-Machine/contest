from django.contrib import admin
from django.utils.html import format_html
from .models import Problem, Category, Tags, TestCase, ExecutionTestCase, Function, Language, Examples, Like

# --- Inlines (Problem ichida boshqa modellarni ko'rsatish uchun) ---

class ExecutionTestCaseInlineAdmin(admin.TabularInline):
    model = ExecutionTestCase
    extra = 1

class FunctionInlineAdmin(admin.TabularInline):
    model = Function
    extra = 1

class ExamplesInlineAdmin(admin.StackedInline):
    model = Examples
    extra = 1

# --- Admin Classes ---

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "difficulty", "created_at", "updated_at"]
    list_filter = ["difficulty", "category"]
    search_fields = ["title", "description"]
    prepopulated_fields = {"slug": ("title",)}
    list_per_page = 20
    # Problem sahifasining o'zida misollar va testlarni tahrirlash imkoniyati
    inlines = [ExamplesInlineAdmin, FunctionInlineAdmin, ExecutionTestCaseInlineAdmin]

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug"]
    prepopulated_fields = {"slug": ("name",)}

@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ["id", "problem", "input_txt", "output_txt"]
    list_filter = ["problem"]

@admin.register(ExecutionTestCase)
class ExecutionTestCaseAdmin(admin.ModelAdmin):
    list_display = ["id", "problem", "language"]

@admin.register(Function)
class FunctionAdmin(admin.ModelAdmin):
    # 'function_name' emas, 'function' deb yozing (yoki models.py da nima deb nomlagan bo'lsangiz o'shani)
    list_display = ["id", "problem", "language", "function"]
    list_per_page = 20

@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]




@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    # Faqat modelda aniq mavjud bo'lgan ustunlarni chiqaramiz
    list_display = ("id", "problem", "user", "like_or_dislike")
    
    # Murakkab JOIN filtrlarini vaqtincha olib tashlaymiz
    list_filter = ("like_or_dislike",)
    
    # Qidiruv maydonlarini vaqtincha tozalaymiz (Xatoni aniqlash uchun)
    search_fields = ("problem__title",) 
    
    list_select_related = ("problem", "user")

