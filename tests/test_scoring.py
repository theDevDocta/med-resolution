from app.core.scoring import compute_final_score, confidence_level, dosage_score


def test_confidence_levels():
    assert confidence_level(95) == "high"
    assert confidence_level(90) == "high"
    assert confidence_level(80) == "medium"
    assert confidence_level(60) == "low"
    assert confidence_level(30) == "uncertain"


def test_compute_final_score_perfect_match():
    score = compute_final_score(lexical_score=100, llm_score=100, dosage=100, form=100, route=100, commercialized=100)
    assert score == 100.0


def test_compute_final_score_weighted_lexical_dominates():
    high_lexical = compute_final_score(lexical_score=100, llm_score=0)
    low_lexical = compute_final_score(lexical_score=0, llm_score=100)
    assert high_lexical > low_lexical


def test_dosage_score_no_query_dose_is_neutral():
    assert dosage_score([], "500", "mg") == 100.0


def test_dosage_score_matching_dose():
    assert dosage_score([{"value": 500.0, "unit": "mg"}], "500", "mg") == 100.0


def test_dosage_score_mismatched_dose_is_penalized_not_excluded():
    score = dosage_score([{"value": 500.0, "unit": "mg"}], "1000", "mg")
    assert 0 < score < 100
