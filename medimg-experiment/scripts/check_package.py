"""Dependency-free checks for the deliberately small skill metadata subset.

This is NOT the official PyYAML-based quick_validate and does not claim to
validate arbitrary YAML. It accepts only the simple mappings shipped here.
"""
import json
from pathlib import Path
import re
import sys


def check(root):
    root=Path(root).resolve();text=(root/'SKILL.md').read_text(encoding='utf-8')
    match=re.match(r'^---\n(.*?)\n---\n',text,re.S)
    if not match:raise ValueError('Missing simple frontmatter')
    meta={}
    for line in match[1].splitlines():
        key,sep,value=line.partition(':')
        if not sep or key not in ['name','description'] or not value.strip():raise ValueError('Unsupported/empty frontmatter field')
        meta[key]=value.strip()
    if set(meta)!=set(['name','description']) or meta['name']!='medimg-experiment':raise ValueError('Skill identity mismatch')
    if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',meta['name']) or len(meta['description'])>1024:raise ValueError('Skill metadata invalid')
    if '[TODO:' in text:raise ValueError('Unfinished entrypoint')
    files=[root/'SKILL.md',*(root/'references').glob('*.md')]
    for file in files:
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
            if '://' not in link and not link.startswith('#'):
                path=(file.parent/link.split('#')[0]).resolve()
                if not path.is_relative_to(root) or not path.exists():raise ValueError('Broken local reference: '+link)
    yaml=(root/'agents'/'openai.yaml').read_text(encoding='utf-8')
    for line in yaml.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        if not re.fullmatch(r'(?:interface|policy):|  (?:display_name|short_description|default_prompt): ".*"|  allow_implicit_invocation: true',line):
            raise ValueError('Unsupported generated metadata line: '+line)
    if '$medimg-experiment' not in yaml or 'allow_implicit_invocation: true' not in yaml:raise ValueError('Invocation metadata missing')
    json.loads((root/'assets'/'contract-template.json').read_text(encoding='utf-8'))
    for name in ['controller.py','worker.py','medexp/process.py','medexp/stats.py']:
        if not (root/'scripts'/name).is_file():raise ValueError('Missing runtime file: '+name)
    for name in ['synth_data.py','audit_split.py','evaluate_test.py','model.py','train.py']:
        if not (root/'assets'/'synthetic'/name).is_file():raise ValueError('Missing demo file: '+name)
    return {'valid':True,'validator':'dependency-free generated-metadata subset + resource links; not official quick_validate',
            'name':meta['name'],'references_checked':len(files),'implicit_discovery':True}


if __name__=='__main__':
    try:print(json.dumps(check(sys.argv[1]),ensure_ascii=False))
    except Exception as e:print(json.dumps({'valid':False,'error':str(e)},ensure_ascii=False));sys.exit(1)
