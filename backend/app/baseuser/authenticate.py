import datetime
import jwt
from decouple import config
from django_bolt import Request
from django_bolt.exceptions import HTTPException

from .models import BaseUser

SECRET_KEY = config('AUTH_SECRET_KEY')

def _parse_last_login(value) -> datetime.datetime | None:
    """last_login qiymatini datetime ga o'giradi."""
    if not value:
        return None
    try:
        if isinstance(value, str):
            return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if isinstance(value, (int, float)):
            return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)
    except Exception:
        return None
    return None

def _build_user_dict(raw: dict, telegram_id: int) -> dict:
    """Auth server response maydonlarini BaseUser modeliga moslaydi."""
    return {k: v for k, v in {
        "telegram_id": int(raw.get("id", telegram_id)),
        "username":    raw.get("u") or "",
        "phone":       raw.get("p") or "",
        "full_name":   raw.get("f") or "",
        "last_login":  _parse_last_login(raw.get("l")),
        "is_active":   True,
    }.items() if v is not None}

async def _save_or_update_user(user: BaseUser | None, data: dict) -> BaseUser | None:
    """Foydalanuvchini bazaga saqlaydi yoki yangilaydi (async ORM)."""
    if user:
        for key, value in data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await user.asave()
        await user.arefresh_from_db()
        return user

    try:
        new_user = await BaseUser.objects.acreate(**data)
        await new_user.arefresh_from_db()
        return new_user
    except Exception:
        existing = await BaseUser.objects.filter(phone=data.get("phone")).afirst()
        if existing:
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await existing.asave()
            await existing.arefresh_from_db()
            return existing
        return None

async def _fetch_from_auth_server(token: str) -> dict | None:
    """Auth serverdan foydalanuvchi ma'lumotini oladi."""
    from .services import auth_service
    raw_data, status = await auth_service.get_user_info(token)
    if status != 200:
        return None
    return raw_data


# ============================================================
# FAQAT SHU IKKITA FUNKSIYA QOLDIRILDI
# ============================================================

# 1. MAJBURIY AUTH — token bo'lmasa yoki xato bo'lsa 401/403 qaytaradi
async def get_current_user(request: Request) -> BaseUser:
    """Token majburiy. Yaroqsiz yoki yo'q bo'lsa HTTPException ko'taradi."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization sarlavhasi topilmadi!")

    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Token formati noto'g'ri (Bearer <token>)!")

    token = parts[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token yaroqsiz yoki muddati o'tgan: {e}")

    telegram_id = payload.get("telegram_id")
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Token ichida telegram_id yo'q!")

    user = await BaseUser.objects.filter(telegram_id=telegram_id).afirst()

    if user and not user.is_active:
        raise HTTPException(status_code=403, detail="Foydalanuvchi hisobi bloklangan!")

    if user:
        return user

    raw_data = await _fetch_from_auth_server(token)
    if not raw_data:
        raise HTTPException(status_code=401, detail="Auth server tokenni tasdiqlamadi!")

    final_user = await _save_or_update_user(None, _build_user_dict(raw_data, telegram_id))
    if not final_user:
        raise HTTPException(status_code=500, detail="Foydalanuvchini bazaga yozishda xatolik!")

    return final_user


# 2. IXTIYORIY AUTH — token bo'lmasa yoki xato bo'lsa None qaytaradi
async def get_current_user_option(request: Request) -> BaseUser | None:
    """
    Token ixtiyoriy. Xato bo'lsa None qaytaradi.
    Faqat bloklangan foydalanuvchi (403) uchun exception ko'taradi.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        return None

    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return None

    telegram_id = payload.get("telegram_id")
    if not telegram_id:
        return None

    user = await BaseUser.objects.filter(telegram_id=telegram_id).afirst()

    if user and not user.is_active:
        raise HTTPException(status_code=403, detail="Foydalanuvchi hisobi bloklangan!")

    if user:
        return user

    raw_data = await _fetch_from_auth_server(token)
    if not raw_data:
        return None

    try:
        return await _save_or_update_user(None, _build_user_dict(raw_data, telegram_id))
    except Exception:
        return None


# 2. GLOBAL SSE STREAM UCHUN (URL Query Param orqali auth)
async def get_current_user_from_url(request: Request) -> BaseUser:
    """Majburiy auth: Tokenni URL query parametridan (?token=...) o'qiydi."""
    query_params = request.get("query", {})
    token = query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="URL tarkibida token topilmadi!")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token yaroqsiz yoki muddati o'tgan: {e}")

    telegram_id = payload.get("telegram_id")
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Token ichida telegram_id yo'q!")

    user = await BaseUser.objects.filter(telegram_id=telegram_id).afirst()

    if user and not user.is_active:
        raise HTTPException(status_code=403, detail="Foydalanuvchi hisobi bloklangan!")

    if user:
        return user

    raw_data = await _fetch_from_auth_server(token)
    if not raw_data:
        raise HTTPException(status_code=401, detail="Auth server tokenni tasdiqlamadi!")

    final_user = await _save_or_update_user(None, _build_user_dict(raw_data, telegram_id))
    if not final_user:
        raise HTTPException(status_code=500, detail="Foydalanuvchini bazaga yozishda xatolik!")

    return final_user