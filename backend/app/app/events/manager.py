import json
import threading
import queue
import time
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import weakref

class EventType(Enum):
    # Leaderboard events
    LEADERBOARD_UPDATE = "leaderboard.update" #data: {"rank": 1, "user": "Ali", "score": 1500}
    LEADERBOARD_RESET = "leaderboard.reset"
    RANK_CHANGE = "leaderboard.rank_change"
    
    # Submission events
    SUBMISSION_NEW = "submission.new"
    SUBMISSION_JUDGING = "submission.judging"
    SUBMISSION_JUDGED = "submission.judged"
    SUBMISSION_COMPILE_ERROR = "submission.compile_error"
    
    # Contest events
    CONTEST_START = "contest.start"
    CONTEST_END = "contest.end"
    CONTEST_FREEZE = "contest.freeze"
    CONTEST_UNFREEZE = "contest.unfreeze"
    TIME_WARNING = "contest.time_warning"
    
    # System events
    SYSTEM_ANNOUNCEMENT = "system.announcement"
    SYSTEM_MAINTENANCE = "system.maintenance"
    ERROR = "system.error"

@dataclass
class SSEMessage:
    """Standart SSE message formati"""
    event_type: str           # Event nomi (client tomonida)
    data: Any                 # Asosiy ma'lumot
    id: Optional[str] = None  # Event ID (reconnect uchun)
    retry: Optional[int] = None  # Reconnect timeout (ms)
    
    def to_sse_format(self) -> str:
        """SSE protocol formatiga o'tkazish"""
        lines = []
        
        if self.id:
            lines.append(f"id: {self.id}")
        
        if self.event_type != "message":  # default "message" bo'lsa qo'shmaymiz
            lines.append(f"event: {self.event_type}")
        
        # Data har doim JSON
        data_str = json.dumps(self.data, ensure_ascii=False, default=str)
        
        # Multi-line data qo'llab-quvvatlash
        for line in data_str.split('\n'):
            lines.append(f"data: {line}")
        
        if self.retry:
            lines.append(f"retry: {self.retry}")
        
        lines.append("")  # Bo'sh qator (SSE tugashi)
        return "\n".join(lines) + "\n"

class EventChannel:
    """Bitta kanal uchun subscriberlar"""
    def __init__(self, name: str, buffer_size: int = 100):
        self.name = name
        self.subscribers: Dict[str, queue.Queue] = {}
        self.lock = threading.RLock()
        self.buffer_size = buffer_size
        self._last_id = 0
        self._history: List[SSEMessage] = []
    
    def _next_id(self) -> str:
        self._last_id += 1
        return f"{self.name}-{self._last_id}"
    
    def subscribe(self, client_id: str, last_id: Optional[str] = None) -> queue.Queue:
        """Yangi subscriber qo'shish"""
        with self.lock:
            q = queue.Queue(maxsize=self.buffer_size)
            self.subscribers[client_id] = q
            
            # Reconnect bo'lsa, o'tgan eventlarni yuborish
            if last_id:
                missed = self._get_missed_events(last_id)
                for msg in missed:
                    try:
                        q.put(msg, block=False)
                    except queue.Full:
                        break
            
            return q
    
    def unsubscribe(self, client_id: str):
        """Subscriberni olib tashlash"""
        with self.lock:
            self.subscribers.pop(client_id, None)
    
    def publish(self, message: SSEMessage):
        """Barcha subscriberlarga yuborish"""
        with self.lock:
            message.id = message.id or self._next_id()
            self._history.append(message)
            # History limit
            if len(self._history) > self.buffer_size:
                self._history = self._history[-self.buffer_size:]
            
            # Barcha subscriberlarga yuborish
            dead_clients = []
            for client_id, q in self.subscribers.items():
                try:
                    q.put(message, block=False)
                except queue.Full:
                    dead_clients.append(client_id)
            
            # To'la queue'larni tozalash
            for cid in dead_clients:
                self.subscribers.pop(cid, None)
    
    def _get_missed_events(self, last_id: str) -> List[SSEMessage]:
        """Reconnect uchun o'tgan eventlarni qaytarish"""
        try:
            # ID format: "channel-N"
            parts = last_id.split('-')
            if len(parts) == 2 and parts[0] == self.name:
                last_num = int(parts[1])
                return [m for m in self._history 
                        if int(m.id.split('-')[1]) > last_num]
        except (ValueError, IndexError):
            pass
        return []

class EventManager:
    """Global event manager — singleton"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._channels: Dict[str, EventChannel] = {}
                    cls._instance._global_lock = threading.RLock()
        return cls._instance
    
    def get_channel(self, name: str) -> EventChannel:
        """Kanal olish yoki yaratish"""
        with self._global_lock:
            if name not in self._channels:
                self._channels[name] = EventChannel(name)
            return self._channels[name]
    
    def publish(self, channel_name: str, message: SSEMessage):
        """Kanalga event yuborish"""
        channel = self.get_channel(channel_name)
        channel.publish(message)
    
    def subscribe(self, channel_name: str, client_id: str, 
                  last_id: Optional[str] = None) -> queue.Queue:
        """Kanalga obuna bo'lish"""
        channel = self.get_channel(channel_name)
        return channel.subscribe(client_id, last_id)
    
    def unsubscribe(self, channel_name: str, client_id: str):
        """Obunani bekor qilish"""
        channel = self.get_channel(channel_name)
        channel.unsubscribe(client_id)
    
    def get_stats(self) -> Dict:
        """Monitoring uchun statistika"""
        with self._global_lock:
            return {
                name: {
                    'subscribers': len(ch.subscribers),
                    'history_size': len(ch._history),
                    'last_id': ch._last_id
                }
                for name, ch in self._channels.items()
            }

# Global instance
event_manager = EventManager()