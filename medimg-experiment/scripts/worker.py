"""One detached monitor, one owned training Job, never launches a new candidate."""
import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sys
import time

from medexp.common import safe_path, inside, read_json, write_json, locked, load_state, save_state, require, number, timestamp
from medexp.process import OwnedProcess, process_identity
from medexp import engine, project, stats


def consume(path, c, record, baseline, cursor, outside_count, last_step, best, final=False):
    if not path.exists():
        require(not final,'最终主要指标日志缺失')
        return cursor,outside_count,last_step,None,best
    require(path.stat().st_size>=cursor,'指标日志被截断，原始证据不完整')
    with path.open('rb') as f:
        f.seek(cursor);raw=f.read()
    chunks=raw.split(b'\n');complete=chunks[:-1]
    require(not final or not chunks[-1].strip(), '指标日志末尾不完整，禁止当作正常结束')
    value=None
    higher=c['primary_metric']['direction']=='higher'
    for line in complete:
        cursor+=len(line)+1
        with (path.parent/'metrics.observed.jsonl').open('ab') as observed:
            observed.write(line+b'\n')
        if not line.strip():continue
        e=json.loads(line.decode('utf-8'))
        require(e.get('run_id')==record['run_id'] and e.get('phase')==record['phase'], '指标运行或阶段标识不匹配')
        require(isinstance(e.get('step'),int) and e['step']>=0,'评估步数格式错误')
        require(isinstance(e.get('metric'),str) and e['metric'],'指标名称缺失')
        require(isinstance(e.get('time'),str),'指标时间缺失')
        dt=datetime.fromisoformat(e['time'].replace('Z','+00:00'))
        require(dt.tzinfo is not None,'指标时间必须带时区')
        number(e.get('value'),'指标事件值')
        if e['metric']==c['primary_metric']['name']:
            require(e['step']>last_step,'主要指标步数重复或倒退')
            value=float(e['value']);last_step=e['step']
            if best is None or (value>best if higher else value<best):best=value
            record['value']=value
            outside_count=engine.metric_anomaly(c,record,value,last_step,baseline,outside_count)
    return cursor,outside_count,last_step,value,best


def check_result(c, directory, record, result, last_value, best):
    """Selection rule, guards and case-level consistency, all against the frozen contract."""
    value=number(result['metrics'][c['primary_metric']['name']],'最终主要指标')
    expect=best if c['primary_metric']['selection']=='best' else last_value
    require(expect is not None and math.isclose(value,expect,rel_tol=1e-10,abs_tol=1e-12),
            f'最终指标与{c["primary_metric"]["selection"]}规则下的原始事件不一致')
    for g in c['guard_metrics']:
        record['guards'][g['name']]=number(result['metrics'].get(g['name']),'护栏指标'+g['name'])
    st=c['verification']['ci']['statistic']
    cases=stats.read_cases(directory/'cases.jsonl',st)
    stats.check_consistency(st,cases,value)
    return value,cases


def run_test(root, test_id):
    """Evaluate each seed run of one candidate with the frozen test command, in a detached checkout."""
    directory=inside(root/'tests',test_id);meta=read_json(directory/'test.json')
    meta.update(worker_pid=os.getpid(),worker_token=process_identity(os.getpid()));write_json(directory/'test.json',meta)
    with locked(root):
        state=load_state(root);c=engine.current_contract(root,state)
        require(state.get('active_test') and state['active_test']['id']==test_id,'测试不再属于当前课题')
        frozen=state['frozen_commit'];test_ids=engine.audit_ids(root,state,'test')
    checkout=directory/'checkout';results=[]
    try:
        project.test_checkout(root,meta['commit'],checkout,frozen,c['scope']['frozen_paths'])
        for run_id in meta['run_ids']:
            out=directory/run_id;out.mkdir()
            run_dir=root/'runs'/run_id;rec=read_json(run_dir/'record.json')
            argv=[str(safe_path(c['environment']['python'])) if a=='{python}' else str(run_dir) if a=='{run_dir}' else str(out) if a=='{output}' else a
                  for a in c['test']['command']]
            env={**os.environ,'PYTHONUTF8':'1','PYTHONUNBUFFERED':'1','PYTHONDONTWRITEBYTECODE':'1','ME_PHASE':'test',
                 'ME_RUN_ID':run_id,'ME_RUN_DIR':str(run_dir),'ME_OUTPUT_DIR':str(out),'ME_CONTRACT_PATH':str(run_dir/'contract.json'),
                 'ME_DEVICE':c['environment']['device'],'TMP':str(out),'TEMP':str(out),'WANDB_MODE':'disabled'}
            owner=OwnedProcess(argv,str(checkout),env,str(out/'test.log'));started=time.monotonic()
            try:
                while owner.poll() is None:
                    require(time.monotonic()-started<c['test']['timeout_seconds'],'测试评估超时')
                    time.sleep(.5)
                code=owner.poll()
            finally:
                owner.close()
            require(code==0,'测试脚本非零退出: '+str(code))
            res=read_json(out/'result.json')
            require(res.get('completed') is True,'测试结果未完成')
            value=number(res['metrics'][c['primary_metric']['name']],'测试主要指标')
            st=c['verification']['ci']['statistic'];cases=stats.read_cases(out/'cases.jsonl',st)
            stats.check_consistency(st,cases,value)
            require(set(cases)==test_ids,'测试逐病例case_id必须与审计登记的test分组完全一致')
            guards={g['name']:number(res['metrics'].get(g['name']),'测试护栏'+g['name']) for g in c['guard_metrics']}
            results.append({'run_id':run_id,'seed':rec['seed'],'value':value,'guards':guards})
        engine.test_finish(root,meta,results)
    except Exception as e:
        engine.test_finish(root,meta,None,type(e).__name__+': '+str(e))
    finally:
        if checkout.exists():
            try:project.test_release(root,checkout)
            except Exception:pass


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True)
    group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--run-id');group.add_argument('--test-id')
    args=parser.parse_args();root=safe_path(args.root)
    if args.test_id:
        return run_test(root,args.test_id)
    directory=inside(root/'runs',args.run_id)
    owner=None;record=None;started=time.monotonic()
    try:
        with locked(root):
            state=load_state(root);require(state['active_run']==args.run_id,'监控运行不再属于当前课题')
            record=read_json(directory/'record.json');c=read_json(directory/'contract.json');cand=read_json(directory/'candidate.json')
            require(project.clean(root) and project.commit(root)==cand['commit'],'后台启动前代码已变更')
            record.update(worker_pid=os.getpid(),worker_token=process_identity(os.getpid()),status='running',started_at=timestamp())
            write_json(directory/'record.json',record)
            remaining=c['budget']['total_seconds']-state['spent_seconds']
            baseline=state['baseline_value']
        argv=[str(safe_path(c['environment']['python'])) if a=='{python}' else str(record['seed']) if a=='{seed}' else a for a in cand['command']]
        env={**os.environ,'PYTHONUTF8':'1','PYTHONUNBUFFERED':'1','PYTHONDONTWRITEBYTECODE':'1',
             'ME_RUN_ID':args.run_id,'ME_PHASE':record['phase'],'ME_OUTPUT_DIR':str(directory),
             'ME_CONTRACT_PATH':str(directory/'contract.json'),'ME_DEVICE':c['environment']['device'],
             'TMP':str(directory/'tmp'),'TEMP':str(directory/'tmp'),'TORCH_HOME':str(directory/'cache'),
             'HF_HOME':str(directory/'cache'),'WANDB_MODE':'disabled'}
        (directory/'tmp').mkdir();(directory/'cache').mkdir()
        owner=OwnedProcess(argv,str(root/'worktree'),env,str(directory/'train.log'))
        record.update(training_pid=owner.pid,training_token=owner.token)
        with locked(root):write_json(directory/'record.json',record)
        cursor=0;outside=0;last_step=-1;last_value=None;best=None
        while True:
            cursor,outside,last_step,value,best=consume(directory/'metrics.jsonl',c,record,baseline,cursor,outside,last_step,best)
            if value is not None:last_value=value
            elapsed=time.monotonic()-started
            record['heartbeat_at']=timestamp();record['elapsed_seconds']=elapsed
            with locked(root):write_json(directory/'record.json',record)
            exitcode=owner.poll()
            if exitcode is not None:break
            require(elapsed<min(c['budget']['run_timeout_seconds'],remaining),'单次或总训练时间预算已达，停止受管任务')
            time.sleep(min(2.0,max(.05,min(c['budget']['run_timeout_seconds'],remaining)-elapsed)))
        # Always close the Job, also when the root exits normally but leaves children.
        owner.close();owner=None
        cursor,outside,last_step,value,best=consume(directory/'metrics.jsonl',c,record,baseline,cursor,outside,last_step,best,final=True)
        if value is not None:last_value=value
        require((directory/'metrics.jsonl').read_bytes()==(directory/'metrics.observed.jsonl').read_bytes(), '主要指标日志被替换，与已观察原始证据不同')
        require(exitcode==0,'训练非零退出: '+str(exitcode))
        result=read_json(directory/'result.json')
        require(result.get('run_id')==args.run_id and result.get('phase')==record['phase'] and result.get('completed') is True,'最终结果身份或完成状态无效')
        value,cases=check_result(c,directory,record,result,last_value,best)
        with locked(root):
            val_ids=engine.audit_ids(root,load_state(root),'val')
        require(set(cases)==val_ids,'验证逐病例case_id必须与审计登记的val分组完全一致')
        engine.metric_anomaly(c,record,value,last_step,baseline,outside,completed=True)
        require(isinstance(result.get('artifacts'),list) and result['artifacts'],'最终结果必须声明必要权重与产物')
        for name in result['artifacts']:
            p=inside(directory,name);require(p.is_file() and p.stat().st_size>0,'声明的产物不存在或为空')
        require(any(Path(x).suffix.lower() in ('.npz','.pt','.pth','.safetensors') for x in result['artifacts']),'缺少必要模型权重')
        require(project.clean(root) and project.commit(root)==record['commit'],'运行期间代码发生变化，结果不绑定已审查版本')
        engine.finish(root,record,value,result,time.monotonic()-started)
    except Exception as e:
        if owner:
            try:owner.terminate();owner.close()
            except Exception:pass
        if record:
            record['elapsed_seconds']=time.monotonic()-started
            with locked(root):
                state=load_state(root)
                if state['active_run']==args.run_id:
                    state['spent_seconds']+=record['elapsed_seconds']
                    engine.incident(root,state,record,'training_or_output',type(e).__name__+': '+str(e))
        else:
            with locked(root):
                state=load_state(root)
                if state['active_run']==args.run_id:
                    engine.incident(root,state,read_json(directory/'record.json'),'monitor_initialization',str(e))


if __name__=='__main__':main()
