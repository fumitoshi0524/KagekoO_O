"""Developer-facing runtime API."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

from dotenv import find_dotenv, load_dotenv

from core.factory import AgentFactory
from core.models import AgentMode, AgentRequest, AgentResponse, ToolUse
from core.orchestrator import AgentOrchestrator
from core.services import Services
from integrations.builtins import BuiltinToolPack
from integrations.llm import create_llm_adapter
from integrations.memory import InMemorySessionStore
from integrations.tools import ToolRegistry

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
    orchestrator: AgentOrchestrator
    provider: str
    model: str | None

    def run(
        self,
        mode: AgentMode,
        message: str,
        session_id: str | None = None,
        tool_plan: list[ToolUse] | None = None,
    ) -> AgentResponse:
        request = AgentRequest(
            message=message,
            session_id=session_id,
            tool_plan=tool_plan or [],
        )
        return self.orchestrator.run(mode, request)


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
    elif (kageko_key and kageko_key.strip() != "") or (
        openai_key and openai_key.strip() != ""
    ):
        selected_provider = "openai"
    else:
        raise ValueError(
            "No LLM provider configured. Set KAGEKO_PROVIDER to openai/deepseek "
            "and provide OPENAI_API_KEY or DEEPSEEK_API_KEY (or KAGEKO_API_KEY)."
        )

    normalized_provider = selected_provider.strip().lower()
    if normalized_provider not in {"openai", "deepseek"}:
        raise ValueError(
            f"Unsupported provider '{selected_provider}'. Supported providers: openai, deepseek."
        )

    if api_key is not None and api_key.strip() != "":
        resolved_api_key = api_key
    elif normalized_provider == "deepseek":
        resolved_api_key = kageko_key or deepseek_key
    else:
        resolved_api_key = kageko_key or openai_key

    resolved_model = model or os.getenv("KAGEKO_MODEL")
    if not resolved_model:
        resolved_model = "deepseek-chat" if normalized_provider == "deepseek" else "gpt-4.1-mini"
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

    # Optional RAG setup
    retriever = None
    if enable_rag:
        from integrations.rag import VectorStore

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

    # Optional MCP setup
    if enable_mcp and mcp_server_url:
        from integrations.mcp import MCPClient, MCPToolAdapter

        mcp_client = MCPClient(server_url=mcp_server_url)
        mcp_client.connect()
        mcp_adapter = MCPToolAdapter(mcp_client=mcp_client)

        # Register MCP tools
        for tool_name in mcp_client.list_tools():
            tools.register(
                f"mcp.{tool_name}", lambda p, n=tool_name: mcp_adapter.call(n, p)
            )

    services = Services(
        llm=create_llm_adapter(
            provider=normalized_provider,
            api_key=resolved_api_key,
            model=resolved_model,
            base_url=resolved_base_url,
        ),
        tools=tools,
        memory=InMemorySessionStore(),
        retriever=retriever,
    )
    orchestrator = AgentOrchestrator(factory=AgentFactory(services=services))
    return KagekoRuntime(
        orchestrator=orchestrator,
        provider=normalized_provider,
        model=resolved_model,
    )
