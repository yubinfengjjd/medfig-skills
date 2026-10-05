"""Package one prompt round of a schematic: archive the previous output, extract the prompt, collect uploads.

Layout of the work directory (outside the project):
  schematic.yaml              the spec
  roundN.md                   evaluation of round N-1 + the prompt (one ```text block) + Chinese explanation
  roundN-1_output.png         the image the user got back last round (archived here by --prev-output)
  roundN_upload/prompt.txt    the prompt, ready to paste
  roundN_upload/<images>      what to upload with it (previous output as draft, style references)

Usage:
  python round_pack.py --dir <work> --round N [--prev-output <png>] [--upload <file> [--as <name>]] ...
                       [--spec schematic.yaml] [--mode auto|full|edit]
The prompt is checked with prompt_check (spec defaults to <work>/schematic.yaml when present); exit 1 on errors,
in which case prompt.txt is still written so it can be inspected, but the round is reported as not ready.
Never deletes anything; an existing upload file with the same name is replaced only by --force.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prompt_check  # noqa: E402
import schematic_spec  # noqa: E402

BLOCK = re.compile(r"```text\n(.*?)```", re.S)


def extract_prompt(md_text):
    blocks = BLOCK.findall(md_text)
    if len(blocks) != 1:
        raise SystemExit(f"round file must contain exactly one ```text block, found {len(blocks)}")
    return blocks[0].strip() + "\n"


def detect_mode(prompt):
    return "edit" if prompt_check.KEEP.search(prompt) else "full"


def pack(work, n, prev_output=None, uploads=(), spec_path=None, mode="auto", force=False):
    """Return (ready, lines). ``uploads`` = [(src, name_or_None)]."""
    work = Path(work)
    md = work / f"round{n}.md"
    if not md.is_file():
        raise SystemExit(f"{md} not found: write the round file first")
    lines = []
    if prev_output:
        src = Path(prev_output)
        if not src.is_file():
            raise SystemExit(f"previous output {src} not found")
        dst = work / f"round{n - 1}_output{src.suffix.lower()}"
        if dst.exists() and not force and dst.read_bytes() != src.read_bytes():
            raise SystemExit(f"{dst} exists with different content (use --force to replace)")
        shutil.copy2(src, dst)
        lines.append(f"archived previous output -> {dst.name}")
    up = work / f"round{n}_upload"
    up.mkdir(exist_ok=True)
    prompt = extract_prompt(md.read_text(encoding="utf-8"))
    (up / "prompt.txt").write_text(prompt, encoding="utf-8")
    for src, name in uploads:
        src = Path(src)
        if not src.is_file():
            raise SystemExit(f"upload {src} not found")
        dst = up / (name or src.name)
        if dst.exists() and not force and dst.read_bytes() != src.read_bytes():
            raise SystemExit(f"{dst} exists with different content (use --force to replace)")
        shutil.copy2(src, dst)
    m = detect_mode(prompt) if mode == "auto" else mode
    ready = True
    spec_path = Path(spec_path) if spec_path else work / "schematic.yaml"
    if spec_path.is_file():
        spec = schematic_spec.load(spec_path)
        issues = schematic_spec.self_check(spec) + prompt_check.check(prompt, spec, m)
        for level, msg in issues:
            lines.append(f"{level}: {msg}")
        n_err = sum(1 for lv, _ in issues if lv == "ERROR")
        lines.append(f"prompt_check ({m}): {n_err} error(s), {len(issues) - n_err} warning(s)")
        ready = n_err == 0
    else:
        lines.append(f"WARN: no spec at {spec_path}; prompt not checked")
    files = sorted(p.name for p in up.iterdir() if p.is_file())
    images = [f for f in files if f != "prompt.txt"]
    lines.append(f"{up.name}/: upload {images or 'nothing'} first, then paste prompt.txt "
                 f"({len(prompt)} chars, {m} mode{': same chat' if m == 'edit' else ': new chat'})")
    lines.append("ready" if ready else "NOT ready: fix the errors in the round file and pack again")
    return ready, lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True)
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--prev-output")
    ap.add_argument("--upload", action="append", default=[])
    ap.add_argument("--as", dest="as_", action="append", default=[],
                    help="new file name for the --upload at the same position")
    ap.add_argument("--spec")
    ap.add_argument("--mode", choices=("auto", "full", "edit"), default="auto")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    if len(a.as_) > len(a.upload):
        ap.error("more --as than --upload")
    names = a.as_ + [None] * (len(a.upload) - len(a.as_))
    ready, lines = pack(a.dir, a.round, a.prev_output, list(zip(a.upload, names)), a.spec, a.mode, a.force)
    print("\n".join(lines))
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
