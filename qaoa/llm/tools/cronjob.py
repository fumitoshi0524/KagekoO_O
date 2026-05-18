"""cronjob tool -- Hermes cron entrypoint (Kageko-local implementation).

Parity with ClawCode -- same CronjobTool, create_cronjob_tool, _CronRegistry,
_CronJob, _CronRun.

Hermes provides rich cron orchestration backed by its cron subsystem.
For Kageko's local implementation (and testability), we implement a compact
in-memory scheduler with the same *capability entrypoint*:

- action="schedule": create a job and start a repeating loop (best-effort)
- action="run_now": execute immediately (returns a run_id)
- action="list": list jobs
- action="poll": poll job runs (latest or by run_id)
- action="stop": disable a job and cancel its loop

Security model:
  - kind="shell": delegated to execute_code sandbox helpers which perform
    permission checks for "unsafe" commands when permissions are available.
  - kind="python": sandboxed; still supports permission request gating at
    schedule/run_now time (best-effort).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ...core.permission import PermissionRequest
from .base import BaseTool, ToolCall, ToolContext, ToolInfo, ToolResponse
from .execute_code import _run_python_sandbox, _run_shell_command


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


@dataclass
class _CronRun:
    run_id: str
    job_id: str
    created_at: float
    done: bool = False
    result: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class _CronJob:
    job_id: str
    kind: str
    code_or_command: str
    interval_s: float
    timeout_s: float
    max_runs: int | None
    created_at: float
    enabled: bool = True
    next_run_at: float | None = None
    run_ids: list[str] = field(default_factory=list)
    _task: asyncio.Task[None] | None = None
    _python_permission_granted: bool = False


class _CronRegistry:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._jobs: dict[str, _CronJob] = {}
        self._runs: dict[str, _CronRun] = {}

    async def create_job(
        self,
        *,
        kind: str,
        code_or_command: str,
        interval_s: float,
        timeout_s: float,
        max_runs: int | None,
        context: ToolContext,
        permissions: Any,
    ) -> str:
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        now = time.time()
        job = _CronJob(
            job_id=job_id,
            kind=kind,
            code_or_command=code_or_command,
            interval_s=interval_s,
            timeout_s=timeout_s,
            max_runs=max_runs,
            created_at=now,
            next_run_at=now + interval_s,
        )

        # For python kind, request permission once at job creation time (best-effort).
        if kind == "python" and permissions:
            req = PermissionRequest(
                tool_name="cronjob",
                description=f"cronjob python: {code_or_command[:200]}",
                path=context.working_directory,
                input={"kind": kind, "timeout_s": None, "interval_s": interval_s},
                session_id=context.session_id,
            )
            resp = await permissions.request(req)
            job._python_permission_granted = bool(getattr(resp, "granted", False))

        async with self._lock:
            self._jobs[job_id] = job

        # Start loop outside lock.
        job._task = asyncio.create_task(self._job_loop(job_id, context, permissions))
        return job_id

    async def _execute_one_run(self, job: _CronJob, context: ToolContext, permissions: Any) -> str:
        run_id = f"run_{uuid.uuid4().hex[:10]}"
        run = _CronRun(run_id=run_id, job_id=job.job_id, created_at=time.time())
        async with self._lock:
            self._runs[run_id] = run
            job.run_ids.append(run_id)

        try:
            if job.kind == "shell":
                result = await _run_shell_command(
                    command=job.code_or_command,
                    timeout_s=float(job.timeout_s),
                    cwd=context.working_directory,
                    task_context=context,
                    permissions=permissions,
                )
            else:
                if not job._python_permission_granted and permissions:
                    result = {
                        "success": False,
                        "kind": "python",
                        "error": "Permission denied for cronjob python",
                        "stdout": "",
                        "stderr": "",
                        "returncode": 1,
                    }
                else:
                    # Python cron has "interval_s" as a rough timeout budget by default.
                    result = await _run_python_sandbox(
                        code=job.code_or_command,
                        timeout_s=float(job.timeout_s),
                        cwd=context.working_directory,
                        session_id=context.session_id,
                    )

            async with self._lock:
                run.done = True
                run.result = result
        except Exception as e:
            async with self._lock:
                run.done = True
                run.error = str(e)
                run.result = {
                    "success": False,
                    "kind": job.kind,
                    "error": str(e),
                    "stdout": "",
                    "stderr": "",
                    "returncode": 1,
                }

        return run_id

    async def _job_loop(self, job_id: str, context: ToolContext, permissions: Any) -> None:
        # Best-effort loop: interval_s spacing; no cron parsing here.
        while True:
            async with self._lock:
                job = self._jobs.get(job_id)
                if not job or not job.enabled:
                    return
                if job.max_runs is not None and len(job.run_ids) >= job.max_runs:
                    job.enabled = False
                    return
                interval = float(job.interval_s)
                next_at = time.time() + interval

                # Update next_run_at for polling UX.
                job.next_run_at = next_at

            await asyncio.sleep(max(0.0, interval))

            async with self._lock:
                job2 = self._jobs.get(job_id)
                if not job2 or not job2.enabled:
                    return
                if job2.max_runs is not None and len(job2.run_ids) >= job2.max_runs:
                    job2.enabled = False
                    return
                # Execute outside lock to avoid blocking other tool calls.
                job_ref = job2

            await self._execute_one_run(job_ref, context, permissions)

    async def run_now(self, *, job_id: str, context: ToolContext, permissions: Any) -> str | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job or not job.enabled:
                return None
            # Execute even if it's beyond max_runs (best-effort), but if max_runs
            # already reached we treat as no-op.
            if job.max_runs is not None and len(job.run_ids) >= job.max_runs:
                return None
            job_ref = job
        return await self._execute_one_run(job_ref, context, permissions)

    async def stop(self, *, job_id: str) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            job.enabled = False
            task = job._task
            job._task = None

        if task:
            task.cancel()
            # Do not await canceled task: on some platforms (esp. Windows)
            # awaiting a canceled loop that spawned subprocess pipes may
            # surface noisy asyncio InvalidStateError at teardown.
            # Enabled=false + cancellation is enough to stop future triggers.
        return True

    async def list_jobs(self) -> dict[str, Any]:
        async with self._lock:
            jobs = []
            for job in self._jobs.values():
                jobs.append(
                    {
                        "job_id": job.job_id,
                        "kind": job.kind,
                        "schedule": f"interval={job.interval_s}s",
                        "enabled": job.enabled,
                        "next_run_at": job.next_run_at,
                        "max_runs": job.max_runs,
                        "run_count": len(job.run_ids),
                    }
                )
            return {"success": True, "count": len(jobs), "jobs": jobs}

    async def poll(
        self,
        *,
        job_id: str,
        run_id: str | None,
        include_output: bool = True,
    ) -> dict[str, Any]:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"success": False, "error": f"Unknown job_id: {job_id}"}

            target_run_id: str | None = run_id
            if not target_run_id:
                # Poll latest.
                target_run_id = job.run_ids[-1] if job.run_ids else None

            if not target_run_id:
                return {
                    "success": True,
                    "job_id": job_id,
                    "enabled": job.enabled,
                    "next_run_at": job.next_run_at,
                    "runs": [],
                    "latest": None,
                }

            run = self._runs.get(target_run_id)
            if not run:
                return {"success": False, "error": f"Unknown run_id: {target_run_id}"}

            def _fmt_run(rid: str) -> dict[str, Any]:
                r = self._runs.get(rid)
                if not r:
                    return {"run_id": rid, "done": False}
                out: dict[str, Any] = {"run_id": r.run_id, "done": r.done, "created_at": r.created_at}
                if include_output and r.result is not None:
                    out["result"] = r.result
                if include_output and r.error:
                    out["error"] = r.error
                return out

            latest = _fmt_run(target_run_id) if include_output else {"run_id": target_run_id}

            return {
                "success": True,
                "job_id": job_id,
                "enabled": job.enabled,
                "next_run_at": job.next_run_at,
                "runs": [_fmt_run(rid) for rid in job.run_ids] if include_output else [],
                "latest": latest,
            }


_registry = _CronRegistry()


class CronjobTool(BaseTool):
    def __init__(self, permissions: Any = None) -> None:
        self._permissions = permissions

    def info(self) -> ToolInfo:
        return ToolInfo(
            name="cronjob",
            category="system",
            domain="technology",
            description=(
                "Schedule and manage repeated execution jobs (Hermes-aligned entrypoint, "
                "Kageko-local in-memory scheduler). Actions: schedule/list/poll/stop/run_now."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["schedule", "list", "poll", "stop", "run_now"],
                        "description": "Cronjob action.",
                    },
                    "job_id": {"type": "string", "description": "Target job id (for poll/stop/run_now)."},
                    "run_id": {"type": "string", "description": "Optional run id (for poll)."},
                    "kind": {
                        "type": "string",
                        "enum": ["shell", "python"],
                        "description": "Execution kind for schedule.",
                    },
                    "code": {
                        "type": "string",
                        "description": "Python code (kind=python) or shell command (kind=shell).",
                    },
                    "interval_s": {"type": "number", "description": "Repeat interval seconds (best-effort).", "default": 5},
                    "timeout_s": {
                        "type": "number",
                        "description": "Execution timeout seconds per run.",
                        "default": 30,
                    },
                    "max_runs": {"type": "integer", "description": "Max runs for this job (optional)."},
                },
                "required": ["action"],
            },
            required=["action"],
        )

    @property
    def is_dangerous(self) -> bool:
        return True

    async def run(self, call: ToolCall, context: ToolContext) -> ToolResponse:
        params = call.get_input_dict()
        action = str(params.get("action", "")).strip().lower()
        job_id = params.get("job_id")
        run_id = params.get("run_id")

        try:
            if action == "list":
                resp = await _registry.list_jobs()
                return ToolResponse(content=_json_dump(resp), is_error=not bool(resp.get("success")))

            if action == "schedule":
                kind = str(params.get("kind", "")).strip().lower()
                if kind not in {"shell", "python"}:
                    payload = {"success": False, "error": "Invalid kind; expected shell/python"}
                    return ToolResponse(content=_json_dump(payload), is_error=True)
                code = params.get("code")
                if not isinstance(code, str) or not code.strip():
                    payload = {"success": False, "error": "Missing code/command for schedule"}
                    return ToolResponse(content=_json_dump(payload), is_error=True)
                interval_s = float(params.get("interval_s", 5) or 5)
                timeout_s = float(params.get("timeout_s", 30) or 30)
                max_runs_raw = params.get("max_runs")
                max_runs: int | None
                if max_runs_raw is None or str(max_runs_raw).strip() == "":
                    max_runs = None
                else:
                    max_runs = int(max_runs_raw)
                    if max_runs <= 0:
                        max_runs = None

                created = await _registry.create_job(
                    kind=kind,
                    code_or_command=code,
                    interval_s=interval_s,
                    timeout_s=timeout_s,
                    max_runs=max_runs,
                    context=context,
                    permissions=self._permissions,
                )
                return ToolResponse(
                    content=_json_dump({"success": True, "job_id": created, "message": "Job scheduled."}),
                )

            if action == "poll":
                if not job_id or not isinstance(job_id, str):
                    payload = {"success": False, "error": "job_id is required for poll"}
                    return ToolResponse(content=_json_dump(payload), is_error=True)
                resp = await _registry.poll(
                    job_id=job_id,
                    run_id=str(run_id) if run_id else None,
                    include_output=True,
                )
                return ToolResponse(content=_json_dump(resp), is_error=not bool(resp.get("success")))

            if action == "stop":
                if not job_id or not isinstance(job_id, str):
                    payload = {"success": False, "error": "job_id is required for stop"}
                    return ToolResponse(content=_json_dump(payload), is_error=True)
                ok = await _registry.stop(job_id=job_id)
                return ToolResponse(
                    content=_json_dump({"success": True, "job_id": job_id, "stopped": ok}),
                    is_error=not ok,
                )

            if action == "run_now":
                if not job_id or not isinstance(job_id, str):
                    payload = {"success": False, "error": "job_id is required for run_now"}
                    return ToolResponse(content=_json_dump(payload), is_error=True)
                rid = await _registry.run_now(job_id=job_id, context=context, permissions=self._permissions)
                if rid is None:
                    payload = {"success": False, "error": "Job disabled or max_runs reached"}
                    return ToolResponse(content=_json_dump(payload), is_error=True)
                return ToolResponse(content=_json_dump({"success": True, "job_id": job_id, "run_id": rid}))

            payload = {"success": False, "error": f"Unknown cron action '{action}'"}
            return ToolResponse(content=_json_dump(payload), is_error=True)
        except Exception as e:
            payload = {"success": False, "error": str(e)}
            return ToolResponse(content=_json_dump(payload), is_error=True)


def create_cronjob_tool(permissions: Any = None) -> CronjobTool:
    return CronjobTool(permissions=permissions)


__all__ = ["create_cronjob_tool", "CronjobTool"]
