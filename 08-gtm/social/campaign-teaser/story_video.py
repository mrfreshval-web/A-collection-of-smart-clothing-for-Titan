"""Видео для сторис «Титан» 1080×1920, 15 с, 30 к/с, без звука (музыку добавить в Instagram).

Запуск: python3 story_video.py photos/ out.mp4 [--site titan.example]
Берёт photos/1…4.(jpg|png|webp). Без фото собирает черновик на заглушках.
Нужен ffmpeg в PATH. Шрифты: Inter / Inter Display (SIL OFL).
"""
import os, sys, argparse, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from compose import F, find_photo, cover_crop, grade, placeholder, gradients, tracked, WHITE, DIM, AMBER

W, H, FPS = 1080, 1920, 30

SCENES = [  # (фото, строки, индекс акцентной строки, цвет акцента, метка)
    (1, ["ТВОЙ", "КЛИМАТ."], 1, AMBER, None),
    (2, ["МИНУС 25.", "ТЕБЕ ТЕПЛО."], 1, AMBER, "SMART CASUAL"),
    (3, ["НА ПРЕДЕЛЕ.", "В СВОЕЙ ЗОНЕ."], 1, (255, 92, 64), "SPORT"),
    (4, ["ГОРЫ", "НЕ ПРОЩАЮТ."], 1, (150, 205, 255), "FUNCTION"),
]
SCENE_LEN = 2.6  # с
FINAL_LEN = 15.0 - SCENE_LEN * len(SCENES)
XFADE = 0.25


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def prep(photo, n):
    """Кадр сцены с запасом 12% под наезд камеры."""
    bw, bh = int(W * 1.12), int(H * 1.12)
    if photo:
        im = grade(cover_crop(ImageOps.exif_transpose(Image.open(photo)).convert("RGB"), bw, bh, 0.35))
    else:
        im = placeholder(bw, bh, n)
    return im


def kenburns(im, t):
    """Медленный наезд: масштаб 1.12 → 1.0 от размера кадра."""
    z = 1.0 + 0.12 * (1 - ease(t * 0.9))
    cw, ch = int(W * z), int(H * z)
    bw, bh = im.size
    x = (bw - cw) // 2
    y = int((bh - ch) * 0.45)
    return im.crop((x, y, x + cw, y + ch)).resize((W, H), Image.BILINEAR)


def text_layer(lines, accent, acc_col, tag, t):
    """Заголовок выезжает снизу построчно, метка линейки проявляется."""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    m = 72
    size = 128
    while max(F("InterDisplay-Black.otf", size).getlength(s) for s in lines) > W - 2 * m:
        size -= 4
    f = F("InterDisplay-Black.otf", size)
    base_y = H - 520
    for i, s in enumerate(lines):
        lt = ease((t - 0.12 - i * 0.1) / 0.35)
        if lt <= 0:
            continue
        off = (1 - lt) * 60
        col = acc_col if i == accent else WHITE
        a = int(255 * lt)
        y = base_y - (len(lines) - 1 - i) * size * 0.98 + off
        d.text((m - size * 0.04, y), s, font=f, fill=col + (a,), anchor="ls")
    bar = ease((t - 0.05) / 0.3)
    if bar > 0:
        top = base_y - (len(lines) - 1) * size * 0.98 - size * 0.95 - 30
        d.rectangle([m, top, m + 90 * bar, top + 8], fill=acc_col + (255,))
    if tag:
        ta = ease((t - 0.45) / 0.3)
        if ta > 0:
            tracked(d, (m, base_y + 70), tag, F("Inter-SemiBold.otf", 30), DIM + (int(255 * ta),), 5, anchor="ls")
    return L


def logo_layer(alpha):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    tracked(d, (72, 260), "ТИТАН", F("InterDisplay-Bold.otf", 44), WHITE + (int(255 * alpha),), 18, anchor="lt")
    return L


def final_frame(t, site):
    """Финал: логотип по буквам, слоган, «Скоро», кнопка."""
    img = Image.new("RGB", (W, H), (7, 7, 9))
    y_, x_ = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x_ - W / 2) / W) ** 2 + ((y_ - H * 0.45) / H) ** 2)
    glow = np.clip(0.5 - r, 0, 1) ** 2 * 0.5 * ease(t / 0.6)
    a = np.asarray(img).astype(np.float32) / 255
    a = a + glow[..., None] * np.array([0.94, 0.66, 0.36])[None, None, :]
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    word = "ТИТАН"
    f = F("InterDisplay-Black.otf", 200)
    tr = 30
    total = sum(f.getlength(c) for c in word) + tr * (len(word) - 1)
    x = (W - total) / 2
    for i, c in enumerate(word):
        lt = ease((t - i * 0.08) / 0.4)
        if lt > 0:
            d.text((x, H * 0.45 + (1 - lt) * 40), c, font=f, fill=WHITE + (int(255 * lt),), anchor="ls")
        x += f.getlength(c) + tr
    s1 = ease((t - 0.7) / 0.4)
    if s1 > 0:
        tracked(d, (W / 2, H * 0.45 + 110), "ТВОЙ КЛИМАТ. ВЕЗДЕ.", F("Inter-SemiBold.otf", 46), AMBER + (int(255 * s1),), 4, anchor="ms")
    s2 = ease((t - 1.1) / 0.4)
    if s2 > 0:
        d.text((W / 2, H * 0.45 + 190), "Одежда, которая думает о теле.", font=F("Inter-Regular.otf", 40), fill=DIM + (int(255 * s2),), anchor="ms")
    s3 = ease((t - 1.5) / 0.4)
    if s3 > 0:
        cta = "СКОРО. ПОДПИШИСЬ ПЕРВЫМ"
        fc = F("Inter-Bold.otf", 32)
        cw = fc.getlength(cta) + 3 * (len(cta) - 1)
        bw, bh = cw + 96, 92
        x0, y0 = (W - bw) / 2, H - 520 + (1 - s3) * 30
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=bh // 2, fill=WHITE + (int(255 * s3),))
        tracked(d, (W / 2, y0 + bh / 2), cta, fc, (12, 12, 14, int(255 * s3)), 3, anchor="mm")
        if site:
            tracked(d, (W / 2, y0 + bh + 70), site.upper(), F("Inter-Medium.otf", 32), DIM + (int(255 * s3),), 3, anchor="ms")
    return img.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photos")
    ap.add_argument("out")
    ap.add_argument("--site", default="")
    a = ap.parse_args()
    bases = [prep(find_photo(a.photos, str(n)), n) for (n, *_r) in SCENES]
    grad = gradients(W, H, top=0.22, bottom=0.5)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                             "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out],
                            stdin=subprocess.PIPE)

    def scene_frame(i, ts):
        n, lines, acc, col, tag = SCENES[i]
        fr = kenburns(bases[i], ts / SCENE_LEN).convert("RGBA")
        fr.alpha_composite(grad)
        fr.alpha_composite(text_layer(lines, acc, col, tag, ts))
        fr.alpha_composite(logo_layer(1.0))
        return fr.convert("RGB")

    total = int(15.0 * FPS)
    for k in range(total):
        t = k / FPS
        si = int(t // SCENE_LEN)
        if si < len(SCENES):
            ts = t - si * SCENE_LEN
            fr = scene_frame(si, ts)
            # быстрая перекрёстная склейка в начало следующей сцены
            if ts > SCENE_LEN - XFADE:
                nxt = scene_frame(si + 1, 0) if si + 1 < len(SCENES) else final_frame(0, a.site)
                fr = Image.blend(fr, nxt, (ts - (SCENE_LEN - XFADE)) / XFADE)
        else:
            fr = final_frame(t - SCENE_LEN * len(SCENES), a.site)
        proc.stdin.write(fr.tobytes())
    proc.stdin.close()
    proc.wait()
    print("saved", a.out)


if __name__ == "__main__":
    main()
