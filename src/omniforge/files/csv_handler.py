"""CSV file processing and analysis utilities using pandas."""

import logging
from pathlib import Path
from typing import Any
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CsvReadResult(BaseModel):
    """Result of reading and previewing a CSV file."""

    preview: list[dict[str, Any]] = Field(description="First few records of the CSV")
    columns: list[str] = Field(description="List of column names")
    shape: list[int] = Field(description="[row_count, column_count]")
    dtypes: dict[str, str] = Field(description="Mapping of column names to data types")
    total_rows: int = Field(description="Total number of rows in the CSV")


class CsvAnalysisResult(BaseModel):
    """Statistical and structural analysis of a CSV file."""

    shape: list[int] = Field(description="[rows, columns]")
    columns: list[str] = Field(description="List of column names")
    missing_values: dict[str, int] = Field(description="Count of missing values per column")
    missing_percentage: dict[str, float] = Field(description="Percentage of missing values per column")
    total_missing: int = Field(description="Total missing cells across the table")
    duplicate_rows: int = Field(description="Number of duplicate rows")
    numeric_columns: list[str] = Field(description="Names of numeric columns")
    categorical_columns: list[str] = Field(description="Names of non-numeric columns")
    statistics: dict[str, Any] = Field(description="Descriptive statistics summary")
    memory_usage_bytes: int = Field(description="Approximate memory footprint in bytes")


def _read_df_safe(file_path: Path, encoding: str | None = None) -> pd.DataFrame:
    """Read CSV with automatic encoding fallback if needed."""
    encodings_to_try = [encoding] if encoding else ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    last_err: Exception | None = None

    for enc in encodings_to_try:
        if enc is None:
            continue
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError as u_err:
            last_err = u_err
            continue
        except Exception:
            raise

    if last_err:
        raise last_err
    return pd.read_csv(file_path)


def read_csv_file(
    file_path: str | Path,
    nrows: int = 10,
    encoding: str | None = None,
) -> dict[str, Any]:
    """Read and preview a CSV file.

    Args:
        file_path: Path to the CSV file.
        nrows: Number of preview rows to include.
        encoding: Optional specific file encoding.

    Returns:
        Dictionary with preview, columns, shape, dtypes, and total_rows.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        df = _read_df_safe(path, encoding=encoding)
        total_rows = len(df)
        preview_df = df.head(nrows).copy()
        # Convert NaN to None for clean JSON serialization
        preview_records = preview_df.where(pd.notnull(preview_df), None).to_dict(orient="records")

        result = CsvReadResult(
            preview=preview_records,
            columns=[str(col) for col in df.columns],
            shape=[int(df.shape[0]), int(df.shape[1])],
            dtypes={str(col): str(dtype) for col, dtype in df.dtypes.items()},
            total_rows=total_rows,
        )
        return result.model_dump()
    except Exception as e:
        logger.error("Failed to read CSV %s: %s", file_path, e)
        return {"error": str(e)}


def analyze_csv(
    file_path: str | Path,
    encoding: str | None = None,
) -> dict[str, Any]:
    """Analyze a CSV file for summary statistics, missing values, and structure.

    Args:
        file_path: Path to the CSV file.
        encoding: Optional specific file encoding.

    Returns:
        Dictionary containing comprehensive data analysis metrics.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        df = _read_df_safe(path, encoding=encoding)
        missing_counts = {str(col): int(count) for col, count in df.isna().sum().items()}
        missing_pct = {
            str(col): round(float(pct * 100), 2) for col, pct in df.isna().mean().items()
        }
        total_missing = int(df.isna().sum().sum())
        duplicate_rows = int(df.duplicated().sum())

        numeric_cols = [str(col) for col in df.select_dtypes(include=["number"]).columns]
        categorical_cols = [str(col) for col in df.select_dtypes(exclude=["number"]).columns]

        # Descriptive statistics
        stats_df = df.describe()
        stats_clean = stats_df.where(pd.notnull(stats_df), None).to_dict()

        analysis = CsvAnalysisResult(
            shape=[int(df.shape[0]), int(df.shape[1])],
            columns=[str(col) for col in df.columns],
            missing_values=missing_counts,
            missing_percentage=missing_pct,
            total_missing=total_missing,
            duplicate_rows=duplicate_rows,
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            statistics=stats_clean,
            memory_usage_bytes=int(df.memory_usage(deep=True).sum()),
        )
        return analysis.model_dump()
    except Exception as e:
        logger.error("Failed to analyze CSV %s: %s", file_path, e)
        return {"error": str(e)}
