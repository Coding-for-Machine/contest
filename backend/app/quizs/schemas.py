
import uuid
from typing import List, Optional, Literal
from datetime import datetime
from ninja import Schema
from pydantic import BaseModel, field_validator

class TestFilterSchema(BaseModel):
    search: Optional[str] = None
    status: Optional[Literal["active", "upcoming", "ended"]] = None

class TestListOut(BaseModel):
    id: int
    title: str
    duration_minutes: int
    question_count: int
    start_time: datetime
    end_time: datetime
    min_pass_percentage: int
    max_attempts: int
    attempts_left: int
    user_status: str  # not_started, in_progress, completed
    best_score: Optional[float] = None
    class Config:
        from_attributes = True

        
class ChoiceOut(Schema):
    id: int
    text: str
    order: int
    
    class Config:
        from_attributes = True

class QuestionOut(Schema):
    id: int
    text: str
    difficulty: str
    xp: int
    order: int
    choices: List[ChoiceOut]

    class Config:
        from_attributes = True

    # Pydantic v2 uchun validator (RelatedManager-ni listga o'tkazish):
    @field_validator('choices', mode='before')
    @classmethod
    def convert_related_manager_to_list(cls, value):
        if hasattr(value, 'all'):  # Agar RelatedManager bo'lsa
            return list(value.all())
        return value
    
    
class TestStartOut(BaseModel):
    session_id: uuid.UUID
    duration_minutes: int
    seconds_left: int
    questions: List[QuestionOut]
    class Config:
        from_attributes = True
class UserResponseIn(BaseModel):
    question_id: int
    selected_choice_id: Optional[int] = None

class TestSubmitPayload(BaseModel):
    test_id: int
    answers: List[UserResponseIn]

class TestResultOut(BaseModel):
    session_id: uuid.UUID
    score: float
    correct_count: int
    wrong_count: int
    unanswered_count: int
    rank_level: str
    is_passed: bool
    certificate_issued: bool
    certificate_url: Optional[str] = None

class HistoryOut(BaseModel):
    session_id: uuid.UUID
    test_title: str
    score: float
    status: str
    completed_at: Optional[datetime] = None

class CertificateOut(BaseModel):
    id: uuid.UUID
    test_title: str
    certificate_code: str
    pdf_url: Optional[str] = None
    issued_at: datetime

class LeaderboardUserOut(BaseModel):
    username: str
    total_xp: int
    level_display: str
