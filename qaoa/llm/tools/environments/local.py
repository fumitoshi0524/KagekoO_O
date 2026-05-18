# QAOA category: system, domain: technology
"""Local host execution (reference ``LocalEnvironment`` pattern; optional persistent shell)."""

from __future__ import annotations

import glob
import os
import platform
import shutil
import signal
import subprocess
import tempfile
import threading
import time

from .base import BaseEnvironment
from .env_vars import _LEGACY_GIT_BASH_ENV_KEY, merge_run_env
from .interrupt import is_interrupted
from .persistent_shell import PersistentShellMixin, _shell_fs_path
from .shell_oneshot import extract_fenced_output, fenced_login_command

_IS_WINDOWS = platform.system() == "Windows"


def find_bash() -> str:
    """Resolve bash for ``bash -c`` / login shell wrapping (Git Bash on Windows)."""
    if not _IS_WINDOWS:
        return shutil.which("bash") or "/bin/sh"

    custom = os.environ.get("KAAGEKO_GIT_BASH_PATH") or os.environ.get(_LEGACY_GIT_BASH_ENV_KEY)
    if custom and os.path.isfile(custom):
        return custom

    for candidate in (
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Git", "bin", "bash.exe"),
        os.path.join(
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            "Git",
            "bin",
            "bash.exe",
        ),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Git", "bin", "bash.exe"),
    ):
        if candidate and os.path.isfile(candidate):
            return candidate

    found = shutil.which("bash")
    if found and os.path.isfile(found):
        return found

    raise RuntimeError(
        "bash not found. On Windows install Git for Windows or set KAAGEKO_GIT_BASH_PATH to bash.exe."
    )


class LocalEnvironment(PersistentShellMixin, BaseEnvironment):
    """Run commands on the host; optional persistent ``bash -l`` session (Kageko-aligned)."""

    def __init__(
        self,
        cwd: str = "",
        timeout: int = 60,
        env: dict[str, str] | None = None,
        *,
        persistent: bool = False,
    ) -> None:
        super().__init__(cwd=cwd or os.getcwd(), timeout=timeout, env=env)
        self.persistent = persistent
        self._shell = find_bash()
        if self.persistent:
            self._init_persistent_shell()

    @property
    def _temp_prefix(self) -> str:
        base = os.path.join(
            tempfile.gettempdir(),
            f"kageko-local-{self._session_id}",
        )
        return _shell_fs_path(base)

    def _spawn_shell_process(self) -> subprocess.Popen[str]:
        run_env = merge_run_env(None, self.env)
        if _IS_WINDOWS:
            return subprocess.Popen(
                [self._shell, "-l"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                env=run_env,
            )
        return subprocess.Popen(
            [self._shell, "-l"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=run_env,
            preexec_fn=os.setsid,
        )

    def _read_temp_files(self, *paths: str) -> list[str]:
        results: list[str] = []
        for path in paths:
            p = path.replace("/", os.sep) if os.sep != "/" else path
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    results.append(f.read())
            else:
                results.append("")
        return results

    def _kill_shell_children(self) -> None:
        if self._shell_pid is None:
            return
        if _IS_WINDOWS:
            try:
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"(Get-CimInstance Win32_Process -Filter \"ParentProcessId={self._shell_pid}\" "
                        f").ProcessId | ForEach-Object {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}",
                    ],
                    capture_output=True,
                    timeout=15,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
            return
        try:
            subprocess.run(
                ["pkill", "-P", str(self._shell_pid)],
                capture_output=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def _cleanup_temp_files(self) -> None:
        pattern = f"{self._temp_prefix}-*"
        for f in glob.glob(pattern):
            try:
                if os.path.isfile(f):
                    os.remove(f)
            except OSError:
                pass

    def _execute_oneshot(
        self,
        command: str,
        cwd: str = "",
        *,
        timeout: int | None = None,
        stdin_data: str | None = None,
    ) -> dict[str, str | int]:
        work_dir = cwd or self.cwd or os.getcwd()
        effective_timeout = timeout if timeout is not None else self.timeout
        exec_command, sudo_stdin = self._prepare_command(command)

        if sudo_stdin is not None and stdin_data is not None:
            effective_stdin = sudo_stdin + stdin_data
        elif sudo_stdin is not None:
            effective_stdin = sudo_stdin
        else:
            effective_stdin = stdin_data

        run_env = merge_run_env(None, self.env)
        fenced_cmd = fenced_login_command(exec_command)

        proc = subprocess.Popen(
            [self._shell, "-lic", fenced_cmd],
            text=True,
            cwd=work_dir,
            env=run_env,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE if effective_stdin is not None else subprocess.DEVNULL,
            preexec_fn=None if _IS_WINDOWS else os.setsid,
        )

        if effective_stdin is not None:

            def _write_stdin() -> None:
                try:
                    proc.stdin.write(effective_stdin)
                    proc.stdin.close()
                except (BrokenPipeError, OSError):
                    pass

            threading.Thread(target=_write_stdin, daemon=True).start()

        _output_chunks: list[str] = []

        def _drain_stdout() -> None:
            try:
                if proc.stdout:
                    for line in proc.stdout:
                        _output_chunks.append(line)
            except ValueError:
                pass
            finally:
                try:
                    if proc.stdout:
                        proc.stdout.close()
                except Exception:
                    pass

        reader = threading.Thread(target=_drain_stdout, daemon=True)
        reader.start()
        deadline = time.monotonic() + effective_timeout

        while proc.poll() is None:
            if is_interrupted():
                try:
                    if _IS_WINDOWS:
                        proc.terminate()
                    else:
                        pgid = os.getpgid(proc.pid)
                        os.killpg(pgid, signal.SIGTERM)
                        try:
                            proc.wait(timeout=1.0)
                        except subprocess.TimeoutExpired:
                            os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
                reader.join(timeout=2)
                return {
                    "output": "".join(_output_chunks)
                    + "\n[Command interrupted — user sent a new message]",
                    "returncode": 130,
                }
            if time.monotonic() > deadline:
                try:
                    if _IS_WINDOWS:
                        proc.terminate()
                    else:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
                reader.join(timeout=2)
                return self._timeout_result(effective_timeout)
            time.sleep(0.2)

        reader.join(timeout=5)
        output = extract_fenced_output("".join(_output_chunks))
        rc = proc.returncode
        return {"output": output, "returncode": int(rc if rc is not None else -1)}
