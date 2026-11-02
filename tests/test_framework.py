"""Tests for the risk classification, DPIA check, portfolio logic and reports."""
import pytest

import main
from ai_act import classify, obligations
from gdpr import assess_dpia
from portfolio import assess, build_portfolio, quadrant
from report import save_matrix, write_excel, write_pdf

# A low-risk profile; each test switches on only what it needs
BASE = {
    "use_case_id": "T1", "role": "provider", "is_ai_system": "yes", "prohibited_practice": "none",
    "annex_iii_area": "none", "safety_component": "no", "profiling": "no", "narrow_procedural_task": "no",
    "interacts_with_people": "no", "generates_synthetic_content": "no", "public_body": "no",
    "personal_data": "no", "special_category_data": "no", "automated_decision": "no",
    "systematic_monitoring": "no", "large_scale": "no", "combines_datasets": "no",
    "vulnerable_subjects": "no", "innovative_technology": "no",
}

USE_CASE = {
    "use_case_id": "T1", "name": "Test", "business_area": "IT",
    "revenue_impact": 4, "cost_saving_impact": 4, "strategic_alignment": 4,
    "data_exists": 4, "data_quality": 4, "data_accessibility": 4,
    "tech_maturity": 4, "team_skill_fit": 4, "integration_ease": 4,
    "cost_estimate": 4, "time_estimate": 4,
}


def profile(**answers):
    return {**BASE, **answers}


# ─── EU AI Act ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("answers, tier", [
    ({}, "Minimal"),
    ({"is_ai_system": "no"}, "Out of scope"),
    ({"prohibited_practice": "emotion_recognition_workplace"}, "Prohibited"),
    ({"annex_iii_area": "employment", "profiling": "yes"}, "High-risk"),
    ({"safety_component": "yes"}, "High-risk"),
    ({"interacts_with_people": "yes"}, "Limited"),
    ({"generates_synthetic_content": "yes"}, "Limited"),
])
def test_risk_tiers(answers, tier):
    assert classify(profile(**answers))["tier"] == tier


def test_prohibited_wins_over_everything_else():
    result = classify(profile(prohibited_practice="social_scoring", annex_iii_area="employment"))
    assert result["tier"] == "Prohibited" and "5(1)(c)" in result["basis"]


def test_art_6_3_exception_only_without_profiling():
    narrow = classify(profile(annex_iii_area="education", narrow_procedural_task="yes"))
    assert narrow["tier"] == "Minimal" and narrow["art_6_3_exception"]
    assert any("Art. 6(4)" in o for o in obligations(profile(), narrow))

    # Profiling of people always keeps an Annex III system high-risk
    profiled = classify(profile(annex_iii_area="education", narrow_procedural_task="yes", profiling="yes"))
    assert profiled["tier"] == "High-risk"


def test_high_risk_obligations_depend_on_role():
    answers = {"annex_iii_area": "credit_scoring", "profiling": "yes"}
    provider = obligations(profile(**answers), classify(profile(**answers)))
    deployer = obligations(profile(role="deployer", **answers), classify(profile(**answers)))
    assert any("Art. 43" in o for o in provider) and not any("Art. 43" in o for o in deployer)
    assert all(any("Art. 27" in o for o in duties) for duties in (provider, deployer))   # FRIA for credit scoring


def test_unknown_codes_are_rejected():
    with pytest.raises(ValueError, match="annex_iii_area"):
        classify(profile(annex_iii_area="hiring"))
    with pytest.raises(ValueError, match="role"):
        classify(profile(role="vendor"))


# ─── GDPR DPIA ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("answers, status", [
    ({}, "Not applicable"),
    ({"personal_data": "yes"}, "Not required"),
    ({"personal_data": "yes", "innovative_technology": "yes"}, "Screening recommended"),
    ({"personal_data": "yes", "vulnerable_subjects": "yes", "combines_datasets": "yes"}, "Required"),
])
def test_dpia_edpb_criteria(answers, status):
    assert assess_dpia(profile(**answers))["status"] == status


def test_dpia_art_35_3_a_and_art_22():
    result = assess_dpia(profile(personal_data="yes", profiling="yes", automated_decision="yes"))
    assert result["status"] == "Required" and result["art_22"]
    assert any("35(3)(a)" in r for r in result["reasons"])


# ─── Portfolio ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value, feasibility, expected", [
    (4, 4, "Quick win"), (4, 2, "Strategic bet"), (2, 4, "Fill-in"), (2, 2, "Deprioritise"),
])
def test_quadrants(value, feasibility, expected):
    assert quadrant(value, feasibility) == expected


def test_compliance_overhead_lowers_feasibility_and_score():
    minimal = assess(USE_CASE, profile())
    high = assess(USE_CASE, profile(annex_iii_area="employment", profiling="yes",
                                    personal_data="yes", vulnerable_subjects="yes", innovative_technology="yes"))
    assert minimal["adjusted_score"] == minimal["final_score"] == 4.0   # no compliance work, no change
    assert high["compliance_overhead"] == 1.25                         # high-risk provider + DPIA
    assert high["adjusted_feasibility"] == 2.75 and high["adjusted_score"] < high["final_score"]
    assert high["gate"] == "Go with conditions"


def test_prohibited_is_blocked_and_ranked_last():
    stronger = {**USE_CASE, "use_case_id": "T2"}
    rows = build_portfolio([stronger, {**USE_CASE, "revenue_impact": 1}],
                           {"T2": profile(prohibited_practice="manipulation"), "T1": profile()})
    assert [r["use_case_id"] for r in rows] == ["T1", "T2"]
    assert rows[-1]["gate"] == "Stop" and rows[-1]["priority"] == "Blocked"


def test_missing_questionnaire_means_assess_first():
    row = assess(USE_CASE, None)
    assert row["ai_act_tier"] == "Not assessed" and row["gate"] == "Assess first"


# ─── Shipped data and reports ──────────────────────────────────────────────────

def test_every_use_case_has_a_valid_risk_profile():
    use_cases = main.load_use_cases(main.INPUT_FILE)
    profiles = main.load_risk_profiles(main.RISK_FILE)
    assert {u["use_case_id"] for u in use_cases} == set(profiles)
    rows = build_portfolio(use_cases, profiles)
    tiers = {r["use_case_id"]: r["ai_act_tier"] for r in rows}
    assert tiers["UC003"] == "High-risk" and tiers["UC009"] == "Prohibited"


def test_reports_are_written(tmp_path):
    rows = build_portfolio(main.load_use_cases(main.INPUT_FILE), main.load_risk_profiles(main.RISK_FILE))
    png = save_matrix(rows, tmp_path / "matrix.png")
    xlsx = write_excel(rows, tmp_path / "portfolio.xlsx", png)
    pdf = write_pdf(rows, tmp_path / "one_pager.pdf")

    from openpyxl import load_workbook
    assert load_workbook(xlsx).sheetnames == ["Portfolio", "Matrix", "Obligations", "Method"]
    with open(pdf, "rb") as f:
        assert f.read(4) == b"%PDF"
