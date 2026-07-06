# events.py
import msgspec
import uuid
from typing import Union
from datetime import datetime

class BaseEvent(msgspec.Struct):
    """Barcha eventlar uchun asosiy ota klass (OOP - Encapsulation & Inheritance)"""
    id: str = msgspec.field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = msgspec.field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Har bir bola klass o'zining tarqatilish turini belgilaydi: "private" o'rniga default
    scope: str = "private" 

# --- SHAXSIY EVENTLAR (Private Scope) ---

class NotificationEvent(BaseEvent, tag="notification"):
    title: str
    message: str

class RunEvent(BaseEvent, tag="run"):
    status: str          # Masalan: "started", "finished", "failed"
    execution_time: float = 0.0

class Submits(BaseEvent, tag="submits"):
    submission_id: int
    result: str          # Masalan: "accepted", "wrong_answer"

# --- GLOBAL EVENTLAR (Global Scope) ---

class BroadcastEvent(BaseEvent, tag="broadcast"):
    # OOP Overriding: Global xabarlar uchun scope'ni avtomatik o'zgartiramiz
    scope: str = "global"
    title: str
    content: str


# Hamma yaratilgan klasslarni Union ichiga kiritish shart (msgspec shuni talab qiladi)
AppEvent = Union[
    NotificationEvent, 
    BroadcastEvent, 
    RunEvent, 
    Submits
]

def serialize_event(event: AppEvent) -> str:
    """Obyektni JSON matniga o'tkazish"""
    return msgspec.json.encode(event).decode('utf-8')
