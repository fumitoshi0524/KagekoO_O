# QAOA category: analysis, domain: technology
"""
LSP Types - Language Server Protocol type definitions.

This module contains Python dataclasses that correspond to LSP protocol types.
Based on LSP Specification 3.17
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import json


# Type aliases
DocumentUri = str
URI = str


class DiagnosticSeverity(int, Enum):
    """Diagnostic severity levels."""
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


class DiagnosticTag(int, Enum):
    """Diagnostic tags for additional metadata."""
    UNNECESSARY = 1
    DEPRECATED = 2


class SymbolKind(int, Enum):
    """Symbol kind enumeration."""
    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    CONSTRUCTOR = 9
    ENUM = 10
    INTERFACE = 11
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    STRING = 15
    NUMBER = 16
    BOOLEAN = 17
    ARRAY = 18
    OBJECT = 19
    KEY = 20
    NULL = 21
    ENUM_MEMBER = 22
    STRUCT = 23
    EVENT = 24
    OPERATOR = 25
    TYPE_PARAMETER = 26


class LanguageKind(str, Enum):
    """Language identifiers for text documents."""
    ABAP = "abap"
    WINDOWS_BAT = "bat"
    BIBTEX = "bibtex"
    CLOJURE = "clojure"
    COFFEESCRIPT = "coffeescript"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    CSS = "css"
    D = "d"
    DELPHI = "delphi"
    DIFF = "diff"
    DART = "dart"
    DOCKERFILE = "dockerfile"
    ELIXIR = "elixir"
    ERLANG = "erlang"
    FSHARP = "fsharp"
    GO = "go"
    GROOVY = "groovy"
    HANDLEBARS = "handlebars"
    HASKELL = "haskell"
    HTML = "html"
    INI = "ini"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    JAVASCRIPT_REACT = "javascriptreact"
    JSON = "json"
    LATEX = "latex"
    LESS = "less"
    LUA = "lua"
    MAKEFILE = "makefile"
    MARKDOWN = "markdown"
    OBJECTIVE_C = "objective-c"
    OBJECTIVE_CPP = "objective-cpp"
    PERL = "perl"
    PERL6 = "perl6"
    PHP = "php"
    POWERSHELL = "powershell"
    PUG = "jade"
    PYTHON = "python"
    R = "r"
    RAZOR = "razor"
    RUBY = "ruby"
    RUST = "rust"
    SCSS = "scss"
    SASS = "sass"
    SCALA = "scala"
    SHADERLAB = "shaderlab"
    SHELL = "shellscript"
    SQL = "sql"
    SWIFT = "swift"
    TYPESCRIPT = "typescript"
    TYPESCRIPT_REACT = "typescriptreact"
    XML = "xml"
    XSL = "xsl"
    YAML = "yaml"


@dataclass
class Position:
    """Position in a text document (zero-based)."""
    line: int
    character: int

    def to_dict(self) -> Dict[str, int]:
        return {"line": self.line, "character": self.character}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "Position":
        return cls(line=data["line"], character=data["character"])


@dataclass
class Range:
    """A range in a text document expressed as start and end positions."""
    start: Position
    end: Position

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Range":
        return cls(
            start=Position.from_dict(data["start"]),
            end=Position.from_dict(data["end"])
        )


@dataclass
class Location:
    """Represents a location inside a resource."""
    uri: DocumentUri
    range: Range

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "range": self.range.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Location":
        return cls(
            uri=data["uri"],
            range=Range.from_dict(data["range"])
        )


@dataclass
class DiagnosticRelatedInformation:
    """Related diagnostic information."""
    location: Location
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": self.location.to_dict(),
            "message": self.message
        }


@dataclass
class CodeDescription:
    """Structure to capture a description for an error code."""
    href: str

    def to_dict(self) -> Dict[str, str]:
        return {"href": self.href}


@dataclass
class Diagnostic:
    """Represents a diagnostic, such as a compiler error or warning."""
    range: Range
    message: str
    severity: Optional[DiagnosticSeverity] = None
    code: Optional[Union[int, str]] = None
    code_description: Optional[CodeDescription] = None
    source: Optional[str] = None
    tags: Optional[List[DiagnosticTag]] = None
    related_information: Optional[List[DiagnosticRelatedInformation]] = None
    data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "range": self.range.to_dict(),
            "message": self.message
        }
        if self.severity is not None:
            result["severity"] = self.severity.value
        if self.code is not None:
            result["code"] = self.code
        if self.code_description is not None:
            result["codeDescription"] = self.code_description.to_dict()
        if self.source is not None:
            result["source"] = self.source
        if self.tags is not None:
            result["tags"] = [t.value for t in self.tags]
        if self.related_information is not None:
            result["relatedInformation"] = [r.to_dict() for r in self.related_information]
        if self.data is not None:
            result["data"] = self.data
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Diagnostic":
        severity = None
        if "severity" in data:
            severity = DiagnosticSeverity(data["severity"])

        tags = None
        if "tags" in data:
            tags = [DiagnosticTag(t) for t in data["tags"]]

        code_description = None
        if "codeDescription" in data:
            code_description = CodeDescription(href=data["codeDescription"]["href"])

        related_information = None
        if "relatedInformation" in data:
            related_information = [
                DiagnosticRelatedInformation(
                    location=Location.from_dict(r["location"]),
                    message=r["message"]
                )
                for r in data["relatedInformation"]
            ]

        return cls(
            range=Range.from_dict(data["range"]),
            message=data["message"],
            severity=severity,
            code=data.get("code"),
            code_description=code_description,
            source=data.get("source"),
            tags=tags,
            related_information=related_information,
            data=data.get("data")
        )


@dataclass
class TextDocumentIdentifier:
    """Text documents are identified using a URI."""
    uri: DocumentUri

    def to_dict(self) -> Dict[str, str]:
        return {"uri": self.uri}


@dataclass
class VersionedTextDocumentIdentifier(TextDocumentIdentifier):
    """Text document identifier with version number."""
    version: int

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["version"] = self.version
        return result


@dataclass
class TextDocumentItem:
    """An item to transfer a text document from the client to the server."""
    uri: DocumentUri
    language_id: str
    version: int
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "languageId": self.language_id,
            "version": self.version,
            "text": self.text
        }


@dataclass
class DidOpenTextDocumentParams:
    """Parameters for textDocument/didOpen notification."""
    text_document: TextDocumentItem

    def to_dict(self) -> Dict[str, Any]:
        return {"textDocument": self.text_document.to_dict()}


@dataclass
class TextDocumentContentChangeEvent:
    """Event describing a change to a text document."""
    text: str
    range: Optional[Range] = None
    range_length: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"text": self.text}
        if self.range is not None:
            result["range"] = self.range.to_dict()
        if self.range_length is not None:
            result["rangeLength"] = self.range_length
        return result


@dataclass
class DidChangeTextDocumentParams:
    """Parameters for textDocument/didChange notification."""
    text_document: VersionedTextDocumentIdentifier
    content_changes: List[TextDocumentContentChangeEvent]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "textDocument": self.text_document.to_dict(),
            "contentChanges": [c.to_dict() for c in self.content_changes]
        }


@dataclass
class DidCloseTextDocumentParams:
    """Parameters for textDocument/didClose notification."""
    text_document: TextDocumentIdentifier

    def to_dict(self) -> Dict[str, Any]:
        return {"textDocument": self.text_document.to_dict()}


@dataclass
class PublishDiagnosticsParams:
    """Parameters for textDocument/publishDiagnostics notification."""
    uri: DocumentUri
    diagnostics: List[Diagnostic]
    version: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PublishDiagnosticsParams":
        diagnostics = [Diagnostic.from_dict(d) for d in data["diagnostics"]]
        return cls(
            uri=data["uri"],
            diagnostics=diagnostics,
            version=data.get("version")
        )


@dataclass
class WorkspaceFolder:
    """A workspace folder."""
    uri: URI
    name: str

    def to_dict(self) -> Dict[str, str]:
        return {"uri": self.uri, "name": self.name}


@dataclass
class ClientInfo:
    """Information about the client."""
    name: str
    version: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        result = {"name": self.name}
        if self.version:
            result["version"] = self.version
        return result


@dataclass
class TextDocumentSyncClientCapabilities:
    """Text document synchronization client capabilities."""
    dynamic_registration: Optional[bool] = None
    will_save: Optional[bool] = None
    will_save_wait_until: Optional[bool] = None
    did_save: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.dynamic_registration is not None:
            result["dynamicRegistration"] = self.dynamic_registration
        if self.will_save is not None:
            result["willSave"] = self.will_save
        if self.will_save_wait_until is not None:
            result["willSaveWaitUntil"] = self.will_save_wait_until
        if self.did_save is not None:
            result["didSave"] = self.did_save
        return result


@dataclass
class PublishDiagnosticsClientCapabilities:
    """Publish diagnostics client capabilities."""
    related_information: Optional[bool] = None
    tag_support: Optional[Dict[str, Any]] = None
    version_support: Optional[bool] = None
    code_description_support: Optional[bool] = None
    data_support: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.related_information is not None:
            result["relatedInformation"] = self.related_information
        if self.tag_support is not None:
            result["tagSupport"] = self.tag_support
        if self.version_support is not None:
            result["versionSupport"] = self.version_support
        if self.code_description_support is not None:
            result["codeDescriptionSupport"] = self.code_description_support
        if self.data_support is not None:
            result["dataSupport"] = self.data_support
        return result


@dataclass
class CompletionClientCapabilities:
    """Completion client capabilities."""
    dynamic_registration: Optional[bool] = None
    completion_item: Optional[Dict[str, Any]] = None
    completion_item_kind: Optional[Dict[str, Any]] = None
    context_support: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.dynamic_registration is not None:
            result["dynamicRegistration"] = self.dynamic_registration
        if self.completion_item is not None:
            result["completionItem"] = self.completion_item
        if self.completion_item_kind is not None:
            result["completionItemKind"] = self.completion_item_kind
        if self.context_support is not None:
            result["contextSupport"] = self.context_support
        return result


@dataclass
class TextDocumentClientCapabilities:
    """Text document specific client capabilities."""
    synchronization: Optional[TextDocumentSyncClientCapabilities] = None
    completion: Optional[CompletionClientCapabilities] = None
    hover: Optional[Dict[str, Any]] = None
    signature_help: Optional[Dict[str, Any]] = None
    declaration: Optional[Dict[str, Any]] = None
    definition: Optional[Dict[str, Any]] = None
    type_definition: Optional[Dict[str, Any]] = None
    implementation: Optional[Dict[str, Any]] = None
    references: Optional[Dict[str, Any]] = None
    document_highlight: Optional[Dict[str, Any]] = None
    document_symbol: Optional[Dict[str, Any]] = None
    code_action: Optional[Dict[str, Any]] = None
    code_lens: Optional[Dict[str, Any]] = None
    document_link: Optional[Dict[str, Any]] = None
    color_provider: Optional[Dict[str, Any]] = None
    formatting: Optional[Dict[str, Any]] = None
    range_formatting: Optional[Dict[str, Any]] = None
    on_type_formatting: Optional[Dict[str, Any]] = None
    rename: Optional[Dict[str, Any]] = None
    publish_diagnostics: Optional[PublishDiagnosticsClientCapabilities] = None
    folding_range: Optional[Dict[str, Any]] = None
    selection_range: Optional[Dict[str, Any]] = None
    linked_editing_range: Optional[Dict[str, Any]] = None
    call_hierarchy: Optional[Dict[str, Any]] = None
    semantic_tokens: Optional[Dict[str, Any]] = None
    moniker: Optional[Dict[str, Any]] = None
    type_hierarchy: Optional[Dict[str, Any]] = None
    inline_value: Optional[Dict[str, Any]] = None
    inlay_hint: Optional[Dict[str, Any]] = None
    diagnostic: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.synchronization is not None:
            result["synchronization"] = self.synchronization.to_dict()
        if self.completion is not None:
            result["completion"] = self.completion.to_dict()
        if self.hover is not None:
            result["hover"] = self.hover
        if self.signature_help is not None:
            result["signatureHelp"] = self.signature_help
        if self.declaration is not None:
            result["declaration"] = self.declaration
        if self.definition is not None:
            result["definition"] = self.definition
        if self.type_definition is not None:
            result["typeDefinition"] = self.type_definition
        if self.implementation is not None:
            result["implementation"] = self.implementation
        if self.references is not None:
            result["references"] = self.references
        if self.document_highlight is not None:
            result["documentHighlight"] = self.document_highlight
        if self.document_symbol is not None:
            result["documentSymbol"] = self.document_symbol
        if self.code_action is not None:
            result["codeAction"] = self.code_action
        if self.code_lens is not None:
            result["codeLens"] = self.code_lens
        if self.document_link is not None:
            result["documentLink"] = self.document_link
        if self.color_provider is not None:
            result["colorProvider"] = self.color_provider
        if self.formatting is not None:
            result["formatting"] = self.formatting
        if self.range_formatting is not None:
            result["rangeFormatting"] = self.range_formatting
        if self.on_type_formatting is not None:
            result["onTypeFormatting"] = self.on_type_formatting
        if self.rename is not None:
            result["rename"] = self.rename
        if self.publish_diagnostics is not None:
            result["publishDiagnostics"] = self.publish_diagnostics.to_dict()
        if self.folding_range is not None:
            result["foldingRange"] = self.folding_range
        if self.selection_range is not None:
            result["selectionRange"] = self.selection_range
        if self.linked_editing_range is not None:
            result["linkedEditingRange"] = self.linked_editing_range
        if self.call_hierarchy is not None:
            result["callHierarchy"] = self.call_hierarchy
        if self.semantic_tokens is not None:
            result["semanticTokens"] = self.semantic_tokens
        if self.moniker is not None:
            result["moniker"] = self.moniker
        if self.type_hierarchy is not None:
            result["typeHierarchy"] = self.type_hierarchy
        if self.inline_value is not None:
            result["inlineValue"] = self.inline_value
        if self.inlay_hint is not None:
            result["inlayHint"] = self.inlay_hint
        if self.diagnostic is not None:
            result["diagnostic"] = self.diagnostic
        return result


@dataclass
class DidChangeConfigurationClientCapabilities:
    """Did change configuration client capabilities."""
    dynamic_registration: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.dynamic_registration is not None:
            result["dynamicRegistration"] = self.dynamic_registration
        return result


@dataclass
class DidChangeWatchedFilesClientCapabilities:
    """Did change watched files client capabilities."""
    dynamic_registration: Optional[bool] = None
    relative_pattern_support: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.dynamic_registration is not None:
            result["dynamicRegistration"] = self.dynamic_registration
        if self.relative_pattern_support is not None:
            result["relativePatternSupport"] = self.relative_pattern_support
        return result


@dataclass
class WorkspaceSymbolClientCapabilities:
    """Workspace symbol client capabilities."""
    dynamic_registration: Optional[bool] = None
    symbol_kind: Optional[Dict[str, Any]] = None
    tag_support: Optional[Dict[str, Any]] = None
    resolve_support: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.dynamic_registration is not None:
            result["dynamicRegistration"] = self.dynamic_registration
        if self.symbol_kind is not None:
            result["symbolKind"] = self.symbol_kind
        if self.tag_support is not None:
            result["tagSupport"] = self.tag_support
        if self.resolve_support is not None:
            result["resolveSupport"] = self.resolve_support
        return result


@dataclass
class WorkspaceClientCapabilities:
    """Workspace specific client capabilities."""
    apply_edit: Optional[bool] = None
    workspace_edit: Optional[Dict[str, Any]] = None
    did_change_configuration: Optional[DidChangeConfigurationClientCapabilities] = None
    did_change_watched_files: Optional[DidChangeWatchedFilesClientCapabilities] = None
    symbol: Optional[WorkspaceSymbolClientCapabilities] = None
    execute_command: Optional[Dict[str, Any]] = None
    workspace_folders: Optional[bool] = None
    configuration: Optional[bool] = None
    semantic_tokens: Optional[Dict[str, Any]] = None
    code_lens: Optional[Dict[str, Any]] = None
    file_operations: Optional[Dict[str, Any]] = None
    inline_value: Optional[Dict[str, Any]] = None
    inlay_hint: Optional[Dict[str, Any]] = None
    diagnostics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.apply_edit is not None:
            result["applyEdit"] = self.apply_edit
        if self.workspace_edit is not None:
            result["workspaceEdit"] = self.workspace_edit
        if self.did_change_configuration is not None:
            result["didChangeConfiguration"] = self.did_change_configuration.to_dict()
        if self.did_change_watched_files is not None:
            result["didChangeWatchedFiles"] = self.did_change_watched_files.to_dict()
        if self.symbol is not None:
            result["symbol"] = self.symbol.to_dict()
        if self.execute_command is not None:
            result["executeCommand"] = self.execute_command
        if self.workspace_folders is not None:
            result["workspaceFolders"] = self.workspace_folders
        if self.configuration is not None:
            result["configuration"] = self.configuration
        if self.semantic_tokens is not None:
            result["semanticTokens"] = self.semantic_tokens
        if self.code_lens is not None:
            result["codeLens"] = self.code_lens
        if self.file_operations is not None:
            result["fileOperations"] = self.file_operations
        if self.inline_value is not None:
            result["inlineValue"] = self.inline_value
        if self.inlay_hint is not None:
            result["inlayHint"] = self.inlay_hint
        if self.diagnostics is not None:
            result["diagnostics"] = self.diagnostics
        return result


@dataclass
class WindowClientCapabilities:
    """Window specific client capabilities."""
    work_done_progress: Optional[bool] = None
    show_message: Optional[Dict[str, Any]] = None
    show_document: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.work_done_progress is not None:
            result["workDoneProgress"] = self.work_done_progress
        if self.show_message is not None:
            result["showMessage"] = self.show_message
        if self.show_document is not None:
            result["showDocument"] = self.show_document
        return result


@dataclass
class ClientCapabilities:
    """Defines the capabilities provided by the client."""
    workspace: Optional[WorkspaceClientCapabilities] = None
    text_document: Optional[TextDocumentClientCapabilities] = None
    notebook_document: Optional[Dict[str, Any]] = None
    window: Optional[WindowClientCapabilities] = None
    general: Optional[Dict[str, Any]] = None
    experimental: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.workspace is not None:
            result["workspace"] = self.workspace.to_dict()
        if self.text_document is not None:
            result["textDocument"] = self.text_document.to_dict()
        if self.notebook_document is not None:
            result["notebookDocument"] = self.notebook_document
        if self.window is not None:
            result["window"] = self.window.to_dict()
        if self.general is not None:
            result["general"] = self.general
        if self.experimental is not None:
            result["experimental"] = self.experimental
        return result


@dataclass
class InitializeParams:
    """Parameters for the initialize request."""
    process_id: Optional[int] = None
    client_info: Optional[ClientInfo] = None
    locale: Optional[str] = None
    root_path: Optional[str] = None
    root_uri: Optional[DocumentUri] = None
    initialization_options: Optional[Any] = None
    capabilities: Optional[ClientCapabilities] = None
    trace: Optional[str] = None
    workspace_folders: Optional[List[WorkspaceFolder]] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.process_id is not None:
            result["processId"] = self.process_id
        if self.client_info is not None:
            result["clientInfo"] = self.client_info.to_dict()
        if self.locale is not None:
            result["locale"] = self.locale
        if self.root_path is not None:
            result["rootPath"] = self.root_path
        if self.root_uri is not None:
            result["rootUri"] = self.root_uri
        if self.initialization_options is not None:
            result["initializationOptions"] = self.initialization_options
        if self.capabilities is not None:
            result["capabilities"] = self.capabilities.to_dict()
        if self.trace is not None:
            result["trace"] = self.trace
        if self.workspace_folders is not None:
            result["workspaceFolders"] = [wf.to_dict() for wf in self.workspace_folders]
        return result


@dataclass
class ServerInfo:
    """Information about the server."""
    name: str
    version: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServerInfo":
        return cls(
            name=data["name"],
            version=data.get("version")
        )


@dataclass
class ServerCapabilities:
    """Capabilities the language server provides."""
    text_document_sync: Optional[Any] = None
    completion_provider: Optional[Dict[str, Any]] = None
    hover_provider: Optional[bool] = None
    signature_help_provider: Optional[Dict[str, Any]] = None
    definition_provider: Optional[bool] = None
    type_definition_provider: Optional[Any] = None
    implementation_provider: Optional[Any] = None
    references_provider: Optional[bool] = None
    document_highlight_provider: Optional[bool] = None
    document_symbol_provider: Optional[bool] = None
    code_action_provider: Optional[Any] = None
    code_lens_provider: Optional[Dict[str, Any]] = None
    document_link_provider: Optional[Dict[str, Any]] = None
    color_provider: Optional[Any] = None
    document_formatting_provider: Optional[bool] = None
    document_range_formatting_provider: Optional[bool] = None
    document_on_type_formatting_provider: Optional[Dict[str, Any]] = None
    rename_provider: Optional[Any] = None
    folding_range_provider: Optional[Any] = None
    execute_command_provider: Optional[Dict[str, Any]] = None
    selection_range_provider: Optional[Any] = None
    linked_editing_range_provider: Optional[Any] = None
    call_hierarchy_provider: Optional[Any] = None
    semantic_tokens_provider: Optional[Dict[str, Any]] = None
    moniker_provider: Optional[Any] = None
    type_hierarchy_provider: Optional[Any] = None
    inline_value_provider: Optional[Any] = None
    inlay_hint_provider: Optional[Any] = None
    diagnostic_provider: Optional[Any] = None
    workspace: Optional[Dict[str, Any]] = None
    experimental: Optional[Any] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServerCapabilities":
        return cls(
            text_document_sync=data.get("textDocumentSync"),
            completion_provider=data.get("completionProvider"),
            hover_provider=data.get("hoverProvider"),
            signature_help_provider=data.get("signatureHelpProvider"),
            definition_provider=data.get("definitionProvider"),
            type_definition_provider=data.get("typeDefinitionProvider"),
            implementation_provider=data.get("implementationProvider"),
            references_provider=data.get("referencesProvider"),
            document_highlight_provider=data.get("documentHighlightProvider"),
            document_symbol_provider=data.get("documentSymbolProvider"),
            code_action_provider=data.get("codeActionProvider"),
            code_lens_provider=data.get("codeLensProvider"),
            document_link_provider=data.get("documentLinkProvider"),
            color_provider=data.get("colorProvider"),
            document_formatting_provider=data.get("documentFormattingProvider"),
            document_range_formatting_provider=data.get("documentRangeFormattingProvider"),
            document_on_type_formatting_provider=data.get("documentOnTypeFormattingProvider"),
            rename_provider=data.get("renameProvider"),
            folding_range_provider=data.get("foldingRangeProvider"),
            execute_command_provider=data.get("executeCommandProvider"),
            selection_range_provider=data.get("selectionRangeProvider"),
            linked_editing_range_provider=data.get("linkedEditingRangeProvider"),
            call_hierarchy_provider=data.get("callHierarchyProvider"),
            semantic_tokens_provider=data.get("semanticTokensProvider"),
            moniker_provider=data.get("monikerProvider"),
            type_hierarchy_provider=data.get("typeHierarchyProvider"),
            inline_value_provider=data.get("inlineValueProvider"),
            inlay_hint_provider=data.get("inlayHintProvider"),
            diagnostic_provider=data.get("diagnosticProvider"),
            workspace=data.get("workspace"),
            experimental=data.get("experimental")
        )


@dataclass
class InitializeResult:
    """Result of the initialize request."""
    capabilities: ServerCapabilities
    server_info: Optional[ServerInfo] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InitializeResult":
        capabilities = ServerCapabilities.from_dict(data["capabilities"])
        server_info = None
        if "serverInfo" in data:
            server_info = ServerInfo.from_dict(data["serverInfo"])
        return cls(capabilities=capabilities, server_info=server_info)


@dataclass
class ResponseError:
    """JSON-RPC 2.0 error response."""
    code: int
    message: str
    data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result


@dataclass
class Message:
    """JSON-RPC 2.0 message."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: Optional[str] = None
    params: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[ResponseError] = None

    def to_json(self) -> str:
        data: Dict[str, Any] = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            data["id"] = self.id
        if self.method is not None:
            data["method"] = self.method
        if self.params is not None:
            data["params"] = self.params
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error.to_dict()
        return json.dumps(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        error = None
        if "error" in data:
            err_data = data["error"]
            error = ResponseError(
                code=err_data["code"],
                message=err_data["message"],
                data=err_data.get("data")
            )
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=error
        )


# Language ID detection helper
def detect_language_id(uri: str) -> str:
    """Detect language ID from file URI/path."""
    ext = uri.lower().split(".")[-1] if "." in uri else ""

    extension_map = {
        "py": LanguageKind.PYTHON.value,
        "go": LanguageKind.GO.value,
        "ts": LanguageKind.TYPESCRIPT.value,
        "tsx": LanguageKind.TYPESCRIPT_REACT.value,
        "js": LanguageKind.JAVASCRIPT.value,
        "jsx": LanguageKind.JAVASCRIPT_REACT.value,
        "java": LanguageKind.JAVA.value,
        "rs": LanguageKind.RUST.value,
        "c": LanguageKind.C.value,
        "cpp": LanguageKind.CPP.value,
        "cc": LanguageKind.CPP.value,
        "cxx": LanguageKind.CPP.value,
        "h": LanguageKind.C.value,
        "hpp": LanguageKind.CPP.value,
        "cs": LanguageKind.CSHARP.value,
        "rb": LanguageKind.RUBY.value,
        "php": LanguageKind.PHP.value,
        "swift": LanguageKind.SWIFT.value,
        "kt": "kotlin",
        "scala": LanguageKind.SCALA.value,
        "lua": LanguageKind.LUA.value,
        "r": LanguageKind.R.value,
        "sh": LanguageKind.SHELL.value,
        "bash": LanguageKind.SHELL.value,
        "zsh": LanguageKind.SHELL.value,
        "ps1": LanguageKind.POWERSHELL.value,
        "sql": LanguageKind.SQL.value,
        "html": LanguageKind.HTML.value,
        "htm": LanguageKind.HTML.value,
        "css": LanguageKind.CSS.value,
        "scss": LanguageKind.SCSS.value,
        "sass": LanguageKind.SASS.value,
        "less": LanguageKind.LESS.value,
        "json": LanguageKind.JSON.value,
        "yaml": LanguageKind.YAML.value,
        "yml": LanguageKind.YAML.value,
        "xml": LanguageKind.XML.value,
        "md": LanguageKind.MARKDOWN.value,
        "markdown": LanguageKind.MARKDOWN.value,
        "dockerfile": LanguageKind.DOCKERFILE.value,
    }

    # Handle special filenames
    filename = uri.lower().split("/")[-1].split("\\")[-1]
    if filename == "dockerfile":
        return LanguageKind.DOCKERFILE.value
    if filename in ("makefile", "gnumakefile"):
        return LanguageKind.MAKEFILE.value

    return extension_map.get(ext, "plaintext")
