"""
Jonli baholash servisi — real-time, har bir nomzod uchun.

Kalibratsiya snapshot ENDI services/sessions.py:start_session() da
o'rnatiladi. Bu yerda faqat SHU snapshotdan foydalaniladi — agar u
biror sababdan bo'sh bo'lsa (masalan, eski, ushbu tuzatishdan oldingi
sessiya), pastda tavsiflangan zaxira (fallback) yo'liga o'tiladi.
"""
import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

UNCALIBRATED_PROVISIONAL_RATIO = 0.2


def get_item_betas_for_calibration(calibration, question_ids: list[int]) -> dict[int, float]:
    """
    BERILGAN (frozen) kalibratsiya versiyasi uchun {question_id: beta}.
    Kalibratsiya immutable bo'lgani uchun to'liq lug'at uzoq muddat keshlanadi.
    """
    from .cache_utils import get_cached_calibration_betas, set_cached_calibration_betas
    from ..models import RaschItemParameter

    if calibration is None:
        return {}

    betas = get_cached_calibration_betas(calibration.id)
    if betas is None:
        betas = dict(
            RaschItemParameter.objects
            .filter(calibration=calibration, is_calibrated=True)
            .values_list("question_id", "beta")
        )
        set_cached_calibration_betas(calibration.id, betas)

    return {qid: betas[qid] for qid in question_ids if qid in betas}


def score_session(session, requesting_user=None):
    """Sessiyani yakunlaydi: javoblarni yig'adi, θ hisoblaydi, darajaga o'giradi."""
    from .cache_utils import schedule_recalibration_check
    from .rasch_core import calculate_person_fit, estimate_theta_map
    from ..models import TestSession, UserResponse, UserSubjectAbility

    if requesting_user is not None and session.user_id != requesting_user.id:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Bu sizning seansingiz emas.")

    with transaction.atomic():
        session = (
            TestSession.objects
            .select_related("test", "test__subject", "rasch_calibration", "scoring_policy")
            .select_for_update()
            .get(pk=session.pk)
        )

        if session.status == TestSession.Status.COMPLETED:
            logger.info("Sessiya allaqachon yakunlangan: %s", session.id)
            return session

        subject = session.test.subject
        question_ids = list(
            session.session_questions.order_by("order").values_list("question_id", flat=True)
        )

        if not question_ids:
            _save_empty_session(session)
            return session

        # === Snapshot kalibratsiya (start_session'da o'rnatilgan) ===
        calibration = session.rasch_calibration
        if calibration is None:
            # Zaxira yo'l: eski sessiya yoki hali umuman kalibratsiya bo'lmagan holat.
            # Buni provisional deb belgilaymiz — chunki bu "frozen" snapshot emas.
            calibration = subject.get_active_calibration()
            logger.warning(
                "Session %s snapshot calibrationsiz yaratilgan edi — fallback ishlatilmoqda.",
                session.id,
            )

        policy = session.scoring_policy or subject.scoring_policies.filter(is_active=True).first()
        betas = get_item_betas_for_calibration(calibration, question_ids)

        responses = list(
            UserResponse.objects.filter(session=session, question_id__in=question_ids).select_related("choice")
        )
        response_map = {r.question_id: r for r in responses}

        scoring_pairs = []
        correct_count = wrong_count = unanswered_count = uncalibrated_count = 0

        for question_id in question_ids:
            response = response_map.get(question_id)

            if response is None or response.choice_id is None:
                unanswered_count += 1
                continue

            is_correct = bool(response.choice.is_correct)
            if is_correct:
                correct_count += 1
            else:
                wrong_count += 1

            if question_id in betas:
                scoring_pairs.append((betas[question_id], is_correct))
            else:
                uncalibrated_count += 1

        answered_count = correct_count + wrong_count
        raw_percentage = round((correct_count / answered_count * 100.0), 2) if answered_count else 0.0

        if scoring_pairs:
            theta, se, converged, _ = estimate_theta_map(
                scoring_pairs,
                prior_variance=subject.rasch_prior_variance,
                theta_min=subject.rasch_theta_min,
                theta_max=subject.rasch_theta_max,
            )
            person_infit, person_outfit = calculate_person_fit(theta, scoring_pairs)
        else:
            theta = se = person_infit = person_outfit = None
            converged = False

        if scoring_pairs and policy:
            scaled = policy.theta_to_scaled(theta)
            grade, grade_description = policy.get_grade(scaled)
        else:
            scaled = 0.0
            grade, grade_description = "NC", "Baholanmadi"

        total_answered = len(scoring_pairs) + uncalibrated_count
        is_provisional = (
            not scoring_pairs
            or calibration is None
            or (total_answered > 0 and (uncalibrated_count / total_answered) > UNCALIBRATED_PROVISIONAL_RATIO)
        )

        session.rasch_theta = theta
        session.rasch_se = se
        session.rasch_converged = converged
        session.person_infit = person_infit
        session.person_outfit = person_outfit
        session.scaled_score = scaled
        session.grade = grade
        session.grade_description = grade_description
        session.is_provisional = is_provisional
        session.uncalibrated_question_count = uncalibrated_count
        session.raw_percentage = raw_percentage
        session.correct_count = correct_count
        session.wrong_count = wrong_count
        session.unanswered_count = unanswered_count
        session.status = TestSession.Status.COMPLETED
        session.completed_at = timezone.now()
        session.save()

        if scoring_pairs and not is_provisional and calibration:
            _update_ability_cache(session, subject, calibration)

    schedule_recalibration_check(subject.id)
    return session


def _save_empty_session(session) -> None:
    from ..models import TestSession

    session.rasch_theta = None
    session.rasch_se = None
    session.scaled_score = 0.0
    session.grade, session.grade_description = "NC", "Baholanmadi"
    session.is_provisional = True
    session.status = TestSession.Status.COMPLETED
    session.completed_at = timezone.now()
    session.save(update_fields=[
        "rasch_theta", "rasch_se", "scaled_score", "grade", "grade_description",
        "is_provisional", "status", "completed_at",
    ])


def _update_ability_cache(session, subject, calibration) -> None:
    from ..models import UserSubjectAbility

    UserSubjectAbility.objects.update_or_create(
        user=session.user, subject=subject,
        defaults={
            "theta": session.rasch_theta,
            "theta_se": session.rasch_se,
            "person_infit": session.person_infit,
            "person_outfit": session.person_outfit,
            "calibration": calibration,
            "calibration_version": calibration.version,
            "response_count": session.correct_count + session.wrong_count,
            "correct_count": session.correct_count,
        },
    )


def get_test_information(session) -> dict:
    """Testning qaysi θ diapazonda aniqroq o'lchayotganini qaytaradi (GRE uslubidagi TIF egri chizig'i)."""
    from .rasch_core import test_information_function
    import numpy as np

    calibration = session.rasch_calibration
    if calibration is None:
        return {"error": "Kalibratsiya mavjud emas"}

    betas = list(calibration.item_parameters.filter(is_calibrated=True).values_list("beta", flat=True))
    thetas = np.linspace(-4, 4, 17)
    info_curve = [
        {"theta": round(float(t), 2), "information": test_information_function(float(t), betas)}
        for t in thetas
    ]
    return {
        "max_info_theta": round(float(thetas[int(np.argmax([c["information"] for c in info_curve]))]), 2),
        "info_curve": info_curve,
    }