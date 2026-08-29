"""
Rasch modelining matematik yadrosi.
Bu yerda faqat statistik hisoblashlar bor, hech qanday Django ORM mantig'i yo'q.
"""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

FIT_STATISTIC_LOW = 0.5
FIT_STATISTIC_HIGH = 1.5
MAX_NEWTON_ITERATIONS = 50
CONVERGENCE_TOLERANCE = 1e-5


def rasch_probability(theta, beta):
    """Bitta yoki vektor (theta, beta) uchun to'g'ri javob ehtimoli."""
    return 1.0 / (1.0 + np.exp(-(theta - beta)))


def estimate_theta_map(
    beta_correct_pairs: list[tuple[float, bool]],
    prior_variance: float = 1.0,
    theta_min: float = -6.0,
    theta_max: float = 6.0,
) -> tuple[float, float, bool, list[float]]:
    """
    MAP (Maximum A Posteriori) theta baholash — N(0, prior_variance) prior bilan.
    E'TIBOR: bu JMLE/MLE emas, MAP. Hujjatlarda shu nom bilan ataladi.

    Qaytaradi: (theta, standard_error, converged, probabilities)
    """
    if not beta_correct_pairs:
        return 0.0, 999.0, False, []

    betas = np.array([b for b, _ in beta_correct_pairs], dtype=float)
    responses = np.array([1.0 if c else 0.0 for _, c in beta_correct_pairs], dtype=float)

    theta = 0.0
    converged = False

    for iteration in range(MAX_NEWTON_ITERATIONS):
        p = rasch_probability(theta, betas)
        gradient = float(np.sum(responses - p)) - (theta / prior_variance)
        info = float(np.sum(p * (1.0 - p))) + (1.0 / prior_variance)

        if info <= 0:
            logger.warning("Fisher information <= 0, iteration=%d", iteration)
            break

        step = gradient / info
        theta += step

        if abs(step) < CONVERGENCE_TOLERANCE:
            converged = True
            break

    theta = float(np.clip(theta, theta_min, theta_max))

    p_final = rasch_probability(theta, betas)
    total_info = float(np.sum(p_final * (1.0 - p_final))) + (1.0 / prior_variance)
    se = 1.0 / np.sqrt(total_info) if total_info > 0 else 999.0

    return round(theta, 4), round(se, 4), converged, p_final.tolist()


def calculate_person_fit(theta, beta_correct_pairs):
    """Person infit/outfit — nomzod javoblarining modelga mosligi."""
    if not beta_correct_pairs:
        return None, None

    betas = np.array([b for b, _ in beta_correct_pairs], dtype=float)
    responses = np.array([1.0 if c else 0.0 for _, c in beta_correct_pairs], dtype=float)

    p = rasch_probability(theta, betas)
    variance = np.clip(p * (1.0 - p), 1e-6, None)
    residual_sq = (responses - p) ** 2

    outfit = float(np.mean(residual_sq / variance))
    sum_variance = float(np.sum(variance))
    infit = float(np.sum(residual_sq) / sum_variance) if sum_variance > 0 else None

    return (round(infit, 3) if infit is not None else None), round(outfit, 3)


def calculate_item_fit(beta, thetas, responses):
    """Bitta savol uchun infit/outfit va beta SE."""
    if len(thetas) == 0 or len(responses) == 0:
        return None, None, None

    p = rasch_probability(thetas, beta)
    variance = np.clip(p * (1.0 - p), 1e-6, None)
    residual_sq = (responses - p) ** 2

    outfit = float(np.mean(residual_sq / variance))
    sum_variance = float(np.sum(variance))
    infit = float(np.sum(residual_sq) / sum_variance) if sum_variance > 0 else None
    beta_se = float(1.0 / np.sqrt(sum_variance)) if sum_variance > 0 else 999.0

    return (
        round(infit, 3) if infit is not None else None,
        round(outfit, 3),
        round(beta_se, 4),
    )


def test_information_function(theta: float, betas: list[float]) -> float:
    """Test Information Function (TIF) — berilgan theta nuqtada test qanchalik aniq o'lchayotgani."""
    if not betas:
        return 0.0
    betas_arr = np.array(betas, dtype=float)
    p = rasch_probability(theta, betas_arr)
    return round(float(np.sum(p * (1.0 - p))), 4)


def build_response_matrix(question_ids, person_ids, response_data):
    """(n_items, n_persons) matritsa. Missing = np.nan."""
    n_items, n_persons = len(question_ids), len(person_ids)
    q_index = {qid: i for i, qid in enumerate(question_ids)}
    p_index = {pid: j for j, pid in enumerate(person_ids)}

    matrix = np.full((n_items, n_persons), np.nan)
    for question_id, person_id, is_correct in response_data:
        i, j = q_index.get(question_id), p_index.get(person_id)
        if i is not None and j is not None:
            matrix[i, j] = 1.0 if is_correct else 0.0
    return matrix


def flag_item(infit, outfit, beta, fit_low=FIT_STATISTIC_LOW, fit_high=FIT_STATISTIC_HIGH, extreme_threshold=4.0):
    """Qaytaradi: (flagged_for_review, is_extreme)."""
    flagged = False
    is_extreme = abs(beta) > extreme_threshold
    if infit is not None and not (fit_low <= infit <= fit_high):
        flagged = True
    if outfit is not None and not (fit_low <= outfit <= fit_high):
        flagged = True
    return flagged, is_extreme


def check_calibration_convergence(difficulties: np.ndarray, abilities: np.ndarray) -> bool:
    """
    girth o'zi convergence flag qaytarmaydi — natijaning barqarorligini
    o'zimiz tekshiramiz: barcha qiymatlar chekli (finite) va oqilona
    diapazonda (|beta| < 15, aks holda separatsiya muammosi bo'lgan).
    """
    if difficulties.size == 0 or abilities.size == 0:
        return False
    if not (np.all(np.isfinite(difficulties)) and np.all(np.isfinite(abilities))):
        return False
    if np.any(np.abs(difficulties) > 15) or np.any(np.abs(abilities) > 15):
        logger.warning("Kalibratsiya ekstremal qiymatlar berdi — separatsiya muammosi bo'lishi mumkin.")
        return False
    return True