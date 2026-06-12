from django.contrib import admin

# Register your models here.
from .models import UserActivityDaily, UserStats, LessonStatus

admin.site.register(UserActivityDaily)
admin.site.register(UserStats)
admin.site.register(LessonStatus)
