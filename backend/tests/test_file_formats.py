import io
import json
import pytest
import docx
import openpyxl
from PIL import Image
from pptx import Presentation
from pypdf import PdfWriter
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _make_text_pdf_bytes(text: str) -> bytes:
    """Builds a minimal valid single-page PDF 1.4 containing literal embedded text."""
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream_content = f"BT\n/F1 12 Tf\n72 720 Td\n({escaped}) Tj\nET\n".encode("latin-1")
    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        b"4 0 obj\n<< /Length " + str(len(stream_content)).encode() + b" >>\nstream\n" + stream_content + b"endstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for obj in objs:
        offsets.append(out.tell())
        out.write(obj)
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode())
    return out.getvalue()


def _make_blank_pdf_bytes() -> bytes:
    w = PdfWriter()
    w.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _make_docx_bytes() -> bytes:
    d = docx.Document()
    d.sections[0].header.paragraphs[0].text = "InsightForge Header"
    d.add_paragraph("Contract Clause 1: Vendors must retain encrypted backups for 90 days.")
    tbl = d.add_table(rows=2, cols=2)
    tbl.cell(0, 0).text = "Tier"
    tbl.cell(0, 1).text = "SLA"
    tbl.cell(1, 0).text = "Enterprise"
    tbl.cell(1, 1).text = "99.95%"
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _make_pptx_bytes() -> bytes:
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Q4 Growth Deck"
    slide.placeholders[1].text = "Annual recurring revenue reached $4.2M with 18% net retention expansion."
    slide.notes_slide.notes_text_frame.text = "Speaker note: emphasize APAC onboarding."
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _make_xlsx_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Metrics"
    ws.append(["Department", "Budget", "Headcount"])
    ws.append(["Engineering", 450000, 12])
    ws.append(["Research", 320000, 8])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_image_bytes(fmt: str) -> bytes:
    img = Image.new("RGB", (64, 48), color=(79, 70, 229))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.mark.parametrize(
    "filename,content,expected_mime,expected_snippet",
    [
        ("policy.pdf", _make_text_pdf_bytes("InsightForge PDF policy requires 75 percent attendance."), "application/pdf", "75 percent attendance"),
        ("scanned.pdf", _make_blank_pdf_bytes(), "application/pdf", "GEMINI_API_KEY"),
        ("contract.docx", _make_docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "99.95%"),
        ("deck.pptx", _make_pptx_bytes(), "application/vnd.openxmlformats-officedocument.presentationml.presentation", "APAC onboarding"),
        ("metrics.xlsx", _make_xlsx_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Engineering"),
        ("data.csv", b"region,revenue\nNA,12000\nEU,9500\n", "text/csv", "NA"),
        ("latin.csv", "city,note\nMünchen,Café\n".encode("latin-1"), "text/csv", "München"),
        ("records.tsv", b"role\tstipend\nIntern\t25000\nFTE\t95000\n", "text/tab-separated-values", "Intern"),
        ("notes.txt", b"InsightForge TXT note: Probation duration is 6 months.", "text/plain", "Probation duration"),
        ("guide.md", b"# Release Guide\n\nAll builds pass pytest and oxlint before deploy.", "text/markdown", "oxlint"),
        ("config.json", json.dumps({"service": "InsightForge", "port": 8000}).encode("utf-8"), "application/json", "InsightForge"),
        ("article.html", b"<html><head><title>Portal</title></head><body><p>HTML policy text here.</p></body></html>", "text/html", "HTML policy text"),
        ("page.htm", b"<html><body><h1>HTM Heading</h1><p>Secondary markup body.</p></body></html>", "text/html", "HTM Heading"),
        ("manifest.xml", b"<catalog><item id='1'>XML verified rule</item></catalog>", "application/xml", "XML verified rule"),
        ("memo.rtf", br"{\rtf1\ansi{\fonttbl{\f0 Arial;}} Memo: \par 30 day notice required.}", "application/rtf", "30 day notice"),
        ("simple.rtf", br"{\rtf1\ansi Minimal RTF-SIMPLE body.}", "application/rtf", "RTF-SIMPLE"),
        ("deploy.yaml", b"service: insightforge\nreplicas: 2\n", "text/yaml", "replicas: 2"),
        ("settings.yml", b"env: production\nrag_alpha: 0.65\n", "text/yaml", "rag_alpha"),
        ("diagram.png", _make_image_bytes("PNG"), "image/png", "64x48 px"),
        ("scan.jpg", _make_image_bytes("JPEG"), "image/jpeg", "64x48 px"),
        ("photo.jpeg", _make_image_bytes("JPEG"), "image/jpeg", "64x48 px"),
        ("chart.webp", _make_image_bytes("WEBP"), "image/webp", "64x48 px"),
    ],
)
def test_upload_preview_and_download_all_supported_formats(filename, content, expected_mime, expected_snippet):
    headers = {"X-Guest-Session-Id": "guest_format_tester"}
    res = client.post(
        "/api/documents/upload",
        files={"file": (filename, content)},
        headers=headers
    )
    assert res.status_code == 200, f"Failed {filename}: {res.text}"
    body = res.json()
    assert body["success"] is True
    doc = body["document"]
    doc_id = doc["document_id"]
    assert doc["total_chunks"] >= 1

    # Preview endpoint must extract structured content
    prev = client.get(f"/api/documents/{doc_id}/preview", headers=headers)
    assert prev.status_code == 200
    prev_data = prev.json()
    combined = "\n".join(p["text"] for p in prev_data["pages"])
    assert expected_snippet in combined

    # File endpoint must return matching MIME type
    f_res = client.get(f"/api/documents/{doc_id}/file", headers=headers)
    assert f_res.status_code == 200
    assert expected_mime in f_res.headers["content-type"]

    # Clean up
    del_res = client.delete(f"/api/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 200


@pytest.mark.parametrize(
    "filename,content",
    [
        ("empty.txt", b""),
        ("malware.exe", b"MZ\x90\x00"),
        ("fake.pdf", b"not a real pdf header"),
        ("fake.png", b"not a png"),
        ("fake.docx", b"not a zip archive"),
        ("broken.json", b"{bad json"),
        ("xxe.xml", b"<!DOCTYPE foo [ <!ENTITY bar 'baz'> ]><foo>&bar;</foo>"),
    ],
)
def test_invalid_or_spoofed_files_rejected_with_400(filename, content):
    res = client.post(
        "/api/documents/upload",
        files={"file": (filename, content)},
        headers={"X-Guest-Session-Id": "guest_negative_tester"}
    )
    assert res.status_code == 400
