"""MCP server exposing coding and execution tools."""
import asyncio
import json
import logging
import os
from pathlib import Path
import sys
import time

logger = logging.getLogger(__name__)


async def list_workspace(directory: str = ".", recursive: bool = False, max_items: int = 100) -> str:
    """List files and folders within a workspace directory.

    Args:
        directory: Target path relative to workspace or absolute.
        recursive: Whether to list nested directory contents.
        max_items: Maximum items to include in results.

    Returns:
        JSON string listing files and directories with sizes and timestamps.
    """
    try:
        target = Path(directory).resolve()
        if not target.exists():
            return json.dumps({"error": f"Directory not found: {directory}"})
        if not target.is_dir():
            return json.dumps({"error": f"Path is not a directory: {directory}"})

        entries: list[dict] = []
        if recursive:
            iterator = target.rglob("*")
        else:
            iterator = target.iterdir()

        for item in iterator:
            if len(entries) >= max_items:
                break
            try:
                stat = item.stat()
                rel_path = str(item.relative_to(target))
                entries.append(
                    {
                        "name": item.name,
                        "path": rel_path,
                        "is_dir": item.is_dir(),
                        "size_bytes": stat.st_size if item.is_file() else 0,
                        "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                    }
                )
            except (OSError, PermissionError) as pe:
                logger.debug("Skipping inaccessible file %s: %s", item, pe)

        return json.dumps({"directory": str(target), "count": len(entries), "items": entries}, indent=2)
    except Exception as e:
        logger.error("list_workspace failed: %s", e)
        return json.dumps({"error": str(e)})


async def read_file(path: str, start_line: int = 1, end_line: int | None = None, max_chars: int = 25000) -> str:
    """Read contents of a text file with optional line-range slicing.

    Args:
        path: Path to the target file.
        start_line: 1-indexed starting line number (inclusive).
        end_line: Optional 1-indexed ending line number (inclusive).
        max_chars: Maximum character limit for output.

    Returns:
        Content of the file as string, or error message.
    """
    try:
        file_path = Path(path).resolve()
        if not file_path.exists():
            return f"Error: File not found: {path}"
        if not file_path.is_file():
            return f"Error: Path is not a file: {path}"

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback for binary or alternative encodings
            content = file_path.read_text(encoding="latin-1")

        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        s_idx = max(0, start_line - 1)
        e_idx = end_line if (end_line is not None and end_line <= total_lines) else total_lines

        selected_lines = lines[s_idx:e_idx]
        output = "".join(selected_lines)

        if len(output) > max_chars:
            output = output[:max_chars] + f"\n\n... [Truncated: {len(output)} chars total, showing first {max_chars}]"

        return output
    except Exception as e:
        logger.error("read_file failed for %s: %s", path, e)
        return f"Error reading file '{path}': {e}"


async def write_file(path: str, content: str, overwrite: bool = True) -> str:
    """Write text content to a file, creating parent directories if needed.

    Args:
        path: Destination file path.
        content: Text content to write.
        overwrite: Whether to overwrite existing files.

    Returns:
        Confirmation message with file path and written character count.
    """
    try:
        file_path = Path(path).resolve()
        if file_path.exists() and not overwrite:
            return f"Error: File already exists and overwrite is set to False: {path}"

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        logger.error("write_file failed for %s: %s", path, e)
        return f"Error writing file '{path}': {e}"


async def run_python(code: str, timeout: int = 30, cwd: str | None = None) -> str:
    """Execute Python code in an isolated subprocess and return stdout, stderr, and exit code.

    Args:
        code: Python script content to execute.
        timeout: Maximum execution timeout in seconds.
        cwd: Optional working directory for script execution.

    Returns:
        JSON string containing exit_code, stdout, stderr, and execution duration.
    """
    start_time = time.time()
    work_dir = Path(cwd).resolve() if cwd else Path.cwd()

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(work_dir),
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )
            exit_code = proc.returncode
            duration = round(time.time() - start_time, 3)

            return json.dumps(
                {
                    "exit_code": exit_code,
                    "duration_seconds": duration,
                    "stdout": stdout_bytes.decode("utf-8", errors="replace"),
                    "stderr": stderr_bytes.decode("utf-8", errors="replace"),
                },
                indent=2,
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return json.dumps(
                {
                    "exit_code": -1,
                    "duration_seconds": round(time.time() - start_time, 3),
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout} seconds.",
                },
                indent=2,
            )
    except Exception as e:
        logger.error("run_python execution error: %s", e)
        return json.dumps(
            {
                "exit_code": -1,
                "duration_seconds": round(time.time() - start_time, 3),
                "stdout": "",
                "stderr": f"Failed to spawn Python process: {e}",
            },
            indent=2,
        )


try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("OmniForge Coding")
    mcp.tool()(list_workspace)
    mcp.tool()(read_file)
    mcp.tool()(write_file)
    mcp.tool()(run_python)

    if __name__ == "__main__":
        mcp.run()
except ImportError:
    mcp = None  # MCP library not installed or unavailable in current environment
