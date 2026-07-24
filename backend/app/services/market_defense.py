"""Market Defense and Analytics Anomaly Engine."""

from __future__ import annotations

import math
from typing import Any


def detect_cpm_anomalies(
    historical_data: list[float] | list[dict[str, Any]],
    current_data: float | dict[str, Any],
) -> dict[str, Any] | None:
    """
    Calculate the 7-day average (mean) and standard deviation of CPM.
    Calculate the Z-Score for the current CPM.
    If Z-Score > 2.0, generate and return an anomaly dictionary.
    """
    cpms = []
    for item in historical_data:
        if isinstance(item, dict):
            if "cpm" in item:
                cpms.append(float(item["cpm"]))
            elif item.get("impressions", 0) > 0:
                cpms.append((float(item.get("spend") or 0) / float(item["impressions"])) * 1000)
        else:
            cpms.append(float(item))

    curr_cpm = 0.0
    if isinstance(current_data, dict):
        if "cpm" in current_data:
            curr_cpm = float(current_data["cpm"])
        elif current_data.get("impressions", 0) > 0:
            curr_cpm = (float(current_data.get("spend") or 0) / float(current_data["impressions"])) * 1000
    else:
        curr_cpm = float(current_data)

    if len(cpms) < 2:
        return None

    mean = sum(cpms) / len(cpms)
    variance = sum((x - mean) ** 2 for x in cpms) / (len(cpms) - 1)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return None

    z_score = (curr_cpm - mean) / std_dev
    if z_score > 2.0:
        return {
            "anomaly_type": "cpm_spike",
            "severity": "critical" if z_score > 3.0 else "high",
            "message": (
                f"CPM anormalement élevé: {curr_cpm:.2f} MAD "
                f"(Moyenne 7j: {mean:.2f} MAD, Z-Score: {z_score:.2f}). "
                "Pression concurrentielle suspectée."
            ),
            "detected_value": curr_cpm,
            "baseline_mean": mean,
            "z_score": z_score,
        }

    return None


def diagnose_funnel(
    historical_metrics: dict[str, Any],
    current_metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Compare current Hook Rate (3s views/impressions), CTR, and CVR against a 14-day average.
    If any drops by more than 20% compared to the baseline, flag it as a funnel anomaly.
    """
    anomalies = []
    metrics_to_check = [
        ("hook_rate", "Hook Rate (3s view rate)"),
        ("ctr", "CTR (Taux de clic)"),
        ("cvr", "CVR (Taux de conversion)"),
    ]

    for key, label in metrics_to_check:
        hist_val = float(historical_metrics.get(key) or 0)
        curr_val = float(current_metrics.get(key) or 0)

        if hist_val > 0:
            drop = (hist_val - curr_val) / hist_val
            if drop > 0.20:
                severity = "high" if drop > 0.40 else "medium"
                anomalies.append({
                    "anomaly_type": "funnel_drop",
                    "severity": severity,
                    "message": (
                        f"Baisse du {label}: {curr_val*100:.2f}% contre une moyenne 14j de "
                        f"{hist_val*100:.2f}% (Chute de {drop*100:.1f}%). "
                        "Fatigue créative ou problème landing page probable."
                    ),
                    "metric_name": key,
                    "detected_value": curr_val,
                    "baseline_mean": hist_val,
                    "drop_percentage": drop,
                })

    return anomalies
