"""Recipe: dense layered case matrix -- groups side by side; per group one representative overlay (a),
a 3 x 4 matrix of map tiles on ONE shared scale (b) and a row of zoomed raw crops (c).

Use when: the claim is about what the model attends to across many cases (>= 12 per group), not about
one hand-picked example. Cases come from stats.stratified_cases (fixed seed, misclassified cases
included, framed in the error colour); the selection record goes into provenance as case_selection and
the rule + seed into the caption. Tiles are exact-aspect crops (imaging.crop_window) centred on the map
mass, placed with imaging.case_tiles, so no tile is letterboxed (S1). Synthetic B-scans + 16 x 16 maps.
"""
from _common import TOML, config, export, plt, style

import numpy as np
import pandas as pd

NAME = "case_matrix"
RECIPE = dict(
    chart='分组分层病例矩阵（代表图 + 多病例热图矩阵 + 局部放大）',
    category='版式',
    use='按类别 / 队列对照展示模型关注区域，每组 ≥ 12 例，分层随机选例且含错例',
    data='每例原图 (H, W) + 低分辨率热图 / 概念图 + 真值 / 预测；先用 stratified_cases 选例',
    avoid='只有 1–4 个病例（改单病例影像 panel 并在图注说明）；各例热图不能共用一个色阶（量级不可比）',
    functions=['stats.stratified_cases', 'imaging.case_tiles', 'imaging.crop_window', 'imaging.concept_map'],
    tags=['case matrix', 'heatmap', 'CAM', 'gallery', '病例矩阵', '热图', '选例'],
    source='项目实战提炼（版式参考乳腺 MRI 生境热图 + 病理放大的多病例组图）',
)
GROUPS = ["Normal", "Edema", "Degeneration"]
GROUP_COLORS = ["#0072B2", "#009E73", "#CC79A7"]
ERROR = "#D55E00"
SEED = 7
SHAPE = (256, 512)


def _bscan(rng, lesion):
    """Synthetic layered B-scan in [0, 1] and a 16 x 16 map peaking near the lesion."""
    H, W = SHAPE
    y, x = np.indices(SHAPE)
    base = 0.45 * H + 18 * np.sin(x / W * np.pi * rng.uniform(1, 2) + rng.uniform(0, 3))
    img = np.zeros(SHAPE)
    for k, (off, amp) in enumerate([(0, .9), (14, .5), (34, .7), (60, .35)]):
        img += amp * np.exp(-((y - base - off) ** 2) / (2 * (3 + k) ** 2))
    cx, cy = rng.uniform(.25, .75) * W, rng.uniform(.4, .6) * H
    if lesion:
        img += .6 * np.exp(-(((x - cx) / 30) ** 2 + ((y - cy) / 14) ** 2))
    img = np.clip(img + rng.normal(0, .06, SHAPE), 0, 1)
    gy, gx = np.indices((16, 16))
    heat = np.exp(-(((gx - cx / W * 16) / 2.5) ** 2 + ((gy - cy / H * 16) / 2.5) ** 2))
    return img, heat * rng.uniform(.5, 1.0)


def _cases():
    rng = np.random.default_rng(0)
    rows = []
    for g, name in enumerate(GROUPS):
        for i in range(30):
            raw, heat = _bscan(rng, lesion=g > 0)
            rows.append(dict(case=f"{name[:2]}{i:02d}", group=name, correct=bool(rng.uniform() > .25),
                             raw=raw, heat=heat))
    return pd.DataFrame(rows)


def build(cfg=None):
    from figkit import panel, stats
    from figkit.panels import imaging
    from figkit.provenance import Provenance
    cfg = cfg or config.load(TOML)
    style.apply(cfg)
    prov = Provenance(NAME, cfg)
    sel, record = stats.stratified_cases(_cases(), "group", "correct", n_correct=9, n_error=3, seed=SEED,
                                         order="case", unique="case", pool="synthetic pool, 30 per group")
    sel = sel.sort_values(["group", "correct", "case"], key=lambda s: s.map(GROUPS.index)
                          if s.name == "group" else s)
    vmin, vmax = 0.0, float(np.max(np.stack(sel.heat.to_list())))  # ONE scale over every shown case
    size = (style.DOUBLE, 4.15)
    fig = plt.figure(figsize=size, layout="none")  # exact add_axes geometry
    fw, fh = size
    col_w, pad = 0.315, (1 - 3 * 0.315) / 4
    a_axes, b_axes, c_axes = [], [], []
    for g, name in enumerate(GROUPS):
        x0 = pad + g * (col_w + pad)
        cs = sel[sel.group == name]
        rep = cs[cs.correct].iloc[0]
        rep_h = col_w * fw * SHAPE[0] / SHAPE[1] / fh
        ax = fig.add_axes([x0, 0.93 - rep_h, col_w, rep_h])
        imaging.concept_map(ax, rep.raw, rep.heat, vmin, vmax)
        ax.set_title(name, color=GROUP_COLORS[g], fontweight="bold", pad=2)
        a_axes.append(ax)
        tiles = [dict(raw=r.raw, heat=r.heat, error=not r.correct, id=r.case) for r in cs.itertuples()]
        b_axes += imaging.case_tiles(fig, [x0, 0.30, col_w, 0.585 - rep_h + 0.04], tiles, vmin, vmax, ncols=4,
                                     error_color=ERROR)
        c_axes += imaging.case_tiles(fig, [x0, 0.125, col_w, 0.15], tiles[3:7], vmin, vmax, ncols=4,
                                     overlay=False, crop_frac=0.5)
    cax = fig.add_axes([0.35, 0.075, 0.30, 0.018])
    cb = fig.colorbar(b_axes[0]._anchor_mappable, cax=cax, orientation="horizontal")
    cb.set_label("Map value (shared scale)")
    panel.mark_panel(a_axes[0], "a", extra_axes=a_axes[1:])
    panel.mark_panel(b_axes[0], "b", extra_axes=b_axes[1:] + [cax])
    panel.mark_panel(c_axes[0], "c", extra_axes=c_axes[1:])
    prov.set("case_selection", record)
    prov.set("cases", [ax._anchor_case for ax in b_axes])
    prov.set("shared_scale", [vmin, vmax])
    return fig, prov, size


def run(cfg=None):
    cfg = cfg or config.load(TOML)
    fig, prov, size = build(cfg)
    res = export.save(fig, NAME, prov, kind="gallery", size=size, cfg=cfg)
    plt.close(fig)
    return res


if __name__ == "__main__":
    print(run()["source"])
