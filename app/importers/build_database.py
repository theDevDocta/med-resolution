"""Construction de la base SQLite à partir des fichiers plats BDPM.

Orchestration : parser les 3 fichiers, générer les alias, écrire dans une
base temporaire, valider, puis remplacer atomiquement la base existante
(spec §14-§15). Ne jamais écrire directement dans la base servie par l'API.
"""

import os
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.core.config import CONTROL_DRUGS, MAX_REJECTED_ROWS_RATIO, MIN_DB_SIZE_BYTES, MIN_ALIAS_LENGTH
from app.core.normalize import compact_form, extract_doses, normalize_drug_name
from app.db.connection import create_connection, init_schema
from app.db.repository import insert_aliases, insert_drugs, insert_presentations, insert_substances
from app.importers.parse_bdpm import parse_cis_bdpm, parse_cis_cip_bdpm, parse_cis_compo_bdpm


class ImportValidationError(Exception):
    pass


@dataclass
class ImportStats:
    drug_count: int
    alias_count: int
    substance_count: int
    presentation_count: int
    rejected_ratio: float


def _strip_form_and_dose(brand_name: str) -> str:
    """Isole la "racine" du nom de marque en retirant dosage/forme.

    Ex: "DOLIPRANE 1000 mg, comprimé" -> "DOLIPRANE"
    """
    root = brand_name.split(",")[0]
    digit_pos = next((i for i, ch in enumerate(root) if ch.isdigit()), None)
    if digit_pos is not None:
        root = root[:digit_pos]
    return root.strip()


def _strip_parenthetical(name: str) -> str:
    """Isole la substance de base sans précision de sel/forme entre parenthèses.

    Ex: "AMOXICILLINE (TRIHYDRATEE)" -> "AMOXICILLINE"
    """
    return re.sub(r"\s*\([^)]*\)", "", name).strip()


def _make_alias_row(cis: str, alias: str, alias_type: str, canonical_name: str, **extra) -> dict | None:
    alias_normalized = normalize_drug_name(alias)
    if len(alias_normalized) < MIN_ALIAS_LENGTH:
        return None
    return {
        "cis": cis,
        "alias": alias,
        "alias_normalized": alias_normalized,
        "alias_compact": compact_form(alias),
        "alias_type": alias_type,
        "canonical_name": canonical_name,
        "substance_name": extra.get("substance_name"),
        "pharmaceutical_form": extra.get("pharmaceutical_form"),
        "dosage": extra.get("dosage"),
        "dosage_unit": extra.get("dosage_unit"),
        "commercialization_status": extra.get("commercialization_status"),
    }


def generate_aliases_for_specialty(specialty: dict, substances: list[dict], presentations: list[dict]) -> list[dict]:
    cis = specialty["cis"]
    brand_name = specialty["brand_name"]
    canonical_name = brand_name
    common = {
        "pharmaceutical_form": specialty.get("pharmaceutical_form"),
        "commercialization_status": specialty.get("commercialization_status"),
    }

    candidates = []
    seen_normalized = set()

    def add(alias, alias_type, **extra):
        row = _make_alias_row(cis, alias, alias_type, canonical_name, **{**common, **extra})
        if row and row["alias_normalized"] not in seen_normalized:
            seen_normalized.add(row["alias_normalized"])
            candidates.append(row)

    brand_doses = extract_doses(brand_name)
    first_brand_dose = brand_doses[0] if brand_doses else None
    brand_dose_extra = (
        {"dosage": str(first_brand_dose["value"]), "dosage_unit": first_brand_dose["unit"]}
        if first_brand_dose
        else {}
    )

    # Alias complet (dénomination brute).
    add(brand_name, "brand", **brand_dose_extra)

    # Alias court (racine, sans forme/dosage).
    brand_root = _strip_form_and_dose(brand_name)
    if brand_root and brand_root.lower() != brand_name.lower():
        add(brand_root, "generated", **brand_dose_extra)

    # Alias racine + dosage(s) détecté(s) dans la dénomination.
    for dose in brand_doses:
        add(f"{brand_root} {int(dose['value'])} {dose['unit']}", "generated",
            dosage=str(dose["value"]), dosage_unit=dose["unit"])
        add(f"{brand_root} {int(dose['value'])}", "generated",
            dosage=str(dose["value"]), dosage_unit=dose["unit"])

    # Alias substance(s), avec une variante "racine" sans précision de sel/forme.
    for substance in substances:
        name = substance["substance_name"]
        dosage_extra = (
            {"dosage": substance["dosage"], "dosage_unit": substance["dosage_unit"]}
            if substance.get("dosage") and substance.get("dosage_unit")
            else {}
        )
        add(name, "substance", substance_name=name, **dosage_extra)

        substance_root = _strip_parenthetical(name)
        if substance_root and substance_root.lower() != name.lower():
            add(substance_root, "substance", substance_name=name, **dosage_extra)

        if dosage_extra:
            add(f"{name} {substance['dosage']} {substance['dosage_unit']}", "generated",
                substance_name=name, **dosage_extra)
            if substance_root and substance_root.lower() != name.lower():
                add(f"{substance_root} {substance['dosage']} {substance['dosage_unit']}", "generated",
                    substance_name=name, **dosage_extra)

    # Alias présentation.
    for presentation in presentations:
        label = presentation.get("presentation_label")
        if label:
            add(label, "presentation")

    return candidates


def run_import(raw_dir: Path, db_path: Path) -> ImportStats:
    cis_path = raw_dir / "CIS_bdpm.txt"
    compo_path = raw_dir / "CIS_COMPO_bdpm.txt"
    cip_path = raw_dir / "CIS_CIP_bdpm.txt"
    for path in (cis_path, compo_path, cip_path):
        if not path.exists():
            raise ImportValidationError(f"Fichier BDPM manquant : {path}")

    specialties, cis_rejected = parse_cis_bdpm(cis_path)
    components, compo_rejected = parse_cis_compo_bdpm(compo_path)
    presentations, cip_rejected = parse_cis_cip_bdpm(cip_path)

    total_lines = len(specialties) + cis_rejected + len(components) + compo_rejected + len(presentations) + cip_rejected
    total_rejected = cis_rejected + compo_rejected + cip_rejected
    rejected_ratio = (total_rejected / total_lines) if total_lines else 1.0

    if not specialties:
        raise ImportValidationError("Aucun médicament importé depuis CIS_bdpm.txt")
    if rejected_ratio > MAX_REJECTED_ROWS_RATIO:
        raise ImportValidationError(
            f"Trop de lignes rejetées à l'import : {rejected_ratio:.1%} (seuil {MAX_REJECTED_ROWS_RATIO:.0%})"
        )

    substances_by_cis = defaultdict(list)
    for component in components:
        substances_by_cis[component["cis"]].append(component)

    presentations_by_cis = defaultdict(list)
    for presentation in presentations:
        presentations_by_cis[presentation["cis"]].append(presentation)

    drug_rows = [
        {**specialty, "brand_name_normalized": normalize_drug_name(specialty["brand_name"])}
        for specialty in specialties
    ]
    substance_rows = [
        {**component, "substance_name_normalized": normalize_drug_name(component["substance_name"])}
        for component in components
    ]
    presentation_rows = [
        {**presentation, "presentation_label_normalized": normalize_drug_name(presentation.get("presentation_label") or "")}
        for presentation in presentations
    ]

    alias_rows = []
    for specialty in specialties:
        alias_rows.extend(
            generate_aliases_for_specialty(
                specialty,
                substances_by_cis.get(specialty["cis"], []),
                presentations_by_cis.get(specialty["cis"], []),
            )
        )

    if not alias_rows:
        raise ImportValidationError("Aucun alias généré, import interrompu")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = create_connection(db_path)
    try:
        init_schema(conn)
        insert_drugs(conn, drug_rows)
        insert_substances(conn, substance_rows)
        insert_presentations(conn, presentation_rows)
        insert_aliases(conn, alias_rows)
        conn.commit()
    finally:
        conn.close()

    _validate_database(db_path, rejected_ratio)

    return ImportStats(
        drug_count=len(specialties),
        alias_count=len(alias_rows),
        substance_count=len(components),
        presentation_count=len(presentations),
        rejected_ratio=rejected_ratio,
    )


def _validate_database(db_path: Path, rejected_ratio: float) -> None:
    if db_path.stat().st_size < MIN_DB_SIZE_BYTES:
        raise ImportValidationError(f"Base produite anormalement petite : {db_path.stat().st_size} octets")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        drug_count = conn.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
        alias_count = conn.execute("SELECT COUNT(*) FROM drug_aliases").fetchone()[0]
        if drug_count == 0:
            raise ImportValidationError("Base produite sans aucun médicament")
        if alias_count == 0:
            raise ImportValidationError("Base produite sans aucun alias")

        missing_controls = []
        for control_drug in CONTROL_DRUGS:
            normalized = normalize_drug_name(control_drug)
            found = conn.execute(
                "SELECT 1 FROM drug_aliases WHERE alias_normalized LIKE ? LIMIT 1",
                (f"%{normalized}%",),
            ).fetchone()
            if not found:
                missing_controls.append(control_drug)
        if missing_controls:
            raise ImportValidationError(f"Médicaments de contrôle introuvables : {', '.join(missing_controls)}")
    finally:
        conn.close()


def build_and_replace(raw_dir: Path, final_db_path: Path) -> ImportStats:
    """Construit la base dans un fichier temporaire puis la substitue de façon atomique."""
    tmp_path = final_db_path.with_suffix(".sqlite.tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    stats = run_import(raw_dir, tmp_path)
    os.replace(tmp_path, final_db_path)
    return stats
