"""Create a candidate native Zotero DOCX, or apply a checked candidate transactionally."""
from __future__ import annotations
import argparse,copy,json,os,re,secrets,shutil,string,sys,zipfile
from datetime import date,datetime
from pathlib import Path
from lxml import etree as E
from extract_citations import q,NS,sha,load,save,package,normalize,fields,paragraphs,visible_text,xml_bytes,extract
CP='http://schemas.openxmlformats.org/officeDocument/2006/custom-properties'
VT='http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
STYLE='http://www.zotero.org/styles/elsevier-vancouver-short-author-list'
def random_id(): return ''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(8))
def run_node(child):
    r=E.Element(q('r'));r.append(child);return r
def fld(kind):
    n=E.Element(q('fldChar'));n.set(q('fldCharType'),kind);return run_node(n)
def instruction(text):
    n=E.Element(q('instrText'));n.set('{http://www.w3.org/XML/1998/namespace}space','preserve');n.text=text;return run_node(n)
def make_citation(marker,records):
    return {'citationID':random_id(),'properties':{'unsorted':False,'formattedCitation':marker,'plainCitation':marker,'noteIndex':0},'citationItems':[copy.deepcopy(r['citation_item']) for r in records], 'schema':'https://github.com/citation-style-language/schema/raw/master/csl-citation.json'}

def page_break_side(run):
    """Only one edge pagination marker with otherwise plain text is proven."""
    if run.tag!=q('r'):return None
    tags=[n.tag for n in run if n.tag!=q('rPr')]
    if len(tags)<2:return None
    if tags[0]==q('lastRenderedPageBreak') and all(t==q('t') for t in tags[1:]):return 'leading'
    if tags[-1]==q('lastRenderedPageBreak') and all(t==q('t') for t in tags[:-1]):return 'trailing'
    return None

def boundary(p,pos):
    """Split touched plain text or proven edge-pagination runs without moving markers."""
    cursor=0
    for idx,node in enumerate(list(p)):
        if node.tag==q('pPr'): continue
        text=''.join((n.text or '') if n.tag==q('t') else '\t' if n.tag==q('tab') else '\n' for n in node.iter() if n.tag in (q('t'),q('tab'),q('br'),q('cr')))
        if cursor==pos: return idx
        if cursor<pos<cursor+len(text):
            side=page_break_side(node)
            if node.tag!=q('r') or (any(n.tag not in (q('rPr'),q('t')) for n in node) and side is None): raise ValueError('Marker boundary crosses unsupported container or mixed-content run')
            cut=pos-cursor;left=copy.deepcopy(node);right=copy.deepcopy(node)
            for r,value in ((left,text[:cut]),(right,text[cut:])):
                for n in list(r):
                    if n.tag==q('t') or (n.tag==q('lastRenderedPageBreak') and ((side=='leading' and r is right) or (side=='trailing' and r is left))):r.remove(n)
                t=E.Element(q('t'));t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=value
                marker=r.find(q('lastRenderedPageBreak'))
                if side=='trailing' and marker is not None:r.insert(r.index(marker),t)
                else:r.append(t)
            p.remove(node);p.insert(idx,left);p.insert(idx+1,right);return idx+1
        cursor+=len(text)
    if cursor==pos: return len(p)
    raise ValueError('Text offset outside paragraph')

def replace_marker(p,occ,data):
    boundary(p,occ['end']);start=boundary(p,occ['start']);end=boundary(p,occ['end'])
    results=list(p)[start:end]
    if not results or any(r.tag!=q('r') or (any(n.tag not in (q('rPr'),q('t')) for n in r) and page_break_side(r) is None) for r in results): raise ValueError('Marker includes non-text content; refusing destructive conversion')
    if ''.join(n.text or '' for r in results for n in r.iter(q('t')))!=occ['marker']: raise ValueError('Marker text/offset mismatch')
    nodes=[fld('begin'),instruction(' ADDIN ZOTERO_ITEM CSL_CITATION '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+' '),fld('separate')]
    for i,n in enumerate(nodes): p.insert(start+i,n)
    p.insert(start+len(nodes)+len(results),fld('end'))

def preferences(parts,baseline):
    b=package(baseline);sample=E.fromstring(b['docProps/custom.xml'])
    props=[copy.deepcopy(p) for p in sample if (p.get('name') or '').startswith('ZOTERO_PREF_')]
    if len(props)!=2: raise ValueError('Baseline must contain exactly ZOTERO_PREF_1 and _2')
    raw=''.join(p[0].text or '' for p in sorted(props,key=lambda n:n.get('name')))
    config=E.fromstring(raw.encode());style=config.find('style')
    if style is None or style.get('id')!=STYLE or config.find("prefs/pref[@name='fieldType']").get('value')!='Field': raise ValueError('Baseline style/fieldType differs from acceptance specification')
    config.find('session').set('id',random_id());new=E.tostring(config,encoding='unicode')
    root=E.fromstring(parts['docProps/custom.xml']) if 'docProps/custom.xml' in parts else E.Element('{'+CP+'}Properties',nsmap={None:CP,'vt':VT})
    for p in list(root):
        if (p.get('name') or '').startswith('ZOTERO_PREF_'): root.remove(p)
    pid=max([int(p.get('pid','1')) for p in root]+[1])+1
    for i,p in enumerate(sorted(props,key=lambda n:n.get('name'))):
        p.set('pid',str(pid+i));p[0].text=new[:-7] if i==0 else '</data>';root.append(p)
    parts['docProps/custom.xml']=xml_bytes(root)
    types=E.fromstring(parts['[Content_Types].xml'])
    if not any(n.get('PartName')=='/docProps/custom.xml' for n in types): E.SubElement(types,'{'+CT+'}Override',PartName='/docProps/custom.xml',ContentType='application/vnd.openxmlformats-officedocument.custom-properties+xml')
    parts['[Content_Types].xml']=xml_bytes(types)
    rels=E.fromstring(parts['_rels/.rels']);typ='http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties'
    if not any(n.get('Type')==typ for n in rels):
        used={n.get('Id') for n in rels};i=1
        while 'rId'+str(i) in used:i+=1
        E.SubElement(rels,'{'+REL+'}Relationship',Id='rId'+str(i),Type=typ,Target='docProps/custom.xml')
    parts['_rels/.rels']=xml_bytes(rels)
    return next(f['instruction'] for f in fields(E.fromstring(b['word/document.xml'])) if f['kind']=='bibliography')

def styled_p(text=None,bold=False):
    p=E.Element(q('p'));r=E.SubElement(p,q('r'));pr=E.SubElement(r,q('rPr'));fonts=E.SubElement(pr,q('rFonts'));fonts.set(q('ascii'),'Arial');fonts.set(q('hAnsi'),'Arial');sz=E.SubElement(pr,q('sz'));sz.set(q('val'),'24')
    if bold:E.SubElement(pr,q('b'))
    if text is not None:E.SubElement(r,q('t')).text=text
    return p

def candidate(source,manifest,snapshot,baseline,output,previous=None):
    source=Path(source);output=Path(output)
    if output.resolve()==source.resolve():raise ValueError('Candidate cannot overwrite source')
    if sha(source)!=manifest['source_sha256']:raise ValueError('Source changed since extraction')
    fresh=extract(source,previous=previous)
    if fresh['occurrences']!=manifest['occurrences']:raise ValueError('Extraction manifest does not describe source')
    refs={r['id']:r for r in manifest['references']};snap={r['key']:r for r in snapshot['items']}
    for r in refs.values():
        if r['status'] not in ('既有','新增','作者指定','人工保留'):raise ValueError('Unclassified reference: '+r['id'])
        if r['status']=='人工保留' and not r.get('reason'):raise ValueError('Manual retention needs a reason')
        if r['status']!='人工保留' and r.get('key') not in snap:raise ValueError('Missing Zotero snapshot item')
        if r['status']=='作者指定':
            resolution=r.get('resolution') or {}
            if r['type']!='URL' or not isinstance(resolution,dict) or resolution.get('source')!='作者映射' or resolution.get('item_key')!=r.get('key') or not Path(resolution.get('file','')).is_absolute() or not isinstance(resolution.get('note'),str):raise ValueError('Invalid author mapping resolution')
            uris=snap[r['key']]['citation_item'].get('uris',[])
            if not uris or any(uri.rsplit('/',1)[-1]!=resolution['item_key'] for uri in uris):raise ValueError('Author mapping key differs from snapshot URI')

    parts=package(source);root=normalize(E.fromstring(parts['word/document.xml']),previous);ps=paragraphs(root);receipt=[]
    for o in reversed(manifest['occurrences']):
        rr=[refs[i['id']] for i in o['identifiers']]
        if any(r['status']=='人工保留' for r in rr):
            receipt.append({**o,'status':'人工保留','reason':'; '.join(r.get('reason','同组含人工保留标识') for r in rr if r['status']=='人工保留')});continue
        items=[snap[r['key']] for r in rr];data=make_citation(o['marker'],items);replace_marker(ps[o['paragraph']],o,data)
        mapped=[{'identifier':r['id'],'resolution':copy.deepcopy(r['resolution']),'level':'WARN'} for r in rr if r['status']=='作者指定']
        receipt.append({**o,'status':'作者指定；字段未刷新' if mapped else '字段未刷新','citationID':data['citationID'],'keys':[r['key'] for r in rr],**({'author_resolutions':mapped} if mapped else {})})
    bib=preferences(parts,baseline);body=root.find(q('body'));idx=len(body)-1 if len(body) and body[-1].tag==q('sectPr') else len(body)
    b=E.Element(q('p'));b.extend([fld('begin'),instruction(bib),fld('separate')]);end=E.Element(q('p'));end.append(fld('end'))
    for i,p in enumerate([styled_p(),styled_p('References',True),b,end]):body.insert(idx+i,p)
    parts['word/document.xml']=xml_bytes(root);output.parent.mkdir(parents=True,exist_ok=True)
    pending=output.with_suffix('.pending.docx')
    if pending.exists() or output.exists():raise ValueError('Candidate exists; choose a fresh process directory')
    with zipfile.ZipFile(pending,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in parts.items():z.writestr(name,data)
    with zipfile.ZipFile(pending) as z:
        if z.testzip():raise ValueError('Candidate ZIP checksum failure')
    os.replace(pending,output)
    type_warnings=['preprint 映射未经第二份作者样例验证'] if any(i.get('raw',{}).get('itemType')=='preprint' for i in snapshot['items']) and not (Path(baseline).parent/'baseline-sample-types.docx').is_file() else []
    author_rows=[{'identifier':r['id'],'resolution':copy.deepcopy(r['resolution']),'level':'WARN'} for r in refs.values() if r['status']=='作者指定']
    type_warnings.extend('作者映射、需作者确认：'+json.dumps(row,ensure_ascii=False) for row in author_rows)
    report={**({'author_resolutions':author_rows} if author_rows else {}),'warnings':type_warnings,'source':str(source.resolve()),'source_sha256':sha(source),'candidate':str(output.resolve()),'candidate_sha256':sha(output),'citation_fields':sum(x['status']!='人工保留' for x in receipt),'bibliography_fields':1,'fields':list(reversed(receipt)),'status':'字段未刷新；文献表待刷新','word_validation':'待作者验收'}
    save(output.parent/'字段注入报告.json',report);return report

def gate(project,authorization=None):
    p=Path(project)/'PROJECT.md'
    if not p.exists():return
    rows=[line for line in p.read_text(encoding='utf-8-sig').splitlines() if re.match(r'^\|\s*11\s*\|',line)]
    confirmed=bool(rows and rows[0].split('|')[4].strip()=='已确认')
    if not confirmed and not (authorization and Path(authorization).is_file() and Path(authorization).read_text(encoding='utf-8-sig').strip()):raise ValueError('Stage 11 not confirmed; provide project-specific written authorization')

def apply_candidate(source,cand,manifest,snapshot,baseline,project=None,output_dir=None,approved=False,authorization=None,previous=None,fail_after=None):
    if not approved:raise ValueError('Author approval after collection required (--approved)')
    from check_references import check
    source=Path(source).resolve();cand=Path(cand).resolve()
    if project:project=Path(project).resolve();gate(project,authorization)
    elif output_dir is None:raise ValueError('Standalone --output-dir required')
    report=check(source,cand,manifest,snapshot,baseline,previous=previous)
    save(cand.parent/'核对报告.json',report)
    if report['errors']:raise ValueError('Reference check ERROR blocks apply')
    m=re.fullmatch(r'(.+)_Manuscript_v(\d+)\.docx',source.name)
    if not m:raise ValueError('Source name must be <project>_Manuscript_v<N>.docx')
    targetdir=project/'05_final' if project else Path(output_dir).resolve();targetdir.mkdir(parents=True,exist_ok=True)
    if project and source.parent!=targetdir:raise ValueError('Pipeline source must be in project 05_final')
    dest=targetdir/f'{m[1]}_Manuscript_v{int(m[2])+1}.docx'
    if dest.exists():raise ValueError('Next manuscript version already exists')
    base=project or Path(output_dir).resolve();archive=base/'_archive'/date.today().isoformat();i=1
    while archive.exists():i+=1;archive=base/'_archive'/f'{date.today().isoformat()}_{i}'
    archive.mkdir(parents=True)
    tx=[];published=False;archived=False;newsha=sha(cand)
    try:
        if project:
            status=project/'PROJECT.md';decision=project/'04_manuscript/作者决定.md'
            text=status.read_text(encoding='utf-8-sig');row=f'| 12 | 参考文献收集与注入 | medical-sci-references | 待确认 | 05_final/{dest.name} | v{int(m[2])+1} | | 字段未刷新；待作者 Word Refresh 验收 |'
            if re.search(r'^\|\s*12\s*\|.*$',text,re.M):text=re.sub(r'^\|\s*12\s*\|.*$',lambda _:row,text,flags=re.M)
            else:
                lines=text.splitlines();at=max([j for j,l in enumerate(lines) if re.match(r'^\|\s*\d+\s*\|',l)]+[-1])+1;lines.insert(at,row);text='\n'.join(lines)+'\n'
            text+='\n- '+date.today().isoformat()+' References：生成 '+dest.name+'；字段未刷新；阶段12待确认。\n'
            dec=decision.read_text(encoding='utf-8-sig') if decision.exists() else '# 作者决定\n'
            entry='- '+date.today().isoformat()+' 字段版主稿 '+dest.name+'；机械核对通过；字段未刷新；待作者验收。\n'
            if re.search(r'^## References\s*$',dec,re.M):
                section=re.search(r'^## References\s*$.*?(?=^## |\Z)',dec,re.M|re.S);at=section.end();dec=dec[:at].rstrip()+'\n\n'+entry+'\n'+dec[at:]
            else:dec+='\n## References\n\n'+entry
            for path,data in ((status,text),(decision,dec)):
                old=path.read_bytes() if path.exists() else None
                if old is not None:
                    bak=archive/path.relative_to(project);bak.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,bak)
                tmp=cand.parent/(path.name+'.transaction');tmp.write_text(data,encoding='utf-8');tx.append((path,tmp,old))
        pending=cand.parent/'publish.pending.docx';shutil.copy2(cand,pending)
        oldpath=archive/'05_final'/source.name;oldpath.parent.mkdir(parents=True,exist_ok=True)
        os.replace(source,oldpath);archived=True
        if fail_after=='archive':raise OSError('Injected archive failure')
        os.replace(pending,dest);published=True
        if sha(dest)!=newsha:raise OSError('Published hash differs')
        for j,(path,tmp,old) in enumerate(tx):
            os.replace(tmp,path)
            if fail_after=='tracking' and j==0:raise OSError('Injected tracking failure')
        result={'status':'待确认','new_manuscript':str(dest),'sha256':newsha,'archive':str(archive),'word_validation':'待作者验收；字段未刷新'};save(cand.parent/'apply报告.json',result);return result
    except Exception:
        if published and dest.exists():os.replace(dest,cand.parent/('rollback-'+dest.name))
        if archived and oldpath.exists():os.replace(oldpath,source)
        for path,tmp,old in tx:
            if old is not None:
                restore=cand.parent/(path.name+'.restore');restore.write_bytes(old);os.replace(restore,path)
            elif path.exists():os.replace(path,cand.parent/(path.name+'.rollback'))
        raise

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('candidate','apply'));p.add_argument('source',type=Path);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--snapshot',required=True,type=Path);p.add_argument('--baseline',required=True,type=Path);p.add_argument('--candidate',required=True,type=Path);p.add_argument('--project-root',type=Path);p.add_argument('--output-dir',type=Path);p.add_argument('--previous-manifest',type=Path);p.add_argument('--approved',action='store_true');p.add_argument('--authorization',type=Path)
    a=p.parse_args();man=load(a.manifest);snap=load(a.snapshot);prev=load(a.previous_manifest) if a.previous_manifest else None
    if a.project_root:gate(a.project_root,a.authorization)
    elif a.output_dir is None:raise ValueError('Standalone --output-dir required')
    if not a.approved:raise ValueError('Stop after collection; obtain author approval before injection (--approved)')
    result=candidate(a.source,man,snap,a.baseline,a.candidate,prev) if a.mode=='candidate' else apply_candidate(a.source,a.candidate,man,snap,a.baseline,a.project_root,a.output_dir,a.approved,a.authorization,prev)
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as e:print(str(e),file=sys.stderr);sys.exit(1)
