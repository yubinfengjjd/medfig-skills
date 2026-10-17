import re
from pathlib import Path
from .common import require, number, safe_path, inside

ROLES = ('baseline', 'proposed', 'ablation', 'comparison')
PHASES = {'search': ['baseline', 'explore', 'verify'], 'matrix': ['matrix']}


def external_path(value, label):
    # A confirmed external path must keep its meaning across the caller and
    # detached worker working directories. Never resolve a relative contract.
    require(isinstance(value, str) and value.strip() and Path(value).is_absolute(),
            f'{label}必须是明确的绝对路径，不能随调用目录变化')
    return safe_path(value)


def text(c, key, label=None):
    require(isinstance(c.get(key), str) and c[key].strip(), f'缺少{label or key}')
    return c[key]


def frozen_command(command, frozen, placeholders, label):
    require(isinstance(command, list) and len(command) >= 2 and all(isinstance(a, str) and a for a in command), f'{label}必须为argv数组')
    require(command[0] == '{python}' and command[1].endswith('.py'), f'{label}须以{{python}}和受管.py脚本开头')
    require(command[1] in frozen, f'{label}脚本必须列入frozen_paths，保证所有候选使用同一评价')
    for arg in command[2:]:
        require('{' not in arg or arg in placeholders, f'{label}不支持占位符: ' + arg)


def validate_matrix(c):
    entries = c.get('matrix', {}).get('entries')
    require(isinstance(entries, list) and entries, 'matrix模式必须列出实验条目')
    ids = [e.get('id') for e in entries]
    require(all(isinstance(i, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', i) for i in ids)
            and len(ids) == len(set(ids)), '矩阵条目id无效或重复')
    for e in entries:
        require(e.get('role') in ROLES, '矩阵条目role必须为' + '/'.join(ROLES))
        require(isinstance(e.get('description'), str) and e['description'].strip(), '矩阵条目须说明内容与目的')
    ref = c['matrix'].get('reference')
    require(ref in ids and next(e for e in entries if e['id'] == ref)['role'] == 'baseline',
            'matrix.reference必须指向一个baseline条目')


def validate(c):
    require(c.get('schema_version') == 2, '仅支持schema_version=2；旧版契约请按新模板建立新课题工程')
    require(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', c.get('study_id') or '') is not None, '课题标识无效')
    require(c.get('task') in ('classification', 'segmentation'), '首版支持分类或分割')
    text(c, 'hypothesis')
    text(c, 'plan_path')
    require(external_path(c['plan_path'], 'plan_path').is_file(), '原始计划文件不存在')
    mode = c.get('mode')
    require(mode in PHASES, 'mode必须为search（基线→探索→复核）或matrix（预定义实验矩阵）')
    require(c.get('stages') == PHASES[mode], f'{mode}模式的stages必须为{PHASES[mode]}')
    if mode == 'matrix':
        validate_matrix(c)
    metric = c['primary_metric']
    require(isinstance(metric.get('name'), str) and metric['name'].strip(), '必须声明主要指标')
    require(metric.get('direction') in ('higher', 'lower'), '指标方向必须声明')
    require(metric.get('selection') in ('last', 'best'), 'primary_metric.selection必须为last或best（验证集最优checkpoint）')
    if mode == 'search':
        number(metric.get('target'), '成功标准target')
        require(number(metric.get('min_effect'), '最小效应') >= 0, '最小效应不得为负')
    guards = c.get('guard_metrics')
    require(isinstance(guards, list), 'guard_metrics必须为列表；确无护栏指标时写[]')
    names = [metric['name']]
    for g in guards:
        require(isinstance(g.get('name'), str) and g['name'].strip() and g['name'] not in names, '护栏指标名称无效或重复')
        names.append(g['name'])
        require(g.get('direction') in ('higher', 'lower'), '护栏指标方向必须声明')
        require(number(g.get('max_degradation'), '护栏允许恶化量') >= 0, '护栏允许恶化量不得为负')
    data = c['data']
    require(isinstance(data.get('paths'), list) and data['paths'], '必须声明数据路径')
    for p in data['paths']:
        require(external_path(p, 'data.paths').exists(), '数据路径不存在')
    for k in ['labels_source', 'split_reference', 'group_unit', 'evaluation_protocol']:
        require(isinstance(data.get(k), str) and data[k].strip(), f'缺少数据规则{k}')
    scope = c['scope']
    for k in ['editable_paths', 'frozen_paths']:
        require(isinstance(scope.get(k), list) and scope[k], f'必须声明{k}')
        for p in scope[k]:
            require(isinstance(p, str) and p and not p.startswith(('/', '\\')) and ':' not in p
                    and '..' not in p.replace('\\', '/').split('/') and '.git' not in p.split('/'), '代码范围路径无效')
    require(isinstance(scope.get('parameters'), list), '必须声明允许参数')
    for p in scope['parameters']:
        require(isinstance(p, str) and p.startswith('--') and p not in ('--seed',), '参数白名单无效；seed由验证协议管理')
        require(not '--seed'.startswith(p) and not p.startswith('--seed='), '参数不能使用seed的覆盖形式或缩写')
    base = c.get('baseline')
    require(isinstance(base, dict), '必须声明baseline来源与强度依据')
    for k in ['source', 'strength_rationale', 'tuning_parity']:
        text(base, k, 'baseline.' + k)
    audit = c.get('split_audit')
    require(isinstance(audit, dict), '必须声明split_audit')
    frozen_command(audit.get('command'), scope['frozen_paths'], ('{output}',), '划分审计命令')
    require(audit['command'].count('{output}') == 1, '划分审计命令须包含一次{output}')
    number(audit.get('timeout_seconds'), '划分审计时限', positive=True)
    test = c.get('test')
    require(isinstance(test, dict) and test.get('policy') in ('locked', 'none'), 'test.policy必须为locked或none')
    if test['policy'] == 'locked':
        text(test, 'reference', 'test.reference')
        frozen_command(test.get('command'), scope['frozen_paths'], ('{run_dir}', '{output}'), '测试评估命令')
        require(test['command'].count('{run_dir}') == 1 and test['command'].count('{output}') == 1,
                '测试命令须各包含一次{run_dir}与{output}')
        number(test.get('timeout_seconds'), '单次测试评估时限', positive=True)
    else:
        text(test, 'rationale', 'test.rationale（不设留出测试的理由与结论限制）')
    anomaly = c['anomaly']
    require(number(anomaly.get('max_drop'), '异常阈值') > 0, '异常阈值必须大于0')
    require(anomaly.get('unit') in ('relative', 'absolute'), '必须明确阈值relative比例或absolute指标单位')
    require(isinstance(anomaly.get('warmup_steps'), int) and anomaly['warmup_steps'] >= 0, '必须声明暖启动步数')
    require(isinstance(anomaly.get('consecutive_outside_range'), int) and anomaly['consecutive_outside_range'] > 0, '必须声明连续异常次数')
    require(isinstance(anomaly.get('reference_ranges'), dict), '必须声明参考区间，可为空表示不启用')
    for phase, bounds in anomaly['reference_ranges'].items():
        require(phase in c['stages'], '参考区间阶段无效')
        require(isinstance(bounds, list) and len(bounds) == 2, '参考区间必须有上下限')
        require(number(bounds[0], '下限') <= number(bounds[1], '上限'), '参考区间倒置')
    budget = c['budget']
    for k in ['total_seconds', 'run_timeout_seconds']:
        number(budget.get(k), k, positive=True)
    if mode == 'search':
        for k in ['max_candidates', 'max_no_improvement']:
            require(isinstance(budget.get(k), int) and not isinstance(budget[k], bool) and budget[k] > 0, f'{k}必须为正整数')
    v = c['verification']
    seeds = v.get('seeds')
    require(isinstance(seeds, list) and len(seeds) >= 3 and len(seeds) == len(set(seeds))
            and all(isinstance(x, int) and not isinstance(x, bool) for x in seeds), '复核必须有至少三个明确且不重复的seed')
    require(v.get('aggregation') in ('mean', 'median', 'worst'), '聚合规则必须为mean/median/worst')
    bounds = v.get('normal_range')
    require(isinstance(bounds, list) and len(bounds) == 2 and number(bounds[0], '正常下限') <= number(bounds[1], '正常上限'), '必须声明完整验证正常范围')
    number(v.get('max_std'), '复核样本标准差上限', positive=True)
    ci = v.get('ci')
    require(isinstance(ci, dict) and ci.get('method') == 'paired_bootstrap', 'verification.ci.method必须为paired_bootstrap')
    require(ci.get('statistic') in ('mean_per_case', 'binary_auroc'), 'ci.statistic必须为mean_per_case或binary_auroc')
    require(ci['statistic'] != 'binary_auroc' or c['task'] == 'classification', 'binary_auroc仅用于分类')
    require(isinstance(ci.get('resamples'), int) and 200 <= ci['resamples'] <= 100000, 'ci.resamples须为200–100000的整数')
    require(isinstance(ci.get('level'), (int, float)) and 0.5 < ci['level'] < 1, 'ci.level须在0.5与1之间')
    require(isinstance(ci.get('seed'), int) and not isinstance(ci['seed'], bool), 'ci.seed必须为整数')
    if mode == 'search':
        require(ci.get('lower_bound_rule') in ('min_effect', 'zero'), 'ci.lower_bound_rule必须为min_effect或zero')
    env = c['environment']
    require(external_path(env.get('python'), 'environment.python').is_file(), '必须提供真实Python解释器，不能用Windows应用别名')
    require(env.get('device') in ('cpu', 'cuda'), 'device必须声明cpu/cuda')
    require(isinstance(env.get('dependencies'), dict) and all(isinstance(k, str) and k and isinstance(x, str) and x for k, x in env['dependencies'].items()), '依赖必须声明包名和精确版本')
    number(env.get('min_free_bytes'), '存储最低余量', positive=True)
    require(c.get('retention', {}).get('mode') == 'necessary', '首版保留必要权重，不自动清理历史产物')
    code = c['code']
    require(isinstance(code.get('files'), list), '必须声明复制的代码清单，可为空')
    if code.get('source_root'):
        src = external_path(code['source_root'], 'code.source_root')
        require(src.is_dir(), '输入代码目录不存在')
        for name in code['files']:
            p = inside(src, name)
            require(p.is_file() and not p.is_symlink(), '复制清单必须是实际代码文件')
            require(p.suffix.lower() in ('.py', '.md', '.json', '.yaml', '.yml', '.toml', '.txt', '.cfg', '.ini')
                    and not p.name.startswith('.env') and 'credential' not in p.name.lower(), '拒绝复制数据、权重或凭证；仅列出必要代码配置')
    else:
        require(not code['files'], '没有source_root时复制清单必须为空')
    return c


def matrix_entry(c, ident):
    return next((e for e in c['matrix']['entries'] if e['id'] == ident), None)
