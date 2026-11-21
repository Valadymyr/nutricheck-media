#!/usr/bin/env python3
"""Картки NutriCheck для Instagram (власний дизайн + фото товару з бази, рішення власника 21.11.2026).

Використання:
  python3 ig_card.py <input.json> <out_dir>

input.json:
{
  "date": "2026-11-18",
  "pod":  {"name": "...", "score": 84, "band": "Чудово", "manufacturer": false, "image_url": "https://...jpg",
           "notes": [{"t": "+", "text": "Мало цукру: 3.9 г на 100 г"}, {"t": "-", "text": "..."}]},
  "quiz": {"name": "...", "score": 70, "band": "Добре", "image_url": "https://...jpg"}
}

image_url — необов'язкове: фото товару (URL або локальний шлях). Не вдалося завантажити — картка без фото.
Вихід (JPEG): <out_dir>/pod.jpg (1080x1350, пост), quiz_q.jpg і quiz_a.jpg (1080x1920, сторіз).
"""
import io
import json
import sys
import urllib.request
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BG = (246, 248, 243)
INK = (28, 33, 30)
MUTED = (110, 118, 112)
BRAND = (21, 128, 61)
BANDS = [(75, (30, 158, 90), "Чудово"), (50, (226, 168, 0), "Добре"), (25, (234, 88, 12), "Так собі"), (0, (215, 38, 61), "Погано")]


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def band_color(score):
    for lo, col, _ in BANDS:
        if score >= lo:
            return col
    return BANDS[-1][1]


def wrap(draw, text, fnt, width_px):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= width_px:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def load_photo(src):
    """Фото товару: URL або шлях. None, якщо не вдалося."""
    if not src:
        return None
    try:
        if str(src).startswith("http"):
            req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0 (NutriCheck card bot)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read(8_000_000)
            im = Image.open(io.BytesIO(data))
        else:
            im = Image.open(src)
        im.load()
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            bg.alpha_composite(im)
            im = bg
        return im.convert("RGB")
    except Exception as e:  # noqa: BLE001
        print("photo_fail", src, e, file=sys.stderr)
        return None


def paste_photo(img, photo, box, radius=36):
    """Фото «вписане» в білу картку з заокругленими кутами (без обрізання товару)."""
    x0, y0, x1, y1 = box
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle(box, radius=radius, fill=(255, 255, 255), outline=(225, 230, 224), width=3)
    pad = 24
    bw, bh = x1 - x0 - 2 * pad, y1 - y0 - 2 * pad
    ph = photo.copy()
    # біла рамка навколо товару на фото магазину часто велика — прибираємо
    try:
        from PIL import ImageChops
        diff = ImageChops.difference(ph, Image.new("RGB", ph.size, (255, 255, 255)))
        bbox = diff.point(lambda v: 255 if v > 18 else 0).getbbox()
        if bbox:
            ph = ph.crop(bbox)
    except Exception:  # noqa: BLE001
        pass
    scale = min(bw / ph.width, bh / ph.height)
    ph = ph.resize((max(1, int(ph.width * scale)), max(1, int(ph.height * scale))), Image.LANCZOS)
    img.paste(ph, (x0 + pad + (bw - ph.width) // 2, y0 + pad + (bh - ph.height) // 2))


def ring(draw, cx, cy, r, score, width=34):
    col = band_color(score)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(225, 230, 224), width=width)
    end = -90 + 360 * max(0, min(score, 100)) / 100
    draw.arc([cx - r, cy - r, cx + r, cy + r], start=-90, end=end, fill=col, width=width)
    f = font(int(r * 0.9), True)
    s = str(score)
    w = draw.textlength(s, font=f)
    draw.text((cx - w / 2, cy - r * 0.62), s, font=f, fill=INK)
    f2 = font(int(r * 0.2))
    w2 = draw.textlength("зі 100", font=f2)
    draw.text((cx - w2 / 2, cy + r * 0.38), "зі 100", font=f2, fill=MUTED)


def header(draw, W, title):
    draw.rectangle([0, 0, W, 120], fill=BRAND)
    draw.text((60, 34), "NutriCheck", font=font(48, True), fill=(255, 255, 255))
    f = font(40)
    w = draw.textlength(title, font=f)
    draw.text((W - 60 - w, 40), title, font=f, fill=(225, 245, 230))


def footer(draw, W, H):
    draw.text((60, H - 150), "Перевір свій товар у Telegram:", font=font(36), fill=MUTED)
    draw.text((60, H - 100), "@NutriCheckUA_bot", font=font(44, True), fill=BRAND)
    f = font(24)
    t = "Оцінка алгоритму за даними етикетки. Не медична порада."
    draw.text((W - 60 - draw.textlength(t, font=f), H - 40), t, font=f, fill=MUTED)


def pod_card(d, out):
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img)
    header(dr, W, d.get("title") or "Продукт дня")
    y = 170
    for line in wrap(dr, d["name"], font(54, True), W - 120)[:3]:
        dr.text((60, y), line, font=font(54, True), fill=INK)
        y += 68
    score = int(d["score"])
    col = band_color(score)
    photo = load_photo(d.get("image_url"))
    if photo:
        # зліва — бал, справа — фото товару
        y += 30
        paste_photo(img, photo, (560, y, W - 60, y + 460))
        ring(dr, 290, y + 200, 170, score)
        b = d.get("band") or ""
        fb = font(56, True)
        dr.text((290 - dr.textlength(b, font=fb) / 2, y + 395), b, font=fb, fill=col)
        if d.get("manufacturer"):
            t = "за даними виробника"
            dr.text((290 - dr.textlength(t, font=font(28)) / 2, y + 465), t, font=font(28), fill=MUTED)
        y += 530
    else:
        ring(dr, 300, y + 230, 190, score)
        dr.text((560, y + 150), d.get("band") or "", font=font(64, True), fill=col)
        if d.get("manufacturer"):
            dr.text((560, y + 240), "за даними виробника", font=font(32), fill=MUTED)
        y += 480
    notes = d.get("notes") or []
    if notes:
        dr.text((60, y), "Що помітно на етикетці:", font=font(38, True), fill=INK)
        y += 64
        for n in notes[:3]:
            if y > H - 200:
                break
            mark = (30, 158, 90) if n.get("t") == "+" else (234, 88, 12) if n.get("t") == "-" else MUTED
            for i, line in enumerate(wrap(dr, n["text"], font(36), W - 170)[:2]):
                if i == 0:
                    dr.ellipse([66, y + 12, 90, y + 36], fill=mark)
                dr.text((110, y), line, font=font(36), fill=INK)
                y += 48
            y += 14
    footer(dr, W, H)
    img.save(out, "JPEG", quality=90)


def story_base(title):
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, W, 220], fill=BRAND)
    dr.text((60, 70), "NutriCheck", font=font(64, True), fill=(255, 255, 255))
    f = font(48)
    dr.text((W - 60 - dr.textlength(title, font=f), 84), title, font=f, fill=(225, 245, 230))
    return img, dr, W, H


def quiz_question(d, out):
    img, dr, W, H = story_base("Вгадай бал")
    y = 300
    for line in wrap(dr, "Скільки балів отримав цей товар?", font(52, True), W - 120):
        dr.text((60, y), line, font=font(52, True), fill=INK)
        y += 66
    y += 30
    photo = load_photo(d.get("image_url"))
    name_lines = wrap(dr, d["name"], font(56 if photo else 60, True), W - 120)[:3 if photo else 4]
    for line in name_lines:
        dr.text((60, y), line, font=font(56 if photo else 60, True), fill=BRAND)
        y += 72 if photo else 78
    if photo:
        y += 20
        paste_photo(img, photo, (W // 2 - 230, y, W // 2 + 230, y + 400))
        y += 440
        step, hh = 140, 112
    else:
        y += 80
        step, hh = 190, 150
    for (lo, col, lbl), rng in zip(BANDS[::-1], ["0–24", "25–49", "50–74", "75–100"]):
        dr.rounded_rectangle([60, y, W - 60, y + hh], radius=40, fill=(255, 255, 255), outline=col, width=6)
        dr.ellipse([100, y + hh // 2 - 30, 160, y + hh // 2 + 30], fill=col)
        dr.text((200, y + hh // 2 - 32), f"{rng} · {lbl}", font=font(52, True), fill=INK)
        y += step
    dr.text((60, H - 220), "Відповідь — у наступній сторіз", font=font(44), fill=MUTED)
    dr.text((60, H - 150), "@NutriCheckUA_bot", font=font(52, True), fill=BRAND)
    img.save(out, "JPEG", quality=90)


def quiz_answer(d, out):
    img, dr, W, H = story_base("Відповідь")
    y = 320
    for line in wrap(dr, d["name"], font(52, True), W - 120)[:3]:
        dr.text((60, y), line, font=font(52, True), fill=INK)
        y += 68
    ring(dr, W // 2, y + 380, 280, int(d["score"]), width=46)
    col = band_color(int(d["score"]))
    b = d.get("band") or ""
    f = font(80, True)
    dr.text((W / 2 - dr.textlength(b, font=f) / 2, y + 720), b, font=f, fill=col)
    dr.text((60, H - 300), "Перевір свій товар безкоштовно:", font=font(44), fill=MUTED)
    dr.text((60, H - 230), "@NutriCheckUA_bot у Telegram", font=font(54, True), fill=BRAND)
    t = "Оцінка алгоритму за даними етикетки."
    dr.text((60, H - 120), t, font=font(32), fill=MUTED)
    img.save(out, "JPEG", quality=90)


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    if data.get("pod"):
        pod_card(data["pod"], out / "pod.jpg")
    if data.get("quiz"):
        quiz_question(data["quiz"], out / "quiz_q.jpg")
        quiz_answer(data["quiz"], out / "quiz_a.jpg")
    print("ok", *sorted(p.name for p in out.glob("*.jpg")))


if __name__ == "__main__":
    main()
