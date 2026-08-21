"""
main.py

This is the entry point of the project.
It loads the use case data, scores each one, ranks them,
and saves a prioritized report as a CSV file.

Run it with:
    python main.py
"""

import csv
from scoring import score_use_case, priority_tier

INPUT_FILE = "data/use_cases.csv"
OUTPUT_FILE = "output/prioritized_report.csv"

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


def build_report(use_cases):
    """Score every use case and return the report rows, sorted best first."""
    report_rows = []

    for case in use_cases:
        scores = score_use_case(case)
        row = {
            "use_case_id": case["use_case_id"],
            "name": case["name"],
            "business_area": case["business_area"],
            "business_impact": scores["business_impact"],
            "data_availability": scores["data_availability"],
            "technical_feasibility": scores["technical_feasibility"],
            "cost_effort": scores["cost_effort"],
            "final_score": scores["final_score"],
            "priority": priority_tier(scores["final_score"]),
        }
        report_rows.append(row)

    report_rows.sort(key=lambda r: r["final_score"], reverse=True)
    return report_rows


def save_report(report_rows, path):
    """Write the report rows to a CSV file."""
    fieldnames = [
        "use_case_id", "name", "business_area",
        "business_impact", "data_availability",
        "technical_feasibility", "cost_effort",
        "final_score", "priority",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)


def print_summary(report_rows):
    """Print a simple ranked summary to the terminal."""
    print("\nUse Case Prioritization Report")
    print("=" * 60)
    for i, row in enumerate(report_rows, start=1):
        print(f"{i}. {row['name']} ({row['business_area']})")
        print(f"   Final Score: {row['final_score']} / 5  -  {row['priority']}")
    print("=" * 60)


def main():
    use_cases = load_use_cases(INPUT_FILE)
    report_rows = build_report(use_cases)
    save_report(report_rows, OUTPUT_FILE)
    print_summary(report_rows)
    print(f"\nFull report saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
