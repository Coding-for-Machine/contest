import jwt
import datetime
import traceback
from ninja.security import HttpBearer
from django.http import HttpRequest
from django.conf import settings
from .models import BaseUser
from .services import auth_service
from decouple import config


SECRET_KEY=config('AUTH_SECRET_KEY')

"""
curl -X 'GET' \
  'http://localhost:8000/api/me' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uX2lkIjoxLCJ0ZWxlZ3JhbV9pZCI6NzE0MjkwODMzNCwicGhvbmVfbnVtYmVyIjoiOTk4OTc5NDM3Njc0IiwidXNlcm5hbWUiOiJDb2RpbmdfZm9yX01hY2hpbmVzIiwiZnVsbF9uYW1lIjoiQXNhZGJlayBcdWQ4M2RcdWRjM2UgXHUyNzI4Iiwic2VjcmV0X2tleSI6IklUTUM0N1FOTkNHQVJHUVdFNUs1RTdHMllOMlRHSUtJIiwiZXhwIjoxODExNDE0ODUwLCJpYXQiOjE3ODA2NTY0NTB9.jr7kJxWTBKi1ZQzDWHSr2ZRfXG8fuFbbE3rSC-S8tSY'
  """
class JWTAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str):
        try:
            # 1. Token decode
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

            telegram_id = payload.get("telegram_id")
            secret_key = payload.get("secret_key")
            phone_number = payload.get("phone_number")
            username = payload.get("username")
            full_name = payload.get("full_name")
            session_id = payload.get("session_id")
            iat = payload.get("iat")

            if not telegram_id:
                return None

            # 2. DB dan user tekshirish (SYNC ORM)
            user = BaseUser.objects.filter(
                telegram_id=telegram_id
            ).first()
            if user and not user.is_active:
                return None

            if user and user.iat == iat and user.secret_key == secret_key:
                # ok, status = auth_service.verify_token(token=token)
                # if not ok and  status!=200:
                #     return None
                return user
            # 3. Auth serverdan yangi ma'lumot olish (SYNC CALL)
            user_data, status = auth_service.get_user_info(token)

            if status != 200 or "user" not in user_data:
                return None

            u = user_data["user"]

            # 4. last_login parse
            last_login_val = u.get("last_login")
            if last_login_val:
                try:
                    if isinstance(last_login_val, str):
                        last_login_val = datetime.datetime.strptime(
                            last_login_val, "%Y-%m-%d %H:%M:%S"
                        )
                    elif isinstance(last_login_val, (int, float)):
                        last_login_val = datetime.datetime.fromtimestamp(
                            last_login_val
                        )
                except Exception:
                    last_login_val = None

            # 5. Data dictionary
            user_data_dict = {
                "telegram_id": int(u.get("user_id", telegram_id)),
                "username": u.get("username", username or ""),
                "phone": u.get("phone", phone_number or ""),
                "full_name": u.get("full_name", full_name or ""),
                "last_login": last_login_val,
                "session_id": u.get("session_id", session_id),
                "secret_key": secret_key or "",
                "iat": iat,
                "is_active": True,
            }

            user_data_dict = {
                k: v for k, v in user_data_dict.items() if v is not None
            }

            # 6. Update yoki create
            if user:
                for key, value in user_data_dict.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                user.save()
                return user

            else:
                try:
                    user = BaseUser.objects.create(**user_data_dict)
                    return user
                except Exception:
                    # Telefon orqali topish
                    user = BaseUser.objects.filter(
                        phone=user_data_dict.get("phone")
                    ).first()

                    if user:
                        for key, value in user_data_dict.items():
                            if hasattr(user, key):
                                setattr(user, key, value)
                        user.save()
                        return user

                    return None

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception:
            traceback.print_exc()
            return None
