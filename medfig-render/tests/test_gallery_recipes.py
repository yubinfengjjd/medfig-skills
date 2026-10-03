"""Every panel-gallery recipe builds and exports with all QA gates empty (synthetic data, temp copy);
INDEX.md is generated from the recipes' RECIPE metadata; planning docs only cite recipes / functions that exist."""
import importlib
import importlib.util
import re
import runpy
import shutil
import sys
from pathlib import Path

import pytest

from conftest import needs_scipilot

GALLERY = Path(__file__).resolve().parents[1] / "examples" / "gallery"
ROOT = GALLERY.parents[2]
RECIPES = sorted(p.stem for p in GALLERY.glob("*.py") if not p.stem.startswith("_"))


def _meta():
    spec = importlib.util.spec_from_file_location("gallery_meta", GALLERY / "_meta.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_index_is_generated_from_recipe_metadata():
    """INDEX.md == _meta.render(): one source of truth (run `python _meta.py` after editing a RECIPE)."""
    m = _meta()
    assert set(m.recipes()) == set(RECIPES)
    assert (GALLERY / "INDEX.md").read_text(encoding="utf-8") == m.render(), "INDEX.md is stale: run _meta.py"


def test_recipe_functions_exist():
    import figkit
    for name, meta in _meta().recipes().items():
        for path in meta["functions"]:
            mod, fn = path.rsplit(".", 1)
            module = importlib.import_module(f"figkit.{mod}" if mod in ("stats", "layout", "style", "qa", "journals")
                                             else f"figkit.panels.{mod}")
            assert callable(getattr(module, fn, None)), f"{name}: {path} not found in {figkit.__file__}"


def test_chart_diversity_points_to_real_recipes_and_functions():
    """Every `name.py` / `module.function` the planning guide cites must exist (no dangling references)."""
    text = (ROOT / "medfig-plan" / "references" / "chart_diversity.md").read_text(encoding="utf-8")
    cited = set(re.findall(r"`([a-z_]+)\.py`", text))
    assert cited and not cited - set(RECIPES), cited - set(RECIPES)
    for mod, fn in re.findall(r"`([a-z]+)\.([a-z_]+)`", text):
        if fn == "py":  # `recipe.py`, checked above
            continue
        top = mod in ("stats", "layout", "style", "qa", "journals")
        module = importlib.import_module(f"figkit.{mod}" if top else f"figkit.panels.{mod}")
        assert callable(getattr(module, fn, None)), f"chart_diversity cites missing {mod}.{fn}"


@needs_scipilot
@pytest.mark.parametrize("name", RECIPES)
def test_recipe_exports_clean(name, tmp_path, monkeypatch):
    proj = tmp_path / "gallery"
    shutil.copytree(GALLERY, proj, ignore=shutil.ignore_patterns("out", "__pycache__"))
    lib = str(GALLERY.parents[1] / "lib")
    monkeypatch.syspath_prepend(lib)
    monkeypatch.syspath_prepend(str(proj))
    monkeypatch.chdir(tmp_path)
    for m in [m for m in sys.modules if m in ("_common", "_figkit_path")]:
        monkeypatch.delitem(sys.modules, m)
    ns = runpy.run_path(str(proj / f"{name}.py"), run_name="recipe")
    mod = type(sys)("recipe_" + name)
    mod.__dict__.update(ns)
    # single-panel recipes define draw() and use _common.run(module); multi-cell recipes own run(cfg=None)
    res = ns["run"](mod) if "draw" in ns else ns["run"]()
    src = Path(res["source"])
    assert src.is_file() and src.parent.parent.parent == proj / "out"
    # export.save raises on any non-empty gate; the returned qa must still be empty (check_figure aside)
    assert all(not v for k, v in res["qa"].items() if k not in ("audit_layout", "check_figure")), res["qa"]
