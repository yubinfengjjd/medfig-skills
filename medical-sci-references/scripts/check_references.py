"""Independent I1-I9 verification; does not prove Word Refresh or scientific support."""
from __future__ import annotations
import argparse,copy,json,re,sys
from pathlib import Path
from lxml import etree as E
from extract_citations import q,sha,load,save,package,normalize,fields,paragraphs,visible_text,extract,c14n,doi_norm
STYLE='http://www.zotero.org/styles/elsevier-vancouver-short-author-list'
CP='http://schemas.openxmlformats.org/officeDocument/2006/custom-properties'
def char_stream(p):
    out=[]
    for n in p.iter():
        if n.tag not in (q('t'),q('tab'),q('br'),q('cr')):continue
        if next(n.iterancestors(q('p')),None) is not p:continue
        r=next(n.iterancestors(q('r')),None);pr=r.find(q('rPr')) if r is not None else None
        value=n.text or '' if n.tag==q('t') else '\t' if n.tag==q('tab') else '\n'
        out.extend((ch,c14n(pr).decode()) for ch in value)
    return out

def skeleton(root):
    root=copy.deepcopy(root)
    for r in list(root.iter(q('r'))):
        tags=[n.tag for n in r if n.tag!=q('rPr')]
        edge_break=len(tags)>=2 and ((tags[0]==q('lastRenderedPageBreak') and all(t==q('t') for t in tags[1:])) or (tags[-1]==q('lastRenderedPageBreak') and all(t==q('t') for t in tags[:-1])))
        if edge_break:
            for n in list(r):
                if n.tag==q('t'):r.remove(n)
        if all(n.tag in (q('rPr'),q('t')) for n in r):r.getparent().remove(r)
    return c14n(root)

def pagination_anchors(root):
    """Zero-width pagination position, XML attributes, run attributes and rPr."""
    result=[]
    for index,p in enumerate(paragraphs(root)):
        offset=0
        for node in p.iter():
            if next(node.iterancestors(q('p')),None) is not p:continue
            if node.tag==q('lastRenderedPageBreak'):
                run=node.getparent()
                result.append({'paragraph':index,'offset':offset,'xml':c14n(node).decode(),'run_attributes':dict(run.attrib),'run_properties':c14n(run.find(q('rPr'))).decode()})
            elif node.tag==q('t'):offset+=len(node.text or '')
            elif node.tag in (q('tab'),q('br'),q('cr')):offset+=1
    return result

def field_location(field,ps):
    p=next(field['begin'].iterancestors(q('p')),None)
    if p is None:return None,None
    at=0
    for n in p.iter():
        if n is field['begin']:break
        if n.tag==q('t'):at+=len(n.text or '')
        elif n.tag in (q('tab'),q('br'),q('cr')):at+=1
    return ps.index(p),at

def check(source,candidate,manifest,snapshot,baseline,previous=None,gaps=None):
    evidence={};rows=[];warnings=[];author_rows=[]
    if any(i.get('raw',{}).get('itemType')=='preprint' for i in snapshot['items']) and not (Path(baseline).parent/'baseline-sample-types.docx').is_file():warnings.append('preprint 映射未经第二份作者样例验证')
    def record(i,ok,details):evidence[i]={'status':'PASS' if ok else 'ERROR','evidence':details}
    try:
        srcpack=package(source);newpack=package(candidate);src=E.fromstring(srcpack['word/document.xml']);new=E.fromstring(newpack['word/document.xml'])
        srcview=normalize(copy.deepcopy(src),previous);original=extract(source,previous=previous)
        srcps=paragraphs(srcview);newps=paragraphs(new);fs=fields(new);cit=[f for f in fs if f['kind']=='citation'];bibs=[f for f in fs if f['kind']=='bibliography']
        refs=manifest['references']
        for r in refs:
            warnings.extend(r['id']+'：'+w for w in r.get('warnings',[]) if r.get('status')!='作者指定' or not w.startswith('作者映射、需作者确认'))
            if r.get('status')=='作者指定':
                author_rows.append({'identifier':r['id'],'resolution':copy.deepcopy(r.get('resolution')),'level':'WARN'})
                warnings.append(r['id']+'：作者映射、需作者确认；'+json.dumps(r.get('resolution'),ensure_ascii=False))
        warnings.extend('三方核对差异：'+x['source']+'；稿件独有='+str(x['manuscript_only'])+'；来源独有='+str(x['source_only']) for x in manifest.get('crosscheck',[]) if x['status']=='WARN')
        refmap={r['id']:r for r in refs};snap={r['key']:r for r in snapshot['items']};occ=original['occurrences']
        exact=manifest['occurrences']==occ and len(refmap)==len(refs) and {i['id'] for o in occ for i in o['identifiers']}==set(refmap)
        legal=all(r['status'] in ('既有','新增','作者指定','人工保留') for r in refs)
        record('I1',exact and legal and sha(source)==manifest['source_sha256'],{'source_occurrences':len(occ),'inventory_references':len(refs),'complete':exact,'legal_status':legal,'source_hash_matches':sha(source)==manifest['source_sha256']})
        expected=[o for o in occ if all(refmap.get(i['id'],{}).get('status')!='人工保留' for i in o['identifiers'])]
        ids=[f['data'].get('citationID') for f in cit]
        record('I2',len(cit)==len(expected) and len(ids)==len(set(ids)) and all(f['data'].get('citationItems') for f in cit),{'expected_fields':len(expected),'actual_fields':len(cit),'citation_ids':ids})
        positions=[];consistent=[]
        for j,o in enumerate(expected):
            f=cit[j] if j<len(cit) else None
            pos=field_location(f,newps) if f else (None,None)
            text=''.join(n.text or '' for r in f['result_runs'] for n in r.iter(q('t'))) if f else None
            posok=pos==(o['paragraph'],o['start']) and text==o['marker'] and (visible_text(newps[pos[0]]) if pos[0] is not None else None)==visible_text(srcps[o['paragraph']])
            positions.append({'occurrence':o['occurrence'],'source':[o['paragraph'],o['start']],'new':pos,'marker_exact':text==o['marker'],'ok':posok})
            rr=[refmap.get(i['id'],{}) for i in o['identifiers']];expected_items=[snap.get(r.get('key'),{}).get('citation_item') for r in rr]
            items=f['data'].get('citationItems',[]) if f else []
            itemok=items==expected_items and all(items) and len(items)==len(o['identifiers'])
            identok=[]
            for item_index,(ident,r) in enumerate(zip(o['identifiers'],rr)):
                s=snap.get(r.get('key'),{});raw=s.get('raw',{});item=s.get('citation_item',{}).get('itemData',{})
                known=s.get('resolved_identifiers',[])
                if r.get('status')=='作者指定':
                    resolution=r.get('resolution') if isinstance(r.get('resolution'),dict) else {}
                    uris=items[item_index].get('uris',[]) if item_index<len(items) else []
                    ok=ident['type']=='URL' and resolution.get('source')=='作者映射' and resolution.get('item_key')==r.get('key') and bool(uris) and all(uri.rsplit('/',1)[-1]==resolution.get('item_key') for uri in uris) and Path(resolution.get('file','')).is_absolute() and isinstance(resolution.get('note'),str)
                elif ident['type']=='DOI':ok=doi_norm(item.get('DOI',''))==doi_norm(ident['value'])
                elif ident['type']=='PMID':ok=bool(re.search(r'\bPMID:\s*'+re.escape(ident['value'])+r'\b',raw.get('extra',''),re.I)) or ident['id'] in known or ('pubmed.ncbi.nlm.nih.gov/'+ident['value']) in raw.get('url','')
                else:ok=ident['id'] in known or ident['value'] in raw.get('url','')
                identok.append(ok)
                if r.get('match')=='title-year':warnings.append('按题名匹配，需人工确认：'+ident['id'])
            itemok=itemok and all(identok)
            consistent.append({'occurrence':o['occurrence'],'keys':[r.get('key') for r in rr],'item_data_exact':items==expected_items,'identifier_matches':identok,'ok':itemok})
            rows.append({'序号':o['occurrence'],'标识':o['marker'],'类型':[i['type'] for i in o['identifiers']],'源位置':[o['paragraph'],o['start'],o['kind']],'新位置':pos,'Zotero key':[r.get('key') for r in rr],'DOI':[x.get('itemData',{}).get('DOI','') for x in items],'状态':'作者指定；字段未刷新' if any(r.get('status')=='作者指定' for r in rr) else '字段未刷新'})
        record('I3',len(positions)==len(cit) and all(p['ok'] for p in positions),positions)
        # Same URI must always carry the same integer itemID and payload.
        identity={};idok=True
        for f in cit:
            for ci in f['data'].get('citationItems',[]):
                uri=tuple(ci.get('uris',[]));iid=ci.get('id');payload=ci.get('itemData',{})
                if type(iid) is not int or payload.get('id')!=iid or not uri:idok=False
                if uri in identity and identity[uri]!=(iid,payload):idok=False
                identity[uri]=(iid,payload)
        record('I4',len(consistent)==len(cit) and all(c['ok'] for c in consistent) and idok,{'fields':consistent,'stable_integer_identity':idok})
        # Restoring wrappers must give the identical source characters and direct formatting.
        newview=normalize(copy.deepcopy(new),manifest);restored=paragraphs(newview)
        char_errors=[]
        for i,(a,b) in enumerate(zip(srcps,restored)):
            if char_stream(a)!=char_stream(b):char_errors.append(i)
        record('I5',len(srcps)==len(restored) and not char_errors,{'source_paragraphs':len(srcps),'restored_paragraphs':len(restored),'character_or_direct_format_differences':char_errors})
        prefok=False;regok=False;style=None;prefdetails={}
        if 'docProps/custom.xml' in newpack:
            cp=E.fromstring(newpack['docProps/custom.xml']);props=[p for p in cp if (p.get('name') or '').startswith('ZOTERO_PREF_')]
            raw=''.join(p[0].text or '' for p in sorted(props,key=lambda x:x.get('name')))
            config=E.fromstring(raw.encode());style=config.find('style').get('id');pref=config.find("prefs/pref[@name='fieldType']")
            prefok=len(props)==2 and style==STYLE and pref is not None and pref.get('value')=='Field'
            types=E.fromstring(newpack['[Content_Types].xml']);rels=E.fromstring(newpack['_rels/.rels'])
            regok=sum(n.get('PartName')=='/docProps/custom.xml' and n.get('ContentType')=='application/vnd.openxmlformats-officedocument.custom-properties+xml' for n in types)==1 and sum(n.get('Type','').endswith('/custom-properties') and n.get('Target')=='docProps/custom.xml' for n in rels)==1
            prefdetails={'names':[p.get('name') for p in props],'style':style,'registered':regok}
        base=package(baseline);base_bib=[f['instruction'] for f in fields(E.fromstring(base['word/document.xml'])) if f['kind']=='bibliography']
        body=new.find(q('body'));bibok=False
        if len(bibs)==1:
            bp=next(bibs[0]['begin'].iterancestors(q('p')),None);ep=next(bibs[0]['end'].iterancestors(q('p')),None)
            if bp is not None and bp.getparent() is body:
                at=body.index(bp);bibok=at>0 and visible_text(body[at-1])=='References' and bibs[0]['instruction'] in base_bib and ep is not None and all(n is ep or n.tag==q('sectPr') for n in list(body)[at+1:])
        record('I6',len(bibs)==1 and prefok and regok and bibok,{'bibliography_count':len(bibs),'trailing_bibliography':bibok,'preferences':prefdetails,'bibliography_status':'文献表待刷新'})
        allowed={'word/document.xml','docProps/custom.xml','[Content_Types].xml','_rels/.rels'}
        changed=[n for n in set(srcpack)|set(newpack) if n not in allowed and srcpack.get(n)!=newpack.get(n)]
        # Compare non-Zotero custom properties and package registrations as well.
        def strip_registration(parts,name):
            r=E.fromstring(parts[name])
            for n in list(r):
                if (name=='docProps/custom.xml' and (n.get('name') or '').startswith('ZOTERO_PREF_')) or (name=='[Content_Types].xml' and n.get('PartName')=='/docProps/custom.xml') or (name=='_rels/.rels' and n.get('Type','').endswith('/custom-properties')):r.remove(n)
            return [c14n(n) for n in r]
        for n in ('[Content_Types].xml','_rels/.rels'):
            if strip_registration(srcpack,n)!=strip_registration(newpack,n):changed.append(n+' unrelated registrations')
        if 'docProps/custom.xml' in srcpack:
            if strip_registration(srcpack,'docProps/custom.xml')!=strip_registration(newpack,'docProps/custom.xml'):changed.append('unrelated custom properties')
        else:
            if strip_registration(newpack,'docProps/custom.xml'):changed.append('unexpected custom properties')
        layoutok=skeleton(srcview)==skeleton(newview)
        record('I7',not changed and layoutok,{'unchanged_binary_and_other_parts':not changed,'changed_parts':changed,'nontext_xml_structure_exact':layoutok,'source_tables':len(srcview.findall('.//'+q('tbl'))),'candidate_tables':len(newview.findall('.//'+q('tbl'))),'source_images':len(srcview.findall('.//'+q('drawing'))),'candidate_images':len(newview.findall('.//'+q('drawing'))),'section_properties_equal':[c14n(x).decode() for x in srcview.iter(q('sectPr'))]==[c14n(x).decode() for x in newview.iter(q('sectPr'))]})
        source_anchors=pagination_anchors(srcview);candidate_anchors=pagination_anchors(newview)
        record('I7a',source_anchors==candidate_anchors,{'exact_pagination_anchors':source_anchors==candidate_anchors,'source_count':len(source_anchors),'candidate_count':len(candidate_anchors),'source_anchors':source_anchors,'candidate_anchors':candidate_anchors})
        manual=[o for o in occ if any(refmap[i['id']]['status']=='人工保留' for i in o['identifiers'])];manualrows=[]
        gaps_text=Path(gaps).read_text(encoding='utf-8-sig') if gaps else ''
        for o in manual:
            rs=[refmap[i['id']] for i in o['identifiers'] if refmap[i['id']]['status']=='人工保留'];ok=all(r.get('reason') for r in rs) and (not gaps or all(r['id'] in gaps_text for r in rs))
            manualrows.append({'occurrence':o['occurrence'],'marker':o['marker'],'reasons':[r.get('reason') for r in rs],'registered':ok})
            rows.append({'序号':o['occurrence'],'标识':o['marker'],'类型':[i['type'] for i in o['identifiers']],'源位置':[o['paragraph'],o['start'],o['kind']],'新位置':[o['paragraph'],o['start']],'Zotero key':[],'DOI':[],'状态':'人工保留'})
            warnings.append('人工保留：'+o['marker']+'；'+'; '.join(r.get('reason','缺少原因') for r in rs))
        record('I8',all(x['registered'] for x in manualrows),manualrows)
        if manual:evidence['I8']['status']='WARN' if all(x['registered'] for x in manualrows) else 'ERROR'
        record('I9',original.get('source_consistent',True),{'field_source':original['source_kind']=='field','previous_manifest_supplied':previous is not None,'source_consistent':original.get('source_consistent',True)})
    except Exception as e:
        evidence['PARSE']={'status':'ERROR','evidence':type(e).__name__+': '+str(e)}
    for name in ('I1','I2','I3','I4','I5','I6','I7','I7a','I8','I9'):
        if name not in evidence:evidence[name]={'status':'ERROR','evidence':'Not evaluated because a prerequisite failed'}
    return {**({'author_resolutions':author_rows} if author_rows else {}),'source':str(source),'candidate':str(candidate),'source_sha256':sha(source),'candidate_sha256':sha(candidate),'invariants':evidence,'errors':[k for k,v in evidence.items() if v['status']=='ERROR'],'warnings':warnings,'rows':sorted(rows,key=lambda x:x['序号']),'boundary':'机械核对不证明 Word 刷新成功，不证明文献支持正文论断，不证明期刊格式合规。字段未刷新；文献表待刷新；待作者验收。'}

def write_report(out,report):
    out=Path(out);save(out/'核对报告.json',report)
    lines=['# 参考文献核对报告','',report['boundary'],'','ERROR: '+str(len(report['errors'])),'']
    for name,v in report['invariants'].items():lines+=['## '+name+' — '+v['status'],'',json.dumps(v['evidence'],ensure_ascii=False,indent=2),'']
    lines+=['## 逐条对照','','序号 | 标识 | 类型 | 源位置 | 新位置 | Zotero key | DOI | 状态','---|---|---|---|---|---|---|---']
    for row in report['rows']:lines.append(' | '.join(str(row[k]) for k in ('序号','标识','类型','源位置','新位置','Zotero key','DOI','状态')))
    if report.get('author_resolutions'):
        lines+=['','## 作者指定（WARN：作者映射、需作者确认）','']
        lines.extend('- '+row['identifier']+'：'+json.dumps(row['resolution'],ensure_ascii=False) for row in report['author_resolutions'])
    lines+=['','## WARN',*['- '+w for w in report['warnings']]]
    (out/'核对报告.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--snapshot',required=True,type=Path);p.add_argument('--baseline',required=True,type=Path);p.add_argument('--output-dir',required=True,type=Path);p.add_argument('--previous-manifest',type=Path);p.add_argument('--gaps',type=Path)
    a=p.parse_args();r=check(a.source,a.candidate,load(a.manifest),load(a.snapshot),a.baseline,load(a.previous_manifest) if a.previous_manifest else None,a.gaps);write_report(a.output_dir,r);print(json.dumps({'errors':r['errors'],'warnings':r['warnings']},ensure_ascii=False));return bool(r['errors'])
if __name__=='__main__':sys.exit(main())
