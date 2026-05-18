"""Plan markdown -> executable task list splitter.

Parity with ClawCode clawcode/llm/plan_tasks.py
"""

from __future__ import annotations

import re

from .plan_store import PlanTaskItem


_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.+?)\s*$")
_HEADING_RE = re.compile(r"^\s{0,3}#{2,6}\s+(.+?)\s*$")


def _clean_title(raw: str) -> str:
    text = (raw or "").strip()
    text = re.sub(r"`+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_plan_to_tasks(plan_text: str, *, max_tasks: int = 12) -> list[PlanTaskItem]:
    """Split a plan markdown into a stable list of small executable tasks."""
    lines = (plan_text or "").splitlines()

    # Strategy 1: explicit bullet/ordered steps.
    tasks: list[PlanTaskItem] = []
    for line in lines:
        m = _LIST_RE.match(line)
        if not m:
            continue
        title = _clean_title(m.group(1))
        if not title:
            continue
        tasks.append(PlanTaskItem(id=f"task-{len(tasks)+1}", title=title))
        if len(tasks) >= max_tasks:
            return tasks

    if tasks:
        return tasks

    # Strategy 2: section headings as tasks.
    for line in lines:
        m = _HEADING_RE.match(line)
        if not m:
            continue
        title = _clean_title(m.group(1))
        if not title:
            continue
        tasks.append(PlanTaskItem(id=f"task-{len(tasks)+1}", title=title))
        if len(tasks) >= max_tasks:
            return tasks

    if tasks:
        return tasks

    # Strategy 3: fallback coarse tasks.
    fallback = [
        "梳理并确认实现边界",
        "实现核心代码变更",
        "补充测试并回归验证",
    ]
    return [PlanTaskItem(id=f"task-{i+1}", title=t) for i, t in enumerate(fallback[:max_tasks])]


def compose_task_execution_prompt(plan_text: str, task: PlanTaskItem) -> str:
    details = (task.details or "").strip()
    details_block = f"\nTask details:\n{details}\n" if details else "\n"
    return (
        "Execute ONLY the current task from the approved plan. "
        "Do not expand scope to other tasks.\n\n"
        f"Approved plan:\n{plan_text.strip()}\n\n"
        f"Current task:\n- {task.title}\n"
        f"{details_block}\n"
        "Return concise progress and finish after completing this task."
    )
