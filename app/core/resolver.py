"""Interface Python interne du resolver (spec §19).

`DrugResolver` contient toute la logique métier de recherche/résolution ;
l'API FastAPI (app/api/*.py) ne fait qu'appeler cette classe.
"""

import sqlite3
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from app.core import scoring
from app.core.config import MIN_ALIAS_LENGTH, MIN_LEXICAL_MATCH_THRESHOLD
from app.core.normalize import compact_form, extract_doses, normalize_drug_name
from app.db import repository
from app.db.connection import get_connection
from app.db.models import DrugAlias

# Mots-outils français très fréquents, écartés de la génération de fenêtres
# de mots (spec §12) : seuls, ils ne portent aucun signal sur un nom de
# médicament et peuvent, une fois combinés à d'autres, fausser le score
# lexical par correspondance partielle fortuite sur un alias long et
# sans rapport.
_IGNORED_WORDS = {
    "le", "la", "les", "l", "un", "une", "des", "de", "du", "et", "ou", "a", "au", "aux",
    "en", "ce", "ces", "cet", "cette", "se", "sa", "son", "ses", "sous", "sur", "dans",
    "avec", "pour", "par", "qui", "que", "ne", "pas", "plus", "est", "sont", "etre",
    "il", "elle", "ils", "elles", "je", "tu", "nous", "vous", "on", "mon", "ma", "mes",
    "patient", "patiente", "prend", "prescrit", "traitement",
}


@dataclass
class DrugCandidate:
    cis: str
    canonical_name: str
    matched_alias: str
    alias_type: str
    substance_name: str | None
    score: float
    confidence: str
    commercialization_status: str | None
    evidence: list[str] = field(default_factory=list)


@dataclass
class ResolveResult:
    suspected_term: str | None
    normalized_term: str | None
    candidates: list[DrugCandidate]


def _is_commercialized(status: str | None) -> bool:
    if not status:
        return False
    normalized = status.strip().lower()
    return "commercialis" in normalized and not normalized.startswith("non")


class DrugResolver:
    def __init__(self, conn: sqlite3.Connection | None = None):
        self.conn = conn or get_connection()

    # ---- API publique (spec §19) ----

    def search(self, query: str, limit: int = 10, commercialized_only: bool = True) -> list[DrugCandidate]:
        normalized_query = normalize_drug_name(query)
        compact_query = compact_form(query)
        if not normalized_query:
            return []

        prelim = repository.preselect_aliases(self.conn, normalized_query, compact_query)
        if commercialized_only:
            prelim = [a for a in prelim if _is_commercialized(a.commercialization_status)]

        best_by_cis: dict[str, tuple[DrugAlias, float]] = {}
        for alias_row in prelim:
            lexical = self._lexical_score(normalized_query, alias_row.alias_normalized)
            final = scoring.compute_final_score(
                lexical_score=lexical,
                commercialized=scoring.commercialized_score(alias_row.commercialization_status),
            )
            existing = best_by_cis.get(alias_row.cis)
            if not existing or final > existing[1]:
                best_by_cis[alias_row.cis] = (alias_row, final)

        ranked = sorted(best_by_cis.values(), key=lambda pair: pair[1], reverse=True)[:limit]
        return [
            DrugCandidate(
                cis=alias_row.cis,
                canonical_name=alias_row.canonical_name,
                matched_alias=alias_row.alias,
                alias_type=alias_row.alias_type,
                substance_name=alias_row.substance_name,
                score=final_score,
                confidence=scoring.confidence_level(final_score),
                commercialization_status=alias_row.commercialization_status,
                evidence=["fuzzy_name_match"],
            )
            for alias_row, final_score in ranked
        ]

    def resolve(
        self,
        verbatim: str,
        llm_version: str | None = None,
        suspected_term: str | None = None,
        context: str | None = None,
        limit: int = 5,
    ) -> ResolveResult:
        normalized_term = normalize_drug_name(suspected_term) if suspected_term else None

        sources = {"suspected_term": suspected_term, "verbatim": verbatim, "llm_version": llm_version}
        query_doses = []
        for text in (verbatim, llm_version, context):
            if text:
                query_doses.extend(extract_doses(text))

        per_source_matches = {
            source_name: self._best_matches_in_text(text)
            for source_name, text in sources.items()
            if text
        }

        merged: dict[str, dict] = {}
        for source_name, matches in per_source_matches.items():
            for cis, (lexical_score, alias_row) in matches.items():
                entry = merged.setdefault(cis, {"alias_row": alias_row, "lexical_score": 0.0, "sources": set()})
                if lexical_score > entry["lexical_score"]:
                    entry["lexical_score"] = lexical_score
                    entry["alias_row"] = alias_row
                entry["sources"].add(source_name)

        candidates = []
        for cis, entry in merged.items():
            alias_row: DrugAlias = entry["alias_row"]
            lexical_score = entry["lexical_score"]
            sources_hit = entry["sources"]

            llm_score = None
            if "llm_version" in per_source_matches:
                match = per_source_matches["llm_version"].get(cis)
                llm_score = match[0] if match else 0.0

            dosage = scoring.dosage_score(query_doses, alias_row.dosage, alias_row.dosage_unit)
            commercialized = scoring.commercialized_score(alias_row.commercialization_status)
            final_score = scoring.compute_final_score(
                lexical_score=lexical_score, llm_score=llm_score, dosage=dosage, commercialized=commercialized
            )

            evidence = ["fuzzy_name_match"]
            if "suspected_term" in sources_hit:
                evidence.append("suspected_term_match")
            if "verbatim" in sources_hit:
                evidence.append("verbatim_match")
            if "llm_version" in sources_hit:
                evidence.append("llm_version_match")
            if query_doses and dosage >= 100.0:
                evidence.append("dosage_match")

            candidates.append(
                DrugCandidate(
                    cis=cis,
                    canonical_name=alias_row.canonical_name,
                    matched_alias=alias_row.alias,
                    alias_type=alias_row.alias_type,
                    substance_name=alias_row.substance_name,
                    score=final_score,
                    confidence=scoring.confidence_level(final_score),
                    commercialization_status=alias_row.commercialization_status,
                    evidence=evidence,
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return ResolveResult(
            suspected_term=suspected_term,
            normalized_term=normalized_term,
            candidates=candidates[:limit],
        )

    # ---- Aides internes ----

    def _candidate_terms(self, text: str) -> list[str]:
        normalized = normalize_drug_name(text)
        words = [w for w in normalized.split() if not w.isdigit() and w not in _IGNORED_WORDS][:40]
        terms = set()
        for n in (1, 2, 3):
            for i in range(len(words) - n + 1):
                term = " ".join(words[i : i + n])
                if len(term) >= MIN_ALIAS_LENGTH:
                    terms.add(term)
        if not terms and normalized:
            terms.add(normalized)
        return list(terms)

    def _fuzzy_match(self, term: str) -> list[tuple[DrugAlias, float]]:
        normalized = normalize_drug_name(term)
        compact = compact_form(term)
        prelim = repository.preselect_aliases(self.conn, normalized, compact)
        return [(alias_row, self._lexical_score(normalized, alias_row.alias_normalized)) for alias_row in prelim]

    def _best_matches_in_text(self, text: str) -> dict[str, tuple[float, DrugAlias]]:
        best: dict[str, tuple[float, DrugAlias]] = {}
        for term in self._candidate_terms(text):
            for alias_row, lexical_score in self._fuzzy_match(term):
                if lexical_score < MIN_LEXICAL_MATCH_THRESHOLD:
                    continue
                existing = best.get(alias_row.cis)
                if not existing or lexical_score > existing[0]:
                    best[alias_row.cis] = (lexical_score, alias_row)
        return best

    @staticmethod
    def _lexical_score(normalized_query: str, alias_normalized: str) -> float:
        if normalized_query == alias_normalized:
            return 100.0
        if compact_form(normalized_query) == compact_form(alias_normalized):
            return 97.0
        # `token_set_ratio` est délibérément exclu : il renvoie 100 dès que
        # les mots de la requête sont un sous-ensemble des mots de l'alias,
        # ce qui explose sur des mots-outils courts ("de l") comparés à un
        # long libellé de présentation contenant incidemment ces mots.
        scores = (
            fuzz.WRatio(normalized_query, alias_normalized),
            fuzz.ratio(normalized_query, alias_normalized),
            fuzz.token_sort_ratio(normalized_query, alias_normalized),
        )
        return float(max(scores))
