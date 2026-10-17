"""Windows process ownership without PID-tree scans or third-party packages.

The monitor holds a non-inheritable, kill-on-close Job Object. Training starts
suspended and joins that job before its first instruction can create a child.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import math
import os
import subprocess
import time

if os.name == "nt":
    import _winapi
    import msvcrt

    _kernel = ctypes.WinDLL("kernel32", use_last_error=True)

    class _JobBasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
        )]

    class _JobExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JobBasicLimits),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    _kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _kernel.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    _kernel.SetInformationJobObject.restype = wintypes.BOOL
    _kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _kernel.TerminateJobObject.restype = wintypes.BOOL
    _kernel.ResumeThread.argtypes = [wintypes.HANDLE]
    _kernel.ResumeThread.restype = wintypes.DWORD
    _kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
        ctypes.POINTER(wintypes.FILETIME)
    ] * 4
    _kernel.GetProcessTimes.restype = wintypes.BOOL


def _require_windows() -> None:
    if os.name != "nt":
        raise NotImplementedError("medexp process control requires Windows")


def _checked(result):
    if not result:
        raise ctypes.WinError(ctypes.get_last_error())
    return result


def _creation_token(handle: int) -> str:
    creation, exit_time, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
    _checked(_kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time),
                                     ctypes.byref(kernel_time), ctypes.byref(user_time)))
    stamp = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
    return f"windows-filetime:{stamp:016x}"


def process_identity(pid: int) -> str | None:
    """Return the live process's creation FILETIME, or None if inaccessible/exited."""
    _require_windows()
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        handle = _winapi.OpenProcess(0x00100000 | 0x1000, False, pid)
    except (OSError, OverflowError):
        return None
    try:
        if _winapi.WaitForSingleObject(handle, 0) != _winapi.WAIT_TIMEOUT:
            return None
        return _creation_token(handle)
    except OSError:
        return None
    finally:
        _winapi.CloseHandle(handle)


def is_alive(pid: int, token: str) -> bool:
    """Accept only a running process with the exact recorded creation identity."""
    _require_windows()
    return bool(token) and process_identity(pid) == token


def _start_suspended(argv: list[str], cwd: str, env: dict[str, str] | None,
                     log_path: str, flags: int = 0) -> tuple[int, int, int]:
    if not argv or any(not isinstance(arg, str) or "\0" in arg for arg in argv):
        raise ValueError("argv must be a nonempty list of strings without NUL characters")
    # Python's native CreateProcess wrapper builds the Unicode environment block
    # and STARTUPINFOEX handle allow-list, as subprocess does on Windows.
    with open(log_path, "ab", buffering=0) as log, open(os.devnull, "rb", buffering=0) as null:
        log_handle = msvcrt.get_osfhandle(log.fileno())
        null_handle = msvcrt.get_osfhandle(null.fileno())
        handles = [log_handle, null_handle]
        for handle in handles:
            os.set_handle_inheritable(handle, True)
        startup = subprocess.STARTUPINFO()
        startup.dwFlags = subprocess.STARTF_USESTDHANDLES | subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        startup.hStdInput = null_handle
        startup.hStdOutput = startup.hStdError = log_handle
        startup.lpAttributeList = {"handle_list": handles}
        process, thread, pid, _ = _winapi.CreateProcess(
            None, subprocess.list2cmdline(argv), None, None, True,
            flags | 0x00000004 | 0x08000000 | 0x00000400,
            env, cwd, startup,
        )
    return process, thread, pid


def _resume(thread: int) -> None:
    if _kernel.ResumeThread(thread) == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())


class OwnedProcess:
    """A training process and its CreateProcess descendants, owned by one monitor.

    env replaces the child environment; callers can merge os.environ explicitly.
    close is idempotent and kills any remaining descendants, including after the
    training root exits normally. wait reports the root's Windows exit code.
    """

    def __init__(self, argv: list[str], cwd: str, env: dict[str, str], log_path: str):
        _require_windows()
        self._argv = list(argv)
        self._process = None
        self._job = None
        self._returncode = None
        thread = None
        try:
            self._job = _checked(_kernel.CreateJobObjectW(None, None))
            limits = _JobExtendedLimits()
            limits.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
            _checked(_kernel.SetInformationJobObject(
                self._job, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
            self._process, thread, self._pid = _start_suspended(self._argv, cwd, env, log_path)
            self._token = _creation_token(self._process)
            _checked(_kernel.AssignProcessToJobObject(self._job, self._process))
            _resume(thread)
        except BaseException:
            if self._process is not None:
                _winapi.TerminateProcess(self._process, 1)
                _winapi.WaitForSingleObject(self._process, 5000)
                _winapi.CloseHandle(self._process)
                self._process = None
            if self._job is not None:
                _winapi.CloseHandle(self._job)
                self._job = None
            raise
        finally:
            if thread is not None:
                _winapi.CloseHandle(thread)

    @property
    def pid(self) -> int:
        return self._pid

    @property
    def token(self) -> str:
        return self._token

    def poll(self) -> int | None:
        if self._returncode is None and self._process is not None:
            if _winapi.WaitForSingleObject(self._process, 0) == _winapi.WAIT_OBJECT_0:
                self._returncode = _winapi.GetExitCodeProcess(self._process)
        return self._returncode

    def terminate(self) -> None:
        """Terminate only members of this owned Job Object; never terminate by PID."""
        if self._job is not None:
            _checked(_kernel.TerminateJobObject(self._job, 1))

    def wait(self, timeout: float | None = None) -> int:
        if self.poll() is not None:
            return self._returncode
        if self._process is None:
            raise RuntimeError("owned process handle is closed")
        if timeout is not None and not math.isfinite(timeout):
            raise ValueError("timeout must be finite or None")
        deadline = None if timeout is None else time.monotonic() + max(0.0, timeout)
        while True:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            milliseconds = _winapi.INFINITE if remaining is None else min(math.ceil(remaining * 1000), 0xFFFFFFFE)
            result = _winapi.WaitForSingleObject(self._process, milliseconds)
            if result == _winapi.WAIT_OBJECT_0:
                self._returncode = _winapi.GetExitCodeProcess(self._process)
                return self._returncode
            if result != _winapi.WAIT_TIMEOUT:
                raise OSError(f"unexpected Windows wait result: {result}")
            if deadline is not None and time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(self._argv, timeout)

    def close(self) -> None:
        if self._job is not None:
            job, self._job = self._job, None
            _winapi.CloseHandle(job)
        if self._process is not None:
            try:
                self.wait(timeout=5)
            finally:
                process, self._process = self._process, None
                _winapi.CloseHandle(process)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def spawn_detached(argv: list[str], cwd: str, log_path: str) -> dict:
    """Launch a hidden worker independent of the launcher's console and handles.

    The worker owns its own training Job Object. An enclosing external job policy
    still applies; DETACHED_PROCESS cannot override a job that disallows breakaway.
    """
    _require_windows()
    process, thread, pid = _start_suspended(argv, cwd, None, log_path, 0x00000008 | 0x00000200)
    try:
        token = _creation_token(process)
        _resume(thread)
        return {"pid": pid, "token": token}
    except BaseException:
        _winapi.TerminateProcess(process, 1)
        _winapi.WaitForSingleObject(process, 5000)
        raise
    finally:
        _winapi.CloseHandle(thread)
        _winapi.CloseHandle(process)
