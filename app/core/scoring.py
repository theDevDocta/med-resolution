"""Calcul du score final et du niveau de confiance d'un candidat.

Le score est une combinaison pondérée de plusieurs signaux (voir spec §11).
Le nom (similarité lexicale) reste toujours le signal principal ; le
contexte clinique ou la version LLM ne peuvent jamais, seuls, produire une
confiance élevée.
"""

from app.core.config import CONFIDENCE_THRESHOLDS, SCORE_WEIGHTS


def confidence_level(score: float) -> str:
    if score >= CONFIDENCE_THRESHOLDS["high"]:
        return "high"
    if score >= CONFIDENCE_THRESHOLDS["medium"]:
        return "medium"
    if score >= CONFIDENCE_THRESHOLDS["low"]:
        return "low"
    return "uncertain"


def dosage_score(query_doses: list[dict], candidate_dosage: str | None, candidate_unit: str | None) -> float:
    """100 si aucune dose n'est fournie côté requête (pas de pénalité par
    défaut), 100 si une dose correspond, 40 si des doses sont fournies mais
    aucune ne correspond (pénalité, pas exclusion)."""
    if not query_doses:
        return 100.0
    if not candidate_dosage:
        return 70.0

    try:
        candidate_value = float(str(candidate_dosage).replace(",", "."))
    except ValueError:
        return 70.0

    for dose in query_doses:
        if dose["value"] == candidate_value:
            if not candidate_unit or dose["unit"] == candidate_unit:
                return 100.0
            return 80.0
    return 40.0


def form_score(query_form: str | None, candidate_form: str | None) -> float:
    if not query_form or not candidate_form:
        return 100.0
    return 100.0 if query_form.strip().lower() in candidate_form.strip().lower() else 60.0


def route_score(query_route: str | None, candidate_routes: str | None) -> float:
    if not query_route or not candidate_routes:
        return 100.0
    return 100.0 if query_route.strip().lower() in candidate_routes.strip().lower() else 60.0


def commercialized_score(commercialization_status: str | None) -> float:
    if not commercialization_status:
        return 70.0
    return 100.0 if "commercialis" in commercialization_status.lower() else 60.0


def compute_final_score(
    lexical_score: float,
    llm_score: float | None = None,
    dosage: float = 100.0,
    form: float = 100.0,
    route: float = 100.0,
    commercialized: float = 100.0,
) -> float:
    """`llm_score=None` signifie qu'aucune version LLM n'est disponible pour ce
    signal (ex: endpoint /search) : son poids est alors reporté sur le score
    lexical plutôt que de pénaliser artificiellement le candidat."""
    if llm_score is None:
        lexical_weight = SCORE_WEIGHTS["lexical"] + SCORE_WEIGHTS["llm"]
        llm_weight = 0.0
        llm_score = 0.0
    else:
        lexical_weight = SCORE_WEIGHTS["lexical"]
        llm_weight = SCORE_WEIGHTS["llm"]

    final = (
        lexical_score * lexical_weight
        + llm_score * llm_weight
        + dosage * SCORE_WEIGHTS["dosage"]
        + form * SCORE_WEIGHTS["form"]
        + route * SCORE_WEIGHTS["route"]
        + commercialized * SCORE_WEIGHTS["commercialized"]
    )
    return round(min(final, 100.0), 1)
