# baseuser/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Foydalanuvchini ham username, ham email orqali 
    Standart Django User modelidan autentifikatsiya qilish.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None
            
        try:
            # Standart Django User jadvalidan username yoki email bo'yicha qidiramiz
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).first()
            
        # Standart parolni tekshirish
        if user and user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
