import logging
import json

from django.contrib import admin
from django.db import models
from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import TruncMonth
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import now

from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import display
from unfold.contrib.filters.admin import RelatedDropdownFilter

from .models import (
    Subject,
    ScoringPolicy,
    Test,
    Question,
    TestEnrollment,
    TestQuestion,
    Choice,
    TestSession,
    TestSessionQuestion,
    UserResponse,
    RaschCalibration,
    RaschItemParameter,
    UserSubjectAbility,
)

logger = logging.getLogger(__name__)


# ============================================================
# INLINES
# ============================================================

class ScoringPolicyInline(StackedInline):
    model = ScoringPolicy
    extra = 0
    fields = ("version", "name", "is_active", "theta_low", "theta_high")
    classes = ("collapse",)


class RaschItemParameterInline(TabularInline):
    model = RaschItemParameter
    extra = 0
    fields = (
        "question", "beta", "beta_se", "infit", "outfit",
        "is_calibrated", "flagged_for_review",
    )
    readonly_fields = ("question",)
    classes = ("collapse",)
    can_delete = False


class ChoiceInline(TabularInline):
    model = Choice
    extra = 3
    fields = ("text", "is_correct")
    classes = ("collapse",)


class TestQuestionInline(TabularInline):
    model = TestQuestion
    extra = 1
    autocomplete_fields = ("question",)
    classes = ("collapse",)


class TestSessionQuestionInline(TabularInline):
    model = TestSessionQuestion
    extra = 0
    autocomplete_fields = ("question",)
    readonly_fields = ("question",)
    can_delete = False
    classes = ("collapse",)


class UserResponseInline(TabularInline):
    model = UserResponse
    extra = 0
    fields = ("user", "question", "choice", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user", "question", "choice")
    can_delete = False
    classes = ("collapse",)


class UserSubjectAbilityInline(TabularInline):
    model = UserSubjectAbility
    extra = 0
    fields = ("subject", "theta", "theta_se", "response_count", "correct_count")
    readonly_fields = ("theta", "theta_se", "response_count", "correct_count")
    can_delete = False
    classes = ("collapse",)


# ============================================================
# SUBJECT ADMIN
# ============================================================

@admin.register(Subject)
class SubjectAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 25
    ordering = ("-id",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ScoringPolicyInline]

    list_display = (
        "name_display",
        "is_active_badge",
        "rasch_settings_display",
        "active_calibration_display",
        "question_count_display",
    )

    fieldsets = (
        ("Fan ma'lumotlari", {
            "fields": (("name", "slug"), "is_active")
        }),
        ("Rasch sozlamalari", {
            "fields": (
                ("rasch_min_persons", "rasch_recalibration_response_threshold"),
                "rasch_prior_variance",
                ("rasch_theta_min", "rasch_theta_max"),
            ),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _question_count=Count("questions", distinct=True),
        )

    @display(description="Fan nomi", header=True)
    def name_display(self, obj):
        return [obj.name, f"Slug: {obj.slug}"]

    @display(description="Holat")
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span class="bg-green-100 text-green-700 px-2.5 py-1 rounded-full text-xs font-semibold '
                'dark:bg-green-900/30 dark:text-green-400">Faol</span>'
            )
        return mark_safe(
            '<span class="bg-red-100 text-red-700 px-2.5 py-1 rounded-full text-xs font-semibold '
            'dark:bg-red-900/30 dark:text-red-400">Nofaol</span>'
        )

    @display(description="Rasch sozlamalari")
    def rasch_settings_display(self, obj):
        return format_html(
            '<span class="text-xs text-gray-600 dark:text-gray-400">'
            'Min: {} ishtirokchi | Prior σ²: {} | θ: [{}, {}]</span>',
            obj.rasch_min_persons,
            obj.rasch_prior_variance,
            obj.rasch_theta_min,
            obj.rasch_theta_max,
        )

    @display(description="Faol kalibratsiya")
    def active_calibration_display(self, obj):
        cal = obj.get_active_calibration()
        if cal:
            return format_html(
                '<span class="bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full text-xs font-semibold '
                'dark:bg-blue-900/30 dark:text-blue-400">v{}</span>',
                cal.version,
            )
        return mark_safe(
            '<span class="bg-amber-100 text-amber-700 px-2.5 py-1 rounded-full text-xs font-semibold '
            'dark:bg-amber-900/30 dark:text-amber-400">Mavjud emas</span>'
        )

    @display(description="Savollar", ordering="_question_count")
    def question_count_display(self, obj):
        return format_html(
            '<span class="bg-purple-100 text-purple-700 px-2.5 py-1 rounded-full text-xs font-semibold '
            'dark:bg-purple-900/30 dark:text-purple-400">{} ta</span>',
            obj._question_count,
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)

        stats = filtered_qs.aggregate(
            total_subjects=Count("id"),
            active_subjects=Count("id", filter=Q(is_active=True)),
            total_questions=Count("questions", distinct=True),
            total_calibrations=Count("rasch_calibrations", distinct=True),
            active_calibrations=Count(
                "rasch_calibrations",
                filter=Q(rasch_calibrations__is_active=True),
                distinct=True,
            ),
        )

        extra_context.update({
            "total_subjects": stats["total_subjects"] or 0,
            "active_subjects": stats["active_subjects"] or 0,
            "total_questions": stats["total_questions"] or 0,
            "total_calibrations": stats["total_calibrations"] or 0,
            "active_calibrations": stats["active_calibrations"] or 0,
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# SCORING POLICY ADMIN
# ============================================================

@admin.register(ScoringPolicy)
class ScoringPolicyAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 25
    ordering = ("-version",)
    search_fields = ("name", "subject__name")

    list_filter = (
        "is_active",
        ("subject", RelatedDropdownFilter),
    )

    list_display = (
        "policy_display",
        "subject_display",
        "is_active_badge",
        "scale_display",
        "grade_boundaries_display",
        "created_at_formatted",
    )

    fieldsets = (
        ("Umumiy", {
            "fields": (("subject", "version", "name"), "is_active")
        }),
        ("Theta → Ball", {
            "fields": (("theta_low", "theta_high"),)
        }),
        ("Daraja chegaralari", {
            "fields": (
                ("grade_a_plus_min", "grade_a_min"),
                ("grade_b_plus_min", "grade_b_min"),
                ("grade_c_plus_min", "grade_c_min"),
            ),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("subject")

    @display(description="Siyosat", header=True)
    def policy_display(self, obj):
        return [obj.name, f"v{obj.version}"]

    @display(description="Fan")
    def subject_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/subject/{}/change/" class="text-blue-600 hover:underline">{}</a>',
            obj.subject.id,
            obj.subject.name,
        )

    @display(description="Holat")
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span class="bg-green-100 text-green-700 px-2.5 py-1 rounded-full text-xs font-semibold '
                'dark:bg-green-900/30 dark:text-green-400">Faol</span>'
            )
        return mark_safe(
            '<span class="bg-gray-100 text-gray-700 px-2.5 py-1 rounded-full text-xs font-semibold '
            'dark:bg-gray-800 dark:text-gray-400">Nofaol</span>'
        )

    @display(description="Shkala")
    def scale_display(self, obj):
        return format_html(
            '<span class="text-xs text-gray-600 dark:text-gray-400">{}→0 | {}→100</span>',
            obj.theta_low,
            obj.theta_high,
        )

    @display(description="Daraja chegaralari")
    def grade_boundaries_display(self, obj):
        return format_html(
            '<span class="text-xs font-mono text-gray-600 dark:text-gray-400">'
            'A+≥{} | A≥{} | B+≥{} | B≥{} | C+≥{} | C≥{}</span>',
            obj.grade_a_plus_min, obj.grade_a_min,
            obj.grade_b_plus_min, obj.grade_b_min,
            obj.grade_c_plus_min, obj.grade_c_min,
        )

    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")


# ============================================================
# TEST ADMIN
# ============================================================

@admin.register(Test)
class TestAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 25
    ordering = ("-id",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "slug", "access_code")
    inlines = [TestQuestionInline]

    list_filter = (
        "is_active",
        ("subject", RelatedDropdownFilter),
        "start_time",
        "end_time",
    )

    list_display = (
        "title_display",
        "subject_display",
        "status_badge",
        "question_count_display",
        "sessions_count_display",
        "price_display",
        "is_active",
        "created_at_formatted",
    )

    fieldsets = (
        ("Asosiy", {
            "fields": (
                ("title", "slug"),
                "subject",
                "description",
                ("is_active", "owner"),
            )
        }),
        ("Vaqt va cheklovlar", {
            "fields": (
                ("start_time", "end_time"),
                "duration_minutes",
                "max_attempts",
                "access_code",
            ),
            "classes": ("collapse",),
        }),
        ("Rasch sozlamalari", {
            "fields": (
                "rasch_theta_pass_threshold",
                "random_questions_count",
            ),
            "classes": ("collapse",),
        }),
        ("Narx", {
            "fields": (("price", "discount_price"),),
            "classes": ("collapse",),
        }),
        ("Qo'shimcha", {
            "fields": (
                "max_lifelines",
                "reveal_correct_answers",
            ),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("subject", "owner").annotate(
            _questions_count=Count("questions", distinct=True),
            _sessions_count=Count("sessions", distinct=True),
        )

    @display(description="Test nomi", header=True)
    def title_display(self, obj):
        return [obj.title[:50], f"ID: #{obj.id}"]

    @display(description="Fan")
    def subject_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/subject/{}/change/" class="text-blue-600 hover:underline">{}</a>',
            obj.subject.id,
            obj.subject.name,
        )

    @display(description="Holat")
    def status_badge(self, obj):
        now_time = now()
        if not obj.is_active:
            return mark_safe(
                '<span class="bg-red-100 text-red-700 px-2.5 py-1 rounded-full text-xs font-semibold '
                'dark:bg-red-900/30 dark:text-red-400">Nofaol</span>'
            )
        if obj.start_time > now_time:
            return mark_safe(
                '<span class="bg-amber-100 text-amber-700 px-2.5 py-1 rounded-full text-xs font-semibold '
                'dark:bg-amber-900/30 dark:text-amber-400">Kutilmoqda</span>'
            )
        if obj.end_time < now_time:
            return mark_safe(
                '<span class="bg-rose-100 text-rose-700 px-2.5 py-1 rounded-full text-xs font-semibold '
                'dark:bg-rose-900/30 dark:text-rose-400">Yakunlangan</span>'
            )
        return mark_safe(
            '<span class="bg-green-100 text-green-700 px-2.5 py-1 rounded-full text-xs font-semibold '
            'dark:bg-green-900/30 dark:text-green-400">Davom etmoqda</span>'
        )

    @display(description="Savollar", ordering="_questions_count")
    def question_count_display(self, obj):
        return format_html(
            '<span class="bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full text-xs font-semibold '
            'dark:bg-blue-900/30 dark:text-blue-400">{} ta</span>',
            obj._questions_count,
        )

    @display(description="Seanslar", ordering="_sessions_count")
    def sessions_count_display(self, obj):
        return format_html(
            '<span class="bg-purple-100 text-purple-700 px-2.5 py-1 rounded-full text-xs font-semibold '
            'dark:bg-purple-900/30 dark:text-purple-400">{} ta</span>',
            obj._sessions_count,
        )

    @display(description="Narx")
    def price_display(self, obj):
        if obj.discount_price and obj.discount_price < obj.price:
            return format_html(
                '<span class="text-green-600 font-semibold">{} so\'m</span> '
                '<span class="text-gray-400 line-through text-xs">{}</span>',
                obj.discount_price,
                obj.price,
            )
        return format_html(
            '<span class="text-gray-700 dark:text-gray-300">{} so\'m</span>',
            obj.price,
        )

    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        now_time = now()
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)

        test_stats = filtered_qs.aggregate(
            total_tests=Count("id"),
            active_tests=Count("id", filter=Q(is_active=True)),
            inactive_tests=Count("id", filter=Q(is_active=False)),
            upcoming_count=Count("id", filter=Q(is_active=True, start_time__gt=now_time)),
            ongoing_count=Count("id", filter=Q(is_active=True, start_time__lte=now_time, end_time__gte=now_time)),
            ended_count=Count("id", filter=Q(is_active=True, end_time__lt=now_time)),
        )

        session_stats = TestSession.objects.aggregate(
            total_sessions=Count("id"),
            completed_sessions=Count("id", filter=Q(status="completed")),
        )

        extra_context.update({
            "total_tests": test_stats["total_tests"] or 0,
            "active_tests": test_stats["active_tests"] or 0,
            "inactive_tests": test_stats["inactive_tests"] or 0,
            "upcoming_count": test_stats["upcoming_count"] or 0,
            "ongoing_count": test_stats["ongoing_count"] or 0,
            "ended_count": test_stats["ended_count"] or 0,
            "total_sessions": session_stats["total_sessions"] or 0,
            "completed_sessions": session_stats["completed_sessions"] or 0,
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# QUESTION ADMIN
# ============================================================

@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 30
    ordering = ("-id",)
    search_fields = ("text", "subject__name")
    inlines = [ChoiceInline]

    list_filter = (
        "is_active",
        ("subject", RelatedDropdownFilter),
        "dif_group",
    )

    list_display = (
        "text_preview",
        "subject_display",
        "is_active_badge",
        "dif_group_display",
        "choices_count_display",
        "active_beta_display",
        "created_at_formatted",
    )

    fieldsets = (
        ("Savol ma'lumotlari", {
            "fields": (
                "subject",
                "text",
                "explanation",
                ("is_active", "dif_group"),
            )
        }),
        ("Yaratuvchi", {
            "fields": ("owner",),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("subject").annotate(
            _choices_count=Count("choices", distinct=True)
        )

    @display(description="Savol matni")
    def text_preview(self, obj):
        return obj.text[:60] + "..." if len(obj.text) > 60 else obj.text

    @display(description="Fan")
    def subject_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/subject/{}/change/" class="text-blue-600 hover:underline">{}</a>',
            obj.subject.id,
            obj.subject.name,
        )

    @display(description="Holat")
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span class="bg-green-100 text-green-700 px-2.5 py-1 rounded-full text-xs font-semibold '
                'dark:bg-green-900/30 dark:text-green-400">Faol</span>'
            )
        return mark_safe(
            '<span class="bg-red-100 text-red-700 px-2.5 py-1 rounded-full text-xs font-semibold '
            'dark:bg-red-900/30 dark:text-red-400">Nofaol</span>'
        )

    @display(description="DIF guruhi")
    def dif_group_display(self, obj):
        if obj.dif_group:
            return format_html(
                '<span class="bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded text-xs '
                'dark:bg-indigo-900/30 dark:text-indigo-400">{}</span>',
                obj.dif_group,
            )
        return mark_safe('<span class="text-gray-400 text-xs">—</span>')

    @display(description="Variantlar", ordering="_choices_count")
    def choices_count_display(self, obj):
        return format_html(
            '<span class="bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 '
            'px-2.5 py-1 rounded-full text-xs">{}</span>',
            obj._choices_count,
        )

    @display(description="β (faol)")
    def active_beta_display(self, obj):
        param = obj.active_rasch_parameter
        if param and param.is_calibrated:
            color = "text-green-600" if abs(param.beta) <= 4 else "text-red-600"
            return format_html(
                '<span class="{} font-mono text-xs">{:.2f}</span>',
                color,
                param.beta,
            )
        return mark_safe('<span class="text-gray-400 text-xs">—</span>')

    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)

        stats = filtered_qs.aggregate(
            total_questions=Count("id"),
            active_questions=Count("id", filter=Q(is_active=True)),
            with_dif=Count("id", filter=~Q(dif_group="") & Q(dif_group__isnull=False)),
        )

        extra_context.update({
            "total_questions": stats["total_questions"] or 0,
            "active_questions": stats["active_questions"] or 0,
            "with_dif": stats["with_dif"] or 0,
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# TEST QUESTION ADMIN
# ============================================================

@admin.register(TestQuestion)
class TestQuestionAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 50
    ordering = ("-id",)
    search_fields = ("test__title", "question__text")
    autocomplete_fields = ("test", "question")

    list_filter = (
        ("test", RelatedDropdownFilter),
        ("question", RelatedDropdownFilter),
    )

    list_display = (
        "id",
        "test_display",
        "question_display",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("test", "question")

    @display(description="Test")
    def test_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/test/{}/change/" class="text-blue-600 hover:underline">{}</a>',
            obj.test.id,
            obj.test.title[:40],
        )

    @display(description="Savol")
    def question_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/question/{}/change/" class="text-green-600 hover:underline">{}</a>',
            obj.question.id,
            obj.question.text[:50],
        )


# ============================================================
# CHOICE ADMIN
# ============================================================

@admin.register(Choice)
class ChoiceAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 30
    ordering = ("-id",)
    search_fields = ("text", "question__text")

    list_filter = (
        "is_correct",
        ("question", admin.RelatedOnlyFieldListFilter),
    )

    list_display = (
        "text_preview",
        "question_display",
        "is_correct_icon",
        "created_at_formatted",
    )

    fieldsets = (
        ("Javob varianti", {
            "fields": (
                "question",
                ("text", "is_correct"),
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("question")

    @display(description="Variant matni")
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text

    @display(description="Savol")
    def question_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/question/{}/change/" class="text-blue-600 hover:underline">{}</a>',
            obj.question.id,
            obj.question.text[:40],
        )

    @display(description="To'g'ri", ordering="is_correct")
    def is_correct_icon(self, obj):
        if obj.is_correct:
            return mark_safe(
                '<span class="text-green-500 font-bold text-base">To\'g\'ri</span>'
            )
        return mark_safe(
            '<span class="text-red-500 font-bold text-base">Noto\'g\'ri</span>'
        )

    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")


# ============================================================
# TEST SESSION ADMIN
# ============================================================

@admin.register(TestSession)
class TestSessionAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 30
    ordering = ("-started_at",)
    autocomplete_fields = ("user", "test")
    search_fields = ("user__username", "user__full_name", "test__title")
    inlines = [TestSessionQuestionInline, UserResponseInline]

    list_filter = (
        "status",
        ("test", admin.RelatedOnlyFieldListFilter),
        "is_provisional",
        "started_at",
    )

    list_display = (
        "user_display",
        "test_display",
        "status_badge",
        "theta_display",
        "scaled_score_display",
        "grade_display",
        "passed_badge",
        "is_provisional_badge",
        "started_at_formatted",
    )

    fieldsets = (
        ("Foydalanuvchi va test", {
            "fields": (("user", "test"),),
        }),
        ("Rasch natijalar", {
            "fields": (
                ("rasch_theta", "rasch_se"),
                ("person_infit", "person_outfit"),
                ("scaled_score", "grade", "grade_description"),
            )
        }),
        ("Kalibratsiya holati", {
            "fields": (
                ("is_provisional", "uncalibrated_question_count"),
                ("rasch_calibration", "scoring_policy"),
            ),
            "classes": ("collapse",),
        }),
        ("Xom statistika", {
            "fields": (
                ("correct_count", "wrong_count", "unanswered_count"),
                "raw_percentage",
                "lifelines_used",
            ),
            "classes": ("collapse",),
        }),
        ("Vaqt", {
            "fields": (("started_at", "completed_at"),),
        }),
    )

    readonly_fields = (
        "started_at", "completed_at",
        "rasch_theta", "rasch_se",
        "person_infit", "person_outfit",
        "scaled_score", "grade", "grade_description",
        "raw_percentage", "correct_count", "wrong_count", "unanswered_count",
        "is_provisional", "uncalibrated_question_count",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "user", "test", "rasch_calibration", "scoring_policy"
        )

    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = getattr(obj.user, "full_name", None) or getattr(obj.user, "username", None) or str(obj.user)
        return [name, f"ID: {obj.user.id}"]

    @display(description="Test")
    def test_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/test/{}/change/" class="text-blue-600 hover:underline">{}</a>',
            obj.test.id,
            obj.test.title[:40],
        )

    @display(description="Holat", ordering="status")
    def status_badge(self, obj):
        colors = {
            "in_progress": ("bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400", "Jarayonda"),
            "completed": ("bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400", "Yakunlangan"),
            "expired": ("bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400", "Muddati o'tgan"),
        }
        badge_class, label = colors.get(obj.status, ("bg-gray-100 text-gray-700", obj.status))
        return mark_safe(
            f'<span class="{badge_class} px-2.5 py-1 rounded-full text-xs font-semibold">{label}</span>'
        )

    @display(description="θ (logit)")
    def theta_display(self, obj):
        if obj.rasch_theta is not None:
            return format_html(
                '<span class="font-mono font-semibold text-blue-600 dark:text-blue-400">{:.2f}</span>',
                obj.rasch_theta,
            )
        return mark_safe('<span class="text-gray-400">—</span>')

    @display(description="Ball")
    def scaled_score_display(self, obj):
        if obj.scaled_score is not None:
            return format_html(
                '<span class="font-semibold text-purple-600 dark:text-purple-400">{:.1f}</span>',
                obj.scaled_score,
            )
        return mark_safe('<span class="text-gray-400">—</span>')

    @display(description="Daraja")
    def grade_display(self, obj):
        if obj.grade:
            colors = {
                "A+": "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
                "A": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
                "B+": "bg-lime-100 text-lime-700 dark:bg-lime-900/30 dark:text-lime-400",
                "B": "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
                "C+": "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
                "C": "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
            }
            badge_class = colors.get(obj.grade, "bg-gray-100 text-gray-700")
            return mark_safe(
                f'<span class="{badge_class} px-2.5 py-1 rounded-full text-xs font-semibold">{obj.grade}</span>'
            )
        return mark_safe('<span class="text-gray-400">—</span>')

    @display(description="O'tdi")
    def passed_badge(self, obj):
        if obj.status != "completed":
            return mark_safe('<span class="text-gray-400 text-xs">Kutilmoqda</span>')
        if obj.passed:
            return mark_safe(
                '<span class="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold '
                'dark:bg-green-900/30 dark:text-green-400">O\'tdi</span>'
            )
        return mark_safe(
            '<span class="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-semibold '
            'dark:bg-red-900/30 dark:text-red-400">O\'tmadi</span>'
        )

    @display(description="Vaqtinchalik")
    def is_provisional_badge(self, obj):
        if obj.is_provisional:
            return mark_safe(
                '<span class="bg-amber-100 text-amber-700 px-2 py-0.5 rounded text-xs font-semibold '
                'dark:bg-amber-900/30 dark:text-amber-400">Vaqtinchalik</span>'
            )
        return mark_safe(
            '<span class="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold '
            'dark:bg-green-900/30 dark:text-green-400">Yakuniy</span>'
        )

    @display(description="Boshlangan vaqt", ordering="started_at")
    def started_at_formatted(self, obj):
        return obj.started_at.strftime("%d-%m-%Y %H:%M") if obj.started_at else "—"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)

        stats = filtered_qs.aggregate(
            total_sessions=Count("id"),
            in_progress_count=Count("id", filter=Q(status="in_progress")),
            completed_count=Count("id", filter=Q(status="completed")),
            expired_count=Count("id", filter=Q(status="expired")),
            avg_theta=Avg("rasch_theta"),
            avg_score=Avg("scaled_score"),
            provisional_count=Count("id", filter=Q(is_provisional=True)),
            passed_count=Count("id", filter=Q(rasch_theta__gte=F("test__rasch_theta_pass_threshold"))),
        )

        extra_context.update({
            "total_sessions": stats["total_sessions"] or 0,
            "in_progress_count": stats["in_progress_count"] or 0,
            "completed_count": stats["completed_count"] or 0,
            "expired_count": stats["expired_count"] or 0,
            "avg_theta": stats["avg_theta"] or 0.0,
            "avg_score": stats["avg_score"] or 0.0,
            "provisional_count": stats["provisional_count"] or 0,
            "passed_count": stats["passed_count"] or 0,
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# TEST SESSION QUESTION ADMIN
# ============================================================

@admin.register(TestSessionQuestion)
class TestSessionQuestionAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 50
    ordering = ("-id",)
    search_fields = ("session__user__username", "question__text")
    autocomplete_fields = ("session", "question")

    list_filter = (
        ("session", RelatedDropdownFilter),
        ("question", RelatedDropdownFilter),
    )

    list_display = (
        "id",
        "session_display",
        "question_display",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("session", "question")

    @display(description="Seans")
    def session_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/testsession/{}/change/" class="text-blue-600 hover:underline">{} — {}</a>',
            obj.session.id,
            obj.session.user,
            obj.session.test.title[:30],
        )

    @display(description="Savol")
    def question_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/question/{}/change/" class="text-green-600 hover:underline">{}</a>',
            obj.question.id,
            obj.question.text[:50],
        )


# ============================================================
# USER RESPONSE ADMIN
# ============================================================

@admin.register(UserResponse)
class UserResponseAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 50
    ordering = ("-created_at",)
    autocomplete_fields = ("user", "question", "choice", "session")
    search_fields = ("user__username", "question__text", "choice__text")

    list_filter = (
        ("session", RelatedDropdownFilter),
        ("question", RelatedDropdownFilter),
        "created_at",
    )

    list_display = (
        "user_display",
        "question_display",
        "choice_display",
        "is_correct_icon",
        "session_link",
        "created_at_formatted",
    )

    fieldsets = (
        ("Foydalanuvchi javobi", {
            "fields": (("user", "session"), ("question", "choice")),
        }),
        ("Vaqt", {
            "fields": ("created_at",),
        }),
    )

    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "user", "question", "choice", "session"
        )

    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = getattr(obj.user, "full_name", None) or getattr(obj.user, "username", None) or str(obj.user)
        return [name, f"ID: {obj.user.id}"]

    @display(description="Savol")
    def question_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/question/{}/change/" class="text-blue-600 hover:underline">{}</a>',
            obj.question.id,
            obj.question.text[:40],
        )

    @display(description="Javob")
    def choice_display(self, obj):
        if obj.choice:
            return obj.choice.text[:50] + "..." if len(obj.choice.text) > 50 else obj.choice.text
        return format_html(
            '<span class="text-gray-400 dark:text-gray-500 italic">Javobsiz qoldirilgan</span>'
        )

    @display(description="To'g'ri")
    def is_correct_icon(self, obj):
        if obj.choice:
            if obj.choice.is_correct:
                return mark_safe('<span class="text-green-500 text-lg">To\'g\'ri</span>')
            return mark_safe('<span class="text-red-500 text-lg">Noto\'g\'ri</span>')
        return mark_safe('<span class="text-gray-400 text-lg">O\'tkazib yuborilgan</span>')

    @display(description="Seans")
    def session_link(self, obj):
        if obj.session:
            return format_html(
                '<a href="/admin/quizs/testsession/{}/change/" '
                'class="text-purple-600 hover:underline text-xs">Seans</a>',
                obj.session.id,
            )
        return mark_safe('<span class="text-gray-400 text-xs">—</span>')

    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)

        stats = filtered_qs.aggregate(
            total_cnt=Count("id"),
            correct_cnt=Count("id", filter=Q(choice__is_correct=True)),
            incorrect_cnt=Count("id", filter=Q(choice__is_correct=False)),
            skipped_cnt=Count("id", filter=Q(choice__isnull=True)),
        )

        total = stats["total_cnt"] or 1

        extra_context.update({
            "total_responses": stats["total_cnt"] or 0,
            "correct_count": stats["correct_cnt"] or 0,
            "incorrect_count": stats["incorrect_cnt"] or 0,
            "skipped_count": stats["skipped_cnt"] or 0,
            "correct_percent": round((stats["correct_cnt"] or 0) / total * 100),
            "incorrect_percent": round((stats["incorrect_cnt"] or 0) / total * 100),
            "skipped_percent": round((stats["skipped_cnt"] or 0) / total * 100),
            "chart_labels": json.dumps(["To'g'ri", "Noto'g'ri", "Javobsiz"]),
            "chart_data": json.dumps([
                stats["correct_cnt"] or 0,
                stats["incorrect_cnt"] or 0,
                stats["skipped_cnt"] or 0,
            ]),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# RASCH CALIBRATION ADMIN
# ============================================================

@admin.register(RaschCalibration)
class RaschCalibrationAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 25
    ordering = ("-version",)
    search_fields = ("subject__name", "algorithm_version")
    inlines = [RaschItemParameterInline]

    list_filter = (
        "status",
        "is_active",
        ("subject", RelatedDropdownFilter),
        "created_at",
    )

    list_display = (
        "calibration_display",
        "subject_display",
        "status_badge",
        "is_active_badge",
        "sample_stats_display",
        "beta_stats_display",
        "converged_badge",
        "created_at_formatted",
    )

    fieldsets = (
        ("Umumiy", {
            "fields": (
                ("subject", "version"),
                ("algorithm_version", "response_policy"),
                ("status", "is_active"),
            )
        }),
        ("Namuna", {
            "fields": (
                ("sample_size", "response_count", "item_count"),
            ),
            "classes": ("collapse",),
        }),
        ("Beta statistikasi", {
            "fields": (
                ("mean_beta", "std_beta"),
                ("min_beta", "max_beta"),
            ),
            "classes": ("collapse",),
        }),
        ("Hisoblash", {
            "fields": ("converged",),
            "classes": ("collapse",),
        }),
        ("Rad etish", {
            "fields": ("rejection_reason",),
            "classes": ("collapse",),
        }),
        ("Vaqt", {
            "fields": (
                ("created_at", "completed_at", "activated_at"),
            ),
            "classes": ("collapse",),
        }),
    )

    readonly_fields = (
        "created_at", "completed_at", "activated_at",
        "sample_size", "response_count", "item_count",
        "mean_beta", "std_beta", "min_beta", "max_beta",
        "converged",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("subject")

    @display(description="Kalibratsiya", header=True)
    def calibration_display(self, obj):
        return [f"v{obj.version}", obj.algorithm_version]

    @display(description="Fan")
    def subject_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/subject/{}/change/" class="text-blue-600 hover:underline">{}</a>',
            obj.subject.id,
            obj.subject.name,
        )

    @display(description="Status", ordering="status")
    def status_badge(self, obj):
        colors = {
            "pending": ("bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400", "Kutilmoqda"),
            "running": ("bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400", "Hisoblanmoqda"),
            "completed": ("bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400", "Ko'rib chiqilmoqda"),
            "failed": ("bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400", "Xatolik"),
            "rejected": ("bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400", "Rad etildi"),
            "active": ("bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400", "Faol"),
            "retired": ("bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400", "Almashtirildi"),
        }
        badge_class, label = colors.get(obj.status, ("bg-gray-100 text-gray-700", obj.status))
        return mark_safe(
            f'<span class="{badge_class} px-2.5 py-1 rounded-full text-xs font-semibold">{label}</span>'
        )

    @display(description="Faol")
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span class="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold '
                'dark:bg-green-900/30 dark:text-green-400">Faol</span>'
            )
        return mark_safe('<span class="text-gray-400 text-xs">—</span>')

    @display(description="Namuna")
    def sample_stats_display(self, obj):
        return format_html(
            '<span class="text-xs text-gray-600 dark:text-gray-400">'
            '{} ishtirokchi | {} javob | {} savol</span>',
            obj.sample_size,
            obj.response_count,
            obj.item_count,
        )

    @display(description="Beta")
    def beta_stats_display(self, obj):
        return format_html(
            '<span class="font-mono text-xs text-gray-600 dark:text-gray-400">'
            'μ={:.2f} σ={:.2f} [{:.2f}, {:.2f}]</span>',
            obj.mean_beta,
            obj.std_beta,
            obj.min_beta,
            obj.max_beta,
        )

    @display(description="Yakunlandi")
    def converged_badge(self, obj):
        if obj.converged:
            return mark_safe(
                '<span class="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold '
                'dark:bg-green-900/30 dark:text-green-400">Yakunlandi</span>'
            )
        if obj.status in ("running", "pending"):
            return mark_safe(
                '<span class="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-semibold '
                'dark:bg-blue-900/30 dark:text-blue-400">Kutilmoqda</span>'
            )
        return mark_safe(
            '<span class="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-semibold '
            'dark:bg-red-900/30 dark:text-red-400">Yakunlanmadi</span>'
        )

    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)

        stats = filtered_qs.aggregate(
            total=Count("id"),
            active_count=Count("id", filter=Q(is_active=True)),
            pending_count=Count("id", filter=Q(status="pending")),
            running_count=Count("id", filter=Q(status="running")),
            completed_count=Count("id", filter=Q(status="completed")),
            failed_count=Count("id", filter=Q(status="failed")),
            converged_count=Count("id", filter=Q(converged=True)),
            total_responses=Sum("response_count"),
            total_items=Sum("item_count"),
        )

        extra_context.update({
            "total_calibrations": stats["total"] or 0,
            "active_count": stats["active_count"] or 0,
            "pending_count": stats["pending_count"] or 0,
            "running_count": stats["running_count"] or 0,
            "completed_count": stats["completed_count"] or 0,
            "failed_count": stats["failed_count"] or 0,
            "converged_count": stats["converged_count"] or 0,
            "total_responses": stats["total_responses"] or 0,
            "total_items": stats["total_items"] or 0,
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# RASCH ITEM PARAMETER ADMIN
# ============================================================

@admin.register(RaschItemParameter)
class RaschItemParameterAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 50
    ordering = ("-beta",)
    search_fields = ("question__text", "calibration__subject__name")
    autocomplete_fields = ("calibration", "question")

    list_filter = (
        "is_calibrated",
        "flagged_for_review",
        "is_extreme",
        ("calibration", RelatedDropdownFilter),
    )

    list_display = (
        "question_display",
        "calibration_display",
        "beta_display",
        "se_display",
        "fit_display",
        "flags_display",
        "sample_size_display",
        "created_at_formatted",
    )

    fieldsets = (
        ("Parametrlar", {
            "fields": (
                ("calibration", "question"),
                ("beta", "beta_se"),
                ("infit", "outfit"),
            )
        }),
        ("Belgilar", {
            "fields": (
                ("is_calibrated", "flagged_for_review", "is_extreme"),
                "sample_size",
            ),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("calibration", "question")

    @display(description="Savol")
    def question_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/question/{}/change/" class="text-blue-600 hover:underline">{}</a>',
            obj.question.id,
            obj.question.text[:50],
        )

    @display(description="Kalibratsiya")
    def calibration_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/raschcalibration/{}/change/" '
            'class="text-purple-600 hover:underline text-xs">{} v{}</a>',
            obj.calibration.id,
            obj.calibration.subject.name,
            obj.calibration.version,
        )

    @display(description="β", ordering="beta")
    def beta_display(self, obj):
        color = "text-green-600" if abs(obj.beta) <= 4 else "text-red-600"
        return format_html(
            '<span class="font-mono font-semibold {}">{:.2f}</span>',
            color,
            obj.beta,
        )

    @display(description="SE")
    def se_display(self, obj):
        if obj.beta_se < 999:
            return format_html(
                '<span class="font-mono text-xs text-gray-600 dark:text-gray-400">±{:.2f}</span>',
                obj.beta_se,
            )
        return mark_safe('<span class="text-gray-400 text-xs">—</span>')

    @display(description="Fit")
    def fit_display(self, obj):
        if obj.infit is not None and obj.outfit is not None:
            infit_ok = 0.5 <= obj.infit <= 1.5
            outfit_ok = 0.5 <= obj.outfit <= 1.5
            color = "text-green-600" if (infit_ok and outfit_ok) else "text-red-600"
            return format_html(
                '<span class="font-mono text-xs {}">In:{:.2f} Out:{:.2f}</span>',
                color,
                obj.infit,
                obj.outfit,
            )
        return mark_safe('<span class="text-gray-400 text-xs">—</span>')

    @display(description="Belgilar")
    def flags_display(self, obj):
        flags = []
        if obj.is_calibrated:
            flags.append(
                '<span class="bg-green-100 text-green-700 px-1.5 py-0.5 rounded text-[10px] '
                'dark:bg-green-900/30 dark:text-green-400">Kalibrlangan</span>'
            )
        if obj.flagged_for_review:
            flags.append(
                '<span class="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded text-[10px] '
                'dark:bg-amber-900/30 dark:text-amber-400">Tekshiruv</span>'
            )
        if obj.is_extreme:
            flags.append(
                '<span class="bg-red-100 text-red-700 px-1.5 py-0.5 rounded text-[10px] '
                'dark:bg-red-900/30 dark:text-red-400">Ekstremal</span>'
            )
        return mark_safe(" ".join(flags)) if flags else mark_safe('<span class="text-gray-400 text-xs">—</span>')

    @display(description="n")
    def sample_size_display(self, obj):
        return format_html(
            '<span class="text-xs text-gray-600 dark:text-gray-400">{}</span>',
            obj.sample_size,
        )

    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")


# ============================================================
# USER SUBJECT ABILITY ADMIN
# ============================================================

@admin.register(UserSubjectAbility)
class UserSubjectAbilityAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 50
    ordering = ("-theta",)
    search_fields = ("user__username", "user__full_name", "subject__name")
    autocomplete_fields = ("user", "subject", "calibration")

    list_filter = (
        ("subject", RelatedDropdownFilter),
        ("calibration", RelatedDropdownFilter),
    )

    list_display = (
        "user_display",
        "subject_display",
        "theta_display",
        "se_display",
        "fit_display",
        "response_stats_display",
        "calibration_version_display",
        "updated_at_formatted",
    )

    fieldsets = (
        ("Foydalanuvchi va fan", {
            "fields": (("user", "subject"),)
        }),
        ("Qobiliyat", {
            "fields": (
                ("theta", "theta_se"),
                ("person_infit", "person_outfit"),
            )
        }),
        ("Statistika", {
            "fields": (
                ("response_count", "correct_count"),
            ),
            "classes": ("collapse",),
        }),
        ("Kalibratsiya", {
            "fields": (
                ("calibration", "calibration_version"),
            ),
            "classes": ("collapse",),
        }),
    )

    readonly_fields = ("updated_at", "created_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "subject", "calibration")

    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = getattr(obj.user, "full_name", None) or getattr(obj.user, "username", None) or str(obj.user)
        return [name, f"ID: {obj.user.id}"]

    @display(description="Fan")
    def subject_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/subject/{}/change/" class="text-blue-600 hover:underline">{}</a>',
            obj.subject.id,
            obj.subject.name,
        )

    @display(description="θ", ordering="theta")
    def theta_display(self, obj):
        color = "text-green-600" if obj.theta >= 0 else "text-red-600"
        return format_html(
            '<span class="font-mono font-bold text-lg {}">{:.2f}</span>',
            color,
            obj.theta,
        )

    @display(description="SE")
    def se_display(self, obj):
        if obj.theta_se < 999:
            return format_html(
                '<span class="font-mono text-xs text-gray-600 dark:text-gray-400">±{:.2f}</span>',
                obj.theta_se,
            )
        return mark_safe('<span class="text-gray-400 text-xs">—</span>')

    @display(description="Fit")
    def fit_display(self, obj):
        if obj.person_infit is not None and obj.person_outfit is not None:
            infit_ok = 0.5 <= obj.person_infit <= 1.5
            outfit_ok = 0.5 <= obj.person_outfit <= 1.5
            color = "text-green-600" if (infit_ok and outfit_ok) else "text-red-600"
            return format_html(
                '<span class="font-mono text-xs {}">In:{:.2f} Out:{:.2f}</span>',
                color,
                obj.person_infit,
                obj.person_outfit,
            )
        return mark_safe('<span class="text-gray-400 text-xs">—</span>')

    @display(description="Javoblar")
    def response_stats_display(self, obj):
        accuracy = (obj.correct_count / obj.response_count * 100) if obj.response_count > 0 else 0
        return format_html(
            '<span class="text-xs text-gray-600 dark:text-gray-400">{} / {} ({:.0f}%)</span>',
            obj.correct_count,
            obj.response_count,
            accuracy,
        )

    @display(description="Kalibratsiya")
    def calibration_version_display(self, obj):
        return format_html(
            '<span class="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs '
            'dark:bg-blue-900/30 dark:text-blue-400">v{}</span>',
            obj.calibration_version,
        )

    @display(description="Yangilangan")
    def updated_at_formatted(self, obj):
        return obj.updated_at.strftime("%d-%m-%Y %H:%M")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)

        stats = filtered_qs.aggregate(
            total_abilities=Count("id"),
            avg_theta=Avg("theta"),
            total_responses=Sum("response_count"),
            total_correct=Sum("correct_count"),
        )

        total_resp = stats["total_responses"] or 1

        extra_context.update({
            "total_abilities": stats["total_abilities"] or 0,
            "avg_theta": stats["avg_theta"] or 0.0,
            "total_responses": stats["total_responses"] or 0,
            "total_correct": stats["total_correct"] or 0,
            "overall_accuracy": round((stats["total_correct"] or 0) / total_resp * 100),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# TEST ENROLLMENT ADMIN
# ============================================================

@admin.register(TestEnrollment)
class TestEnrollmentAdmin(ModelAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER

    list_display = [
        "display_user",
        "test",
        "formatted_amount",
        "transaction_id",
        "created_at",
    ]

    search_fields = [
        "user__username",
        "user__telegram_id",
        "test__title",
        "transaction_id",
    ]

    list_filter = [
        ("test", admin.RelatedOnlyFieldListFilter),
        "created_at",
    ]

    list_select_related = ["user", "test"]
    readonly_fields = ["id", "created_at"]
    ordering = ["-created_at"]

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)

        stats = filtered_qs.aggregate(
            total_sales_count=Count("id"),
            total_revenue=Sum("amount"),
            average_check=Avg("amount"),
        )

        total_revenue = stats["total_revenue"] or 0
        total_sales_count = stats["total_sales_count"] or 0
        average_check = stats["average_check"] or 0

        monthly_data = (
            filtered_qs.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(revenue=Sum("amount"))
            .order_by("month")
        )

        chart_labels = []
        chart_values = []
        for item in monthly_data:
            if item["month"]:
                chart_labels.append(item["month"].strftime("%Y-%m"))
                chart_values.append(float(item["revenue"] or 0))

        extra_context.update({
            "total_sales_count": total_sales_count,
            "total_revenue": f"{total_revenue:,.2f}",
            "average_check": f"{average_check:,.2f}",
            "chart_labels_json": json.dumps(chart_labels),
            "chart_values_json": json.dumps(chart_values),
        })

        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Foydalanuvchi")
    def display_user(self, obj):
        return obj.user.username if obj.user.username else f"TG: {obj.user.telegram_id}"

    @admin.display(description="To'lov summasi", ordering="amount")
    def formatted_amount(self, obj):
        return f"{obj.amount:,.2f} UZS"