from django.urls import path
from .views import certificate_verify, certificate_download

app_name = "quizs"

urlpatterns = [
    path("verify/<str:code>/",   certificate_verify,   name="verify"),
    path("download/<str:code>/", certificate_download, name="download"),
]
