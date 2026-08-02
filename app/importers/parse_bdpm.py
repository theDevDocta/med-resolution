"""Parsing des fichiers plats BDPM (tabulés, encodage latin-1).

Positions de colonnes documentées ici (les fichiers BDPM n'ont pas d'en-tête).
Le parsing est tolérant aux lignes plus courtes que prévu (champs optionnels
en fin de ligne selon les millésimes) mais rejette les lignes manifestement
incomplètes (moins de colonnes obligatoires).

Références colonnes (base-donnees-publique.medicaments.gouv.fr) :

CIS_bdpm.txt (12 colonnes) :
    0 CIS, 1 dénomination, 2 forme pharmaceutique, 3 voies d'administration,
    4 statut administratif AMM, 5 type de procédure AMM,
    6 état de commercialisation, 7 date AMM, 8 statut BDM,
    9 numéro autorisation européenne, 10 titulaire, 11 surveillance renforcée

CIS_COMPO_bdpm.txt (8 colonnes) :
    0 CIS, 1 désignation élément pharmaceutique, 2 code substance,
    3 dénomination substance, 4 dosage substance, 5 référence dosage,
    6 nature du composant, 7 numéro de lien

CIS_CIP_bdpm.txt (10+ colonnes) :
    0 CIS, 1 CIP7, 2 libellé présentation, 3 statut administratif,
    4 état de commercialisation, 5 date de commercialisation, 6 CIP13,
    7 agrément aux collectivités, 8 taux de remboursement, 9 prix
"""

import csv
from pathlib import Path

from app.core.config import BDPM_ENCODING

CIS_MIN_COLUMNS = 7
COMPO_MIN_COLUMNS = 5
CIP_MIN_COLUMNS = 7


class BdpmParseError(Exception):
    pass


def _read_tsv_rows(path: Path) -> list[list[str]]:
    with open(path, encoding=BDPM_ENCODING, newline="") as fh:
        return [row for row in csv.reader(fh, delimiter="\t") if any(cell.strip() for cell in row)]


def _cell(row: list[str], index: int) -> str | None:
    if index >= len(row):
        return None
    value = row[index].strip()
    return value or None


def parse_cis_bdpm(path: Path) -> tuple[list[dict], int]:
    """Retourne (spécialités, nombre de lignes rejetées)."""
    rows = _read_tsv_rows(path)
    specialties = []
    rejected = 0
    for row in rows:
        if len(row) < CIS_MIN_COLUMNS or not _cell(row, 0) or not _cell(row, 1):
            rejected += 1
            continue
        specialties.append(
            {
                "cis": _cell(row, 0),
                "brand_name": _cell(row, 1),
                "pharmaceutical_form": _cell(row, 2),
                "administration_routes": _cell(row, 3),
                "authorization_status": _cell(row, 4),
                "commercialization_status": _cell(row, 6),
                "holder": _cell(row, 10),
            }
        )
    return specialties, rejected


def _split_dosage(raw_dosage: str | None) -> tuple[str | None, str | None]:
    if not raw_dosage:
        return None, None
    parts = raw_dosage.split(maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return raw_dosage, None


def parse_cis_compo_bdpm(path: Path) -> tuple[list[dict], int]:
    rows = _read_tsv_rows(path)
    components = []
    rejected = 0
    for row in rows:
        if len(row) < COMPO_MIN_COLUMNS or not _cell(row, 0) or not _cell(row, 3):
            rejected += 1
            continue
        dosage_value, dosage_unit = _split_dosage(_cell(row, 4))
        components.append(
            {
                "cis": _cell(row, 0),
                "substance_code": _cell(row, 2),
                "substance_name": _cell(row, 3),
                "dosage": dosage_value,
                "dosage_unit": dosage_unit,
            }
        )
    return components, rejected


def parse_cis_cip_bdpm(path: Path) -> tuple[list[dict], int]:
    rows = _read_tsv_rows(path)
    presentations = []
    rejected = 0
    for row in rows:
        if len(row) < CIP_MIN_COLUMNS or not _cell(row, 0) or not _cell(row, 2):
            rejected += 1
            continue
        presentations.append(
            {
                "cis": _cell(row, 0),
                "cip7": _cell(row, 1),
                "presentation_label": _cell(row, 2),
                "commercialization_status": _cell(row, 4),
                "cip13": _cell(row, 6),
                "reimbursement_rate": _cell(row, 8),
                "price": _cell(row, 9),
            }
        )
    return presentations, rejected
