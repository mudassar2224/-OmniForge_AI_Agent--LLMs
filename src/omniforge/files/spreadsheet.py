"""Spreadsheet (Excel / XLSX) processing and analysis using openpyxl and pandas."""

import logging
from pathlib import Path
from typing import Any
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SpreadsheetReadResult(BaseModel):
    """Result of reading and previewing an Excel spreadsheet."""

    sheet_names: list[str] = Field(description="Names of all sheets in workbook")
    active_sheet: str = Field(description="Name of the sheet being inspected")
    preview: list[dict[str, Any]] = Field(description="First few records of the sheet")
    columns: list[str] = Field(description="List of column names")
    shape: list[int] = Field(description="[row_count, column_count]")
    dtypes: dict[str, str] = Field(description="Mapping of column names to data types")
    total_rows: int = Field(description="Total number of rows in the sheet")


class SpreadsheetAnalysisResult(BaseModel):
    """Statistical and structural analysis of a spreadsheet sheet."""

    sheet_names: list[str] = Field(description="Names of all sheets in workbook")
    active_sheet: str = Field(description="Name of the sheet analyzed")
    shape: list[int] = Field(description="[rows, columns]")
    columns: list[str] = Field(description="List of column names")
    missing_values: dict[str, int] = Field(description="Count of missing values per column")
    missing_percentage: dict[str, float] = Field(description="Percentage of missing values per column")
    total_missing: int = Field(description="Total missing cells across the sheet")
    duplicate_rows: int = Field(description="Number of duplicate rows")
    numeric_columns: list[str] = Field(description="Names of numeric columns")
    categorical_columns: list[str] = Field(description="Names of non-numeric columns")
    statistics: dict[str, Any] = Field(description="Descriptive statistics summary")
    memory_usage_bytes: int = Field(description="Approximate memory footprint in bytes")


def get_sheet_names(file_path: str | Path) -> list[str]:
    """Retrieve sheet names from an Excel workbook without loading entire data.

    Args:
        file_path: Path to the Excel file (.xlsx, .xls).

    Returns:
        List of sheet names.
    """
    path = Path(file_path)
    if not path.exists():
        return []

    try:
        import openpyxl

        wb = openpyxl.load_workbook(filename=str(path), read_only=True, keep_links=False)
        names = list(wb.sheetnames)
        wb.close()
        return names
    except Exception as e:
        logger.debug("openpyxl fast sheet name inspection failed: %s, falling back to pd.ExcelFile", e)
        try:
            excel_file = pd.ExcelFile(str(path))
            return excel_file.sheet_names
        except Exception as e2:
            logger.error("Failed to retrieve sheet names for %s: %s", file_path, e2)
            return []


def read_spreadsheet(
    file_path: str | Path,
    sheet_name: str | int | None = 0,
    nrows: int = 10,
) -> dict[str, Any]:
    """Read and preview an Excel spreadsheet.

    Args:
        file_path: Path to the Excel spreadsheet (.xlsx, .xls).
        sheet_name: Target sheet name or index (default is 0 for first sheet).
        nrows: Number of preview rows to return.

    Returns:
        Dictionary with sheet_names, active_sheet, preview, columns, shape, and dtypes.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        all_sheets = get_sheet_names(path)
        actual_sheet_name = str(sheet_name)
        if isinstance(sheet_name, int) and all_sheets and 0 <= sheet_name < len(all_sheets):
            actual_sheet_name = all_sheets[sheet_name]

        df = pd.read_excel(str(path), sheet_name=sheet_name, engine="openpyxl")
        total_rows = len(df)
        preview_df = df.head(nrows).copy()
        # Clean NaNs for JSON serialization
        preview_records = preview_df.where(pd.notnull(preview_df), None).to_dict(orient="records")

        result = SpreadsheetReadResult(
            sheet_names=all_sheets,
            active_sheet=actual_sheet_name,
            preview=preview_records,
            columns=[str(col) for col in df.columns],
            shape=[int(df.shape[0]), int(df.shape[1])],
            dtypes={str(col): str(dtype) for col, dtype in df.dtypes.items()},
            total_rows=total_rows,
        )
        return result.model_dump()
    except Exception as e:
        logger.error("Failed to read spreadsheet %s: %s", file_path, e)
        return {"error": str(e)}


def analyze_spreadsheet(
    file_path: str | Path,
    sheet_name: str | int | None = 0,
) -> dict[str, Any]:
    """Analyze an Excel spreadsheet sheet for statistics, missing values, and structure.

    Args:
        file_path: Path to the Excel spreadsheet (.xlsx, .xls).
        sheet_name: Target sheet name or index.

    Returns:
        Dictionary containing structural and statistical metrics.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        all_sheets = get_sheet_names(path)
        actual_sheet_name = str(sheet_name)
        if isinstance(sheet_name, int) and all_sheets and 0 <= sheet_name < len(all_sheets):
            actual_sheet_name = all_sheets[sheet_name]

        df = pd.read_excel(str(path), sheet_name=sheet_name, engine="openpyxl")

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

        analysis = SpreadsheetAnalysisResult(
            sheet_names=all_sheets,
            active_sheet=actual_sheet_name,
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
        logger.error("Failed to analyze spreadsheet %s: %s", file_path, e)
        return {"error": str(e)}
