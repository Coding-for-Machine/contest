from django.contrib import admin
from django.urls import include, path
from baseuser.views import admin_login_custom_otp, admin_otp_verify

urlpatterns = [
    path("admin/login/", admin_login_custom_otp, name="admin_login"),
    path("admin/otp-verify/", admin_otp_verify, name="admin_otp_verify"),
    path('admin/', admin.site.urls),
    path("certificates/", include("quizs.urls")),
    path("webhooks/", include("payment.urls")),

]
urlpatterns += [
    path("mdeditor/", include("mdeditor.urls")),
]


from django.shortcuts import render


def permission_denied_view(request, exception=None):
    """Django handler403 uchun custom view."""
    return render(request, '403.html', status=403)

handler403 = permission_denied_view