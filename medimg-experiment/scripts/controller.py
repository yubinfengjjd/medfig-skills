"""Codex-facing JSON CLI. Approval/review records do not authenticate a human."""
import argparse
import json
import sys
from medexp.common import safe_path
from medexp import engine


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description='本地医学影像实验控制，先确认再训练')
    commands=p.add_subparsers(dest='action',required=True)
    for name in ['init','approve','audit','candidate','review','run','test','status','reported','recover','resume','export']:
        sp=commands.add_parser(name);sp.add_argument('--root',required=True)
        if name in ('init','resume'):sp.add_argument('--contract',required=True)
        if name in ('approve','reported','resume'):sp.add_argument('--statement',required=True)
        if name=='resume':sp.add_argument('--direction',required=True)
        if name=='candidate':
            sp.add_argument('--id',required=True);sp.add_argument('--phase',choices=['baseline','explore','verify','matrix'],required=True)
            sp.add_argument('--command',required=True);sp.add_argument('--description',required=True)
            sp.add_argument('--entry',default=None)
        if name=='review':sp.add_argument('--record',required=True)
        if name=='run':sp.add_argument('--candidate',required=True);sp.add_argument('--seed',type=int,required=True)
        if name=='test':sp.add_argument('--candidate',required=True);sp.add_argument('--rationale',required=True)
    args=p.parse_args()
    try:
        root=safe_path(args.root)
        if args.action=='init':r=engine.init(root,args.contract)
        elif args.action=='approve':r=engine.approve(root,args.statement)
        elif args.action=='audit':r=engine.audit(root)
        elif args.action=='candidate':r=engine.candidate(root,args.id,args.phase,args.command,args.description,args.entry)
        elif args.action=='test':r=engine.test(root,args.candidate,args.rationale)
        elif args.action=='review':r=engine.review(root,args.record)
        elif args.action=='run':r=engine.run(root,args.candidate,args.seed)
        elif args.action=='status':r=engine.status(root)
        elif args.action=='reported':r=engine.reported(root,args.statement)
        elif args.action=='recover':r=engine.recover(root)
        elif args.action=='resume':r=engine.resume(root,args.contract,args.direction,args.statement)
        else:r=engine.export(root)
        summaries={'awaiting_confirmation':'等待用户确认契约与预算，尚未训练','ready':'当前阶段可按批准范围继续',
                   'running':'受管训练运行中，后台不生成新候选','queued':'当前训练已提交，等待后台检查与执行',
                   'verification_required':'探索结果达标，仍需完成正式复核','accepted':'当前契约的正式复核已通过，实际研究有效性另行验证',
                   'awaiting_report':'异常已停止并保全，先向用户汇报再回退','reported':'已登记汇报，接下来执行受管回退与失败记录',
                   'awaiting_direction':'失败处理完成，等待用户选择方向与确认新契约','budget_exhausted':'预算或无改善上限已达，目标尚未达成',
                   'testing':'锁定测试集评估运行中；结果只报告，不用于选择','matrix_complete':'实验矩阵全部条目完成复核，可做锁定测试与导出'}
        r['summary_zh']=summaries.get(r.get('status'), '受管操作完成；请结合返回的候选、审查或报告路径检查结果')
        if args.action=='audit':r['summary_zh']='划分审计通过：分组单位跨划分无重叠；标签质量与重复图像仍需审查'
        print(json.dumps(r,ensure_ascii=False,allow_nan=False))
        return 0
    except Exception as e:
        print(json.dumps({'error':type(e).__name__,'summary_zh':str(e)},ensure_ascii=False))
        return 2


if __name__=='__main__':sys.exit(main())
