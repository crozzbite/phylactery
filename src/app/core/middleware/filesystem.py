"""
Filesystem Middleware for Phylactery.

Provides 6 filesystem tools to agents:
- ls: List files and directories
- read_file: Read file contents with line numbers
- write_file: Create new files
- edit_file: Edit existing files
- glob: Find files by pattern
- grep: Search file contents

Based on LangChain Deep Agents FilesystemMiddleware.
"""

from typing import Optional, Callable
from langchain_core.tools import tool

from ..backends.protocol import BackendProtocol
from ..backends.state import StateBackend


BackendFactory = Callable[["ToolRuntime"], BackendProtocol]  # type: ignore


class FilesystemMiddleware:
    """
    Middleware that provides filesystem tools to agents.
    
    Tools operate through a pluggable backend, allowing different
    storage strategies (RAM, disk, database, etc.).
    """
    
    def __init__(
        self,
        backend: Optional[BackendProtocol | BackendFactory] = None,
        system_prompt: Optional[str] = None,
        custom_tool_descriptions: Optional[dict[str, str]] = None
    ):
        """
        Initialize FilesystemMiddleware.
        
        Args:
            backend: Backend instance or factory function. Defaults to StateBackend.
            system_prompt: Optional custom addition to system prompt
            custom_tool_descriptions: Optional custom descriptions for tools
        """
        self.backend_factory = backend
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.custom_descriptions = custom_tool_descriptions or {}
    
    def _default_system_prompt(self) -> str:
        """Default system prompt explaining filesystem tools."""
        return """
You have access to a filesystem with the following tools:

- **ls**: List files and directories
- **read_file**: Read file contents (with line numbers and pagination)
- **write_file**: Create new files (fails if file exists)
- **edit_file**: Edit existing files by exact string replacement
- **glob**: Find files matching a pattern (e.g., **/*.py)
- **grep**: Search for text in files

Use the filesystem to:
- Store intermediate results from tool calls
- Keep notes and context across multiple steps
- Organize information by topic or task
- Remember important findings

Files in /workspace/ are temporary (lost on restart).
Files in /memories/ persist across sessions.
"""
    
    def get_tools(self, runtime: "ToolRuntime") -> list:  # type: ignore
        """
        Get filesystem tools bound to a specific runtime.
        
        Args:
            runtime: Tool runtime providing access to backend
            
        Returns:
            List of LangChain tools
        """
        # Initialize backend
        if self.backend_factory is None:
            backend = StateBackend(runtime)
        elif callable(self.backend_factory):
            backend = self.backend_factory(runtime)
        else:
            backend = self.backend_factory
        
        # Create tools with backend bound
        @tool
        def ls(path: str = "/") -> str:
            """
            List files and directories at the given path.
            
            Args:
                path: Directory path to list (default: "/")
                
            Returns:
                Formatted list of files and directories with metadata
            """
            try:
                items = backend.ls_info(path)
                if not items:
                    return f"Directory '{path}' is empty"
                
                lines = []
                for item in items:
                    if item.is_dir:
                        lines.append(f"📁 {item.path}")
                    else:
                        size_kb = item.size // 1024 if item.size else 0
                        lines.append(f"📄 {item.path} ({size_kb}KB)")
                
                return "\n".join(lines)
            except Exception as e:
                return f"Error listing '{path}': {e}"
        
        @tool
        def read_file(file_path: str, offset: int = 0, limit: int = 2000) -> str:
            """
            Read file contents with line numbers.
            
            Args:
                file_path: Path to file
                offset: Starting line number (0-indexed)
                limit: Maximum number of lines to read
                
            Returns:
                File contents with line numbers, or error message
            """
            return backend.read(file_path, offset, limit)
        
        @tool
        def write_file(file_path: str, content: str) -> str:
            """
            Create a new file. Fails if file already exists.
            
            Args:
                file_path: Path for new file (must start with /)
                content: File content
                
            Returns:
                Success message or error
            """
            result = backend.write(file_path, content)
            if result.error:
                return f"Error: {result.error}"
            return f"File created: {result.path}"
        
        @tool
        def edit_file(
            file_path: str,
            old_string: str,
            new_string: str,
            replace_all: bool = False
        ) -> str:
            """
            Edit file by replacing exact string matches.
            
            Args:
                file_path: Path to file
                old_string: Exact string to replace
                new_string: Replacement string
                replace_all: If False, old_string must be unique. If True, replace all occurrences.
                
            Returns:
                Success message with occurrence count, or error
            """
            result = backend.edit(file_path, old_string, new_string, replace_all)
            if result.error:
                return f"Error: {result.error}"
            return f"Replaced {result.occurrences} occurrence(s) in {result.path}"
        
        @tool
        def glob(pattern: str, path: str = "/") -> str:
            """
            Find files matching a glob pattern.
            
            Args:
                pattern: Glob pattern (e.g., "**/*.py", "*.md")
                path: Base path to search from
                
            Returns:
                List of matching file paths
            """
            try:
                items = backend.glob_info(pattern, path)
                if not items:
                    return f"No files match pattern '{pattern}'"
                
                paths = [item.path for item in items]
                return "\n".join(paths)
            except Exception as e:
                return f"Error: {e}"
        
        @tool
        def grep(pattern: str, path: Optional[str] = None, glob_pattern: Optional[str] = None) -> str:
            """
            Search for text in files using regex.
            
            Args:
                pattern: Regex pattern to search for
                path: Optional directory to search in
                glob_pattern: Optional glob pattern to filter files
                
            Returns:
                Matching lines with file paths and line numbers
            """
            result = backend.grep_raw(pattern, path, glob_pattern)
            if isinstance(result, str):
                return f"Error: {result}"
            
            if not result:
                return f"No matches found for pattern '{pattern}'"
            
            lines = []
            for match in result:
                lines.append(f"{match.path}:{match.line}: {match.text}")
            
            return "\n".join(lines)
        
        return [ls, read_file, write_file, edit_file, glob, grep]
