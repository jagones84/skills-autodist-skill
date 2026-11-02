#!/usr/bin/env python3
"""Analyze a CSV file and print a concise structured report.

Usage:
    analyze.py <csv_path> [--groupby COLUMN] [--value COLUMN]

Run with the dataviz venv python: /home/jagones/.venvs/dataviz/bin/python
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Parse args, load the CSV, print a compact analysis report."""
    parser = argparse.ArgumentParser(description="Concise CSV analysis report")
    parser.add_argument("csv", help="Path to the CSV file")
    parser.add_argument("--groupby", default=None, help="Categorical column to group by")
    parser.add_argument("--value", default=None, help="Numeric column to aggregate")
    args = parser.parse_args()

    import pandas as pd

    path = Path(args.csv)
    if not path.is_file():
        print(f"ERROR: file not found: {path}")
        return 1

    df = pd.read_csv(path)
    print(f"## Shape: {df.shape[0]} rows x {df.shape[1]} cols")
    print("\n## Columns & dtypes")
    print(df.dtypes.to_string())

    missing = df.isna().sum()
    if missing.any():
        print("\n## Missing values")
        print(missing[missing > 0].to_string())
    else:
        print("\n## Missing values: none")

    num = df.select_dtypes("number")
    if not num.empty:
        print("\n## Numeric describe")
        print(num.describe().round(2).to_string())

    if args.groupby and args.value:
        if args.groupby in df.columns and args.value in num.columns:
            print(f"\n## {args.value} by {args.groupby}")
            print(df.groupby(args.groupby)[args.value].agg(["count", "sum", "mean"]).round(2).to_string())
        else:
            print(f"\n## groupby: column not found ({args.groupby} / {args.value})")

    if num.shape[1] >= 2:
        corr = num.corr(numeric_only=True)
        pairs = (
            corr.where(~(corr.abs() > 0.999))
            .stack()
            .sort_values(ascending=False, key=abs)
            .head(3)
        )
        if not pairs.empty:
            print("\n## Top correlations")
            for (a, b), v in pairs.items():
                print(f"  {a} ~ {b}: {v:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
