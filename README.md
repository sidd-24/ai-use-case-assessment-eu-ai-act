# Data and AI Use Case Structuring and Feasibility Assessment Framework

## What this project does

This project helps a team decide which data or AI ideas are worth building.

Every idea gets scored on four things.

- Business impact
- Data availability
- Technical feasibility
- Cost and effort

Each idea gets a final score out of 5. The ideas are then ranked from strongest to weakest. This helps a team focus on the best ideas first and drop the weak ones early.

## How it works

1. Use cases are listed in `data/use_cases.csv`. Each row is one idea with raw scores from 1 to 5 for different sub questions.
2. `scoring.py` holds the scoring rules. It averages sub scores into four category scores, then combines them using weights into one final score.
3. `main.py` loads the data, scores every use case, ranks them, and saves the result to `output/prioritized_report.csv`. It also prints a summary in the terminal.

## How to run it

```
python main.py
```

## How to use it with your own ideas

Open `data/use_cases.csv` and add a new row for each idea. Fill in a score from 1 to 5 for each column. Then run the script again.

## Scoring weights

- Business impact: 35 percent
- Data availability: 25 percent
- Technical feasibility: 25 percent
- Cost and effort: 15 percent

These weights can be changed in `scoring.py` if a team wants to value one category more than another.
