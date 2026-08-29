"""
Rasch kalibratsiya servisi — offline, davriy.

O'lchov modeli: User = PERSON, Question = ITEM, TestSession = ATTEMPT.
Bir userning bir nechta sessiyasi alohida person hisoblanmaydi —
response_policy qaysi attemptdan foydalanishni belgilaydi.

TUZATILGAN MUAMMOLAR (avvalgi versiyalarga nisbatan):
  - _select_sessions_by_policy: Python loop + N ta DB so'rov o'rniga,
    endi Subquery/OuterRef bilan BITTA so'rovda bajariladi.
  - Duplicate person topilganda ENDI RaschCalibration.REJECTED audit
    yozuvi bilan saqlanadi (avval jimgina None qaytarib, iz qoldirmasdi).
  - converged endi haqiqatan tekshiriladi (check_calibration_convergence).
"""
import logging
from typing import Optional

import numpy as np
from django.db import transaction
from django.db.models import Max, Min, OuterRef, Subquery
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    from girth import rasch_mml, tag_missing_data
    GIRTH_AVAILABLE = True
except ImportError:
    GIRTH_AVAILABLE = False
    logger.warning("girth kutubxonasi o'rnatilmagan. Rasch kalibratsiya ishlamaydi.")

SUPPORTED_POLICIES = {"first_attempt_only", "last_attempt_only", "best_attempt_only", "all_sessions"}
CONNECTIVITY_MIN_RATIO = 0.8  # eng katta komponent item'larning kamida shuncha foizini qamrab olishi kerak


# ============================================================
# SESSION SELECTION — bitta so'rov (Subquery), N+1 yo'q
# ============================================================

def _select_sessions_by_policy(subject, policy: str, max_persons: Optional[int] = None) -> list:
    from ..models import TestSession

    if policy not in SUPPORTED_POLICIES:
        logger.warning("Noma'lum response_policy=%s. first_attempt_only ishlatiladi.", policy)
        policy = "first_attempt_only"

    base_qs = TestSession.objects.filter(
        test__subject=subject,
        status__in=[TestSession.Status.COMPLETED, TestSession.Status.EXPIRED],
        user__isnull=False,
    )

    if policy == "all_sessions":
        logger.warning("all_sessions policy ishlatilmoqda — production uchun tavsiya qilinmaydi.")
        qs = base_qs.order_by("started_at", "id")

    elif policy == "first_attempt_only":
        earliest = base_qs.filter(user_id=OuterRef("user_id")).order_by("started_at", "id").values("id")[:1]
        qs = base_qs.filter(id=Subquery(earliest)).order_by("started_at")

    elif policy == "last_attempt_only":
        latest = base_qs.filter(user_id=OuterRef("user_id")).order_by("-started_at", "-id").values("id")[:1]
        qs = base_qs.filter(id=Subquery(latest)).order_by("-started_at")

    else:  # best_attempt_only
        best = (
            base_qs.filter(user_id=OuterRef("user_id"))
            .order_by("-raw_percentage", "-started_at", "-id")
            .values("id")[:1]
        )
        qs = base_qs.filter(id=Subquery(best))

    if max_persons is not None:
        qs = qs[:max_persons]

    return list(qs)


def _validate_unique_persons(sessions: list, policy: str) -> dict:
    user_ids = [s.user_id for s in sessions if s.user_id is not None]
    unique_user_ids = set(user_ids)
    duplicates = len(user_ids) - len(unique_user_ids)
    valid = duplicates == 0 or policy == "all_sessions"

    return {
        "valid": valid,
        "total_sessions": len(sessions),
        "unique_users": len(unique_user_ids),
        "duplicate_sessions": duplicates,
    }


# ============================================================
# ITEM CONNECTIVITY
# ============================================================

def check_item_connectivity(selected_sessions: list, questions: list) -> dict:
    """
    Savollar orasidagi bog'lanishni USER overlap orqali tekshiradi
    (bir xil userga javob berilgan savollar bir komponentga tegishli).
    """
    from collections import defaultdict, deque
    from ..models import TestSessionQuestion

    if not questions:
        return {"connected": False, "components": 0, "largest_component": 0, "total_items": 0, "isolated_items": []}

    session_ids = [s.id for s in selected_sessions]
    session_to_user = {s.id: s.user_id for s in selected_sessions if s.user_id is not None}
    question_ids = [q.id for q in questions]

    question_users = defaultdict(set)
    rows = (
        TestSessionQuestion.objects
        .filter(session_id__in=session_ids, question_id__in=question_ids)
        .values_list("session_id", "question_id")
    )
    for session_id, question_id in rows:
        user_id = session_to_user.get(session_id)
        if user_id is not None:
            question_users[question_id].add(user_id)

    adjacency = {qid: set() for qid in question_ids}
    for idx, q1 in enumerate(question_ids):
        users_q1 = question_users.get(q1, set())
        for q2 in question_ids[idx + 1:]:
            if users_q1 & question_users.get(q2, set()):
                adjacency[q1].add(q2)
                adjacency[q2].add(q1)

    visited, components = set(), []
    for qid in question_ids:
        if qid in visited:
            continue
        component, queue = [], deque([qid])
        visited.add(qid)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        components.append(component)

    largest = max((len(c) for c in components), default=0)
    isolated = [c[0] for c in components if len(c) == 1]

    return {
        "connected": len(components) == 1,
        "components": len(components),
        "largest_component": largest,
        "total_items": len(question_ids),
        "isolated_items": isolated,
    }


# ============================================================
# RESPONSE DATASET
# ============================================================

def _build_calibration_response_data(questions: list, selected_sessions: list):
    from ..models import TestSessionQuestion, UserResponse

    question_ids = [q.id for q in questions]
    session_ids = [s.id for s in selected_sessions]
    session_to_user = {s.id: s.user_id for s in selected_sessions if s.user_id is not None}

    user_ids, seen_users = [], set()
    for session in selected_sessions:
        if session.user_id is not None and session.user_id not in seen_users:
            seen_users.add(session.user_id)
            user_ids.append(session.user_id)

    valid_session_questions = set(
        TestSessionQuestion.objects
        .filter(session_id__in=session_ids, question_id__in=question_ids)
        .values_list("session_id", "question_id")
    )

    responses = (
        UserResponse.objects
        .filter(session_id__in=session_ids, question_id__in=question_ids, choice__isnull=False)
        .select_related("choice")
    )

    response_data, seen_responses = [], set()
    for response in responses:
        user_id = session_to_user.get(response.session_id)
        if user_id is None:
            continue
        key = (user_id, response.question_id)
        if key in seen_responses:
            continue
        if (response.session_id, response.question_id) not in valid_session_questions:
            continue
        seen_responses.add(key)
        response_data.append((response.question_id, user_id, bool(response.choice.is_correct)))

    return user_ids, response_data


# ============================================================
# CALIBRATE SUBJECT — asosiy funksiya
# ============================================================

def calibrate_subject(
    subject_id: int, response_policy: str = "first_attempt_only", max_persons: Optional[int] = None
):
    from .rasch_core import build_response_matrix, calculate_item_fit, check_calibration_convergence, flag_item
    from ..models import Question, RaschCalibration, RaschItemParameter, Subject

    if not GIRTH_AVAILABLE:
        logger.error("girth o'rnatilmagan. Kalibratsiya bajarilmadi.")
        return None

    subject = Subject.objects.get(id=subject_id)
    questions = list(Question.objects.filter(subject=subject, is_active=True).order_by("id"))
    sessions = _select_sessions_by_policy(subject, response_policy, max_persons)
    person_validation = _validate_unique_persons(sessions, response_policy)

    version = (subject.rasch_calibrations.order_by("-version").values_list("version", flat=True).first() or 0) + 1

    # === TUZATISH: har doim audit yozuvi yaratiladi, hech qachon "jim" None qaytarilmaydi ===
    calibration = RaschCalibration.objects.create(
        subject=subject, version=version,
        response_policy=response_policy, data_cutoff_at=timezone.now(),
        item_count=len(questions), status=RaschCalibration.Status.RUNNING,
    )

    if response_policy != "all_sessions" and not person_validation["valid"]:
        return _reject(calibration, (
            f"Datasetda duplicate person topildi: sessions={person_validation['total_sessions']} "
            f"users={person_validation['unique_users']} duplicates={person_validation['duplicate_sessions']}. "
            f"Bu — response_policy noto'g'ri ishlaganini bildiradi, dasturchiga xabar bering."
        ))

    unique_users = person_validation["unique_users"]
    if unique_users < subject.rasch_min_persons or not questions:
        return _reject(calibration, (
            f"Yetarli ma'lumot yo'q: {unique_users} nafar unique person "
            f"(kerak: {subject.rasch_min_persons}), {len(questions)} savol."
        ))

    user_ids, response_data = _build_calibration_response_data(questions, sessions)
    if not user_ids:
        return _reject(calibration, "Calibration datasetda hech qanday person topilmadi.")

    connectivity = check_item_connectivity(sessions, questions)
    if not connectivity["connected"] and connectivity["largest_component"] < len(questions) * CONNECTIVITY_MIN_RATIO:
        return _reject(calibration, (
            f"Item connectivity yetarli emas: {connectivity['components']} ta komponent, "
            f"eng kattasi {connectivity['largest_component']}/{connectivity['total_items']}. "
            f"Anchor savollar kerak (turli test-shakllar orasida umumiy savollar bo'lishi kerak)."
        ))

    question_id_list = [q.id for q in questions]
    matrix = build_response_matrix(question_id_list, user_ids, response_data)
    response_count = int(np.sum(~np.isnan(matrix)))

    if response_count == 0:
        return _reject(calibration, "Calibration uchun hech qanday valid response topilmadi.")

    try:
        cleaned = tag_missing_data(matrix, [0, 1])
        result = rasch_mml(cleaned)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Rasch kalibratsiyasi muvaffaqiyatsiz: subject=%s", subject_id)
        return _fail(calibration, str(exc))

    difficulties = np.asarray(result["Difficulty"], dtype=float)
    abilities = np.asarray(result["Ability"], dtype=float)

    if len(difficulties) != len(questions):
        return _fail(calibration, "Rasch natijasidagi item soni question soniga mos kelmadi.")

    converged = check_calibration_convergence(difficulties, abilities)
    if not converged:
        return _fail(calibration, "Kalibratsiya barqaror yaqinlashmadi (ekstremal yoki cheksiz qiymatlar).")

    _save_item_parameters(calibration, questions, difficulties, matrix, abilities, calculate_item_fit, flag_item)

    with transaction.atomic():
        calibration.sample_size = unique_users
        calibration.response_count = response_count
        calibration.mean_beta = round(float(np.mean(difficulties)), 4)
        calibration.std_beta = round(float(np.std(difficulties)), 4)
        calibration.min_beta = round(float(np.min(difficulties)), 4)
        calibration.max_beta = round(float(np.max(difficulties)), 4)
        calibration.converged = True
        calibration.status = RaschCalibration.Status.COMPLETED
        calibration.completed_at = timezone.now()
        calibration.save()

    logger.info(
        "Rasch calibration yakunlandi: subject=%s v%d items=%d persons=%d responses=%d policy=%s",
        subject_id, version, len(questions), unique_users, response_count, response_policy,
    )
    return calibration


def _reject(calibration, reason: str):
    from ..models import RaschCalibration
    calibration.status = RaschCalibration.Status.REJECTED
    calibration.rejection_reason = reason
    calibration.save(update_fields=["status", "rejection_reason"])
    logger.warning("Kalibratsiya rad etildi (v%d, subject=%s): %s", calibration.version, calibration.subject_id, reason)
    return calibration


def _fail(calibration, reason: str):
    from ..models import RaschCalibration
    calibration.status = RaschCalibration.Status.FAILED
    calibration.rejection_reason = reason
    calibration.save(update_fields=["status", "rejection_reason"])
    logger.error("Kalibratsiya xatolik bilan tugadi (v%d, subject=%s): %s", calibration.version, calibration.subject_id, reason)
    return calibration


def _save_item_parameters(calibration, questions, difficulties, matrix, abilities, calculate_item_fit, flag_item):
    from ..models import RaschItemParameter

    params = []
    for index, (question, beta) in enumerate(zip(questions, difficulties)):
        row = matrix[index, :]
        observed_mask = ~np.isnan(row)
        n_observed = int(np.sum(observed_mask))

        if n_observed == 0:
            params.append(RaschItemParameter(
                calibration=calibration, question=question, beta=float(beta),
                beta_se=999.0, sample_size=0, is_calibrated=False,
            ))
            continue

        theta_obs, x_obs = abilities[observed_mask], row[observed_mask]
        infit, outfit, beta_se = calculate_item_fit(float(beta), theta_obs, x_obs)
        flagged, is_extreme = flag_item(infit, outfit, float(beta))

        params.append(RaschItemParameter(
            calibration=calibration, question=question, beta=float(beta),
            beta_se=beta_se if beta_se is not None else 999.0,
            infit=infit, outfit=outfit, sample_size=n_observed,
            is_calibrated=True, flagged_for_review=flagged, is_extreme=is_extreme,
        ))

    RaschItemParameter.objects.bulk_create(params)


# ============================================================
# CALIBRATION COMPARISON (barqarorlikni tekshirish uchun)
# ============================================================

def compare_calibrations(old_cal, new_cal) -> dict:
    """
    Ikki kalibratsiyani solishtiradi. Rasch beta shkalasi location-shift'ga
    ega bo'lishi mumkinligi uchun median-aligned farq ishlatiladi.
    """
    old_params = {p.question_id: p.beta for p in old_cal.item_parameters.filter(is_calibrated=True)}
    new_params = {p.question_id: p.beta for p in new_cal.item_parameters.filter(is_calibrated=True)}
    common = set(old_params) & set(new_params)

    if not common:
        return {"stable": False, "reason": "Umumiy savollar yo'q."}

    old_betas = np.asarray([old_params[q] for q in common], dtype=float)
    new_betas = np.asarray([new_params[q] for q in common], dtype=float)

    correlation = float(np.corrcoef(old_betas, new_betas)[0, 1]) if len(common) >= 2 else 1.0

    location_shift = float(np.median(new_betas - old_betas))
    aligned_diff = (new_betas - location_shift) - old_betas
    mean_abs_aligned_diff = float(np.mean(np.abs(aligned_diff)))
    max_abs_aligned_diff = float(np.max(np.abs(aligned_diff)))

    old_flagged = old_cal.item_parameters.filter(flagged_for_review=True).count()
    new_flagged = new_cal.item_parameters.filter(flagged_for_review=True).count()

    stable = (
        correlation > 0.95
        and mean_abs_aligned_diff < 0.20
        and max_abs_aligned_diff < 0.50
        and new_flagged <= old_flagged + 2
    )

    return {
        "stable": stable,
        "correlation": round(correlation, 3),
        "location_shift": round(location_shift, 3),
        "mean_abs_aligned_diff": round(mean_abs_aligned_diff, 3),
        "max_abs_aligned_diff": round(max_abs_aligned_diff, 3),
        "flagged_items_delta": new_flagged - old_flagged,
        "common_items": len(common),
    }


# ============================================================
# NEEDS RECALIBRATION
# ============================================================

def needs_recalibration(subject) -> bool:
    from ..models import UserResponse

    active = subject.get_active_calibration()

    if active is None:
        # Sovuq boshlanish: minimal shaxslar soni yig'ilmaguncha qayta-qayta
        # og'ir kalibratsiyani navbatga qo'yib yubormaslik uchun taxminiy tekshiruv.
        unique_persons = (
            UserResponse.objects
            .filter(question__subject=subject, choice__isnull=False)
            .values("user_id").distinct().count()
        )
        return unique_persons >= subject.rasch_min_persons

    new_responses = UserResponse.objects.filter(
        question__subject=subject, choice__isnull=False, created_at__gt=active.data_cutoff_at,
    ).count()
    return new_responses >= subject.rasch_recalibration_response_threshold