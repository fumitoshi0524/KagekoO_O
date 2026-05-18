# QAOA category: system, domain: technology
"""Docker execution environment wrapping mini-swe-agent's DockerEnvironment (Kageko-aligned)."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Optional

from .base import BaseEnvironment, get_sandbox_dir
from .interrupt import is_interrupted

logger = logging.getLogger(__name__)

_DOCKER_SEARCH_PATHS = [
    "/usr/local/bin/docker",
    "/opt/homebrew/bin/docker",
    "/Applications/Docker.app/Contents/Resources/bin/docker",
]

_docker_executable: Optional[str] = None
_ENV_VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _normalize_forward_env_names(forward_env: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in forward_env or []:
        if not isinstance(item, str):
            logger.warning("Ignoring non-string docker_forward_env entry: %r", item)
            continue
        key = item.strip()
        if not key or not _ENV_VAR_NAME_RE.match(key) or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def find_docker() -> Optional[str]:
    global _docker_executable
    if _docker_executable is not None:
        return _docker_executable
    found = shutil.which("docker")
    if found:
        _docker_executable = found
        return found
    for path in _DOCKER_SEARCH_PATHS:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            _docker_executable = path
            logger.info("Found docker at non-PATH location: %s", path)
            return path
    return None


_SECURITY_ARGS = [
    "--cap-drop", "ALL",
    "--cap-add", "DAC_OVERRIDE",
    "--cap-add", "CHOWN",
    "--cap-add", "FOWNER",
    "--security-opt", "no-new-privileges",
    "--pids-limit", "256",
    "--tmpfs", "/tmp:rw,nosuid,size=512m",
    "--tmpfs", "/var/tmp:rw,noexec,nosuid,size=256m",
    "--tmpfs", "/run:rw,noexec,nosuid,size=64m",
]

_storage_opt_ok: Optional[bool] = None


def _ensure_docker_available() -> None:
    docker_exe = find_docker()
    if not docker_exe:
        logger.error("Docker backend selected but no docker executable was found.")
        raise RuntimeError(
            "Docker executable not found in PATH or known install locations. "
            "Install Docker and ensure the 'docker' command is available."
        )
    try:
        result = subprocess.run(
            [docker_exe, "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Docker executable could not be executed. Check your Docker installation."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            "Docker daemon is not responding. Ensure Docker is running and try again."
        )
    except Exception:
        logger.error("Unexpected error while checking Docker availability.", exc_info=True)
        raise
    else:
        if result.returncode != 0:
            raise RuntimeError(
                "Docker command is available but 'docker version' failed. "
                "Check your Docker installation."
            )


def _import_minisweagent_docker() -> Any:
    try:
        from minisweagent.environments.docker import DockerEnvironment as _Docker

        return _Docker
    except ImportError as e:
        raise RuntimeError(
            "Docker backend requires the minisweagent package. "
            "Install: pip install 'kageko[environments-docker]'"
        ) from e


class DockerEnvironment(BaseEnvironment):
    """Hardened Docker container execution (reference ``DockerEnvironment`` aligned)."""

    def __init__(
        self,
        image: str,
        cwd: str = "/root",
        timeout: int = 60,
        env: dict[str, str] | None = None,
        cpu: float = 0,
        memory: int = 0,
        disk: int = 0,
        persistent_filesystem: bool = False,
        task_id: str = "default",
        volumes: list[Any] | None = None,
        forward_env: list[str] | None = None,
        network: bool = True,
        host_cwd: str | None = None,
        auto_mount_cwd: bool = False,
    ) -> None:
        if cwd == "~":
            cwd = "/root"
        super().__init__(cwd=cwd, timeout=timeout, env=env)
        self._base_image = image
        self._persistent = persistent_filesystem
        self._task_id = task_id
        self._forward_env = _normalize_forward_env_names(forward_env)
        self._container_id: Optional[str] = None
        if volumes is not None and not isinstance(volumes, list):
            logger.warning("docker_volumes config is not a list: %r", volumes)
            volumes = []

        _ensure_docker_available()
        _Docker = _import_minisweagent_docker()

        resource_args: list[str] = []
        if cpu > 0:
            resource_args.extend(["--cpus", str(cpu)])
        if memory > 0:
            resource_args.extend(["--memory", f"{memory}m"])
        if disk > 0 and sys.platform != "darwin":
            if self._storage_opt_supported():
                resource_args.extend(["--storage-opt", f"size={disk}m"])
            else:
                logger.warning(
                    "Docker storage driver does not support per-container disk limits."
                )
        if not network:
            resource_args.append("--network=none")

        volume_args: list[str] = []
        workspace_explicitly_mounted = False
        for vol in volumes or []:
            if not isinstance(vol, str):
                logger.warning("Docker volume entry is not a string: %r", vol)
                continue
            vol = vol.strip()
            if not vol or ":" not in vol:
                continue
            volume_args.extend(["-v", vol])
            if ":/workspace" in vol:
                workspace_explicitly_mounted = True

        host_cwd_abs = os.path.abspath(os.path.expanduser(host_cwd)) if host_cwd else ""
        bind_host_cwd = (
            auto_mount_cwd
            and bool(host_cwd_abs)
            and os.path.isdir(host_cwd_abs)
            and not workspace_explicitly_mounted
        )

        self._workspace_dir: Optional[str] = None
        self._home_dir: Optional[str] = None
        writable_args: list[str] = []
        if self._persistent:
            sandbox = get_sandbox_dir() / "docker" / task_id
            self._home_dir = str(sandbox / "home")
            os.makedirs(self._home_dir, exist_ok=True)
            writable_args.extend(["-v", f"{self._home_dir}:/root"])
            if not bind_host_cwd and not workspace_explicitly_mounted:
                self._workspace_dir = str(sandbox / "workspace")
                os.makedirs(self._workspace_dir, exist_ok=True)
                writable_args.extend(["-v", f"{self._workspace_dir}:/workspace"])
        else:
            if not bind_host_cwd and not workspace_explicitly_mounted:
                writable_args.extend(["--tmpfs", "/workspace:rw,exec,size=10g"])
            writable_args.extend([
                "--tmpfs", "/home:rw,exec,size=1g",
                "--tmpfs", "/root:rw,exec,size=1g",
            ])

        if bind_host_cwd:
            logger.info("Mounting host cwd to /workspace: %s", host_cwd_abs)
            volume_args = ["-v", f"{host_cwd_abs}:/workspace", *volume_args]

        all_run_args = list(_SECURITY_ARGS) + writable_args + resource_args + volume_args
        docker_exe = find_docker() or "docker"

        self._inner = _Docker(
            image=image,
            cwd=cwd,
            timeout=timeout,
            run_args=all_run_args,
            executable=docker_exe,
        )
        self._container_id = self._inner.container_id

    @staticmethod
    def _storage_opt_supported() -> bool:
        global _storage_opt_ok
        if _storage_opt_ok is not None:
            return _storage_opt_ok
        try:
            docker = find_docker() or "docker"
            result = subprocess.run(
                [docker, "info", "--format", "{{.Driver}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout.strip().lower() != "overlay2":
                _storage_opt_ok = False
                return False
            probe = subprocess.run(
                [docker, "create", "--storage-opt", "size=1m", "hello-world"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if probe.returncode == 0:
                container_id = probe.stdout.strip()
                if container_id:
                    subprocess.run([docker, "rm", container_id], capture_output=True, timeout=5)
                _storage_opt_ok = True
            else:
                _storage_opt_ok = False
        except Exception:
            _storage_opt_ok = False
        return bool(_storage_opt_ok)

    def execute(
        self,
        command: str,
        cwd: str = "",
        *,
        timeout: int | None = None,
        stdin_data: str | None = None,
    ) -> dict[str, str | int]:
        exec_command, sudo_stdin = self._prepare_command(command)
        work_dir = cwd or self.cwd
        effective_timeout = timeout or self.timeout

        if sudo_stdin is not None and stdin_data is not None:
            effective_stdin = sudo_stdin + stdin_data
        elif sudo_stdin is not None:
            effective_stdin = sudo_stdin
        else:
            effective_stdin = stdin_data

        wd = work_dir or ""
        if wd == "~" or wd.startswith("~/"):
            exec_command = f"cd {work_dir} && {exec_command}"
            work_dir = "/"

        assert self._inner.container_id
        cmd = [self._inner.config.executable, "exec"]
        if effective_stdin is not None:
            cmd.append("-i")
        cmd.extend(["-w", work_dir])
        for key in self._forward_env:
            value = os.getenv(key)
            if value is not None:
                cmd.extend(["-e", f"{key}={value}"])
        for key, value in self._inner.config.env.items():
            cmd.extend(["-e", f"{key}={value}"])
        cmd.extend([self._inner.container_id, "bash", "-lc", exec_command])

        try:
            _output_chunks: list[str] = []
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE if effective_stdin else subprocess.DEVNULL,
                text=True,
            )
            if effective_stdin:
                try:
                    proc.stdin.write(effective_stdin)
                    proc.stdin.close()
                except Exception:
                    pass

            def _drain() -> None:
                try:
                    if proc.stdout:
                        for line in proc.stdout:
                            _output_chunks.append(line)
                except Exception:
                    pass

            reader = threading.Thread(target=_drain, daemon=True)
            reader.start()
            deadline = time.monotonic() + effective_timeout

            while proc.poll() is None:
                if is_interrupted():
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    reader.join(timeout=2)
                    return {
                        "output": "".join(_output_chunks) + "\n[Command interrupted]",
                        "returncode": 130,
                    }
                if time.monotonic() > deadline:
                    proc.kill()
                    reader.join(timeout=2)
                    return self._timeout_result(effective_timeout)
                time.sleep(0.2)

            reader.join(timeout=5)
            rc = proc.returncode
            return {
                "output": "".join(_output_chunks),
                "returncode": int(rc if rc is not None else -1),
            }
        except Exception as e:
            return {"output": f"Docker execution error: {e}", "returncode": 1}

    def cleanup(self) -> None:
        self._inner.cleanup()

        if not self._persistent and self._container_id:
            docker_exe = find_docker() or self._inner.config.executable
            try:
                subprocess.run(
                    [docker_exe, "rm", "-f", self._container_id],
                    capture_output=True,
                    timeout=30,
                )
            except Exception as e:
                logger.warning("Failed to remove container %s: %s", self._container_id, e)
            self._container_id = None

        if not self._persistent:
            for d in (self._workspace_dir, self._home_dir):
                if d:
                    shutil.rmtree(d, ignore_errors=True)
