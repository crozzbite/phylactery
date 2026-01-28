import logging
from contextlib import AsyncExitStack
from typing import TypedDict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

logger = logging.getLogger(__name__)


class MCPTool(TypedDict):
    """Definition of an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, object]


class MCPClient:
    """Client for connecting to Model Context Protocol (MCP) servers."""

    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
        self.session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    async def connect(self) -> None:
        """Connects to the MCP server."""
        self._exit_stack = AsyncExitStack()
        read, write = await self._exit_stack.enter_async_context(stdio_client(self.server_params))
        self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        logger.info("Connected to MCP Server")

    async def list_tools(self) -> list[MCPTool]:
        """Lists available tools from the server."""
        if not self.session:
            raise RuntimeError("Client not connected")

        response = await self.session.list_tools()
        tools: list[MCPTool] = []
        for tool in response.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description or "No description",
                "input_schema": tool.inputSchema,
            })
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> str:
        """Calls a tool on the server."""
        if not self.session:
            raise RuntimeError("Client not connected")

        result: CallToolResult = await self.session.call_tool(tool_name, arguments)

        # Format the result content
        output = []
        if result.content:
            for item in result.content:
                if item.type == "text":
                    output.append(item.text)
                # Handle other content types if needed

        return "\n".join(output) if output else "No output"

    async def close(self) -> None:
        """Closes the connection."""
        if self._exit_stack:
            await self._exit_stack.aclose()
