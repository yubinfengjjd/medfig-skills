"""Check a headed English abstract's format and whitespace word count.

This checks structure, not numerical accuracy, translations or scientific validity.
The Results sentence count is an estimate that requires manual confirmation.
"""
import argparse
import json
import re
from pathlib import Path

DEFAULT_HEADINGS = ('Background', 'Methods', 'Results', 'Conclusions')


def analyze(text, limit=250, headings=DEFAULT_HEADINGS):
    if limit < 1 or len(headings) != 4 or len(set(headings)) != 4:
        raise ValueError('Use a positive word limit and four distinct headings')
    marks = list(re.finditer(r'^#{1,6}\s+(.+?)\s*#*\s*$', text, re.M))
    expected = [h.casefold() for h in headings]
    selected = [(i, m) for i, m in enumerate(marks) if m.group(1).casefold() in expected]
    names = [m.group(1).casefold() for _, m in selected]
    errors = []
    if names != expected:
        errors.append('Required headings must appear once each in the requested order')
    sections = {}
    for i, mark in selected:
        name = mark.group(1)
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[mark.end():end].strip()
        paragraphs = [p for p in re.split(r'\n\s*\n', body) if p.strip()]
        if len(paragraphs) != 1:
            errors.append(f'{name}: expected one nonempty paragraph')
        if any(re.match(r'^\s*(?:[-*+]\s|\d+[.)]\s)', line) for line in body.splitlines()):
            errors.append(f'{name}: abstract prose must not be a list')
        sections[name] = body
    if len(selected) == 4:
        first, last = selected[0][0], selected[-1][0]
        if last - first != 3:
            errors.append('Unexpected heading inside the abstract')
    body_count = sum(len(body.split()) for body in sections.values())
    heading_count = sum(len(name.split()) for name in sections)
    if body_count > limit:
        errors.append(f'Body word count {body_count} exceeds limit {limit}')
    result_body = next((body for name, body in sections.items() if name.casefold() == expected[2]), '')
    sentence_count = len([s for s in re.split(r'(?<=[.!?])\s+(?=[A-Z])', result_body) if s.strip()]) if result_body else 0
    return {'words_body': body_count, 'words_with_headings': body_count + heading_count,
            'word_limit': limit, 'section_words': {name: len(body.split()) for name, body in sections.items()},
            'results_sentences_estimate': sentence_count, 'errors': errors,
            'manual_checks': ['Confirm 3-5 Results sentences; abbreviations may affect the estimate',
                              'Check all facts, numbers, uncertainty, claim strength and EN/ZH alignment against sources',
                              'Confirm every major analysis family (transfer / explanation / uncertainty / secondary '
                              'endpoints, as present in the manuscript) appears in Methods and in Results; numbers '
                              'may be trimmed, whole families must not be dropped']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--limit', type=int, default=250)
    parser.add_argument('--headings', nargs=4, default=DEFAULT_HEADINGS)
    args = parser.parse_args()
    result = analyze(args.file.read_text(encoding='utf-8-sig'), args.limit, args.headings)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
