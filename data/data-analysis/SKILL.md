---
name: data-analysis
description: "Structured data analysis of CSV/Excel files using pandas in a dedicated venv. Use when the user asks to analyze a dataset: statistics, missing values, distributions, correlations, aggregations. Outputs a concise text report."
---

# Data Analysis (pandas venv)

Analyze tabular datasets (CSV) with pandas installed in the dedicated venv `/home/jagones/.venvs/dataviz`.

## Usage

1. Run the bundled script (does NOT modify the source file):

```bash
/home/jagones/.venvs/dataviz/bin/python \
  /home/jagones/.openclaw/workspace/skills/data-analysis/scripts/analyze.py \
  <path-to-csv> [--groupby column] [--value column]
```

2. The script prints: shape, columns+dtypes, missing values, numeric describe, groupby aggregation (optional), top pairwise correlations.
3. For custom questions, run ad-hoc pandas snippets with the same venv python — never install packages into the system python.

## Requirements

- venv at `/home/jagones/.venvs/dataviz` (pandas, numpy, matplotlib, seaborn)
- For charts, pair this skill with `python-dataviz` (same venv).
