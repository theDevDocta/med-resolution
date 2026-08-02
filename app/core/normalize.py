"""Normalisation des noms de médicaments et extraction de doses.

Une seule fonction de normalisation est utilisée à l'import et à la recherche,
afin de garantir que les alias stockés et les requêtes utilisateur sont
comparables.
"""

import re
import unicodedata

from unidecode import unidecode

# Unités reconnues (forme cible normalisée) et leurs variantes textuelles.
_UNIT_ALIASES = {
    "mg": ["mg", "milligramme", "milligrammes"],
    "g": ["g", "gramme", "grammes"],
    "microgramme": ["microgramme", "microgrammes", "ug", "µg", "mcg"],
    "ml": ["ml", "millilitre", "millilitres"],
    "%": ["%", "pourcent", "pour cent"],
    "ui": ["ui", "unite", "unites", "unite internationale", "unites internationales"],
}

# Table simple de nombres français fréquents (spec §13) : pas de parseur universel.
_FRENCH_NUMBERS = {
    "zero": 0,
    "un": 1,
    "une": 1,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "six": 6,
    "sept": 7,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
    "vingt": 20,
    "trente": 30,
    "quarante": 40,
    "cinquante": 50,
    "soixante": 60,
    "cent": 100,
    "cents": 100,
    "mille": 1000,
}

_DOSE_UNIT_PATTERN = "|".join(
    sorted((re.escape(v) for aliases in _UNIT_ALIASES.values() for v in aliases), key=len, reverse=True)
)
_DOSE_NUMERIC_RE = re.compile(rf"(\d+(?:[.,]\d+)?)\s*({_DOSE_UNIT_PATTERN})\b", re.IGNORECASE)


def normalize_drug_name(value: str) -> str:
    """Convertit une chaîne en forme normalisée adaptée à la recherche.

    Minuscules, sans accents, ponctuation/tirets/apostrophes réduits en
    espaces, espaces multiples réduits, chiffres conservés, unités courantes
    normalisées (ex: "µg"/"mcg" -> "microgramme").
    """
    if not value:
        return ""

    text = unidecode(value).lower()
    text = text.replace("-", " ").replace("'", " ").replace("’", " ")
    text = re.sub(r"[^\w\s%]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()

    # Fusionne les groupes de milliers séparés par un espace ("1 000" -> "1000").
    text = re.sub(r"(?<=\d) (?=\d)", "", text)

    for canonical, variants in _UNIT_ALIASES.items():
        for variant in sorted(variants, key=len, reverse=True):
            variant_norm = unidecode(variant).lower()
            text = re.sub(rf"\b{re.escape(variant_norm)}\b", canonical, text)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def compact_form(value: str) -> str:
    """Forme compacte : normalisée puis dépourvue de tous les espaces."""
    return normalize_drug_name(value).replace(" ", "")


def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")


def french_number_to_int(text: str) -> int | None:
    """Convertit quelques nombres français fréquents en entier.

    Gère des compositions simples ("cinq cents" -> 500, "deux cents" -> 200)
    mais ne prétend pas à un parseur universel (voir spec §13).
    """
    words = normalize_drug_name(text).split()
    total = 0
    matched = False
    for word in words:
        if word in _FRENCH_NUMBERS:
            value = _FRENCH_NUMBERS[word]
            matched = True
            if value >= 100 and total > 0:
                total *= value
            else:
                total += value
    return total if matched else None


def extract_doses(text: str) -> list[dict]:
    """Détecte les doses numériques (ex: "500 mg") et les nombres écrits en
    toutes lettres suivis d'une unité (ex: "cinq cents milligrammes").

    Retourne une liste de dicts {"value": float, "unit": str}.
    """
    if not text:
        return []

    normalized = normalize_drug_name(text)
    doses = []

    for match in _DOSE_NUMERIC_RE.finditer(normalized):
        value = float(match.group(1).replace(",", "."))
        unit = _canonical_unit(match.group(2))
        doses.append({"value": value, "unit": unit})

    for canonical, variants in _UNIT_ALIASES.items():
        for variant in variants:
            pattern = re.compile(rf"([a-z ]+?)\s+{re.escape(canonical)}\b")
            for match in pattern.finditer(normalized):
                number = french_number_to_int(match.group(1))
                if number is not None:
                    doses.append({"value": float(number), "unit": canonical})

    # Déduplique en conservant l'ordre.
    seen = set()
    unique_doses = []
    for dose in doses:
        key = (dose["value"], dose["unit"])
        if key not in seen:
            seen.add(key)
            unique_doses.append(dose)
    return unique_doses


def _canonical_unit(raw_unit: str) -> str:
    raw_norm = unidecode(raw_unit).lower()
    for canonical, variants in _UNIT_ALIASES.items():
        if raw_norm in [unidecode(v).lower() for v in variants]:
            return canonical
    return raw_norm
