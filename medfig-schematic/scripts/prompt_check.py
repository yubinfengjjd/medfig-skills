"""Check an image-generation prompt for a schematic against its ``schematic.yaml`` before it is sent.

Checks (references/prompt_patterns.md):
  - every quoted string ("..." or “...”) is a spec label (or listed in ignore_quotes); a label that is not in the
    spec is text the figure must not contain
  - every #RRGGBB colour is in the spec palette
  - no forbidden pattern (internal codes), no development-history word, no banned claim word in quoted labels
  - numbers in quoted labels are design numbers (allowed_numbers)
  - the prompt is English (no CJK characters: the explanation for the user goes outside the prompt)
  - image slots are declared empty when they are mentioned
  - full mode: size / aspect stated, a TEXT RULES block, "no logos / watermarks", every spec label used (WARN)
  - edit mode: a "keep everything else" clause, at most MAX_EDITS numbered changes (WARN above)
  - "add an arrow" without a route (from / to / into) (WARN: give the exact path)

Usage: python prompt_check.py prompt.txt --spec schematic.yaml [--mode full|edit]
Exit 1 when any ERROR is found. Only reads.
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schematic_spec  # noqa: E402

LIB = HERE.parents[1] / "medfig-render" / "lib"   # source checkout and installed skills share this layout
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))
try:
    from figkit import qa  # noqa: E402
except Exception:  # figkit missing: skip the shared word lists, keep the spec checks
    qa = None

MAX_EDITS = 6
QUOTE = re.compile(r'"([^"\n]+)"|“([^”\n]+)”')
CJK = re.compile(r"[　-〿㐀-䶿一-鿿＀-￯]")
KEEP = re.compile(r"\bkeep (?:everything|all) else\b|\bkeep\b[^.\n]*\bexactly as (?:it is|they are)\b"
                  r"|\bdo not change\b|\bonly (?:make|change|redraw)\b", re.I)
EMPTY = re.compile(r"\bempty\b|\bdraw nothing inside\b|\bno (?:image|retina|scan) content\b", re.I)
EDIT_ITEM = re.compile(r"^\s*\d+\.\s", re.M)
SENTENCE = re.compile(r"[^.\n]*\barrow\b[^.\n]*", re.I)
ADD_ARROW = re.compile(r"\b(?:add|draw|put)\b[^.\n]*\barrow\b", re.I)
ROUTE = re.compile(r"\bfrom\b[^.\n]*\b(?:to|into|towards?)\b|\brouted?\b|\bpath\b", re.I)


def quoted(prompt):
    return [a or b for a, b in QUOTE.findall(prompt)]


def check(prompt, spec, mode="full"):
    """[(level, message)] for one prompt."""
    out = []
    labels = set(spec["labels_flat"])
    ignore = set(spec["ignore_quotes"])
    allowed_n = set(spec["allowed_numbers"])

    if CJK.search(prompt):
        out.append(("ERROR", "prompt contains CJK characters: write the prompt in English, "
                             "the Chinese explanation goes outside the prompt"))

    used = set()
    for q in quoted(prompt):
        q = q.strip()
        if q in ignore:
            continue
        if q in labels:
            used.add(q)
        else:
            out.append(("ERROR", f'quoted text "{q}" is not a spec label (add it to labels, or to ignore_quotes '
                                 "if it is not figure text)"))
        bad = [n for n in schematic_spec.label_numbers(q) if n not in allowed_n]
        if bad:
            out.append(("ERROR", f'"{q}": numbers {bad} are not design numbers (allowed_numbers)'))
        if qa is not None:
            for w in qa.banned_in_text(q):
                out.append(("ERROR", f'"{q}": banned word {w!r}'))
            for k in qa.dev_history_in_text(q):
                out.append(("ERROR", f'"{q}": development-history word ({k})'))

    for hx in sorted(set(h.upper() for h in schematic_spec.HEX.findall(prompt))):
        if hx not in spec["colours"]:
            out.append(("ERROR", f"colour {hx} is not in the spec palette"))

    for p in spec["forbidden_patterns"]:
        m = re.search(p, prompt)
        if m:
            out.append(("ERROR", f"forbidden pattern {p!r} found: {m.group(0)!r}"))

    if any(s in prompt for s in spec["image_slots"]) or re.search(r"\bimage slots?\b", prompt, re.I):
        if not EMPTY.search(prompt):
            out.append(("ERROR", "image slots are mentioned but never declared empty "
                                 "(say: empty light-grey rectangle, dashed border, draw nothing inside)"))

    for sent in SENTENCE.findall(prompt):
        if ADD_ARROW.search(sent) and not ROUTE.search(sent):
            out.append(("WARN", f"arrow without a route: {sent.strip()[:90]!r} -- name where it starts, "
                                "where it goes around and where it ends"))

    if mode == "full":
        if not re.search(r"\b\d+\s*mm\b", prompt) or not re.search(r"\b\d+(?:\.\d+)?\s*:\s*\d+\b", prompt):
            out.append(("ERROR", "full prompt must state the size in mm and the aspect ratio (e.g. 180 mm, 3:2)"))
        if not re.search(r"\btext rules\b", prompt, re.I):
            out.append(("ERROR", "full prompt needs a TEXT RULES block (only the given labels, no title, spelling)"))
        if not re.search(r"\bno logos?\b", prompt, re.I) or not re.search(r"\bwatermarks?\b", prompt, re.I):
            out.append(("WARN", "say 'no logos, no watermarks'"))
        missing = [lab for lab in spec["labels_flat"] if lab not in used]
        if missing:
            out.append(("WARN", f"{len(missing)} spec labels are not quoted in the prompt "
                                f"(fine only when an uploaded draft carries them): {missing[:8]}"))
    else:
        if not KEEP.search(prompt):
            out.append(("ERROR", "edit prompt must say what stays: 'Keep everything else exactly as it is. "
                                 "Only make these changes:'"))
        n = len(EDIT_ITEM.findall(prompt))
        if n > MAX_EDITS:
            out.append(("WARN", f"{n} numbered changes in one edit (> {MAX_EDITS}): the layout tends to drift; "
                                "split into two rounds"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("prompt")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--mode", choices=("full", "edit"), default="full")
    a = ap.parse_args(argv)
    spec = schematic_spec.load(a.spec)
    issues = schematic_spec.self_check(spec)
    issues += check(Path(a.prompt).read_text(encoding="utf-8"), spec, a.mode)
    for level, msg in issues:
        print(f"{level}: {msg}")
    n_err = sum(1 for lv, _ in issues if lv == "ERROR")
    n_warn = len(issues) - n_err
    print(f"prompt_check: {n_err} error(s), {n_warn} warning(s)")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
