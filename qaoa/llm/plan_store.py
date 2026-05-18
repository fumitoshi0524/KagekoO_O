"""Plan artifact persistence for Kageko-compatible /plan workflow.

Parity with ClawCode clawcode/llm/plan_store.py
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..storage_paths import iter_read_candidates, resolve_write_path


@dataclass
class PlanArtifact:
    session_id: str
    user_request: str
    plan_text: str
    created_at: int
    file_path: str


@dataclass
class PlanTaskItem:
    id: str
    title: str
    status: str = "pending"  # pending | in_progress | completed | failed
    details: str = ""
    result_summary: str = ""


@dataclass
class PlanExecutionState:
    is_building: bool = False
    current_task_index: int = -1
    started_at: int = 0
    finished_at: int = 0
    last_progress_at: int = 0
    stall_count: int = 0
    last_error: str = ""
    interrupted: bool = False
    retry_count_by_task: dict[str, int] = field(default_factory=dict)


@dataclass
class PlanBundle:
    session_id: str
    user_request: str
    plan_text: str
    created_at: int
    markdown_path: str
    json_path: str
    tasks: list[PlanTaskItem] = field(default_factory=list)
    execution: PlanExecutionState = field(default_factory=PlanExecutionState)
    routing_meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanBundle":
        tasks_raw = data.get("tasks") if isinstance(data.get("tasks"), list) else []
        tasks: list[PlanTaskItem] = []
        for item in tasks_raw:
            if not isinstance(item, dict):
                continue
            tasks.append(
                PlanTaskItem(
                    id=str(item.get("id") or ""),
                    title=str(item.get("title") or ""),
                    status=str(item.get("status") or "pending"),
                    details=str(item.get("details") or ""),
                    result_summary=str(item.get("result_summary") or ""),
                )
            )
        exe_raw = data.get("execution") if isinstance(data.get("execution"), dict) else {}
        retry_raw = exe_raw.get("retry_count_by_task")
        retry_count_by_task: dict[str, int] = {}
        if isinstance(retry_raw, dict):
            for k, v in retry_raw.items():
                key = str(k).strip()
                if not key:
                    continue
                try:
                    retry_count_by_task[key] = int(v)
                except Exception:
                    continue
        execution = PlanExecutionState(
            is_building=bool(exe_raw.get("is_building", False)),
            current_task_index=int(exe_raw.get("current_task_index", -1)),
            started_at=int(exe_raw.get("started_at", 0)),
            finished_at=int(exe_raw.get("finished_at", 0)),
            last_progress_at=int(exe_raw.get("last_progress_at", 0)),
            stall_count=int(exe_raw.get("stall_count", 0)),
            last_error=str(exe_raw.get("last_error") or ""),
            interrupted=bool(exe_raw.get("interrupted", False)),
            retry_count_by_task=retry_count_by_task,
        )
        return cls(
            session_id=str(data.get("session_id") or ""),
            user_request=str(data.get("user_request") or ""),
            plan_text=str(data.get("plan_text") or ""),
            created_at=int(data.get("created_at", 0)),
            markdown_path=str(data.get("markdown_path") or ""),
            json_path=str(data.get("json_path") or ""),
            tasks=tasks,
            execution=execution,
            routing_meta=data.get("routing_meta") if isinstance(data.get("routing_meta"), dict) else {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_request": self.user_request,
            "plan_text": self.plan_text,
            "created_at": self.created_at,
            "markdown_path": self.markdown_path,
            "json_path": self.json_path,
            "tasks": [asdict(t) for t in self.tasks],
            "execution": asdict(self.execution),
            "routing_meta": self.routing_meta,
        }


class PlanStore:
    """Persist and load plan artifacts from `.qaoa/plans/` with fallback reads."""

    def __init__(self, working_directory: str) -> None:
        self._root = Path(working_directory).expanduser().resolve()
        self._plans_dir = resolve_write_path(self._root, Path("plans") / "_init").parent
        self._plans_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session_id: str, user_request: str, plan_text: str) -> PlanArtifact:
        ts = int(time.time())
        stem = f"plan-{session_id[:8]}-{ts}"
        md_path = self._plans_dir / f"{stem}.md"
        meta_path = self._plans_dir / f"{stem}.json"

        md_path.write_text(plan_text or "", encoding="utf-8")
        meta = {
            "session_id": session_id,
            "user_request": user_request,
            "created_at": ts,
            "markdown_file": md_path.name,
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        return PlanArtifact(
            session_id=session_id,
            user_request=user_request,
            plan_text=plan_text or "",
            created_at=ts,
            file_path=str(md_path),
        )

    def save_bundle(
        self,
        session_id: str,
        user_request: str,
        plan_text: str,
        tasks: list[PlanTaskItem],
    ) -> PlanBundle:
        artifact = self.save(session_id=session_id, user_request=user_request, plan_text=plan_text)
        json_path = Path(artifact.file_path).with_suffix(".json")
        bundle = PlanBundle(
            session_id=session_id,
            user_request=user_request,
            plan_text=plan_text or "",
            created_at=artifact.created_at,
            markdown_path=artifact.file_path,
            json_path=str(json_path),
            tasks=tasks,
            execution=PlanExecutionState(),
        )
        json_path.write_text(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return bundle

    @staticmethod
    def _slugify(name: str) -> str:
        s = (name or "").strip().lower()
        s = re.sub(r"[^a-z0-9]+", "-", s)
        s = re.sub(r"-{2,}", "-", s).strip("-")
        return s or "plan"

    def _next_versioned_stem(self, base_dir: Path, slug: str) -> str:
        """Return `<slug>` or `<slug>-vN` based on existing markdown files."""
        existing = sorted(base_dir.glob(f"{slug}*.md"))
        if not existing:
            return slug
        max_v = 1
        for p in existing:
            stem = p.stem
            if stem == slug:
                max_v = max(max_v, 1)
                continue
            m = re.fullmatch(rf"{re.escape(slug)}-v(\d+)", stem)
            if m:
                try:
                    max_v = max(max_v, int(m.group(1)))
                except Exception:
                    continue
        return f"{slug}-v{max_v + 1}"

    def save_bundle_versioned(
        self,
        session_id: str,
        user_request: str,
        plan_text: str,
        tasks: list[PlanTaskItem],
        *,
        subdir: str = "multi-plan",
        base_name: str = "",
    ) -> PlanBundle:
        """Save plan bundle into a fixed subdir with iterative naming."""
        name_src = (base_name or "").strip() or (user_request or "").strip()
        slug = self._slugify(name_src[:80])
        target_dir = self._plans_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        stem = self._next_versioned_stem(target_dir, slug)
        md_path = target_dir / f"{stem}.md"
        json_path = target_dir / f"{stem}.json"
        ts = int(time.time())

        md_path.write_text(plan_text or "", encoding="utf-8")
        bundle = PlanBundle(
            session_id=session_id,
            user_request=user_request,
            plan_text=plan_text or "",
            created_at=ts,
            markdown_path=str(md_path),
            json_path=str(json_path),
            tasks=tasks,
            execution=PlanExecutionState(),
        )
        json_path.write_text(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return bundle

    def load_markdown(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.is_absolute():
            path = (self._root / path).resolve()
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")

        # Backward/compat fallback: .qaoa -> .qaoa -> .claude
        name = path.name
        for cand in iter_read_candidates(self._root, Path("plans") / name):
            if cand.exists():
                return cand.read_text(encoding="utf-8", errors="replace")
        return ""

    def load_plan_bundle(self, plan_path: str) -> PlanBundle | None:
        md = Path(plan_path)
        if not md.is_absolute():
            md = (self._root / md).resolve()
        json_path = md.with_suffix(".json")
        candidate_json: list[Path] = [json_path]
        if not json_path.exists():
            for cand in iter_read_candidates(self._root, Path("plans") / json_path.name):
                candidate_json.append(cand)
        for cand in candidate_json:
            if not cand.exists():
                continue
            try:
                raw = json.loads(cand.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            if isinstance(raw, dict):
                bundle = PlanBundle.from_dict(raw)
                if not bundle.markdown_path:
                    bundle.markdown_path = str(md)
                if not bundle.json_path:
                    bundle.json_path = str(cand)
                if not bundle.plan_text:
                    bundle.plan_text = self.load_markdown(str(md))
                return bundle
        if not md.exists():
            return None
        # Backward-compat: markdown-only artifact.
        return PlanBundle(
            session_id="",
            user_request="",
            plan_text=self.load_markdown(str(md)),
            created_at=int(time.time()),
            markdown_path=str(md),
            json_path=str(json_path),
            tasks=[],
            execution=PlanExecutionState(),
        )

    def save_plan_bundle(self, bundle: PlanBundle) -> None:
        if not bundle.json_path:
            return
        path = Path(bundle.json_path)
        if not path.is_absolute():
            path = (self._root / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def find_latest_bundle_for_session(self, session_id: str) -> PlanBundle | None:
        """Return the newest saved plan bundle for this session (full JSON with ``tasks`` list).

        Ignores legacy meta-only JSON files from :meth:`save` that have no ``tasks`` key.
        """
        sid = str(session_id or "").strip()
        if not sid:
            return None
        best: tuple[int, int, PlanBundle] | None = None
        for path in self._plans_dir.glob("plan-*.json"):
            try:
                raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            if str(raw.get("session_id") or "").strip() != sid:
                continue
            if not isinstance(raw.get("tasks"), list):
                continue
            bundle = PlanBundle.from_dict(raw)
            if not bundle.json_path:
                bundle.json_path = str(path.resolve())
            created = int(bundle.created_at)
            try:
                mtime_ns = path.stat().st_mtime_ns
            except OSError:
                mtime_ns = 0
            key = (created, mtime_ns)
            if best is None or key > best[:2]:
                best = (created, mtime_ns, bundle)
        return best[2] if best else None

    def find_latest_bundle_for_session_in_subdir(
        self, session_id: str, subdir: str
    ) -> PlanBundle | None:
        """Return newest saved bundle for a session under a specific plans subdir."""
        sid = str(session_id or "").strip()
        sd = str(subdir or "").strip().strip("/\\")
        if not sid or not sd:
            return None
        base = self._plans_dir / sd
        if not base.is_dir():
            return None
        best: tuple[int, int, PlanBundle] | None = None
        for path in base.glob("*.json"):
            try:
                raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            if str(raw.get("session_id") or "").strip() != sid:
                continue
            if not isinstance(raw.get("tasks"), list):
                continue
            bundle = PlanBundle.from_dict(raw)
            if not bundle.json_path:
                bundle.json_path = str(path.resolve())
            if not bundle.markdown_path:
                bundle.markdown_path = str(path.with_suffix(".md").resolve())
            if not bundle.plan_text and bundle.markdown_path:
                bundle.plan_text = self.load_markdown(bundle.markdown_path)
            created = int(bundle.created_at or 0)
            try:
                mtime_ns = path.stat().st_mtime_ns
            except OSError:
                mtime_ns = 0
            key = (created, mtime_ns)
            if best is None or key > best[:2]:
                best = (created, mtime_ns, bundle)
        return best[2] if best else None

    def list_bundles_in_subdir(self, subdir: str, *, limit: int = 100) -> list[PlanBundle]:
        """List bundles under plans subdir ordered by created_at/mtime desc."""
        sd = str(subdir or "").strip().strip("/\\")
        if not sd:
            return []
        base = self._plans_dir / sd
        if not base.is_dir():
            return []
        rows: list[tuple[int, int, PlanBundle]] = []
        for path in base.glob("*.json"):
            try:
                raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            if not isinstance(raw.get("tasks"), list):
                continue
            bundle = PlanBundle.from_dict(raw)
            if not bundle.json_path:
                bundle.json_path = str(path.resolve())
            if not bundle.markdown_path:
                bundle.markdown_path = str(path.with_suffix(".md").resolve())
            created = int(bundle.created_at or 0)
            try:
                mtime_ns = path.stat().st_mtime_ns
            except OSError:
                mtime_ns = 0
            rows.append((created, mtime_ns, bundle))
        rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [b for _, _, b in rows[: max(1, int(limit))]]

    @staticmethod
    def normalize_stale_build_after_restart(bundle: PlanBundle) -> bool:
        """Clear a crashed or killed process's ``is_building`` / ``in_progress`` state.

        Returns whether the bundle was modified (caller may persist with :meth:`save_plan_bundle`).
        """
        changed = False
        if bundle.execution.is_building:
            bundle.execution.is_building = False
            changed = True
            if bundle.execution.current_task_index != -1:
                bundle.execution.current_task_index = -1
                changed = True
        for t in bundle.tasks:
            if t.status == "in_progress":
                t.status = "pending"
                changed = True
        return changed
