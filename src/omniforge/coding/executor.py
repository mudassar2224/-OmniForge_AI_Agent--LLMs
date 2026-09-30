"""Sandboxed Python code execution."""

import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DENIED_IMPORTS = ["shutil.rmtree", "os.system", "subprocess.call", "eval(", "exec("]
MAX_EXECUTION_TIME = 30  # seconds
MAX_OUTPUT_LENGTH = 10000  # characters


class ExecutionResult(BaseModel):
    """Result of sandboxed code execution."""

    success: bool = Field(description="Whether the code executed successfully with exit code 0")
    output: str = Field(default="", description="Captured standard output")
    error: str = Field(default="", description="Captured standard error or exception description")
    return_code: int = Field(default=0, description="Process return code or -1 on error/timeout")


async def execute_python(
    code: str,
    workspace_path: str = "workspace",
    timeout: int = MAX_EXECUTION_TIME,
) -> dict[str, Any]:
    """Execute Python code in an isolated subprocess with safety limits.

    Args:
        code: Python source code string to execute.
        workspace_path: Working directory path where code will run.
        timeout: Maximum duration in seconds before killing the process.

    Returns:
        Dictionary containing success, output, error, and return_code.
    """
    # Basic safety check
    for denied in DENIED_IMPORTS:
        if denied in code:
            logger.warning("Execution blocked due to denied pattern: %s", denied)
            return ExecutionResult(
                success=False,
                output="",
                error=f"Blocked: {denied} is not allowed",
                return_code=-1,
            ).model_dump()

    workspace = Path(workspace_path).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    # Write code to unique temporary file in workspace to support concurrent executions
    exec_id = uuid.uuid4().hex[:8]
    script_path = workspace / f"_omniforge_exec_{exec_id}.py"
    script_path.write_text(code, encoding="utf-8")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace),
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
            },
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_LENGTH]
            error = stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_LENGTH]
            return ExecutionResult(
                success=proc.returncode == 0,
                output=output,
                error=error,
                return_code=proc.returncode if proc.returncode is not None else -1,
            ).model_dump()
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception as kill_err:
                logger.debug("Error killing process after timeout: %s", kill_err)
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution timed out after {timeout}s",
                return_code=-1,
            ).model_dump()
    except Exception as e:
        logger.exception("Failed to execute Python subprocess: %s", e)
        return ExecutionResult(
            success=False,
            output="",
            error=str(e),
            return_code=-1,
        ).model_dump()
    finally:
        if script_path.exists():
            try:
                script_path.unlink()
            except OSError as rm_err:
                logger.debug("Failed to remove temp script %s: %s", script_path, rm_err)
