"""Render only two polish audit records, offline, without rerunning editing/checks.

Crosscheck judgments are immutable inputs. An agent-reviewed presentation triage
separates author questions from coverage gaps; the renderer never guesses this
semantic distinction. See references/polish-rules.md for the triage schema.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re

NAMES = ('作者裁决清单.md', '附录_交叉核对审计.md')
RESULTS = ('一致', '差异有据', '来源待查', '未执行')


def clean(value):
    return re.sub(r'\s+', ' ', re.sub(r'<br\s*/?>', ' ', str(value), flags=re.I)).strip()


def cell(value, limit=2400):
    text = clean(value)
    if len(text) > limit:
        text = text[:limit].rstrip() + '…'
    return text.replace('|', '&#124;')


def blocks(text):
    # Same one-based block convention as build_manuscript, without DOCX imports.
    out, buf = [], []
    for line in text.splitlines():
        if not line.strip() or re.match(r'^#{1,6}\s|^[-*]\s', line):
            if buf:
                out.append(' '.join(buf)); buf = []
            if line.strip():
                out.append(line.strip())
        else:
            buf.append(line.strip())
    if buf:
        out.append(' '.join(buf))
    return out


def sentences(text):
    """Keep decimals, figure references and parenthesized expressions intact."""
    text = clean(text)
    out, start, depth = [], 0, 0
    for i, char in enumerate(text):
        if char in '([':
            depth += 1
        elif char in ')]':
            depth = max(0, depth - 1)
        if char not in '.!?' or depth or (i+1 < len(text) and not text[i+1].isspace()):
            continue
        if re.search(r'\b(?:Fig|Figs|Eq|Eqs|Table|Tables|Dr|Mr|Ms|Prof|vs|al|No|e\.g|i\.e)\.$', text[:i+1], re.I):
            continue
        # The full preceding sentence, including the terminal punctuation.
        out.append(text[start:i+1].strip())
        start = i + 1
    if text[start:].strip():
        out.append(text[start:].strip())
    return out


def original_unit(row, raw):
    key = row['unit_key']
    if isinstance(key, str) and key.startswith('c'):
        # A caption is the entire semantic unit, even for numeric audit rows.
        label = key[1:].upper()
        pattern = re.compile(r'^\s*(?:#{1,6}\s*)?\*\*(?:Supplementary\s+)?(?:Figure|Table)\s+(S?\d+)\.', re.M | re.I)
        hits = list(pattern.finditer(raw))
        for i, hit in enumerate(hits):
            if hit[1].upper() == label:
                return clean(raw[hit.start():hits[i+1].start() if i+1 < len(hits) else len(raw)])
        raise ValueError(f"Caption boundary not found: {row['file']} {key}")
    if not isinstance(key, int) or key < 1:
        raise ValueError(f'Invalid block key: {key}')
    unit = blocks(raw)[key-1]
    if row['type'] != '数字':
        return clean(unit)
    # Recover each legacy slice from its containing complete sentence. If a
    # slice cannot be mapped safely, show the complete block, never a fragment.
    full = sentences(unit)
    selected = [clean(s) for s in row.get('original_sentences', []) if clean(s)]
    if not selected or any(not any(s in f or f in s for f in full) for s in selected):
        return clean(unit)
    return ' '.join(f for f in full if any(s in f or f in s for s in selected))


def safe_child(base, relative):
    relative = str(relative).replace('\\', '/')
    path = (base/relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f'Path escapes input tree: {relative}')
    return path


def triage_rows(rows, plan):
    ids = [row['id'] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate crosscheck IDs')
    items = plan.get('items', {})
    pending = {row['id'] for row in rows if row['result'] == '来源待查'}
    if set(items) != pending:
        raise ValueError(f'Presentation triage must cover exactly 来源待查 IDs: missing={sorted(pending-set(items))}, extra={sorted(set(items)-pending)}')
    for row in rows:
        if row['result'] not in RESULTS:
            raise ValueError(f"Unknown judgment: {row['result']}")
    for key, item in items.items():
        kind = item.get('kind')
        if kind not in ('coverage_gap', 'inherited', 'author_action') or not item.get('gap'):
            raise ValueError(f'Invalid presentation triage for {key}')
        if kind == 'author_action' and not all(item.get(k) for k in ('group', 'question', 'conservative', 'needed')):
            raise ValueError(f'Incomplete author action: {key}')
        if kind == 'inherited' and not item.get('reference'):
            raise ValueError(f'Inherited item needs an existing reference: {key}')
    return items


def inherited_text(old, plan):
    if not old:
        return plan.get('inherited_markdown', '既有未决事项：无；未自动关闭任何事项。')
    match = re.search(r'^## (?:§1[.：\s]*)?沿用既有未决事项\s*$', old, re.M)
    if not match:
        raise ValueError('Cannot identify inherited section; supply a reviewed list for a new project, do not discard an existing list')
    start = match.end()
    stop = re.search(r'^## (?:本轮来源待查|§2[^\n]*)\s*$', old[start:], re.M)
    if not stop:
        raise ValueError('Cannot identify end of inherited section')
    text = old[start:start+stop.start()].strip('\n')
    extra = re.search(r'^## 其他裁决与交付限制\s*\n', old, re.M)
    if extra:
        text += '\n\n### 沿用其他裁决与交付限制\n\n' + old[extra.end():].strip('\n')
    return text


def render_records(process, plan):
    process = Path(process)
    cross_path = process/'crosscheck.json'
    if plan.get('crosscheck_sha256') != hashlib.sha256(cross_path.read_bytes()).hexdigest():
        raise ValueError('Presentation triage crosscheck_sha256 does not match the input')
    rows = json.loads(cross_path.read_text(encoding='utf-8'))
    items = triage_rows(rows, plan)
    old_path = process/NAMES[0]
    old = old_path.read_text(encoding='utf-8') if old_path.exists() else ''
    inherited = inherited_text(old, plan)
    # Existing conflicts remain unresolved and are referenced rather than added
    # again as new questions. Validate every reference against the retained text.
    for key, item in items.items():
        if item['kind'] == 'inherited' and item['reference'] not in inherited:
            raise ValueError(f'Inherited reference absent from §1: {key} {item["reference"]}')
    counts = Counter(row['result'] for row in rows)
    actions = defaultdict(list)
    gaps = defaultdict(list)
    originals = {}
    for row in rows:
        original = safe_child(process/'before', row['file'])
        originals[row['id']] = original_unit(row, original.read_text(encoding='utf-8-sig'))
        if row['id'] in items:
            item = items[row['id']]
            gaps[(row['file'], row['type'], item['gap'], item['kind'])].append(row['id'])
            if item['kind'] == 'author_action':
                actions[item['group']].append(row)
    lines = ['# 作者裁决清单', '', '状态：保留既有未决事项；本记录不表示作者已决定，不改变交叉核对判定或稿件。', '',
             '## §1 沿用既有未决事项', '', inherited, '', '## §2 本轮需作者动作', '',
             f'本轮需作者动作：{len(actions)} 组。既有事项见 §1；单一材料出现或未逐项复述本身不产生作者问题。', '']
    for group, group_rows in sorted(actions.items()):
        specs = [items[r['id']] for r in group_rows]
        first = specs[0]
        if any(any(s[k] != first[k] for k in ('question', 'conservative', 'needed')) for s in specs):
            raise ValueError(f'Conflicting action descriptions for group {group}')
        lines += [f'### {clean(group)}', '', f"问题：{clean(first['question'])}", '',
                  '涉及文件/单元 ID：' + '；'.join(f"{file}：{', '.join(r['id'] for r in group_rows if r['file']==file)}" for file in sorted({r['file'] for r in group_rows})) + '。', '',
                  f"保守处理：{clean(first['conservative'])}", '', f"所需证据或决定：{clean(first['needed'])}", '']
    presentation_counts = Counter(item['kind'] for item in items.values())
    lines += ['## §3 附录与审计计数', '',
              f"完整 {len(rows)} 单元见 [附录_交叉核对审计.md](附录_交叉核对审计.md)；" + '、'.join(f'{k} {counts[k]}' for k in RESULTS) + '。', '',
              f"来源待查 {counts['来源待查']} 条中：结构性覆盖缺口 {presentation_counts['coverage_gap']} 条、沿用既有事项 {presentation_counts['inherited']} 条、本轮动作关联 {presentation_counts['author_action']} 条（{len(actions)} 组）。**计数≠问题数**：限定/数字 ID 可指同一科学单元，不能当作独立问题或研究错误。", '',
              '“材料未逐项复述”属于材料结构造成的记录覆盖缺口，不据此认定稿件问题；原判定仍为来源待查、无法证明缺失。“文件 × 类型 × 共同证据缺口”的分组统计及完整 ID 表均见附录。', '']
    grouped = ['## 来源待查分组统计', '', '| 文件 | 类型 | 共同证据缺口 | 审计 ID 数 | 呈现去向 |', '|---|---|---|---:|---|']
    destinations = {'coverage_gap': '附录；结构性覆盖缺口', 'inherited': '§1；沿用既有事项', 'author_action': '§2；作者动作'}
    for (file, kind, gap, destination), ids in sorted(gaps.items()):
        grouped.append('| ' + ' | '.join((cell(file), cell(kind), cell(gap), str(len(ids)), destinations[destination])) + ' |')
    appendix = ['# 附录：交叉核对审计', '',
                '判定口径：**一致**＝所查材料在同一分析语境相容，仅证明跨文档相容；**差异有据**＝显示、精度或分析口径差异有可追溯依据，不授权改事实；**来源待查**＝证据不足、未覆盖或存在待核实冲突，无法证明缺失，保留原文；**未执行**＝未完成核对，不能计作一致。判定沿用输入，不因呈现分组重新判定。', '',
                f'完整保留 {len(rows)} 个唯一 ID。图/表注从标题起至下一标题或文件末整体取文；正文数字按所属完整句取文，无法安全匹配旧切片时保守展示整个单元。换行合为空格，超长显示用“…”标记；全文及原证据见同目录 crosscheck.json 和 before/。原文取自 before/，不是候选稿。', '',
                '**计数≠问题数**。下表按文件、限定/数字类型和共同证据缺口分组；结构性记录缺口不据此认定稿件问题，既有事项与需作者动作项分别指回清单 §1/§2。', '',
                *grouped, '', '## 完整审计表', '',
                '| ID | 文件 | 单元（原文） | 判定 | 证据摘要 | 保守处理 |', '|---|---|---|---|---|---|']
    for row in rows:
        item = items.get(row['id'])
        evidence = [row.get('basis', '')]
        evidence += [f"{e['file']}:{e.get('line', '—')}：{e.get('quote', '')}" for e in row.get('evidence', [])]
        action = row.get('conservative_action', '保留原文，不自动修改。')
        if item:
            action += ' 呈现：' + destinations[item['kind']] + '；' + item['gap']
        label = f"{row['unit_key']}（{row['type']}）；原文：" + originals[row['id']]
        appendix.append('| ' + ' | '.join((cell(row['id']), cell(row['file']), cell(label), cell(row['result']), cell('；'.join(evidence), 1800), cell(action))) + ' |')
    return {NAMES[0]: '\n'.join(lines)+'\n', NAMES[1]: '\n'.join(appendix)+'\n'}


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def replace_records(root, process, output, archive_date):
    root, process = Path(root).resolve(), Path(process).resolve()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', archive_date):
        raise ValueError('Archive date must be YYYY-MM-DD')
    if process.parent != root/'_process/Finalize' or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_polish_v\d+', process.name):
        raise ValueError('Expected a project _process/Finalize/<date>_polish_v<N> directory')
    if set(output) != set(NAMES):
        raise ValueError('Only the two audit records may be replaced')
    if any((process/(name+'.tmp')).exists() for name in NAMES):
        raise ValueError('Temporary record file already exists; no files changed')
    before = snapshot(root)
    updates, archives = {}, {}
    for name in NAMES:
        dst = safe_child(process, name)
        content = output[name].encode('utf-8')
        previous = dst.read_bytes() if dst.exists() else None
        if previous == content:
            continue
        updates[dst] = (previous, content)
        if previous is not None:
            archived = safe_child(root/'_archive'/archive_date, dst.relative_to(root))
            if archived.exists() and archived.read_bytes() != previous:
                raise ValueError(f'Archive collision; no files changed: {archived}')
            archives[archived] = previous
    # Preflight all collisions, archive exact bytes, then replace only records.
    for archived, data in archives.items():
        archived.parent.mkdir(parents=True, exist_ok=True)
        if not archived.exists():
            with archived.open('xb') as handle:
                handle.write(data)
        if archived.read_bytes() != data:
            raise OSError(f'Archive verification failed: {archived}')
    try:
        for dst, (_, data) in updates.items():
            temp = dst.with_name(dst.name+'.tmp')
            with temp.open('xb') as handle:
                handle.write(data)
            os.replace(temp, dst)
    except BaseException:
        for dst, (previous, _) in updates.items():
            temp = dst.with_name(dst.name+'.tmp')
            if temp.exists():
                temp.unlink()
            if previous is None:
                dst.unlink(missing_ok=True)
            else:
                dst.write_bytes(previous)
        raise
    after = snapshot(root)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    allowed = {p.relative_to(root).as_posix() for p in (*updates, *archives)}
    if set(changed) - allowed:
        raise RuntimeError(f'Unexpected external changes during regeneration: {sorted(set(changed)-allowed)}')
    return {'record_changes': [p.relative_to(root).as_posix() for p in updates],
            'archive_files': [p.relative_to(root).as_posix() for p in archives],
            'all_changed_files': changed, '04_manuscript_unchanged': True, '05_final_unchanged': True,
            'sha256_records': {name: after[(process/name).relative_to(root).as_posix()] for name in NAMES}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--process-dir', required=True, type=Path)
    parser.add_argument('--triage-json', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preview-dir', type=Path, help='Write the two records to a separate development directory')
    mode.add_argument('--write', action='store_true', help='Archive and replace only the two process records')
    parser.add_argument('--project-root', type=Path)
    parser.add_argument('--archive-date', default=date.today().isoformat())
    args = parser.parse_args()
    plan = json.loads(args.triage_json.read_text(encoding='utf-8'))
    output = render_records(args.process_dir, plan)
    if args.preview_dir:
        preview = args.preview_dir.resolve()
        source = args.process_dir.resolve()
        if preview == source or preview.is_relative_to(source) or source.is_relative_to(preview):
            parser.error('Preview must be separate from the source process directory')
        preview.mkdir(parents=True, exist_ok=True)
        for name, text in output.items():
            (preview/name).write_bytes(text.encode('utf-8'))
        print(json.dumps({'preview': str(preview), 'files': list(output)}, ensure_ascii=False))
    else:
        if not args.project_root:
            parser.error('--write requires --project-root')
        print(json.dumps(replace_records(args.project_root, args.process_dir, output, args.archive_date), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
