"""Représentations légères des lignes des tables SQLite.

Utilisées en interne par le repository et le resolver ; les schémas de
réponse HTTP (app/schemas/responses.py) sont distincts et exposent une forme
adaptée à l'API.
"""

from dataclasses import dataclass


@dataclass
class Drug:
    id: int
    cis: str
    brand_name: str
    brand_name_normalized: str
    pharmaceutical_form: str | None
    administration_routes: str | None
    authorization_status: str | None
    commercialization_status: str | None
    holder: str | None


@dataclass
class Substance:
    id: int
    cis: str
    substance_code: str | None
    substance_name: str
    substance_name_normalized: str
    dosage: str | None
    dosage_unit: str | None


@dataclass
class Presentation:
    id: int
    cis: str
    cip7: str | None
    cip13: str | None
    presentation_label: str | None
    presentation_label_normalized: str | None
    commercialization_status: str | None
    reimbursement_rate: str | None
    price: str | None


@dataclass
class DrugAlias:
    id: int
    cis: str
    alias: str
    alias_normalized: str
    alias_compact: str
    alias_type: str
    canonical_name: str
    substance_name: str | None
    pharmaceutical_form: str | None
    dosage: str | None
    dosage_unit: str | None
    commercialization_status: str | None

    @classmethod
    def from_row(cls, row) -> "DrugAlias":
        return cls(**{field: row[field] for field in row.keys()})
