"""Collect public identifiers into Zotero; only additive writes, with receipts and readback."""
from __future__ import annotations
import argparse,copy,json,re,shutil,sqlite3,sys,time,urllib.error,urllib.parse,urllib.request,uuid
from datetime import datetime,timezone
from pathlib import Path
from xml.etree import ElementTree as X
from extract_citations import doi_norm,load,save,sha,write_manifest,identifiers
BASE='http://127.0.0.1:23119'
PUBLIC={'www.ebi.ac.uk','eutils.ncbi.nlm.nih.gov','api.crossref.org','export.arxiv.org'}
class StopWrite(RuntimeError):pass
class MetadataConflict(RuntimeError):pass
class Local:
    def __init__(self,key_file=None):
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));self.server=None
        self.key_file=Path(key_file) if key_file else Path.home()/'.medical-sci-references/zotero-local-api-key.json';self.auth=None
    def request(self,path,method='GET',data=None,write=False,content_type='application/json',_reauthorized=False):
        if not path.startswith(('/api/','/connector/')):raise ValueError('Unexpected local path')
        headers={'Zotero-API-Version':'3','X-Zotero-Connector-API-Version':'3','Content-Type':content_type}
        if write:
            if self.auth is None:
                if not self.key_file.exists():raise StopWrite('Credential file absent; author must be present for authorization')
                self.auth=load(self.key_file)
            if not self.server:self.request('/api/')
            headers.update({'Zotero-API-Key':self.auth['key'],'Zotero-Server-ID':self.server})
        body=None if data is None else (data.encode('utf-8') if isinstance(data,str) else json.dumps(data,ensure_ascii=False).encode('utf-8'))
        req=urllib.request.Request(BASE+path,data=body,method=method,headers=headers)
        try:
            with self.opener.open(req,timeout=15) as resp:
                raw=resp.read().decode('utf-8');head=dict(resp.headers)
                if resp.headers.get('Zotero-Server-ID'):self.server=resp.headers['Zotero-Server-ID']
                try:obj=json.loads(raw)
                except ValueError:obj=raw
                return obj,resp.status,head
        except urllib.error.HTTPError as e:
            # Do not print request headers or credential values.
            if write and e.code==401 and not _reauthorized:
                # One authorization retry, no credential-file writes. Caller must have author present.
                auth_headers={'Content-Type':'application/json','Zotero-Server-ID':self.server}
                auth_req=urllib.request.Request(BASE+'/api/local/authorize',data=json.dumps({'appName':'medical-sci-references'}).encode(),method='POST',headers=auth_headers)
                try:
                    with self.opener.open(auth_req,timeout=45) as ar:auth=json.load(ar)
                except Exception:raise StopWrite('Authorization retry failed/denied; no connector downgrade') from None
                if not auth.get('key'):raise StopWrite('Authorization returned no key')
                self.auth=auth;return self.request(path,method,data,write,content_type,True)
            if write and e.code in (401,403,412,428):raise StopWrite('Local API authentication/server identity failed (HTTP '+str(e.code)+'); no connector downgrade') from None
            raise
    def all(self,path):
        rows=[];start=0
        while True:
            sep='&' if '?' in path else '?';page,_,headers=self.request(path+sep+f'limit=100&start={start}')
            if not isinstance(page,list):raise ValueError('API list expected')
            rows+=page;start+=len(page)
            if len(page)<100 or start>=int(headers.get('Total-Results',str(start+1))):return rows
    def items(self):return self.all('/api/users/0/items/top')
    def selected(self):return self.request('/connector/getSelectedCollection','POST',{})[0]
    def probe(self,attempts=3,delay=5):
        history=[]
        for i in range(attempts):
            try:
                root,code,head=self.request('/api/');items,readcode,ih=self.request('/api/users/0/items/top?limit=1');ping,pingcode,_=self.request('/connector/ping')
                selected=self.selected();_,options,_=self.request('/api/users/0/items',method='OPTIONS')
                write_available=False;write_probe='No credentials; connector fallback'
                if self.key_file.is_file():
                    try:
                        _,write_status,_=self.request('/api/users/0/items','POST',[],write=True)
                        write_available=200<=write_status<300;write_probe='Empty array POST, HTTP '+str(write_status)+'; no item submitted'
                    except urllib.error.HTTPError as e:
                        body=e.read().decode('utf-8','replace')
                        if e.code==400 and body.strip()=='No items provided':write_available=True;write_probe='HTTP 400 No items provided (empty array, no side effect)'
                        elif e.code in (404,405,501):write_probe='Local write unavailable: HTTP '+str(e.code)
                        else:raise StopWrite('Unexpected write-capability probe response: HTTP '+str(e.code)) from None
                return {'ready':True,'attempts':history+[{'attempt':i+1,'api':code,'read':readcode,'ping':pingcode}],'version':head.get('X-Zotero-Version'),'library_count':int(ih.get('Total-Results',len(items))),'server_id':self.server,'selected':selected,'credential_present':self.key_file.is_file(),'options_status':options,'local_write_available':write_available,'write_capability':write_probe+'; capability probe is not proof of successful item write'}
            except StopWrite as e:
                return {'ready':False,'auth_error':str(e),'attempts':history,'action':'Stop writing; no automatic connector downgrade'}
            except Exception as e:
                history.append({'attempt':i+1,'error':type(e).__name__+': '+str(e)})
                if i+1<attempts:time.sleep(delay)
        return {'ready':False,'attempts':history,'action':'Record pending Zotero steps; continue offline development. Do not start/restart/close or repair Zotero.'}

def public_get(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in PUBLIC:raise ValueError('Public metadata endpoint not allowlisted')
    # The only query values supplied by callers are public identifiers and API controls.
    req=urllib.request.Request(url,headers={'User-Agent':'medical-sci-references/1.0','Accept':'application/json,application/xml,text/xml'})
    with urllib.request.urlopen(req,timeout=35) as r:return r.read()

def text(el,path):
    n=el.find(path);return ''.join(n.itertext()).strip() if n is not None else ''
def completeness(data):
    required=['title','creators','date']+(['publicationTitle'] if data.get('itemType')=='journalArticle' else [])
    return ['缺少 '+n for n in required if not data.get(n)]+(['缺少 journalAbbreviation（不造缩写）'] if data.get('itemType')=='journalArticle' and not data.get('journalAbbreviation') else [])

def metadata(ident):
    typ,value=ident['type'],ident['value']
    if typ=='PMID':
        url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id='+urllib.parse.quote(value)
        root=X.fromstring(public_get(url));article=root.find('.//PubmedArticle')
        if article is None:raise ValueError('PubMed article not found')
        a=article.find('MedlineCitation/Article');journal=a.find('Journal');date=journal.find('JournalIssue/PubDate');year=text(date,'Year') or text(date,'MedlineDate')[:4]
        creators=[]
        for author in a.findall('AuthorList/Author'):
            last=text(author,'LastName');given=text(author,'ForeName') or text(author,'Initials');literal=text(author,'CollectiveName')
            if last:creators.append({'creatorType':'author','lastName':last,'firstName':given})
            elif literal:creators.append({'creatorType':'author','name':literal})
        doi=next((n.text for n in article.findall('PubmedData/ArticleIdList/ArticleId') if n.get('IdType')=='doi'),'')
        data={'itemType':'journalArticle','title':text(a,'ArticleTitle'),'creators':creators,'date':year,'publicationTitle':text(journal,'Title'),'journalAbbreviation':text(journal,'ISOAbbreviation'),'volume':text(journal,'JournalIssue/Volume'),'issue':text(journal,'JournalIssue/Issue'),'pages':text(a,'Pagination/MedlinePgn') or '-'.join(x for x in (text(a,'Pagination/StartPage'),text(a,'Pagination/EndPage')) if x),'DOI':doi_norm(doi or ''),'ISSN':text(journal,'ISSN'),'language':text(a,'Language'),'extra':'PMID: '+value,'url':'https://pubmed.ncbi.nlm.nih.gov/'+value+'/','libraryCatalog':'PubMed'}
    elif typ=='DOI':
        url='https://api.crossref.org/works/'+urllib.parse.quote(doi_norm(value),safe='');m=json.loads(public_get(url))['message']
        creators=[]
        for a in m.get('author',[]):
            if a.get('family'):creators.append({'creatorType':'author','lastName':a['family'],'firstName':a.get('given','')})
            elif a.get('name'):creators.append({'creatorType':'author','name':a['name']})
        parts=m.get('published',m.get('issued',{})).get('date-parts',[[]])[0]
        preprint=m.get('type')=='posted-content'
        data={'itemType':'preprint' if preprint else 'journalArticle','title':next(iter(m.get('title',[])),''),'creators':creators,'date':'-'.join(str(v).zfill(2) if i else str(v) for i,v in enumerate(parts)),'DOI':doi_norm(m.get('DOI',value)),'url':m.get('URL',''),'libraryCatalog':'Crossref'}
        if not preprint:data.update(publicationTitle=next(iter(m.get('container-title',[])),''),journalAbbreviation=next(iter(m.get('short-container-title',[])),''),volume=m.get('volume',''),issue=m.get('issue',''),pages=m.get('page',m.get('article-number','')),ISSN=next(iter(m.get('ISSN',[])),''),language=m.get('language',''))
        else:data['repository']=next(iter(m.get('institution',[{}])),{}).get('name','')
    elif typ=='arXiv':
        url='https://export.arxiv.org/api/query?id_list='+urllib.parse.quote(value)
        atom='{http://www.w3.org/2005/Atom}';r=X.fromstring(public_get(url));entry=r.find(atom+'entry')
        if entry is None:raise ValueError('arXiv entry missing')
        data={'itemType':'preprint','title':' '.join(text(entry,atom+'title').split()),'creators':[{'creatorType':'author','name':text(a,atom+'name')} for a in entry.findall(atom+'author')],'date':text(entry,atom+'published')[:10],'repository':'arXiv','archiveID':value,'url':'https://arxiv.org/abs/'+value,'extra':'arXiv: '+value,'libraryCatalog':'arXiv'}
        doi=text(entry,'{http://arxiv.org/schemas/atom}doi')
        if doi:data['DOI']=doi_norm(doi)
    else:raise ValueError('URL-only is manual retention')
    warnings=completeness(data)
    if typ=='arXiv' and any('name' in a for a in data.get('creators',[])):warnings.append('arXiv 仅提供作者全名，使用单字段作者，不推断姓/名')
    return {'data':{k:v for k,v in data.items() if v not in ('',None,[])},'endpoint':url,'identifier':ident['id'],'warnings':warnings,'fetched_at':datetime.now(timezone.utc).isoformat()}

def title_norm(s):return ''.join(c for c in s.casefold() if c.isalnum())
def year(s):
    m=re.search(r'\b(?:19|20)\d{2}\b',s or '');return m[0] if m else ''
def match_item(items,ident,meta=None):
    data=meta['data'] if meta else {};doi=doi_norm(data.get('DOI','') or (ident['value'] if ident['type']=='DOI' else ''))
    matches=[x for x in items if doi and doi_norm(x['data'].get('DOI',''))==doi]
    method='DOI'
    if not matches:
        pmid=ident['value'] if ident['type']=='PMID' else next(iter(re.findall(r'PMID:\s*(\d+)',data.get('extra',''))),'')
        matches=[x for x in items if pmid and (str(x['data'].get('PMID',''))==pmid or re.search(r'\bPMID:\s*'+re.escape(pmid)+r'\b',x['data'].get('extra',''),re.I) or re.search(r'(?:pubmed\.ncbi\.nlm\.nih\.gov/|pubmed/|MED/|PMID:\s*)'+re.escape(pmid)+r'(?:\D|$)',x['data'].get('url','')+' '+x['data'].get('libraryCatalog',''),re.I))];method='PMID'
    if not matches and ident['type']=='arXiv':
        matches=[x for x in items if ident['value'] in x['data'].get('url','') or ('arXiv: '+ident['value']) in x['data'].get('extra','')];method='arXiv'
    if not matches and data.get('title') and year(data.get('date','')):
        matches=[x for x in items if title_norm(x['data'].get('title',''))==title_norm(data['title']) and year(x['data'].get('date',''))==year(data['date'])];method='title-year'
    if len(matches)>1:raise MetadataConflict('Multiple Zotero items match '+ident['id']+'; author adjudication required')
    return (matches[0],method) if matches else (None,None)

def equivalent_local_field(old,data,field,meta,source,column,identifier):
    if title_norm(old)==title_norm(data.get(field,'')):return True
    if field=='publicationTitle' and data.get('journalAbbreviation') and title_norm(old)==title_norm(data['journalAbbreviation']):
        warning='期刊全称/权威缩写等价（WARN）：'+json.dumps({'identifier':identifier,'source':str(source),'field':column,'local':old,'full_name':data.get('publicationTitle',''),'abbreviation':data['journalAbbreviation'],'resolution':'Exact authoritative journal abbreviation equivalence'},ensure_ascii=False)
        meta.setdefault('warnings',[]).append(warning)
        return True
    return False

def verify_local_tables(project,ident,meta):
    if not project:return
    # Finalize stores candidate bibliographic fields in a structured manifest.
    for source in Path(project).glob('_process/Finalize/**/assembly_manifest.json'):
        for rec in load(source).get('citation_candidates',[]):
            if rec.get('id')!=ident['id']:continue
            row=rec.get('fields',{});data=meta['data'];diff=[]
            for column,field in (('题名','title'),('期刊','publicationTitle'),('期刊/出处','publicationTitle')):
                old=row.get(column,'').strip('—- ')
                if old and not equivalent_local_field(old,data,field,meta,source,column,ident['id']):diff.append({'field':column,'local':old,'fetched':data.get(field,'')})
            old=row.get('第一作者 年份','')
            if old and year(old) and year(old)!=year(data.get('date','')):diff.append({'field':'year','local':old,'fetched':data.get('date','')})
            if old and data.get('creators'):
                first=data['creators'][0].get('lastName',data['creators'][0].get('name',''))
                if first and title_norm(first) not in title_norm(old):diff.append({'field':'first author','local':old,'fetched':first})
            if diff:raise MetadataConflict(json.dumps({'identifier':ident['id'],'source':str(source),'differences':diff},ensure_ascii=False))
    for path in Path(project).glob('04_manuscript/*/*核查说明.md'):
        lines=path.read_text(encoding='utf-8-sig').splitlines();headers=None
        for line in lines:
            if not line.strip().startswith('|'):headers=None;continue
            cells=[x.strip().strip('`*') for x in line.strip().strip('|').split('|')]
            if any(x in cells for x in ('标识','正文标识')):headers=cells;continue
            if not headers or len(cells)!=len(headers):continue
            row=dict(zip(headers,cells));idtext=row.get('标识',row.get('正文标识',''))
            if ident['id'] not in [x['id'] for x in identifiers(idtext)]:continue
            data=meta['data'];diff=[]
            for column,field in (('题名','title'),('期刊','publicationTitle'),('期刊/出处','publicationTitle')):
                old=row.get(column,'').strip('—- ')
                if old and not equivalent_local_field(old,data,field,meta,path,column,ident['id']):diff.append({'field':column,'local':old,'fetched':data.get(field,'')})
            old=row.get('第一作者 年份','')
            if old and year(old) and year(old)!=year(data.get('date','')):diff.append({'field':'year','local':old,'fetched':data.get('date','')})
            if old and data.get('creators'):
                family=data['creators'][0].get('lastName',data['creators'][0].get('name',''))
                if family and title_norm(family) not in title_norm(old):diff.append({'field':'first author','local':old,'fetched':family})
            if diff:raise MetadataConflict(json.dumps({'identifier':ident['id'],'source':str(path),'differences':diff},ensure_ascii=False))

def bibtex(data):
    def esc(v):return str(v).replace('\\',r'\textbackslash{}').replace('{',r'\{').replace('}',r'\}').replace('\n',' ')
    authors=[]
    for a in data.get('creators',[]):authors.append('{'+esc(a['name'])+'}' if 'name' in a else esc(a.get('lastName',''))+', '+esc(a.get('firstName','')))
    mapping={'title':data.get('title',''),'author':' and '.join(authors),'year':year(data.get('date','')),'journal':data.get('publicationTitle',data.get('repository','')),'volume':data.get('volume',''),'number':data.get('issue',''),'pages':data.get('pages',''),'doi':data.get('DOI',''),'url':data.get('url',''),'issn':data.get('ISSN',''),'shortjournal':data.get('journalAbbreviation',''),'language':data.get('language','')}
    pmid=re.search(r'PMID:\s*(\d+)',data.get('extra',''))
    if pmid:mapping['pmid']=pmid[1]
    if data.get('archiveID'):mapping.update(eprint=data['archiveID'],archiveprefix='arXiv')
    kind='article' if data['itemType']=='journalArticle' else 'misc'
    return '@'+kind+'{msr'+uuid.uuid4().hex+',\n'+',\n'.join('  '+k+' = {'+(v if k=='author' else esc(v))+'}' for k,v in mapping.items() if v)+'\n}\n'

def write_one(client,data,collection,channel,process,ident):
    """Pre-write receipt, recheck target, one additive POST, then verify by readback."""
    process=Path(process);process.mkdir(parents=True,exist_ok=True)
    # Re-check dedup immediately before the side effect.
    found,method=match_item(client.items(),ident,{'data':data})
    if found:return found,False,{'deduplicated_before_write':True,'match':method}
    receipt={'identifier':ident['id'],'channel':channel,'target':collection['data']['name'],'collection_key':collection['key'],'metadata':data,'at':datetime.now(timezone.utc).isoformat(),'state':'planned'}
    plan=process/('write-plan-'+uuid.uuid4().hex+'.json');save(plan,receipt)
    if channel=='A':
        payload=copy.deepcopy(data);payload['collections']=[collection['key']]
        result,code,_=client.request('/api/users/0/items','POST',[payload],write=True)
        receipt.update(http_status=code,response=result)
        if not isinstance(result,dict) or result.get('failed') or not (result.get('successful') or result.get('success')):
            receipt['state']='failed';save(plan,receipt);raise StopWrite('API did not confirm an added item; see receipt')
    else:
        selected=client.selected();receipt['selected_before_write']=selected;save(plan,receipt)
        print(json.dumps({'connector_target':selected.get('name'),'id':selected.get('id'),'expected':collection['data']['name']},ensure_ascii=False),flush=True)
        if selected.get('name')!=collection['data']['name'] or selected.get('libraryID')!=1 or not selected.get('editable') or not selected.get('id') or (collection.get('internal_id') is not None and selected.get('id')!=collection['internal_id']):raise StopWrite('Connector target mismatch; stop and ask author to select target collection')
        result,code,_=client.request('/connector/import?session='+uuid.uuid4().hex,'POST',bibtex(data),content_type='text/plain');receipt.update(http_status=code,response=result)
    save(plan,receipt)
    # Do not retry the POST: a lost response may still have created an item.
    for attempt in range(10):
        found,method=match_item(client.items(),ident,{'data':data})
        if found:
            if collection['key'] not in found['data'].get('collections',[]):raise StopWrite('Readback item is outside target collection')
            receipt.update(state='verified',key=found['key'],match=method);save(plan,receipt);return found,True,receipt
        time.sleep(1)
    raise StopWrite('Write response received but no item verified; reconcile before retry')

def integer_ids(sqlite_path,work_dir):
    work=Path(work_dir).resolve()
    if work.name!='_tmp':raise ValueError('--work-dir must name an explicit _tmp directory')
    dst=work/('zotero-readonly-'+uuid.uuid4().hex);dst.mkdir(parents=True)
    source=Path(sqlite_path)
    for suffix in ('','-wal','-shm'):
        p=Path(str(source)+suffix)
        if p.exists():shutil.copy2(p,dst/p.name)
    cp=dst/source.name
    with sqlite3.connect(cp.as_uri()+'?mode=ro',uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite copy integrity check failed')
        rows=db.execute('SELECT key,itemID FROM items WHERE libraryID=1').fetchall()
        cols=dict(db.execute('SELECT key,collectionID FROM collections WHERE libraryID=1').fetchall())
    result=dict(rows);result['__collection_ids__']=cols;return result

def csl_item(client,item,iid,resolved):
    csl=client.request('/api/users/0/items/'+item['key']+'?format=csljson')[0]
    if isinstance(csl,list):
        if len(csl)!=1:raise ValueError('Single-item CSL expected')
        csl=csl[0]
    uri=csl['id']
    if not re.fullmatch(r'https?://zotero\.org/users/(?:\d+|local/[^/]+)/items/'+re.escape(item['key']),str(uri)):raise ValueError('Unexpected Zotero URI')
    csl['id']=iid
    if item['data']['itemType']=='journalArticle':
        csl.pop('URL',None);csl.pop('accessed',None)
    return {'key':item['key'],'raw':item['data'],'citation_item':{'id':iid,'uris':[uri],'itemData':csl},'resolved_identifiers':resolved}

def author_resolutions(resolve_file,refs,items):
    """Validate exact author mappings and all used targets before any additive write."""
    if resolve_file is None:return {},{}
    path=Path(resolve_file).resolve();document=load(path)
    if not isinstance(document,dict) or not isinstance(document.get('mapping'),dict):raise StopWrite('Mapping file must contain a mapping object')
    if not isinstance(document.get('note',''),str):raise StopWrite('Mapping note must be text')
    wanted={r['id'] for r in refs if r['type']=='URL'};canonical={};collection=document.get('collection_key')
    if collection is not None and (not isinstance(collection,str) or not re.fullmatch(r'[A-Z0-9]{8}',collection)):raise StopWrite('Mapping collection_key must be an 8-character Zotero key')
    compact=lambda value:''.join(value.split()).casefold()
    for original,entry in document['mapping'].items():
        if not isinstance(original,str) or original!=original.strip():raise StopWrite('Mapping 标识空白不一致')
        bare=original.startswith(('https://','http://'));identifier='URL: '+original if bare else original
        if not identifier.startswith('URL: ') or not identifier[5:].startswith(('https://','http://')) or any(c.isspace() for c in identifier[5:]):raise StopWrite('Mapping 标识必须与清单精确匹配（URL: 前缀或裸URL）')
        if identifier in canonical:raise StopWrite('Mapping has duplicate canonical identifier: '+identifier)
        if not isinstance(entry,dict) or not isinstance(entry.get('note',''),str):raise StopWrite('Mapping entries and note have invalid types')
        if ('item_key' in entry)==('identifier' in entry):raise StopWrite('Mapping entry needs exactly one item_key or identifier')
        canonical[identifier]=(entry,bare)
        if identifier not in wanted and any(compact(identifier)==compact(actual) for actual in wanted):raise StopWrite('Mapping 标识大小写/空白不一致：'+identifier)
    result={}
    for identifier in wanted:
        if identifier not in canonical:continue
        entry,bare=canonical[identifier]
        if 'item_key' in entry:
            key=entry['item_key']
            if not isinstance(key,str) or not re.fullmatch(r'[A-Z0-9]{8}',key):raise StopWrite('Invalid mapping item_key: '+str(key))
            candidates=[item for item in items if item['key']==key]
        else:
            alternate=entry['identifier']
            if not isinstance(alternate,dict) or alternate.get('type') not in ('DOI','PMID','arXiv','URL') or not isinstance(alternate.get('value'),str):raise StopWrite('Invalid alternate mapping identifier')
            ident={**alternate,'id':alternate['type']+': '+alternate['value']}
            if ident['type']=='URL':candidates=[item for item in items if item['data'].get('url')==ident['value']]
            else:
                item,_=match_item(items,ident);candidates=[item] if item else []
            key=candidates[0]['key'] if len(candidates)==1 else str(alternate)
        if len(candidates)!=1:raise StopWrite('Author mapping item key does not exist or is ambiguous: '+key)
        found=candidates[0]
        if collection and collection not in found['data'].get('collections',[]):raise StopWrite('Author mapping item '+key+' is outside declared collection '+collection)
        note='；'.join(n for n in (document.get('note',''),entry.get('note','')) if n)
        resolution={'source':'作者映射','file':str(path),'note':note,'item_key':key}
        warnings=['作者映射、需作者确认：'+json.dumps(resolution,ensure_ascii=False)]
        if bare:warnings.append('作者映射键为裸URL：仅补充固定 URL: 前缀；URL其余部分逐字符匹配')
        result[identifier]={'item':found,'resolution':resolution,'warnings':warnings}
    return result,{'file':str(path),'collection_key':collection}

def reports(process,manifest,report):
    process=Path(process);write_manifest(process,manifest);save(process/'zotero写入报告.json',report)
    (process/'zotero写入报告.md').write_text('# Zotero 写入报告\n\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n\n撤销仅由作者决定：在 Zotero 按本报告新增 key 定位测试条目，确认后手动移除；脚本不自动删除。\n',encoding='utf-8')
    lines=['# 缺口与人工清单','']
    for r in manifest['references']:
        if r.get('status')!='作者指定' and (r.get('reason') or r.get('warnings')):lines.append('- '+r['id']+'：'+r.get('reason','')+'；'+'；'.join(r.get('warnings',[]))+'。建议：人工核查元数据或入库原因；保留原标识。')
    mapped=[r for r in manifest['references'] if r.get('status')=='作者指定']
    if mapped:
        lines+=['','## 已由作者映射','']
        for r in mapped:lines.append('- '+r['id']+'：作者映射、需作者确认；'+json.dumps(r['resolution'],ensure_ascii=False)+'；'+'；'.join(r.get('warnings',[])))
    (process/'缺口与人工清单.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def collect(manifest,process,collection_name,channel='auto',key_file=None,sqlite_path=None,work_dir=None,project=None,allow_create=False,authorization=None,resolve_file=None):
    process=Path(process);process.mkdir(parents=True,exist_ok=True)
    if project:
        from inject_zotero_fields import gate
        gate(project,authorization)
    client=Local(key_file);probe=client.probe()
    report={'probe':probe,'target':collection_name,'channel':channel,'results':[],'added_keys':[],'status':'pending'}
    reports(process,manifest,report)
    if not probe['ready']:return report
    items=client.items();save(process/'library-before.json',items)
    try:
        author_map,map_info=author_resolutions(resolve_file,manifest['references'],items)
    except (ValueError,OSError,StopWrite,MetadataConflict) as e:
        report.update(status='stopped',error=type(e).__name__+': '+str(e));reports(process,manifest,report);raise
    if resolve_file is not None:report['resolve_file']=map_info['file']

    collections=client.all('/api/users/0/collections');matches=[c for c in collections if c['data']['name']==collection_name and not c['data'].get('parentCollection')]
    if len(matches)>1:raise StopWrite('Multiple top-level collections have target name')
    if author_map and map_info.get('collection_key') and (not matches or matches[0]['key']!=map_info['collection_key']):
        message='Author mapping declared collection does not match selected target collection'
        report.update(status='stopped',error=message);reports(process,manifest,report);raise StopWrite(message)
    chosen=channel if channel!='auto' else ('A' if probe.get('local_write_available') else 'B');report['channel']=chosen
    if not matches:
        if not allow_create or chosen!='A':raise StopWrite('Target collection missing; ask author or explicitly allow creation')
        # Development callers never enable this; normal installed use can create a project collection.
        result,_,_=client.request('/api/users/0/collections','POST',[{'name':collection_name,'parentCollection':False}],write=True)
        matches=[c for c in client.all('/api/users/0/collections') if c['data']['name']==collection_name and not c['data'].get('parentCollection')]
        if len(matches)!=1:raise StopWrite('Created collection not verified')
    collection=matches[0];report['collection_key']=collection['key']
    collection['internal_id']=integer_ids(sqlite_path or Path.home()/'Zotero/zotero.sqlite',work_dir or process/'_tmp')['__collection_ids__'].get(collection['key'])
    if collection['internal_id'] is None:raise StopWrite('Target collection internal ID missing from SQLite snapshot')
    if chosen=='B':
        selected=client.selected();report['selected']=selected;reports(process,manifest,report)
        print(json.dumps({'connector_target':selected.get('name'),'expected':collection_name},ensure_ascii=False),flush=True)
        if selected.get('name')!=collection_name or selected.get('libraryID')!=1 or not selected.get('editable') or not selected.get('id') or selected.get('id')!=collection['internal_id']:raise StopWrite('B channel target mismatch; stop and report')
    refs=manifest['references'];resolved={};selecteditems={}
    try:
        for r in refs:
            if r['type']=='URL':
                if r['id'] not in author_map:
                    if r.get('status')=='作者指定':
                        for field in ('resolution','key','match','warnings'):r.pop(field,None)
                    r.update(status='人工保留',reason='URL-only 不自动抓取');continue
                mapped=author_map[r['id']];found=mapped['item'];resolution=copy.deepcopy(mapped['resolution'])
                r.update(status='作者指定',key=found['key'],match='author-map',reason='',resolution=resolution,warnings=list(mapped['warnings']))
                selecteditems[found['key']]=found;resolved.setdefault(found['key'],[]).append(r['id'])
                report.setdefault('author_resolutions',[]).append({'identifier':r['id'],'resolution':resolution,'level':'WARN'})
                report['results'].append({'identifier':r['id'],'status':'作者指定','key':found['key'],'match':'author-map','write_receipt':None,'resolution':resolution,'warnings':r['warnings']})
                reports(process,manifest,report);continue

            meta=None
            # DOI first needs PMID->DOI resolution for libraries without PMID. Use public ID only.
            try:
                meta=metadata(r);save(process/('metadata-'+str(r['first_occurrence'])+'-'+r['type']+'.json'),meta);verify_local_tables(project,r,meta);save(process/('metadata-'+str(r['first_occurrence'])+'-'+r['type']+'.json'),meta)
                r['warnings']=meta['warnings']
            except MetadataConflict:raise
            except Exception as e:
                found,method=match_item(items,r)
                if not found:r.update(status='人工保留',reason='元数据获取失败：'+type(e).__name__+': '+str(e));reports(process,manifest,report);continue
                r.setdefault('warnings',[]).append('公开元数据请求失败；仅复用标识直接匹配的库条目：'+type(e).__name__)
            found,method=match_item(items,r,meta)
            added=False;receipt=None
            if not found:
                if any(w.startswith('缺少 '+x) for w in meta['warnings'] for x in ('title','creators','date','publicationTitle')):
                    r.update(status='人工保留',reason='必填元数据缺失；不臆造条目');reports(process,manifest,report);continue
                found,added,receipt=write_one(client,meta['data'],collection,chosen,process,r);method=receipt.get('match','DOI');items=client.items()
            r.update(status='新增' if added else '既有',key=found['key'],match=method,reason='')
            if method=='title-year':r.setdefault('warnings',[]).append('按题名匹配，需人工确认')
            selecteditems[found['key']]=found;resolved.setdefault(found['key'],[]).append(r['id'])
            if meta and meta['data'].get('extra') and found['data'].get('PMID'):
                r.setdefault('warnings',[]).append('Zotero 10 将提交的 Extra PMID 规范化到原生 PMID 字段')
            if meta:
                for field in ('title','date','publicationTitle','pages','volume','issue'):
                    if meta['data'].get(field) and found['data'].get(field)!=meta['data'][field]:
                        r.setdefault('warnings',[]).append('既有库元数据与公开记录不同：'+field+'；库='+str(found['data'].get(field,''))+'；公开='+str(meta['data'][field]))
            if added:report['added_keys'].append(found['key'])
            report['results'].append({'identifier':r['id'],'status':r['status'],'key':found['key'],'match':method,'write_receipt':receipt,'warnings':r.get('warnings',[])})
            reports(process,manifest,report)
        ids=integer_ids(sqlite_path or Path.home()/'Zotero/zotero.sqlite',work_dir or process/'_tmp')
        snapshot={'items':[csl_item(client,item,ids[key],resolved[key]) for key,item in selecteditems.items()],'captured_at':datetime.now(timezone.utc).isoformat(),'read_path':'local API + copied sqlite/wal/shm (mode=ro) for integer itemID'}
        save(process/'zotero条目快照.json',snapshot)
        after=client.items();save(process/'library-after.json',after);beforekeys={x['key']:x['data'] for x in load(process/'library-before.json')};afterkeys={x['key']:x['data'] for x in after}
        report['existing_items_unchanged']=all(afterkeys.get(k)==v for k,v in beforekeys.items())
        if not report['existing_items_unchanged']:raise StopWrite('Existing library data changed during run; investigate, do not modify library')
        categories=('既有','新增','作者指定','人工保留') if any(r['status']=='作者指定' for r in refs) else ('既有','新增','人工保留')
        report['counts']={s:sum(r['status']==s for r in refs) for s in categories};report['status']='collected; stop for author approval before injection';reports(process,manifest,report);return report
    except Exception as e:
        report['status']='stopped';report['error']=type(e).__name__+': '+str(e);reports(process,manifest,report);raise

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('probe','collect'));p.add_argument('--manifest',type=Path);p.add_argument('--output-dir',required=True,type=Path);p.add_argument('--collection');p.add_argument('--channel',choices=('auto','A','B'),default='auto');p.add_argument('--key-file',type=Path);p.add_argument('--sqlite',type=Path);p.add_argument('--work-dir',type=Path);p.add_argument('--project-root',type=Path);p.add_argument('--allow-create-collection',action='store_true');p.add_argument('--authorization',type=Path);p.add_argument('--resolve-file',type=Path)
    a=p.parse_args()
    if a.mode=='probe':r=Local(a.key_file).probe();save(a.output_dir/'就绪探测.json',r)
    else:
        if not a.manifest:raise ValueError('--manifest required')
        name=a.collection
        if not name and a.project_root:
            title=next((l[2:].strip() for l in (a.project_root/'PROJECT.md').read_text(encoding='utf-8-sig').splitlines() if l.startswith('# ')),None);name=title
        if not name:raise ValueError('Standalone use requires explicit --collection')
        r=collect(load(a.manifest),a.output_dir,name,a.channel,a.key_file,a.sqlite,a.work_dir,a.project_root,a.allow_create_collection,a.authorization,a.resolve_file)
    print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r.get('ready',True) and r.get('probe',{}).get('ready',True) else 2
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,StopWrite,MetadataConflict) as e:print(str(e),file=sys.stderr);sys.exit(1)
