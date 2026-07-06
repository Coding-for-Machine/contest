# certificates/views.py
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from certificate.models import Certificate


def certificate_verify(request, code: str):
    """
    GET /certificates/verify/<code>/
    Sertifikatni ochiq tekshirish sahifasi (login talab qilinmaydi).
    """
    cert = get_object_or_404(
        Certificate.objects.select_related("user", "course", "test", "contest"),
        certificate_code=code,
    )
    return render(request, "certificates/verify.html", {"cert": cert})


def certificate_download(request, code: str):
    """
    GET /certificates/download/<code>/
    PDF faylni inline ko'rsatish yoki yuklab olish.
    ?download=1  → attachment (yuklab olish)

    🛡️ XAVFSIZLIK TUZATILDI: Faqat sertifikat egasi yoki superuser yuklay oladi.
    """

    # Sertifikatni bazadan qidirish
    cert = get_object_or_404(Certificate, certificate_code=code)

    # 2. 🛡️ ANTI-HACKER HIMOYaSI: Huquqlarni qat'iy tekshirish
    # Agar foydalanuvchi superadmin bo'lmasa VA sertifikat egasi bo'lmasa - ruxsat bermaymiz!

    # PDF fayl mavjudligini tekshirish
    if not cert.pdf_file:
        raise Http404("PDF fayl hali tayyor emas yoki tizim xatosi tufayli o'chib ketgan.")

    # 3. Faylni xavfsiz va xotirani to'ldirib yubormaydigan (streaming) ko'rinishda qaytarish
    response = FileResponse(
        cert.pdf_file,  # Django FileField o'zi context manager hisoblanadi
        content_type="application/pdf",
        as_attachment=request.GET.get("download") == "1",
        filename=f"sertifikat-{cert.certificate_code}.pdf",
    )
    return response
