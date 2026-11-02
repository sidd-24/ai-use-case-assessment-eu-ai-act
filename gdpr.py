"""
gdpr.py

This file checks whether a use case needs a Data Protection Impact
Assessment (DPIA) under Article 35 GDPR.

It uses the cases listed in Article 35(3) and the criteria from the
EDPB guidelines on DPIAs (WP248 rev.01): if processing meets two or more
criteria, a DPIA is required in most cases.
"""
from ai_act import is_yes

# EDPB criteria and the risk profile column that answers each one
EDPB_CRITERIA = {
    "profiling": "Evaluation or scoring of people",
    "automated_decision": "Automated decision with legal or similarly significant effect",
    "systematic_monitoring": "Systematic monitoring of people",
    "special_category_data": "Sensitive data (Art. 9 special categories)",
    "large_scale": "Processing on a large scale",
    "combines_datasets": "Matching or combining datasets",
    "vulnerable_subjects": "Vulnerable data subjects (e.g. employees, applicants, children)",
    "innovative_technology": "Innovative use of technology",
}


def assess_dpia(profile):
    """
    Take one risk profile row.
    Return a dictionary with the DPIA status and the reasons behind it.
    Status is one of: Required, Screening recommended, Not required,
    Not applicable (no personal data) or Not assessed.
    """
    if profile is None:
        return {"status": "Not assessed", "reasons": [], "art_22": False}
    if not is_yes(profile["personal_data"]):
        return {"status": "Not applicable", "reasons": ["No personal data processed"], "art_22": False}

    met = [label for column, label in EDPB_CRITERIA.items() if is_yes(profile[column])]
    reasons = []

    # Article 35(3)(a): extensive evaluation by automated means, including
    # profiling, that leads to decisions with legal effect
    if is_yes(profile["profiling"]) and is_yes(profile["automated_decision"]):
        reasons.append("Art. 35(3)(a) automated evaluation with legal or similar effect")
    # Article 35(3)(b): large-scale processing of special category data
    if is_yes(profile["large_scale"]) and is_yes(profile["special_category_data"]):
        reasons.append("Art. 35(3)(b) large-scale processing of sensitive data")

    if reasons or len(met) >= 2:
        status = "Required"
    elif len(met) == 1:
        status = "Screening recommended"
    else:
        status = "Not required"

    reasons += [f"EDPB criterion: {label}" for label in met]
    # Article 22: people may not be subject to purely automated decisions
    # with legal effect without safeguards such as human intervention
    return {"status": status, "reasons": reasons, "art_22": is_yes(profile["automated_decision"])}
