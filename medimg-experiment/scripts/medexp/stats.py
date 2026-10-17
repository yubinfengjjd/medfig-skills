"""Case-level evidence and paired bootstrap. Standard library only."""
import json
import math
import random
import statistics
from .common import require, number, safe_path


def read_cases(path, statistic):
    path = safe_path(path)
    require(path.is_file(), '缺少逐病例记录cases.jsonl')
    cases = {}
    raw = path.read_bytes()
    require(not raw or raw.endswith(b'\n'), 'cases.jsonl末行不完整')
    for line in raw.decode('utf-8').splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        cid = e.get('case_id')
        require(isinstance(cid, str) and cid, '逐病例记录缺少case_id')
        require(cid not in cases, '逐病例记录case_id重复: ' + cid)
        if statistic == 'mean_per_case':
            cases[cid] = number(e.get('value'), '逐病例指标值')
        else:
            require(e.get('label') in (0, 1), 'binary_auroc逐病例记录label必须为0/1')
            cases[cid] = (e['label'], number(e.get('score'), '逐病例score'))
    require(cases, '逐病例记录为空')
    return cases


def auroc(pairs):
    # Mann-Whitney with average ranks for ties.
    ordered = sorted(pairs, key=lambda x: x[1])
    ranks = [0.0] * len(ordered)
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][1] == ordered[i][1]:
            j += 1
        for k in range(i, j + 1):
            ranks[k] = (i + j) / 2 + 1
        i = j + 1
    pos = sum(1 for label, _ in ordered if label == 1)
    neg = len(ordered) - pos
    if pos == 0 or neg == 0:
        return None
    rank_sum = sum(r for r, (label, _) in zip(ranks, ordered) if label == 1)
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)


def compute(statistic, cases, ids):
    if statistic == 'mean_per_case':
        return statistics.fmean(cases[i] for i in ids)
    return auroc([cases[i] for i in ids])


def check_consistency(statistic, cases, value):
    full = compute(statistic, cases, list(cases))
    require(full is not None, '逐病例记录无法计算主要指标（单一类别）')
    require(math.isclose(full, value, rel_tol=1e-6, abs_tol=1e-9),
            f'逐病例记录复算主要指标={full}，与报告值{value}不一致')


def aggregate(mode, values, higher):
    if mode == 'mean':
        return statistics.fmean(values)
    if mode == 'median':
        return statistics.median(values)
    return min(values) if higher else max(values)


def paired_bootstrap(statistic, runs_a, runs_b, higher, mode, resamples, level, seed):
    """runs_* are per-seed case dicts. Effect = A better than B (direction-adjusted)."""
    ids = sorted(runs_a[0])
    for r in runs_a + runs_b:
        require(sorted(r) == ids, '配对比较要求所有运行使用同一组病例')
    if statistic == 'binary_auroc':
        for r in runs_a + runs_b:
            require(all(r[i][0] == runs_a[0][i][0] for i in ids), '配对比较的病例标签不一致')

    def effect(sample):
        a = aggregate(mode, [compute(statistic, r, sample) for r in runs_a], higher)
        b = aggregate(mode, [compute(statistic, r, sample) for r in runs_b], higher)
        if a is None or b is None:
            return None
        return (a - b) if higher else (b - a)

    point = effect(ids)
    require(point is not None, '完整病例集无法计算配对效应')
    rng = random.Random(seed)
    draws, skipped = [], 0
    for _ in range(resamples):
        sample = [ids[rng.randrange(len(ids))] for _ in ids]
        e = effect(sample)
        if e is None:
            skipped += 1
        else:
            draws.append(e)
    require(skipped <= resamples * 0.1, 'bootstrap重采样中单一类别过多，病例数不足以估计区间')
    draws.sort()
    alpha = (1 - level) / 2
    lo = draws[max(0, math.floor(alpha * len(draws)))]
    hi = draws[min(len(draws) - 1, math.ceil((1 - alpha) * len(draws)) - 1)]
    return {'effect': point, 'ci_low': lo, 'ci_high': hi, 'level': level, 'cases': len(ids),
            'resamples': resamples, 'skipped_resamples': skipped, 'seeds_a': len(runs_a), 'seeds_b': len(runs_b),
            'method': 'paired case-level percentile bootstrap; per-seed statistic aggregated by contract rule'}


def seed_sd(values):
    return statistics.stdev(values) if len(values) >= 2 else 0.0
