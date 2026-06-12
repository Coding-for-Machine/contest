from ninja import NinjaAPI
from django.utils import timezone  # ✅ IMPORT QILISH KERAK!
from contests.views import router as contests_router
from problems.views import api as problems_api
from courses.api import course_api
from quizs.api import quiz_api
# from submissions.views import api as submit
from baseuser.authenticate import JWTAuth

api = NinjaAPI(
    title="Contest API",
    version="1.0.0",
    description="Dasturlash tanlovlari API",
    docs_url="/docs/",
)

# Public endpoints (auth=None router da)
api.add_router("/", contests_router)
api.add_router("/", problems_api)
api.add_router("/courses", course_api)
api.add_router("/quizs", quiz_api)
# api.add_router("/submit", submit)

# Health check
@api.get("/health", auth=None)
async def health_check(request):
    return {
        "status": "ok",
        "time": timezone.now().isoformat(),  # ✅ Endi ishlaydi!
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