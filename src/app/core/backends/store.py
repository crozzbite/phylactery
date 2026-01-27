"""
StoreBackend: Persistent cross-thread filesystem storage.

Files are stored in a durable store (SQLite for dev, Firestore for prod)
and persist across sessions and threads. Uses LangGraph BaseStore interface.

Use case: Long-term memories, persistent knowledge, cross-session data.
"""

from datetime import datetime
from typing import Optional
import re
from fnmatch import fnmatch
import json

from .protocol import BackendProtocol, FileInfo, WriteResult, EditResult, GrepMatch


class StoreBackend(BackendProtocol):
    """
    Persistent filesystem backend using LangGraph BaseStore.
    
    Files persist across threads and sessions. Storage implementation
    is pluggable (SQLite, Firestore, etc.).
    """
    
    def __init__(self, runtime: "ToolRuntime"):  # type: ignore
        """
        Initialize StoreBackend with access to runtime store.
        
        Args:
            runtime: Tool runtime providing access to BaseStore
        """
        self.runtime = runtime
        self.namespace = ("filesystem",)
    
    @property
    def _store(self):
        """Get store from runtime."""
        if not hasattr(self.runtime, "store") or self.runtime.store is None:
            raise RuntimeError("StoreBackend requires a configured store in runtime")
        return self.runtime.store
    
    def _get_file(self, file_path: str) -> Optional[dict]:
        """Get file metadata and content from store."""
        try:
            item = self._store.get(namespace=self.namespace, key=file_path)
            return item.value if item else None
        except Exception:
            return None
    
    def _put_file(self, file_path: str, content: str) -> None:
        """Store file in persistent storage."""
        self._store.put(
            namespace=self.namespace,
            key=file_path,
            value={
                "content": content,
                "modified_at": datetime.now().isoformat(),
                "size": len(content)
            }
        )
    
    def _list_all_files(self) -> list[tuple[str, dict]]:
        """List all files in store."""
        try:
            items = self._store.search(namespace_prefix=self.namespace)
            return [(item.key, item.value) for item in items]
        except Exception:
            return []
    
    def ls_info(self, path: str) -> list[FileInfo]:
        """List files and directories at path."""
        path = path.rstrip("/") + "/"
        if path == "//":
            path = "/"
        
        results: dict[str, FileInfo] = {}
        
        for file_path, metadata in self._list_all_files():
            if file_path.startswith(path):
                relative = file_path[len(path):]
                
                # Direct child file
                if "/" not in relative:
                    results[file_path] = FileInfo(
                        path=file_path,
                        is_dir=False,
                        size=metadata.get("size"),
                        modified_at=datetime.fromisoformat(metadata["modified_at"])
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
        file_data = self._get_file(file_path)
        if not file_data:
            return f"Error: File '{file_path}' not found"
        
        content = file_data["content"]
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
        
        for file_path, metadata in self._list_all_files():
            # Filter by path
            if path and not file_path.startswith(path):
                continue
            
            # Filter by glob
            if glob and not fnmatch(file_path, glob):
                continue
            
            # Search in content
            content = metadata["content"]
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
        
        for file_path, metadata in self._list_all_files():
            if file_path.startswith(path) and fnmatch(file_path, pattern):
                results.append(FileInfo(
                    path=file_path,
                    is_dir=False,
                    size=metadata.get("size"),
                    modified_at=datetime.fromisoformat(metadata["modified_at"])
                ))
        
        return sorted(results, key=lambda x: x.path)
    
    def write(self, file_path: str, content: str) -> WriteResult:
        """Create new file (fails if exists)."""
        if self._get_file(file_path):
            return WriteResult(error=f"File '{file_path}' already exists")
        
        self._put_file(file_path, content)
        
        return WriteResult(
            path=file_path,
            files_update=None  # External persistence, no state update needed
        )
    
    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False
    ) -> EditResult:
        """Edit file by replacing exact string matches."""
        file_data = self._get_file(file_path)
        if not file_data:
            return EditResult(error=f"File '{file_path}' not found")
        
        content = file_data["content"]
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
        
        self._put_file(file_path, new_content)
        
        return EditResult(
            path=file_path,
            files_update=None,  # External persistence
            occurrences=occurrences
        )
