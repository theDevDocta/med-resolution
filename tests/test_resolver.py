def test_search_exact_brand_name(resolver):
    results = resolver.search("doliprane")
    assert any(r.canonical_name.startswith("DOLIPRANE") for r in results)
    assert results[0].score >= 90


def test_search_typo_recovers_amoxicilline(resolver):
    results = resolver.search("amoxiciline")
    assert any("AMOXICILLINE" in r.canonical_name for r in results)


def test_search_typo_recovers_metoprolol(resolver):
    results = resolver.search("metropolol", commercialized_only=False)
    assert any("METOPROLOL" in (r.substance_name or "") for r in results)


def test_search_compact_spacing_typo(resolver):
    results = resolver.search("doli prane")
    assert any(r.canonical_name.startswith("DOLIPRANE") for r in results)


def test_search_by_substance_name(resolver):
    results = resolver.search("paracetamol", commercialized_only=False)
    cis_set = {r.cis for r in results}
    assert "60002283" in cis_set  # DOLIPRANE
    assert "60003152" in cis_set  # DAFALGAN


def test_search_commercialized_only_excludes_non_commercialized(resolver):
    results = resolver.search("lopressor", commercialized_only=True)
    assert results == []

    results_all = resolver.search("lopressor", commercialized_only=False)
    assert any(r.canonical_name.startswith("LOPRESSOR") for r in results_all)


def test_resolve_returns_candidate_with_evidence(resolver):
    result = resolver.resolve(
        verbatim="le patient prend de l amoxiciline cinq cents",
        llm_version="le patient prend de l'amoxicilline 500 mg",
        suspected_term="amoxiciline",
    )
    assert result.candidates
    top = result.candidates[0]
    assert "AMOXICILLINE" in top.canonical_name
    assert "fuzzy_name_match" in top.evidence
    assert "llm_version_match" in top.evidence
    assert "dosage_match" in top.evidence
    assert top.confidence in {"high", "medium"}


def test_resolve_low_score_for_unrelated_term(resolver):
    result = resolver.resolve(verbatim="le patient regarde la television ce soir")
    assert not result.candidates or result.candidates[0].score < 55


def test_resolve_stopwords_do_not_outrank_the_real_match(resolver):
    """Régression : "de l" (mots-outils) apparaissant tel quel dans le long
    libellé de présentation de VACCITEST ne doit pas produire un score
    gonflé (via token_set_ratio) qui dépasse ou égale le vrai candidat
    AMOXICILLINE."""
    result = resolver.resolve(verbatim="le patient prend de l amoxiciline cinq cents")
    assert result.candidates
    top = result.candidates[0]
    assert "AMOXICILLINE" in top.canonical_name
    assert not any("VACCITEST" in c.canonical_name and c.score >= top.score for c in result.candidates)
