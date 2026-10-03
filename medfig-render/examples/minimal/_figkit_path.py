"""Make ``figkit`` importable for the example scripts, wherever this example folder was copied.

Order: already importable -> $FIGKIT_LIB -> repository-relative ``../../lib`` (when run inside the repo)
-> the installed skill ``~/.claude/skills/medfig-render/lib``.
"""
import importlib.util
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent


def ensure_figkit() -> None:
    if importlib.util.find_spec("figkit") is not None:
        return
    env = os.environ.get("FIGKIT_LIB")
    repo = PROJECT.parents[1] / "lib"
    if env:
        lib = Path(env).expanduser()
    elif (repo / "figkit").is_dir():
        lib = repo
    else:
        lib = Path("~/.claude/skills/medfig-render/lib").expanduser()
    sys.path.insert(0, str(lib))


ensure_figkit()
