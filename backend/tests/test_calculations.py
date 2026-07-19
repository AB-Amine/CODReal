from app.services.calculations import (
    CalculationEngine,
    CampaignInput,
    OrderForCalc,
)


def test_real_metrics():
    engine = CalculationEngine(default_return_fee=25.0)
    campaign = CampaignInput(
        campaign_id="c1",
        name="Summer COD",
        platform="meta",
        spend=1000.0,
    )
    orders = [
        OrderForCalc("o1", "c1", "delivered", 450),
        OrderForCalc("o2", "c1", "delivered", 450),
        OrderForCalc("o3", "c1", "returned", 0),
        OrderForCalc("o4", "c1", "refused", 0),
    ]
    m = engine.compute_campaign(campaign, orders)
    assert m.delivered_orders == 2
    assert m.returned_orders == 1
    assert m.refused_orders == 1
    assert m.net_revenue == 900.0
    assert m.return_fees == 50.0  # 2 * 25
    assert m.net_profit == 900 - 1000 - 50  # -150
    assert m.real_cpa == 500.0  # 1000 / 2
    assert m.real_roas == 0.9  # 900 / 1000
    assert m.performance_score == "critical"


def test_dashboard_aggregation():
    engine = CalculationEngine()
    campaigns = [
        CampaignInput("c1", "A", "meta", spend=500),
        CampaignInput("c2", "B", "tiktok", spend=300),
    ]
    orders = [
        OrderForCalc("1", "c1", "delivered", 800),
        OrderForCalc("2", "c2", "delivered", 200),
        OrderForCalc("3", "c2", "returned", 0),
    ]
    kpis = engine.compute_dashboard(campaigns, orders)
    assert kpis.total_ad_spend == 800
    assert kpis.delivered_revenue == 1000
    assert kpis.total_delivered == 2
    assert kpis.total_campaigns == 2
    assert kpis.real_roas == 1.25
