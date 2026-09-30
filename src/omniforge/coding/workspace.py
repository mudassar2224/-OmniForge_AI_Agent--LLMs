"""Workspace management for isolated code execution."""

import logging
import shutil
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FileInfo(BaseModel):
    """Metadata describing a file or directory in the workspace."""

    name: str = Field(description="Name of the file or directory")
    path: str = Field(description="Relative path from workspace root")
    is_dir: bool = Field(description="Whether the item is a directory")
    size: int = Field(default=0, description="Size in bytes for files, 0 for directories")


class Workspace:
    """Manages an isolated workspace for code execution and file manipulation."""

    def __init__(self, base_path: str | Path = "workspace") -> None:
        """Initialize the workspace directory.

        Args:
            base_path: Root path of the workspace directory.
        """
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.debug("Workspace initialized at: %s", self.base_path)

    def _resolve_safe_path(self, filepath: str | Path) -> Path:
        """Resolve a relative filepath safely within the workspace.

        Args:
            filepath: Target path inside the workspace.

        Returns:
            Resolved absolute Path.

        Raises:
            ValueError: If path traversal outside workspace is detected.
        """
        target = (self.base_path / filepath).resolve()
        if not target.is_relative_to(self.base_path):
            raise ValueError(f"Access denied: path traversal detected for '{filepath}'")
        return target

    def list_files(self, subdir: str = "") -> list[dict[str, Any]]:
        """List files and directories in the workspace or a subdirectory.

        Args:
            subdir: Relative subdirectory to list.

        Returns:
            List of dictionaries containing name, path, is_dir, and size.
        """
        target = self._resolve_safe_path(subdir)
        if not target.exists() or not target.is_dir():
            return []

        files: list[dict[str, Any]] = []
        for item in sorted(target.iterdir()):
            info = FileInfo(
                name=item.name,
                path=str(item.relative_to(self.base_path)),
                is_dir=item.is_dir(),
                size=item.stat().st_size if item.is_file() else 0,
            )
            files.append(info.model_dump())
        return files

    def read_file(self, filepath: str) -> str:
        """Read text content from a file in the workspace.

        Args:
            filepath: Relative path to the file.

        Returns:
            Text content of the file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If path traversal is detected.
            IsADirectoryError: If the target path points to a directory.
        """
        target = self._resolve_safe_path(filepath)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        if target.is_dir():
            raise IsADirectoryError(f"Target is a directory, not a file: {filepath}")
        return target.read_text(encoding="utf-8")

    def write_file(self, filepath: str, content: str) -> str:
        """Write text content to a file in the workspace.

        Args:
            filepath: Relative path where the file should be created/updated.
            content: String content to write.

        Returns:
            Absolute path string to the written file.

        Raises:
            ValueError: If path traversal is detected.
        """
        target = self._resolve_safe_path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info("Written file: %s", filepath)
        return str(target)

    def delete_file(self, filepath: str) -> bool:
        """Delete a file or directory within the workspace.

        Args:
            filepath: Relative path to delete.

        Returns:
            True if deleted, False if target did not exist.

        Raises:
            ValueError: If path traversal is detected.
        """
        target = self._resolve_safe_path(filepath)
        if not target.exists():
            return False

        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        logger.info("Deleted: %s", filepath)
        return True

    def file_exists(self, filepath: str) -> bool:
        """Check if a file or directory exists in the workspace.

        Args:
            filepath: Relative path to verify.

        Returns:
            True if it exists, False otherwise.
        """
        try:
            target = self._resolve_safe_path(filepath)
            return target.exists()
        except ValueError:
            return False

    def clean_workspace(self) -> None:
        """Remove all files and directories inside the workspace."""
        for item in self.base_path.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        logger.info("Workspace cleaned: %s", self.base_path)
