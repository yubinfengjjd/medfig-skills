"""Data health report for the planning inventory: one markdown section per input table (CSV / TSV / parquet /
xlsx) with shape, per-column dtype / missing / unique, exact duplicate rows, constant columns and, with
``--group``, n per group. Plotting bad data neatly still produces bad science, so run this before choosing
charts (idea after myzhao0114-del/scientific-figure-skill, re-implemented; that repository has no licence).

Usage: python data_health.py data/a.csv data/b.parquet [--group site] [--out docs/_process/data_health.md]
Only reads; never modifies the inputs.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd


def read_table(path):
    p = Path(path)
    suf = p.suffix.lower()
    if suf in (".csv", ".txt"):
        return pd.read_csv(p)
    if suf == ".tsv":
        return pd.read_csv(p, sep="\t")
    if suf == ".parquet":
        return pd.read_parquet(p)
    if suf in (".xlsx", ".xls"):
        return pd.read_excel(p)
    if suf == ".jsonl":
        return pd.read_json(p, lines=True)
    raise ValueError(f"{p.name}: unsupported table format {suf!r}")


def health(df, name="table", group=None):
    """Findings dict + markdown lines for one table."""
    f = dict(name=name, rows=int(len(df)), cols=int(df.shape[1]),
             duplicate_rows=int(df.duplicated().sum()),
             constant_columns=[c for c in df.columns if df[c].nunique(dropna=False) <= 1],
             missing={c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()},
             groups=None, warnings=[])
    if group is not None:
        if group not in df.columns:
            f["warnings"].append(f"group column {group!r} not found")
        else:
            f["groups"] = {str(k): int(v) for k, v in df[group].value_counts(dropna=False).sort_index().items()}
            small = [k for k, v in f["groups"].items() if v < 5]
            if small:
                f["warnings"].append(f"groups with n < 5: {small} (draw points, not bars / boxes)")
    if f["duplicate_rows"]:
        f["warnings"].append(f"{f['duplicate_rows']} exact duplicate rows")
    if f["constant_columns"]:
        f["warnings"].append(f"constant columns: {f['constant_columns']}")
    lines = [f"## {name}", "", f"- rows: {f['rows']:,} · columns: {f['cols']}",
             f"- exact duplicate rows: {f['duplicate_rows']}", "",
             "| column | dtype | missing | missing % | unique |", "|---|---|---|---|---|"]
    for c in df.columns:
        miss = int(df[c].isna().sum())
        lines.append(f"| {c} | {df[c].dtype} | {miss} | {100 * miss / max(len(df), 1):.1f} | "
                     f"{df[c].nunique(dropna=True)} |")
    if f["groups"] is not None:
        lines += ["", f"n per `{group}`:", ""] + [f"- {k}: {v:,}" for k, v in f["groups"].items()]
    lines += [""] + ([f"**Warnings:** " + "; ".join(f["warnings"])] if f["warnings"] else ["No warnings."]) + [""]
    return f, lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tables", nargs="+")
    ap.add_argument("--group", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    out = ["# Data health report", ""]
    findings = []
    for t in a.tables:
        f, lines = health(read_table(t), name=Path(t).name, group=a.group)
        findings.append(f)
        out += lines
    text = "\n".join(out)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return findings


if __name__ == "__main__":
    main()
