from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent / "equations"
OUT.mkdir(parents=True, exist_ok=True)
FONT = r"C:\Windows\Fonts\cambria.ttc"
BASE = ImageFont.truetype(FONT, 58, index=0)
SUB = ImageFont.truetype(FONT, 36, index=0)


def render(name, segments):
    canvas = Image.new("RGBA", (2200, 170), (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)
    widths = []
    for text, subscript in segments:
        font = SUB if subscript else BASE
        box = draw.textbbox((0, 0), text, font=font)
        widths.append(box[2] - box[0])
    x = max(30, (canvas.width - sum(widths)) // 2)
    for (text, subscript), width in zip(segments, widths):
        y = 62 if subscript else 28
        draw.text((x, y), text, fill=(0, 0, 0, 255), font=SUB if subscript else BASE)
        x += width
    bbox = canvas.getbbox()
    cropped = canvas.crop((max(0, bbox[0] - 20), max(0, bbox[1] - 15), min(canvas.width, bbox[2] + 20), min(canvas.height, bbox[3] + 15)))
    cropped.save(OUT / name, dpi=(300, 300))


render("Q4-01A.png", [("M", False), ("0", True), (":  y = a", False)])
render(
    "Q4-01B.png",
    [("M", False), ("1", True), (":  y = a + b", False), ("C", True), (" log", False), ("10", True), ("(C)", False)],
)
render(
    "Q4-01C.png",
    [("M", False), ("2", True), (":  y = a + b", False), ("C", True), (" log", False), ("10", True), ("(C) + b", False), ("T", True), (" t", False)],
)

for path in sorted(OUT.glob("Q4-*.png")):
    print(path)
