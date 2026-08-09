import io
import uuid
import base64
import secrets
import logging
from datetime import datetime

import qrcode

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from baseuser.models import BaseUser

logger = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================

def image_to_base64(image_field):
    """Django Image/FileField ni base64 ga aylantirish."""
    if not image_field or not image_field.name:
        return None
    try:
        with image_field.open('rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        logger.warning(f"Failed to convert image to base64: {e}")
        return None


def cert_upload_path(folder):
    return f"certificates/{folder}/%Y/%m/"


def generate_certificate_code():
    max_attempts = 10
    for _ in range(max_attempts):
        code = (
            f"CERT-"
            f"{datetime.now().strftime('%Y%m%d')}-"
            f"{secrets.token_hex(6).upper()}"
        )
        try:
            if not Certificate.objects.filter(certificate_code=code).exists():
                return code
        except Exception:
            continue
    raise RuntimeError("Could not generate unique certificate code after max attempts")


# ============================================================
# QUERYSET / MANAGER
# ============================================================

class CertificateQuerySet(models.QuerySet):
    def with_relations(self):
        return self.select_related("user", "template", "course", "test", "contest")

    def completed(self):
        return self.filter(status="completed")

    def processing(self):
        return self.filter(status="processing")

    def failed(self):
        return self.filter(status="failed")

    def pending(self):
        return self.filter(status="pending")


class CertificateManager(models.Manager):
    def get_queryset(self):
        return CertificateQuerySet(self.model, using=self._db)

    def with_relations(self):
        return self.get_queryset().with_relations()

    def completed(self):
        return self.get_queryset().completed()

    def pending(self):
        return self.get_queryset().pending()


# ============================================================
# CERTIFICATE TEMPLATE
# ============================================================

class CertificateTemplate(models.Model):
    class TemplateType(models.TextChoices):
        COURSE = ("course", "Course")
        TEST = ("test", "Test")
        CONTEST = ("contest", "Contest")
        DEFAULT = ("default", "Default")

    name = models.CharField(max_length=255)
    template_type = models.CharField(
        max_length=20, choices=TemplateType.choices,
        default=TemplateType.DEFAULT, db_index=True
    )
    organization_name = models.CharField(max_length=255, default="CfM Contest")
    verify_domain = models.CharField(max_length=255, default="platforma.uz")
    congratulation_text = models.TextField(default="Muvaffaqiyatli tamomlaganlik uchun berildi.")
    mentor_name = models.CharField(max_length=150, default="Platforma Mentori")
    mentor_status = models.CharField(max_length=150, default="Mentor")
    logo = models.ImageField(upload_to=cert_upload_path("logos"), null=True, blank=True)
    signature = models.ImageField(upload_to=cert_upload_path("signatures"), null=True, blank=True)
    background = models.ImageField(upload_to=cert_upload_path("backgrounds"), null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Certificate Template"
        verbose_name_plural = "Certificate Templates"
        constraints = [
            models.UniqueConstraint(
                fields=["template_type"],
                condition=models.Q(is_active=True),
                name="unique_active_certificate_template"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.template_type})"

    @classmethod
    def get_template(cls, template_type):
        cache_key = f"certificate_template:{template_type}"
        template = cache.get(cache_key)
        if template:
            return template

        template = cls.objects.filter(template_type=template_type, is_active=True).first()
        if not template:
            template = cls.objects.filter(
                template_type=cls.TemplateType.DEFAULT, is_active=True
            ).first()

        if template:
            cache.set(cache_key, template, 3600)
        return template

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f"certificate_template:{self.template_type}")


# ============================================================
# CERTIFICATE
# ============================================================

class Certificate(models.Model):
    class Status(models.TextChoices):
        PENDING = ("pending", "Pending")
        PROCESSING = ("processing", "Processing")
        COMPLETED = ("completed", "Completed")
        FAILED = ("failed", "Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        BaseUser, on_delete=models.CASCADE, related_name="certificates"
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.SET_NULL, null=True,
        blank=True, related_name="certificates"
    )
    test = models.ForeignKey(
        "quizs.Test", on_delete=models.SET_NULL, null=True,
        blank=True, related_name="certificates"
    )
    contest = models.ForeignKey(
        "contests.Contest", on_delete=models.SET_NULL, null=True,
        blank=True, related_name="certificates"
    )
    template = models.ForeignKey(
        CertificateTemplate, on_delete=models.SET_NULL, null=True,
        blank=True, related_name="certificates"
    )
    certificate_code = models.CharField(
        max_length=100, unique=True, editable=False, db_index=True
    )
    template_snapshot = models.JSONField(default=dict, blank=True)
    qr_code_image = models.ImageField(upload_to=cert_upload_path("qr"), null=True, blank=True)
    pdf_file = models.FileField(upload_to=cert_upload_path("pdf"), null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True
    )
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)
    issued_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = CertificateManager()

    class Meta:
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"
        ordering = ["-issued_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(course__isnull=False) |
                    models.Q(test__isnull=False) |
                    models.Q(contest__isnull=False)
                ),
                name="certificate_has_source"
            )
        ]

    def __str__(self):
        return f"{self.certificate_code} - {self.user}"

    # ---------------- VALIDATION ----------------

    def clean(self):
        sources = [self.course_id, self.test_id, self.contest_id]
        if not any(sources):
            raise ValidationError("Certificate uchun Course, Test yoki Contest tanlanishi kerak.")
        if sum(bool(item) for item in sources) > 1:
            raise ValidationError("Certificate faqat bitta manbaga tegishli bo'lishi kerak.")

    # ---------------- SOURCE ----------------

    @property
    def source_type(self):
        if self.course_id:
            return CertificateTemplate.TemplateType.COURSE
        if self.test_id:
            return CertificateTemplate.TemplateType.TEST
        if self.contest_id:
            return CertificateTemplate.TemplateType.CONTEST
        return CertificateTemplate.TemplateType.DEFAULT

    @property
    def source_object(self):
        if self.course_id:
            return self.course
        if self.test_id:
            return self.test
        if self.contest_id:
            return self.contest
        return None

    @property
    def source_title(self):
        obj = self.source_object
        if not obj:
            return "Certificate"
        return getattr(obj, "title", str(obj))

    @property
    def user_full_name(self):
        return (
            getattr(self.user, "full_name", None)
            or getattr(self.user, "username", None)
            or str(self.user)
        )

    @property
    def verify_url(self):
        domain = getattr(settings, "SITE_URL", "https://platforma.uz")
        return f"{domain.rstrip('/')}/certificates/verify/{self.certificate_code}/"

    def create_template_snapshot(self):
        if not self.template:
            return {}
        return {
            "organization_name": self.template.organization_name,
            "verify_domain": self.template.verify_domain,
            "congratulation_text": self.template.congratulation_text,
            "mentor_name": self.template.mentor_name,
            "mentor_status": self.template.mentor_status,
            "logo": self.template.logo.name if self.template.logo else None,
            "signature": self.template.signature.name if self.template.signature else None,
            "background": self.template.background.name if self.template.background else None,
        }

    # ---------------- FILE MANAGEMENT ----------------

    def clear_files(self):
        if self.pdf_file:
            self.pdf_file.delete(save=False)
            self.pdf_file = None
        if self.qr_code_image:
            self.qr_code_image.delete(save=False)
            self.qr_code_image = None

    # ---------------- GENERATION STATUS ----------------

    def start_generation(self):
        self.status = self.Status.PROCESSING
        self.error_message = None
        self.save(update_fields=["status", "error_message"])

    def generation_finished(self):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "pdf_file", "qr_code_image"])

    def generation_failed(self, exception):
        self.status = self.Status.FAILED
        self.error_message = str(exception)
        self.retry_count += 1
        self.save(update_fields=["status", "error_message", "retry_count"])

    def reset_for_regeneration(self):
        self.clear_files()
        self.status = self.Status.PROCESSING
        self.error_message = None
        self.retry_count = 0
        self.completed_at = None
        self.save(update_fields=[
            "status", "error_message", "retry_count",
            "completed_at", "pdf_file", "qr_code_image"
        ])

    # ---------------- QR GENERATION ----------------

    def generate_qr(self):
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(self.verify_url)
            qr.make(fit=True)

            image = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")

            filename = f"{self.certificate_code}.png"
            self.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=False)
        except Exception as e:
            logger.error(f"QR generation error: {e}", exc_info=True)
            raise

    # ---------------- RESULT METHODS (TO'G'RILANGAN) ----------------

    def get_test_result(self):
        """
        Test natijalarini user + test kombinatsiyasi orqali topadi.
        """
        if not self.test_id:
            return {}

        try:
            from quizs.models import TestSession

            session = TestSession.objects.filter(
                user=self.user,
                test=self.test,
                status="completed"
            ).order_by("-completed_at", "-total_xp_earned").first()

            if not session:
                return {}

            total_possible = getattr(session.test, "total_possible_xp", 0) or 1

            return {
                "score": session.score,
                "correct": session.correct_count,
                "wrong": session.wrong_count,
                "unanswered": session.unanswered_count,
                "total_xp_earned": session.total_xp_earned,
                "percentage": round((session.score / total_possible) * 100, 1) if total_possible else 0,
            }
        except Exception as e:
            logger.warning(f"get_test_result error: {e}")
            return {}

    def get_contest_result(self):
        """
        Contest natijalarini user + contest kombinatsiyasi orqali topadi.
        """
        if not self.contest_id:
            return {}

        try:
            from contests.models import ContestRegistration

            registration = ContestRegistration.objects.filter(
                user=self.user,
                contest=self.contest,
            ).order_by("-total_xp_earned").first()

            if not registration:
                return {}

            total_answered = registration.correct_count + registration.wrong_count
            accuracy = round((registration.correct_count / total_answered) * 100, 1) if total_answered else 0

            return {
                "rank": registration.rank,
                "xp": registration.total_xp_earned,
                "correct": registration.correct_count,
                "wrong": registration.wrong_count,
                "accuracy": accuracy,
            }
        except Exception as e:
            logger.warning(f"get_contest_result error: {e}")
            return {}

    # ---------------- PDF GENERATION (TO'G'RILANGAN) ----------------

    def generate_pdf(self):
        """
        WeasyPrint orqali HTML template dan PDF yaratadi.
        """
        snapshot = self.template_snapshot or {}

        logo_b64 = image_to_base64(self.template.logo) if self.template else None
        signature_b64 = image_to_base64(self.template.signature) if self.template else None
        qr_b64 = image_to_base64(self.qr_code_image)

        info_tags = []
        show_scores = False
        percentage = None
        correct_count = None
        total_questions = None
        total_xp_earned = None
        contest_rank = None

        # ---------- KURS ----------
        if self.source_type == CertificateTemplate.TemplateType.COURSE and self.course:
            info_tags.append(self.course.title)
            if self.course.total_modules_count:
                info_tags.append(f"{self.course.total_modules_count} modul")
            if self.course.total_lessons_count:
                info_tags.append(f"{self.course.total_lessons_count} dars")

        # ---------- TEST ----------
        elif self.source_type == CertificateTemplate.TemplateType.TEST and self.test:
            info_tags.append(self.test.title)
            if self.test.duration_minutes:
                info_tags.append(f"{self.test.duration_minutes} daqiqa")
            if self.test.question_count:
                info_tags.append(f"{self.test.question_count} savol")

            show_scores = True
            test_result = self.get_test_result()
            percentage = test_result.get("percentage")
            correct_count = test_result.get("correct")
            total_questions = getattr(self.test, "question_count", None)
            total_xp_earned = test_result.get("total_xp_earned")

        # ---------- CONTEST ----------
        elif self.source_type == CertificateTemplate.TemplateType.CONTEST and self.contest:
            info_tags.append(self.contest.title)
            participants = self.contest.registrations.count() if hasattr(self.contest, "registrations") else 0
            if participants:
                info_tags.append(f"{participants} ishtirokchi")

            show_scores = True
            contest_result = self.get_contest_result()
            contest_rank = contest_result.get("rank")
            total_xp_earned = contest_result.get("xp")
            percentage = contest_result.get("accuracy")

        context = {
            "certificate": self,
            "full_name": self.user_full_name,
            "title": self.source_title,
            "code": self.certificate_code,
            "verify_url": self.verify_url,
            "issued_date": self.issued_at.strftime("%d.%m.%Y") if self.issued_at else "",
            "organization_name": snapshot.get("organization_name", "CfM Contest"),
            "mentor_name": snapshot.get("mentor_name", "Platforma Mentori"),
            "mentor_status": snapshot.get("mentor_status", "Mentor"),
            "congratulation_text": snapshot.get("congratulation_text", ""),
            "logo_base64": logo_b64,
            "signature_base64": signature_b64,
            "qr_base64": qr_b64,
            "source_type": self.source_type,
            "info_tags": info_tags,
            "show_scores": show_scores,
            "percentage": percentage,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "total_xp_earned": total_xp_earned,
            "contest_rank": contest_rank,
        }

        html_string = render_to_string("certificates/certificate.html", context)

        buffer = io.BytesIO()
        HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf(buffer)

        filename = f"{self.certificate_code}.pdf"
        self.pdf_file.save(filename, ContentFile(buffer.getvalue()), save=False)

    # ---------------- CORE GENERATION FLOW ----------------

    def generate_files(self):
        """generate_certificate va regenerate_certificate uchun umumiy oqim."""
        self.start_generation()
        self.generate_qr()
        self.generate_pdf()
        self.generation_finished()

    # ---------------- SAVE ----------------

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if is_new:
            if not self.certificate_code:
                self.certificate_code = generate_certificate_code()

            if not self.template:
                self.template = CertificateTemplate.get_template(self.source_type)

            self.template_snapshot = self.create_template_snapshot()
            self.full_clean()

        super().save(*args, **kwargs)

        if is_new:
            from .tasks import generate_certificate_files
            transaction.on_commit(
                lambda: generate_certificate_files.delay(str(self.id))
            )

    # ---------------- DELETE ----------------

    def delete(self, *args, **kwargs):
        self.clear_files()
        super().delete(*args, **kwargs)


# ============================================================
# CACHE CLEANUP
# ============================================================

def delete_cached_template(template_type=None):
    if template_type:
        cache.delete(f"certificate_template:{template_type}")
    else:
        try:
            cache.delete_pattern("certificate_template:*")
        except AttributeError:
            for tmpl in CertificateTemplate.objects.filter(is_active=True):
                cache.delete(f"certificate_template:{tmpl.template_type}")