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
from lxml import etree


def etree_str(el) -> str:
    return etree.tostring(el, encoding="unicode")
from docx.shared import Cm, Pt, RGBColor

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

    # Font mặc định của cả tài liệu, của MỌI kiểu, và của số thứ tự danh sách.
    # Chỉ đặt font cho chữ là chưa đủ: số "1." "2." của danh sách đánh số lấy font
    # từ định nghĩa đánh số hoặc kiểu mặc định, nên vẫn ra Calibri.
    def ep_font(rpr):
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.insert(0, rf)
        for a_ in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a_), FONT)
        for a_ in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
            if rf.get(qn(a_)) is not None:
                del rf.attrib[qn(a_)]

    goc_st = d.styles.element
    dd = goc_st.find(qn("w:docDefaults"))
    if dd is not None:
        for rpr in dd.iter(qn("w:rPr")):
            ep_font(rpr)
    for st in goc_st.iter(qn("w:style")):
        rpr = st.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            st.append(rpr)
        ep_font(rpr)
    try:
        so = d.part.numbering_part.element
        for lvl in so.iter(qn("w:lvl")):
            rpr = lvl.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                lvl.append(rpr)
            ep_font(rpr)
    except Exception:
        pass                                     # tài liệu không có danh sách

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

        if "blip" in p._p.xml:                     # đoạn chứa ảnh
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.space_before, pf.space_after = Pt(6), Pt(2)
            pf.keep_with_next = True     # không để chú thích rớt sang trang sau
            continue
        if ten_style == "Image Caption":
            for r in p.runs:
                dat_font(r, CO_BODY)
                r.italic = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.space_after = Pt(8)
            continue
        if ten_style == "Title":
            for r in p.runs:
                dat_font(r, CO_MUC + 2, dam=True)
                r.font.color.rgb = RGBColor(0, 0, 0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.space_after = Pt(10)
        elif ten_style in ("Heading 1", "Heading 2"):
            for r in p.runs:
                dat_font(r, CO_MUC, dam=True)
                r.font.color.rgb = RGBColor(0, 0, 0)
            pf.space_before, pf.space_after = Pt(10), Pt(5)
            pf.keep_with_next = True     # tiêu đề không đứng trơ cuối trang
        elif ten_style.startswith("Heading"):
            for r in p.runs:
                dat_font(r, CO_MUC_NHO, dam=True)
                r.font.color.rgb = RGBColor(0, 0, 0)
            pf.space_before, pf.space_after = Pt(8), Pt(4)
            pf.keep_with_next = True     # tiêu đề không đứng trơ cuối trang
        else:
            for r in p.runs:
                dat_font(r, CO_BODY)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # đoạn dẫn ngay trước một bảng ("Dẫn chứng trên git.") đi cùng bảng đó,
    # không bị bỏ lại một mình ở cuối trang
    for el in d.element.body.iterchildren():
        nxt = el.getnext()
        truoc_anh = (nxt is not None and nxt.tag == qn("w:p")
                     and "blip" in etree_str(nxt))
        if el.tag == qn("w:p") and nxt is not None and (
                nxt.tag == qn("w:tbl") or truoc_anh):
            # vòng lặp đoạn ở trên đã ghi keepNext = 0, nên phải ghi đè chứ
            # không chỉ thêm khi chưa có
            pPr = el.get_or_add_pPr()
            for cu in pPr.findall(qn("w:keepNext")):
                pPr.remove(cu)
            pPr.append(OxmlElement("w:keepNext"))

    # co ảnh về đúng bề rộng vùng chữ, giữ tỉ lệ; ảnh nhỏ hơn thì để nguyên
    rong = Cm(21.0) - LE_NGANG * 2
    for sh in d.inline_shapes:
        if sh.width and sh.width > rong:
            ty = rong / sh.width
            sh.width, sh.height = int(sh.width * ty), int(sh.height * ty)

    for t in d.tables:
        t.autofit = True
        ke_khung(t)
        for i, row in enumerate(t.rows):
            trPr = row._tr.get_or_add_trPr()
            for el in trPr.findall(qn("w:cantSplit")):
                trPr.remove(el)
            if i == 0:
                # dòng tiêu đề lặp lại khi bảng sang trang, và không đứng trơ
                # một mình ở cuối trang
                if trPr.find(qn("w:tblHeader")) is None:
                    trPr.append(OxmlElement("w:tblHeader"))
            for c in row.cells:
                for p in c.paragraphs:
                    pf = p.paragraph_format
                    pf.space_before = pf.space_after = Pt(1)
                    pf.line_spacing = 1.0
                    if i == 0:
                        pf.keep_with_next = True
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
                        "--from=markdown", "--to=docx",
                        f"--resource-path={os.path.dirname(os.path.abspath(md))}"],
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
    global CO_BANG
    ap = argparse.ArgumentParser(description="Markdown -> PDF đúng quy cách")
    ap.add_argument("files", nargs="+", help="file .md (nhận cả mẫu *.md)")
    ap.add_argument("--co-bang", type=int, default=CO_BANG,
                    help="cỡ chữ trong bảng (mặc định 12)")
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

    CO_BANG = a.co_bang
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
