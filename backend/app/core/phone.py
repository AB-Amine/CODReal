"""Phone number normalization for Moroccan COD matching.

Rules (CDC Annexe 2):
1. Strip +212, 0, spaces, dashes
2. Produce a canonical local form for matching
"""

from __future__ import annotations

import re


def normalize_phone(raw: str | None, default_region: str = "MA") -> str | None:
    """Normalize a phone number for matching.

    Supports Moroccan formats:
    - 0612345678
    - +212612345678
    - 00212612345678
    - 6 12 34 56 78
    - (06) 12-34-56-78

    Returns a 9-digit local mobile form (e.g. 612345678) or None if invalid.
    """
    if raw is None:
        return None

    text = str(raw).strip()
    if not text:
        return None

    # Keep digits only (and leading + for detection)
    has_plus = text.startswith("+")
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None

    # 00 international prefix
    if digits.startswith("00"):
        digits = digits[2:]

    # Morocco country code
    if digits.startswith("212"):
        digits = digits[3:]
    elif has_plus and len(digits) > 9:
        # Other country codes — keep last 9 for best-effort match
        digits = digits[-9:]

    # Local leading 0
    if digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]

    # Moroccan mobile: 9 digits starting with 6 or 7
    if len(digits) == 9 and digits[0] in ("5", "6", "7"):
        return digits

    # Sometimes people paste 10 digits without stripping 0 correctly
    if len(digits) == 10 and digits.startswith("0"):
        candidate = digits[1:]
        if candidate[0] in ("5", "6", "7"):
            return candidate

    # Fallback: if we have at least 9 digits, use last 9
    if len(digits) >= 9:
        candidate = digits[-9:]
        if candidate[0] in ("5", "6", "7"):
            return candidate

    return None


def phones_match(a: str | None, b: str | None) -> bool:
    """Return True if two raw phone strings normalize to the same value."""
    na = normalize_phone(a)
    nb = normalize_phone(b)
    if na is None or nb is None:
        return False
    return na == nb
