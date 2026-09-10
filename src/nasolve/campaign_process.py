"""Owned foreground workers and conservative process checks for campaigns.

Saved process records are evidence, never authority to send a signal. Only the
runner which created a child may terminate its isolated process group. A copied
or unidentifiable live record requires inspection rather than a guessed retry.
"""

from __future__ import annotations

import errno
import os
import platform
import re
import signal
import stat
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Mapping

from .campaigns import CampaignError


class CampaignProcessError(CampaignError):
    """A worker could not be launched or its process group remains unresolved."""

    def __init__(self, message: str, *, stopped_verified: bool = False):
        super().__init__(message)
        self.stopped_verified = stopped_verified


def _require_posix() -> None:
    if os.name != "posix":
        raise CampaignProcessError(
            "Campaign execution requires POSIX process groups and locks (macOS or Linux)"
        )


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    """Hold an exclusive nonblocking kernel lock without ever unlinking its file.

    The caller owns and validates the parent directory. A persistent inode is
    essential: deleting a lock file lets another caller lock a different inode.
    Descriptors are not inherited by exec; the worker holds its own dataset lock.
    """
    _require_posix()
    import fcntl

    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise CampaignProcessError(f"Cannot open campaign lock {path}: {exc}") from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise CampaignProcessError(f"Campaign lock is not a regular file: {path}")
        os.set_inheritable(descriptor, False)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN}:
                raise CampaignProcessError(f"Campaign work is already active; lock busy: {path}") from exc
            raise CampaignProcessError(f"Cannot acquire campaign lock {path}: {exc}") from exc
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _boot_id() -> str | None:
    try:
        if sys.platform.startswith("linux"):
            return Path("/proc/sys/kernel/random/boot_id").read_text().strip() or None
        if sys.platform == "darwin":
            result = subprocess.run(
                ["/usr/sbin/sysctl", "-n", "kern.boottime"],
                capture_output=True, text=True, timeout=2, check=False,
            )
            if result.returncode == 0:
                # sysctl appends a date in the caller's local timezone. Only
                # the numeric boot epoch is a stable identity across sessions.
                match = re.search(r"\{\s*sec\s*=\s*(\d+)\s*,\s*usec\s*=\s*(\d+)\s*\}", result.stdout)
                if match:
                    return "darwin-boot:" + ":".join(match.groups())
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _start_marker(pid: int) -> str | None:
    try:
        if sys.platform.startswith("linux"):
            # Containers may expose a proc mount from a different PID namespace.
            # Such a numeric path would describe an unrelated process.
            if int(Path("/proc/self/stat").read_text().split(" ", 1)[0]) != os.getpid():
                return None
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            return "proc-start-ticks:" + fields[19]
        result = subprocess.run(
            ["/bin/ps", "-p", str(pid), "-o", "lstart="],
            capture_output=True, text=True, timeout=2, check=False,
        )
        return "ps-lstart:" + result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def current_process_identity() -> dict[str, object]:
    """Record this process before the worker begins any scientific writes."""
    _require_posix()
    return _identity(os.getpid(), os.getpgrp())


def _identity(pid: int, pgid: int) -> dict[str, object]:
    started = _now()
    return {
        "pid": pid, "pgid": pgid, "host": platform.node(),
        "boot_id": _boot_id(), "start_marker": _start_marker(pid),
        "started_utc": started, "heartbeat_utc": started,
    }


def _group_alive(pgid: int) -> bool | None:
    """Return live members, absence, or uncertainty; zombies cannot write files."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Darwin returns EPERM for an existing group containing only zombies,
        # even for signal 0. Inspect its members before declaring uncertainty.
        pass
    except OSError:
        return None
    try:
        listing = subprocess.run(
            ["/bin/ps", "-axo", "pgid=,stat="],
            capture_output=True, text=True, timeout=0.25, check=False,
        )
        if listing.returncode != 0:
            return None
        members = []
        for line in listing.stdout.splitlines():
            fields = line.split()
            if fields and fields[0] == str(pgid):
                if len(fields) != 2:
                    return None
                members.append(fields[1])
        if members:
            return any(not member.startswith("Z") for member in members)
        # The group may have exited between killpg and ps. If it still exists,
        # an incomplete/unsupported process listing must not authorize a retry.
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return False
        except (PermissionError, OSError):
            pass
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def process_alive(identity: Mapping[str, object] | None) -> bool | None:
    """Inspect a saved identity without sending a signal to its recorded PID.

    True means the recorded group currently has a live member, even if its ID
    was reused. False means that group is gone or this machine rebooted. None
    means that inactivity cannot be established on this machine. A start marker
    is recorded for diagnosis but deliberately does not justify killing a PID.
    """
    if os.name != "posix" or not isinstance(identity, Mapping):
        return None
    if identity.get("host") != platform.node():
        return None
    pgid, pid = identity.get("pgid"), identity.get("pid")
    if type(pgid) is not int or pgid <= 1 or type(pid) is not int or pid != pgid:
        return None
    boot_id = _boot_id()
    saved_boot = identity.get("boot_id")
    if isinstance(saved_boot, str) and saved_boot and boot_id and saved_boot != boot_id:
        return False
    return _group_alive(pgid)


@contextmanager
def _ignore_termination() -> Iterator[None]:
    previous = {}
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, signal.SIG_IGN)
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


@contextmanager
def _defer_spawn_interrupts() -> Iterator[None]:
    """Do not interrupt fork/exec before Popen returns the owned child handle.

    Caught handlers reset during exec, so the worker does not inherit blocked
    termination signals. The enclosing runner restores both original handlers
    even if interruption occurs while these temporary handlers are restored.
    """
    previous = {}
    pending = []
    if threading.current_thread() is threading.main_thread():
        def defer(signum, frame):
            pending.append(signum)
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, defer)
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        if pending:
            raise KeyboardInterrupt


def _stop_owned_group(process: subprocess.Popen) -> None:
    """Stop only our unreaped child's group; retain its PID through escalation."""
    if process.returncode is not None:
        if _group_alive(process.pid) is not False:
            raise CampaignProcessError(
                "Worker exited with surviving or unidentifiable descendants; inspect before retrying"
            )
        return
    with _ignore_termination():
        for sig, allowance in ((signal.SIGTERM, 2.0), (signal.SIGKILL, 1.0)):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                break
            except PermissionError as exc:
                # The owned child may already be a zombie on Darwin. Only a
                # verified inactive group makes this denial safe to accept.
                if _group_alive(process.pid) is False:
                    break
                raise CampaignProcessError(f"Cannot stop owned campaign worker group: {exc}") from exc
            except OSError as exc:
                raise CampaignProcessError(f"Cannot stop owned campaign worker group: {exc}") from exc
            deadline = time.monotonic() + allowance
            while time.monotonic() < deadline:
                if _group_alive(process.pid) is False:
                    break
                # Do not poll/reap the leader here: reserving its PID prevents
                # this escalation from addressing a newly reused process ID.
                time.sleep(0.05)
            if _group_alive(process.pid) is False:
                break
        # Escalation is complete. Reaping now is safe: no later signal will use
        # this PID. It also lets group absence establish inactivity on platforms
        # where a process listing was unavailable while the leader was a zombie.
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired as exc:
            raise CampaignProcessError("Campaign worker could not be reaped; inspect before retrying") from exc
        if _group_alive(process.pid) is not False:
            raise CampaignProcessError(
                "Campaign worker group did not stop verifiably; inspect before retrying"
            )


def run_job(
    job_path: Path,
    *,
    on_process: Callable[[dict[str, object]], None] | None = None,
    on_heartbeat: Callable[[dict[str, object]], None] | None = None,
    poll_interval: float = 1.0,
) -> int:
    """Run one isolated worker, reporting identity/heartbeats and its exit code.

    Ctrl-C and SIGTERM stop the owned process group before raising
    KeyboardInterrupt. A callback failure also stops it before propagating.
    Logs are created exclusively; rerunning an existing job is prohibited.
    Exceptions carry stopped_verified=True only when no child was launched for
    this new job or the owned group was verifiably stopped. Existing logs and
    uncertain descendants never supply that proof.
    """
    try:
        _require_posix()
    except CampaignProcessError as exc:
        exc.stopped_verified = True
        raise
    if not 0 < poll_interval <= 60:
        raise CampaignProcessError(
            "Campaign poll interval must be between zero and 60 seconds", stopped_verified=True,
        )
    try:
        job_path = Path(job_path).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise CampaignProcessError(
            f"Cannot access campaign job {job_path}: {exc}", stopped_verified=True,
        ) from exc
    if not job_path.is_file():
        raise CampaignProcessError(
            f"Campaign job is not a regular file: {job_path}", stopped_verified=True,
        )
    logfile = job_path.parent / "worker.log"
    try:
        output = logfile.open("xb")
    except OSError as exc:
        raise CampaignProcessError(
            f"Cannot create immutable campaign worker log {logfile}: {exc}",
            stopped_verified=not isinstance(exc, FileExistsError),
        ) from exc
    previous_term = None
    previous_int = None
    if threading.current_thread() is threading.main_thread():
        def interrupt(signum, frame):
            raise KeyboardInterrupt
        previous_int = signal.getsignal(signal.SIGINT)
        previous_term = signal.signal(signal.SIGTERM, interrupt)
    process = None
    try:
        with output:
            try:
                with _defer_spawn_interrupts():
                    process = subprocess.Popen(
                        [sys.executable, "-m", "nasolve.campaign_worker", str(job_path)],
                        stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                        start_new_session=True, close_fds=True,
                    )
                identity = _identity(process.pid, process.pid)
                if on_process is not None:
                    on_process(dict(identity))
                while True:
                    code = process.poll()
                    if code is not None:
                        if _group_alive(process.pid) is not False:
                            raise CampaignProcessError(
                                "Worker exited with surviving or unidentifiable descendants; inspect before retrying"
                            )
                        return code
                    if on_heartbeat is not None:
                        identity["heartbeat_utc"] = _now()
                        on_heartbeat(dict(identity))
                    time.sleep(poll_interval)
            except BaseException as exc:
                if process is not None:
                    _stop_owned_group(process)
                # A failing cleanup raises its own unverified exception before
                # this assignment. KeyboardInterrupt also retains this proof
                # when it arrived before the process callback could save a PID.
                exc.stopped_verified = True
                raise
    except OSError as exc:
        raise CampaignProcessError(
            f"Cannot launch campaign worker: {exc}",
            stopped_verified=getattr(exc, "stopped_verified", False),
        ) from exc
    finally:
        if previous_int is not None:
            signal.signal(signal.SIGINT, previous_int)
        if previous_term is not None:
            signal.signal(signal.SIGTERM, previous_term)
