"""
Tool Registry: Dynamic tool discovery from MCP servers.

Responsibilities:
- Load tools from MCP client at runtime
- Validate tool availability
- Provide tool schemas for validation

Benefits:
- No hardcoded tool lists
- Automatically supports new MCP servers
- Enables runtime extensibility
"""

from typing import Dict, Optional


class ToolRegistry:
    """
    Dynamic registry of available tools from MCP servers.
    
    Usage:
        registry = ToolRegistry()
        await registry.register_from_mcp(mcp_runner)
        
        if registry.is_allowed("read_file"):
            schema = registry.get_schema("read_file")
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self.tools: Dict[str, Dict[str, object]] = {}
    
    def register_from_mcp(self, mcp_runner) -> None:
        """
        Discover and register tools from MCP runner.
        
        Args:
            mcp_runner: MCPToolRunner instance (must be initialized)
        
        Raises:
            RuntimeError: If MCP runner not initialized
        """
        if not mcp_runner.initialized:
            raise RuntimeError(
                "MCPToolRunner not initialized. "
                "Call mcp_runner.initialize() first."
            )
        
        # Get all available tools
        tool_names = mcp_runner.list_available_tools()
        
        for name in tool_names:
            schema = mcp_runner.get_tool_schema(name)
            self.tools[name] = {
                "name": name,
                "schema": schema or {},
                "source": "mcp"
            }
    
    def register_custom(self, name: str, schema: Dict[str, object]) -> None:
        """
        Register a custom tool (non-MCP).
        
        Args:
            name: Tool name
            schema: Tool JSON schema
        """
        self.tools[name] = {
            "name": name,
            "schema": schema,
            "source": "custom"
        }
    
    def is_allowed(self, name: str) -> bool:
        """
        Check if tool is registered.
        
        Args:
            name: Tool name
        
        Returns:
            bool: True if tool exists in registry
        """
        return name in self.tools
    
    def get_schema(self, name: str) -> Optional[Dict[str, object]]:
        """
        Get JSON schema for a tool.
        
        Args:
            name: Tool name
        
        Returns:
            Schema dict or None if not found
        """
        tool = self.tools.get(name)
        return tool.get("schema") if tool else None
    
    def list_tools(self) -> List[str]:
        """
        Get list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self.tools.keys())
    
    def clear(self) -> None:
        """Clear all registered tools (useful for testing)."""
        self.tools.clear()


# Global instance (singleton pattern)
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get global tool registry instance.
    
    Returns:
        ToolRegistry: Singleton instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


__all__ = [
    "ToolRegistry",
    "get_tool_registry"
]
