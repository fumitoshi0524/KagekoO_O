"""CliState — runtime state container and caching for the Kageko CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runtime import KagekoRuntime


class CliState:
    def __init__(
        self,
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
        auto_approve: bool = False,
        verbose: bool = False,
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.workspace = workspace
        self.skills_dir = skills_dir
        self.enable_rag = enable_rag
        self.rag_persist_dir = rag_persist_dir
        self.enable_mcp = enable_mcp
        self.mcp_server_url = mcp_server_url
        self.auto_approve = auto_approve
        self.verbose = verbose
        self.runtime: KagekoRuntime | None = None
        self.runtime_key: tuple[object, ...] | None = None

    def get_runtime(
        self,
        provider: str | None,
        api_key: str | None,
        model: str | None,
        base_url: str | None,
        workspace: str | None,
        skills_dir: str | None,
        enable_rag: bool,
        rag_persist_dir: str | None,
        enable_mcp: bool,
        mcp_server_url: str | None,
    ) -> KagekoRuntime:
        from ..runtime import create_runtime

        cache_key = (
            provider, api_key, model, base_url, workspace, skills_dir,
            enable_rag, rag_persist_dir, enable_mcp, mcp_server_url,
        )
        if self.runtime is not None and self.runtime_key == cache_key:
            return self.runtime
        self.runtime = create_runtime(
            provider=provider, api_key=api_key, model=model, base_url=base_url,
            workspace=workspace, skills_dir=skills_dir, enable_rag=enable_rag,
            rag_persist_dir=rag_persist_dir, enable_mcp=enable_mcp,
            mcp_server_url=mcp_server_url,
        )
        self.runtime_key = cache_key
        return self.runtime
