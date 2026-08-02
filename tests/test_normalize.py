from app.core.normalize import compact_form, extract_doses, french_number_to_int, normalize_drug_name


def test_normalize_accents():
    assert normalize_drug_name("Doliprâne") == "doliprane"


def test_normalize_punctuation_and_form():
    assert normalize_drug_name("DOLIPRANE 1 000 mg, comprimé") == "doliprane 1000 mg comprime"


def test_normalize_apostrophes_and_dashes():
    assert normalize_drug_name("l'amoxicilline") == "l amoxicilline"
    assert normalize_drug_name("anti-inflammatoire") == "anti inflammatoire"


def test_compact_form_strips_spaces():
    assert compact_form("doli prane") == "doliprane"


def test_compact_form_matches_regardless_of_spacing():
    assert compact_form("doliprane") == compact_form("doli prane")


def test_french_number_to_int():
    assert french_number_to_int("cinq cents") == 500
    assert french_number_to_int("deux cents") == 200
    assert french_number_to_int("mille") == 1000
    assert french_number_to_int("cent") == 100
    assert french_number_to_int("bonjour") is None


def test_extract_doses_numeric():
    doses = extract_doses("amoxicilline 500 mg")
    assert {"value": 500.0, "unit": "mg"} in doses


def test_extract_doses_written_out():
    doses = extract_doses("cinq cents milligrammes de paracetamol")
    assert {"value": 500.0, "unit": "mg"} in doses


def test_extract_doses_empty():
    assert extract_doses("") == []
    assert extract_doses("paracetamol") == []
