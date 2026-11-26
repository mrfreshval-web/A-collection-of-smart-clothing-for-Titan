"""Вёрстка рекламных макетов «Титан» для Instagram поверх фотографий.

Запуск:
  python3 compose.py photos/ out/ [--site titan.example]
В папке photos/ ожидаются файлы 1.jpg … 5.jpg (или .png/.webp) и, по желанию, story.jpg.
Если фото нет, макет собирается на тёмном фоне-заглушке (для проверки вёрстки).
Шрифты: Inter / Inter Display (SIL OFL).
"""
import sys, os, glob, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

INTER = "/usr/share/fonts/opentype/inter/"
WHITE = (245, 242, 236)
DIM = (200, 196, 190)
AMBER = (240, 168, 92)

SLIDES = [
    dict(n=1, tag="СКОРО", head=["ТВОЙ КЛИМАТ.", "ВЕЗДЕ."], accent=1,
         sub="Одежда, которая думает о теле.", cta=None, swipe=True, fy=0.3),
    dict(n=2, tag="SMART CASUAL", head=["МИНУС 25.", "ТЕБЕ ТЕПЛО."], accent=1,
         sub="Город, мороз, ветер. Тебе комфортно.", cta=None, swipe=True, fy=0.2),
    dict(n=3, tag="SMART CASUAL", head=["ЗАБУДЬ О ХОЛОДЕ.", "ДУМАЙ О ЦЕЛИ."], accent=1,
         sub="Комфорт тела теперь забота одежды.", cta=None, swipe=True, fy=0.25),
    dict(n=4, tag="SMART CASUAL", head=["КЛАССИКА СНАРУЖИ.", "ТВОЙ КЛИМАТ ВНУТРИ."], accent=1,
         sub="Стиль без компромиссов.", cta=None, swipe=True, fy=0.2),
    dict(n=5, tag="ЭКОСИСТЕМА «ЗДОРОВЬЕ ТИТАНА»", head=["ОДЕЖДА,", "КОТОРАЯ ДУМАЕТ", "О ТЕЛЕ."], accent=2,
         sub="Smart Casual · Sport · Function", cta="СКОРО. ПОДПИШИСЬ ПЕРВЫМ", swipe=False, dark=True),
]


def F(name, size):
    return ImageFont.truetype(os.path.join(INTER, name), int(size))


def find_photo(folder, stem):
    for ext in ("jpg", "jpeg", "png", "webp", "JPG", "PNG"):
        p = os.path.join(folder, f"{stem}.{ext}")
        if os.path.exists(p):
            return p
    return None


WATERMARK_TRIM = 0.07  # доля кадра снизу, которую срезаем (подпись автора фото)


def load_photo(path):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    w, h = im.size
    return im.crop((0, 0, w, int(h * (1 - WATERMARK_TRIM))))


def dark_bg(W, H):
    """Тёмный фон с тёплым свечением для финального кадра."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.32) / H) ** 2)
    g = np.clip(0.55 - r, 0, 1) ** 2 * 0.55
    a = 0.03 + g[..., None] * np.array([0.94, 0.62, 0.32])[None, None, :]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def cover_crop(img, W, H, fy=0.4):
    """Кадрирование «cover» с фокусом по вертикали fy (0 верх, 1 низ)."""
    iw, ih = img.size
    s = max(W / iw, H / ih)
    img = img.resize((int(iw * s + 0.5), int(ih * s + 0.5)), Image.LANCZOS)
    iw, ih = img.size
    x = (iw - W) // 2
    y = int((ih - H) * fy)
    return img.crop((x, y, x + W, y + H))


def grade(img):
    """Единая цветокоррекция кампании: глубже тени, чуть меньше насыщенности, тёплый свет."""
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(0.9)
    a = np.asarray(img).astype(np.float32) / 255
    a = np.clip((a - 0.02) / 0.98, 0, 1) ** 1.08
    a[..., 0] *= 1.02
    a[..., 2] *= 0.97
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def placeholder(W, H, n):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W * 0.5) / W) ** 2 + ((y - H * 0.38) / H) ** 2)
    base = np.clip(0.32 - r * 0.45, 0.03, 1)
    a = np.stack([base * 1.0, base * 0.85, base * 0.75], -1)
    im = Image.fromarray((a * 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.text((W / 2, H * 0.38), f"ФОТО {n}", font=F("Inter-Light.otf", 40), fill=(90, 86, 80), anchor="mm")
    return im


def gradients(W, H, top=0.22, bottom=0.58, strength=0.92):
    """Затемнение сверху (под логотип) и снизу (под заголовок)."""
    y = np.arange(H, dtype=np.float32) / H
    t_top = np.clip((top - y) / top, 0, 1) ** 1.6 * 0.55
    t_bot = np.clip((y - (1 - bottom)) / bottom, 0, 1) ** 1.35 * strength
    t = np.maximum(t_top, t_bot)
    a = (t * 255).astype(np.uint8)[:, None].repeat(W, 1)
    layer = Image.new("RGBA", (W, H), (6, 6, 8, 0))
    layer.putalpha(Image.fromarray(a))
    return layer


def tracked(d, xy, text, font, fill, tracking, anchor="ls"):
    x, y = xy
    total = sum(font.getlength(c) for c in text) + tracking * (len(text) - 1)
    if anchor[0] == "r":
        x -= total
    elif anchor[0] == "m":
        x -= total / 2
    for c in text:
        d.text((x, y), c, font=font, fill=fill, anchor="l" + anchor[1])
        x += font.getlength(c) + tracking
    return total


def fit_size(lines, fontname, max_w, start):
    s = start
    while s > 40:
        f = F(fontname, s)
        if max(f.getlength(l) for l in lines) <= max_w:
            return s
        s -= 2
    return s


def compose(photo, cfg, W, H, site, story=False):
    S = 2  # рендер в 2x для чистых краёв
    w, h = W * S, H * S
    if cfg.get("dark"):
        img = dark_bg(w, h)
    elif photo:
        img = cover_crop(load_photo(photo), w, h, cfg.get("fy", 0.35))
        img = grade(img)
    else:
        img = placeholder(w, h, cfg["n"])
    img = img.convert("RGBA")
    img.alpha_composite(gradients(w, h, top=0.2 if not story else 0.22, bottom=0.55 if not story else 0.5))
    d = ImageDraw.Draw(img)
    m = 64 * S
    top_y = (64 if not story else 250) * S
    acc = cfg.get("accent_col", AMBER)
    k = 1.35 if story else 1.0  # крупнее мелкий текст в сторис

    # логотип и метка линейки
    tracked(d, (m, top_y), "ТИТАН", F("InterDisplay-Bold.otf", 34 * k * S), WHITE, 0.42 * 34 * k * S, anchor="lt")
    if not story:
        f_tag = F("Inter-Medium.otf", 17 * S)
        tw = tracked(ImageDraw.Draw(Image.new("L", (1, 1))), (0, 0), cfg["tag"], f_tag, 0, 0.16 * 17 * S)
        px, py = 18 * S, 11 * S
        x1 = w - m
        x0 = x1 - tw - 2 * px
        d.rounded_rectangle([x0, top_y - 2 * S, x1, top_y + 17 * S + 2 * py - 4 * S], radius=40 * S,
                            outline=WHITE + (200,), width=max(1, int(1.4 * S)))
        tracked(d, (x0 + px, top_y + py - 2 * S), cfg["tag"], f_tag, WHITE, 0.16 * 17 * S, anchor="lt")

    # заголовок
    bottom = h - (64 if not story else 300) * S
    lines = cfg["head"]
    fname = "InterDisplay-Black.otf"
    size = fit_size(lines, fname, w - 2 * m, (104 if not story else 112) * S)
    fh = F(fname, size)
    lead = size * 0.98
    # снизу вверх: сайт / CTA / подзаголовок / заголовок
    y = bottom
    if site and (cfg.get("cta") or story):
        f_site = F("Inter-Medium.otf", 22 * k * S)
        tracked(d, (m, y), site.upper(), f_site, DIM, 0.08 * 22 * k * S, anchor="ls")
        y -= 46 * S
    if cfg.get("cta") or story:
        cta = cfg.get("cta") or "СКОРО. ПОДПИШИСЬ ПЕРВЫМ"
        f_cta = F("Inter-Bold.otf", 22 * k * S)
        cw = sum(f_cta.getlength(c) for c in cta) + 0.1 * 22 * k * S * (len(cta) - 1)
        bh = int(66 * k * S)
        d.rounded_rectangle([m, y - bh, m + cw + 64 * k * S, y], radius=bh // 2, fill=WHITE)
        tracked(d, (m + 32 * k * S, y - bh / 2), cta, f_cta, (12, 12, 14), 0.1 * 22 * k * S, anchor="lm")
        y -= bh + 34 * S
    if cfg.get("swipe") and not story:
        tracked(d, (w - m, y), "ЛИСТАЙ  →", F("Inter-SemiBold.otf", 18 * S), WHITE, 0.18 * 18 * S, anchor="rs")
    f_sub = F("Inter-Regular.otf", 30 * k * S)
    d.text((m, y), cfg["sub"], font=f_sub, fill=DIM, anchor="ls")
    y -= 30 * k * S + 36 * S
    # акцентная линия
    for i, line in enumerate(reversed(lines)):
        idx = len(lines) - 1 - i
        col = acc if idx == cfg.get("accent") else WHITE
        d.text((m - size * 0.04, y), line, font=fh, fill=col, anchor="ls")
        y -= lead
    d.rectangle([m, y + lead - size * 0.95 - 26 * S, m + 72 * S, y + lead - size * 0.95 - 20 * S], fill=acc)

    return img.convert("RGB").resize((W, H), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photos")
    ap.add_argument("out")
    ap.add_argument("--site", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for cfg in SLIDES:
        p = find_photo(a.photos, str(cfg["n"]))
        im = compose(p, cfg, 1080, 1350, a.site)
        path = os.path.join(a.out, f"titan-{cfg['n']}.png")
        im.save(path, optimize=True)
        print("saved", path, "(photo)" if p else "(placeholder)")
    p = find_photo(a.photos, "story") or find_photo(a.photos, "1")
    im = compose(p, SLIDES[0], 1080, 1920, a.site, story=True)
    path = os.path.join(a.out, "titan-story.png")
    im.save(path, optimize=True)
    print("saved", path)


if __name__ == "__main__":
    main()
