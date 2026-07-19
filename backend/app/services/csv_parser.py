"""CSV/Excel upload parsing and validation for delivery data."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any, BinaryIO

import pandas as pd

from app.core.phone import normalize_phone

REQUIRED_COLUMNS = {"phone", "status", "amount_collected", "delivery_date"}
OPTIONAL_COLUMNS = {"order_ref", "carrier", "campaign_name", "campaign_id"}
VALID_STATUSES = {"delivered", "returned", "refused", "pending"}

# French / Moroccan aliases → canonical column names
COLUMN_ALIASES: dict[str, str] = {
    "phone": "phone",
    "telephone": "phone",
    "téléphone": "phone",
    "tel": "phone",
    "mobile": "phone",
    "num_tel": "phone",
    "numero": "phone",
    "numéro": "phone",
    "order_ref": "order_ref",
    "order_id": "order_ref",
    "commande": "order_ref",
    "ref": "order_ref",
    "reference": "order_ref",
    "référence": "order_ref",
    "id_commande": "order_ref",
    "status": "status",
    "statut": "status",
    "etat": "status",
    "état": "status",
    "amount_collected": "amount_collected",
    "montant": "amount_collected",
    "montant_collecte": "amount_collected",
    "montant_collecté": "amount_collected",
    "amount": "amount_collected",
    "prix": "amount_collected",
    "delivery_date": "delivery_date",
    "date": "delivery_date",
    "date_livraison": "delivery_date",
    "date_livr": "delivery_date",
    "carrier": "carrier",
    "transporteur": "carrier",
    "livreur": "carrier",
    "campaign_name": "campaign_name",
    "campagne": "campaign_name",
    "campaign": "campaign_name",
    "campaign_id": "campaign_id",
}

STATUS_ALIASES: dict[str, str] = {
    "delivered": "delivered",
    "livré": "delivered",
    "livre": "delivered",
    "livree": "delivered",
    "livrée": "delivered",
    "ok": "delivered",
    "success": "delivered",
    "returned": "returned",
    "retour": "returned",
    "retourné": "returned",
    "retourne": "returned",
    "return": "returned",
    "refused": "refused",
    "refusé": "refused",
    "refuse": "refused",
    "refus": "refused",
    "annulé": "refused",
    "annule": "refused",
    "cancelled": "refused",
    "pending": "pending",
    "en_cours": "pending",
    "en cours": "pending",
    "attente": "pending",
    "in_transit": "pending",
}


@dataclass
class RowError:
    row: int  # 1-based data row (excluding header)
    field: str
    message: str
    value: Any = None


@dataclass
class ParseResult:
    valid_rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    columns_detected: list[str] = field(default_factory=list)
    total_rows: int = 0
    valid_count: int = 0
    error_count: int = 0


def _normalize_header(name: str) -> str:
    key = str(name).strip().lower().replace(" ", "_")
    return COLUMN_ALIASES.get(key, key)


def _normalize_status(raw: Any) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    text = str(raw).strip().lower()
    return STATUS_ALIASES.get(text)


def parse_delivery_file(
    content: bytes,
    filename: str,
) -> ParseResult:
    """Parse CSV or Excel delivery file into validated order dicts."""
    result = ParseResult()
    name = (filename or "").lower()

    try:
        if name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            # Try utf-8 then latin-1 (common in Moroccan exports)
            try:
                df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
            except UnicodeDecodeError:
                df = pd.read_csv(
                    io.BytesIO(content),
                    dtype=str,
                    keep_default_na=False,
                    encoding="latin-1",
                )
    except Exception as exc:
        result.errors.append(
            RowError(row=0, field="_file", message=f"Impossible de lire le fichier: {exc}")
        )
        result.error_count = 1
        return result

    if df.empty:
        result.warnings.append("Fichier vide — aucune ligne à importer.")
        return result

    # Rename columns via aliases
    rename_map = {c: _normalize_header(c) for c in df.columns}
    df = df.rename(columns=rename_map)
    # Drop duplicate columns after aliasing (keep first)
    df = df.loc[:, ~df.columns.duplicated()]
    result.columns_detected = list(df.columns)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        result.errors.append(
            RowError(
                row=0,
                field="_columns",
                message=f"Colonnes obligatoires manquantes: {', '.join(sorted(missing))}",
            )
        )
        result.error_count = 1
        return result

    result.total_rows = len(df)

    for idx, row in df.iterrows():
        row_num = int(idx) + 1 if isinstance(idx, (int, float)) else idx + 1
        row_errors: list[RowError] = []

        phone_raw = row.get("phone")
        nphone = normalize_phone(phone_raw)
        if not nphone:
            row_errors.append(
                RowError(
                    row=row_num,
                    field="phone",
                    message="Numéro de téléphone invalide ou non marocain",
                    value=phone_raw,
                )
            )

        status = _normalize_status(row.get("status"))
        if status is None or status not in VALID_STATUSES:
            row_errors.append(
                RowError(
                    row=row_num,
                    field="status",
                    message=f"Statut invalide (attendu: {', '.join(sorted(VALID_STATUSES))})",
                    value=row.get("status"),
                )
            )

        amount_raw = row.get("amount_collected")
        try:
            amount = float(
                str(amount_raw).replace(",", ".").replace(" ", "").replace("MAD", "")
            )
            if amount < 0:
                raise ValueError("négatif")
        except (TypeError, ValueError):
            amount = 0.0
            row_errors.append(
                RowError(
                    row=row_num,
                    field="amount_collected",
                    message="Montant collecté invalide",
                    value=amount_raw,
                )
            )

        date_raw = row.get("delivery_date")
        delivery_date = None
        if date_raw is not None and str(date_raw).strip():
            try:
                delivery_date = pd.to_datetime(date_raw).strftime("%Y-%m-%d")
            except Exception:
                row_errors.append(
                    RowError(
                        row=row_num,
                        field="delivery_date",
                        message="Date invalide (format attendu: YYYY-MM-DD)",
                        value=date_raw,
                    )
                )
        else:
            row_errors.append(
                RowError(
                    row=row_num,
                    field="delivery_date",
                    message="Date de livraison manquante",
                    value=date_raw,
                )
            )

        if row_errors:
            result.errors.extend(row_errors)
            continue

        order_ref = row.get("order_ref")
        order_ref = str(order_ref).strip() if order_ref not in (None, "") else None
        carrier = row.get("carrier")
        carrier = str(carrier).strip() if carrier not in (None, "") else None

        result.valid_rows.append(
            {
                "id": order_ref or f"row-{row_num}",
                "order_ref": order_ref,
                "phone": phone_raw,
                "phone_normalized": nphone,
                "status": status,
                "amount_collected": amount,
                "delivery_date": delivery_date,
                "carrier": carrier,
                "campaign_name": (
                    str(row["campaign_name"]).strip()
                    if "campaign_name" in df.columns and row.get("campaign_name")
                    else None
                ),
                "campaign_id": (
                    str(row["campaign_id"]).strip()
                    if "campaign_id" in df.columns and row.get("campaign_id")
                    else None
                ),
            }
        )

    result.valid_count = len(result.valid_rows)
    result.error_count = len({e.row for e in result.errors if e.row > 0})
    if result.valid_count and result.error_count:
        result.warnings.append(
            f"{result.error_count} ligne(s) rejetée(s), {result.valid_count} acceptée(s)."
        )
    return result


def parse_result_to_dict(result: ParseResult) -> dict[str, Any]:
    return {
        "valid_rows": result.valid_rows,
        "errors": [
            {"row": e.row, "field": e.field, "message": e.message, "value": e.value}
            for e in result.errors
        ],
        "warnings": result.warnings,
        "columns_detected": result.columns_detected,
        "total_rows": result.total_rows,
        "valid_count": result.valid_count,
        "error_count": result.error_count,
    }
