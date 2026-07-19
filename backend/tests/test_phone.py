from app.core.phone import normalize_phone, phones_match


def test_normalize_local_zero():
    assert normalize_phone("0612345678") == "612345678"


def test_normalize_plus_212():
    assert normalize_phone("+212612345678") == "612345678"


def test_normalize_spaces_dashes():
    assert normalize_phone("06 12-34-56-78") == "612345678"


def test_normalize_00212():
    assert normalize_phone("00212612345678") == "612345678"


def test_normalize_already_local():
    assert normalize_phone("612345678") == "612345678"


def test_invalid_empty():
    assert normalize_phone("") is None
    assert normalize_phone(None) is None


def test_phones_match():
    assert phones_match("0612345678", "+212 6 12 34 56 78")
    assert not phones_match("0612345678", "0699999999")
