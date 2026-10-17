"""Offline English prose style diagnostics (stdlib only).

This file is vendored byte-for-byte in medical-sci-abstract/scripts. No network,
language model, or scientific inference is used. Semicolon exemptions are narrow
recognizers, never a blanket exemption for parentheses or a 'Notes:' label.
Sentence counts are estimates: decimals, bracketed content, common abbreviations,
closing quotes and wrapped paragraphs are handled; uncommon abbreviations and
unbalanced brackets require human review. Whitespace-delimited tokens count as
words (including statistical notation), matching the existing whitespace rule.
Headings, fenced code, Markdown table rows and bold figure/table titles are not
prose. Structural lists retain word counts and the unconditional 60-word cap.
"""
import re

VERSION = '2026-10-17.2'
_OPEN = {'(': ')', '[': ']', '（': '）', '［': '］'}
_CLOSE = set(_OPEN.values())
_SEMI = ';；'
_ABBR = re.compile(r'\b(?:e\.g\.|i\.e\.|et\s+al\.|vs\.|Fig\.|Figs\.|Dr\.|Mr\.|Ms\.|No\.|approx\.|etc\.)', re.I)
_CITATION = re.compile(r'(?:PMID\s*:\s*\d+|(?:DOI|URL|arXiv)\s*:\s*\S+|(?:Supplementary\s+)?(?:Figs?\.?|Figures?|Tables?)\s+S?\d+[a-z]?(?:[–, -]+[a-z0-9]+)*)', re.I)
_STAT = re.compile(r'(?:\b(?:CI|SD|SE|IQR|AUROC|AUPRC|BACC|MAE|HR|OR|RR|P|p|n|N|r|rho|tau|beta|mean|median|range|df)\b|[ρτβχ]|[=<>≤≥])')
_CLAUSE = re.compile(r'\b(?:we|they|it|this|these|those|was|were|is|are|has|have|had|showed|improved|declined|increased|decreased|observed|found|measured|estimated|compared|assessed|recorded|demonstrated|changed|differed)\b',re.I)


def _brackets(text):
    stack, pairs = [], []
    for i, char in enumerate(text):
        if char in _OPEN:
            stack.append((i, _OPEN[char]))
        elif char in _CLOSE and stack and char == stack[-1][1]:
            start, _ = stack.pop()
            pairs.append((start, i))
    return pairs


def _structural_bracket(content):
    # Remove nested groups for classification, but inspect their own pairs too.
    chars = list(content)
    for a, b in _brackets(content):
        chars[a:b+1] = ' '*(b+1-a)
    parts = [p.strip() for p in re.split('['+_SEMI+']', ''.join(chars))]
    if len(parts) < 2 or not all(parts):
        return False
    if all(_CITATION.fullmatch(p) for p in parts):
        return True
    # Each item must be a compact numerical/statistical fragment, not a clause.
    return all(re.search(r'\d', p) and (_STAT.search(p)
               or re.fullmatch(r'[\d\s.,%+−–/-]+',p)
               or re.match(r'^[A-Za-z][A-Za-z -]{0,50}\s*[:,]\s*[+−-]?[\d.]',p)) and len(p.split()) <= 12
               and not _CLAUSE.search(p)
               for p in parts)


def _abbreviation_list(text):
    text = re.sub(r'^\s*(?:[-*+]\s+|\d+[.)]\s+)', '', text)
    text = re.sub(r'^\s*(?:Abbreviations?|Notes?|Table\s+(?:S?\d+)\s+notes?)\s*:\s*', '', text, flags=re.I)
    parts = [p.strip().rstrip('.。') for p in re.split('['+_SEMI+']', text)]
    if len(parts) < 2:
        return False
    # Every item needs an abbreviation key and a nonempty expansion (any case).
    # Multiword keys are allowed only when every token is itself acronym-like.
    # A 'Notes:' prefix alone, or prose mentioning acronyms, grants no exemption.
    for part in parts:
        m = re.fullmatch(r'([A-Za-z][A-Za-z0-9/−–-]{0,20}(?:[ \t]+[A-Za-z][A-Za-z0-9/−–-]{0,20})*)\s*[,，=:：]\s*[^;；.!?]+',part)
        if not m or not all(key.isupper() or sum(c.isupper() for c in key) >= 2
                            for key in m[1].split()):
            return False
    return True


def prose_semicolons(text):
    if _abbreviation_list(text):
        return 0
    exempt = set()
    for a, b in _brackets(text):
        if _structural_bracket(text[a+1:b]):
            exempt.update(i for i in range(a+1, b) if text[i] in _SEMI)
    return sum(char in _SEMI and i not in exempt for i, char in enumerate(text))


def _blocks(text, section):
    """Yield (raw, start offset, section label); soft line wraps stay together."""
    parts, start, label, fenced = [], 0, section, False
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        heading = re.match(r'^#{1,6}\s+(.+?)\s*#*$', stripped)
        structural_line = _abbreviation_list(stripped)
        boundary = not stripped or heading or stripped.startswith('|') or stripped.startswith(('```','~~~'))
        new_item = bool(re.match(r'^\s*(?:[-*+]\s+|\d+[.)]\s+|\*\*(?:Supplementary )?(?:Figure|Table)\s)', line))
        if boundary or new_item or structural_line:
            if parts:
                yield ''.join(parts), start, label
                parts = []
        if stripped.startswith(('```','~~~')):
            fenced = not fenced
        elif heading:
            label = section + ' / ' + heading[1] if heading[1].casefold() != section.casefold() else section
        elif not boundary and not fenced:
            if not parts:
                start = offset
            parts.append(line)
            if structural_line:
                yield ''.join(parts), start, label
                parts = []
        offset += len(line)
    if parts:
        yield ''.join(parts), start, label


def _sentences(block):
    chars = list(block)
    # Mask only presentation tokens; preserve character offsets in original input.
    title = re.match(r'\s*\*\*((?:Supplementary )?(?:Figure|Table)\s+S?\d+\..*?)\*\*', block)
    if title:
        chars[:title.end()] = ' '*title.end()
    for m in re.finditer(r'\*\*|__|(?<!\w)(?:\([a-h](?:[–-][a-h])?\)|（[a-h](?:[–-][a-h])?）)(?!\w)', block):
        chars[m.start():m.end()] = ' '*(m.end()-m.start())
    visible = ''.join(chars)
    bullet = re.match(r'^\s*(?:[-*+]\s+|\d+[.)]\s+)', visible)
    if bullet:
        visible = ' '*bullet.end()+visible[bullet.end():]
    protected = set()
    for a, b in _brackets(visible):
        protected.update(range(a, b+1))
    for m in _ABBR.finditer(visible):
        protected.update(range(m.start(), m.end()))
    start, i = 0, 0
    while i < len(visible):
        char = visible[i]
        if char in '.!?' and i not in protected:
            if char == '.' and i and i+1 < len(visible) and visible[i-1].isdigit() and visible[i+1].isdigit():
                i += 1
                continue
            end = i+1
            while end < len(visible) and visible[end] in '\"\'”’':
                end += 1
            if end == len(visible) or visible[end].isspace():
                raw = visible[start:end]
                if raw.strip():
                    lead = len(raw)-len(raw.lstrip())
                    yield raw.strip(), start+lead
                start = end
                i = end
                continue
        i += 1
    raw = visible[start:]
    if raw.strip():
        yield raw.strip(), start+len(raw)-len(raw.lstrip())


def analyze_style(text, section='manuscript'):
    """Return statistics, sentence locations, and ERROR/WARN finding dictionaries.

    Both entry checkers expose this function. Finalize reuses the pipeline copy.
    Warnings do not change successful exit status; any ERROR must remain nonzero.
    """
    sents = []
    for block_id, (block, offset, label) in enumerate(_blocks(text, section)):
        for sent, local in _sentences(block):
            words = sent.split()
            if not re.search(r'\w', sent):
                continue
            absolute = offset+local
            first = re.search(r'\w[\w’\'-]*', sent)
            sents.append(dict(section=label, sentence=len(sents)+1, first_word=first[0],
                              excerpt=sent[:80], line=text.count('\n',0,absolute)+1, offset=absolute,
                              words=len(words), prose_semicolons=prose_semicolons(sent), block=block_id))
    findings = []
    def add(level, rule, value, threshold, hint, locations):
        pos = locations[0]
        msg = (f"{pos['section']} 句{pos['sentence']}（{pos['first_word']}，行{pos['line']}）："
               f'当前值 {value}，阈值 {threshold}；{hint}')
        findings.append(dict(level=level, rule=rule, msg=msg, context=pos['excerpt'],
                             **{k: pos[k] for k in ('section','sentence','first_word','excerpt','line','offset')},
                             value=value, threshold=threshold, hint=hint,
                             locations=[{k:s[k] for k in ('section','sentence','first_word','excerpt','line','offset')} for s in locations]))
    for s in sents:
        if s['prose_semicolons'] >= 2:
            add('ERROR','semicolon-chain',s['prose_semicolons'],'<2',
                '拆句，或用并列/从属连词，或改为紧凑并列；核对结构性分号豁免。',[s])
        if s['words'] > 60:
            add('ERROR','sentence-hard',s['words'],'≤60 words',
                '拆分过载句，保留限定与统计归属；用连词衔接。',[s])
    n = len(sents)
    long_sents = [s for s in sents if s['words'] > 45]
    mean = sum(s['words'] for s in sents)/n if n else 0
    if n and len(long_sents)/n > .10:
        add('WARN','sentence-share',len(long_sents)/n,'≤10% sentences >45 words',
            '检查这些长句，拆句或改为紧凑并列；不要删掉必要限定。',long_sents)
    if n and not 18 <= mean <= 28:
        add('WARN','sentence-average',mean,'18–28 words/sentence',
            '检查全节句式：长句适度拆句，短句用连词或从句衔接，避免电报体。',[sents[0]])
    runs, run = [], []
    def flush():
        if len(run) >= 3:
            runs.append(list(run))
            add('WARN','sentence-short-run',len(run),'<3 consecutive sentences <8 words',
                '用连词/从句连接相关短句，或写成紧凑并列，保留主题层次。',run)
        run.clear()
    for s in sents:
        if run and run[-1]['block'] != s['block']:
            flush()
        if s['words'] < 8:
            run.append(s)
        else:
            flush()
    flush()
    return dict(version=VERSION, section=section, statistics=dict(
        sentences=n, words=sum(s['words'] for s in sents), mean_words=mean,
        over_45=len(long_sents), over_45_share=len(long_sents)/n if n else 0,
        over_60=sum(s['words'] > 60 for s in sents),
        semicolon_chains=sum(s['prose_semicolons'] >= 2 for s in sents),
        short_runs=len(runs), max_short_run=max((len(r) for r in runs), default=0)),
        sentences=sents, findings=findings)
