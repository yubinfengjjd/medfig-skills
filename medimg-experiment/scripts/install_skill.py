"""Install only the reviewed skill payload into an explicitly supplied NEW path."""
import argparse
from pathlib import Path
import shutil
import json
from check_package import check
from medexp.common import safe_path,require


def install(source,target):
    source=safe_path(source);target=safe_path(target)
    check(source)
    require(target.name=='medimg-experiment','安装目录名必须是medimg-experiment')
    require(not target.exists(),'目标已存在，禁止自动覆盖；先核对旧版与活动实验')
    require(not target.is_relative_to(source) and not source.is_relative_to(target),'安装源与目标不能重叠')
    target.mkdir(parents=True)
    shutil.copyfile(source/'SKILL.md',target/'SKILL.md')
    for name in ['agents','references','assets','scripts']:
        shutil.copytree(source/name,target/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    check(target)
    return {'installed':str(target),'source':str(source),'note':'全局文件安装完成；宿主是否已刷新技能列表需新会话确认'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--target',required=True);a=p.parse_args()
    print(json.dumps(install(a.source,a.target),ensure_ascii=False))
