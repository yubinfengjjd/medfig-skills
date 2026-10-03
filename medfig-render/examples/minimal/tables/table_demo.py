"""Minimal table: per-subgroup estimate with 95% interval and per-class counts, as CSV + Markdown with
a provenance record. Outputs: <out_dir>/tables/table_demo.{csv,md} and table_demo.source.json.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
import _figkit_path  # noqa: E402,F401  (importable -> $FIGKIT_LIB -> repo lib -> installed skill)

import pandas as pd  # noqa: E402

from figkit import config, io, qa  # noqa: E402
from figkit.provenance import Provenance  # noqa: E402

NAME = "table_demo"


def _fmt(v):
    """Three decimals with a true minus sign (U+2212)."""
    return f"{v:.3f}".replace("-", "−")


def build(cfg):
    prov = Provenance(NAME)
    rd = io.Reader(prov, cfg)
    iv = rd.csv("intervals.csv")
    cc = rd.csv("confusion.csv")
    n_by_class = cc.groupby("truth", sort=False)["count"].sum()
    tab = pd.DataFrame({
        "Subgroup": iv["label"],
        "Estimate": iv["est"].map(_fmt),
        "95% CI": [f"{_fmt(lo)} to {_fmt(hi)}" for lo, hi in zip(iv["lo"], iv["hi"])],
    })
    prov.add_transform("intervals.csv -> Estimate / 95% CI formatted to 3 decimals")
    prov.set("n_rows", len(tab))
    # n per class comes from the data, never typed by hand; zero-count classes are reported as absent
    prov.set("n_by_class", {k: int(v) for k, v in n_by_class.items()})
    prov.set("absent_classes", [k for k, v in n_by_class.items() if v == 0])
    note = ("Estimates are balanced accuracy on synthetic data. Classes without cases: "
            + (", ".join(prov.values["absent_classes"]) or "none") + ".")
    return tab, note, prov


def _markdown(tab, note):
    head = "| " + " | ".join(tab.columns) + " |"
    sep = "|" + "|".join("---" for _ in tab.columns) + "|"
    body = ["| " + " | ".join(str(v) for v in r) + " |" for r in tab.itertuples(index=False)]
    return "\n".join([head, sep, *body, "", note, ""])


def main():
    cfg = config.load(PROJECT / "figkit.toml")
    tab, note, prov = build(cfg)
    md = _markdown(tab, note)
    banned = qa.banned_in_text(md)
    if banned:
        raise RuntimeError(f"{NAME}: banned words {banned}")
    out = Path(cfg.out_dir) / "tables"
    out.mkdir(parents=True, exist_ok=True)
    csv = out / f"{NAME}.csv"
    tab.to_csv(csv, index=False, encoding="utf-8")
    (out / f"{NAME}.md").write_text(md, encoding="utf-8")
    prov.set("outputs", [csv.name, f"{NAME}.md"])
    return {"csv": csv, "md": out / f"{NAME}.md", "source": prov.write(out)}


if __name__ == "__main__":
    print(main()["source"])
