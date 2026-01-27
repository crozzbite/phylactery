"""
Backend protocol definition for filesystem operations.

This module defines the interface that all backend implementations must follow.
Based on LangChain Deep Agents BackendProtocol.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Optional


@dataclass
class FileInfo:
    """Information about a file in the filesystem."""
    
    path: str
    is_dir: bool = False
    size: Optional[int] = None
    modified_at: Optional[datetime] = None


@dataclass
class WriteResult:
    """Result of a write operation."""
    
    path: Optional[str] = None
    error: Optional[str] = None
    files_update: Optional[dict[str, str]] = None  # For StateBackend only


@dataclass
class EditResult:
    """Result of an edit operation."""
    
    path: Optional[str] = None
    error: Optional[str] = None
    files_update: Optional[dict[str, str]] = None  # For StateBackend only
    occurrences: int = 0


@dataclass
class GrepMatch:
    """A single grep match result."""
    
    path: str
    line: int
    text: str


class BackendProtocol(Protocol):
    """
    Protocol that all filesystem backends must implement.
    
    Backends provide storage abstraction for filesystem operations,
    allowing different persistence strategies (RAM, disk, database, etc.).
    """
    
    def ls_info(self, path: str) -> list[FileInfo]:
        """
        List files and directories at the given path.
        
        Args:
            path: Absolute path to list (e.g., "/workspace/")
            
        Returns:
            List of FileInfo objects, sorted by path
        """
        ...
    
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """
        Read file contents with line numbers.
        
        Args:
            file_path: Absolute path to file
            offset: Starting line number (0-indexed)
            limit: Maximum number of lines to read
            
        Returns:
            Numbered content or error message like "Error: File '/x' not found"
        """
        ...
    
    def grep_raw(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None
    ) -> list[GrepMatch] | str:
        """
        Search for pattern in files.
        
        Args:
            pattern: Regex pattern to search for
            path: Optional directory to search in
            glob: Optional glob pattern to filter files
            
        Returns:
            List of GrepMatch objects, or error string if invalid regex
        """
        ...
    
    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        """
        Find files matching a glob pattern.
        
        Args:
            pattern: Glob pattern (e.g., "**/*.py")
            path: Base path to search from
            
        Returns:
            List of matching FileInfo objects
        """
        ...
    
    def write(self, file_path: str, content: str) -> WriteResult:
        """
        Create a new file (create-only, fails if exists).
        
        Args:
            file_path: Absolute path for new file
            content: File content
            
        Returns:
            WriteResult with path on success, or error message
        """
        ...
    
    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False
    ) -> EditResult:
        """
        Edit an existing file by replacing exact string matches.
        
        Args:
            file_path: Absolute path to file
            old_string: Exact string to replace
            new_string: Replacement string
            replace_all: If False, old_string must be unique; if True, replace all occurrences
            
        Returns:
            EditResult with occurrences count on success, or error message
        """
        ...
