import re
import io
import tempfile
import urllib.request
import ssl
from pathlib import Path
from typing import List, Dict, Union
from pypdf import PdfReader
from bs4 import BeautifulSoup
from backend.app.core.logger import logger
from backend.app.core.gemini import gemini_client

class DocumentExtractor:
    """
    Universal multi-format document parser.
    Supports PDF (with layout mode and Gemini Vision fallback),
    DOCX, PPTX, XLSX, CSV, TXT, MD, and live Website URLs.
    """
    @staticmethod
    def extract_from_file(file_path: Union[str, Path]) -> List[Dict[str, Union[int, str]]]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found at: {file_path}")

        logger.info(f"Extracting text from file: {path.name} (type: {path.suffix})")
        with open(path, "rb") as f:
            return DocumentExtractor.extract_from_bytes(f.read(), source_name=path.name, temp_file_path=str(path))

    @staticmethod
    def extract_from_bytes(
        file_bytes: bytes,
        source_name: str = "uploaded_document.pdf",
        temp_file_path: Union[str, None] = None
    ) -> List[Dict[str, Union[int, str]]]:
        ext = Path(source_name).suffix.lower()

        if ext == ".docx":
            return DocumentExtractor._extract_docx(file_bytes, source_name)
        elif ext == ".pptx":
            return DocumentExtractor._extract_pptx(file_bytes, source_name)
        elif ext in [".xlsx", ".csv"]:
            return DocumentExtractor._extract_spreadsheet(file_bytes, source_name, ext)
        elif ext in [".txt", ".md"]:
            return DocumentExtractor._extract_plain_text(file_bytes, source_name, ext)
        else:
            # Default to PDF extraction
            return DocumentExtractor._extract_pdf(file_bytes, source_name, temp_file_path)

    @staticmethod
    def extract_from_url(url: str) -> List[Dict[str, Union[int, str]]]:
        """
        Scrapes a live webpage, strips scripts and styles, and extracts readable article text.
        """
        logger.info(f"Scraping live website URL: {url}")
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) InsightForge/1.0"}
        )
        ssl_ctx = ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as response:
                html = response.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            raise ValueError(f"Could not connect to URL '{url}': {str(e)}")

        soup = BeautifulSoup(html, "html.parser")

        # Strip unneeded elements
        for element in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
            element.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else url
        body_text = soup.get_text(separator="\n")
        
        # Clean blank lines
        clean_lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        full_text = f"# {title}\nSource: {url}\n\n" + "\n".join(clean_lines)

        # Chunk into virtual pages of ~400 words
        words = full_text.split()
        page_size = 400
        pages: List[Dict[str, Union[int, str]]] = []
        for idx in range(0, max(1, len(words)), page_size):
            page_words = words[idx:idx + page_size]
            if page_words:
                pages.append({
                    "page": (idx // page_size) + 1,
                    "text": " ".join(page_words)
                })

        logger.info(f"URL '{url}' parsed into {len(pages)} sections ({len(words)} words).")
        return pages

    @staticmethod
    def _extract_docx(docx_bytes: bytes, source_name: str) -> List[Dict[str, Union[int, str]]]:
        try:
            import docx
            doc = docx.Document(io.BytesIO(docx_bytes))
            full_text = []
            for p in doc.paragraphs:
                if p.text.strip():
                    full_text.append(p.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                    if row_text:
                        full_text.append(f"| {row_text} |")

            words = "\n\n".join(full_text).split()
            page_size = 400
            pages: List[Dict[str, Union[int, str]]] = []
            for idx in range(0, max(1, len(words)), page_size):
                page_words = words[idx:idx + page_size]
                if page_words:
                    pages.append({
                        "page": (idx // page_size) + 1,
                        "text": " ".join(page_words)
                    })
            if not pages:
                pages = [{"page": 1, "text": "Empty DOCX document."}]
            logger.info(f"DOCX {source_name} parsed into {len(pages)} sections.")
            return pages
        except Exception as e:
            logger.error(f"Failed to parse DOCX {source_name}: {e}")
            raise ValueError(f"Corrupt or unreadable DOCX: {e}")

    @staticmethod
    def _extract_pptx(pptx_bytes: bytes, source_name: str) -> List[Dict[str, Union[int, str]]]:
        try:
            import pptx
            prs = pptx.Presentation(io.BytesIO(pptx_bytes))
            pages: List[Dict[str, Union[int, str]]] = []
            for idx, slide in enumerate(prs.slides, start=1):
                slide_text = []
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for paragraph in shape.text_frame.paragraphs:
                            t = paragraph.text.strip()
                            if t:
                                slide_text.append(t)
                    if shape.has_table:
                        for row in shape.table.rows:
                            row_vals = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                            if row_vals:
                                slide_text.append(" | ".join(row_vals))
                
                content = f"[Slide {idx}]\n" + "\n".join(slide_text) if slide_text else f"[Slide {idx}] (No text)"
                pages.append({
                    "page": idx,
                    "text": content
                })
            logger.info(f"PPTX {source_name} parsed into {len(pages)} slides.")
            return pages
        except Exception as e:
            logger.error(f"Failed to parse PPTX {source_name}: {e}")
            raise ValueError(f"Corrupt or unreadable PPTX: {e}")

    @staticmethod
    def _extract_spreadsheet(data_bytes: bytes, source_name: str, ext: str) -> List[Dict[str, Union[int, str]]]:
        try:
            import pandas as pd
            if ext == ".csv":
                df = pd.read_csv(io.BytesIO(data_bytes), on_bad_lines="skip")
                sheet_dict = {"Data": df}
            else:
                sheet_dict = pd.read_excel(io.BytesIO(data_bytes), sheet_name=None)

            pages: List[Dict[str, Union[int, str]]] = []
            page_counter = 1

            for sheet_name, df in sheet_dict.items():
                if df.empty:
                    continue
                # 1. Summary of Sheet (Shape, Columns, Numeric stats)
                summary_lines = [
                    f"### Spreadsheet Sheet: {sheet_name}",
                    f"- Total Rows: {len(df)}",
                    f"- Total Columns: {len(df.columns)}",
                    f"- Column Headers: {', '.join([str(c) for c in df.columns])}"
                ]

                # Statistical summary for numeric columns
                numeric_cols = df.select_dtypes(include=["number"]).columns
                if len(numeric_cols) > 0:
                    summary_lines.append("\n**Statistical Summary (Numeric Metrics):**")
                    for col in numeric_cols[:6]:
                        col_series = df[col].dropna()
                        if not col_series.empty:
                            summary_lines.append(
                                f"- Column '{col}': Total={col_series.sum():.2f}, Mean={col_series.mean():.2f}, "
                                f"Min={col_series.min():.2f}, Max={col_series.max():.2f}"
                            )

                # Add sample markdown table of top rows
                summary_lines.append("\n**Sample Records:**")
                summary_lines.append(df.head(10).to_markdown(index=False))

                pages.append({
                    "page": page_counter,
                    "text": "\n".join(summary_lines)
                })
                page_counter += 1

                # If large, chunk remaining rows in batches of 50
                if len(df) > 10:
                    for chunk_idx in range(10, min(200, len(df)), 40):
                        batch = df.iloc[chunk_idx:chunk_idx + 40]
                        pages.append({
                            "page": page_counter,
                            "text": f"### {sheet_name} (Rows {chunk_idx + 1} to {chunk_idx + len(batch)}):\n" + batch.to_markdown(index=False)
                        })
                        page_counter += 1

            if not pages:
                pages = [{"page": 1, "text": "Empty spreadsheet."}]

            logger.info(f"Spreadsheet {source_name} parsed into {len(pages)} sections.")
            return pages
        except Exception as e:
            logger.error(f"Failed to parse spreadsheet {source_name}: {e}")
            raise ValueError(f"Corrupt or unreadable spreadsheet: {e}")

    @staticmethod
    def _extract_plain_text(text_bytes: bytes, source_name: str, ext: str) -> List[Dict[str, Union[int, str]]]:
        try:
            raw = text_bytes.decode("utf-8", errors="replace")
        except Exception:
            raw = text_bytes.decode("latin-1", errors="replace")

        words = raw.split()
        page_size = 400
        pages: List[Dict[str, Union[int, str]]] = []
        for idx in range(0, max(1, len(words)), page_size):
            page_words = words[idx:idx + page_size]
            if page_words:
                pages.append({
                    "page": (idx // page_size) + 1,
                    "text": " ".join(page_words)
                })
        if not pages:
            pages = [{"page": 1, "text": "Empty document."}]
        logger.info(f"Plain text {source_name} parsed into {len(pages)} sections.")
        return pages

    @staticmethod
    def _extract_pdf(
        pdf_bytes: bytes,
        source_name: str,
        temp_file_path: Union[str, None]
    ) -> List[Dict[str, Union[int, str]]]:
        stream = io.BytesIO(pdf_bytes)
        try:
            reader = PdfReader(stream)
        except Exception as e:
            logger.error(f"Failed to parse PDF stream for {source_name}: {e}")
            raise ValueError(f"Corrupt or unreadable PDF: {e}")

        pages: List[Dict[str, Union[int, str]]] = []
        total_pages = len(reader.pages)
        logger.info(f"PDF {source_name} has {total_pages} pages.")

        for idx, page in enumerate(reader.pages, start=1):
            try:
                try:
                    raw_text = page.extract_text(extraction_mode="layout") or ""
                except Exception:
                    raw_text = page.extract_text() or ""

                if not raw_text.strip():
                    raw_text = page.extract_text() or ""

                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
                single_lines = sum(1 for l in lines if len(l) <= 1)
                if len(lines) > 10 and (single_lines / len(lines)) > 0.4:
                    try:
                        raw_text = page.extract_text(extraction_mode="layout")
                    except Exception:
                        pass

                clean_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw_text)
                clean_text = re.sub(r"\r\n|\r", "\n", clean_text)
                clean_text = re.sub(r"[ \t]+", " ", clean_text)
                clean_text = re.sub(r"\n\s*\n+", "\n\n", clean_text).strip()

                if clean_text:
                    pages.append({
                        "page": idx,
                        "text": clean_text
                    })
                else:
                    logger.warning(f"Page {idx} of {source_name} contained no direct text.")
            except Exception as page_err:
                logger.warning(f"Error extracting page {idx} in {source_name}: {page_err}")

        # Smart Multimodal Fallback for scanned PDFs
        total_word_count = sum(len(str(p["text"]).split()) for p in pages)
        if total_word_count < 15:
            logger.info(f"PDF '{source_name}' has sparse or zero text ({total_word_count} words). Triggering Gemini Multimodal Document Vision fallback...")
            try:
                if temp_file_path and Path(temp_file_path).exists():
                    ocr_text = gemini_client.extract_document_multimodal(temp_file_path)
                else:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(pdf_bytes)
                        tmp_path = tmp.name
                    try:
                        ocr_text = gemini_client.extract_document_multimodal(tmp_path)
                    finally:
                        try:
                            Path(tmp_path).unlink()
                        except Exception:
                            pass

                if ocr_text:
                    logger.info(f"Gemini Multimodal Vision successfully transcribed '{source_name}' ({len(ocr_text.split())} words).")
                    pages = [{
                        "page": 1,
                        "text": ocr_text
                    }]
            except Exception as ocr_err:
                logger.warning(f"Multimodal OCR fallback could not process {source_name}: {ocr_err}")

        return pages

PDFExtractor = DocumentExtractor
