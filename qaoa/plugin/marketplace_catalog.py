"""Parse Claude Code marketplace.json catalogs."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


class MarketplaceOwner(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    email: str | None = None


class MarketplaceMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: str | None = None
    version: str | None = None
    pluginRoot: str | None = None


class MarketplaceFile(BaseModel):
    """Contents of .claude-plugin/marketplace.json."""

    model_config = ConfigDict(extra="allow")

    name: str
    owner: MarketplaceOwner | dict[str, Any]
    plugins: list[dict[str, Any]] = Field(default_factory=list)
    metadata: MarketplaceMetadata | dict[str, Any] | None = None

    @field_validator("owner", mode="before")
    @classmethod
    def _owner(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return v
        return {"name": str(v)}


def marketplace_json_path(marketplace_root: Path) -> Path:
    return marketplace_root / ".claude-plugin" / "marketplace.json"


def load_marketplace_file(path: Path) -> MarketplaceFile | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if not isinstance(raw, dict):
            return None
        return MarketplaceFile.model_validate(raw)
    except Exception as e:
        logger.warning("Invalid marketplace.json %s: %s", path, e)
        return None


def load_marketplace_from_root(marketplace_root: Path) -> MarketplaceFile | None:
    return load_marketplace_file(marketplace_json_path(marketplace_root))


def plugin_root_prefix(meta: MarketplaceFile) -> str:
    m = meta.metadata
    if isinstance(m, MarketplaceMetadata) and m.pluginRoot:
        return m.pluginRoot.strip().rstrip("/")
    if isinstance(m, dict):
        pr = m.get("pluginRoot")
        if isinstance(pr, str) and pr.strip():
            return pr.strip().rstrip("/")
    return ""


def find_plugin_entry(catalog: MarketplaceFile, plugin_name: str) -> dict[str, Any] | None:
    for p in catalog.plugins:
        if isinstance(p, dict) and p.get("name") == plugin_name:
            return p
    return None
