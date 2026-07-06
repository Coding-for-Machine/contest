# certificates/models.py - TO'LIQ TUZATILGAN VERSION

import base64
import io
import uuid
import logging
import secrets
from datetime import datetime

import qrcode
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import escape
from django.core.cache import cache
from weasyprint import HTML
from baseuser.models import BaseUser

logger = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================

def _cert_upload(subdir):
    return f"certificates/{subdir}/%Y/%m/"


def _load_image_as_b64(image_field) -> str:
    """Rasmni base64 ga o'tkazish - xatoliklarni log qiladi"""
    if not image_field:
        return ""
    
    try:
        if not image_field.storage.exists(image_field.name):
            logger.warning(f"Rasm mavjud emas: {image_field.name}")
            return ""
            
        image_field.open("rb")
        result = base64.b64encode(image_field.read()).decode("utf-8")
        image_field.close()
        return result
        
    except FileNotFoundError:
        logger.error(f"Rasm topilmadi: {image_field.name}")
        return ""
    except Exception as e:
        logger.error(f"Rasm yuklashda xatolik: {e}", exc_info=True)
        return ""


def _generate_cert_code() -> str:
    """Xavfsiz va noyob sertifikat kodi"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # 50 marta urinish
    for _ in range(50):
        random_part = secrets.token_hex(8).upper()
        candidate = f"CERT-{timestamp}-{random_part}"
        
        if not Certificate.objects.filter(certificate_code=candidate).exists():
            return candidate
    
    # Fallback
    return f"CERT-{timestamp}-{uuid.uuid4().hex[:8].upper()}"


def _safe_get_attr(obj, attr, default=None):
    """Attribute xavfsiz olish - method ham bo'lishi mumkin"""
    if obj is None:
        return default
    
    try:
        value = getattr(obj, attr, default)
        
        if callable(value):
            # Django model emasligini tekshirish
            if not hasattr(value, '_meta'):
                try:
                    return value()
                except TypeError:
                    logger.debug(f"Method argument talab qiladi: {attr}")
                    return default
        return value
        
    except (AttributeError, TypeError, ValueError) as e:
        logger.debug(f"_safe_get_attr xatolik: {attr} - {e}")
        return default


def _safe_get_related_count(obj, related_name):
    """Related obyektlar sonini xavfsiz olish"""
    if obj is None:
        return None
    try:
        related = getattr(obj, related_name, None)
        if related is not None:
            return related.count()
        return None
    except (AttributeError, TypeError) as e:
        logger.debug(f"_safe_get_related_count xatolik: {related_name} - {e}")
        return None


# ============================================================
# CERTIFICATE TEMPLATE
# ============================================================

class CertificateTemplate(models.Model):
    class TemplateType(models.TextChoices):
        COURSE  = "course",  "Kurs uchun"
        TEST    = "test",    "Test (Imtihon) uchun"
        CONTEST = "contest", "Musobaqa uchun"
        DEFAULT = "default", "Umumiy shablon"

    name = models.CharField("Shablon nomi", max_length=255)
    template_type = models.CharField(
        "Shablon turi", max_length=20,
        choices=TemplateType.choices,
        default=TemplateType.DEFAULT,
        unique=True, db_index=True,
    )
    organization_name = models.CharField("Tashkilot nomi", max_length=255, default="Platforma.uz")
    verify_domain = models.CharField("Tekshiruv domen", max_length=255, default="platforma.uz")
    congratulation_text = models.TextField(
        "Tabrik matni",
        default="Muvaffaqiyatli tamomlaganlik uchun berildi.",
    )
    mentor_name = models.CharField("Mentor ismi", max_length=150, default="cfm")
    mentor_status = models.CharField("Mentor lavozimi", max_length=150, default="Kurs Mentori")
    mentor_signature = models.ImageField(
        "Mentor imzosi (PNG)", upload_to=_cert_upload("signatures"), null=True, blank=True
    )
    logo_image = models.ImageField(
        "Platforma logotipi", upload_to=_cert_upload("logos"), null=True, blank=True
    )
    illustration_image = models.ImageField(
        "Bezak rasmi", upload_to=_cert_upload("illustrations"), null=True, blank=True
    )

    class Meta:
        verbose_name = "Sertifikat Sozlamasi"
        verbose_name_plural = "Sertifikat Sozlamalari"

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

    @classmethod
    def get_for_type(cls, type_key: str) -> "CertificateTemplate":
        """Template olish - caching bilan"""
        cache_key = f"cert_template_{type_key}"
        obj = cache.get(cache_key)
        
        if obj is None:
            obj = cls.objects.filter(template_type=type_key).first()
            if obj is None:
                obj = cls.objects.filter(template_type=cls.TemplateType.DEFAULT).first()
            
            # DEFAULT ham yo'q bo'lsa, yaratish
            if obj is None:
                obj = cls.objects.create(
                    name="Default Template",
                    template_type=cls.TemplateType.DEFAULT,
                )
                logger.warning(f"Default template yaratildi: {obj.pk}")
            
            cache.set(cache_key, obj, 3600 * 24)  # 1 kun
        
        return obj


# ============================================================
# CERTIFICATE
# ============================================================

class Certificate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        BaseUser, on_delete=models.CASCADE, related_name="certificates"
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="issued_certificates",
    )
    test = models.ForeignKey(
        "quizs.Test", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="issued_test_certificates",
    )
    test_session = models.OneToOneField(
        "quizs.TestSession", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="issued_test_certificate",
    )
    contest = models.ForeignKey(
        "contests.Contest", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="issued_contest_certificates",
    )
    contest_registration = models.OneToOneField(
        "contests.ContestRegistration", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="issued_certificate",
    )
    
    certificate_code = models.CharField(
        "Sertifikat kodi", max_length=100, unique=True, blank=True, db_index=True
    )
    qr_code_image = models.ImageField(
        "QR Kod", upload_to=_cert_upload("qrcodes"), blank=True, null=True
    )
    pdf_file = models.FileField(
        "PDF Fayl", upload_to=_cert_upload("pdfs"), blank=True, null=True
    )
    issued_at = models.DateTimeField("Berilgan vaqti", auto_now_add=True)
    
    # Yangi maydonlar
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Kutilmoqda'),
            ('processing', 'Jarayonda'),
            ('completed', 'Tayyor'),
            ('failed', 'Xatolik'),
        ],
        default='pending',
        db_index=True,
    )
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Berilgan Sertifikat"
        verbose_name_plural = "Berilgan Sertifikatlar"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.certificate_code} — {self.user}"

    # ----------------------------------------------------------
    # VALIDATION
    # ----------------------------------------------------------

    def clean(self):
        if not any([self.course_id, self.test_id, self.contest_id]):
            raise ValidationError(
                "Sertifikat uchun kamida bitta manba "
                "(Kurs, Test yoki Musobaqa) ko'rsatilishi shart."
            )

    # ----------------------------------------------------------
    # PROPERTIES
    # ----------------------------------------------------------

    @property
    def source_title(self) -> str:
        if self.course_id:
            return _safe_get_attr(self.course, "title", "Kurs")
        if self.test_id:
            return _safe_get_attr(self.test, "title", "Test")
        if self.contest_id:
            return _safe_get_attr(self.contest, "title", "Musobaqa")
        return "Maxsus Yo'nalish"

    @property
    def source_type(self) -> str:
        if self.course_id:
            return CertificateTemplate.TemplateType.COURSE
        if self.test_id:
            return CertificateTemplate.TemplateType.TEST
        if self.contest_id:
            return CertificateTemplate.TemplateType.CONTEST
        return CertificateTemplate.TemplateType.DEFAULT

    @property
    def verify_url(self) -> str:
        site_url = getattr(settings, "SITE_URL", "https://platforma.uz").rstrip("/")
        return f"{site_url}/certificates/verify/{self.certificate_code}/"

    # ----------------------------------------------------------
    # SAVE
    # ----------------------------------------------------------

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["qr_code_image", "pdf_file", "certificate_code"])
        
        if not self.certificate_code:
            self.certificate_code = _generate_cert_code()
        
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Celery task ga yuborish
        if is_new or not self.qr_code_image or not self.pdf_file:
            from .tasks import generate_certificate_pdf
            transaction.on_commit(
                lambda: generate_certificate_pdf.delay(str(self.pk))
            )

    # ----------------------------------------------------------
    # QR
    # ----------------------------------------------------------

    def _generate_qr(self):
        """QR kod yaratish"""
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(self.verify_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            self._qr_bytes = buf.getvalue()  # ✅ Tuzatish: _qr_bytes set qilindi
            
            self.qr_code_image.save(
                f"qr-{self.certificate_code}.png",
                ContentFile(self._qr_bytes),
                save=False,
            )
            logger.info(f"[CERT] QR yaratildi: {self.pk}")
            
        except Exception as e:
            logger.error(f"[CERT] QR generatsiya xatolik: {e}", exc_info=True)
            raise

    def _get_qr_b64(self) -> str:
        """QR kodni base64 da qaytarish"""
        # 1. _qr_bytes dan olish
        if hasattr(self, "_qr_bytes") and self._qr_bytes:
            return base64.b64encode(self._qr_bytes).decode("utf-8")
        
        # 2. qr_code_image dan olish
        if self.qr_code_image:
            try:
                self.qr_code_image.open("rb")
                result = base64.b64encode(self.qr_code_image.read()).decode("utf-8")
                self.qr_code_image.close()
                return result
            except Exception as e:
                logger.warning(f"QR o'qishda xatolik: {e}")
        
        # 3. Yangi QR yaratish
        try:
            self._generate_qr()
            if hasattr(self, "_qr_bytes") and self._qr_bytes:
                return base64.b64encode(self._qr_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"QR yaratishda xatolik: {e}")
        
        return ""  # fallback

    # ----------------------------------------------------------
    # SCORE CONTEXT
    # ----------------------------------------------------------

    def _get_score_context(self) -> dict:
        if not self.test_session_id or not self.test_session:
            return {
                "score": None,
                "correct_count": None,
                "wrong_count": None,
                "unanswered_count": None,
                "total_questions": None,
                "total_xp_earned": None,
                "percentage": None,
            }
        
        ts = self.test_session
        total = (ts.correct_count or 0) + (ts.wrong_count or 0) + (ts.unanswered_count or 0)
        
        percentage = None
        if hasattr(ts, "calculate_percentage"):
            try:
                percentage = round(ts.calculate_percentage(), 1)
            except Exception as e:
                logger.warning(f"Percentage hisoblashda xatolik: {e}")
        
        return {
            "score": ts.score,
            "correct_count": ts.correct_count,
            "wrong_count": ts.wrong_count,
            "unanswered_count": ts.unanswered_count,
            "total_questions": total if total > 0 else None,
            "total_xp_earned": ts.total_xp_earned,
            "percentage": percentage,
        }

    def _get_contest_score_context(self) -> dict:
        if not self.contest_registration_id or not self.contest_registration:
            return {
                "contest_correct_count": None,
                "contest_wrong_count": None,
                "contest_unanswered_count": None,
                "contest_total_xp": None,
                "contest_rank": None,
                "contest_accuracy": None,
            }
        
        reg = self.contest_registration
        return {
            "contest_correct_count": reg.correct_count,
            "contest_wrong_count": reg.wrong_count,
            "contest_unanswered_count": reg.unanswered_count,
            "contest_total_xp": reg.total_xp_earned,
            "contest_rank": reg.rank,
            "contest_accuracy": getattr(reg, "accuracy_percent", None),
        }

    # ----------------------------------------------------------
    # EXTRA CONTEXT
    # ----------------------------------------------------------

    def _get_course_info(self) -> dict:
        if not self.course:
            return {}
        info = {
            "title": _safe_get_attr(self.course, "title", ""),
            "description": _safe_get_attr(self.course, "description", ""),
            "price": _safe_get_attr(self.course, "price", None),
            "is_active": _safe_get_attr(self.course, "is_active", False),
        }
        if hasattr(self.course, "level"):
            info["level"] = _safe_get_attr(self.course, "level", None)
        if hasattr(self.course, "category"):
            info["category"] = _safe_get_attr(self.course, "category", None)
        
        info["modules_count"] = _safe_get_related_count(self.course, "modullar")
        info["lessons_count"] = _safe_get_related_count(self.course, "lessons")
        info["enrollments_count"] = _safe_get_related_count(self.course, "enrollments")
        return info

    def _get_test_info(self) -> dict:
        if not self.test:
            return {}
        info = {
            "title": _safe_get_attr(self.test, "title", ""),
            "duration_minutes": _safe_get_attr(self.test, "duration_minutes", 0),
            "question_count": _safe_get_attr(self.test, "question_count", 0),
            "min_pass_percentage": _safe_get_attr(self.test, "min_pass_percentage", 60),
            "penalty_coefficient": _safe_get_attr(self.test, "penalty_coefficient", 0),
        }
        if hasattr(self.test, "total_possible_xp"):
            info["total_possible_xp"] = _safe_get_attr(self.test, "total_possible_xp", None)
        return info

    def _get_contest_info(self) -> dict:
        if not self.contest:
            return {}
        info = {
            "title": _safe_get_attr(self.contest, "title", ""),
            "description": _safe_get_attr(self.contest, "description", ""),
            "start_time": _safe_get_attr(self.contest, "start_time", None),
            "end_time": _safe_get_attr(self.contest, "end_time", None),
        }
        if hasattr(self.contest, "pass_score_percent"):
            info["pass_score_percent"] = _safe_get_attr(self.contest, "pass_score_percent", 50)
        info["participants_count"] = _safe_get_attr(self.contest, "participants_count", None)
        info["duration_minutes"] = _safe_get_attr(self.contest, "duration_minutes", 0)
        return info

    def _get_extra_context(self) -> dict:
        extra = {
            "course_info": self._get_course_info(),
            "test_info": self._get_test_info(),
            "contest_info": self._get_contest_info(),
        }
        extra.update(self._get_contest_score_context())
        return extra

    # ----------------------------------------------------------
    # GENERATE DESCRIPTION - HTML XAVFSIZ
    # ----------------------------------------------------------

    def _generate_description(self) -> str:
        """Tavsif matni - HTML escape qilingan"""
        full_name = escape(self.user.full_name or self.user.username or str(self.user))
        title = escape(self.source_title)
        
        # ── COURSE ──────────────────────────────────────────
        if self.source_type == CertificateTemplate.TemplateType.COURSE:
            course = self.course
            modules_count = _safe_get_related_count(course, "modullar")
            lessons_count = _safe_get_related_count(course, "lessons")
            enrollments_count = _safe_get_related_count(course, "enrollments")
            
            parts = [
                f"<strong>{full_name}</strong> tomonidan "
                f"<strong>\"{title}\"</strong> nomli kurs to'liq o'rganildi "
                f"va barcha amaliy topshiriqlar muvaffaqiyatli bajarildi."
            ]
            
            if modules_count and lessons_count:
                parts.append(
                    f"Kurs <strong>{modules_count} ta bob</strong> va "
                    f"<strong>{lessons_count} ta darsdan</strong> iborat bo'lib, "
                    f"har bir bo'lim chuqur o'zlashtirildi."
                )
            elif modules_count:
                parts.append(
                    f"Kurs <strong>{modules_count} ta bob</strong>ni o'z ichiga oladi."
                )
            
            if enrollments_count and enrollments_count > 10:
                parts.append(
                    f"Ushbu kursda <strong>{enrollments_count} nafar</strong> talaba "
                    f"tahsil olgan bo'lib, sertifikat egasi yuqori natijalar bilan "
                    f"o'quv dasturini yakunladi."
                )
            else:
                parts.append(
                    "Nazariy bilimlar va amaliy ko'nikmalar yuqori darajada "
                    "o'zlashtirilganligi tasdiqlandi."
                )
            
            return " ".join(parts)
        
        # ── TEST / IMTIHON ───────────────────────────────────
        elif self.source_type == CertificateTemplate.TemplateType.TEST:
            test = self.test
            score_ctx = self._get_score_context()
            percentage = score_ctx.get("percentage")
            correct = score_ctx.get("correct_count")
            total = score_ctx.get("total_questions")
            min_pass = _safe_get_attr(test, "min_pass_percentage", 60)
            duration = _safe_get_attr(test, "duration_minutes", 0)
            
            parts = [
                f"<strong>{full_name}</strong> tomonidan "
                f"<strong>\"{title}\"</strong> imtihoni muvaffaqiyatli topshirildi."
            ]
            
            if percentage is not None and correct is not None and total:
                parts.append(
                    f"Jami <strong>{total} ta savoldan</strong> "
                    f"<strong>{correct} tasiga</strong> to'g'ri javob berildi "
                    f"va yakuniy natija <strong>{percentage}%</strong> ni tashkil etdi."
                )
            
            if min_pass:
                parts.append(
                    f"Imtihondan o'tish uchun talab etilgan minimal ko'rsatkich "
                    f"<strong>{min_pass}%</strong> bo'lib, "
                    f"sertifikat egasi ushbu talabni to'liq qondirdi."
                )
            
            if duration:
                parts.append(
                    f"Test <strong>{duration} daqiqa</strong> muddatda o'tkazildi."
                )
            
            return " ".join(parts)
        
        # ── CONTEST / MUSOBAQA ──────────────────────────────
        elif self.source_type == CertificateTemplate.TemplateType.CONTEST:
            contest = self.contest
            reg = self.contest_registration
            rank = _safe_get_attr(reg, "rank", None)
            accuracy = _safe_get_attr(reg, "accuracy_percent", None)
            total_xp = _safe_get_attr(reg, "total_xp_earned", None)
            participants = _safe_get_attr(contest, "participants_count", None)
            
            parts = [
                f"<strong>{full_name}</strong> tomonidan "
                f"<strong>\"{title}\"</strong> nomli musobaqada faol ishtirok etildi."
            ]
            
            if rank:
                if rank <= 3:
                    rank_text = {1: "birinchi", 2: "ikkinchi", 3: "uchinchi"}.get(rank)
                    parts.append(
                        f"Musobaqa yakunida ishtirokchi "
                        f"<strong>{rank_text} o'rinni</strong> qo'lga kiritdi."
                    )
                else:
                    parts.append(
                        f"Musobaqa yakunida ishtirokchi "
                        f"<strong>{rank}-o'ringa</strong> sazovor bo'ldi."
                    )
            
            if participants:
                parts.append(
                    f"Musobaqada jami <strong>{participants} nafar</strong> "
                    f"ishtirokchi qatnashdi."
                )
            
            if accuracy is not None:
                parts.append(
                    f"Javoblar aniqligi <strong>{accuracy}%</strong> darajasida bo'ldi."
                )
            
            if total_xp:
                parts.append(
                    f"Ushbu musobaqada <strong>{total_xp} XP</strong> ball to'plandi."
                )
            
            parts.append("Yuqori bilim darajasi va sport ruhi namoyish etildi.")
            return " ".join(parts)
        
        # ── DEFAULT ─────────────────────────────────────────
        return (
            f"<strong>{full_name}</strong> tomonidan <strong>\"{title}\"</strong> "
            "yo'nalishi bo'yicha professional o'quv dasturi, amaliy laboratoriya ishlari "
            "hamda yakuniy loyiha muvaffaqiyatli tamomlandi. "
            "Barcha talablar to'liq bajarildi va bilim darajasi tasdiqlandi."
        )

    # ----------------------------------------------------------
    # GENERATE PDF
    # ----------------------------------------------------------

    def _generate_pdf(self):
        """PDF fayl yaratish"""
        try:
            tpl = CertificateTemplate.get_for_type(self.source_type)
            
            contest_rank = None
            contest_accuracy = None
            if self.contest_registration:
                contest_rank = _safe_get_attr(self.contest_registration, "rank", None)
                contest_accuracy = _safe_get_attr(self.contest_registration, "accuracy_percent", None)
            
            context = {
                # Asosiy
                "full_name": self.user.full_name or self.user.username or str(self.user),
                "title": self.source_title,
                "source_type": self.source_type,
                "date": (self.issued_at or timezone.now()).strftime("%Y-yil, %d-%B"),
                "code": self.certificate_code,
                "verify_url": self.verify_url,
                # Tavsif
                "description_text": self._generate_description(),
                # QR
                "qr_base64": self._get_qr_b64(),
                # Template sozlamalari
                "organization_name": tpl.organization_name,
                "verify_domain": tpl.verify_domain,
                "congratulation_text": tpl.congratulation_text,
                "mentor_name": tpl.mentor_name,
                "mentor_status": tpl.mentor_status,
                # Rasmlar
                "logo_base64": _load_image_as_b64(tpl.logo_image),
                "signature_base64": _load_image_as_b64(tpl.mentor_signature),
                "illustration_base64": _load_image_as_b64(tpl.illustration_image),
                # Test natijasi
                **self._get_score_context(),
                # Qo'shimcha
                **self._get_extra_context(),
                # Contest
                "contest_rank": contest_rank,
                "contest_accuracy": contest_accuracy,
            }
            
            html_str = render_to_string("certificates/cert_template.html", context)
            buf = io.BytesIO()
            
            # WeasyPrint options
            HTML(string=html_str).write_pdf(
                buf,
                presentational_hints=True,
                # optimize_size parametrini olib tashlaymiz
            )

            
            self.pdf_file.save(
                f"cert-{self.certificate_code}.pdf",
                ContentFile(buf.getvalue()),
                save=False,
            )
            logger.info(f"[CERT] PDF yaratildi: {self.pk}")
            
        except Exception as e:
            logger.error(f"[CERT] PDF generatsiya xatolik: {e}", exc_info=True)
            raise