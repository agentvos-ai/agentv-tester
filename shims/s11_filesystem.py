import logging
import os
import shutil
import stat
from typing import Any

from core.errors import ShimError
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


def rmtree_errorhandler(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.
    If the error is due to a read-only file, it attempts to change the mode and retry.
    """
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


@register_shim("filesystem")
class FilesystemShim(BaseShim):
    """
    Industrial-grade filesystem interface.
    Uses local disk storage within a sandboxed workspace.
    """

    def __init__(self, seed: int = 42):
        self.workspace_root = os.path.abspath(".agent_workspace/fs")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "Interface for managing local and networked file storage."

    def setup(self) -> None:
        """Ensure workspace directory exists."""
        if not os.path.exists(self.workspace_root):
            os.makedirs(self.workspace_root)

    def shutdown(self) -> None:
        """Cleanup the workspace."""
        if os.path.exists(self.workspace_root):
            try:
                shutil.rmtree(self.workspace_root, onerror=rmtree_errorhandler)
            except Exception as e:
                logger.warning(f"Failed to fully cleanup Filesystem workspace: {e!s}")

    def reset(self) -> None:
        """Deterministic reset of the filesystem."""
        self.shutdown()
        self.setup()

        # Seed some default files
        self.write_file("logs/system.log", "System initialized.\n")
        self.write_file("config/app.yaml", "mode: production\n")

    def list_files(self, path: str = ".") -> list[str]:
        """Lists files in the specified directory."""
        full_path = os.path.join(self.workspace_root, path)
        if not os.path.exists(full_path):
            raise ShimError(f"Path '{path}' not found.")

        try:
            return os.listdir(full_path)
        except Exception as e:
            raise ShimError(f"Failed to list files in '{path}': {e!s}")

    def read_file(self, path: str) -> str:
        """Reads the content of a file."""
        full_path = os.path.join(self.workspace_root, path)
        if not os.path.exists(full_path):
            raise ShimError(f"File '{path}' not found.")

        try:
            with open(full_path, "r") as f:
                return f.read()
        except Exception as e:
            raise ShimError(f"Failed to read file '{path}': {e!s}")

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a file, creating directories if needed."""
        full_path = os.path.join(self.workspace_root, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        try:
            with open(full_path, "w") as f:
                f.write(content)
            return f"Successfully wrote to '{path}'."
        except Exception as e:
            raise ShimError(f"Failed to write file '{path}': {e!s}")

    def delete_file(self, path: str) -> str:
        """Deletes a file or directory."""
        full_path = os.path.join(self.workspace_root, path)
        if not os.path.exists(full_path):
            raise ShimError(f"Path '{path}' not found.")

        try:
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
            return f"Successfully deleted '{path}'."
        except Exception as e:
            raise ShimError(f"Failed to delete '{path}': {e!s}")

    def list_dir(self, path: str = ".") -> list[str]:
        """Alias for list_files to maintain compatibility."""
        return self.list_files(path)

    def move(self, src: str, dst: str) -> str:
        """Moves a file or directory."""
        full_src = os.path.join(self.workspace_root, src)
        full_dst = os.path.join(self.workspace_root, dst)
        try:
            shutil.move(full_src, full_dst)
            return f"Moved '{src}' to '{dst}'."
        except Exception as e:
            raise ShimError(f"Failed to move '{src}' to '{dst}': {e!s}")

    def delete(self, path: str) -> str:
        """Alias for delete_file to maintain compatibility."""
        return self.delete_file(path)

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            ("fs_list", self.list_files, "List files in a directory."),
            ("fs_list_dir", self.list_dir, "List contents of a directory."),
            ("fs_read", self.read_file, "Read content from a file."),
            ("fs_write", self.write_file, "Write content to a file."),
            ("fs_move", self.move, "Move or rename a file/directory."),
            ("fs_delete", self.delete, "Delete a file or directory."),
        ]
