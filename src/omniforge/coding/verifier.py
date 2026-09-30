"""Code verification and quality analysis utilities."""

import ast
import logging
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SyntaxCheckResult(BaseModel):
    """Result of Python syntax verification."""

    valid: bool = Field(description="Whether the Python code has valid syntax")
    error: str | None = Field(default=None, description="Syntax error message if invalid")


class CodeQualityReport(BaseModel):
    """Report detailing code metrics and quality indicators."""

    lines: int = Field(description="Total line count")
    has_docstring: bool = Field(description="Whether docstrings are present")
    has_type_hints: bool = Field(description="Whether type annotations appear present")
    has_error_handling: bool = Field(description="Whether try/except blocks are present")
    syntax: dict[str, Any] = Field(description="Syntax validation result")
    function_count: int = Field(default=0, description="Number of function definitions")
    class_count: int = Field(default=0, description="Number of class definitions")


def verify_python_syntax(code: str) -> dict[str, Any]:
    """Check Python code for syntax errors.

    Args:
        code: Python source code string.

    Returns:
        Dictionary with 'valid' (bool) and 'error' (str or None).
    """
    try:
        ast.parse(code)
        return SyntaxCheckResult(valid=True, error=None).model_dump()
    except SyntaxError as e:
        error_msg = f"Line {e.lineno}: {e.msg}"
        logger.debug("Syntax error detected: %s", error_msg)
        return SyntaxCheckResult(valid=False, error=error_msg).model_dump()
    except Exception as e:
        logger.debug("Failed parsing code: %s", e)
        return SyntaxCheckResult(valid=False, error=str(e)).model_dump()


def analyze_code_quality(code: str) -> dict[str, Any]:
    """Perform static code quality analysis and structural checks.

    Args:
        code: Python source code string.

    Returns:
        Dictionary containing lines, has_docstring, has_type_hints,
        has_error_handling, syntax, and structural counts.
    """
    lines = code.strip().split("\n") if code.strip() else []
    has_docstring = '"""' in code or "'''" in code
    has_type_hints = ":" in code and "->" in code
    has_error_handling = "try:" in code or "except" in code

    syntax_res = verify_python_syntax(code)

    function_count = 0
    class_count = 0

    if syntax_res.get("valid"):
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    function_count += 1
                elif isinstance(node, ast.ClassDef):
                    class_count += 1
        except Exception:
            pass

    report = CodeQualityReport(
        lines=len(lines),
        has_docstring=has_docstring,
        has_type_hints=has_type_hints,
        has_error_handling=has_error_handling,
        syntax=syntax_res,
        function_count=function_count,
        class_count=class_count,
    )
    return report.model_dump()
