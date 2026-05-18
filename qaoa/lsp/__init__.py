# QAOA category: analysis, domain: technology
"""
LSP (Language Server Protocol) Integration Module

This module provides LSP client functionality for communicating with
language servers using the Language Server Protocol.
"""

from .types import (
    Position,
    Range,
    Diagnostic,
    DiagnosticSeverity,
    Location,
    TextDocumentItem,
    TextDocumentIdentifier,
    VersionedTextDocumentIdentifier,
    DidOpenTextDocumentParams,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    PublishDiagnosticsParams,
    InitializeParams,
    InitializeResult,
    ClientCapabilities,
    WorkspaceClientCapabilities,
    TextDocumentClientCapabilities,
    WorkspaceFolder,
    ServerCapabilities,
    ServerInfo,
    Message,
    ResponseError,
)
from .client import LSPClient, ServerState
from .manager import LSPManager, LanguageServerConfig

__all__ = [
    # Types
    "Position",
    "Range",
    "Diagnostic",
    "DiagnosticSeverity",
    "Location",
    "TextDocumentItem",
    "TextDocumentIdentifier",
    "VersionedTextDocumentIdentifier",
    "DidOpenTextDocumentParams",
    "DidChangeTextDocumentParams",
    "DidCloseTextDocumentParams",
    "PublishDiagnosticsParams",
    "InitializeParams",
    "InitializeResult",
    "ClientCapabilities",
    "WorkspaceClientCapabilities",
    "TextDocumentClientCapabilities",
    "WorkspaceFolder",
    "ServerCapabilities",
    "ServerInfo",
    "Message",
    "ResponseError",
    # Client
    "LSPClient",
    "ServerState",
    # Manager
    "LSPManager",
    "LanguageServerConfig",
]
