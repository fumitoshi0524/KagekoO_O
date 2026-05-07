"""QAOA pipeline CLI: synthetic data, benchmark prediction, and strict evaluation."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.metadata
import json
from pathlib import Path

try:
    __version__ = importlib.metadata.version("KagekoO_O")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.1.0"

from qaoa.learning import (
    evaluate_qaoa_predictions,
    export_qaoa_conversations_jsonl,
    export_qaoa_jsonl,
    export_sft_jsonl,
    load_qaoa_jsonl,
    synthesize_qaoa_turns,
)
from qaoa.adapters.builtins import BuiltinToolPack
from qaoa.adapters.tools import ToolRegistry
from qaoa.runtime import create_runtime
from qaoa.types import AgentMode, QAOATurn


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kageko-qaoa",
        description="QAOA data + benchmark pipeline for Kageko",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    synth = subparsers.add_parser("synth", help="Generate synthetic QAOA trajectories")
    synth.add_argument("--output", required=True, help="Output JSONL path")
    synth.add_argument("--workspace", help="Workspace root for tool discovery")
    synth.add_argument("--skills-dir", help="Skills directory")
    synth.add_argument("--examples-per-tool", type=int, default=2, help="Examples per tool")
    synth.add_argument("--sft-output", help="Optional SFT JSONL output path")

    benchmark = subparsers.add_parser("benchmark", help="Run runtime benchmark on QAOA dataset")
    benchmark.add_argument("--input", required=True, help="Reference QAOA JSONL path")
    benchmark.add_argument("--output", required=True, help="Predictions QAOA JSONL path")
    benchmark.add_argument("--provider", choices=["openai", "deepseek", "claude", "gemini"])
    benchmark.add_argument("--api-key", help="Provider API key override")
    benchmark.add_argument("--model", help="Model name")
    benchmark.add_argument("--base-url", help="Custom provider base URL")
    benchmark.add_argument("--workspace", help="Workspace root")
    benchmark.add_argument("--skills-dir", help="Skills directory")
    benchmark.add_argument("--enable-rag", action="store_true", help="Enable retriever tools")
    benchmark.add_argument("--rag-persist-dir", help="RAG persist directory")
    benchmark.add_argument("--enable-mcp", action="store_true", help="Enable MCP tools")
    benchmark.add_argument("--mcp-server-url", help="MCP server URL")

    evaluate = subparsers.add_parser("eval", help="Evaluate predicted QAOA JSONL against reference")
    evaluate.add_argument("--reference", required=True, help="Reference QAOA JSONL path")
    evaluate.add_argument("--predicted", required=True, help="Predicted QAOA JSONL path")

    sft = subparsers.add_parser("export-sft", help="Convert QAOA JSONL to SFT JSONL")
    sft.add_argument("--input", required=True, help="Input QAOA JSONL path")
    sft.add_argument("--output", required=True, help="Output SFT JSONL path")

    return parser


def _run_synth(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve() if args.workspace else Path.cwd().resolve()
    skills_dir = Path(args.skills_dir).resolve() if args.skills_dir else None
    registry = ToolRegistry()
    BuiltinToolPack(workspace=workspace, skills_dir=skills_dir).register(registry)

    turns = synthesize_qaoa_turns(
        tool_specs=registry.list_specs(),
        examples_per_tool=args.examples_per_tool,
    )
    output_path = Path(args.output).resolve()
    export_qaoa_jsonl(turns=turns, output_path=output_path)
    print(f"wrote_qaoa_turns={len(turns)} output={output_path}")

    if args.sft_output:
        sft_path = Path(args.sft_output).resolve()
        export_sft_jsonl(turns=turns, output_path=sft_path)
        print(f"wrote_sft_examples={len(turns)} output={sft_path}")
    return 0


def _run_benchmark(args: argparse.Namespace) -> int:
    reference_conversations = load_qaoa_jsonl(Path(args.input).resolve())
    runtime = create_runtime(
        provider=args.provider,
        api_key=args.api_key,
        model=args.model,
        base_url=args.base_url,
        workspace=args.workspace,
        skills_dir=args.skills_dir,
        enable_rag=args.enable_rag,
        rag_persist_dir=args.rag_persist_dir,
        enable_mcp=args.enable_mcp,
        mcp_server_url=args.mcp_server_url,
    )

    predicted_conversations: dict[str, list[QAOATurn]] = {}
    for conversation_id in sorted(reference_conversations):
        predicted_turns: list[QAOATurn] = []
        for reference_turn in reference_conversations[conversation_id]:
            response = runtime.run(
                AgentMode.QAOA,
                reference_turn.query,
                session_id=conversation_id,
            )
            if response.qaoa_turns:
                predicted_turns.append(response.qaoa_turns[0])
            else:
                predicted_turns.append(QAOATurn(query=reference_turn.query, answer=response.answer))
        predicted_conversations[conversation_id] = predicted_turns

    output_path = Path(args.output).resolve()
    export_qaoa_conversations_jsonl(
        conversations=predicted_conversations,
        output_path=output_path,
    )
    print(
        f"wrote_predictions conversations={len(predicted_conversations)} output={output_path}"
    )
    return 0


def _run_eval(args: argparse.Namespace) -> int:
    reference = load_qaoa_jsonl(Path(args.reference).resolve())
    predicted = load_qaoa_jsonl(Path(args.predicted).resolve())
    metrics = evaluate_qaoa_predictions(reference=reference, predicted=predicted)
    print(json.dumps(asdict(metrics), indent=2, ensure_ascii=False))
    return 0


def _run_export_sft(args: argparse.Namespace) -> int:
    conversations = load_qaoa_jsonl(Path(args.input).resolve())
    turns = [turn for conv_id in sorted(conversations) for turn in conversations[conv_id]]
    output_path = Path(args.output).resolve()
    export_sft_jsonl(turns=turns, output_path=output_path)
    print(f"wrote_sft_examples={len(turns)} output={output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "synth":
        return _run_synth(args)
    if args.command == "benchmark":
        return _run_benchmark(args)
    if args.command == "eval":
        return _run_eval(args)
    if args.command == "export-sft":
        return _run_export_sft(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
