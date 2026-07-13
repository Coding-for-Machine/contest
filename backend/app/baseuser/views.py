# apps/users/views.py
import datetime
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import update_last_login  # 👈 Djangoning o'zini global metodini import qilamiz
from django.contrib import messages
from .models import BaseUser
from .services import auth_service
from .forms import BaseUserLoginForm

def admin_login_custom_otp(request):
    """
    1-BOSQICH: Token borligini tekshirish, agar bo'lmasa 
    Username/Email va Parolni BaseUserLoginForm orqali qat'iy authenticate qilish.
    Agar SUPERUSER kirsa, OTP sahifasiga yo'naltirmasdan birdan admin panelga kirgizadi.
    """
    # Foydalanuvchi allaqachon to'liq kirgan bo'lsa, to'g'ridan-to'g'ri ichkariga
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect("admin:index")

    if request.method == "POST":
        token = request.POST.get("token") or request.META.get("HTTP_AUTHORIZATION", "").replace("Bearer ", "")
        
        # ── A. TOKEN ORQALI TEZKOR VERIFY QILISH (AVTO LOG-IN) ──
        if token:
            is_valid, status_code = auth_service.verify_token(token)
            if is_valid and status_code == 200:
                user_data, user_status = auth_service.get_user_info(token)
                if user_status == 200 and "user" in user_data:
                    telegram_id = user_data["user"].get("user_id")
                    # Bu yerda faqat Django User autentifikatsiya bo'ladi
                    from django.contrib.auth.models import User
                    user = User.objects.filter(username=user_data["user"].get("username"), is_active=True).first()
                    
                    if user and (user.is_staff or user.is_superuser):
                        auth_login(request, user, backend='baseuser.backends.EmailOrUsernameModelBackend')
                        update_last_login(None, user)  # 👈 Standart xavfsiz vaqt yangilash
                        messages.success(request, f"Xush kelibsiz, {user.username}!")
                        return redirect("admin:index")
            
            messages.error(request, "Token eskirgan yoki ruxsatnomangiz yo'q! Iltimos, qayta kiring.")

        # ── B. FORMADAN LOGIN VA PAROL KIRITILGANDA ──
        form = BaseUserLoginForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # 🔥 ── AGAR SUPERUSER BO'LSA OTP-SIZ BIRDAN ADMIN PANELGA KIRADI ── 🔥
            if user.is_superuser or user.is_staff:
                auth_login(request, user, backend='baseuser.backends.EmailOrUsernameModelBackend')
                update_last_login(None, user)  # 👈 Standart xavfsiz vaqt yangilash (Xato bermaydi!)
                messages.success(request, f"Bosh administrator sifatida muvaffaqiyatli kirdingiz!")
                return redirect("admin:index")
                
            # Agar superuser bo'lmasa, demak u Staff User (O'qituvchi).
            # Uni pre-auth sessiyada muzlatib, OTP sahifasiga yo'naltiramiz.
            request.session["pre_auth_user_id"] = int(user.id)
            request.session.modified = True
            request.session.save()  
            
            return redirect("admin_otp_verify")
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
            for field, errors in form.errors.items():
                if field != '__all__':
                    for error in errors:
                        messages.error(request, error)
    else:
        form = BaseUserLoginForm(request=request)

    return render(request, "admin/login.html", {"form": form})


def admin_otp_verify(request):
    """
    2-BOSQICH: Staff userlar (O'qituvchilar) uchun 6 xonali OTP kodni Tashqi Serverga yuborish.
    """
    user_id = request.session.get("pre_auth_user_id")
    if not user_id:
        return redirect("admin_login")

    # Muzlatilgan user standart Django User jadvalidan olinadi
    from django.contrib.auth.models import User
    try:
        django_user = User.objects.get(id=int(user_id))
    except User.DoesNotExist:
        return redirect("admin_login")

    if request.method == "POST":
        otp_code = request.POST.get("token", "").strip()
        
        # Tashqi serverga OTP yuborish
        data, status_code = auth_service.login_with_otp(otp_code=otp_code)
        
        if status_code != 200:
            error_msg = data.get("error", "OTP kod noto'g'ri yoki muddati o'tgan!")
            messages.error(request, error_msg)
            return render(request, "two_factor/core/login.html")
            
        u = data.get("user", {})
        telegram_id = u.get("user_id")
        
        if not telegram_id:
            messages.error(request, "Xatolik: Auth serverdan foydalanuvchi IDsi qaytmadi.")
            return render(request, "two_factor/core/login.html")
            
        last_login_val = u.get("last_login")
        if last_login_val and isinstance(last_login_val, str):
            try:
                last_login_val = datetime.datetime.strptime(last_login_val, "%Y-%m-%d %H:%M:%S")
            except Exception:
                last_login_val = None

        user_data_dict = {
            "username": u.get("username", django_user.username),
            "phone": u.get("phone", ""),
            "full_name": u.get("full_name", ""),
            "last_login": last_login_val,
            "session_id": u.get("session_id"),
            "is_active": True,
        }
        
        # Parallel ravishda API foydalanuvchilari jadvalini (BaseUser) sinxron yangilash yoki yaratish
        base_user = BaseUser.objects.filter(telegram_id=telegram_id).first()
        if base_user:
            for key, value in user_data_dict.items():
                if hasattr(base_user, key) and value is not None:
                    setattr(base_user, key, value)
            base_user.save()
        else:
            try:
                BaseUser.objects.create(telegram_id=telegram_id, **user_data_dict)
            except Exception:
                pass

        # OTP to'g'ri bo'lsa standart xodimni tizimga kirgizish
        if django_user.is_staff or django_user.is_superuser:
            auth_login(request, django_user, backend='baseuser.backends.EmailOrUsernameModelBackend')
            update_last_login(None, django_user)  # 👈 Standart xavfsiz vaqt yangilash
            
            response = redirect("admin:index")
            if "token" in data:
                request.session["jwt_access_token"] = data["token"]
                response.set_cookie("jwt_token", data["token"], max_age=86400, httponly=True)
                
            messages.success(request, f"Xush kelibsiz, {django_user.username}!")
            return response
        else:
            messages.error(request, "Sizda boshqaruv paneliga (Staff) kirish huquqi yo'q!")

    return render(request, "two_factor/core/login.html")
