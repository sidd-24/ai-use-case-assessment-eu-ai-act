"""
main.py

This is the entry point of the project.
It loads the use cases and their risk questionnaires, scores and
classifies each one, ranks them, and saves the portfolio reports.

Run it with:
    python main.py
"""

import csv
from pathlib import Path

from portfolio import build_portfolio
from report import save_matrix, write_excel, write_pdf

INPUT_FILE = "data/use_cases.csv"
RISK_FILE = "data/risk_profile.csv"
OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "prioritized_report.csv"

# Columns that hold raw scores, these need to be read as numbers
SCORE_COLUMNS = [
    "revenue_impact", "cost_saving_impact", "strategic_alignment",
    "data_exists", "data_quality", "data_accessibility",
    "tech_maturity", "team_skill_fit", "integration_ease",
    "cost_estimate", "time_estimate",
]


def load_use_cases(path):
    """Read the CSV file and return a list of use case dictionaries."""
    use_cases = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for col in SCORE_COLUMNS:
                row[col] = int(row[col])
            use_cases.append(row)
    return use_cases


def load_risk_profiles(path):
    """Read the risk questionnaire and return a dictionary keyed by use case id."""
    if not Path(path).exists():
        return {}
    with open(path, "r", newline="", encoding="utf-8") as f:
        return {row["use_case_id"]: {k: v.strip() for k, v in row.items()} for row in csv.DictReader(f)}


def save_report(report_rows, path):
    """Write the report rows to a CSV file."""
    fieldnames = [
        "use_case_id", "name", "business_area",
        "business_impact", "data_availability",
        "technical_feasibility", "cost_effort",
        "final_score", "compliance_overhead", "adjusted_score", "priority",
        "quadrant", "ai_act_tier", "ai_act_basis", "dpia", "fria", "gate",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report_rows)


def print_summary(report_rows):
    """Print a simple ranked summary to the terminal."""
    print("\nUse Case Portfolio Report")
    print("=" * 72)
    for i, row in enumerate(report_rows, start=1):
        print(f"{i}. {row['name']} ({row['business_area']})")
        print(f"   Score: {row['adjusted_score']} / 5 (before compliance {row['final_score']})"
              f"  -  {row['priority']}  -  {row['quadrant']}")
        print(f"   AI Act: {row['ai_act_tier']}  |  DPIA: {row['dpia']}  |  Gate: {row['gate']}")
        if row["conditions"]:
            print(f"   Conditions: {'; '.join(row['conditions'])}")
    print("=" * 72)


def main():
    use_cases = load_use_cases(INPUT_FILE)
    profiles = load_risk_profiles(RISK_FILE)
    report_rows = build_portfolio(use_cases, profiles)

    OUTPUT_DIR.mkdir(exist_ok=True)
    save_report(report_rows, OUTPUT_FILE)
    matrix = save_matrix(report_rows, OUTPUT_DIR / "portfolio_matrix.png")
    workbook = write_excel(report_rows, OUTPUT_DIR / "AI_Use_Case_Portfolio.xlsx", matrix)
    one_pager = write_pdf(report_rows, OUTPUT_DIR / "steering_one_pager.pdf")

    print_summary(report_rows)
    print(f"\nReports saved to {OUTPUT_FILE}, {workbook}, {one_pager} and {matrix}")


if __name__ == "__main__":
    main()
