from app.services.matching import LeadCandidate, MatchingEngine, OrderRecord


def test_phone_match():
    engine = MatchingEngine()
    leads = [
        LeadCandidate(id="l1", campaign_id="c1", phone="0612345678"),
        LeadCandidate(id="l2", campaign_id="c2", phone="+212698765432"),
    ]
    orders = [
        OrderRecord(id="o1", phone="+212612345678", status="delivered", amount_collected=400),
        OrderRecord(id="o2", phone="0698765432", status="returned", amount_collected=0),
        OrderRecord(id="o3", phone="0600000000", status="pending", amount_collected=0),
    ]
    report = engine.match(leads, orders)
    assert report.stats["matched"] == 2
    assert "o3" in report.unmatched_orders
    assert {m.campaign_id for m in report.matches} == {"c1", "c2"}


def test_order_ref_priority():
    engine = MatchingEngine()
    leads = [
        LeadCandidate(id="l1", campaign_id="c_phone", phone="0611111111"),
        LeadCandidate(id="l2", campaign_id="c_ref", phone="0699999999", order_ref="CMD-1"),
    ]
    orders = [
        OrderRecord(
            id="o1",
            phone="0611111111",
            order_ref="CMD-1",
            status="delivered",
            amount_collected=300,
        ),
    ]
    report = engine.match(leads, orders)
    assert len(report.matches) == 1
    assert report.matches[0].campaign_id == "c_ref"
    assert report.matches[0].match_type.value == "order_ref"


def test_phone_to_campaign_fallback():
    engine = MatchingEngine()
    orders = [
        OrderRecord(id="o1", phone="0612345678", status="delivered", amount_collected=500),
    ]
    report = engine.match(
        [],
        orders,
        phone_to_campaign={"612345678": "camp-meta-1"},
    )
    assert len(report.matches) == 1
    assert report.matches[0].campaign_id == "camp-meta-1"
