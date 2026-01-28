"""
MCP Tool Runner: Wrapper for Model Context Protocol tool execution.

This module provides a clean interface to MCP servers while handling:
- Server initialization from config
- Tool discovery
- Error handling (timeouts, server crashes, tool not found)
- Result normalization

JSON-RPC is handled internally by the MCP SDK - we just call Python methods.
"""

import asyncio
from typing import Dict, List, Optional
from pathlib import Path


class MCPToolRunner:
    """
    MCP client wrapper for tool execution.
    
    Responsibilities:
    - Load MCP servers from config file
    - Discover available tools
    - Execute tools with error handling
    - Normalize results to {"ok": bool, "output"|"error": str}
    
    Usage:
        runner = MCPToolRunner()
        await runner.initialize(".mcp/config.json")
        result = await runner.call("read_file", {"path": "README.md"})
        if result["ok"]:
            print(result["output"])
    """
    
    def __init__(self):
        """Initialize empty runner. Call initialize() before use."""
        self.session = None
        self.tools = {}  # {tool_name: tool_schema}
        self.initialized = False
    
    async def initialize(self, config_path: str) -> None:
        """
        Load MCP servers from config file.
        
        Config format (.mcp/config.json):
        {
          "mcpServers": {
            "filesystem": {
              "command": "npx",
              "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
            },
            "gmail": {...}
          }
        }
        
        Args:
            config_path: Path to MCP config JSON file
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            RuntimeError: If MCP initialization fails
        """
        if not Path(config_path).exists():
            raise FileNotFoundError(
                f"MCP config not found: {config_path}\n"
                "Create .mcp/config.json with your server configs."
            )
        
        try:
            # Import MCP SDK (lazy import to avoid dep issues if not installed)
            import mcp
            
            # Create and initialize session
            self.session = mcp.ClientSession()
            await self.session.initialize_from_config(config_path)
            
            # Discover tools
            tools_list = await self.session.list_tools()
            for tool in tools_list:
                self.tools[tool["name"]] = tool
            
            self.initialized = True
            
        except ImportError:
            raise RuntimeError(
                "MCP SDK not installed. Run: uv add mcp"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize MCP: {str(e)}")
    
    async def call(
        self,
        name: str,
        args: Dict[str, object],
        timeout: int = 30
    ) -> Dict[str, object]:
        """
        Execute tool via MCP.
        
        Args:
            name: Tool name
            args: Tool arguments
            timeout: Timeout in seconds (default: 30)
        
        Returns:
            Dict with keys:
            - "ok": bool (True if success, False if error)
            - "output": str (tool result if ok=True)
            - "error": str (error message if ok=False)
        
        Error Handling:
            - ToolNotFoundError → {"ok": False, "error": "Tool not found: ..."}
            - ToolExecutionError → {"ok": False, "error": "Execution failed: ..."}
            - TimeoutError → {"ok": False, "error": "Timeout after Xs"}
            - Generic Exception → {"ok": False, "error": "Unexpected error: ..."}
        """
        if not self.initialized:
            return {
                "ok": False,
                "error": "MCPToolRunner not initialized. Call initialize() first."
            }
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.session.call_tool(name, args),
                timeout=timeout
            )
            
            # MCP result format: {"content": [{"type": "text", "text": "..."}]}
            content = result.get("content", [])
            if not content:
                return {"ok": False, "error": "Empty result from MCP server"}
            
            # Extract text from first content item
            first_item = content[0]
            if isinstance(first_item, dict):
                output = first_item.get("text", str(first_item))
            else:
                output = str(first_item)
            
            return {"ok": True, "output": output}
        
        except asyncio.TimeoutError:
            return {
                "ok": False,
                "error": f"Tool execution timeout after {timeout}s"
            }
        
        except Exception as e:
            # Handle known MCP exceptions
            error_name = type(e).__name__
            if "ToolNotFound" in error_name:
                return {
                    "ok": False,
                    "error": f"Tool not found: {name}"
                }
            elif "ToolExecution" in error_name:
                return {
                    "ok": False,
                    "error": f"Tool execution failed: {str(e)}"
                }
            else:
                return {
                    "ok": False,
                    "error": f"Unexpected error ({error_name}): {str(e)}"
                }
    
    def list_available_tools(self) -> List[str]:
        """
        Get list of available tool names.
        
        Returns:
            List of tool names discovered from MCP servers
        """
        return list(self.tools.keys())
    
    def get_tool_schema(self, name: str) -> Optional[Dict[str, object]]:
        """
        Get JSON schema for a specific tool.
        
        Args:
            name: Tool name
        
        Returns:
            Tool schema dict or None if not found
        """
        return self.tools.get(name)


# For testing without real MCP server
class MockMCPToolRunner(MCPToolRunner):
    """
    Mock runner for testing without real MCP servers.
    
    Usage:
        runner = MockMCPToolRunner()
        await runner.initialize("")  # No-op
        result = await runner.call("read_file", {"path": "test.txt"})
        # Returns mock data
    """
    
    async def initialize(self, config_path: str) -> None:
        """No-op initialization."""
        self.tools = {
            "read_file": {"name": "read_file"},
            "write_file": {"name": "write_file"},
            "glob": {"name": "glob"},
        }
        self.initialized = True
    
    async def call(
        self,
        name: str,
        args: Dict[str, object],
        timeout: int = 30
    ) -> Dict[str, object]:
        """Return mock data based on tool name."""
        if name == "read_file":
            path = args.get("path", "unknown")
            return {"ok": True, "output": f"Mock content of {path}"}
        
        elif name == "glob":
            pattern = args.get("pattern", "*")
            return {"ok": True, "output": f"file1.txt\nfile2.txt  (mock glob: {pattern})"}
        
        elif name == "write_file":
            return {"ok": True, "output": "File written successfully (mock)"}
        
        else:
            return {"ok": False, "error": f"Mock tool not implemented: {name}"}


__all__ = ["MCPToolRunner", "MockMCPToolRunner"]
