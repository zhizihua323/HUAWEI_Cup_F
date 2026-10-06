import json
import re
import sys
from pathlib import Path

import pdfplumber
from PIL import Image, ImageDraw, ImageFont


def extract_pdf(pdf_path: Path, output_path: Path) -> None:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            pages.append({"page": i, "text": page.extract_text() or ""})
    output_path.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")


def contact_sheet(image_paths, output_path: Path, cols=4, thumb_width=320):
    items = []
    for p in image_paths:
        im = Image.open(p).convert("RGB")
        ratio = thumb_width / im.width
        im = im.resize((thumb_width, int(im.height * ratio)))
        items.append((p, im))
    if not items:
        return
    label_h = 28
    cell_h = max(im.height for _, im in items) + label_h
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_width, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, (p, im) in enumerate(items):
        x = (idx % cols) * thumb_width
        y = (idx // cols) * cell_h
        sheet.paste(im, (x, y + label_h))
        draw.text((x + 8, y + 6), p.stem, fill="black")
    sheet.save(output_path)


def main():
    mode = sys.argv[1]
    if mode == "extract":
        extract_pdf(Path(sys.argv[2]), Path(sys.argv[3]))
    elif mode == "sheet":
        folder = Path(sys.argv[2])
        output = Path(sys.argv[3])
        start = int(sys.argv[4])
        end = int(sys.argv[5])
        paths = sorted(folder.glob("*.png"))[start - 1:end]
        contact_sheet(paths, output)
    elif mode == "report":
        pages = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        first_n = int(sys.argv[3])
        for item in pages[:first_n]:
            print(f"\n=== PAGE {item['page']} ===\n{item['text']}")
        print("\n=== HEADING CANDIDATES ===")
        pattern = re.compile(r"^\s*(?:[一二三四五六七八九十]+、|\d+(?:\.\d+){0,2}\s+)")
        for item in pages:
            for line in item["text"].splitlines():
                if pattern.match(line):
                    print(f"{item['page']}: {line.strip()}")


if __name__ == "__main__":
    main()
