# QAOA category: system, domain: technology
"""Factory for execution environments (reference ``terminal_tool._create_environment`` aligned)."""

from __future__ import annotations

import json
import os
from typing import Any

from .base import BaseEnvironment
from .local import LocalEnvironment


def _default_persistent_flag(explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    v = os.getenv("KAAGEKO_TERMINAL_PERSISTENT", "").strip().lower()
    return v in ("1", "true", "yes")


def _env_str(*keys: str, default: str = "") -> str:
    for k in keys:
        v = os.getenv(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


def _env_bool(*keys: str, default: bool = False) -> bool:
    for k in keys:
        v = os.getenv(k)
        if v is not None:
            return v.strip().lower() in ("1", "true", "yes")
    return default


def _env_int(*keys: str, default: int) -> int:
    for k in keys:
        v = os.getenv(k)
        if v is not None and str(v).strip():
            try:
                return int(v.strip())
            except ValueError:
                pass
    return default


def _env_float(*keys: str, default: float) -> float:
    for k in keys:
        v = os.getenv(k)
        if v is not None and str(v).strip():
            try:
                return float(v.strip())
            except ValueError:
                pass
    return default


def _parse_json_list_env(*keys: str, default: str = "[]") -> list[Any]:
    raw = ""
    for k in keys:
        v = os.getenv(k)
        if v is not None and str(v).strip():
            raw = str(v).strip()
            break
    if not raw:
        raw = default
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _build_docker(
    cwd: str,
    timeout: int,
    env: dict[str, str] | None,
) -> BaseEnvironment:
    from .docker import DockerEnvironment

    image = _env_str(
        "KAAGEKO_TERMINAL_DOCKER_IMAGE",
        "TERMINAL_DOCKER_IMAGE",
        default="nikolaik/python-nodejs:python3.11-nodejs20",
    )
    task_id = _env_str("KAAGEKO_TERMINAL_TASK_ID", default="kageko")
    forward = [str(x) for x in _parse_json_list_env(
        "KAAGEKO_TERMINAL_DOCKER_FORWARD_ENV",
        "TERMINAL_DOCKER_FORWARD_ENV",
    )]
    volumes = _parse_json_list_env(
        "KAAGEKO_TERMINAL_DOCKER_VOLUMES",
        "TERMINAL_DOCKER_VOLUMES",
    )
    cpu = _env_float("KAAGEKO_TERMINAL_CONTAINER_CPU", "TERMINAL_CONTAINER_CPU", default=1.0)
    memory = _env_int("KAAGEKO_TERMINAL_CONTAINER_MEMORY", "TERMINAL_CONTAINER_MEMORY", default=5120)
    disk = _env_int("KAAGEKO_TERMINAL_CONTAINER_DISK", "TERMINAL_CONTAINER_DISK", default=51200)
    persistent = _env_bool(
        "KAAGEKO_TERMINAL_CONTAINER_PERSISTENT",
        "TERMINAL_CONTAINER_PERSISTENT",
        default=True,
    )
    mount_cwd = _env_bool(
        "KAAGEKO_TERMINAL_DOCKER_MOUNT_CWD_TO_WORKSPACE",
        "TERMINAL_DOCKER_MOUNT_CWD_TO_WORKSPACE",
        default=False,
    )
    terminal_cwd = _env_str("KAAGEKO_TERMINAL_CWD", "TERMINAL_CWD", default="")
    default_docker_cwd = "/root"
    host_cwd: str | None = None
    host_prefixes = ("/Users/", "/home/", "C:\\", "C:/")

    if mount_cwd and terminal_cwd:
        candidate = os.path.abspath(os.path.expanduser(terminal_cwd))
        if (
            any(candidate.startswith(p) for p in host_prefixes)
            or (
                os.path.isabs(candidate)
                and os.path.isdir(candidate)
                and not candidate.startswith(("/workspace", "/root"))
            )
        ):
            host_cwd = candidate
            work_cwd = "/workspace"
        else:
            work_cwd = cwd or default_docker_cwd
    elif terminal_cwd and not mount_cwd:
        if any(terminal_cwd.startswith(p) for p in host_prefixes) and terminal_cwd != default_docker_cwd:
            work_cwd = default_docker_cwd
        else:
            work_cwd = terminal_cwd
    else:
        work_cwd = cwd or default_docker_cwd

    eff_timeout = _env_int("KAAGEKO_TERMINAL_TIMEOUT", "TERMINAL_TIMEOUT", default=timeout)

    return DockerEnvironment(
        image=image,
        cwd=work_cwd,
        timeout=eff_timeout,
        env=env,
        cpu=cpu,
        memory=memory,
        disk=disk,
        persistent_filesystem=persistent,
        task_id=task_id,
        volumes=volumes,
        forward_env=forward,
        host_cwd=host_cwd,
        auto_mount_cwd=mount_cwd,
    )


def _build_ssh(
    cwd: str,
    timeout: int,
    env: dict[str, str] | None,
) -> BaseEnvironment:
    from .ssh import SSHEnvironment

    host = _env_str("KAAGEKO_TERMINAL_SSH_HOST", "TERMINAL_SSH_HOST")
    user = _env_str("KAAGEKO_TERMINAL_SSH_USER", "TERMINAL_SSH_USER")
    if not host or not user:
        raise ValueError(
            "SSH backend requires KAAGEKO_TERMINAL_SSH_HOST and KAAGEKO_TERMINAL_SSH_USER "
            "(or TERMINAL_SSH_HOST / TERMINAL_SSH_USER)."
        )
    port = _env_int("KAAGEKO_TERMINAL_SSH_PORT", "TERMINAL_SSH_PORT", default=22)
    key = _env_str("KAAGEKO_TERMINAL_SSH_KEY", "TERMINAL_SSH_KEY")
    ssh_cwd = cwd or _env_str("KAAGEKO_TERMINAL_CWD", "TERMINAL_CWD", default="~")
    eff_timeout = _env_int("KAAGEKO_TERMINAL_TIMEOUT", "TERMINAL_TIMEOUT", default=timeout)
    ssh_persist = _env_bool("KAAGEKO_TERMINAL_SSH_PERSISTENT", "TERMINAL_SSH_PERSISTENT")
    if os.getenv("KAAGEKO_TERMINAL_SSH_PERSISTENT") is None and os.getenv("TERMINAL_SSH_PERSISTENT") is None:
        ssh_persist = _env_bool("TERMINAL_PERSISTENT_SHELL", default=True)
    return SSHEnvironment(
        host=host,
        user=user,
        cwd=ssh_cwd,
        timeout=eff_timeout,
        port=port,
        key_path=key,
        persistent=ssh_persist,
        env=env,
    )


def create_environment(
    env_type: str | None = None,
    cwd: str = "",
    timeout: int = 60,
    env: dict[str, str] | None = None,
    *,
    persistent: bool | None = None,
) -> BaseEnvironment:
    """Instantiate a backend.

    ``env_type`` defaults to ``KAAGEKO_TERMINAL_ENV`` or ``"local"``.

    For ``local`` only: ``persistent`` defaults from ``KAAGEKO_TERMINAL_PERSISTENT``.

    Docker reads ``KAAGEKO_TERMINAL_DOCKER_*`` and ``KAAGEKO_TERMINAL_CONTAINER_*``
    (``TERMINAL_*`` names accepted as fallback). SSH requires host/user env vars.

    Raises:
        RuntimeError: e.g. Docker without minisweagent.
        ValueError: Unknown type or missing SSH configuration.
    """
    t = (env_type or os.getenv("KAAGEKO_TERMINAL_ENV") or "local").strip().lower()
    pers = _default_persistent_flag(persistent)
    if t == "local":
        return LocalEnvironment(cwd=cwd, timeout=timeout, env=env, persistent=pers)

    if t == "docker":
        return _build_docker(cwd=cwd, timeout=timeout, env=env)

    if t == "ssh":
        return _build_ssh(cwd=cwd, timeout=timeout, env=env)

    if t == "modal":
        from .modal import ModalEnvironment

        return ModalEnvironment(cwd=cwd, timeout=timeout, env=env)

    if t == "daytona":
        from .daytona import DaytonaEnvironment

        return DaytonaEnvironment(cwd=cwd, timeout=timeout, env=env)

    if t in ("singularity", "apptainer"):
        from .singularity import SingularityEnvironment

        return SingularityEnvironment(cwd=cwd, timeout=timeout, env=env)

    raise ValueError(f"Unknown KAAGEKO terminal environment: {t!r}")
