"""
ai_act.py

This file sorts each use case into an EU AI Act risk tier and lists
the obligations that come with it (Regulation (EU) 2024/1689).

The answers come from data/risk_profile.csv, one row per use case.
This is a screening aid to structure the conversation with legal and
compliance teams. It does not replace a legal assessment.
"""

# Risk tiers, from most to least restrictive
TIERS = ["Prohibited", "High-risk", "Limited", "Minimal", "Out of scope", "Not assessed"]

# Prohibited practices, Article 5(1)
PROHIBITED_PRACTICES = {
    "manipulation": "Art. 5(1)(a) manipulative or deceptive techniques",
    "exploiting_vulnerabilities": "Art. 5(1)(b) exploiting vulnerabilities of age, disability or social situation",
    "social_scoring": "Art. 5(1)(c) social scoring",
    "predictive_policing": "Art. 5(1)(d) predicting crime risk from profiling alone",
    "facial_scraping": "Art. 5(1)(e) untargeted scraping of facial images",
    "emotion_recognition_workplace": "Art. 5(1)(f) emotion recognition in the workplace or education",
    "biometric_categorisation": "Art. 5(1)(g) biometric categorisation by sensitive traits",
    "realtime_biometric_id": "Art. 5(1)(h) real-time remote biometric identification for law enforcement",
}

# High-risk areas, Annex III
ANNEX_III_AREAS = {
    "biometrics": "Annex III(1) biometrics",
    "critical_infrastructure": "Annex III(2) critical infrastructure",
    "education": "Annex III(3) education and vocational training",
    "employment": "Annex III(4) employment and workers management",
    "essential_services": "Annex III(5)(a) access to public benefits and services",
    "credit_scoring": "Annex III(5)(b) creditworthiness and credit scoring",
    "insurance_pricing": "Annex III(5)(c) life and health insurance pricing",
    "law_enforcement": "Annex III(6) law enforcement",
    "migration": "Annex III(7) migration, asylum and border control",
    "justice_democracy": "Annex III(8) justice and democratic processes",
}

ROLES = ["provider", "deployer"]

PROVIDER_HIGH_RISK = [
    "Risk management system across the lifecycle (Art. 9)",
    "Data governance: relevant, representative training data and bias checks (Art. 10)",
    "Technical documentation (Art. 11, Annex IV)",
    "Automatic event logging (Art. 12)",
    "Instructions for use for deployers (Art. 13)",
    "Human oversight designed into the system (Art. 14)",
    "Accuracy, robustness and cybersecurity (Art. 15)",
    "Quality management system (Art. 17)",
    "Conformity assessment, EU declaration of conformity and CE marking (Art. 43, 47, 48)",
    "Registration in the EU database (Art. 49)",
    "Post-market monitoring and serious incident reporting (Art. 72, 73)",
]

DEPLOYER_HIGH_RISK = [
    "Use the system according to the provider's instructions (Art. 26(1))",
    "Assign human oversight to trained, competent staff (Art. 26(2))",
    "Make sure input data is relevant and representative (Art. 26(4))",
    "Monitor operation and report risks or incidents to the provider (Art. 26(5))",
    "Keep the automatically generated logs for at least six months (Art. 26(6))",
    "Inform affected persons that a high-risk AI system is used for decisions about them (Art. 26(11))",
    "Explain individual decisions on request (Art. 86)",
]


def is_yes(value):
    """Turn a yes/no answer from the CSV into True or False."""
    return str(value).strip().lower() in ("yes", "y", "true", "1")


def validate_profile(profile):
    """
    Check one risk profile row for unknown codes.
    Raise a ValueError naming the use case and the bad value.
    """
    case_id = profile.get("use_case_id", "?")
    if profile["role"] not in ROLES:
        raise ValueError(f"{case_id}: role must be one of {ROLES}, got '{profile['role']}'")
    if profile["prohibited_practice"] not in ("none", *PROHIBITED_PRACTICES):
        raise ValueError(f"{case_id}: unknown prohibited_practice '{profile['prohibited_practice']}'")
    if profile["annex_iii_area"] not in ("none", *ANNEX_III_AREAS):
        raise ValueError(f"{case_id}: unknown annex_iii_area '{profile['annex_iii_area']}'")


def classify(profile):
    """
    Take one risk profile row.
    Return a dictionary with the risk tier, the legal basis and
    whether the Article 6(3) exception or Article 50 transparency applies.
    """
    if profile is None:
        return {"tier": "Not assessed", "basis": "No risk questionnaire answered yet",
                "art_6_3_exception": False, "transparency": False}

    validate_profile(profile)
    transparency = is_yes(profile["interacts_with_people"]) or is_yes(profile["generates_synthetic_content"])
    result = {"art_6_3_exception": False, "transparency": transparency}

    # Article 3(1): rule-based software and plain reporting are not AI systems
    if not is_yes(profile["is_ai_system"]):
        result.update(tier="Out of scope", basis="Not an AI system under Art. 3(1)", transparency=False)
        return result

    if profile["prohibited_practice"] != "none":
        result.update(tier="Prohibited", basis=PROHIBITED_PRACTICES[profile["prohibited_practice"]])
        return result

    # Article 6(1): safety component of a product covered by Annex I
    if is_yes(profile["safety_component"]):
        result.update(tier="High-risk", basis="Art. 6(1) safety component of an Annex I product")
        return result

    area = profile["annex_iii_area"]
    if area != "none":
        # Article 6(3): an Annex III system is not high-risk when it only does a
        # narrow procedural task, but never when it profiles people
        if is_yes(profile["narrow_procedural_task"]) and not is_yes(profile["profiling"]):
            result["art_6_3_exception"] = True
        else:
            result.update(tier="High-risk", basis=f"Art. 6(2), {ANNEX_III_AREAS[area]}")
            return result

    if transparency:
        result.update(tier="Limited", basis="Art. 50 transparency obligations")
    else:
        result.update(tier="Minimal", basis="No specific obligations under the AI Act")
    if result["art_6_3_exception"]:
        result["basis"] += f" (Art. 6(3) exception from {ANNEX_III_AREAS[area]})"
    return result


def needs_fria(profile, classification):
    """
    Article 27: a fundamental rights impact assessment is needed before
    a high-risk system is used by a public body, or for credit scoring
    and life or health insurance pricing.
    """
    if classification["tier"] != "High-risk":
        return False
    return is_yes(profile["public_body"]) or profile["annex_iii_area"] in ("credit_scoring", "insurance_pricing")


def obligations(profile, classification):
    """
    Take a risk profile and its classification.
    Return the list of obligations that apply.
    A provider that builds the system for its own use is also its deployer,
    so it gets both lists.
    """
    tier = classification["tier"]
    if tier == "Not assessed":
        return ["Answer the risk questionnaire before any go decision"]
    if tier == "Out of scope":
        return []
    if tier == "Prohibited":
        return [f"Do not develop or use: {classification['basis']}"]

    items = ["AI literacy for staff who build or operate the system (Art. 4)"]
    provider = profile["role"] == "provider"

    if tier == "High-risk":
        if provider:
            items += PROVIDER_HIGH_RISK
        items += DEPLOYER_HIGH_RISK
        if profile["annex_iii_area"] == "employment":
            items.append("Inform workers and their representatives before use (Art. 26(7))")
        if needs_fria(profile, classification):
            items.append("Fundamental rights impact assessment before first use (Art. 27)")

    if classification["art_6_3_exception"]:
        items.append("Document why the system is not high-risk and register it (Art. 6(4), 49(2))")

    if classification["transparency"]:
        if is_yes(profile["interacts_with_people"]) and provider:
            items.append("Tell people they are interacting with an AI system (Art. 50(1))")
        if is_yes(profile["generates_synthetic_content"]):
            if provider:
                items.append("Mark generated content as AI-generated in a machine-readable way (Art. 50(2))")
            items.append("Disclose deepfakes and AI-generated text published to inform the public (Art. 50(4))")

    if tier == "Minimal":
        items.append("Optional: follow a voluntary code of conduct (Art. 95)")
    return items
