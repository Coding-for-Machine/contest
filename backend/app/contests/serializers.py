from typing import List, Optional
from datetime import datetime
from django.utils import timezone
from django_bolt.serializers import Serializer, PositiveInt, NonNegativeInt
from contests.models import Contest

class UserSerializer(Serializer):
    id: PositiveInt
    username: str
    full_name: str

class ContestSerializer(Serializer):
    id: PositiveInt
    title: str
    description: str
    type: str
    status: str
    start_time: datetime
    end_time: datetime
    duration: str
    participants_count: NonNegativeInt = 0
    registration_count: NonNegativeInt = 0
    difficulty: str
    is_featured: bool = False
    registered: bool = False
    can_join: bool = False
    time_until_start: Optional[str] = None

    @classmethod
    def from_model(cls, contest: Contest, now: datetime):
        # Status mantiqi
        status = "upcoming" if now < contest.start_time else \
                 "ongoing" if now <= contest.end_time else "ended"
        
        # Ro'yxatdan o'tganlik (annotate orqali keladi)
        is_reg = getattr(contest, 'user_is_registered', False)
        
        # Vaqtni hisoblash (faqat upcoming uchun)
        time_until = None
        if status == "upcoming":
            diff = contest.start_time - now
            time_until = f"{diff.days} kun {diff.seconds//3600} soat"

        return cls(
            id=contest.id,
            title=contest.title,
            description=contest.description,
            type=contest.type,
            status=status,
            start_time=contest.start_time,
            end_time=contest.end_time,
            duration=contest.duration,
            participants_count=getattr(contest, 'part_count', 0),
            registration_count=getattr(contest, 'reg_count', 0),
            difficulty=contest.difficulty,
            is_featured=contest.is_featured,
            registered=is_reg,
            can_join=(status == "ongoing" and is_reg),
            time_until_start=time_until,
            _from_model=True
        )
