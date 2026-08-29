"""
Sessiya boshlash servisi.

MUHIM TUZATISH (avvalgi versiyalarda topilgan bug): kalibratsiya snapshot
ENDI sessiya BOSHLANGANDA olinadi, TUGAGANDA emas. Shunday qilib, agar
test davomida yangi kalibratsiya faollashtirilib qolsa ham, allaqachon
boshlangan sessiyalar eski (o'zlari boshlagan) versiya bilan baholanadi —
bir xil paytda test topshirayotgan ikki kishi turli qoidalar bilan
baholanib qolmaydi.
"""
import random

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone


def start_session(user, test):
    """
    Yangi test seansini boshlaydi:
      1. is_available va max_attempts tekshiradi
      2. Savollarni tanlaydi (random_questions_count hisobga olinadi)
      3. Kalibratsiya va baholash siyosatini SHU PAYTDA "muzlatadi" (snapshot)
    """
    from ..models import RaschCalibration, ScoringPolicy, Test, TestSession, TestSessionQuestion

    if not test.is_available:
        raise ValidationError("Test hozircha mavjud emas (hali boshlanmagan yoki allaqachon yopilgan).")

    if test.max_attempts > 0:
        attempts_used = TestSession.objects.filter(user=user, test=test).count()
        if attempts_used >= test.max_attempts:
            raise PermissionDenied(
                f"Maksimal urinishlar soniga ({test.max_attempts}) yetdingiz."
            )

    with transaction.atomic():
        all_questions = list(test.questions.filter(is_active=True))
        if not all_questions:
            raise ValidationError("Testda faol savollar mavjud emas.")

        if test.random_questions_count and test.random_questions_count < len(all_questions):
            selected = random.sample(all_questions, test.random_questions_count)
        else:
            selected = all_questions

        # === SNAPSHOT — sessiya boshlanayotgan PAYTDAGI holat ===
        calibration = test.subject.get_active_calibration()
        policy = test.subject.scoring_policies.filter(is_active=True).first()

        session = TestSession.objects.create(
            user=user,
            test=test,
            rasch_calibration=calibration,
            scoring_policy=policy,
        )

        TestSessionQuestion.objects.bulk_create([
            TestSessionQuestion(session=session, question=q, order=i)
            for i, q in enumerate(selected)
        ])

    return session