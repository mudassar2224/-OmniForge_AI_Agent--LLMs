"""OmniForge file processing and analysis modules."""

from omniforge.files.pdf import extract_pdf_text, get_pdf_metadata, PdfMetadata
from omniforge.files.docx import extract_docx_text, get_docx_metadata, DocxMetadata
from omniforge.files.csv_handler import (
    read_csv_file,
    analyze_csv,
    CsvReadResult,
    CsvAnalysisResult,
)
from omniforge.files.spreadsheet import (
    read_spreadsheet,
    analyze_spreadsheet,
    get_sheet_names,
    SpreadsheetReadResult,
    SpreadsheetAnalysisResult,
)
from omniforge.files.multimodal import (
    get_file_type,
    process_file,
    ProcessedFileResult,
)

__all__ = [
    "extract_pdf_text",
    "get_pdf_metadata",
    "PdfMetadata",
    "extract_docx_text",
    "get_docx_metadata",
    "DocxMetadata",
    "read_csv_file",
    "analyze_csv",
    "CsvReadResult",
    "CsvAnalysisResult",
    "read_spreadsheet",
    "analyze_spreadsheet",
    "get_sheet_names",
    "SpreadsheetReadResult",
    "SpreadsheetAnalysisResult",
    "get_file_type",
    "process_file",
    "ProcessedFileResult",
]
