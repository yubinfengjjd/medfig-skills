r"""Check the structure and mapping of a medpaper-pipeline code intake.

Usage: python -X utf8 scripts/intake_check.py <project_root> [--json]
Standard library only; reads 01_analysis without following links or external references.
Exit code: 0 = no error, 1 = at least one error. Warnings do not fail the run.
This checks structure, not execution, author approval authenticity or scientific validity.
"""
import argparse
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

HEADERS = ('序号', '整理后路径', '原路径', '运行命令', '前置序号', '产出', '对应图表', '备注')
BLACKLIST = {'.pt', '.pth', '.npz', '.safetensors', '.ckpt', '.bin', '.h5', '.sqlite'}
CODE_NAME = re.compile(r'^\d{2}_')


def is_link(path):
    """Reject symlinks (including dangling links) and Windows reparse points."""
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)
    )


def cell_text(cell):
    return cell.strip().strip('`').strip()


def table_cells(line):
    # Escaped pipes in command cells do not introduce extra columns.
    return [cell_text(c).replace(r'\|', '|') for c in re.split(r'(?<!\\)\|', line.strip().strip('|'))]


def scan(root):
    root = Path(root).absolute()
    errors, warnings = [], []

    def issue(path, rule, msg, line=0, warning=False):
        item = {'file': path.relative_to(root).as_posix(), 'line': line, 'rule': rule, 'msg': msg}
        (warnings if warning else errors).append(item)

    def linked(path):
        if is_link(path):
            issue(path, 'symlink', '符号链接或重解析点一律拒绝，不适用作者批准')
            return True
        return False

    def read(path):
        try:
            return path.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError) as exc:
            issue(path, 'read', f'无法读取 UTF-8 文件：{exc}')
            return ''

    def files_below(directory):
        """Inventory regular files; reject links before inspecting their targets."""
        files = []

        def walk_error(exc):
            issue(Path(exc.filename), 'read', f'目录无法读取：{exc}')

        for current, dirs, names in os.walk(directory, followlinks=False, onerror=walk_error):
            dirs.sort()
            names.sort()
            for name in dirs[:]:
                p = Path(current) / name
                if linked(p):
                    dirs.remove(name)
            for name in names:
                p = Path(current) / name
                if not linked(p):
                    files.append(p)
        return files

    analysis = root / '01_analysis'
    if not analysis.exists() and not analysis.is_symlink():
        issue(analysis, 'structure', '缺少 01_analysis/ 目录')
        return errors, warnings
    if linked(analysis):
        return errors, warnings
    if not analysis.is_dir():
        issue(analysis, 'structure', '01_analysis 必须是目录')
        return errors, warnings

    # One walk checks links everywhere, including study, but never enters linked directories.
    inventory = files_below(analysis)
    index = analysis / 'README.md'
    index_text = ''
    if index in inventory:
        index_text = read(index)
    else:
        issue(index, 'index', '缺少总 README.md')

    for p in inventory:
        if p.parent == analysis and p.suffix.lower() in BLACKLIST:
            issue(p, 'blacklist', '黑名单文件未在来源映射表逐文件批准')

    sources = sorted(p for p in analysis.iterdir() if not is_link(p) and p.is_dir())
    for source in sources:
        # Match a directory name, not merely a prefix of another registered directory.
        if not re.search(r'(?<![\w.-])' + re.escape(source.name) + r'(?![\w.-])', index_text):
            issue(index, 'registration', f'总 README 未登记目录：{source.name}')

        plans, state = source / 'plans', source / 'state.json'
        study = (plans.exists() and not is_link(plans) and plans.is_dir()
                 and state.exists() and not is_link(state) and state.is_file())
        if study:
            # Controller-owned files (including checkpoints) do not use intake mappings/names.
            continue

        for name, directory in (('README.md', False), ('映射表.md', False), ('code', True)):
            p = source / name
            present = p.exists() and not is_link(p) and (p.is_dir() if directory else p.is_file())
            if not present:
                issue(p, 'structure', f'来源缺少 {name}{"/" if directory else ""}')

        source_files = {p.relative_to(source).as_posix(): p for p in inventory if source in p.parents}
        mapping = source / '映射表.md'
        mapped = {}
        if '映射表.md' in source_files:
            in_table = False
            found_header = False
            for line_no, line in enumerate(read(mapping).splitlines(), 1):
                if not line.strip().startswith('|'):
                    if line.strip():
                        in_table = False
                    continue
                cells = table_cells(line)
                if tuple(cells) == HEADERS:
                    in_table = found_header = True
                    continue
                if not in_table or all(re.fullmatch(r':?-{3,}:?', c) for c in cells):
                    continue
                if len(cells) != len(HEADERS):
                    issue(mapping, 'mapping-row', '映射表数据行必须含八列', line_no)
                    continue
                row = dict(zip(HEADERS, cells))
                if row['原路径'] in ('', '-', '—'):
                    issue(mapping, 'original-path', '原路径不得为空', line_no)
                rel = row['整理后路径'].replace('\\', '/')
                parts = PurePosixPath(rel).parts
                if (not parts or parts[0] not in ('code', 'results', 'receipts') or len(parts) < 2
                        or '..' in parts or PureWindowsPath(rel).drive or PurePosixPath(rel).is_absolute()):
                    issue(mapping, 'mapping-path', '整理后路径须位于本来源 code/results/receipts 内', line_no)
                    continue
                rel = PurePosixPath(rel).as_posix()
                if rel in mapped:
                    issue(mapping, 'duplicate-path', f'重复整理后路径：{rel}', line_no)
                mapped[rel] = row
                if rel not in source_files:
                    issue(mapping, 'missing-file', f'映射文件不存在或不是普通文件：{rel}', line_no)
            if not found_header:
                issue(mapping, 'mapping-header', '缺少规定的八列映射表表头')

        code_files = {rel: p for rel, p in source_files.items() if rel.startswith('code/')}
        for rel, p in sorted(code_files.items()):
            if rel not in mapped:
                issue(p, 'unmapped-code', 'code/ 文件未列入映射表')
            if not CODE_NAME.match(p.name):
                issue(p, 'code-name', 'code/ 文件名须以两位数字和下划线开头')
        if (source / 'code').is_dir() and not is_link(source / 'code') and not code_files:
            issue(source / 'code', 'empty-code', 'code/ 没有文件，请核对是否无代码可整理', warning=True)

        for rel, p in sorted(source_files.items()):
            if p.suffix.lower() in BLACKLIST and '作者批准' not in mapped.get(rel, {}).get('备注', ''):
                issue(p, 'blacklist', '黑名单文件未在该文件映射表备注标明“作者批准”')
    return errors, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project_root')
    parser.add_argument('--json', action='store_true', help='输出结构化错误与警告')
    args = parser.parse_args(argv)
    try:
        errors, warnings = scan(args.project_root)
    except (OSError, UnicodeError) as exc:
        errors = [{'file': '01_analysis', 'line': 0, 'rule': 'read', 'msg': f'无法完成核验：{exc}'}]
        warnings = []
    if args.json:
        print(json.dumps({'errors': errors, 'warnings': warnings}, ensure_ascii=False, indent=1))
    else:
        for e in errors:
            print(f"{e['file']}:{e['line']}  [error] {e['msg']}")
        for w in warnings:
            print(f"{w['file']}:{w['line']}  [警告] {w['msg']}")
        print(f'{len(errors)} hit(s), {len(warnings)} warning(s)')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
