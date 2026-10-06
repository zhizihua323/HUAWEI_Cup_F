import json
import sys
from collections import Counter
from docx import Document
from docx.oxml.ns import qn


def font_info(font):
    return {
        "name": font.name,
        "size_pt": font.size.pt if font.size else None,
        "bold": font.bold,
        "italic": font.italic,
    }


def main():
    doc = Document(sys.argv[1])
    styles = {}
    for name in ["Normal", "Title", "Heading 1", "Heading 2", "Heading 3", "Caption"]:
        if name in doc.styles:
            s = doc.styles[name]
            rpr = s.element.rPr
            east = None
            if rpr is not None and rpr.rFonts is not None:
                east = rpr.rFonts.get(qn("w:eastAsia"))
            pf = s.paragraph_format
            styles[name] = {
                **font_info(s.font),
                "eastAsia": east,
                "line_spacing": str(pf.line_spacing),
                "space_before_pt": pf.space_before.pt if pf.space_before else None,
                "space_after_pt": pf.space_after.pt if pf.space_after else None,
                "left_indent_cm": pf.left_indent.cm if pf.left_indent else None,
                "first_line_indent_cm": pf.first_line_indent.cm if pf.first_line_indent else None,
            }
    run_fonts = Counter()
    run_sizes = Counter()
    for p in doc.paragraphs:
        for r in p.runs:
            if r.text.strip():
                run_fonts[(r.font.name or "", r._element.rPr.rFonts.get(qn("w:eastAsia")) if r._element.rPr is not None and r._element.rPr.rFonts is not None else "")] += len(r.text)
                run_sizes[r.font.size.pt if r.font.size else None] += len(r.text)
    sec = doc.sections[0]
    print(json.dumps({
        "styles": styles,
        "direct_run_fonts_weighted": run_fonts.most_common(12),
        "direct_run_sizes_weighted": run_sizes.most_common(12),
        "page_cm": [sec.page_width.cm, sec.page_height.cm],
        "margins_cm": [sec.top_margin.cm, sec.bottom_margin.cm, sec.left_margin.cm, sec.right_margin.cm],
        "different_first_page": sec.different_first_page_header_footer,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
