# tests/unit/test_qaoa_export.py
import json
import pytest
from pathlib import Path
from kageko.data.qaoa_export import QAOAExporter
from kageko.types import QAOATrajectory, ToolCall, ToolResult


def test_trajectory_to_dict():
    traj = QAOATrajectory(query="read config")
    traj.step(
        ToolCall(id="c1", name="file_read", args={"path": "config.py"}),
        ToolResult(tool_call_id="c1", content="model = gpt-4o"),
    )
    traj.set_answer("Config sets model to gpt-4o")

    d = _traj_to_dict(traj)
    assert d["query"] == "read config"
    assert len(d["steps"]) == 1
    assert d["steps"][0]["action"]["tool"] == "file_read"
    assert d["answer"] == "Config sets model to gpt-4o"


def _traj_to_dict(traj):
    return {
        "query": traj.query,
        "steps": [
            {
                "step": s.step_number,
                "action": {"tool": s.action.name, "args": s.action.args},
                "observation": {"content": s.observation.content},
            }
            for s in traj.steps
        ],
        "answer": traj.answer,
    }


def test_export_to_jsonl(tmp_path):
    exporter = QAOAExporter(str(tmp_path / "trajectories.jsonl"))

    traj = QAOATrajectory(query="test query")
    traj.step(
        ToolCall(id="c1", name="echo", args={"text": "hi"}),
        ToolResult(tool_call_id="c1", content="hi"),
    )
    traj.set_answer("done")

    exporter.export(traj)
    exporter.flush()

    content = (tmp_path / "trajectories.jsonl").read_text()
    lines = [l for l in content.strip().split("\n") if l]
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["query"] == "test query"


def test_export_batch(tmp_path):
    exporter = QAOAExporter(str(tmp_path / "batch.jsonl"))

    for i in range(3):
        traj = QAOATrajectory(query=f"query {i}")
        traj.set_answer(f"answer {i}")
        exporter.export(traj)

    exporter.flush()

    lines = (tmp_path / "batch.jsonl").read_text().strip().split("\n")
    assert len(lines) == 3
