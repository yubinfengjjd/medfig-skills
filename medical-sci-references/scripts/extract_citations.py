"""Extract citation markers and restore unrefreshed native Zotero fields. Offline."""
from __future__ import annotations
import argparse,copy,hashlib,json,re,sys,zipfile
from pathlib import Path
from lxml import etree as E
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'w':W}
def q(local): return '{'+W+'}'+local
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def xml_bytes(node): return E.tostring(node,encoding='UTF-8',xml_declaration=True,standalone=True)
def c14n(node): return E.tostring(node,method='c14n') if node is not None else b''
def package(path):
    with zipfile.ZipFile(path) as z: return {n:z.read(n) for n in z.namelist()}
def doi_norm(value): return re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)','',value.strip(),flags=re.I).rstrip('.,;').lower()
TOKEN=re.compile(r'\b(PMID|DOI|arXiv|URL):\s*(https?://[^\s;\]\)）}>]+|10\.[^\s;\]\)）}>]+|\d{4}\.\d{4,5}(?:v\d+)?|\d+)',re.I)
def identifiers(text):
    out=[]
    for m in TOKEN.finditer(text):
        typ={'pmid':'PMID','doi':'DOI','arxiv':'arXiv','url':'URL'}[m[1].lower()]
        val=m[2].rstrip('.,;')
        if typ=='DOI': val=doi_norm(val)
        if typ=='PMID' and not val.isdigit(): raise ValueError('Malformed PMID: '+val)
        if typ=='DOI' and not re.fullmatch(r'10\.\d{4,9}/\S+',val):raise ValueError('Malformed DOI: '+val)
        if typ=='arXiv' and not re.fullmatch(r'\d{4}\.\d{4,5}(?:v\d+)?',val):raise ValueError('Unsupported arXiv identifier: '+val)
        if typ=='URL' and not val.startswith(('http://','https://')):raise ValueError('Malformed URL')
        out.append({'type':typ,'value':val,'id':typ+': '+val})
    return out

def scan_markers(text):
    """Adjacent identifiers inside one pair of brackets form one occurrence."""
    for prefix in re.finditer(r'\b(?:PMID|DOI|arXiv|URL):',text,re.I):
        if not any(m.start()==prefix.start() for m in TOKEN.finditer(text)):raise ValueError('Malformed or unsupported citation marker near '+text[prefix.start():prefix.start()+60])
    groups=[];used=set()
    for m in re.finditer(r'\([^()]*\)|（[^（）]*）|\[[^\[\]]*\]',text):
        inner=m[0][1:-1];ids=identifiers(inner)
        if ids and not TOKEN.sub('',inner).strip(' ;,，；\t\n'):
            groups.append({'start':m.start(),'end':m.end(),'marker':m[0],'identifiers':ids})
            used.update(range(m.start(),m.end()))
    for m in TOKEN.finditer(text):
        if m.start() in used: continue
        end=m.end()
        while end>m.start() and text[end-1] in '.,;': end-=1
        groups.append({'start':m.start(),'end':end,'marker':text[m.start():end], 'identifiers':identifiers(text[m.start():end])})
    return sorted(groups,key=lambda x:x['start'])

def fields(root):
    """Complex fields can span paragraphs; instrText fragments are concatenated."""
    stack=[];out=[]
    for run in root.iter(q('r')):
        for node in run:
            if node.tag==q('fldChar'):
                kind=node.get(q('fldCharType'))
                if kind=='begin': stack.append({'runs':[],'instruction':'','result_runs':[],'phase':'instruction','begin':run})
                elif kind=='separate' and stack: stack[-1]['phase']='result'
                elif kind=='end' and stack:
                    field=stack.pop();field['end']=run
                    if run not in field['runs']: field['runs'].append(run)
                    ins=field['instruction'];field['kind']='citation' if 'ZOTERO_ITEM' in ins else 'bibliography' if 'ZOTERO_BIBL' in ins else 'other'
                    if field['kind']=='citation':
                        match=re.fullmatch(r'\s*ADDIN ZOTERO_ITEM CSL_CITATION\s+(\{.*\})\s*',ins,re.S)
                        if not match: raise ValueError('Malformed Zotero citation instruction')
                        field['data']=json.loads(match[1])
                    out.append(field)
            elif node.tag==q('instrText') and stack and stack[-1]['phase']=='instruction': stack[-1]['instruction']+=node.text or ''
        for field in stack:
            if run not in field['runs']: field['runs'].append(run)
            if field['phase']=='result' and any(n.tag==q('t') for n in run): field['result_runs'].append(run)
    if stack: raise ValueError('Unbalanced complex fields')
    for simple in root.iter(q('fldSimple')):
        if 'ZOTERO_' in simple.get(q('instr'),''): raise ValueError('fldSimple Zotero field unsupported by author baseline; report before conversion')
    return out

def visible_text(p):
    def belongs(n): return next(n.iterancestors(q('p')),None) is p
    return ''.join((n.text or '') if n.tag==q('t') else '\t' if n.tag==q('tab') else '\n' for n in p.iter() if n.tag in (q('t'),q('tab'),q('br'),q('cr')) and belongs(n))
def paragraphs(root): return list(root.iter(q('p')))
def normalize(root,previous=None):
    """Remove only existing Zotero wrappers and their final References block."""
    fs=fields(root);cit=[f for f in fs if f['kind']=='citation'];bibs=[f for f in fs if f['kind']=='bibliography']
    for i,f in enumerate(cit):
        result=''.join(n.text or '' for r in f['result_runs'] for n in r.iter(q('t')))
        raw=f['data'].get('properties',{}).get('plainCitation','')
        if not scan_markers(result):
            if previous is None: raise ValueError('Refreshed field requires --previous-manifest to restore original marker')
            prior={r['id']:r for r in previous['references']}
            eligible=[o for o in previous['occurrences'] if all(prior[x['id']]['status']!='人工保留' for x in o['identifiers'])]
            raw=eligible[i]['marker']
        else: raw=result
        if not scan_markers(raw): raise ValueError('Cannot restore marker from field')
        parent=f['begin'].getparent()
        if any(r.getparent() is not parent for r in f['runs']): raise ValueError('Citation spans containers; manual review required')
        at=parent.index(f['begin']);results=f['result_runs']
        if result!=raw:
            nr=E.Element(q('r'))
            if results and results[0].find(q('rPr')) is not None: nr.append(copy.deepcopy(results[0].find(q('rPr'))))
            t=E.SubElement(nr,q('t'));t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=raw
            results=[nr]
        for r in f['runs']: parent.remove(r)
        for j,r in enumerate(results): parent.insert(at+j,r)
    if bibs:
        if len(bibs)!=1: raise ValueError('Multiple bibliographies')
        body=root.find(q('body'));begin=bibs[0]['begin']
        p=next(begin.iterancestors(q('p')),None)
        if p is None or p.getparent() is not body: raise ValueError('Bibliography outside document body')
        idx=body.index(p);h=idx-1
        if h<0 or visible_text(body[h])!='References': raise ValueError('Bibliography not preceded by References heading')
        start=h-1 if h>0 and body[h-1].tag==q('p') and not visible_text(body[h-1]) else h
        # Only trailing bibliography result paragraphs are accepted, never tables/section changes.
        tail=[n for n in list(body)[idx:] if n.tag!=q('sectPr')]
        if any(n.tag!=q('p') or n.find('.//'+q('sectPr')) is not None for n in tail): raise ValueError('Unexpected content in bibliography tail')
        for n in list(body)[start:]:
            if n.tag!=q('sectPr'): body.remove(n)
    return root

def classify(p,text):
    if next(p.iterancestors(q('tbl')),None) is not None or re.match(r'^(?:Table\s+\d|Notes?:)',text,re.I): return 'table'
    if re.match(r'^Figure\s+\d',text,re.I): return 'figure'
    return 'body'

def crosscheck(project,refs):
    if not project: return []
    project=Path(project);paths=list(project.glob('_process/Finalize/**/参考文献候选清单.md'))+list(project.glob('04_manuscript/*/*核查说明.md'))
    actual={r['id'] for r in refs};out=[]
    for p in sorted(paths):
        text=p.read_text(encoding='utf-8-sig');found={r['id'] for r in identifiers(text)}
        out.append({'source':str(p),'manuscript_only':sorted(actual-found),'source_only':sorted(found-actual),'identifiers':sorted(found),'status':'WARN' if found!=actual else 'PASS'})
    return out

def extract(source,project=None,previous=None):
    parts=package(source);root=E.fromstring(parts['word/document.xml'])
    original_fields=fields(root);is_field=any(f['kind']=='citation' for f in original_fields)
    restored_fields=[]
    for f in original_fields:
        if f['kind']=='citation':
            restored_fields.append({'data':copy.deepcopy(f['data']),'placeholder':f['data'].get('properties',{}).get('plainCitation','')})
    normalize(root,previous);occ=[];refs={};section='front'
    for i,p in enumerate(paragraphs(root)):
        text=visible_text(p)
        if text.strip() in ('Abstract','Introduction','Methods','Results','Discussion'): section=text.strip()
        for m in scan_markers(text):
            m.update(occurrence=len(occ)+1,paragraph=i,section=section,kind=classify(p,text),before=text[:m['start']],after=text[m['end']:])
            occ.append(m)
            for ident in m['identifiers']:
                if ident['id'] not in refs: refs[ident['id']]={**ident,'first_occurrence':m['occurrence'],'status':'人工保留' if ident['type']=='URL' else '待收集','reason':'URL-only 不自动抓取' if ident['type']=='URL' else ''}
    result={'schema':1,'source':str(Path(source).resolve()),'source_sha256':sha(source),'source_kind':'field' if is_field else 'marker','occurrences':occ,'references':list(refs.values()),'crosscheck':crosscheck(project,list(refs.values())),'restored_fields':restored_fields}
    if previous is not None:
        prior_refs={r['id']:r for r in previous['references']}
        expected_fields=[o for o in previous['occurrences'] if all(prior_refs[x['id']]['status']!='人工保留' for x in o['identifiers'])]
        if is_field:
            if len(restored_fields)!=len(expected_fields):raise ValueError('I9: restored field count differs from previous manifest')
            for restored,o in zip(restored_fields,expected_fields):
                keys=[u.split('/')[-1] for ci in restored['data']['citationItems'] for u in ci.get('uris',[])[:1]]
                expected_keys=[prior_refs[x['id']].get('key') for x in o['identifiers']]
                if keys!=expected_keys:raise ValueError('I9: restored field item identities differ from previous manifest')
        old=[(m['paragraph'],m['start'],m['marker'],m['identifiers']) for m in previous['occurrences']]
        new=[(m['paragraph'],m['start'],m['marker'],m['identifiers']) for m in occ]
        result['source_consistent']=old==new
        if not result['source_consistent']: raise ValueError('I9: field-restored source differs from previous manifest')
    return result

def write_manifest(out,data):
    out=Path(out);save(out/'引用清单.json',data)
    lines=['# 引用清单','','序号 | 标识 | 类型 | 首现位置 | Zotero key | 来源 | 元数据缺口','---|---|---|---|---|---|---']
    for i,r in enumerate(data['references'],1):
        o=data['occurrences'][r['first_occurrence']-1]
        lines.append(f"{i} | {r['id']} | {r['type']} | {o['section']}/{o['kind']}/p{o['paragraph']} | {r.get('key','')} | {r['status']} | {', '.join(r.get('warnings',[]))}")
    lines+=['','## 三方核对',json.dumps(data['crosscheck'],ensure_ascii=False,indent=2)]
    (out/'引用清单.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output-dir',required=True,type=Path);p.add_argument('--project-root',type=Path);p.add_argument('--previous-manifest',type=Path)
    a=p.parse_args();data=extract(a.source,a.project_root,load(a.previous_manifest) if a.previous_manifest else None);write_manifest(a.output_dir,data)
    print(json.dumps({'occurrences':len(data['occurrences']),'references':len(data['references']),'crosscheck':data['crosscheck']},ensure_ascii=False))
if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError) as e: print(str(e),file=sys.stderr);sys.exit(1)
