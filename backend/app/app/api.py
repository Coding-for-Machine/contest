from django.http import Http404, JsonResponse
from ninja import NinjaAPI
from django.utils import timezone
from ninja.errors import HttpError
from contests.views import router as contests_router
from problems.views import api as problems_api
from courses.api import course_api
from quizs.api import router as quize_router
# from submissions.views import api as submit
from baseuser.authenticate import JWTAuth

api = NinjaAPI(
    title="CfM Contest API",
    version="1.0.0",
    description="Dasturlash tanlovlari API",
    docs_url="/docs/",
    openapi_url="/openapi.json"
)


# Public endpoints (auth=None router da)
api.add_router("/", contests_router)
api.add_router("/", problems_api)
api.add_router("/courses", course_api)
api.add_router("/quizs", quize_router)
# api.add_router("/submit", submit)

# Health check
@api.get("/health", auth=None)
async def health_check(request):
    return {
        "status": "ok",
        "time": timezone.now().isoformat(),
        "service": "Contest API"
    }
@api.get("/me", auth=JWTAuth())
async def get_me(request):
    # 'authenticate' metodidan qaytgan 'user' obyekti 
    # avtomatik ravishda request.auth ichida bo'ladi
    user = request.auth
    return {
        "username": user.username,
        "telegram_id": user.telegram_id,
        "full_name": user.full_name
    }

class NotFoundError(Exception):
    def __init__(self, message="Resource not found"):
        self.message = message

# 🛠 1. HttpError uchun maxsus handler qo'shamiz (400, 403 va h.k. xatolar to'g'ri qaytishi uchun)
@api.exception_handler(HttpError)
def ninja_http_error_handler(request, exc):
    return api.create_response(request, {"detail": exc.message}, status=exc.status_code)

@api.exception_handler(NotFoundError)
def not_found_handler(request, exc):
    return api.create_response(request, {"detail": exc.message}, status=404)

@api.exception_handler(Http404)
def django_404_handler(request, exc):
    return api.create_response(request, {"detail": "Not found"}, status=404)

@api.exception_handler(Exception)
def generic_error_handler(request, exc):
    import logging
    logging.exception("Unhandled exception")
    return api.create_response(request, {"detail": str(exc)}, status=500)