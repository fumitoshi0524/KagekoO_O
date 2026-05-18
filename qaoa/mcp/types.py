"""MCP (Model Context Protocol) type definitions.

This module provides type definitions for the Model Context Protocol,
based on the MCP specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..config.constants import MCPType


# Protocol version
LATEST_PROTOCOL_VERSION = "2024-11-05"


@dataclass
class Implementation:
    """Client or server implementation information.

    Attributes:
        name: Name of the implementation
        version: Version string
    """

    name: str
    version: str


@dataclass
class Capabilities:
    """Client or server capabilities.

    Attributes:
        experimental: Experimental capabilities
        tools: Tool capabilities
        resources: Resource capabilities
        prompts: Prompt capabilities
        logging: Logging capabilities
    """

    experimental: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, Any] = field(default_factory=dict)
    resources: dict[str, Any] = field(default_factory=dict)
    prompts: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClientCapabilities:
    """Client capabilities for initialization."""

    experimental: dict[str, Any] = field(default_factory=dict)
    roots: dict[str, Any] = field(default_factory=dict)
    sampling: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerCapabilities:
    """Server capabilities returned from initialization."""

    experimental: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None
    logging: dict[str, Any] | None = None


@dataclass
class InitializeRequest:
    """Initialize request from client to server.

    Attributes:
        protocol_version: The protocol version to use
        capabilities: Client capabilities
        client_info: Client implementation info
    """

    protocol_version: str = LATEST_PROTOCOL_VERSION
    capabilities: ClientCapabilities = field(default_factory=ClientCapabilities)
    client_info: Implementation = field(
        default_factory=lambda: Implementation(name="Kageko", version="0.1.0")
    )


@dataclass
class InitializeResult:
    """Initialize result from server.

    Attributes:
        protocol_version: The protocol version being used
        capabilities: Server capabilities
        server_info: Server implementation info
        instructions: Optional instructions for the client
    """

    protocol_version: str
    capabilities: ServerCapabilities
    server_info: Implementation
    instructions: str | None = None


@dataclass
class ToolInputSchema:
    """JSON Schema for tool input parameters.

    Attributes:
        type: Schema type (usually "object")
        properties: Property definitions
        required: List of required property names
    """

    type: str = "object"
    properties: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)


@dataclass
class Tool:
    """MCP Tool definition.

    Attributes:
        name: Tool name
        description: Tool description
        input_schema: Input parameter schema
        category: QAOA functional category
        domain: QAOA application domain
    """

    name: str
    description: str
    input_schema: ToolInputSchema = field(default_factory=ToolInputSchema)
    category: str = ""
    domain: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tool":
        """Create a Tool from a dictionary.

        Args:
            data: Dictionary with tool data

        Returns:
            Tool instance
        """
        input_schema = ToolInputSchema()
        if "inputSchema" in data:
            schema = data["inputSchema"]
            input_schema = ToolInputSchema(
                type=schema.get("type", "object"),
                properties=schema.get("properties", {}),
                required=schema.get("required", []),
            )

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            input_schema=input_schema,
        )


@dataclass
class ListToolsRequest:
    """Request to list available tools.

    Attributes:
        cursor: Pagination cursor for large result sets
    """

    cursor: str | None = None


@dataclass
class ListToolsResult:
    """Result of listing tools.

    Attributes:
        tools: List of available tools
        next_cursor: Cursor for next page of results
    """

    tools: list[Tool] = field(default_factory=list)
    next_cursor: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ListToolsResult":
        """Create a ListToolsResult from a dictionary.

        Args:
            data: Dictionary with result data

        Returns:
            ListToolsResult instance
        """
        tools = []
        for tool_data in data.get("tools", []):
            tools.append(Tool.from_dict(tool_data))

        return cls(
            tools=tools,
            next_cursor=data.get("nextCursor"),
        )


@dataclass
class CallToolRequest:
    """Request to call a tool.

    Attributes:
        name: Tool name
        arguments: Tool arguments
    """

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class TextContent:
    """Text content in a tool result.

    Attributes:
        type: Content type (always "text")
        text: The text content
    """

    type: str = "text"
    text: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TextContent":
        """Create a TextContent from a dictionary.

        Args:
            data: Dictionary with content data

        Returns:
            TextContent instance
        """
        return cls(
            type=data.get("type", "text"),
            text=data.get("text", ""),
        )


@dataclass
class ImageContent:
    """Image content in a tool result.

    Attributes:
        type: Content type (always "image")
        data: Base64-encoded image data
        mime_type: Image MIME type
    """

    type: str = "image"
    data: str = ""
    mime_type: str = "image/png"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImageContent":
        """Create an ImageContent from a dictionary.

        Args:
            data: Dictionary with content data

        Returns:
            ImageContent instance
        """
        return cls(
            type=data.get("type", "image"),
            data=data.get("data", ""),
            mime_type=data.get("mimeType", "image/png"),
        )


@dataclass
class ResourceContent:
    """Resource reference content.

    Attributes:
        type: Content type (always "resource")
        uri: Resource URI
        mime_type: Resource MIME type
        text: Text content (if text resource)
        blob: Binary content (if binary resource)
    """

    type: str = "resource"
    uri: str = ""
    mime_type: str | None = None
    text: str | None = None
    blob: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResourceContent":
        """Create a ResourceContent from a dictionary.

        Args:
            data: Dictionary with content data

        Returns:
            ResourceContent instance
        """
        return cls(
            type=data.get("type", "resource"),
            uri=data.get("uri", ""),
            mime_type=data.get("mimeType"),
            text=data.get("text"),
            blob=data.get("blob"),
        )


# Content type alias
Content = TextContent | ImageContent | ResourceContent


@dataclass
class CallToolResult:
    """Result of calling a tool.

    Attributes:
        content: List of content items
        is_error: Whether the result is an error
    """

    content: list[Content] = field(default_factory=list)
    is_error: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CallToolResult":
        """Create a CallToolResult from a dictionary.

        Args:
            data: Dictionary with result data

        Returns:
            CallToolResult instance
        """
        content: list[Content] = []
        for item in data.get("content", []):
            content_type = item.get("type", "text")
            if content_type == "text":
                content.append(TextContent.from_dict(item))
            elif content_type == "image":
                content.append(ImageContent.from_dict(item))
            elif content_type == "resource":
                content.append(ResourceContent.from_dict(item))

        return cls(
            content=content,
            is_error=data.get("isError", False),
        )

    def get_text(self) -> str:
        """Get all text content as a single string.

        Returns:
            Combined text from all text content items
        """
        texts = []
        for item in self.content:
            if isinstance(item, TextContent):
                texts.append(item.text)
            else:
                texts.append(str(item))
        return "\n".join(texts)


# Resource types


@dataclass
class Resource:
    """MCP Resource definition.

    Attributes:
        uri: Resource URI
        name: Resource name
        description: Resource description
        mime_type: Resource MIME type
    """

    uri: str
    name: str
    description: str | None = None
    mime_type: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Resource":
        """Create a Resource from a dictionary.

        Args:
            data: Dictionary with resource data

        Returns:
            Resource instance
        """
        return cls(
            uri=data.get("uri", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            mime_type=data.get("mimeType"),
        )


@dataclass
class ListResourcesRequest:
    """Request to list available resources.

    Attributes:
        cursor: Pagination cursor
    """

    cursor: str | None = None


@dataclass
class ListResourcesResult:
    """Result of listing resources.

    Attributes:
        resources: List of resources
        next_cursor: Cursor for next page
    """

    resources: list[Resource] = field(default_factory=list)
    next_cursor: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ListResourcesResult":
        """Create a ListResourcesResult from a dictionary.

        Args:
            data: Dictionary with result data

        Returns:
            ListResourcesResult instance
        """
        resources = []
        for res_data in data.get("resources", []):
            resources.append(Resource.from_dict(res_data))

        return cls(
            resources=resources,
            next_cursor=data.get("nextCursor"),
        )


@dataclass
class ReadResourceRequest:
    """Request to read a resource.

    Attributes:
        uri: Resource URI
    """

    uri: str


@dataclass
class ReadResourceResult:
    """Result of reading a resource.

    Attributes:
        contents: List of resource contents
    """

    contents: list[ResourceContent] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReadResourceResult":
        """Create a ReadResourceResult from a dictionary.

        Args:
            data: Dictionary with result data

        Returns:
            ReadResourceResult instance
        """
        contents = []
        for item in data.get("contents", []):
            contents.append(ResourceContent.from_dict(item))

        return cls(contents=contents)


# JSON-RPC types


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 Request.

    Attributes:
        jsonrpc: Protocol version (always "2.0")
        id: Request ID
        method: Method name
        params: Method parameters
    """

    jsonrpc: str = "2.0"
    id: int | str | None = None
    method: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        result: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.id is not None:
            result["id"] = self.id
        if self.params:
            result["params"] = self.params
        return result


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 Response.

    Attributes:
        jsonrpc: Protocol version (always "2.0")
        id: Request ID
        result: Result data (if successful)
        error: Error data (if failed)
    """

    jsonrpc: str = "2.0"
    id: int | str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JSONRPCResponse":
        """Create a JSONRPCResponse from a dictionary.

        Args:
            data: Dictionary with response data

        Returns:
            JSONRPCResponse instance
        """
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error"),
        )

    def is_error(self) -> bool:
        """Check if this is an error response.

        Returns:
            True if error response
        """
        return self.error is not None


@dataclass
class JSONRPCError:
    """JSON-RPC 2.0 Error.

    Attributes:
        code: Error code
        message: Error message
        data: Additional error data
    """

    code: int
    message: str
    data: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.data is not None:
            result["data"] = self.data
        return result


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
