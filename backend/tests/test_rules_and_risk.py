from app.agents.rules import analyze_rules
from app.agents.risk import risk_level_from_score


def test_blocked_click_link_high():
    rule, _, _ = analyze_rules("Your account blocked click link")
    assert risk_level_from_score(rule.score) in ("MEDIUM", "HIGH")
    assert rule.score >= 31


def test_share_otp_high():
    rule, _, _ = analyze_rules("Share OTP to verify account")
    assert risk_level_from_score(rule.score) == "HIGH"
    assert rule.score >= 61


def test_order_shipped_low():
    rule, _, _ = analyze_rules("Your order shipped")
    assert risk_level_from_score(rule.score) == "LOW"
    assert rule.score <= 30


def test_anydesk_remote_access_high():
    rule, _, _ = analyze_rules("Install AnyDesk and share code for bank refund support")
    assert risk_level_from_score(rule.score) == "HIGH"
    assert rule.score >= 61


def test_collect_to_receive_high():
    rule, _, _ = analyze_rules("To receive money, accept the collect request in your UPI app")
    assert risk_level_from_score(rule.score) == "HIGH"
    assert rule.score >= 61

