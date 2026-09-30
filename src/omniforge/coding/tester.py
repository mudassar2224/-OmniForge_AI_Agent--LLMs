"""Test runner module for executing pytest in the workspace."""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MAX_OUTPUT_LENGTH = 10000
MAX_ERROR_LENGTH = 5000


class TestResult(BaseModel):
    """Result of test execution."""

    success: bool = Field(description="Whether all tests passed (return code 0)")
    output: str = Field(default="", description="Captured test stdout")
    error: str = Field(default="", description="Captured test stderr or failure message")
    return_code: int = Field(default=0, description="pytest exit code or -1 on error/timeout")


async def run_tests(
    workspace_path: str = "workspace",
    test_file: str | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Run pytest in the workspace or on a specific test file.

    Args:
        workspace_path: Working directory path where tests reside.
        test_file: Optional relative path to a specific test file.
        timeout: Maximum duration in seconds before timing out.

    Returns:
        Dictionary containing success, output, error, and return_code.
    """
    workspace = Path(workspace_path).resolve()
    if not workspace.exists():
        return TestResult(
            success=False,
            output="",
            error=f"Workspace path does not exist: {workspace_path}",
            return_code=-1,
        ).model_dump()

    args = [sys.executable, "-m", "pytest", "-v", "--tb=short"]
    if test_file:
        target_test = (workspace / test_file).resolve()
        if not target_test.exists():
            return TestResult(
                success=False,
                output="",
                error=f"Test file not found: {test_file}",
                return_code=-1,
            ).model_dump()
        args.append(str(target_test))
    else:
        args.append(str(workspace))

    logger.info("Running tests: %s in %s", " ".join(args), workspace)

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
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
            error = stderr.decode("utf-8", errors="replace")[:MAX_ERROR_LENGTH]
            return TestResult(
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
                logger.debug("Error killing test runner after timeout: %s", kill_err)
            return TestResult(
                success=False,
                output="",
                error=f"Tests timed out after {timeout}s",
                return_code=-1,
            ).model_dump()
    except Exception as e:
        logger.exception("Failed to run tests: %s", e)
        return TestResult(
            success=False,
            output="",
            error=str(e),
            return_code=-1,
        ).model_dump()
