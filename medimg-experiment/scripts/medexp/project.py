import fnmatch
import os
from pathlib import Path
import shutil
import subprocess
from .common import require, safe_path, inside, GateError


def git(directory, *args):
    r = subprocess.run(['git', '-C', str(directory), *args], capture_output=True,
                       encoding='utf-8', errors='replace', env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
                       creationflags=0x08000000 if os.name == 'nt' else 0)
    require(r.returncode == 0, 'Git操作失败: ' + r.stderr[-2000:])
    return r.stdout.strip()


def prepare(root, c):
    require(not root.exists(), '受管目录必须是全新目录，禁止覆盖')
    src = safe_path(c['code']['source_root']) if c['code']['source_root'] else None
    if src:
        require(not root.is_relative_to(src) and not src.is_relative_to(root), '受管目录与源代码目录不得重叠')
    root.mkdir(parents=True)
    repo = root/'code';repo.mkdir()
    if src:
        for name in c['code']['files']:
            dest = inside(repo, name);dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(inside(src, name), dest)
    (repo/'.gitignore').write_text('__pycache__/\n*.pyc\n', encoding='utf-8')
    git(repo, 'init', '-b', 'stable')
    git(repo, 'config', 'user.name', 'Medimg Experiment Local')
    git(repo, 'config', 'user.email', 'local@medimg.invalid')
    git(repo, 'config', 'core.autocrlf', 'false')
    git(repo, 'add', '--all');git(repo, 'commit', '-m', 'Managed input snapshot')
    git(repo, 'worktree', 'add', '-b', 'working', str(root/'worktree'), 'stable')


def commit(root):
    return git(root/'worktree', 'rev-parse', 'HEAD')


def clean(root):
    return not git(root/'worktree', 'status', '--porcelain', '--untracked-files=all')


def matches(name, patterns):
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


def snapshot(root, c, frozen_commit, phase):
    work = root/'worktree'
    changed = git(work, 'diff', '--name-only', 'HEAD').splitlines()
    changed += git(work, 'ls-files', '--others', '--exclude-standard').splitlines()
    for name in changed:
        inside(work, name)
        bootstrap = frozen_commit is None and matches(name, c['scope']['frozen_paths'])
        require(bootstrap or (matches(name, c['scope']['editable_paths']) and not matches(name, c['scope']['frozen_paths'])),
                '修改越出批准范围或触及固定评价文件: ' + name)
    for name in c['scope']['frozen_paths']:
        require(not any(ch in name for ch in '*?['), '固定评价文件必须使用明确路径')
        require(inside(work, name).is_file(), '固定评价文件尚未建立: ' + name)
    if frozen_commit:
        altered = git(work, 'diff', '--name-only', frozen_commit, '--', *c['scope']['frozen_paths'])
        require(not altered, '评价协议与首次基线版本不同')
    git(work, 'add', '--all')
    if git(work, 'diff', '--cached', '--name-only'):
        git(work, 'commit', '-m', 'Approved-range candidate snapshot')
    return commit(root)


def restore(root, anchor, run_id):
    work = root/'worktree'
    # Archive even late edits before resetting ONLY this managed worktree.
    if not clean(root):
        git(work, 'add', '--all')
        if git(work, 'diff', '--cached', '--name-only'):
            git(work, 'commit', '-m', 'Preserve late edits before recovery ' + run_id)
    git(work, 'update-ref', 'refs/medexp/recovery/' + run_id, commit(root))
    if anchor:
        git(work, 'reset', '--hard', anchor)
        git(root/'code', 'update-ref', 'refs/heads/stable', anchor)


def test_checkout(root, commit, directory, frozen_commit, frozen_paths):
    """Detached read-only-by-convention checkout of the exact tested commit."""
    git(root/'code', 'worktree', 'add', '--detach', str(directory), commit)
    altered = git(directory, 'diff', '--name-only', frozen_commit, '--', *frozen_paths)
    require(not altered, '被测提交的固定评价文件与冻结版本不同')
    return directory


def test_release(root, directory):
    git(root/'code', 'worktree', 'remove', '--force', str(directory))
