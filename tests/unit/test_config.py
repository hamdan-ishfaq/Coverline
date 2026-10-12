"""Config YAMLs load and validate, and bake in the settled decisions."""

from config.loader import load_costs, load_llm, load_policy, load_prereg, load_thresholds


def test_thresholds_match_prereg():
    t = load_thresholds()
    p = load_prereg()
    assert t.tolerance_days == p.label.tolerance_days == 1
    assert t.snapshot_h.base == p.label.snapshot_h.base == 14
    assert t.snapshot_h.min == p.label.snapshot_h.min == 7
    assert t.snapshot_h.max == p.label.snapshot_h.max == 28


def test_thresholds_cost_based_escalation():
    assert load_thresholds().escalation_threshold_mode == "cost_based"


def test_costs_are_usd_with_defaults():
    c = load_costs()
    assert c.currency == "USD"
    assert c.line_down_cost_per_day == {"A": 2000.0, "B": 500.0, "C": 100.0}
    assert c.expedite_success.reliable > c.expedite_success.chronically_late
    assert c.threshold_cost_matrix.c_false_negative / c.threshold_cost_matrix.c_false_positive == 5.0


def test_policy_defaults():
    p = load_policy()
    assert p.kill_switch is False
    assert p.default_level == "L2"
    assert p.approval_bands[-1].approver == "head_of_supply_chain"


def test_llm_provider_chain_groq_first_gemini_then_openrouter():
    l = load_llm()
    assert l.mode in {"live", "replay", "template"}
    assert [p.name for p in l.providers] == ["groq", "gemini", "openrouter"]
    assert all(p.key_env in {"GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"} for p in l.providers)