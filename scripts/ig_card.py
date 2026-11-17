#!/usr/bin/env python3
"""Картки NutriCheck для Instagram (власний дизайн, без фото магазинів).

Використання:
  python3 ig_card.py <input.json> <out_dir>

input.json:
{
  "date": "2026-11-18",
  "pod":  {"name": "...", "score": 84, "band": "Чудово", "manufacturer": false,
           "notes": [{"t": "+", "text": "Мало цукру: 3.9 г на 100 г"}, {"t": "-", "text": "..."}]},
  "quiz": {"name": "...", "score": 70, "band": "Добре"}
}

Вихід (JPEG): <out_dir>/pod.jpg (1080x1350, пост), quiz_q.jpg і quiz_a.jpg (1080x1920, сторіз).
"""
import json
import sys
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
    header(dr, W, "Продукт дня")
    y = 170
    for line in wrap(dr, d["name"], font(54, True), W - 120)[:3]:
        dr.text((60, y), line, font=font(54, True), fill=INK)
        y += 68
    ring(dr, 300, y + 230, 190, int(d["score"]))
    col = band_color(int(d["score"]))
    dr.text((560, y + 150), d.get("band") or "", font=font(64, True), fill=col)
    if d.get("manufacturer"):
        dr.text((560, y + 240), "за даними виробника", font=font(32), fill=MUTED)
    y += 480
    notes = d.get("notes") or []
    if notes:
        dr.text((60, y), "Що помітно на етикетці:", font=font(38, True), fill=INK)
        y += 64
        for n in notes[:3]:
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
    y = 330
    for line in wrap(dr, "Скільки балів отримав цей товар?", font(52, True), W - 120):
        dr.text((60, y), line, font=font(52, True), fill=INK)
        y += 66
    y += 54
    for line in wrap(dr, d["name"], font(60, True), W - 120)[:4]:
        dr.text((60, y), line, font=font(60, True), fill=BRAND)
        y += 78
    y += 80
    for (lo, col, lbl), rng in zip(BANDS[::-1], ["0–24", "25–49", "50–74", "75–100"]):
        dr.rounded_rectangle([60, y, W - 60, y + 150], radius=40, fill=(255, 255, 255), outline=col, width=6)
        dr.ellipse([100, y + 45, 160, y + 105], fill=col)
        dr.text((200, y + 42), f"{rng} · {lbl}", font=font(54, True), fill=INK)
        y += 190
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
