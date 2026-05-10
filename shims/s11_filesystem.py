import logging

logger = logging.getLogger(__name__)

import os
import shutil
from pathlib import Path
from typing import List, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim


@register_shim("filesystem")
class FilesystemShim(BaseShim):
    """
    Secure enterprise filesystem simulator.
    Jailed to a local scratch directory for safety.
    """

    def __init__(self, seed: int = 42):
        self.base_path: Path = Path("scratch/fs_shim").resolve()
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "Secure enterprise filesystem for managing files and directories."

    def reset(self) -> None:
        """Deterministic reset of the filesystem state."""
        if self.base_path.exists():
            shutil.rmtree(self.base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.write_file("README.txt", "Enterprise Filesystem Root")

    def _get_safe_path(self, path: str) -> Path:
        target = (self.base_path / path).resolve()
        if not str(target).startswith(str(self.base_path)):
            raise ShimError(f"Path traversal attempt: {path}")
        return target

    def read_file(self, path: str) -> str:
        """Reads the content of a file."""
        target = self._get_safe_path(path)
        if not target.exists():
            raise ShimError(f"File not found: {path}")
        with open(target, "r") as f:
            return f.read()

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a file."""
        target = self._get_safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w") as f:
            f.write(content)
        return f"File '{path}' written successfully."

    def list_dir(self, path: str = ".") -> List[str]:
        """Lists contents of a directory."""
        target = self._get_safe_path(path)
        if not target.exists():
            raise ShimError(f"Directory not found: {path}")
        return os.listdir(target)

    def move(self, src: str, dst: str) -> str:
        """Moves a file or directory."""
        src_path = self._get_safe_path(src)
        dst_path = self._get_safe_path(dst)
        if not src_path.exists():
            raise ShimError(f"Source not found: {src}")
        shutil.move(str(src_path), str(dst_path))
        return f"Moved '{src}' to '{dst}'."

    def delete(self, path: str) -> str:
        """Deletes a file or directory."""
        target = self._get_safe_path(path)
        if not target.exists():
            raise ShimError(f"Target not found: {path}")
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return f"Deleted '{path}'."

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("fs_read", self.read_file, "Read the content of a file."),
            ("fs_write", self.write_file, "Write content to a file."),
            ("fs_list", self.list_dir, "List the contents of a directory."),
            ("fs_move", self.move, "Move a file or directory."),
            ("fs_delete", self.delete, "Delete a file or directory."),
        ]
