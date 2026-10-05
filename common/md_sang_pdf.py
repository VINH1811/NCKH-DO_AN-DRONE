# -*- coding: utf-8 -*-
"""Chuyển tài liệu Markdown sang PDF đúng quy cách trình bày của đề tài.

Đường đi: pandoc dựng .docx -> python-docx chỉnh quy cách -> Word xuất .pdf.
Không dùng pandoc xuất thẳng PDF vì cách đó cần LaTeX, mà LaTeX lại hay vỡ dấu
tiếng Việt nếu thiếu font.

Quy cách (giống bộ hồ sơ đề án đã nộp):
  Times New Roman · chữ thường 13 · tiêu đề và mục 14 in đậm · bảng 12 · A4

Chạy:
  python common/md_sang_pdf.py docs/pilot/*.md
  python common/md_sang_pdf.py docs/pilot/phieu_dong_y.md --giu-docx
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import re
import subprocess
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

FONT = "Times New Roman"
CO_BODY, CO_MUC, CO_MUC_NHO, CO_BANG = 13, 14, 13, 12
LE_NGANG, LE_DOC = Cm(2.0), Cm(1.8)


def dat_font(run, co: float, dam: bool | None = None):
    run.font.name = FONT
    run.font.size = Pt(co)
    if dam is not None:
        run.bold = dam
    rf = run._element.get_or_add_rPr().get_or_add_rFonts()
    # tiếng Việt có dấu rơi vào hệ chữ Đông Á, phải đặt cả bốn thuộc tính
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)


def ke_khung(t):
    tblPr = t._tbl.tblPr
    for cu in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(cu)
    bd = OxmlElement("w:tblBorders")
    for canh in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{canh}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), "808080")
        bd.append(e)
    tblPr.append(bd)


def chinh_docx(duong_dan: str) -> None:
    d = Document(duong_dan)
    for sec in d.sections:
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.left_margin = sec.right_margin = LE_NGANG
        sec.top_margin = sec.bottom_margin = LE_DOC

    for ten in ("Normal", "Body Text", "Compact", "Quote", "Block Text"):
        try:
            st = d.styles[ten]
            st.font.name, st.font.size = FONT, Pt(CO_BODY)
            st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        except KeyError:
            pass

    for p in list(d.paragraphs):
        ten_style = p.style.name or ""
        if not p.text.strip() and "blip" not in p._p.xml:
            p._element.getparent().remove(p._element)
            continue
        pf = p.paragraph_format
        pf.line_spacing = 1.15
        pf.space_before, pf.space_after = Pt(0), Pt(4)
        pf.keep_with_next = False
        pf.page_break_before = False

        if ten_style == "Title":
            for r in p.runs:
                dat_font(r, CO_MUC + 2, dam=True)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.space_after = Pt(10)
        elif ten_style in ("Heading 1", "Heading 2"):
            for r in p.runs:
                dat_font(r, CO_MUC, dam=True)
            pf.space_before, pf.space_after = Pt(10), Pt(5)
        elif ten_style.startswith("Heading"):
            for r in p.runs:
                dat_font(r, CO_MUC_NHO, dam=True)
            pf.space_before, pf.space_after = Pt(8), Pt(4)
        else:
            for r in p.runs:
                dat_font(r, CO_BODY)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for t in d.tables:
        t.autofit = True
        ke_khung(t)
        for i, row in enumerate(t.rows):
            trPr = row._tr.get_or_add_trPr()
            for el in trPr.findall(qn("w:cantSplit")):
                trPr.remove(el)
            for c in row.cells:
                for p in c.paragraphs:
                    pf = p.paragraph_format
                    pf.space_before = pf.space_after = Pt(1)
                    pf.line_spacing = 1.0
                    for r in p.runs:
                        dat_font(r, CO_BANG, dam=True if i == 0 else None)
    d.save(duong_dan)


def mo_word():
    """Bật Word một lần cho cả mẻ. Bật/tắt cho từng file vừa chậm vừa hay treo:
    instance cũ chưa thoát hẳn mà instance mới đã xin bật."""
    import win32com.client as win32
    w = win32.DispatchEx("Word.Application")      # tiến trình riêng, không bám
    w.Visible = False
    w.DisplayAlerts = 0                           # không hiện hộp thoại nào
    return w


def xuat_pdf(word, docx_path: str, pdf_path: str) -> bool:
    try:
        doc = word.Documents.Open(os.path.abspath(docx_path),
                                  ReadOnly=False, AddToRecentFiles=False)
        doc.SaveAs(os.path.abspath(pdf_path), FileFormat=17)   # 17 = PDF
        doc.Close(False)
        return True
    except Exception as e:
        print(f"  Word xuất PDF lỗi: {e}")
        return False


def mot_file(word, md: str, giu_docx: bool) -> bool:
    goc = os.path.splitext(md)[0]
    docx_path, pdf_path = goc + ".docx", goc + ".pdf"
    print(f"{os.path.basename(md)}")

    s = io.open(md, encoding="utf-8").read()
    s = re.sub(r"\n{3,}", "\n\n", s)
    tam = goc + "._build.md"
    io.open(tam, "w", encoding="utf-8").write(s)

    r = subprocess.run(["pandoc", tam, "-o", docx_path,
                        "--from=markdown", "--to=docx"],
                       capture_output=True, text=True)
    os.remove(tam)
    if r.returncode != 0:
        print(f"  pandoc lỗi: {r.stderr[:300]}")
        return False

    chinh_docx(docx_path)
    ok = xuat_pdf(word, docx_path, pdf_path)
    if ok:
        print(f"  -> {os.path.basename(pdf_path)} "
              f"({os.path.getsize(pdf_path)/1024:.0f} KB)")
    if not giu_docx and os.path.exists(docx_path):
        os.remove(docx_path)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Markdown -> PDF đúng quy cách")
    ap.add_argument("files", nargs="+", help="file .md (nhận cả mẫu *.md)")
    ap.add_argument("--giu-docx", action="store_true",
                    help="giữ lại .docx trung gian để sửa tay")
    a = ap.parse_args()

    ds = []
    for f in a.files:
        ds.extend(sorted(glob.glob(f)) if any(c in f for c in "*?") else [f])
    ds = [f for f in ds if f.lower().endswith(".md")]
    if not ds:
        print("Không có file .md nào.")
        return 1

    word = mo_word()
    try:
        xong = sum(mot_file(word, f, a.giu_docx) for f in ds)
    finally:
        try:
            word.Quit()
        except Exception:
            pass
    print(f"\nXong {xong}/{len(ds)} file.")
    return 0 if xong == len(ds) else 1


if __name__ == "__main__":
    sys.exit(main())
