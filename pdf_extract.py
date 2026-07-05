"""
VeriPath Regulatory Certificate Vault — Stage 2
Local PDF text extraction using pypdf, BEFORE any Claude API call.
This keeps API costs down: only extracted text (a few KB) goes to
Claude, never the raw PDF bytes.
"""
import io
from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> dict:
    """
    Extracts raw text from an uploaded PDF's bytes.

    Args:
        file_bytes: raw bytes from st.file_uploader (call .read() or .getvalue())

    Returns:
        {
            "success": bool,
            "text": str,          # full extracted text, all pages joined
            "page_count": int,
            "error": str | None
        }
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        page_count = len(reader.pages)

        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            text_parts.append(page_text)

        full_text = "\n\n".join(text_parts).strip()

        if not full_text:
            return {
                "success": False,
                "text": "",
                "page_count": page_count,
                "error": "No extractable text found — this PDF may be a scanned image. "
                         "OCR is not yet supported; ask the uploader for a text-based PDF."
            }

        return {
            "success": True,
            "text": full_text,
            "page_count": page_count,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "page_count": 0,
            "error": f"Could not read PDF: {str(e)}"
        }


def truncate_for_api(text: str, max_chars: int = 12000) -> str:
    """
    Certificates are short (1-3 pages), but this is a safety cap so a
    mis-uploaded large document doesn't blow up the Claude API call cost.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...truncated for length...]"
