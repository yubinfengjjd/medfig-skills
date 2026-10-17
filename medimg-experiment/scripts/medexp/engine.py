import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from .common import require, safe_path, inside, read_json, write_json, locked, load_state, save_state, timestamp, GateError
from .contract import validate, matrix_entry
from . import project, stats

REVIEWERS = ('independent-subagent', 'codex-independent', 'claude-independent')
BUSY = ('running', 'testing', 'awaiting_report', 'reported', 'awaiting_direction')


def current_contract(root, state):
    return read_json(root/'plans'/f'contract-{state["revision"]:03d}.json')


def init(root, contract_path):
    c = validate(read_json(contract_path))
    for data in c['data']['paths']:
        require(not root.is_relative_to(safe_path(data)), '实验输出不能写入原数据目录')
    require(shutil.disk_usage(root.parent if root.parent.exists() else root.anchor).free >= c['environment']['min_free_bytes'], '实验盘空间不足')
    project.prepare(root, c)
    (root/'plans').mkdir();(root/'runs').mkdir();(root/'candidates').mkdir();(root/'tests').mkdir()
    for directory in ['failures', 'rejections', 'negative-results', 'reviews', 'stable', 'audit']:
        (root/'evidence'/directory).mkdir(parents=True)
    shutil.copyfile(safe_path(c['plan_path']), root/'plans'/'original.md')
    write_json(root/'plans'/'contract-001.json', c)
    state = {'schema_version': 2, 'study_id': c['study_id'], 'mode': c['mode'], 'revision': 1, 'approved': False,
             'status': 'awaiting_confirmation', 'stage': c['stages'][0], 'stable': None, 'baseline_stable': None,
             'frozen_commit': None, 'active_run': None, 'active_test': None, 'pending_incident': None,
             'audit': None, 'matrix_done': {}, 'tests': [], 'test_looks': 0,
             'spent_seconds': 0, 'candidate_count': 0, 'no_improvement': 0,
             'baseline_value': None, 'verification_source': None, 'created_at': timestamp()}
    save_state(root, state, 'initialized')
    write_plan(root, state, '初始化；原始计划未修改')
    return state


def write_plan(root, state, reason):
    path = root/'plans'/f'effective-{state["revision"]:03d}.md'
    text = f'# 有效实验计划 v{state["revision"]}\n\n'
    text += f'模式：{state["mode"]}；状态：{state["status"]}；阶段：{state["stage"]}\n\n'
    text += f'修订原因：{reason}\n\n原始计划：original.md（保留不覆盖）。\n'
    text += f'执行规则：contract-{state["revision"]:03d}.json\n'
    text += '\n当前有效稳定方法：'+(state['stable']['candidate_id'] if state.get('stable') else '尚未建立')+'\n'
    if state.get('matrix_done'):text += '已完成矩阵条目：'+', '.join(sorted(state['matrix_done']))+'\n'
    text += f'测试集查看次数（全部版本累计）：{state.get("test_looks", 0)}\n'
    text += '拒绝候选、失败及有效负结果分别保存在evidence目录；不纳入有效代码，证据仍保留。\n'
    if state.get('direction'):text += '\n用户选定方向：' + state['direction'] + '\n'
    path.write_text(text, encoding='utf-8')
    with (root/'plans'/'revisions.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'revision': state['revision'], 'reason': reason, 'time': timestamp(), 'status': state['status']}, ensure_ascii=False)+'\n')
def approve(root, statement):
    require(statement.strip(), '必须记录用户对契约、预算与运行范围的明确确认')
    with locked(root):
        state = load_state(root)
        require(state['status'] == 'awaiting_confirmation', '当前不在契约确认阶段')
        validate(current_contract(root, state))
        state['approved'] = True;state['status'] = 'ready'
        write_json(root/'plans'/f'approval-{state["revision"]:03d}.json',
                   {'user_statement': statement, 'time': timestamp(), 'identity_assurance': 'caller-recorded'})
        save_state(root, state, 'contract_approved')
        write_plan(root,state,'用户确认契约及预算；先做划分审计，再进入第一个候选')
    return state


def frozen_hashes(root, c):
    out = {}
    for name in c['scope']['frozen_paths']:
        require(inside(root/'worktree', name).is_file(), '固定评价文件尚未建立: ' + name)
        out[name] = project.git(root/'worktree', 'hash-object', name)
    return out


def audit(root):
    """Run the frozen split-audit script before the first snapshot; check disjoint groups."""
    with locked(root):
        state = load_state(root);c = current_contract(root, state)
        require(state['approved'] and state['status'] == 'ready' and state['active_run'] is None, '契约未确认或当前不可审计')
        require(state['frozen_commit'] is None, '评价文件已冻结；划分审计只能在首个候选快照前运行，变更划分须建新课题')
        hashes = frozen_hashes(root, c)
        out = root/'evidence'/'audit'/f'audit-{uuid.uuid4().hex[:8]}.json'
        argv = [str(safe_path(c['environment']['python'])) if a == '{python}' else str(out) if a == '{output}' else a
                for a in c['split_audit']['command']]
        env = {**os.environ, 'PYTHONUTF8': '1', 'ME_PHASE': 'audit', 'ME_CONTRACT_PATH': str(root/'plans'/f'contract-{state["revision"]:03d}.json')}
        r = subprocess.run(argv, cwd=str(root/'worktree'), capture_output=True, text=True, encoding='utf-8', errors='replace',
                           timeout=c['split_audit']['timeout_seconds'], env=env, creationflags=0x08000000 if os.name == 'nt' else 0)
        (out.with_suffix('.log')).write_text(r.stdout[-20000:] + '\n--- stderr ---\n' + r.stderr[-20000:], encoding='utf-8')
        require(r.returncode == 0, '划分审计脚本失败: ' + r.stderr[-1000:])
        require(frozen_hashes(root, c) == hashes, '审计期间固定文件被改动')
        a = read_json(out)
        require(a.get('group_unit') == c['data']['group_unit'], '审计group_unit与契约不一致')
        splits = a.get('splits')
        need = ['train', 'val'] + (['test'] if c['test']['policy'] == 'locked' else [])
        require(isinstance(splits, dict) and all(k in splits for k in need), '审计必须包含划分: ' + '/'.join(need))
        seen = {}
        summary = {}
        for name, s in splits.items():
            ids = s.get('group_ids')
            require(isinstance(ids, list) and ids and all(isinstance(i, str) and i for i in ids), f'{name}缺少group_ids')
            require(len(ids) == len(set(ids)), f'{name}内group_ids重复')
            for i in ids:
                require(i not in seen, f'分组单位跨划分泄漏: {i} 同时在 {seen.get(i)} 与 {name}')
                seen[i] = name
            counts = s.get('class_counts')
            require(isinstance(counts, dict) and counts and all(isinstance(v, int) and v >= 0 for v in counts.values()), f'{name}缺少class_counts')
            summary[name] = {'groups': len(ids), 'class_counts': counts}
        record = {'path': str(out), 'frozen_hashes': hashes, 'summary': summary, 'group_unit': a['group_unit'],
                  'passed': True, 'time': timestamp(), 'note': '只证明登记的分组单位跨划分不重叠；标签质量与重复图像另需审查'}
        state['audit'] = record
        save_state(root, state, 'split_audit_passed')
    return record


def audit_ids(root, state, split):
    return set(read_json(state['audit']['path'])['splits'][split]['group_ids'])
def candidate(root, ident, phase, command_path, description, entry=None):
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', ident) is not None, '候选标识无效')
    require(description.strip(), '必须说明候选假设与改动')
    with locked(root):
        state = load_state(root);c = current_contract(root, state)
        require(state['active_run'] is None and state['status'] in ('ready', 'verification_required'), '未确认、异常、测试中、等待方向或运行时不得建立新候选')
        require(state.get('audit') and state['audit']['passed'], '先运行audit完成划分审计')
        require(phase == state['stage'], '候选阶段与批准计划顺序不一致')
        if c['mode'] == 'matrix':
            require(entry and matrix_entry(c, entry), 'matrix模式须用--entry指定契约中的条目')
            require(entry not in state['matrix_done'], '该矩阵条目本版本已完成，不重复建立')
            for existing in (root/'candidates').glob('*.json'):
                old = read_json(existing)
                require(not (old['revision'] == state['revision'] and old.get('entry') == entry and old['runs']),
                        '该条目已有运行中的候选；补跑seed请用原候选，异常重试走恢复流程')
        else:
            require(entry is None, 'search模式不使用--entry')
        path = root/'candidates'/f'{ident}.json'
        require(not path.exists(), '候选标识已存在，证据不可覆盖')
        command = read_json(command_path)
        validate_command(root, c, command)
        if state['frozen_commit'] is None:
            require(frozen_hashes(root, c) == state['audit']['frozen_hashes'], '固定文件与划分审计时的版本不同；重新运行audit')
        sha = project.snapshot(root, c, state['frozen_commit'], phase)
        for existing in (root/'candidates').glob('*.json'):
            old = read_json(existing)
            require(not (old['revision']==state['revision'] and old['phase']==phase and old['commit']==sha and old['command']==command and old.get('entry')==entry),
                    '相同代码、参数和阶段的候选已存在；使用原候选完成不同seed，不能换名称重试')
        if state['frozen_commit'] is None:
            state['frozen_commit'] = sha
        if phase == 'verify':
            source = read_json(root/'candidates'/f'{state["verification_source"]}.json')
            require(sha == source['commit'] and command == source['command'], '正式复核必须使用达标探索候选的同一代码与命令；仅seed变化')
        record = {'id': ident, 'phase': phase, 'entry': entry, 'revision': state['revision'], 'commit': sha,
                  'command': command, 'description': description, 'review': None, 'runs': [], 'counted': False}
        write_json(path, record)
        project.git(root/'worktree', 'update-ref', 'refs/medexp/candidates/'+ident, sha)
        save_state(root, state, 'candidate_snapshotted')
    return record


def validate_command(root, c, command):
    require(isinstance(command, list) and len(command) >= 2 and all(isinstance(a, str) and a for a in command), '命令必须为非空argv数组，不使用shell')
    require(command[0] == '{python}', '必须使用契约解释器占位符{python}')
    require(command[1].endswith('.py') and not command[1].startswith('-'), '必须直接运行受管Python脚本')
    require(inside(root/'worktree', command[1]).is_file(), '训练脚本不在受管工程')
    switches=[a for a in command[2:] if a=='--seed' or a.startswith('--seed=')]
    require(switches==['--seed'] and command.count('{seed}') == 1 and command.index('--seed')+1 < len(command)
            and command[command.index('--seed')+1] == '{seed}', 'seed必须由复核协议注入一次，禁止重复或--seed=覆盖')
    for arg in command[2:]:
        if arg.startswith('--'):
            require(arg.split('=')[0] in c['scope']['parameters']+['--seed'], '命令参数未获准: '+arg)
        require('{' not in arg or arg == '{seed}', '不支持其他命令占位符')


def review(root, record_path):
    r = read_json(record_path)
    with locked(root):
        state = load_state(root)
        require(state['active_run'] is None, '训练过程中不得修改审查记录')
        path = inside(root/'candidates', r['candidate_id']+'.json');cand = read_json(path)
        require(cand['revision'] == state['revision'] and r.get('commit') == cand['commit'], '审查版本不匹配')
        require(project.clean(root) and project.commit(root) == cand['commit'], '审查后代码已变更')
        require(r.get('reviewer') in REVIEWERS and isinstance(r.get('agent_id'), str) and r['agent_id'].strip(), '必须登记独立只读审查子代理及其ID')
        require(r.get('verdict') in ('pass', 'block') and isinstance(r.get('findings'), list), '审查结论格式无效')
        require(isinstance(r.get('artifacts_read'), list) and r['artifacts_read'], '必须列出实际检查的原始产物')
        for name in r['artifacts_read']:
            require(inside(root/'worktree', name).is_file(), '审查引用的文件不存在')
        r['identity_assurance'] = 'caller-recorded; same-family; not scientific proof'
        cand['review'] = r;write_json(path, cand)
        write_json(root/'evidence'/'reviews'/f'{cand["id"]}-{uuid.uuid4().hex[:8]}.json', r)
        save_state(root, state, 'independent_review_recorded')
    return cand
def environment_check(root, c):
    env = c['environment']
    require(shutil.disk_usage(root).free >= env['min_free_bytes'], '可用空间低于确认的存储余量')
    for p in c['data']['paths']:
        path = safe_path(p)
        require(path.exists() and os.access(path, os.R_OK), '数据不可读取')
    script = ('import json,sys,importlib.metadata as m; '
              'print(json.dumps({"python":sys.version,"dependencies":{k:m.version(k) for k in '+repr(list(env['dependencies']))+'}}))')
    r = subprocess.run([str(safe_path(env['python'])), '-c', script], capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=30,
                       env={**os.environ,'PYTHONUTF8':'1'}, creationflags=0x08000000)
    require(r.returncode == 0, '解释器或依赖不可用；先提出独立环境方案: '+r.stderr[-1000:])
    result = json.loads(r.stdout)
    require(result['dependencies'] == env['dependencies'], '依赖版本与已确认契约不同')
    if env['device'] == 'cuda':
        r = subprocess.run([str(safe_path(env['python'])), '-c', 'import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))'], capture_output=True, text=True, timeout=30, creationflags=0x08000000)
        require(r.returncode == 0, '契约CUDA设备不可用；不自动切换CPU')
        result['gpu'] = r.stdout.strip()
    return result


def budget_stop(state, c, cand):
    if state['spent_seconds'] >= c['budget']['total_seconds']:
        return True
    if c['mode'] == 'search':
        return state['no_improvement'] >= c['budget']['max_no_improvement'] or (
            cand['phase'] == 'explore' and not cand['counted'] and state['candidate_count'] >= c['budget']['max_candidates'])
    return False


def run(root, ident, seed):
    from .process import spawn_detached
    with locked(root):
        state = load_state(root);c = current_contract(root, state)
        require(state['approved'] and state['status'] in ('ready', 'verification_required'), '契约未确认或当前存在待处理状态')
        require(state['active_run'] is None and state.get('active_test') is None, '同一课题仅允许一个受管训练或测试')
        cand = read_json(inside(root/'candidates', ident+'.json'))
        require(cand['revision'] == state['revision'] and cand['phase'] == state['stage'], '候选版本或阶段无效')
        require(cand.get('entry') not in state['matrix_done'], '该矩阵条目本版本已完成')
        require(project.clean(root) and project.commit(root) == cand['commit'], '代码变更导致审查失效')
        require(cand.get('review') and cand['review']['verdict'] == 'pass' and cand['review']['commit'] == cand['commit'], '缺少通过的独立审查')
        require(seed in c['verification']['seeds'], 'seed不在确认的复核协议中')
        for run_id in cand['runs']:
            old = read_json(root/'runs'/run_id/'record.json')
            require(old['seed'] != seed, '同一候选seed不能重复覆盖；重试须走用户恢复流程')
        if budget_stop(state, c, cand):
            state['status'] = 'budget_exhausted';save_state(root,state,'search_stopped_at_budget')
            raise GateError('预算或连续无改善上限已达；目标尚未达成')
        try:
            env_evidence = environment_check(root,c)
        except Exception as e:
            incident(root,state,None,'preflight_environment',str(e))
            raise GateError(str(e))
        run_id = 'r-'+uuid.uuid4().hex[:12];directory = root/'runs'/run_id;directory.mkdir()
        record = {'run_id': run_id, 'candidate_id': ident, 'entry': cand.get('entry'), 'phase': cand['phase'], 'revision': state['revision'],
                  'commit': cand['commit'], 'seed': seed, 'status': 'queued', 'created_at': timestamp(),
                  'environment': env_evidence, 'worker_pid': None, 'worker_token': None,
                  'training_pid': None, 'training_token': None, 'value': None, 'guards': {}}
        write_json(directory/'record.json',record);write_json(directory/'contract.json',c)
        # A reconstructable bundle survives any later working-tree rollback.
        project.git(root/'code','bundle','create',str(directory/'code.bundle'),'refs/medexp/candidates/'+ident)
        write_json(directory/'candidate.json',cand)
        if cand['phase']=='explore' and not cand['counted']:
            state['candidate_count']+=1;cand['counted']=True
        cand['runs'].append(run_id);write_json(root/'candidates'/f'{ident}.json',cand)
        state['active_run']=run_id;state['status']='running';save_state(root,state,'training_reserved')
        worker = Path(__file__).resolve().parents[1]/'worker.py'
        try:
            owner=spawn_detached([sys.executable,str(worker),'--root',str(root),'--run-id',run_id],str(root),str(directory/'monitor.log'))
            record.update(worker_pid=owner['pid'],worker_token=owner['token']);write_json(directory/'record.json',record)
        except Exception as e:
            incident(root,state,record,'worker_start',str(e))
            raise GateError('后台启动失败，已进入等待汇报: '+str(e))
    return record


def incident(root,state,record,kind,detail):
    incident_id = record['run_id'] if record else 'preflight-'+uuid.uuid4().hex[:12]
    payload={'incident_id':incident_id,'run_id':record['run_id'] if record else None,
             'phase':record['phase'] if record else state['stage'],'kind':kind,'detail':detail,
             'value':record.get('value') if record else None,'time':timestamp(),
             'attempted_checks':'仅检查与停止；未自动重试、未回退'}
    write_json(root/'evidence'/f'incident-{incident_id}.json',payload)
    state['active_run']=None;state['pending_incident']=payload;state['status']='awaiting_report'
    if record:
        record['status']='anomaly';record['anomaly']=payload;write_json(root/'runs'/record['run_id']/'record.json',record)
    save_state(root,state,'incident_preserved_waiting_report')


def metric_anomaly(c,record,value,step,baseline,outside_count,completed=False):
    require(math.isfinite(value), '主要指标出现NaN/Inf')
    a=c['anomaly'];phase=record['phase']
    if step < a['warmup_steps'] and not completed:return 0
    # Matrix ablations may legitimately be worse; only search phases use the baseline drop rule.
    if baseline is not None and phase in ('explore', 'verify'):
        drop=(baseline-value) if c['primary_metric']['direction']=='higher' else (value-baseline)
        if a['unit']=='relative':
            require(baseline != 0,'基线为0，不能应用relative异常阈值')
            drop/=abs(baseline)
        require(drop < a['max_drop'],'指标下降触发确认的异常阈值')
    # The final value repeats the selected event, not another evaluation.
    if completed:return outside_count
    bounds=a['reference_ranges'].get(phase)
    outside_count=outside_count+1 if bounds and not bounds[0]<=value<=bounds[1] else 0
    require(outside_count < a['consecutive_outside_range'],'连续指标越出该阶段参考区间')
    return outside_count
def higher(c):
    return c['primary_metric']['direction'] == 'higher'


def guard_violations(c, cand_guards, ref_guards):
    """Both arguments map guard name -> aggregated value. Returns names that degrade too much."""
    out = []
    for g in c['guard_metrics']:
        a, b = cand_guards.get(g['name']), ref_guards.get(g['name'])
        if a is None or b is None:
            out.append(g['name'] + '（缺值）');continue
        worse = (b - a) if g['direction'] == 'higher' else (a - b)
        if worse > g['max_degradation']:
            out.append(f'{g["name"]}恶化{worse:.6g}>{g["max_degradation"]}')
    return out


def summarize(c, root, run_ids):
    records = [read_json(root/'runs'/r/'record.json') for r in run_ids]
    values = [r['value'] for r in records]
    mode = c['verification']['aggregation']
    guards = {}
    for g in c['guard_metrics']:
        gv = [r['guards'].get(g['name']) for r in records]
        guards[g['name']] = None if any(x is None for x in gv) else stats.aggregate(mode, gv, g['direction'] == 'higher')
    return {'run_ids': run_ids, 'seeds': [r['seed'] for r in records], 'value': stats.aggregate(mode, values, higher(c)),
            'values': values, 'sd': stats.seed_sd(values), 'guards': guards}


def run_cases(c, root, run_ids, subdir=None):
    st = c['verification']['ci']['statistic']
    out = []
    for r in run_ids:
        base = root/'runs'/r if subdir is None else root/'tests'/subdir/r
        out.append(stats.read_cases(base/'cases.jsonl', st))
    return out


def paired(c, root, a_ids, b_ids, subdir_a=None, subdir_b=None):
    ci = c['verification']['ci']
    return stats.paired_bootstrap(ci['statistic'], run_cases(c, root, a_ids, subdir_a), run_cases(c, root, b_ids, subdir_b),
                                  higher(c), c['verification']['aggregation'], ci['resamples'], ci['level'], ci['seed'])


def finish(root,record,value,result,elapsed):
    with locked(root):
        state=load_state(root);c=current_contract(root,state)
        require(state['active_run']==record['run_id'],'运行归属已变更，不得提交结果')
        state['spent_seconds']+=elapsed;state['active_run']=None
        record.update(status='completed',value=value,elapsed_seconds=elapsed,finished_at=timestamp(),artifacts=result['artifacts'])
        write_json(root/'runs'/record['run_id']/'record.json',record)
        cand=read_json(root/'candidates'/f'{record["candidate_id"]}.json')
        if record['phase']=='explore':
            baseline=state['baseline_value']
            effect=(value-baseline) if higher(c) else (baseline-value)
            violated=guard_violations(c, record['guards'], state['baseline_stable']['guards'])
            if effect <= 0 or violated:
                write_json(root/'evidence'/'rejections'/f'{record["run_id"]}.json',{**record,'effect':effect,'guard_violations':violated})
                project.restore(root,state['stable']['commit'],record['run_id'])
                state['no_improvement']+=1;state['status']='ready'
                if state['no_improvement']>=c['budget']['max_no_improvement']:state['status']='budget_exhausted'
            else:
                state['no_improvement']=0;state['status']='ready'
                reached=value>=c['primary_metric']['target'] if higher(c) else value<=c['primary_metric']['target']
                if reached and effect>=c['primary_metric']['min_effect']:
                    state['stage']='verify';state['status']='verification_required';state['verification_source']=cand['id']
        else:
            runs=[read_json(root/'runs'/x/'record.json') for x in cand['runs']]
            completed=[r['run_id'] for r in runs if r['status']=='completed']
            if len(completed)<len(c['verification']['seeds']):
                state['status']='verification_required' if record['phase']=='verify' else 'ready'
            else:
                s=summarize(c,root,completed)
                normal=c['verification']['normal_range']
                problems=[]
                if not all(normal[0]<=x<=normal[1] for x in s['values']+[s['value']]):problems.append('seed或聚合值越出正常范围')
                if s['sd']>c['verification']['max_std']:problems.append(f'seed样本标准差{s["sd"]:.6g}超过上限')
                if record['phase']=='verify':
                    base=state['baseline_stable']
                    reached=s['value']>=c['primary_metric']['target'] if higher(c) else s['value']<=c['primary_metric']['target']
                    if not reached:problems.append('聚合值未达target')
                    problems+=guard_violations(c,s['guards'],base['guards'])
                    try:
                        s['ci_vs_baseline']=paired(c,root,completed,base['run_ids'])
                        need=c['primary_metric']['min_effect'] if c['verification']['ci']['lower_bound_rule']=='min_effect' else 0
                        if s['ci_vs_baseline']['ci_low']<need or (need==0 and s['ci_vs_baseline']['ci_low']<=0):
                            problems.append(f'配对CI下限{s["ci_vs_baseline"]["ci_low"]:.6g}未超过{need}')
                    except GateError as e:
                        problems.append('配对bootstrap失败: '+str(e))
                if problems:
                    if record['phase'] in ('verify','matrix'):
                        write_json(root/'evidence'/'negative-results'/f'{record["run_id"]}.json',{**s,'problems':problems,'valid_negative_result':True})
                    incident(root,state,record,'formal_validation','完整复核不满足：'+'；'.join(problems))
                    return
                stable={**s,'commit':cand['commit'],'revision':state['revision'],'verified_at':timestamp(),'candidate_id':cand['id'],'entry':cand.get('entry')}
                write_json(root/'evidence'/'stable'/f'{cand["id"]}.json',stable)
                if record['phase']=='matrix':
                    state['matrix_done'][cand['entry']]=stable
                    state['status']='matrix_complete' if len(state['matrix_done'])==len(c['matrix']['entries']) else 'ready'
                else:
                    state['stable']=stable;project.git(root/'code','update-ref','refs/heads/stable',cand['commit'])
                    if record['phase']=='baseline':
                        state['baseline_stable']=stable;state['baseline_value']=s['value'];state['stage']='explore';state['status']='ready'
                    else:state['status']='accepted'
        if state['status']=='ready' and state['spent_seconds']>=c['budget']['total_seconds']:state['status']='budget_exhausted'
        write_plan(root,state,'运行评估完成：'+record['run_id']+'；结果与有效方法分别登记')
        save_state(root,state,'run_evaluated')
def status(root):
    from .process import is_alive
    with locked(root):
        state=load_state(root)
        if state['active_run']:
            record=read_json(root/'runs'/state['active_run']/'record.json')
            if not record['worker_pid'] and (datetime.now(timezone.utc)-datetime.fromisoformat(record['created_at'])).total_seconds()>10:
                incident(root,state,record,'monitor_registration_missing','监控启动超过10秒仍未登记；禁止迟到进程开始训练，等待汇报')
            if record['worker_pid'] and not is_alive(record['worker_pid'],record['worker_token']):
                # Worker termination closes its kill-on-close Job; preserve partial outputs.
                c=current_contract(root,state)
                observed=record.get('elapsed_seconds',0)
                since=(datetime.now(timezone.utc)-datetime.fromisoformat(record.get('started_at',record['created_at']))).total_seconds()
                estimate=max(observed,min(max(0,since),c['budget']['run_timeout_seconds'],max(0,c['budget']['total_seconds']-state['spent_seconds'])))
                record['elapsed_seconds']=estimate;record['elapsed_seconds_estimated']=True
                record['elapsed_note']='监控丢失后按截至协调时的墙钟上界保守扣预算，受单次与剩余预算限制；不是精确GPU用时'
                state['spent_seconds']+=estimate
                incident(root,state,record,'monitor_lost','监控进程已退出；原始输出保留，未把旧状态当作仍在训练')
        test=state.get('active_test')
        if test:
            meta=read_json(root/'tests'/test['id']/'test.json')
            alive=meta.get('worker_pid') and is_alive(meta['worker_pid'],meta['worker_token'])
            young=(datetime.now(timezone.utc)-datetime.fromisoformat(meta['created_at'])).total_seconds()<=10
            if not alive and not (young and not meta.get('worker_pid')):
                close_test(root,state,meta,None,'测试监控丢失；部分输出保留，本次查看仍计入次数')
        return state


def reported(root,statement):
    require(statement.strip(),'必须先在对话中汇报阶段、异常、数值与排查情况，再记录汇报')
    with locked(root):
        state=load_state(root);require(state['status']=='awaiting_report','当前没有待汇报异常')
        state['report_statement']=statement;state['status']='reported'
        save_state(root,state,'incident_reported_caller_recorded')
    return state


def recover(root):
    with locked(root):
        state=load_state(root)
        if state['status']=='awaiting_direction':return state
        require(state['status']=='reported','必须先汇报，禁止跳过reported记录直接回退')
        issue=state['pending_incident'];anchor=state['stable']['commit'] if state['stable'] else None
        project.restore(root,anchor,issue['incident_id'])
        state['recovery_note']='已回退到已验证稳定版本' if anchor else '暂无可回退目标；仅保全当前代码与证据'
        save_state(root,state,'code_recovery_completed')
        failure={**issue,'recovery_note':state['recovery_note'],'report_statement':state['report_statement'],
                 'rollback_commit':anchor,'code_preserved':True}
        write_json(root/'evidence'/'failures'/f'{issue["incident_id"]}.json',failure)
        save_state(root,state,'failure_recorded')
        state['status']='awaiting_direction';write_plan(root,state,'异常处理完成：'+issue['detail'])
        save_state(root,state,'plan_updated_waiting_direction')
    return state


def resume(root,contract_path,direction,statement):
    require(direction.strip() and statement.strip(),'必须有用户明确选定的修改方向和新契约确认；沉默不能恢复')
    c=validate(read_json(contract_path))
    with locked(root):
        state=load_state(root);require(state['status'] in ('awaiting_direction','budget_exhausted','accepted','matrix_complete'),'仅在等待方向、预算结束或完成后开新版本')
        require(c['study_id']==state['study_id'] and c['mode']==state['mode'],'课题标识与模式不能变更')
        old=current_contract(root,state)
        require(c['code']==old['code'] and c['plan_path']==old['plan_path'],'恢复不重新导入源代码或覆盖原计划')
        same_eval=all(c[k]==old[k] for k in ('data','test','split_audit','task')) and c['scope']['frozen_paths']==old['scope']['frozen_paths']
        require(same_eval, '数据、划分、测试或评价文件变更必须建立新课题工程，不在原循环中混用证据')
        if state['stable']:
            write_json(root/'evidence'/'stable'/f'archived-revision-{state["revision"]}.json',state['stable'])
        carried={}
        if c['mode']=='matrix' and all(c[k]==old[k] for k in ('primary_metric','guard_metrics','verification')):
            for e,done in state['matrix_done'].items():
                if matrix_entry(c,e)==matrix_entry(old,e):carried[e]={**done,'carried_from_revision':done.get('carried_from_revision',state['revision'])}
        state.update(revision=state['revision']+1,approved=True,status='ready',stage=c['stages'][0],stable=None,baseline_stable=None,
                     baseline_value=None,pending_incident=None,spent_seconds=0,candidate_count=0,no_improvement=0,
                     verification_source=None,direction=direction,matrix_done=carried)
        if c['mode']=='matrix' and len(carried)==len(c['matrix']['entries']):state['status']='matrix_complete'
        write_json(root/'plans'/f'contract-{state["revision"]:03d}.json',c)
        write_json(root/'plans'/f'approval-{state["revision"]:03d}.json',{'user_statement':statement,'direction':direction,'identity_assurance':'caller-recorded','time':timestamp()})
        write_plan(root,state,'用户选定新方向；新预算单独登记'+('；沿用未变矩阵条目: '+', '.join(carried) if carried else '，重新建立基线'))
        save_state(root,state,'user_direction_resumed')
    return state
def test_runs(root, state, c, ident):
    """Return the completed run IDs a candidate may be tested with, or raise."""
    if c['mode'] == 'search':
        base, stable = state.get('baseline_stable'), state.get('stable')
        ok = (base and base['candidate_id'] == ident) or (state['status'] == 'accepted' and stable and stable['candidate_id'] == ident)
        require(ok, 'search模式只允许测试本版本已建立的基线，或已accepted的最终版本')
        return (base if base and base['candidate_id'] == ident else stable)['run_ids']
    require(state['status'] == 'matrix_complete', 'matrix模式须全部条目完成后才测试，避免边看测试边改矩阵')
    done = [d for d in state['matrix_done'].values() if d['candidate_id'] == ident]
    require(done, '候选不是已完成的矩阵条目')
    return done[0]['run_ids']


def test(root, ident, rationale):
    from .process import spawn_detached
    require(rationale.strip(), '必须说明为何此时查看测试集')
    with locked(root):
        state = load_state(root);c = current_contract(root, state)
        require(c['test']['policy'] == 'locked', '契约未设锁定测试集')
        require(state['active_run'] is None and state.get('active_test') is None and state['status'] not in BUSY, '当前有运行、测试或待处理异常')
        require(not any(t['candidate_id'] == ident and t['revision'] == state['revision'] and not t.get('error') for t in state['tests']),
                '该候选本版本已完成测试；重复查看不产生新信息')
        run_ids = test_runs(root, state, c, ident)
        test_id = 't-' + uuid.uuid4().hex[:10]
        directory = root/'tests'/test_id;directory.mkdir(parents=True)
        cand = read_json(root/'candidates'/f'{ident}.json')
        meta = {'id': test_id, 'candidate_id': ident, 'entry': cand.get('entry'), 'commit': cand['commit'], 'run_ids': run_ids,
                'revision': state['revision'], 'rationale': rationale, 'created_at': timestamp(), 'prior_status': state['status'],
                'worker_pid': None, 'worker_token': None}
        write_json(directory/'test.json', meta)
        state['test_looks'] = state.get('test_looks', 0) + 1
        state['active_test'] = {'id': test_id, 'candidate_id': ident}
        state['status'] = 'testing'
        save_state(root, state, 'locked_test_started')
        worker = Path(__file__).resolve().parents[1]/'worker.py'
        try:
            owner = spawn_detached([sys.executable, str(worker), '--root', str(root), '--test-id', test_id], str(root), str(directory/'monitor.log'))
            meta.update(worker_pid=owner['pid'], worker_token=owner['token']);write_json(directory/'test.json', meta)
        except Exception as e:
            close_test(root, state, meta, None, '测试后台启动失败: ' + str(e))
            raise GateError('测试后台启动失败: ' + str(e))
    return meta


def close_test(root, state, meta, results, error=None):
    """Called under lock. Records the look even on failure; never feeds back into selection."""
    c = current_contract(root, state)
    entry = {'id': meta['id'], 'candidate_id': meta['candidate_id'], 'entry': meta.get('entry'), 'revision': meta['revision'],
             'rationale': meta['rationale'], 'time': timestamp(), 'look_number': state['test_looks'], 'error': error}
    if results:
        entry['summary'] = {'values': [r['value'] for r in results], 'value': stats.aggregate(c['verification']['aggregation'], [r['value'] for r in results], higher(c)),
                            'sd': stats.seed_sd([r['value'] for r in results]), 'run_ids': [r['run_id'] for r in results],
                            'guards': {g['name']: stats.aggregate(c['verification']['aggregation'], [r['guards'][g['name']] for r in results], g['direction'] == 'higher')
                                       for g in c['guard_metrics'] if all(g['name'] in r['guards'] for r in results)}}
    state['tests'].append(entry)
    write_json(root/'tests'/meta['id']/'summary.json', entry)
    state['status'] = meta['prior_status'];state['active_test'] = None
    save_state(root, state, 'locked_test_failed' if error else 'locked_test_recorded')


def test_finish(root, meta, results, error=None):
    with locked(root):
        state = load_state(root)
        require(state.get('active_test') and state['active_test']['id'] == meta['id'], '测试归属已变更')
        close_test(root, state, meta, results, error)


def test_comparisons(root, state, c):
    """Paired test-set CIs, report only: candidate vs this revision's reference."""
    ok = [t for t in state['tests'] if t['revision'] == state['revision'] and not t.get('error')]
    if c['mode'] == 'search':
        ref_id = state['baseline_stable']['candidate_id'] if state.get('baseline_stable') else None
    else:
        ref = state['matrix_done'].get(c['matrix']['reference'])
        ref_id = ref['candidate_id'] if ref else None
    ref_t = next((t for t in ok if t['candidate_id'] == ref_id), None)
    out = []
    for t in ok:
        if not ref_t or t is ref_t:
            continue
        try:
            ci = stats.paired_bootstrap(c['verification']['ci']['statistic'],
                                        [stats.read_cases(root/'tests'/t['id']/r/'cases.jsonl', c['verification']['ci']['statistic']) for r in t['summary']['run_ids']],
                                        [stats.read_cases(root/'tests'/ref_t['id']/r/'cases.jsonl', c['verification']['ci']['statistic']) for r in ref_t['summary']['run_ids']],
                                        higher(c), c['verification']['aggregation'], c['verification']['ci']['resamples'], c['verification']['ci']['level'], c['verification']['ci']['seed'])
        except GateError as e:
            ci = {'error': str(e)}
        out.append({'candidate_id': t['candidate_id'], 'entry': t.get('entry'), 'reference': ref_id, 'ci': ci})
    return out
def matrix_comparisons(root, state, c):
    ref = state['matrix_done'].get(c['matrix']['reference'])
    out = []
    for e in c['matrix']['entries']:
        done = state['matrix_done'].get(e['id'])
        row = {'entry': e['id'], 'role': e['role'], 'done': bool(done)}
        if done:
            row.update(value=done['value'], sd=done['sd'], guards=done['guards'])
            if ref and e['id'] != c['matrix']['reference']:
                try:
                    row['ci_vs_reference'] = paired(c, root, done['run_ids'], ref['run_ids'])
                except GateError as err:
                    row['ci_vs_reference'] = {'error': str(err)}
                row['guard_flags'] = guard_violations(c, done['guards'], ref['guards'])
        out.append(row)
    return out


def fmt(x):
    return '' if x is None else (f'{x:.4g}' if isinstance(x, float) else str(x))


def export(root):
    status(root)
    with locked(root):
        state=load_state(root);c=current_contract(root,state)
        records=[read_json(p) for p in sorted((root/'runs').glob('*/record.json'))]
        matrix=matrix_comparisons(root,state,c) if c['mode']=='matrix' else None
        tests=test_comparisons(root,state,c) if c['test']['policy']=='locked' else []
    limitations=['同家族模型审查不构成科学证明','受管操作控制不是操作系统沙箱','批准与审查身份是调用者记录',
                 '验证集用于选择，其上的结果有选择偏倚；结论以锁定测试集为准']
    if c['test']['policy']=='none':limitations.append('未设留出测试集：'+c['test']['rationale'])
    looks=state.get('test_looks',0)
    if looks>2:limitations.append(f'测试集已被查看{looks}次（跨版本累计）；若据此调整方向，测试结果也带乐观偏倚，需外部或新留出数据确认')
    report={'state':state,'contract_revision':state['revision'],'baseline_declaration':c['baseline'],'runs':records,
            'acceptance_status':state['status'],'matrix':matrix,'tests':state['tests'],'test_comparisons':tests,
            'limitations':limitations,'negative_results':[read_json(p) for p in (root/'evidence'/'negative-results').glob('*.json')]}
    write_json(root/'report.json',report)
    ci_level=c['verification']['ci']['level']
    L=['# 实验与证据报告','',f'课题：{state["study_id"]}；模式：{c["mode"]}；有效计划版本：{state["revision"]}；状态：{state["status"]}；阶段：{state["stage"]}','',
       '## 数据与基线声明','',f'分组单位：{c["data"]["group_unit"]}；标签：{c["data"]["labels_source"]}；评价：{c["data"]["evaluation_protocol"]}',
       f'划分审计：{json.dumps(state["audit"]["summary"],ensure_ascii=False) if state.get("audit") else "未运行"}',
       f'基线来源：{c["baseline"]["source"]}；强度依据：{c["baseline"]["strength_rationale"]}；调参对等：{c["baseline"]["tuning_parity"]}','',
       f'主要指标：{c["primary_metric"]["name"]}（{c["primary_metric"]["direction"]}，checkpoint={c["primary_metric"]["selection"]}）；护栏：'+
       (', '.join(f'{g["name"]}≤恶化{g["max_degradation"]}' for g in c['guard_metrics']) or '无'),'',
       '## 全部运行（验证集）','','| 运行 | 候选 | 条目 | 阶段 | 版本 | seed | 状态 | 主要指标 |','|---|---|---|---|---|---|---|---|']
    for r in records:L.append(f'| {r["run_id"]} | {r["candidate_id"]} | {r.get("entry") or ""} | {r["phase"]} | {r["revision"]} | {r["seed"]} | {r["status"]} | {fmt(r.get("value"))} |')
    if matrix:
        L+=['',f'## 实验矩阵（验证集，相对 {c["matrix"]["reference"]} 的配对 {int(ci_level*100)}% CI）','',
            '| 条目 | 角色 | 聚合值 | seed SD | Δ | CI | 护栏提示 |','|---|---|---|---|---|---|---|']
        for m in matrix:
            ci=m.get('ci_vs_reference') or {}
            L.append(f'| {m["entry"]} | {m["role"]} | {fmt(m.get("value"))} | {fmt(m.get("sd"))} | {fmt(ci.get("effect"))} | '
                     f'{"" if "ci_low" not in ci else fmt(ci["ci_low"])+" – "+fmt(ci["ci_high"])}{ci.get("error","")} | {"; ".join(m.get("guard_flags",[]))} |')
    if state.get('stable'):
        s=state['stable'];ci=s.get('ci_vs_baseline')
        L+=['','## 当前有效方法','',f'{s["candidate_id"]}：聚合 {fmt(s["value"])}，seed SD {fmt(s["sd"])}'+
            (f'；相对基线 Δ={fmt(ci["effect"])}，{int(ci_level*100)}% CI {fmt(ci["ci_low"])} – {fmt(ci["ci_high"])}（验证集，{ci["cases"]}例）' if ci else '')]
    L+=['','## 锁定测试集','',f'查看次数（跨版本累计）：{looks}','']
    for t in state['tests']:
        s=t.get('summary') or {}
        L.append(f'- 第{t["look_number"]}次 {t["candidate_id"]}（v{t["revision"]}）：{fmt(s.get("value")) if s else "失败："+str(t.get("error"))}；理由：{t["rationale"]}')
    for t in tests:
        ci=t['ci']
        L.append(f'- 测试集配对比较 {t["candidate_id"]} vs {t["reference"]}：'+(f'Δ={fmt(ci["effect"])}，CI {fmt(ci["ci_low"])} – {fmt(ci["ci_high"])}' if 'effect' in ci else ci.get('error','')))
    L+=['','## 限制','']+['- '+x for x in limitations]+['',
        'accepted / matrix_complete 只表示本契约规则达标；真实医学结论、GPU/PyTorch表现或临床效用需另行验证。失败、拒绝与负结果分别保存，不删除不利证据。']
    (root/'report.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
    return {'report_json':str(root/'report.json'),'report_markdown':str(root/'report.md'),'status':state['status']}
