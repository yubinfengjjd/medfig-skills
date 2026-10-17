"""Offline citation accounting; see references/citation-quotas.md.
Usage: python -X utf8 citation_stats.py PROJECT_ROOT [--json]
No network; audit statuses attest verification but cannot prove it.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

DEFAULTS = {'total': 55, 'Introduction': 20, 'Introduction_review': 10,
            'Discussion': 20, 'Methods': 15}
SECTIONS = ('Methods', 'Introduction', 'Discussion', 'Results', 'Abstract', 'Legends')
LABELS = {'total': r'目标文献总数', 'Introduction': r'Introduction(?!\s*综述层)',
          'Introduction_review': r'Introduction\s*综述层', 'Discussion': r'Discussion',
          'Methods': r'Methods'}
IDENTIFIER = re.compile(r'\b(PMID|DOI|URL|arXiv)\s*[:：]\s*'
                       r'(https?://[^\s;；，]+|10\.\d{4,9}/[^\s;；，]+|\d+(?:\.\d+)?(?:v\d+)?(?![\w.]))', re.I)
NEGATIVE_STATUS = ('未核验', '未核对', '暂未核验', '待核验', '待核对',
                   '待确认', '核验失败', '未通过', '不核验')


def normalized(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).casefold()


def verification_status(text):
    value = normalized(text)
    if any(token in value for token in NEGATIVE_STATUS):
        return False, True
    if any(token in value for token in ('已核验', '已核对', 'verified')):
        return True, True
    return False, False


def review_use(text):
    value = normalized(text)
    if any(token in value for token in ('非综述', '不属综述', '不是综述')):
        return False
    return '综述' in value or 'review' in value


def review_ranges(text):
    """Only explicit paragraph intervals; never trust a reported PMID aggregate."""
    text = unicodedata.normalize('NFKC', text)
    pattern = (r'综述层(?:次)?(?P<prefix>[^\n。;；\d]{0,30}?)'
               r'(?:第\s*)?(?P<start>\d+)\s*[-–—~〜至到]\s*'
               r'(?:第\s*)?(?P<end>\d+)\s*(?P<unit>段)?')
    intervals = []
    for match in re.finditer(pattern, text):
        if not match['unit'] and '段落' not in match['prefix']:
            continue
        start, end = int(match['start']), int(match['end'])
        if start >= 1 and end >= start and [start, end] not in intervals:
            intervals.append([start, end])
    return intervals


def audit_review_ranges(path):
    return review_ranges(path.read_text(encoding='utf-8-sig')) if path.is_file() else []


def review_warnings(stat, file):
    findings = []
    if (stat['review_ranges'] and stat['review_row_markers_present'] and
            stat['review_range_unique_pmids'] != stat['review_row_marker_unique_pmids']):
        findings.append(warning('citation-review-count-mismatch',
            f"Introduction 综述层两种口径不同：显式段落范围 {stat['review_range_unique_pmids']} 篇 "
            f"vs 逐行标记 {stat['review_row_marker_unique_pmids']} 篇；采用显式段落范围，"
            f"范围 {stat['review_ranges']}", file))
    if len(stat['review_ranges']) > 1:
        findings.append(warning('citation-review-multiple-ranges',
            f"发现多个综述层显式范围 {stat['review_ranges']}；按范围并集计数，请核对声明", file))
    return findings


def status_warnings(records, file):
    return [dict(warning('citation-status-unrecognized',
                         f"未识别核验状态原文：{row['status_raw'][:40]!r}；按未核验处理", file),
                 line=row['line'])
            for row in records if not row['status_recognized']]


def warning(rule, msg, file='PROJECT.md'):
    return {'file': file, 'line': 0, 'rule': rule, 'msg': msg}


def load_targets(root):
    path = Path(root) / 'PROJECT.md'
    text = path.read_text(encoding='utf-8-sig') if path.is_file() else ''
    heading = re.search(r'^(#{1,6})\s+(?:\d+[.、]?\s*)?写作目标\s*$', text, re.M)
    values, sources, notes = dict(DEFAULTS), {}, []
    if not heading:
        msg = '缺 PROJECT.md' if not path.is_file() else '缺“写作目标”小节'
        return {'values': values, 'sources': {k: 'default' for k in values},
                'journal': '无/待定', 'notes': [msg + '；使用通用缺省配额']}, []
    body = text[heading.end():]
    end = re.search(r'^#{1,' + str(len(heading[1])) + r'}\s+', body, re.M)
    if end:
        body = body[:end.start()]
    warnings = []
    for key, label in LABELS.items():
        matches = re.findall(r'(?<![\w])' + label + r'\s*(?:[:：|]\s*)?(?:≥|>=)?\s*'
                             r'([^\s|、,，;；]+)', body, re.I)
        if len(matches) == 1 and re.fullmatch(r'\d+(?:篇)?', matches[0]):
            values[key] = int(matches[0].removesuffix('篇'))
            sources[key] = 'PROJECT.md'
        else:
            sources[key] = 'default'
            if matches:
                warnings.append(warning('citation-target-format',
                    f'{key} 配额格式无效或重复 {matches}；使用缺省 {values[key]}'))
            else:
                notes.append(f'{key} 未登记；使用缺省 {values[key]}')
    journal = re.search(r'目标期刊\s*[:：|]\s*([^\n|]+)', body)
    return {'values': values, 'sources': sources,
            'journal': journal[1].strip() if journal else '无/待定', 'notes': notes}, warnings


def identifiers(text):
    def link_text(match):
        label, target = match[1], match[2]
        if re.search(r'\bURL\s*[:：]', label, re.I):
            # Prefer an explicit identifier in the label; otherwise use its publication target.
            return label if re.search(r'URL\s*[:：]\s*https?://', label, re.I) else 'URL: ' + target
        return label

    text = re.sub(r'\[([^\]\n]+)\]\((https?://(?:[^()\s]|\([^()\s]*\))+)\)', link_text, text)
    out = []
    for match in IDENTIFIER.finditer(text):
        kind, value = match[1].lower(), match[2].rstrip('.,。')
        for left, right in (('(', ')'), ('（', '）')):
            while value.endswith(right) and value.count(right) > value.count(left):
                value = value[:-1]
        if kind == 'pmid' and not re.fullmatch(r'\d{6,9}', value):
            continue
        if kind == 'doi' and not re.fullmatch(r'10\.\d{4,9}/\S+', value):
            continue
        if kind == 'url' and not value.startswith(('https://', 'http://')):
            continue
        if kind == 'arxiv' and not re.fullmatch(r'\d{4}\.\d{4,5}(?:v\d+)?', value):
            continue
        out.append(kind + ':' + (value.lower() if kind == 'doi' else value))
    return out


def citation_groups(text):
    """One parenthesized citation cluster is one location; allow nested DOI ()."""
    text = re.sub(r'```.*?```|<!--.*?-->', '', text, flags=re.S)
    stack, start = [], 0
    for pos, char in enumerate(text):
        if char in '(（':
            if not stack:
                start = pos
            stack.append(')' if char == '(' else '）')
        elif stack and char == stack[-1]:
            stack.pop()
            if not stack:
                ids = identifiers(text[start + 1:pos])
                if ids:
                    yield list(dict.fromkeys(ids))


def identifier_column(label):
    label = normalized(label)
    return label.startswith(('标识', '正文标识')) or label.endswith('标识')


def status_column(label):
    label = normalized(label)
    return '核验状态' in label or '核验依据' in label


def audit_records(path):
    if not path.is_file():
        return []
    header, records = None, []
    for line_number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip().startswith('|'):
            header = None
            continue
        cells = [c.strip().strip('`') for c in line.strip().strip('|').split('|')]
        if any(status_column(c) for c in cells) and any(identifier_column(c) for c in cells):
            header = cells
            continue
        if header is None or len(cells) != len(header) or all(re.fullmatch(r'[: -]+', c) for c in cells):
            continue
        id_col = next(i for i, c in enumerate(header) if identifier_column(c))
        status_col = next(i for i, c in enumerate(header) if status_column(c))
        ids = identifiers(cells[id_col])
        if ids:
            use = ' '.join(cells[i] for i, c in enumerate(header) if c.startswith('正文用途'))
            verified, recognized = verification_status(cells[status_col])
            records.append({'ids': ids, 'verified': verified, 'review': review_use(use),
                            'status_raw': cells[status_col], 'status_recognized': recognized,
                            'paragraphs': [int(n) for n in re.findall(r'第\s*(\d+)\s*段',
                                           unicodedata.normalize('NFKC', use))],
                            'line': line_number})
    return records


def section_stats(section, texts, records, canonical, review_intervals=()):
    accepted = {x for row in records if row['verified'] for x in row['ids']}
    rejected = {x for row in records if not row['verified'] for x in row['ids']}
    accepted -= rejected
    review = {x for row in records if row['verified'] and row['review'] for x in row['ids']}
    range_review = {x for row in records if row['verified'] and
                    any(start <= para <= end for para in row['paragraphs']
                        for start, end in review_intervals) for x in row['ids']}
    marker_ids, range_ids = set(), set()
    refs, pmids, unverified = set(), set(), set()
    degraded = {k: set() for k in ('doi', 'url', 'arxiv')}
    locations = verified_locations = occurrences = 0
    for text in texts:
        for group in citation_groups(text):
            locations += 1
            verified_group = set(group) & accepted
            eligible = {x for x in verified_group if x.startswith(('pmid:', 'doi:'))}
            if eligible:
                verified_locations += 1
            occurrences += len(eligible)
            refs.update(canonical.get(x, x) for x in eligible)
            for x in verified_group:
                kind = x.split(':', 1)[0]
                if kind == 'pmid':
                    pmids.add(x)
                    if x in review:
                        marker_ids.add(x)
                    if x in range_review:
                        range_ids.add(x)
            mapped_eligible = {canonical.get(x, x) for x in eligible}
            for x in group:
                kind = x.split(':', 1)[0]
                if kind == 'doi' or (kind in ('url', 'arxiv') and
                                     canonical.get(x, x) not in mapped_eligible):
                    degraded[kind].add(x)
            unverified.update(set(group) - accepted)
    review_ids = range_ids if review_intervals else marker_ids
    quota_ids = pmids if section in ('Introduction', 'Discussion') else refs
    return {'citation_locations': locations, 'verified_locations': verified_locations,
            'verified_identifier_occurrences': occurrences, 'unique_verified': len(refs),
            'verified_references': sorted(refs), 'unique_verified_pmids': len(pmids),
            'review_unique_pmids': len(review_ids), 'quota_actual': len(quota_ids),
            'review_ranges': list(review_intervals),
            'review_source': 'explicit-range' if review_intervals else 'row-markers',
            'review_row_markers_present': any(row['review'] for row in records),
            'review_row_marker_unique_pmids': len(marker_ids),
            'review_range_unique_pmids': len(range_ids) if review_intervals else None,
            'degraded': {k: sorted(v) for k, v in degraded.items()},
            'unverified': sorted(unverified)}


def collect(root):
    root = Path(root)
    targets, warnings = load_targets(root)
    records, files = {}, {}
    for section in SECTIONS:
        folder = root / '04_manuscript' / section
        names = (['Figure_Legends_EN.md', 'Supplementary_Figure_Legends_EN.md', 'Table_Titles_Notes_EN.md']
                 if section == 'Legends' else [section + '_EN.md'])
        files[section] = [folder / name for name in names if (folder / name).is_file()]
        records[section] = audit_records(folder / (section + '_核查说明.md'))
        warnings.extend(status_warnings(records[section],
                        f'04_manuscript/{section}/{section}_核查说明.md'))
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    for rows in records.values():
        for row in rows:
            if row['verified']:
                for x in row['ids']:
                    parent[find(x)] = find(row['ids'][0])
    canonical = {x: find(x) for x in list(parent)}
    stats, total = {}, set()
    for section in SECTIONS:
        texts = [p.read_text(encoding='utf-8-sig') for p in files[section]]
        ranges = audit_review_ranges(root / '04_manuscript' / section / (section + '_核查说明.md'))
        stat = section_stats(section, texts, records[section], canonical, ranges)
        if section == 'Introduction':
            warnings.extend(review_warnings(stat, f'04_manuscript/{section}/{section}_核查说明.md'))
        stat['files'] = [p.relative_to(root).as_posix() for p in files[section]]
        total.update(stat['verified_references'])
        stats[section] = stat
        if stat['unverified']:
            warnings.append(warning('citation-unverified',
                f"{section} {len(stat['unverified'])} 个标识缺本节已核验记录，不计入配额：" +
                ', '.join(stat['unverified']), f'04_manuscript/{section}/{section}_核查说明.md'))
        if section in DEFAULTS:
            target = targets['values'][section]
            stat.update(target=target, gap=max(0, target - stat['quota_actual']))
            if stat['gap']:
                warnings.append(warning('citation-quota', f"{section} 实际 {stat['quota_actual']} vs 目标 {target}；缺口 {stat['gap']} 篇"))
        if section == 'Results' and stat['citation_locations']:
            warnings.append(warning('citation-results', 'Results 出现引用，违反 Results 禁引约定，须由章节检查修正'))
    review = stats['Introduction']['review_unique_pmids']
    review_target = targets['values']['Introduction_review']
    if review < review_target:
        warnings.append(warning('citation-quota', f'Introduction 综述层 实际 {review} vs 目标 {review_target}；缺口 {review_target-review} 篇'))
    gap = max(0, targets['values']['total'] - len(total))
    if gap:
        warnings.append(warning('citation-quota', f"全稿实际 {len(total)} vs 目标 {targets['values']['total']}；缺口 {gap} 篇"))
    return {'targets': targets, 'sections': stats, 'total_unique_verified': len(total),
            'total_target': targets['values']['total'], 'total_gap': gap,
            'warnings': warnings}


def check_section_quota(section, en_path):
    path = Path(en_path).resolve()
    section = section.capitalize()
    project = next((p for p in path.parents if (p / 'PROJECT.md').is_file()), None)
    targets, warnings = load_targets(project or path.parent)
    records = audit_records(path.with_name(section + '_核查说明.md'))
    warnings.extend(status_warnings(records, str(path.with_name(section + '_核查说明.md'))))
    ranges = audit_review_ranges(path.with_name(section + '_核查说明.md'))
    stat = section_stats(section, [path.read_text(encoding='utf-8-sig')], records, {}, ranges)
    if section == 'Introduction':
        warnings.extend(review_warnings(stat, str(path.with_name(section + '_核查说明.md'))))
    for key, actual in [(section, stat['quota_actual'])] + (
            [('Introduction_review', stat['review_unique_pmids'])] if section == 'Introduction' else []):
        target = targets['values'][key]
        if actual < target:
            warnings.append(warning('citation-quota', f'{key} 实际 {actual} vs 目标 {target}；缺口 {target-actual} 篇'))
    if stat['unverified']:
        warnings.append(warning('citation-unverified', '正文标识缺本节已核验记录：' + ', '.join(stat['unverified'])))
    if targets['notes']:
        warnings.append(warning('citation-target-default', '；'.join(targets['notes'])))
    return warnings


def format_report(report):
    lines = ['引用统计：只计本节核查表明确“已核验”且 EN 正文实际引用的 PMID/DOI；'
             'Introduction/Discussion 分节配额只计 PMID。',
             f"目标期刊：{report['targets']['journal']}；配额来源：" +
             json.dumps(report['targets']['sources'], ensure_ascii=False)]
    lines.extend(report['targets']['notes'])
    for section, stat in report['sections'].items():
        lines.append(f"{section}: 引用处数 {stat['citation_locations']}；已核验处数 {stat['verified_locations']}；"
                     f"已核验去重 {stat['unique_verified']}（PMID {stat['unique_verified_pmids']}）；" +
                     (f"配额实际 {stat['quota_actual']} vs 目标 {stat['target']}；缺口 {stat['gap']}；" if 'target' in stat else '') +
                     '降级 DOI/URL/arXiv ' + '/'.join(str(len(stat['degraded'][k])) for k in ('doi', 'url', 'arxiv')))
    lines.append(f"Introduction 综述层：实际 {report['sections']['Introduction']['review_unique_pmids']} vs "
                 f"目标 {report['targets']['values']['Introduction_review']}")
    intro = report['sections']['Introduction']
    if intro['review_ranges']:
        lines.append(f"综述层计数来源：显式段落范围 {intro['review_ranges']}；范围计数 {intro['review_range_unique_pmids']}；"
                     f"逐行标记 {intro['review_row_marker_unique_pmids']}；采用范围计数")
    lines.append(f"跨节去重总数 {report['total_unique_verified']} vs 目标 {report['total_target']}；缺口 {report['total_gap']}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project_root', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if not args.project_root.is_dir():
        parser.error('project_root must be an existing directory')
    report = collect(args.project_root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
        for w in report['warnings']:
            print('[WARN] ' + w['msg'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
