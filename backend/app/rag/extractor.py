import io
import ipaddress
import json
import re
import socket
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Union

from bs4 import BeautifulSoup
from pypdf import PdfReader

from backend.app.core.config import settings
from backend.app.core.gemini import gemini_client
from backend.app.core.logger import logger

IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def _paginate_preserving_structure(full_text: str, page_word_limit: int = 400) -> List[Dict[str, Union[int, str]]]:
    """
    Splits text into virtual pages of roughly `page_word_limit` words while
    preserving paragraph (`\\n\\n`) and line (`\\n`) boundaries cleanly.
    """
    normalized = re.sub(r"\r\n|\r", "\n", full_text or "").strip()
    if not normalized:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", normalized) if p.strip()]
    pages: List[Dict[str, Union[int, str]]] = []
    current_parts: List[str] = []
    current_words = 0

    for para in paragraphs:
        p_words = len(para.split())
        if p_words > page_word_limit:
            if current_parts:
                pages.append({"page": len(pages) + 1, "text": "\n\n".join(current_parts)})
                current_parts = []
                current_words = 0
            lines = [ln.strip() for ln in para.split("\n") if ln.strip()]
            buf: List[str] = []
            buf_words = 0
            for ln in lines:
                lw = len(ln.split())
                if buf and buf_words + lw > page_word_limit:
                    pages.append({"page": len(pages) + 1, "text": "\n".join(buf)})
                    buf = []
                    buf_words = 0
                if lw > page_word_limit:
                    words = ln.split()
                    for idx in range(0, len(words), page_word_limit):
                        pages.append({"page": len(pages) + 1, "text": " ".join(words[idx:idx + page_word_limit])})
                else:
                    buf.append(ln)
                    buf_words += lw
            if buf:
                pages.append({"page": len(pages) + 1, "text": "\n".join(buf)})
            continue

        if current_parts and current_words + p_words > page_word_limit:
            pages.append({"page": len(pages) + 1, "text": "\n\n".join(current_parts)})
            current_parts = [para]
            current_words = p_words
        else:
            current_parts.append(para)
            current_words += p_words

    if current_parts:
        pages.append({"page": len(pages) + 1, "text": "\n\n".join(current_parts)})

    return pages


def _decode_text_bytes(raw_bytes: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def _validate_safe_url(url: str) -> None:
    """
    Validates URL scheme and blocks loopback, private, link-local,
    multicast, and reserved IP targets to prevent SSRF.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Invalid URL. Only public http:// and https:// URLs are allowed.")

    hostname = parsed.hostname.strip().lower()
    if hostname in ("localhost", "localhost.localdomain") or hostname.endswith((".local", ".internal")):
        raise ValueError("Access to local/internal hostnames is blocked for security.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ValueError(f"Could not resolve hostname '{hostname}': {e}")

    if not addr_info:
        raise ValueError(f"Could not resolve IP address for '{hostname}'.")

    for _, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0].split("%")[0]
        ip_obj = ipaddress.ip_address(ip_str)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
            or not ip_obj.is_global
        ):
            raise ValueError(f"Target IP '{ip_str}' is in a restricted network range and cannot be accessed.")


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class DocumentExtractor:
    """
    Universal multi-format document parser supporting:
    PDF (with Gemini Vision OCR fallback), DOCX, PPTX, XLSX, CSV, TSV,
    TXT, MD, JSON, HTML/HTM, XML, RTF, YAML/YML, PNG, JPG/JPEG, WebP, and public URLs.
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
        elif ext in {".xlsx", ".csv", ".tsv"}:
            return DocumentExtractor._extract_spreadsheet(file_bytes, source_name, ext)
        elif ext == ".json":
            return DocumentExtractor._extract_json(file_bytes, source_name)
        elif ext in {".html", ".htm"}:
            return DocumentExtractor._extract_html(file_bytes, source_name)
        elif ext == ".xml":
            return DocumentExtractor._extract_xml(file_bytes, source_name)
        elif ext == ".rtf":
            return DocumentExtractor._extract_rtf(file_bytes, source_name)
        elif ext in {".txt", ".md", ".yaml", ".yml"}:
            return DocumentExtractor._extract_plain_text(file_bytes, source_name, ext)
        elif ext in IMAGE_MIME_TYPES:
            return DocumentExtractor._extract_image(file_bytes, source_name, ext)
        else:
            return DocumentExtractor._extract_pdf(file_bytes, source_name, temp_file_path)

    @staticmethod
    def extract_from_url(url: str) -> List[Dict[str, Union[int, str]]]:
        """
        Safely fetches a public webpage (blocking SSRF and verifying TLS)
        and extracts structured readable article text.
        """
        logger.info(f"Scraping live website URL: {url}")
        _validate_safe_url(url)

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; InsightForge/1.0)"}
        )
        ssl_ctx = ssl.create_default_context()
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl_ctx),
            _SafeRedirectHandler()
        )
        max_bytes = settings.MAX_UPLOAD_SIZE_BYTES

        try:
            with opener.open(req, timeout=12) as response:
                raw = response.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    raise ValueError("Remote webpage response exceeds maximum allowed size.")
                html_text = _decode_text_bytes(raw)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            raise ValueError(f"Could not connect to URL '{url}': {str(e)}")

        pages = DocumentExtractor._parse_html_content(html_text, source_label=url)
        logger.info(f"URL '{url}' parsed into {len(pages)} sections.")
        return pages

    @staticmethod
    def _parse_html_content(html_text: str, source_label: str) -> List[Dict[str, Union[int, str]]]:
        soup = BeautifulSoup(html_text, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
            element.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else source_label
        body_text = soup.get_text(separator="\n")
        clean_lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        full_text = f"# {title}\nSource: {source_label}\n\n" + "\n".join(clean_lines)
        pages = _paginate_preserving_structure(full_text, page_word_limit=400)
        return pages or [{"page": 1, "text": f"# {title}\nSource: {source_label}\n\n(No readable text found)"}]

    @staticmethod
    def _extract_html(html_bytes: bytes, source_name: str) -> List[Dict[str, Union[int, str]]]:
        html_text = _decode_text_bytes(html_bytes)
        pages = DocumentExtractor._parse_html_content(html_text, source_label=source_name)
        logger.info(f"HTML {source_name} parsed into {len(pages)} sections.")
        return pages

    @staticmethod
    def _extract_docx(docx_bytes: bytes, source_name: str) -> List[Dict[str, Union[int, str]]]:
        try:
            import docx
            doc = docx.Document(io.BytesIO(docx_bytes))
            parts: List[str] = []

            for section in doc.sections:
                header_lines = [p.text.strip() for p in section.header.paragraphs if p.text.strip()]
                if header_lines:
                    parts.append("Header: " + " | ".join(header_lines))

            for p in doc.paragraphs:
                if p.text.strip():
                    parts.append(p.text.strip())

            for table in doc.tables:
                table_lines = []
                for row in table.rows:
                    row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                    if row_text:
                        table_lines.append(f"| {row_text} |")
                if table_lines:
                    parts.append("\n".join(table_lines))

            for section in doc.sections:
                footer_lines = [p.text.strip() for p in section.footer.paragraphs if p.text.strip()]
                if footer_lines:
                    parts.append("Footer: " + " | ".join(footer_lines))

            full_text = "\n\n".join(parts)
            pages = _paginate_preserving_structure(full_text, page_word_limit=400)
            if not pages:
                pages = [{"page": 1, "text": "Empty DOCX document."}]
            logger.info(f"DOCX {source_name} parsed into {len(pages)} sections.")
            return pages
        except Exception as e:
            logger.error(f"Failed to parse DOCX {source_name}: {e}")
            raise ValueError(f"Corrupt or unreadable DOCX: {e}")

    @staticmethod
    def _collect_pptx_shape_lines(shape, out_lines: List[str]) -> None:
        if getattr(shape, "has_text_frame", False):
            for paragraph in shape.text_frame.paragraphs:
                t = paragraph.text.strip()
                if t:
                    out_lines.append(t)
        if getattr(shape, "has_table", False):
            for row in shape.table.rows:
                row_vals = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_vals:
                    out_lines.append("| " + " | ".join(row_vals) + " |")
        if hasattr(shape, "shapes"):
            for sub in shape.shapes:
                DocumentExtractor._collect_pptx_shape_lines(sub, out_lines)

    @staticmethod
    def _extract_pptx(pptx_bytes: bytes, source_name: str) -> List[Dict[str, Union[int, str]]]:
        try:
            import pptx
            prs = pptx.Presentation(io.BytesIO(pptx_bytes))
            pages: List[Dict[str, Union[int, str]]] = []
            for idx, slide in enumerate(prs.slides, start=1):
                slide_lines: List[str] = []
                for shape in slide.shapes:
                    DocumentExtractor._collect_pptx_shape_lines(shape, slide_lines)

                if getattr(slide, "has_notes_slide", False) and slide.notes_slide.notes_text_frame:
                    notes = slide.notes_slide.notes_text_frame.text.strip()
                    if notes:
                        slide_lines.append(f"[Speaker Notes]: {notes}")

                content = f"[Slide {idx}]\n" + "\n".join(slide_lines) if slide_lines else f"[Slide {idx}] (No text)"
                pages.append({"page": idx, "text": content})

            if not pages:
                pages = [{"page": 1, "text": "Empty PPTX presentation."}]
            logger.info(f"PPTX {source_name} parsed into {len(pages)} slides.")
            return pages
        except Exception as e:
            logger.error(f"Failed to parse PPTX {source_name}: {e}")
            raise ValueError(f"Corrupt or unreadable PPTX: {e}")

    @staticmethod
    def _extract_spreadsheet(data_bytes: bytes, source_name: str, ext: str) -> List[Dict[str, Union[int, str]]]:
        try:
            import pandas as pd
            if ext in {".csv", ".tsv"}:
                sep = "\t" if ext == ".tsv" else ","
                text_data = _decode_text_bytes(data_bytes)
                if not text_data.strip():
                    return [{"page": 1, "text": "Empty spreadsheet."}]
                df = pd.read_csv(
                    io.StringIO(text_data),
                    sep=sep,
                    on_bad_lines="skip",
                    keep_default_na=False,
                    na_values=[""]
                )
                sheet_dict = {"Data": df}
            else:
                sheet_dict = pd.read_excel(
                    io.BytesIO(data_bytes),
                    sheet_name=None,
                    keep_default_na=False,
                    na_values=[""]
                )

            pages: List[Dict[str, Union[int, str]]] = []
            page_counter = 1

            for sheet_name, df in sheet_dict.items():
                if df.empty:
                    continue
                summary_lines = [
                    f"### Spreadsheet Sheet: {sheet_name}",
                    f"- Total Rows: {len(df)}",
                    f"- Total Columns: {len(df.columns)}",
                    f"- Column Headers: {', '.join([str(c) for c in df.columns])}"
                ]

                numeric_cols = df.select_dtypes(include=["number"]).columns
                if len(numeric_cols) > 0:
                    summary_lines.append("\n**Statistical Summary (Numeric Metrics):**")
                    for col in numeric_cols[:8]:
                        col_series = df[col].dropna()
                        if not col_series.empty:
                            summary_lines.append(
                                f"- Column '{col}': Total={col_series.sum():.2f}, Mean={col_series.mean():.2f}, "
                                f"Min={col_series.min():.2f}, Max={col_series.max():.2f}"
                            )

                summary_lines.append("\n**Sample Records:**")
                try:
                    summary_lines.append(df.head(15).to_markdown(index=False))
                except Exception:
                    summary_lines.append(df.head(15).to_string(index=False))

                pages.append({"page": page_counter, "text": "\n".join(summary_lines)})
                page_counter += 1

                if len(df) > 15:
                    for chunk_idx in range(15, min(2000, len(df)), 40):
                        batch = df.iloc[chunk_idx:chunk_idx + 40]
                        try:
                            batch_str = batch.to_markdown(index=False)
                        except Exception:
                            batch_str = batch.to_string(index=False)
                        pages.append({
                            "page": page_counter,
                            "text": f"### {sheet_name} (Rows {chunk_idx + 1} to {chunk_idx + len(batch)}):\n" + batch_str
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
    def _extract_json(json_bytes: bytes, source_name: str) -> List[Dict[str, Union[int, str]]]:
        raw = _decode_text_bytes(json_bytes)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in '{source_name}': {e}")

        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        formatted = f"# JSON Document: {source_name}\n\n{pretty}"
        pages = _paginate_preserving_structure(formatted, page_word_limit=350)
        return pages or [{"page": 1, "text": "Empty JSON document."}]

    @staticmethod
    def _extract_xml(xml_bytes: bytes, source_name: str) -> List[Dict[str, Union[int, str]]]:
        raw = _decode_text_bytes(xml_bytes)
        if re.search(r"<!\s*(DOCTYPE|ENTITY)", raw, re.IGNORECASE):
            raise ValueError("XML documents with DOCTYPE or ENTITY declarations are rejected for security.")
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            raise ValueError(f"Malformed XML in '{source_name}': {e}")

        lines: List[str] = [f"# XML Document: {source_name}"]

        def walk(node, depth: int = 0):
            tag = node.tag.split("}")[-1]
            attrs = " ".join(f"{k}={v}" for k, v in node.attrib.items())
            text_val = (node.text or "").strip()
            indent = "  " * depth
            label = f"{indent}- <{tag}" + (f" {attrs}" if attrs else "") + ">"
            if text_val:
                label += f": {text_val}"
            lines.append(label)
            for child in node:
                walk(child, depth + 1)

        walk(root)
        pages = _paginate_preserving_structure("\n".join(lines), page_word_limit=400)
        return pages or [{"page": 1, "text": "Empty XML document."}]

    @staticmethod
    def _extract_rtf(rtf_bytes: bytes, source_name: str) -> List[Dict[str, Union[int, str]]]:
        raw = _decode_text_bytes(rtf_bytes)
        if not raw.lstrip().startswith("{\\rtf"):
            raise ValueError(f"File '{source_name}' does not have a valid RTF header.")

        # Strip non-body destination groups (ignorable \* groups and metadata tables) respecting nested braces
        skip_destinations = {
            "fonttbl", "colortbl", "stylesheet", "info", "pict", "object",
            "listtable", "listoverridetable", "revtbl", "rsidtbl", "generator",
            "themedata", "colorschememapping", "latentstyles", "datastore",
        }
        out_chars: List[str] = []
        depth = 0
        skip_at_depth: Union[int, None] = None
        i = 0
        n = len(raw)
        while i < n:
            ch = raw[i]
            if ch == "\\" and i + 1 < n and raw[i + 1] in ("\\", "{", "}"):
                if skip_at_depth is None:
                    out_chars.append(raw[i:i + 2])
                i += 2
                continue
            if ch == "{":
                depth += 1
                if skip_at_depth is None:
                    m = re.match(r"\{\\(\*|[a-zA-Z]+)", raw[i:i + 40])
                    if m and (m.group(1) == "*" or m.group(1).lower() in skip_destinations):
                        skip_at_depth = depth
                        i += 1
                        continue
                    out_chars.append(ch)
            elif ch == "}":
                if skip_at_depth is not None and depth == skip_at_depth:
                    skip_at_depth = None
                elif skip_at_depth is None:
                    out_chars.append(ch)
                depth = max(0, depth - 1)
            else:
                if skip_at_depth is None:
                    out_chars.append(ch)
            i += 1

        cleaned = "".join(out_chars)
        cleaned = cleaned.replace("\\\\", "\x00BS\x00").replace("\\{", "\x00LB\x00").replace("\\}", "\x00RB\x00")
        cleaned = re.sub(r"\\(?:par|line)\b ?", "\n", cleaned)
        cleaned = re.sub(r"\\tab\b ?", "\t", cleaned)
        cleaned = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: bytes.fromhex(m.group(1)).decode("cp1252", errors="replace"), cleaned)
        cleaned = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", cleaned)
        cleaned = cleaned.replace("{", "").replace("}", "")
        cleaned = cleaned.replace("\x00BS\x00", "\\").replace("\x00LB\x00", "{").replace("\x00RB\x00", "}")
        lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
        pages = _paginate_preserving_structure("\n\n".join(lines), page_word_limit=400)
        return pages or [{"page": 1, "text": "Empty RTF document."}]

    @staticmethod
    def _extract_plain_text(text_bytes: bytes, source_name: str, ext: str) -> List[Dict[str, Union[int, str]]]:
        raw = _decode_text_bytes(text_bytes)
        pages = _paginate_preserving_structure(raw, page_word_limit=400)
        if not pages:
            pages = [{"page": 1, "text": "Empty document."}]
        logger.info(f"Plain text {source_name} ({ext}) parsed into {len(pages)} sections.")
        return pages

    @staticmethod
    def _extract_image(image_bytes: bytes, source_name: str, ext: str) -> List[Dict[str, Union[int, str]]]:
        try:
            from PIL import Image
            with Image.open(io.BytesIO(image_bytes)) as img:
                img.verify()
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                fmt = img.format or ext.lstrip(".").upper()
                mode = img.mode
        except Exception as e:
            logger.error(f"Invalid image '{source_name}': {e}")
            raise ValueError(f"Corrupt or unreadable image '{source_name}': {e}")

        header = f"### Image Document: {source_name}\n- Format: {fmt} ({mode})\n- Dimensions: {width}x{height} px\n- File Size: {len(image_bytes)} bytes"

        if gemini_client.is_configured:
            try:
                mime_type = IMAGE_MIME_TYPES.get(ext, "image/png")
                ocr_text = gemini_client.extract_image_multimodal(image_bytes, mime_type, source_name=source_name)
                if ocr_text:
                    return _paginate_preserving_structure(f"{header}\n\n### Extracted Visual Content:\n{ocr_text}", page_word_limit=400)
            except Exception as e:
                logger.warning(f"Gemini Vision OCR failed for image '{source_name}': {e}")

        fallback_note = (
            f"{header}\n\n"
            "Note: Image indexed with structural metadata. Configure GEMINI_API_KEY in .env to enable Gemini Multimodal Vision OCR & diagram transcription."
        )
        return [{"page": 1, "text": fallback_note}]

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
                        alt_text = page.extract_text() or ""
                        if alt_text.strip():
                            raw_text = alt_text
                    except Exception:
                        pass

                clean_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw_text)
                clean_text = re.sub(r"\r\n|\r", "\n", clean_text)
                clean_text = re.sub(r"[ \t]+", " ", clean_text)
                clean_text = re.sub(r"\n\s*\n+", "\n\n", clean_text).strip()

                if clean_text:
                    pages.append({"page": idx, "text": clean_text})
                else:
                    logger.warning(f"Page {idx} of {source_name} contained no direct text.")
            except Exception as page_err:
                logger.warning(f"Error extracting page {idx} in {source_name}: {page_err}")

        total_word_count = sum(len(str(p["text"]).split()) for p in pages)
        if total_word_count < 15:
            logger.info(f"PDF '{source_name}' has sparse/no embedded text ({total_word_count} words).")
            if gemini_client.is_configured:
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
                        logger.info(f"Gemini Multimodal Vision transcribed '{source_name}' ({len(ocr_text.split())} words).")
                        return [{"page": 1, "text": ocr_text}]
                except Exception as ocr_err:
                    logger.warning(f"Multimodal OCR fallback could not process {source_name}: {ocr_err}")

            if not pages:
                pages = [{
                    "page": 1,
                    "text": (
                        f"Scanned or image-based PDF '{source_name}' ({total_pages} page(s)) contains no embedded text layer. "
                        "Configure GEMINI_API_KEY in .env to enable Gemini Multimodal Vision OCR transcription."
                    )
                }]

        return pages


PDFExtractor = DocumentExtractor
