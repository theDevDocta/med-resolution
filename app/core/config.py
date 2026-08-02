"""Configuration centralisée : URLs BDPM, chemins, poids de scoring."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- URLs BDPM (base-donnees-publique.medicaments.gouv.fr) ---
# Regroupées ici, jamais dispersées dans le code d'import.
# Le site sert désormais les fichiers via /download/file/<nom> (l'ancien
# telechargement.php?fichier=... a été retiré).
BDPM_BASE_URL = os.environ.get(
    "BDPM_BASE_URL", "https://base-donnees-publique.medicaments.gouv.fr/download/file"
)
BDPM_FILES = {
    "CIS_bdpm.txt": f"{BDPM_BASE_URL}/CIS_bdpm.txt",
    "CIS_COMPO_bdpm.txt": f"{BDPM_BASE_URL}/CIS_COMPO_bdpm.txt",
    "CIS_CIP_bdpm.txt": f"{BDPM_BASE_URL}/CIS_CIP_bdpm.txt",
}
BDPM_ENCODING = os.environ.get("BDPM_ENCODING", "latin-1")

# --- Chemins ---
DATA_DIR = Path(os.environ.get("BDPM_DATA_DIR", BASE_DIR / "data"))
RAW_DIR = DATA_DIR / "raw"
DB_PATH = Path(os.environ.get("BDPM_DB_PATH", DATA_DIR / "bdpm.sqlite"))
DB_TMP_PATH = DB_PATH.with_suffix(".sqlite.tmp")

# --- Recherche ---
SQL_PRESELECTION_LIMIT = 500
MIN_ALIAS_LENGTH = 3
# Score lexical minimal pour retenir un candidat trouvé dans une fenêtre de
# mots du verbatim/LLM (évite le bruit des mots-outils courts).
MIN_LEXICAL_MATCH_THRESHOLD = 50.0

# --- Poids de scoring (doivent sommer à 1.0) ---
SCORE_WEIGHTS = {
    "lexical": 0.55,
    "llm": 0.20,
    "dosage": 0.10,
    "form": 0.05,
    "route": 0.05,
    "commercialized": 0.05,
}

CONFIDENCE_THRESHOLDS = {
    "high": 90,
    "medium": 75,
    "low": 55,
}

# --- Administration ---
# Si définie, protège POST /admin/update-database (header X-Admin-Key).
# Vide en dev local : aucune vérification n'est imposée.
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")

# --- Authentification microservice ---
# Si définie, protège /search, /resolve et /admin (header X-API-Key).
# /health reste toujours accessible sans clé (sondes de santé).
# Vide en dev local : aucune vérification n'est imposée.
API_KEY = os.environ.get("API_KEY", "")

# --- Contrôles d'import ---
CONTROL_DRUGS = ["paracetamol", "doliprane", "amoxicilline", "metformine", "metoprolol"]
MAX_REJECTED_ROWS_RATIO = 0.20
MIN_DB_SIZE_BYTES = 10_000  # garde-fou anti base vide/corrompue
