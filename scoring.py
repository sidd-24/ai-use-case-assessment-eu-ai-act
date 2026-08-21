"""
scoring.py

This file holds the scoring rules for the framework.
Each use case is scored on four categories.
Each category is an average of a few sub questions.
The four category scores are then combined using weights
to get one final priority score.
"""

# Weight of each category in the final score.
# These should add up to 1.0
CATEGORY_WEIGHTS = {
    "business_impact": 0.35,
    "data_availability": 0.25,
    "technical_feasibility": 0.25,
    "cost_effort": 0.15,
}

# Which raw columns belong to which category
CATEGORY_COLUMNS = {
    "business_impact": ["revenue_impact", "cost_saving_impact", "strategic_alignment"],
    "data_availability": ["data_exists", "data_quality", "data_accessibility"],
    "technical_feasibility": ["tech_maturity", "team_skill_fit", "integration_ease"],
    "cost_effort": ["cost_estimate", "time_estimate"],
}


def score_category(row, category):
    """
    Take one use case row and one category name.
    Return the average score for that category.
    """
    columns = CATEGORY_COLUMNS[category]
    values = [row[col] for col in columns]
    return sum(values) / len(values)


def score_use_case(row):
    """
    Take one use case row.
    Return a dictionary with each category score and the final weighted score.
    """
    result = {}

    for category in CATEGORY_WEIGHTS:
        result[category] = round(score_category(row, category), 2)

    final_score = 0
    for category, weight in CATEGORY_WEIGHTS.items():
        final_score += result[category] * weight

    result["final_score"] = round(final_score, 2)
    return result


def priority_tier(final_score):
    """
    Turn a final score into a simple label.
    Score is out of 5.
    """
    if final_score >= 4.0:
        return "High Priority"
    elif final_score >= 3.0:
        return "Medium Priority"
    else:
        return "Low Priority"
