"""Persistent task board with dependency tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import json
import uuid
from pathlib import Path


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELETED = "deleted"


@dataclass(slots=True, kw_only=True)
class Task:
    id: str
    subject: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    blocked_by: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "description": self.description,
            "status": self.status.value,
            "blockedBy": self.blocked_by,
            "blocks": self.blocks,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Task:
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            subject=d["subject"],
            description=d.get("description", ""),
            status=TaskStatus(d.get("status", "pending")),
            blocked_by=d.get("blockedBy", []),
            blocks=d.get("blocks", []),
            metadata=d.get("metadata", {}),
        )


@dataclass(slots=True, kw_only=True)
class TaskBoard:
    tasks: dict[str, Task] = field(default_factory=dict)
    persist_path: Path | None = None

    def create(self, subject: str, description: str = "",
               blocked_by: list[str] | None = None) -> Task:
        tid = str(uuid.uuid4())[:8]
        task = Task(id=tid, subject=subject, description=description,
                     blocked_by=blocked_by or [])
        for bid in (blocked_by or []):
            if bid in self.tasks:
                self.tasks[bid].blocks.append(tid)
        self.tasks[tid] = task
        self._persist()
        return task

    def update(self, task_id: str, **kwargs) -> Task | None:
        task = self.tasks.get(task_id)
        if task is None:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        self._persist()
        return task

    def get(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def list_all(self, status: TaskStatus | None = None) -> list[Task]:
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: t.id)
        return tasks

    def available(self) -> list[Task]:
        """Tasks that are pending and not blocked."""
        return [
            t for t in self.tasks.values()
            if t.status == TaskStatus.PENDING
            and all(
                self.tasks.get(bid) and self.tasks[bid].status == TaskStatus.COMPLETED
                for bid in t.blocked_by
            )
        ]

    def delete(self, task_id: str) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.DELETED
            self._persist()

    def _persist(self) -> None:
        if self.persist_path is None:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"tasks": [t.to_dict() for t in self.tasks.values()]}
        self.persist_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self.tasks = {}
        for td in data.get("tasks", []):
            task = Task.from_dict(td)
            self.tasks[task.id] = task
        self.persist_path = path
