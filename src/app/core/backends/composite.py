"""
CompositeBackend: Route different paths to different backends.

Allows hybrid storage strategies, e.g.:
- /workspace/ → StateBackend (ephemeral)
- /memories/ → StoreBackend (persistent)

Routes are matched by longest prefix.
"""

from typing import Optional, Callable

from .protocol import BackendProtocol, FileInfo, WriteResult, EditResult, GrepMatch


BackendFactory = Callable[["ToolRuntime"], BackendProtocol]  # type: ignore


class CompositeBackend(BackendProtocol):
    """
    Router backend that delegates to different backends based on path prefix.
    
    Example:
        CompositeBackend(
            default=StateBackend(runtime),
            routes={
                "/memories/": StoreBackend(runtime),
                "/skills/": StoreBackend(runtime)
            }
        )
    
    Longest prefix wins. Paths are preserved in results.
    """
    
    def __init__(
        self,
        default: BackendProtocol,
        routes: dict[str, BackendProtocol]
    ):
        """
        Initialize CompositeBackend with routing rules.
        
        Args:
            default: Backend to use when no route matches
            routes: Mapping of path prefixes to backends (longest prefix wins)
        """
        self.default = default
        # Sort routes by length (longest first) for correct matching
        self.routes = sorted(
            routes.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )
    
    def _get_backend(self, path: str) -> BackendProtocol:
        """Get the appropriate backend for a given path."""
        for prefix, backend in self.routes:
            if path.startswith(prefix):
                return backend
        return self.default
    
    def ls_info(self, path: str) -> list[FileInfo]:
        """List files, aggregating results from all backends if needed."""
        backend = self._get_backend(path)
        
        # If path exactly matches a route prefix, only use that backend
        for prefix, route_backend in self.routes:
            if path == prefix or path == prefix.rstrip("/"):
                return route_backend.ls_info(path)
        
        # Otherwise, aggregate results from all backends
        results: dict[str, FileInfo] = {}
        
        # Get from matched backend
        for info in backend.ls_info(path):
            results[info.path] = info
        
        # If listing root or a parent of routes, show route directories
        if path in ["/", ""]:
            for prefix, route_backend in self.routes:
                # Add route prefix as directory
                dir_path = prefix.rstrip("/") + "/"
                if dir_path not in results:
                    results[dir_path] = FileInfo(path=dir_path, is_dir=True)
        
        return sorted(results.values(), key=lambda x: x.path)
    
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file from appropriate backend."""
        backend = self._get_backend(file_path)
        return backend.read(file_path, offset, limit)
    
    def grep_raw(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None
    ) -> list[GrepMatch] | str:
        """Search across all backends, aggregating results."""
        all_matches: list[GrepMatch] = []
        
        # Determine which backends to search
        if path:
            # Search only in the backend that handles this path
            backend = self._get_backend(path)
            result = backend.grep_raw(pattern, path, glob)
            if isinstance(result, str):
                return result  # Error
            all_matches.extend(result)
        else:
            # Search in all backends
            backends_to_search = [self.default]
            backends_to_search.extend(backend for _, backend in self.routes)
            
            for backend in backends_to_search:
                result = backend.grep_raw(pattern, path, glob)
                if isinstance(result, str):
                    return result  # Error
                all_matches.extend(result)
        
        # Remove duplicates and sort
        unique_matches = {(m.path, m.line, m.text): m for m in all_matches}
        return sorted(unique_matches.values(), key=lambda x: (x.path, x.line))
    
    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        """Find files across all backends."""
        all_results: dict[str, FileInfo] = {}
        
        # Determine which backends to search
        if path != "/":
            # Search only in the backend that handles this path
            backend = self._get_backend(path)
            for info in backend.glob_info(pattern, path):
                all_results[info.path] = info
        else:
            # Search in all backends
            backends_to_search = [self.default]
            backends_to_search.extend(backend for _, backend in self.routes)
            
            for backend in backends_to_search:
                for info in backend.glob_info(pattern, path):
                    all_results[info.path] = info
        
        return sorted(all_results.values(), key=lambda x: x.path)
    
    def write(self, file_path: str, content: str) -> WriteResult:
        """Write to appropriate backend based on path."""
        backend = self._get_backend(file_path)
        return backend.write(file_path, content)
    
    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False
    ) -> EditResult:
        """Edit file in appropriate backend."""
        backend = self._get_backend(file_path)
        return backend.edit(file_path, old_string, new_string, replace_all)
