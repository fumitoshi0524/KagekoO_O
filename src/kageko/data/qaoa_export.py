# src/kageko/data/qaoa_export.py
from __future__ import annotations

import json
from pathlib import Path

from kageko.types import QAOATrajectory


class QAOAExporter:
    """Export QAOA trajectories to JSONL for research/training data."""

    def __init__(self, output_path: str):
        self._path = Path(output_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._buffer: list[dict] = []

    def export(self, trajectory: QAOATrajectory) -> dict:
        """Convert trajectory to a serializable dict and buffer it."""
        record = {
            "query": trajectory.query,
            "steps": [
                {
                    "step": s.step_number,
                    "action": {
                        "tool": s.action.name,
                        "args": s.action.args,
                    },
                    "observation": {
                        "content": s.observation.content,
                        "is_error": s.observation.is_error,
                    },
                }
                for s in trajectory.steps
            ],
            "answer": trajectory.answer,
            "metadata": trajectory.metadata,
        }
        self._buffer.append(record)
        return record

    def flush(self) -> int:
        """Write buffered records to JSONL file. Returns count written."""
        with open(self._path, "a", encoding="utf-8") as f:
            for record in self._buffer:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        count = len(self._buffer)
        self._buffer.clear()
        return count

    def load_all(self) -> list[dict]:
        """Load all trajectories from the JSONL file."""
        if not self._path.exists():
            return []
        records = []
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
