from django_bolt import Router, Request, Depends
from msgspec import Struct
from baseuser.models import BaseUser
from baseuser.authenticate import get_current_user_option
from quizs.models import Test

api = Router(tags=["Test API"])

class VideoStcut(Struct):
    id: int
    thumbnail: str | None
    hls_url: str | None
    duration: str

class TestList(Struct):
    id: int
    title: str
    slug: str
    duration: int
    question_count: int | 0
    min_pass_percentage: int | 60
    image: str | None
    
    


@api.get("/")
async def get_test_lest_api(request: Request, request_user: BaseUser | None = Depends(get_current_user_option)):
    test_data = await Test.objects.filter(is_active=True)
    if request_user:
        pass
    else:
        pass
    return