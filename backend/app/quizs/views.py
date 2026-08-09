# certificates/views.py
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from certificate.models import Certificate


def certificate_verify(request, code: str):
    """
    GET /certificates/verify/<code>/
    Sertifikatni ochiq tekshirish sahifasi (login talab qilinmaydi).
    Bu sahifa OMMAVIY — istalgan kishi sertifikat haqiqiyligini tekshira oladi.
    """
    cert = get_object_or_404(
        Certificate.objects.select_related("user", "course", "test", "contest"),
        certificate_code=code,
    )
    return render(request, "certificates/verify.html", {"cert": cert})


@login_required
def certificate_download(request, code: str):
    """
    GET /certificates/download/<code>/
    PDF faylni inline ko'rsatish yoki yuklab olish.
    ?download=1  → attachment (yuklab olish)

    XAVFSIZLIK: Faqat quyidagilar yuklay oladi:
      - Sertifikat egasi (cert.user == request.user)
      - Superuser / staff
    Boshqa har qanday login qilgan (yoki qilmagan) foydalanuvchi uchun 403.
    """
    cert = get_object_or_404(
        Certificate.objects.select_related("user"),
        certificate_code=code,
    )

    # --- Ruxsatni QAT'IY tekshirish ---
    is_owner = cert.user_id == request.user.id
    is_privileged = request.user.is_superuser or request.user.is_staff

    if not (is_owner or is_privileged):
        raise PermissionDenied(
            "Bu sertifikatni yuklab olishga ruxsatingiz yo'q."
        )

    # PDF fayl mavjudligini tekshirish
    if not cert.pdf_file:
        raise Http404("PDF fayl hali tayyor emas yoki tizim xatosi tufayli o'chib ketgan.")

    # Faylni xavfsiz, xotirani to'ldirmaydigan (streaming) ko'rinishda qaytarish
    response = FileResponse(
        cert.pdf_file.open("rb"),
        content_type="application/pdf",
        as_attachment=request.GET.get("download") == "1",
        filename=f"sertifikat-{cert.certificate_code}.pdf",
    )
    return response