"""
StateBackend: Ephemeral in-memory filesystem storage.

Files are stored in the agent's state (AgentState) and persist only within
a single thread/session. Data is lost when the agent restarts.

Use case: Temporary working files, scratch pad, evicted tool results.
"""

from datetime import datetime
from typing import Optional
import re
from fnmatch import fnmatch

from .protocol import BackendProtocol, FileInfo, WriteResult, EditResult, GrepMatch


class StateBackend(BackendProtocol):
    """
    In-memory filesystem backend using agent state.
    
    Files are stored in a dictionary within AgentState and are ephemeral
    (lost on restart). This is the default backend for Phylactery.
    """
    
    def __init__(self, runtime: "ToolRuntime"):  # type: ignore
        """
        Initialize StateBackend with access to runtime state.
        
        Args:
            runtime: Tool runtime providing access to agent state
        """
        self.runtime = runtime
    
    @property
    def _files(self) -> dict[str, str]:
        """Get files dict from state, initializing if needed."""
        if not hasattr(self.runtime.state, "files"):
            self.runtime.state["files"] = {}
        return self.runtime.state["files"]
    
    def ls_info(self, path: str) -> list[FileInfo]:
        """List files and directories at path."""
        path = path.rstrip("/") + "/"
        if path == "//":
            path = "/"
        
        results: dict[str, FileInfo] = {}
        
        for file_path, content in self._files.items():
            if file_path.startswith(path):
                relative = file_path[len(path):]
                
                # Direct child file
                if "/" not in relative:
                    results[file_path] = FileInfo(
                        path=file_path,
                        is_dir=False,
                        size=len(content),
                        modified_at=datetime.now()
                    )
                # Child directory
                else:
                    dir_name = relative.split("/")[0]
                    dir_path = path + dir_name + "/"
                    if dir_path not in results:
                        results[dir_path] = FileInfo(
                            path=dir_path,
                            is_dir=True
                        )
        
        return sorted(results.values(), key=lambda x: x.path)
    
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file with line numbers."""
        if file_path not in self._files:
            return f"Error: File '{file_path}' not found"
        
        content = self._files[file_path]
        lines = content.splitlines()
        
        # Apply offset and limit
        selected_lines = lines[offset:offset + limit]
        
        # Add line numbers (1-indexed)
        numbered = [
            f"{offset + i + 1}: {line}"
            for i, line in enumerate(selected_lines)
        ]
        
        return "\n".join(numbered)
    
    def grep_raw(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None
    ) -> list[GrepMatch] | str:
        """Search for pattern in files."""
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"Invalid regex pattern: {e}"
        
        matches: list[GrepMatch] = []
        
        for file_path, content in self._files.items():
            # Filter by path
            if path and not file_path.startswith(path):
                continue
            
            # Filter by glob
            if glob and not fnmatch(file_path, glob):
                continue
            
            # Search in content
            for line_num, line in enumerate(content.splitlines(), start=1):
                if regex.search(line):
                    matches.append(GrepMatch(
                        path=file_path,
                        line=line_num,
                        text=line
                    ))
        
        return matches
    
    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        """Find files matching glob pattern."""
        results: list[FileInfo] = []
        
        for file_path, content in self._files.items():
            if file_path.startswith(path) and fnmatch(file_path, pattern):
                results.append(FileInfo(
                    path=file_path,
                    is_dir=False,
                    size=len(content),
                    modified_at=datetime.now()
                ))
        
        return sorted(results, key=lambda x: x.path)
    
    def write(self, file_path: str, content: str) -> WriteResult:
        """Create new file (fails if exists)."""
        if file_path in self._files:
            return WriteResult(error=f"File '{file_path}' already exists")
        
        self._files[file_path] = content
        
        return WriteResult(
            path=file_path,
            files_update={file_path: content}  # For state persistence
        )
    
    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False
    ) -> EditResult:
        """Edit file by replacing exact string matches."""
        if file_path not in self._files:
            return EditResult(error=f"File '{file_path}' not found")
        
        content = self._files[file_path]
        occurrences = content.count(old_string)
        
        if occurrences == 0:
            return EditResult(error=f"String '{old_string}' not found in file")
        
        if not replace_all and occurrences > 1:
            return EditResult(
                error=f"String '{old_string}' appears {occurrences} times. "
                      f"Use replace_all=True to replace all occurrences."
            )
        
        # Perform replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
        
        self._files[file_path] = new_content
        
        return EditResult(
            path=file_path,
            files_update={file_path: new_content},
            occurrences=occurrences
        )
