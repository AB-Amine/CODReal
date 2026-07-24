from app.services.market_defense import detect_cpm_anomalies, diagnose_funnel


def test_detect_cpm_anomalies():
    # Standard deviation of identical items is 0
    assert detect_cpm_anomalies([10, 10], 15) is None

    # CPM list with low variance: mean around 10, std dev around 1
    # Current CPM is 16.0 (Z-score should be high, > 2.0)
    res = detect_cpm_anomalies([10.0, 11.0, 10.0, 12.0, 10.0, 9.0, 11.0], 16.0)
    assert res is not None
    assert res["anomaly_type"] == "cpm_spike"
    assert res["z_score"] > 2.0


def test_diagnose_funnel():
    hist = {"hook_rate": 0.30, "ctr": 0.02, "cvr": 0.03}

    # No drop
    curr_ok = {"hook_rate": 0.29, "ctr": 0.019, "cvr": 0.029}
    assert len(diagnose_funnel(hist, curr_ok)) == 0

    # Large drops: CVR drops from 3% to 2% (33% drop), CTR drops from 2% to 1.5% (25% drop)
    curr_bad = {"hook_rate": 0.30, "ctr": 0.015, "cvr": 0.02}
    res = diagnose_funnel(hist, curr_bad)
    assert len(res) == 2

    metrics = [r["metric_name"] for r in res]
    assert "cvr" in metrics
    assert "ctr" in metrics
