"""Developer-facing runtime API."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

from dotenv import find_dotenv, load_dotenv

from .adapters.builtins import BuiltinToolPack
from .adapters.llm import create_llm_adapter
from .adapters.loader import GeneratedToolPack
from .adapters.memory import InMemorySessionStore
from .adapters.tools import ToolRegistry
from .context import ContextManager
from .engine import QAOAEngine
from .pipeline.core import PipelineCore, PipelineResult, QAOADataResult, QualityEvalResult
from .types import AgentMode, AgentRequest, AgentResponse, QAOASkill, ToolUse

_POWERSHELL_ENV_PATTERN = re.compile(
    r"\$env:([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\r\n$#]+))"
)


def _load_powershell_style_env(dotenv_path: str) -> None:
    try:
        content = Path(dotenv_path).read_text(encoding="utf-8")
    except OSError:
        return

    for match in _POWERSHELL_ENV_PATTERN.finditer(content):
        key = match.group(1)
        value = match.group(2) or match.group(3) or match.group(4) or ""
        value = value.strip()
        if value == "":
            continue
        os.environ.setdefault(key, value)


def _load_environment() -> None:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path, override=False)
        _load_powershell_style_env(dotenv_path)
    else:
        load_dotenv(override=False)


@dataclass(slots=True, kw_only=True)
class KagekoRuntime:
    engine: QAOAEngine
    tools: ToolRegistry
    memory: InMemorySessionStore
    provider: str
    model: str | None
    _api_key: str
    skills: dict[str, QAOASkill]
    active_skills: dict[str, str]

    def run(
        self,
        mode: AgentMode,
        message: str,
        session_id: str | None = None,
        tool_plan: list[ToolUse] | None = None,
        skill_name: str | None = None,
        generate_skill: bool = False,
    ) -> AgentResponse:
        if mode != AgentMode.QAOA:
            raise ValueError("Only qaoa mode is supported in this version.")
        request = AgentRequest(message=message, session_id=session_id, tool_plan=tool_plan or [])
        history = self.memory.read(session_id) if session_id is not None else []
        selected_skill = self._resolve_skill(session_id=session_id, skill_name=skill_name)
        turn, trace = self.engine.run(
            query=request.query,
            tool_plan=request.tool_plan,
            skill=selected_skill,
            allow_skill_generation=generate_skill,
        )
        if session_id is not None:
            self.memory.append(session_id, request.query)
            self.memory.append(session_id, turn.answer)
        return AgentResponse(
            answer=turn.answer,
            trace=history + trace,
            qaoa_turns=[turn],
            tools=_to_tools(turn),
        )

    def generate_skill(self, *, name: str, objective: str) -> QAOASkill:
        key = name.strip()
        if key == "":
            raise ValueError("Skill name cannot be empty.")
        skill = self.engine.generate_skill(objective=objective)
        materialized = QAOASkill(
            name=key,
            objective=skill.objective,
            tools=skill.tools,
            steps=skill.steps,
        )
        self.skills[key] = materialized
        return materialized

    def list_skills(self) -> list[QAOASkill]:
        return [self.skills[name] for name in sorted(self.skills)]

    def activate_skill(self, *, session_id: str, name: str) -> None:
        if name not in self.skills:
            raise ValueError(f"Skill '{name}' is not found.")
        self.active_skills[session_id] = name

    def clear_active_skill(self, *, session_id: str) -> None:
        if session_id in self.active_skills:
            del self.active_skills[session_id]

    def get_active_skill(self, *, session_id: str) -> QAOASkill | None:
        skill_name = self.active_skills.get(session_id)
        if skill_name is None:
            return None
        return self.skills.get(skill_name)

    def list_sessions(self) -> list[str]:
        return self.memory.list_sessions()

    def clear_session(self, *, session_id: str) -> None:
        self.memory.clear(session_id)
        if session_id in self.active_skills:
            del self.active_skills[session_id]

    def generate_tool_via_pipeline(
        self,
        *,
        spec: str,
        name: str,
        category: str,
        domain: str,
        output_dir: str,
    ) -> PipelineResult:
        pipeline = PipelineCore(
            provider=self.provider,
            api_key=self._api_key,
            model=self.model,
        )
        return pipeline.generate_tool(
            spec=spec, name=name, category=category, domain=domain, output_dir=output_dir
        )

    def generate_skill_via_pipeline(
        self,
        *,
        name: str,
        goal: str,
        output_dir: str,
    ) -> PipelineResult:
        pipeline = PipelineCore(
            provider=self.provider,
            api_key=self._api_key,
            model=self.model,
        )
        return pipeline.generate_skill(name=name, goal=goal, output_dir=output_dir)

    def generate_tools_batch_via_pipeline(
        self,
        *,
        specs: list[dict[str, str]],
        output_dir: str,
    ) -> list[PipelineResult]:
        pipeline = PipelineCore(
            provider=self.provider,
            api_key=self._api_key,
            model=self.model,
        )
        return pipeline.generate_tool_batch(specs=specs, output_dir=output_dir)

    def generate_qaoa_single_hop_via_pipeline(
        self,
        *,
        tool_specs: list[dict[str, object]],
        count: int = 10,
    ) -> QAOADataResult:
        pipeline = PipelineCore(
            provider=self.provider,
            api_key=self._api_key,
            model=self.model,
        )
        return pipeline.generate_qaoa_single_hop(tool_specs=tool_specs, count=count)

    def generate_qaoa_multi_hop_via_pipeline(
        self,
        *,
        tool_specs: list[dict[str, object]],
        count: int = 10,
        min_steps: int = 2,
        max_steps: int = 5,
    ) -> QAOADataResult:
        pipeline = PipelineCore(
            provider=self.provider,
            api_key=self._api_key,
            model=self.model,
        )
        return pipeline.generate_qaoa_multi_hop(
            tool_specs=tool_specs, count=count, min_steps=min_steps, max_steps=max_steps,
        )

    def generate_qaoa_multi_turn_via_pipeline(
        self,
        *,
        tool_specs: list[dict[str, object]],
        count: int = 5,
        min_turns: int = 2,
        max_turns: int = 4,
    ) -> QAOADataResult:
        pipeline = PipelineCore(
            provider=self.provider,
            api_key=self._api_key,
            model=self.model,
        )
        return pipeline.generate_qaoa_multi_turn(
            tool_specs=tool_specs, count=count, min_turns=min_turns, max_turns=max_turns,
        )

    def evaluate_query_quality_via_pipeline(
        self, *, query: str, tool_spec: dict[str, object],
    ) -> QualityEvalResult:
        pipeline = PipelineCore(
            provider=self.provider,
            api_key=self._api_key,
            model=self.model,
        )
        return pipeline.evaluate_query_quality(query=query, tool_spec=tool_spec)

    def evaluate_trajectory_quality_via_pipeline(
        self, *, query: str, tool_name: str, args: dict[str, object],
        observation: str, answer: str, tool_spec: dict[str, object],
    ) -> QualityEvalResult:
        pipeline = PipelineCore(
            provider=self.provider,
            api_key=self._api_key,
            model=self.model,
        )
        return pipeline.evaluate_trajectory_quality(
            query=query, tool_name=tool_name, args=args,
            observation=observation, answer=answer, tool_spec=tool_spec,
        )

    def _resolve_skill(
        self, *, session_id: str | None, skill_name: str | None
    ) -> QAOASkill | None:
        if skill_name is not None and skill_name.strip() != "":
            resolved = self.skills.get(skill_name)
            if resolved is None:
                raise ValueError(f"Skill '{skill_name}' is not found.")
            return resolved
        if session_id is None:
            return None
        active_name = self.active_skills.get(session_id)
        if active_name is None:
            return None
        return self.skills.get(active_name)


def create_runtime(
    *,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    workspace: str | None = None,
    skills_dir: str | None = None,
    enable_rag: bool = False,
    rag_persist_dir: str | None = None,
    enable_mcp: bool = False,
    mcp_server_url: str | None = None,
) -> KagekoRuntime:
    _load_environment()

    env_provider = os.getenv("KAGEKO_PROVIDER")
    openai_key = os.getenv("OPENAI_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    claude_key = os.getenv("CLAUDE_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    kageko_key = os.getenv("KAGEKO_API_KEY")

    if provider is not None:
        selected_provider = provider
    elif env_provider is not None:
        selected_provider = env_provider
    elif api_key is not None and api_key.strip() != "":
        selected_provider = "openai"
    elif (
        deepseek_key is not None
        and deepseek_key.strip() != ""
        and not (openai_key and openai_key.strip() != "")
    ):
        selected_provider = "deepseek"
    elif (claude_key and claude_key.strip() != "") or (
        anthropic_key and anthropic_key.strip() != ""
    ):
        selected_provider = "claude"
    elif (gemini_key and gemini_key.strip() != "") or (
        google_api_key and google_api_key.strip() != ""
    ):
        selected_provider = "gemini"
    elif (kageko_key and kageko_key.strip() != "") or (
        openai_key and openai_key.strip() != ""
    ):
        selected_provider = "openai"
    else:
        raise ValueError(
            "No LLM provider configured. Set KAGEKO_PROVIDER to openai/deepseek/claude/gemini "
            "and provide corresponding API key."
        )

    normalized_provider = selected_provider.strip().lower()
    supported_providers = {"openai", "deepseek", "claude", "gemini"}
    if normalized_provider not in supported_providers:
        raise ValueError(
            f"Unsupported provider '{selected_provider}'. Supported providers: {', '.join(sorted(supported_providers))}."
        )

    if api_key is not None and api_key.strip() != "":
        resolved_api_key = api_key
    elif normalized_provider == "deepseek":
        resolved_api_key = kageko_key or deepseek_key
    elif normalized_provider == "claude":
        resolved_api_key = kageko_key or claude_key or anthropic_key
    elif normalized_provider == "gemini":
        resolved_api_key = kageko_key or gemini_key or google_api_key
    else:
        resolved_api_key = kageko_key or openai_key

    resolved_model = model or os.getenv("KAGEKO_MODEL")
    if not resolved_model:
        default_models = {
            "openai": "gpt-4.1-mini",
            "deepseek": "deepseek-chat",
            "claude": "claude-3-7-sonnet-latest",
            "gemini": "gemini-2.5-flash",
        }
        resolved_model = default_models[normalized_provider]
    resolved_base_url = base_url or os.getenv("KAGEKO_BASE_URL")

    runtime_workspace = Path(
        workspace or os.getenv("KAGEKO_WORKSPACE") or os.getcwd()
    ).resolve()
    configured_skills = skills_dir or os.getenv("KAGEKO_SKILLS_DIR")
    runtime_skills_dir = (
        Path(configured_skills).resolve() if configured_skills else None
    )

    tools = ToolRegistry()
    BuiltinToolPack(
        workspace=runtime_workspace, skills_dir=runtime_skills_dir
    ).register(tools)

    # Auto-load generated tools from workspace/tools directory
    generated_tools_dir = runtime_workspace / "tools"
    GeneratedToolPack(tools_dir=generated_tools_dir).register(tools)

    # Optional RAG setup
    retriever = None
    if enable_rag:
        from .adapters.rag import VectorStore

        vector_store = VectorStore(
            collection_name="kageko_docs",
            persist_directory=rag_persist_dir,
        )

        class VectorRetriever:
            def retrieve(self, query: str, top_k: int = 5) -> list[str]:
                return vector_store.query(query, n_results=top_k)

            def add_documents(self, documents: list[str]) -> None:
                vector_store.add_documents(documents)

        retriever = VectorRetriever()
        tools.register(
            "retriever.search",
            lambda payload: "\n\n".join(retriever.retrieve(payload, top_k=3)) or "<no-documents>",
            description="Retrieve relevant documents from vector store.",
            input_contract="search query text",
            output_contract="top matching documents joined as text",
            tags=("retrieval", "rag"),
            category="search",
            domain="technology",
        )
        tools.register(
            "retriever.add",
            lambda payload: _retriever_add_documents(retriever, payload),
            description="Add documents to vector store. One document per non-empty line.",
            input_contract="newline-separated documents",
            output_contract="'retriever-added:<count>' confirmation",
            tags=("retrieval", "rag", "write"),
            category="operations",
            domain="technology",
        )

    # Optional MCP setup
    if enable_mcp and mcp_server_url:
        from .adapters.mcp import MCPClient, MCPToolAdapter

        mcp_client = MCPClient(server_url=mcp_server_url)
        mcp_client.connect()
        mcp_adapter = MCPToolAdapter(mcp_client=mcp_client)

        # Register MCP tools
        for tool_name in mcp_client.list_tools():
            tools.register(
                f"mcp.{tool_name}", lambda p, n=tool_name: mcp_adapter.call(n, p)
            )

    # Runtime toolset is immutable; tool evolution is code/training time only.
    tools.freeze()

    llm = create_llm_adapter(
        provider=normalized_provider,
        api_key=resolved_api_key,
        model=resolved_model,
        base_url=resolved_base_url,
    )
    persist_dir = Path.home() / ".kageko" / "sessions"
    memory = InMemorySessionStore(persist_dir=persist_dir)
    context = ContextManager(workspace=runtime_workspace).load()
    engine = QAOAEngine(llm=llm, tools=tools, retriever=retriever, context=context)
    return KagekoRuntime(
        engine=engine,
        tools=tools,
        memory=memory,
        provider=normalized_provider,
        model=resolved_model,
        _api_key=resolved_api_key or "",
        skills={},
        active_skills={},
    )


def _retriever_add_documents(retriever, payload: str) -> str:
    documents = [line.strip() for line in payload.splitlines() if line.strip() != ""]
    if not documents:
        raise ValueError("retriever.add requires at least one non-empty line.")
    retriever.add_documents(documents)
    return f"retriever-added:{len(documents)}"


def _to_tools(turn) -> list[ToolUse]:
    if not turn.actions:
        return []
    observations_by_action: dict[str, list[str]] = {}
    for observation in turn.observations:
        bucket = observations_by_action.setdefault(observation.action_name, [])
        bucket.append(observation.output)
    tools: list[ToolUse] = []
    for action in turn.actions:
        outputs = observations_by_action.get(action.name, [])
        output = outputs.pop(0) if outputs else None
        tools.append(ToolUse(name=action.name, input=action.input, output=output))
    return tools
