# QAOA category: system, domain: technology
"""In-memory registry for managed background processes (Hermes-aligned, kageko paths).

Parity with ClawCode -- same ProcessRegistry, ProcessSession, process_registry singleton.

Tracks processes spawned via ``terminal(background=true)``, with rolling output buffers,
poll/wait/kill, optional checkpoint under ``~/.kageko/processes.json``.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shlex
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .environments.env_vars import sanitize_subprocess_env
from .environments.interrupt import is_interrupted
from .environments.local import find_bash

logger = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"

# Limits (Hermes-compatible)
MAX_OUTPUT_CHARS = 200_000
FINISHED_TTL_SECONDS = 1800
MAX_PROCESSES = 64


def _kageko_home() -> Path:
    custom = os.getenv("KAGEKO_HOME", "").strip()
    if custom:
        return Path(custom).expanduser()
    return Path.home() / ".kageko"


CHECKPOINT_PATH = _kageko_home() / "processes.json"


def _atomic_write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


@dataclass
class ProcessSession:
    """A tracked background process with output buffering."""

    id: str
    command: str
    task_id: str = ""
    session_key: str = ""
    pid: int | None = None
    process: subprocess.Popen[str] | None = None
    env_ref: Any = None
    cwd: str | None = None
    started_at: float = 0.0
    exited: bool = False
    exit_code: int | None = None
    output_buffer: str = ""
    max_output_chars: int = MAX_OUTPUT_CHARS
    detached: bool = False
    watcher_platform: str = ""
    watcher_chat_id: str = ""
    watcher_thread_id: str = ""
    watcher_interval: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _reader_thread: threading.Thread | None = field(default=None, repr=False)
    _pty: Any = field(default=None, repr=False)


class ProcessRegistry:
    """Thread-safe registry of running and finished background processes."""

    _SHELL_NOISE_SUBSTRINGS = (
        "bash: cannot set terminal process group",
        "bash: no job control in this shell",
        "no job control in this shell",
        "cannot set terminal process group",
        "tcsetattr: Inappropriate ioctl for device",
    )

    def __init__(self) -> None:
        self._running: dict[str, ProcessSession] = {}
        self._finished: dict[str, ProcessSession] = {}
        self._lock = threading.Lock()
        self.pending_watchers: list[dict[str, Any]] = []

    @staticmethod
    def _clean_shell_noise(text: str) -> str:
        lines = text.split("\n")
        while lines and any(noise in lines[0] for noise in ProcessRegistry._SHELL_NOISE_SUBSTRINGS):
            lines.pop(0)
        return "\n".join(lines)

    def spawn_local(
        self,
        command: str,
        cwd: str | None = None,
        task_id: str = "",
        session_key: str = "",
        env_vars: dict[str, str] | None = None,
        use_pty: bool = False,
    ) -> ProcessSession:
        """Spawn on the host (``KAGEKO_TERMINAL_ENV=local``)."""
        session = ProcessSession(
            id=f"proc_{uuid.uuid4().hex[:12]}",
            command=command,
            task_id=task_id,
            session_key=session_key,
            cwd=cwd or os.getcwd(),
            started_at=time.time(),
        )

        if use_pty and not _IS_WINDOWS:
            try:
                from ptyprocess import PtyProcess as _PtyProcessCls  # type: ignore[import-untyped]

                user_shell = find_bash()
                pty_env = sanitize_subprocess_env(dict(os.environ), env_vars)
                pty_env["PYTHONUNBUFFERED"] = "1"
                pty_proc = _PtyProcessCls.spawn(
                    [user_shell, "-lic", command],
                    cwd=session.cwd,
                    env=pty_env,
                    dimensions=(30, 120),
                )
                session.pid = pty_proc.pid
                session._pty = pty_proc
                reader = threading.Thread(
                    target=self._pty_reader_loop,
                    args=(session,),
                    daemon=True,
                    name=f"proc-pty-reader-{session.id}",
                )
                session._reader_thread = reader
                reader.start()
                with self._lock:
                    self._prune_if_needed()
                    self._running[session.id] = session
                self._write_checkpoint()
                return session
            except ImportError:
                logger.warning("ptyprocess not installed, falling back to pipe mode")
            except Exception as e:
                logger.warning("PTY spawn failed (%s), falling back to pipe mode", e)
        elif use_pty and _IS_WINDOWS:
            logger.warning("PTY background mode is not supported on Windows; using pipe mode")

        user_shell = find_bash()
        bg_env = sanitize_subprocess_env(dict(os.environ), env_vars)
        bg_env["PYTHONUNBUFFERED"] = "1"
        popen_kw: dict[str, Any] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.PIPE,
            "text": True,
            "cwd": session.cwd,
            "env": bg_env,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if not _IS_WINDOWS:
            popen_kw["preexec_fn"] = os.setsid
        proc = subprocess.Popen([user_shell, "-lic", command], **popen_kw)

        session.process = proc
        session.pid = proc.pid

        reader = threading.Thread(
            target=self._reader_loop,
            args=(session,),
            daemon=True,
            name=f"proc-reader-{session.id}",
        )
        session._reader_thread = reader
        reader.start()

        with self._lock:
            self._prune_if_needed()
            self._running[session.id] = session

        self._write_checkpoint()
        return session

    def spawn_via_env(
        self,
        env: Any,
        command: str,
        cwd: str | None = None,
        task_id: str = "",
        session_key: str = "",
        timeout: int = 10,
    ) -> ProcessSession:
        """Spawn via non-local backend: ``nohup`` + log/pid files + polling (limited vs local)."""
        session = ProcessSession(
            id=f"proc_{uuid.uuid4().hex[:12]}",
            command=command,
            task_id=task_id,
            session_key=session_key,
            cwd=cwd,
            started_at=time.time(),
            env_ref=env,
        )

        log_path = f"/tmp/kageko_bg_{session.id}.log"
        pid_path = f"/tmp/kageko_bg_{session.id}.pid"
        quoted_command = shlex.quote(command)
        bg_command = (
            f"nohup bash -c {quoted_command} > {log_path} 2>&1 & "
            f"echo $! > {pid_path} && cat {pid_path}"
        )

        try:
            result = env.execute(bg_command, timeout=timeout)
            output = str(result.get("output", "")).strip()
            for line in output.splitlines():
                line = line.strip()
                if line.isdigit():
                    session.pid = int(line)
                    break
        except Exception as e:
            session.exited = True
            session.exit_code = -1
            session.output_buffer = f"Failed to start: {e}"

        if not session.exited:
            reader = threading.Thread(
                target=self._env_poller_loop,
                args=(session, env, log_path, pid_path),
                daemon=True,
                name=f"proc-poller-{session.id}",
            )
            session._reader_thread = reader
            reader.start()

        with self._lock:
            self._prune_if_needed()
            self._running[session.id] = session

        self._write_checkpoint()
        return session

    def _reader_loop(self, session: ProcessSession) -> None:
        proc = session.process
        if proc is None or proc.stdout is None:
            return
        first_chunk = True
        try:
            while True:
                chunk = proc.stdout.read(4096)
                if not chunk:
                    break
                if first_chunk:
                    chunk = self._clean_shell_noise(chunk)
                    first_chunk = False
                with session._lock:
                    session.output_buffer += chunk
                    if len(session.output_buffer) > session.max_output_chars:
                        session.output_buffer = session.output_buffer[-session.max_output_chars :]
        except Exception as e:
            logger.debug("Process stdout reader ended: %s", e)

        try:
            proc.wait(timeout=5)
        except Exception as e:
            logger.debug("Process wait timed out or failed: %s", e)
        session.exited = True
        session.exit_code = proc.returncode
        self._move_to_finished(session)

    def _env_poller_loop(self, session: ProcessSession, env: Any, log_path: str, pid_path: str) -> None:
        while not session.exited:
            time.sleep(2)
            try:
                result = env.execute(f"cat {log_path} 2>/dev/null", timeout=10)
                new_output = str(result.get("output", ""))
                if new_output:
                    with session._lock:
                        session.output_buffer = new_output
                        if len(session.output_buffer) > session.max_output_chars:
                            session.output_buffer = session.output_buffer[-session.max_output_chars :]

                check = env.execute(
                    f"kill -0 $(cat {pid_path} 2>/dev/null) 2>/dev/null; echo $?",
                    timeout=5,
                )
                check_output = str(check.get("output", "")).strip()
                if check_output and check_output.splitlines()[-1].strip() != "0":
                    exit_result = env.execute(
                        f"wait $(cat {pid_path} 2>/dev/null) 2>/dev/null; echo $?",
                        timeout=5,
                    )
                    exit_str = str(exit_result.get("output", "")).strip()
                    try:
                        session.exit_code = int(exit_str.splitlines()[-1].strip())
                    except (ValueError, IndexError):
                        session.exit_code = -1
                    session.exited = True
                    self._move_to_finished(session)
                    return

            except Exception:
                session.exited = True
                session.exit_code = -1
                self._move_to_finished(session)
                return

    def _pty_reader_loop(self, session: ProcessSession) -> None:
        pty = session._pty
        if pty is None:
            return
        try:
            while pty.isalive():
                try:
                    chunk = pty.read(4096)
                    if chunk:
                        text = chunk if isinstance(chunk, str) else chunk.decode("utf-8", errors="replace")
                        with session._lock:
                            session.output_buffer += text
                            if len(session.output_buffer) > session.max_output_chars:
                                session.output_buffer = session.output_buffer[-session.max_output_chars :]
                except EOFError:
                    break
                except Exception:
                    break
        except Exception as e:
            logger.debug("PTY stdout reader ended: %s", e)

        try:
            pty.wait()
        except Exception as e:
            logger.debug("PTY wait timed out or failed: %s", e)
        session.exited = True
        session.exit_code = pty.exitstatus if hasattr(pty, "exitstatus") else -1
        self._move_to_finished(session)

    def _move_to_finished(self, session: ProcessSession) -> None:
        env_ref = session.env_ref
        with self._lock:
            self._running.pop(session.id, None)
            self._finished[session.id] = session
        if env_ref is not None and hasattr(env_ref, "cleanup"):
            try:
                env_ref.cleanup()
            except Exception:
                logger.debug("Environment cleanup after process end failed", exc_info=True)
        self._write_checkpoint()

    def get(self, session_id: str) -> ProcessSession | None:
        with self._lock:
            return self._running.get(session_id) or self._finished.get(session_id)

    def poll(self, session_id: str) -> dict[str, Any]:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}

        with session._lock:
            output_preview = session.output_buffer[-1000:] if session.output_buffer else ""

        result: dict[str, Any] = {
            "session_id": session.id,
            "command": session.command,
            "status": "exited" if session.exited else "running",
            "pid": session.pid,
            "uptime_seconds": int(time.time() - session.started_at),
            "output_preview": output_preview,
        }
        if session.exited:
            result["exit_code"] = session.exit_code
        if session.detached:
            result["detached"] = True
            result["note"] = "Process recovered after restart -- output history unavailable"
        return result

    def read_log(self, session_id: str, offset: int = 0, limit: int = 200) -> dict[str, Any]:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}

        with session._lock:
            full_output = session.output_buffer

        lines = full_output.splitlines()
        total_lines = len(lines)

        if offset == 0 and limit > 0:
            selected = lines[-limit:]
        else:
            selected = lines[offset : offset + limit]

        return {
            "session_id": session.id,
            "status": "exited" if session.exited else "running",
            "output": "\n".join(selected),
            "total_lines": total_lines,
            "showing": f"{len(selected)} lines",
        }

    def wait(self, session_id: str, timeout: int | None = None) -> dict[str, Any]:
        default_timeout = int(os.getenv("TERMINAL_TIMEOUT", "180"))
        max_timeout = default_timeout
        requested_timeout = timeout
        timeout_note: str | None = None

        if requested_timeout and requested_timeout > max_timeout:
            effective_timeout = max_timeout
            timeout_note = (
                f"Requested wait of {requested_timeout}s was clamped "
                f"to configured limit of {max_timeout}s"
            )
        else:
            effective_timeout = requested_timeout or max_timeout

        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}

        deadline = time.monotonic() + effective_timeout

        while time.monotonic() < deadline:
            if session.exited:
                result: dict[str, Any] = {
                    "status": "exited",
                    "exit_code": session.exit_code,
                    "output": session.output_buffer[-2000:],
                }
                if timeout_note:
                    result["timeout_note"] = timeout_note
                return result

            if is_interrupted():
                result = {
                    "status": "interrupted",
                    "output": session.output_buffer[-1000:],
                    "note": "User sent a new message -- wait interrupted",
                }
                if timeout_note:
                    result["timeout_note"] = timeout_note
                return result

            time.sleep(1)

        result = {
            "status": "timeout",
            "output": session.output_buffer[-1000:],
        }
        if timeout_note:
            result["timeout_note"] = timeout_note
        else:
            result["timeout_note"] = f"Waited {effective_timeout}s, process still running"
        return result

    def kill_process(self, session_id: str) -> dict[str, Any]:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}

        if session.exited:
            return {
                "status": "already_exited",
                "exit_code": session.exit_code,
            }

        try:
            if session._pty:
                try:
                    session._pty.terminate(force=True)
                except Exception:
                    if session.pid:
                        os.kill(session.pid, signal.SIGTERM)
            elif session.process:
                try:
                    if _IS_WINDOWS:
                        session.process.terminate()
                    else:
                        os.killpg(os.getpgid(session.process.pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    session.process.kill()
            elif session.env_ref and session.pid:
                session.env_ref.execute(f"kill {session.pid} 2>/dev/null", timeout=5)
            session.exited = True
            session.exit_code = -15
            self._move_to_finished(session)
            self._write_checkpoint()
            return {"status": "killed", "session_id": session.id}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def write_stdin(self, session_id: str, data: str) -> dict[str, Any]:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}
        if session.exited:
            return {"status": "already_exited", "error": "Process has already finished"}

        if session._pty:
            try:
                pty_data = data.encode("utf-8") if isinstance(data, str) else data
                session._pty.write(pty_data)
                return {"status": "ok", "bytes_written": len(data)}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        if not session.process or not session.process.stdin:
            return {
                "status": "error",
                "error": "Process stdin not available (non-local backend or stdin closed)",
            }
        try:
            session.process.stdin.write(data)
            session.process.stdin.flush()
            return {"status": "ok", "bytes_written": len(data)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def submit_stdin(self, session_id: str, data: str = "") -> dict[str, Any]:
        return self.write_stdin(session_id, data + "\n")

    def list_sessions(self, task_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            all_sessions = list(self._running.values()) + list(self._finished.values())

        if task_id:
            all_sessions = [s for s in all_sessions if s.task_id == task_id]

        result: list[dict[str, Any]] = []
        for s in all_sessions:
            entry: dict[str, Any] = {
                "session_id": s.id,
                "command": s.command[:200],
                "cwd": s.cwd,
                "pid": s.pid,
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(s.started_at)),
                "uptime_seconds": int(time.time() - s.started_at),
                "status": "exited" if s.exited else "running",
                "output_preview": s.output_buffer[-200:] if s.output_buffer else "",
            }
            if s.exited:
                entry["exit_code"] = s.exit_code
            if s.detached:
                entry["detached"] = True
            result.append(entry)
        return result

    def has_active_processes(self, task_id: str) -> bool:
        with self._lock:
            return any(s.task_id == task_id and not s.exited for s in self._running.values())

    def _prune_if_needed(self) -> None:
        now = time.time()
        expired = [
            sid
            for sid, s in self._finished.items()
            if (now - s.started_at) > FINISHED_TTL_SECONDS
        ]
        for sid in expired:
            del self._finished[sid]

        total = len(self._running) + len(self._finished)
        if total >= MAX_PROCESSES and self._finished:
            oldest_id = min(self._finished, key=lambda sid: self._finished[sid].started_at)
            del self._finished[oldest_id]

    def _append_pending_watcher_unlocked(self, session: ProcessSession) -> None:
        """Append Hermes-shaped watcher dict; caller must hold ``self._lock``."""
        if session.watcher_interval <= 0:
            return
        self.pending_watchers.append(
            {
                "session_id": session.id,
                "check_interval": session.watcher_interval,
                "session_key": session.session_key,
                "task_id": session.task_id,
                "platform": session.watcher_platform,
                "chat_id": session.watcher_chat_id,
                "thread_id": session.watcher_thread_id,
            }
        )

    def enqueue_watcher_for_session(self, session: ProcessSession) -> None:
        """Thread-safe enqueue for tools (e.g. ``terminal`` after spawn)."""
        if session.watcher_interval <= 0:
            return
        with self._lock:
            self._append_pending_watcher_unlocked(session)

    def _write_checkpoint(self) -> None:
        try:
            with self._lock:
                entries = []
                for s in self._running.values():
                    if not s.exited:
                        entries.append(
                            {
                                "session_id": s.id,
                                "command": s.command,
                                "pid": s.pid,
                                "cwd": s.cwd,
                                "started_at": s.started_at,
                                "task_id": s.task_id,
                                "session_key": s.session_key,
                                "watcher_platform": s.watcher_platform,
                                "watcher_chat_id": s.watcher_chat_id,
                                "watcher_thread_id": s.watcher_thread_id,
                                "watcher_interval": s.watcher_interval,
                            }
                        )
            _atomic_write_json(CHECKPOINT_PATH, entries)
        except Exception as e:
            logger.debug("Failed to write checkpoint file: %s", e, exc_info=True)

    def recover_from_checkpoint(self) -> int:
        if not CHECKPOINT_PATH.exists():
            return 0
        try:
            entries = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return 0
        if not isinstance(entries, list):
            return 0

        recovered = 0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            pid = entry.get("pid")
            if not pid:
                continue
            alive = False
            try:
                os.kill(int(pid), 0)
                alive = True
            except (ProcessLookupError, PermissionError, TypeError, ValueError):
                pass
            if alive:
                session = ProcessSession(
                    id=str(entry["session_id"]),
                    command=str(entry.get("command", "unknown")),
                    task_id=str(entry.get("task_id", "")),
                    session_key=str(entry.get("session_key", "")),
                    pid=int(pid),
                    cwd=entry.get("cwd"),
                    started_at=float(entry.get("started_at", time.time())),
                    detached=True,
                    watcher_platform=str(entry.get("watcher_platform", "")),
                    watcher_chat_id=str(entry.get("watcher_chat_id", "")),
                    watcher_thread_id=str(entry.get("watcher_thread_id", "")),
                    watcher_interval=int(entry.get("watcher_interval", 0) or 0),
                )
                with self._lock:
                    self._running[session.id] = session
                    self._append_pending_watcher_unlocked(session)
                recovered += 1
                logger.info("Recovered detached process: %s (pid=%s)", session.command[:60], pid)

        try:
            _atomic_write_json(CHECKPOINT_PATH, [])
        except Exception as e:
            logger.debug("Could not clear checkpoint file: %s", e, exc_info=True)

        return recovered


process_registry = ProcessRegistry()
