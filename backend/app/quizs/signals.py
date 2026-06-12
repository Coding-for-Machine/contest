from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Max
from .models import TestSession, Test, CertificateTemplate, Certificate, UserRank
from courses.models import Lesson

@receiver(post_save, sender=TestSession)
def auto_grant_certificate_and_rank_signal(sender, instance, created, **kwargs):
    """
    Sessiya tugashi bilan ishga tushib, barcha hisob-kitoblar va 
    sertifikatlashtirishni dinamik va tezkor amalga oshiruvchi universal signal.
    """
    if instance.status != TestSession.Status.COMPLETED:
        return

    user = instance.user

    # 1. FOYDALANUVCHINING REYTINGINI VA XP BALLARINI OShIRISH
    rank_profile, _ = UserRank.objects.get_or_create(user=user)
    rank_profile.total_xp += instance.total_xp_earned
    rank_profile.update_level()

    # 2. MUSTAQIL TEST UCHUN SERTIFIKAT TIZIMI
    if instance.test and not instance.test.lesson:
        try:
            template = CertificateTemplate.objects.get(test=instance.test)
            if instance.percentage >= template.min_percentage:
                Certificate.objects.get_or_create(
                    user=user,
                    test_session=instance,
                    defaults={'template': template}
                )
        except CertificateTemplate.DoesNotExist:
            pass

    # 3. KURS SERTIFIKATINI PROFESSIONAL VA DINAMIK TEKSHIRISH
    elif instance.test and instance.test.lesson:
        course = instance.test.lesson.course
        
        try:
            template = CertificateTemplate.objects.get(course=course)
            
            # Kurs ichidagi barcha faol testlar sonini olamiz
            total_tests = Test.objects.filter(lesson__course=course, is_active=True).count()
            
            if total_tests > 0:
                # 💥 ASOSIY OPTIMIZATSIYA (SQL GROUP BY)
                # Talabaning ushbu kursdagi har bir test bo'yicha olgan eng yuqori foizlari
                user_best_results = TestSession.objects.filter(
                    user=user,
                    test__lesson__course=course,
                    status=TestSession.Status.COMPLETED
                ).values('test_id').annotate(best_pct=Max('percentage'))
                
                # Kurs testlarining o'tish shartlari: {test_id: min_pass_percentage}
                test_passing_map = {
                    t['id']: t['min_pass_percentage'] 
                    for t in Test.objects.filter(lesson__course=course, is_active=True).values('id', 'min_pass_percentage')
                }
                
                successful_passes = 0
                for res in user_best_results:
                    t_id = res['test_id']
                    if t_id in test_passing_map and res['best_pct'] >= test_passing_map[t_id]:
                        successful_passes += 1

                # Agar talaba kursdagi hamma testlardan muvaffaqiyatli o'tgan bo'lsa
                if successful_passes >= total_tests:
                    Certificate.objects.get_or_create(
                        user=user,
                        course=course,
                        defaults={'template': template}
                    )
                    
        except CertificateTemplate.DoesNotExist:
            pass