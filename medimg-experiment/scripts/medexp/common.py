from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time
import uuid


class GateError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise GateError(message)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def _blocked_roots():
    raw = os.environ.get('MEDEXP_BLOCKED_ROOTS', '')
    roots = []
    for item in raw.split(os.pathsep):
        value = item.strip()
        if value:
            q = Path(value).expanduser().absolute()
            roots.extend((str(q).replace('\\', '/').lower(),
                          str(q.resolve()).replace('\\', '/').lower()))
    return roots


def safe_path(value):
    # Reject both lexical and resolved paths, BEFORE opening or executing anything.
    p = Path(value).absolute()
    blocked = _blocked_roots()
    for q in (p, p.resolve()):
        norm = str(q).replace('\\', '/').lower()
        require(not any(norm == r or norm.startswith(r + '/') for r in blocked),
                '禁止访问已登记的隔离根目录')
    return p.resolve()


def inside(root, relative):
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute(), '必须使用相对路径')
    p = safe_path(root / relative)
    require(p.is_relative_to(root.resolve()) and p != root.resolve(), '路径越出受管目录')
    return p


def read_json(path):
    return json.loads(safe_path(path).read_text(encoding='utf-8'))


def write_json(path, data):
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, allow_nan=False, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def number(value, label, positive=False):
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
            f'{label}必须是有限数值')
    require(not positive or value > 0, f'{label}必须大于0')
    return value


@contextmanager
def locked(root):
    import msvcrt
    path = safe_path(root) / '.control.lock'
    with path.open('a+b') as f:
        if path.stat().st_size == 0:
            f.write(b'0'); f.flush()
        deadline = time.monotonic() + 10
        while True:
            try:
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                require(time.monotonic() < deadline, '控制状态锁超时；不要并行修改同一课题')
                time.sleep(.05)
        try:
            yield
        finally:
            f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def load_state(root):
    return read_json(root / 'state.json')


def save_state(root, state, event):
    state['updated_at'] = timestamp()
    write_json(root / 'state.json', state)
    with (root / 'events.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'time': timestamp(), 'event': event, 'revision': state['revision'],
                            'status': state['status']}, ensure_ascii=False) + '\n')
        f.flush(); os.fsync(f.fileno())
