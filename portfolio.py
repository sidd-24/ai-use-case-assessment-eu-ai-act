"""
portfolio.py

This file combines the business score with the compliance checks.

Each use case gets:
- a value score (business impact) and a feasibility score
  (data, technology, cost), both out of 5
- a compliance overhead that lowers feasibility, because meeting
  AI Act and GDPR obligations costs time and money
- a quadrant in the value vs feasibility matrix
- a gate decision: Go, Go with conditions, Stop or Assess first
"""
from ai_act import classify, obligations, needs_fria
from gdpr import assess_dpia
from scoring import CATEGORY_WEIGHTS, score_use_case, priority_tier

# Feasibility points removed for compliance work. These are planning
# assumptions, not a judgement of the idea. A provider of a high-risk
# system carries the full conformity work, a deployer a smaller share.
COMPLIANCE_OVERHEAD = {
    ("High-risk", "provider"): 1.0,
    ("High-risk", "deployer"): 0.5,
    ("Limited", "provider"): 0.25,
    ("Limited", "deployer"): 0.1,
}
DPIA_OVERHEAD = 0.25
FRIA_OVERHEAD = 0.25

# Value and feasibility above this line count as high in the matrix
QUADRANT_SPLIT = 3.0

FEASIBILITY_CATEGORIES = ["data_availability", "technical_feasibility", "cost_effort"]

# Order of gate decisions in the ranked report
GATE_ORDER = {"Go": 0, "Go with conditions": 1, "Assess first": 2, "Stop": 3}


def feasibility_score(scores):
    """Weighted average of the three feasibility categories, out of 5."""
    total_weight = sum(CATEGORY_WEIGHTS[c] for c in FEASIBILITY_CATEGORIES)
    return sum(scores[c] * CATEGORY_WEIGHTS[c] for c in FEASIBILITY_CATEGORIES) / total_weight


def compliance_overhead(profile, classification, dpia):
    """Feasibility points to subtract for compliance work."""
    if profile is None:
        return 0.0
    overhead = COMPLIANCE_OVERHEAD.get((classification["tier"], profile["role"]), 0.0)
    if dpia["status"] == "Required":
        overhead += DPIA_OVERHEAD
    if needs_fria(profile, classification):
        overhead += FRIA_OVERHEAD
    return overhead


def quadrant(value, feasibility):
    """Place a use case in one of the four matrix quadrants."""
    if value >= QUADRANT_SPLIT:
        return "Quick win" if feasibility >= QUADRANT_SPLIT else "Strategic bet"
    return "Fill-in" if feasibility >= QUADRANT_SPLIT else "Deprioritise"


def gate(classification, dpia):
    """
    Decide whether a use case can go ahead.
    Return the decision and the conditions that must be met first.
    """
    tier = classification["tier"]
    if tier == "Prohibited":
        return "Stop", [f"Prohibited practice under {classification['basis']}"]
    if tier == "Not assessed":
        return "Assess first", ["Answer the risk questionnaire"]

    conditions = []
    if tier == "High-risk":
        conditions.append("Meet high-risk requirements before go-live")
    if tier == "Limited":
        conditions.append("Build in AI transparency notices")
    if dpia["status"] == "Required":
        conditions.append("Complete a DPIA before processing")
    elif dpia["status"] == "Screening recommended":
        conditions.append("Document a DPIA screening")
    if dpia["art_22"]:
        conditions.append("Human review of automated decisions (Art. 22 GDPR)")
    return ("Go with conditions" if conditions else "Go"), conditions


def assess(use_case, profile):
    """
    Take one use case row and its risk profile (or None).
    Return one report row with business, compliance and portfolio results.
    """
    scores = score_use_case(use_case)
    classification = classify(profile)
    dpia = assess_dpia(profile)

    value = scores["business_impact"]
    feasibility = feasibility_score(scores)
    overhead = compliance_overhead(profile, classification, dpia)
    adjusted_feasibility = max(1.0, feasibility - overhead)

    # Same weights as the original score, with feasibility after compliance
    value_weight = CATEGORY_WEIGHTS["business_impact"]
    adjusted_score = value_weight * value + (1 - value_weight) * adjusted_feasibility

    decision, conditions = gate(classification, dpia)
    return {
        "use_case_id": use_case["use_case_id"],
        "name": use_case["name"],
        "business_area": use_case["business_area"],
        **scores,
        "value": round(value, 2),
        "feasibility": round(feasibility, 2),
        "compliance_overhead": round(overhead, 2),
        "adjusted_feasibility": round(adjusted_feasibility, 2),
        "adjusted_score": round(adjusted_score, 2),
        "quadrant": quadrant(value, adjusted_feasibility),
        "ai_act_tier": classification["tier"],
        "ai_act_basis": classification["basis"],
        "role": profile["role"] if profile else "",
        "dpia": dpia["status"],
        "dpia_reasons": dpia["reasons"],
        "fria": needs_fria(profile, classification) if profile else False,
        "obligations": obligations(profile, classification),
        "gate": decision,
        "conditions": conditions,
        "priority": "Blocked" if decision == "Stop" else priority_tier(round(adjusted_score, 2)),
    }


def build_portfolio(use_cases, profiles):
    """
    Assess every use case and rank them.
    Stopped and unassessed use cases go to the bottom, the rest are
    sorted by compliance-adjusted score, best first.
    """
    rows = [assess(case, profiles.get(case["use_case_id"])) for case in use_cases]
    rows.sort(key=lambda r: (GATE_ORDER[r["gate"]] >= 2, -r["adjusted_score"]))
    return rows
