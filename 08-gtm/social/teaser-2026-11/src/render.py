"""Рендер тизер-визуалов «Титан» для Instagram (философия «Изотерма»).

Запуск: python3 render.py <папка_вывода>
Зависимости: numpy, scipy, Pillow. Шрифты: Inter (OFL), Geist Mono (OFL).
"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import distance_transform_edt, gaussian_filter

SS = 2  # суперсэмплинг
SITE = os.environ.get("TITAN_SITE", "").strip()  # адрес сайта, печатается на финальном слайде и в сторис
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)

FONT_DIRS = [
    "/usr/share/fonts/opentype/inter/",
    os.path.join(os.path.dirname(__file__), "fonts/"),
]


def font(name, size):
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, int(size * SS))
    raise FileNotFoundError(name)


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0


# ---------------------------------------------------------------- силуэты
def mirror(pts):
    return pts + [(-x, y) for (x, y) in reversed(pts)]


PARKA = {
    "torso": mirror([(0, 0.125), (0.05, 0.13), (0.135, 0.168), (0.172, 0.2), (0.168, 0.29),
                     (0.15, 0.43), (0.152, 0.58), (0.162, 0.70)]),
    "arm_r": [(0.135, 0.168), (0.178, 0.186), (0.2, 0.225), (0.212, 0.33), (0.226, 0.46),
              (0.232, 0.565), (0.226, 0.6), (0.218, 0.625), (0.2, 0.636), (0.186, 0.622),
              (0.183, 0.6), (0.188, 0.565), (0.178, 0.45), (0.168, 0.31), (0.16, 0.22)],
    "leg_r": [(0.012, 0.69), (0.082, 0.69), (0.078, 0.82), (0.072, 0.95), (0.092, 0.982),
              (0.094, 1.0), (0.018, 1.0), (0.02, 0.95), (0.016, 0.82)],
    "hood": (0.0, 0.074, 0.063, 0.078),
    # конструктивные линии одежды (тонко): (тип, данные)
    "seams": [("ellipse", (0.0, 0.083, 0.036, 0.048)),            # проём капюшона
              ("line", [(0, 0.135), (0, 0.69)]),                     # центральная застёжка
              ("line", [(-0.151, 0.45), (0.151, 0.45)]),             # линия талии (кулиска)
              ("line", [(0.188, 0.565), (0.232, 0.565)]),            # манжета
              ("line", [(-0.188, 0.565), (-0.232, 0.565)]),
              ("line", [(-0.125, 0.255), (-0.06, 0.255)]),           # клапан кармана груди
              ("line", [(0.07, 0.95), (0.022, 0.95)]),               # верх ботинка
              ("line", [(-0.07, 0.95), (-0.022, 0.95)])],
}

ATHLETE = {
    "torso": mirror([(0, 0.155), (0.035, 0.158), (0.05, 0.175), (0.15, 0.2), (0.178, 0.225),
                     (0.17, 0.30), (0.135, 0.40), (0.11, 0.5), (0.115, 0.56)]),
    "arm_r": [(0.15, 0.2), (0.19, 0.212), (0.212, 0.25), (0.228, 0.33), (0.245, 0.42),
              (0.255, 0.5), (0.25, 0.53), (0.232, 0.545), (0.22, 0.52), (0.21, 0.43),
              (0.19, 0.35), (0.175, 0.29)],
    "leg_r": [(0.0, 0.56), (0.118, 0.56), (0.128, 0.66), (0.115, 0.79), (0.11, 0.94),
              (0.13, 0.985), (0.13, 1.0), (0.05, 1.0), (0.052, 0.94), (0.045, 0.79),
              (0.03, 0.66), (0.0, 0.64)],
    "hood": (0.0, 0.08, 0.044, 0.058),
    "seams": [("line", [(-0.047, 0.178), (0, 0.205), (0.047, 0.178)]),   # горловина
              ("line", [(-0.112, 0.5), (0.112, 0.5)]),                    # пояс
              ("line", [(0.19, 0.34), (0.226, 0.33)]),                    # край рукава
              ("line", [(-0.19, 0.34), (-0.226, 0.33)]),
              ("line", [(0.123, 0.70), (0.035, 0.70)]),                   # край шорт
              ("line", [(-0.123, 0.70), (-0.035, 0.70)])],
}


def silhouette_mask(shape, W, H, cx, top, h):
    """Маска силуэта (float 0..1) в суперсэмплинг-разрешении."""
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    tr = lambda p: (cx + p[0] * h, top + p[1] * h)
    d.polygon([tr(p) for p in shape["torso"]], fill=255)
    for key in ("arm_r", "leg_r"):
        pts = shape[key]
        d.polygon([tr(p) for p in pts], fill=255)
        d.polygon([tr((-x, y)) for (x, y) in pts], fill=255)
    ex, ey, rx, ry = shape["hood"]
    c = tr((ex, ey))
    d.ellipse([c[0] - rx * h, c[1] - ry * h, c[0] + rx * h, c[1] + ry * h], fill=255)
    m = np.asarray(img, dtype=np.float32) / 255.0
    # скругление углов: размытие + порог, как у мягкой ткани
    m = gaussian_filter(m, sigma=h * 0.006)
    return (m > 0.5).astype(np.float32)


def draw_seams(base, shape, cx, top, h, color, alpha):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tr = lambda p: (cx + p[0] * h, top + p[1] * h)
    col = tuple(int(c * 255) for c in color) + (int(alpha * 255),)
    w = max(1, int(1.1 * SS))
    for kind, data in shape["seams"]:
        if kind == "line":
            d.line([tr(p) for p in data], fill=col, width=w)
        else:
            ex, ey, rx, ry = data
            c = tr((ex, ey))
            d.ellipse([c[0] - rx * h, c[1] - ry * h, c[0] + rx * h, c[1] + ry * h], outline=col, width=w)
    base.alpha_composite(layer)


# ---------------------------------------------------------------- шум и поле
def smooth_noise(W, H, scale, seed, octaves=3):
    rng = np.random.default_rng(seed)
    acc = np.zeros((H, W), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gw, gh = max(2, int(W / scale) + 2), max(2, int(H / scale) + 2)
        g = rng.standard_normal((gh, gw)).astype(np.float32)
        im = Image.fromarray(g, mode="F").resize((W, H), Image.BICUBIC)
        acc += amp * np.asarray(im)
        tot += amp
        amp *= 0.5
        scale /= 2.0
    return acc / tot


def isolines(u, width_px, grad=None):
    """Антиалиасные изолинии поля u на целых значениях."""
    if grad is None:
        gy, gx = np.gradient(u)
        grad = np.sqrt(gx * gx + gy * gy) + 1e-6
    f = np.abs(u - np.round(u))
    return np.clip(1.0 - f / (grad * width_px * 0.5), 0, 1), grad


def vignette(W, H, c_in, c_out, cx=0.5, cy=0.45, power=1.6):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x / W - cx) * 1.0) ** 2 + ((y / H - cy) * H / W * 0.8) ** 2)
    t = np.clip(r / 0.85, 0, 1) ** power
    return c_in[None, None, :] * (1 - t[..., None]) + c_out[None, None, :] * t[..., None]


def lerp(a, b, t):
    return a[None, None, :] * (1 - t[..., None]) + b[None, None, :] * t[..., None]


def field_render(W, H, src_mask, pal, *, spacing=26.0, growth=1.0, warp=0.0, warp_scale=380,
                 seed=1, wind=0.0, pulse=0.0, terrain=0.0, line_w=1.25, major_every=5,
                 fade_far=1.0, inner_fill=None, glow=1.0, bg=None):
    """Главный рендер: тёмный фон, изотермы от силуэта, тёплое ядро, холодная периферия."""
    inside = src_mask > 0.5
    d = distance_transform_edt(~inside).astype(np.float32)  # px (SS)
    d_ss = d / SS
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)

    # искажение поля: ветер / шум / рельеф растут с удалением от тела
    dd = d_ss.copy()
    if wind:
        # среда давит слева: линии сжаты с наветренной стороны
        cxm = (x * src_mask).sum() / max(src_mask.sum(), 1)
        side = np.tanh((x - cxm) / (W * 0.25))
        dd = dd * (1.0 + wind * (-side))
    if warp:
        n = smooth_noise(W, H, warp_scale * SS, seed)
        k = np.clip(d_ss / 260.0, 0, 1) ** 1.3
        dd = dd + warp * n * k * 60.0
    if terrain:
        n1 = smooth_noise(W, H, 620 * SS, seed + 7, octaves=4)
        ridge = 1.0 - np.abs(n1)  # «хребты»
        k = np.clip(d_ss / 180.0, 0, 1) ** 1.6
        dd = dd + terrain * (ridge * 140.0 + n1 * 60.0) * k

    # шаг линий растёт с удалением (поле «рассеивается»)
    u = (np.maximum(dd, 0) / spacing) ** (1.0 / growth) * (1.0 if growth == 1 else spacing ** (1 / growth - 1) * 1.0)
    if growth != 1.0:
        u = (np.maximum(dd, 0) / spacing) ** (1.0 / growth)
    if pulse:
        # пульсовые волны: пакеты яркости, расходящиеся от тела
        pw = 0.5 + 0.5 * np.cos(2 * np.pi * (u / 7.0))
        pw = pw ** 3
    else:
        pw = None

    lines, grad = isolines(u, line_w * SS)
    major, _ = isolines(u / major_every, line_w * 1.9 * SS, grad=grad / major_every)

    t = np.clip(d_ss / (0.55 * max(W, H) / SS), 0, 1)  # 0 у тела → 1 далеко
    tc = t ** 0.55
    col = lerp(pal["warm"], pal["mid"], np.clip(tc * 2, 0, 1))
    col = np.where((tc > 0.5)[..., None], lerp(pal["mid"], pal["cold"], np.clip(tc * 2 - 1, 0, 1)), col)

    a = 0.55 * (1 - t) ** (1.2 * fade_far) + 0.07
    a_lines = lines * a
    if pw is not None:
        a_lines = a_lines * (0.35 + 0.65 * pw) + lines * pulse * pw * 0.25 * (1 - t)
    a_major = major * np.clip(a * 1.25 + 0.05, 0, 1)
    A = np.clip(np.maximum(a_lines, a_major), 0, 1)
    A[inside] = 0

    if bg is None:
        bg = vignette(W, H, pal["bg_in"], pal["bg_out"])
    img = bg.copy()

    # мягкое тепловое свечение вокруг тела
    g = np.exp(-d_ss / 70.0) * 0.22 * glow + np.exp(-d_ss / 16.0) * 0.18 * glow
    img = img + pal["warm"][None, None, :] * g[..., None] * (~inside)[..., None]

    img = img * (1 - A[..., None]) + col * A[..., None]

    # тело: глубокий монолит с едва заметным внутренним объёмом
    di = distance_transform_edt(inside).astype(np.float32) / SS
    body = pal["body"][None, None, :] + pal["warm"][None, None, :] * (np.exp(-di / 10.0) * 0.10)[..., None]
    if inner_fill is not None:
        body = inner_fill(body, di, x, y)
    img = np.where(inside[..., None], body, img)

    # контур: тонкий тёплый край
    rim = np.clip(1.0 - np.abs(d_ss - 0.0) / 1.4, 0, 1) * (~inside) + np.clip(1.0 - di / 1.2, 0, 1) * inside
    img = img * (1 - rim[..., None] * 0.9) + pal["rim"][None, None, :] * rim[..., None] * 0.9
    return np.clip(img, 0, 1), d_ss


def finish(arr, grain=0.018, seed=0):
    """Снижение разрешения, зерно, возврат PIL RGBA (в SS-разрешении для текста)."""
    rng = np.random.default_rng(seed)
    n = rng.standard_normal(arr.shape[:2]).astype(np.float32)
    n = gaussian_filter(n, 0.6) * grain * 2.2
    arr = np.clip(arr + n[..., None], 0, 1)
    return Image.fromarray((arr * 255).astype(np.uint8), "RGB").convert("RGBA")


def downscale_save(img, path):
    W, H = img.size
    img.convert("RGB").resize((W // SS, H // SS), Image.LANCZOS).save(path, optimize=True)
    print("saved", path)


# ---------------------------------------------------------------- типографика
class Typo:
    def __init__(self, img):
        self.img = img
        self.d = ImageDraw.Draw(img)

    def text(self, xy, s, f, color, alpha=1.0, tracking=0.0, anchor="la", spacing=1.18):
        x, y = xy[0] * SS, xy[1] * SS
        col = tuple(int(c * 255) for c in color) + (int(alpha * 255),)
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        lines = s.split("\n")
        asc, desc = f.getmetrics()
        lh = (asc + desc) * spacing
        for i, line in enumerate(lines):
            ly = y + i * lh
            if tracking == 0:
                d.text((x, ly), line, font=f, fill=col, anchor=anchor)
            else:
                tw = self.width(line, f, tracking)
                if anchor[0] == "m":
                    cx = x - tw / 2
                elif anchor[0] == "r":
                    cx = x - tw
                else:
                    cx = x
                a = "l" + anchor[1]
                for ch in line:
                    d.text((cx, ly), ch, font=f, fill=col, anchor=a)
                    cx += f.getlength(ch) + tracking * f.size
        self.img.alpha_composite(layer)

    def width(self, line, f, tracking):
        return sum(f.getlength(ch) for ch in line) + tracking * f.size * max(len(line) - 1, 0)

    def rule(self, x0, y0, x1, y1, color, alpha=1.0, w=1.0):
        col = tuple(int(c * 255) for c in color) + (int(alpha * 255),)
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).line([(x0 * SS, y0 * SS), (x1 * SS, y1 * SS)], fill=col, width=max(1, int(w * SS)))
        self.img.alpha_composite(layer)

    def ticks(self, x, y0, y1, n, color, alpha, length=6, major=5):
        for i in range(n + 1):
            yy = y0 + (y1 - y0) * i / n
            L = length * (1.8 if i % major == 0 else 1)
            self.rule(x, yy, x + L, yy, color, alpha * (1 if i % major == 0 else 0.6), 1)

    def crosshair(self, x, y, color, alpha, r=7):
        self.rule(x - r, y, x + r, y, color, alpha)
        self.rule(x, y - r, x, y + r, color, alpha)


def darken_band(img, y0, y1, strength, W, H, top=False):
    """Мягкое затемнение под текстом (градиент), чтобы текст читался."""
    y = np.arange(H, dtype=np.float32)[:, None] / SS
    if top:
        t = np.clip((y1 - y) / (y1 - y0), 0, 1)
    else:
        t = np.clip((y - y0) / (y1 - y0), 0, 1)
    t = t ** 1.5 * strength
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    arr = arr * (1 - t[..., None] * np.ones((1, W, 1)))
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")


# ---------------------------------------------------------------- палитры
PAL_CORE = dict(bg_in=hexc("0c0f13"), bg_out=hexc("040506"), body=hexc("050607"),
                warm=hexc("e9a25c"), mid=hexc("9a7a66"), cold=hexc("4d6276"), rim=hexc("f3c48c"))
PAL_CITY = dict(bg_in=hexc("0b1016"), bg_out=hexc("030507"), body=hexc("05070a"),
                warm=hexc("eaa863"), mid=hexc("8aa3bd"), cold=hexc("7fb8ee"), rim=hexc("f5cf9c"))
PAL_SPORT = dict(bg_in=hexc("130b0b"), bg_out=hexc("050303"), body=hexc("070404"),
                 warm=hexc("ff5a3c"), mid=hexc("c2343a"), cold=hexc("5e2a33"), rim=hexc("ff8a62"))
PAL_ALPS = dict(bg_in=hexc("0d1217"), bg_out=hexc("040607"), body=hexc("050708"),
                warm=hexc("f0d2a8"), mid=hexc("b9cbd8"), cold=hexc("e6eff5"), rim=hexc("ffffff"))

INK = hexc("ece7df")      # основной светлый текст (тёплый бумажный)
INK_DIM = hexc("8f8a84")

F_HEAD = "Inter-ExtraLight.otf"
F_HEAD_B = "Inter-Light.otf"
F_MARK = "InterDisplay-Thin.otf"
F_MONO = "GeistMono-Regular.ttf"


def frame_marks(T, W, H, pal, sheet, total, title):
    """Служебная разметка «атласа»: шапка, номер листа, угловые метки."""
    m = 56
    f_mono = font(F_MONO, 15)
    T.text((m, m), "ТИТАН", font(F_MONO, 15), INK, 0.92, tracking=0.42)
    T.text((W - m, m), f"{sheet:02d} / {total:02d}", f_mono, INK_DIM, 0.9, tracking=0.12, anchor="ra")
    T.text((m, m + 26), title, f_mono, INK_DIM, 0.85, tracking=0.18)
    T.rule(m, m + 58, W - m, m + 58, INK, 0.16)
    for (cx, cy) in [(m, H - m), (W - m, H - m)]:
        pass


# ---------------------------------------------------------------- слайды
def slide_cover(W=1080, H=1350, name="01-cover.png", sheet=1, total=5):
    w, h = W * SS, H * SS
    fh = 0.585 * H * SS
    cx, top = w / 2, 0.125 * H * SS
    mask = silhouette_mask(PARKA, w, h, cx, top, fh)
    arr, _ = field_render(w, h, mask, PAL_CORE, spacing=13.0, growth=1.18, warp=0.55, seed=3)
    img = finish(arr, seed=11)
    draw_seams(img, PARKA, cx, top, fh, PAL_CORE["rim"], 0.28)
    img = darken_band(img, 840, 1350, 0.82, w, h)
    T = Typo(img)
    frame_marks(T, W, H, PAL_CORE, sheet, total, "ЛИСТ I · ЛИЧНЫЙ КЛИМАТ")
    # шкала-легенда справа
    lx, ly0, ly1 = W - 70, 260, 700
    T.ticks(lx, ly0, ly1, 20, INK, 0.35, length=5)
    T.text((lx - 10, ly0 - 4), "+36,6", font(F_MONO, 13), PAL_CORE["rim"], 0.95, anchor="rm")
    T.text((lx - 10, ly1 + 4), "−25", font(F_MONO, 13), PAL_CORE["cold"] * 1.6, 0.95, anchor="rm")
    T.text((lx - 10, (ly0 + ly1) / 2), "°C", font(F_MONO, 13), INK_DIM, 0.8, anchor="rm")
    T.crosshair(W / 2, 0.125 * H - 22, INK, 0.35)
    # заголовок
    T.text((56, 992), "Твоё тело —\nглавный проект\nтвоей жизни.", font(F_HEAD, 66), INK, 1.0, spacing=1.06)
    T.rule(56, 1258, 300, 1258, PAL_CORE["warm"], 0.9, 1.2)
    T.text((56, 1278), "ОДЕЖДА, КОТОРАЯ ДУМАЕТ О ТЕЛЕ", font(F_MONO, 13), INK_DIM, 0.95, tracking=0.2)
    T.text((W - 56, 1278), "СКОРО", font(F_MONO, 13), PAL_CORE["rim"], 0.95, tracking=0.3, anchor="ra")
    downscale_save(img, os.path.join(OUT, name))


def city_bg(W, H, pal, seed=5):
    """Фон: еле видимый ритм вертикалей ночного города у нижней кромки."""
    bg = vignette(W, H, pal["bg_in"], pal["bg_out"])
    rng = np.random.default_rng(seed)
    layer = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(layer)
    x = 0
    while x < W:
        bw = rng.integers(36, 120) * SS / 2
        bh = rng.integers(140, 520) * SS / 2
        d.rectangle([x, H * 0.70 - bh, x + bw - 6 * SS, H * 0.70], fill=int(rng.integers(10, 26)))
        x += bw
    m = np.asarray(layer, np.float32) / 255.0
    return np.clip(bg + m[..., None] * pal["mid"][None, None, :] * 0.5, 0, 1)


def slide_city(W=1080, H=1350, name="02-smart-casual.png", sheet=2, total=5):
    w, h = W * SS, H * SS
    fh = 0.56 * H * SS
    cx, top = w * 0.5, 0.15 * H * SS
    mask = silhouette_mask(PARKA, w, h, cx, top, fh)
    arr, _ = field_render(w, h, mask, PAL_CITY, spacing=12.0, growth=1.12, warp=0.35, seed=8,
                          wind=0.38, bg=city_bg(w, h, PAL_CITY))
    img = finish(arr, seed=12)
    draw_seams(img, PARKA, cx, top, fh, PAL_CITY["rim"], 0.26)
    img = darken_band(img, 860, 1350, 0.84, w, h)
    T = Typo(img)
    frame_marks(T, W, H, PAL_CITY, sheet, total, "ЛИНЕЙКА · SMART CASUAL · ГОРОД")
    # метка ветра слева
    for i in range(5):
        yy = 330 + i * 26
        T.rule(56, yy, 56 + 64 - i * 8, yy, PAL_CITY["cold"], 0.55 - i * 0.07)
    T.text((56, 470), "ВЕТЕР\n12 М/С", font(F_MONO, 13), INK_DIM, 0.85, tracking=0.16)
    T.text((W - 56, 330), "−25 °C", font(F_MONO, 15), PAL_CITY["cold"], 0.95, tracking=0.1, anchor="ra")
    T.text((W - 56, 356), "СНАРУЖИ", font(F_MONO, 12), INK_DIM, 0.8, tracking=0.2, anchor="ra")
    T.text((56, 992), "−25 снаружи.\nТвой климат — внутри.", font(F_HEAD, 62), INK, 1.0, spacing=1.08)
    T.rule(56, 1258, 300, 1258, PAL_CITY["cold"], 0.9, 1.2)
    T.text((56, 1278), "ВЕРХНЯЯ ОДЕЖДА · ОБУВЬ · АКСЕССУАРЫ", font(F_MONO, 13), INK_DIM, 0.95, tracking=0.2)
    T.text((W - 56, 1278), "−25…+15 °C", font(F_MONO, 13), PAL_CITY["cold"], 0.95, tracking=0.12, anchor="ra")
    downscale_save(img, os.path.join(OUT, name))


def slide_sport(W=1080, H=1350, name="03-sport.png", sheet=3, total=5):
    w, h = W * SS, H * SS
    fh = 0.58 * H * SS
    cx, top = w * 0.5, 0.135 * H * SS
    mask = silhouette_mask(ATHLETE, w, h, cx, top, fh)
    arr, _ = field_render(w, h, mask, PAL_SPORT, spacing=10.0, growth=1.08, warp=0.18, seed=4,
                          pulse=1.0, glow=1.3)
    img = finish(arr, seed=13)
    draw_seams(img, ATHLETE, cx, top, fh, PAL_SPORT["rim"], 0.3)
    img = darken_band(img, 860, 1350, 0.85, w, h)
    T = Typo(img)
    frame_marks(T, W, H, PAL_SPORT, sheet, total, "ЛИНЕЙКА · SPORT · ЗАЛ")
    # пульсовая трасса — абстрактный ритм, без указания на технику измерения
    pts = []
    base = 300
    for i in range(0, 241):
        xx = 56 + i * 0.9
        ph = (i % 60)
        yy = base
        if ph == 20: yy = base - 6
        if ph == 23: yy = base + 8
        if ph == 25: yy = base - 34
        if ph == 27: yy = base + 14
        if ph == 30: yy = base - 3
        pts.append((xx, yy))
    for a, b in zip(pts[:-1], pts[1:]):
        T.rule(a[0], a[1], b[0], b[1], PAL_SPORT["warm"], 0.85, 1.1)
    T.text((56, 340), "ПУЛЬСОВАЯ\nЗОНА 5", font(F_MONO, 13), INK_DIM, 0.85, tracking=0.16)
    T.text((W - 56, 286), "182", font(F_HEAD_B, 40), PAL_SPORT["rim"], 0.95, anchor="ra")
    T.text((W - 56, 330), "УД/МИН", font(F_MONO, 12), INK_DIM, 0.8, tracking=0.2, anchor="ra")
    T.text((56, 992), "На пределе пульса.\nТело — в своей зоне.", font(F_HEAD, 62), INK, 1.0, spacing=1.08)
    T.rule(56, 1258, 300, 1258, PAL_SPORT["warm"], 0.9, 1.2)
    T.text((56, 1278), "КРОССФИТ · ФУНКЦИОНАЛЬНЫЙ ТРЕНИНГ", font(F_MONO, 13), INK_DIM, 0.95, tracking=0.2)
    T.text((W - 56, 1278), "SPORT", font(F_MONO, 13), PAL_SPORT["rim"], 0.95, tracking=0.3, anchor="ra")
    downscale_save(img, os.path.join(OUT, name))


def slide_alps(W=1080, H=1350, name="04-function.png", sheet=4, total=5):
    w, h = W * SS, H * SS
    fh = 0.50 * H * SS
    cx, top = w * 0.5, 0.20 * H * SS
    mask = silhouette_mask(PARKA, w, h, cx, top, fh)
    arr, _ = field_render(w, h, mask, PAL_ALPS, spacing=11.0, growth=1.1, terrain=1.0, warp=0.2,
                          seed=21, fade_far=0.6, glow=0.8)
    img = finish(arr, seed=14)
    draw_seams(img, PARKA, cx, top, fh, PAL_ALPS["rim"], 0.24)
    img = darken_band(img, 860, 1350, 0.84, w, h)
    T = Typo(img)
    frame_marks(T, W, H, PAL_ALPS, sheet, total, "ЛИНЕЙКА · FUNCTION · ЭКСТРИМ")
    T.text((56, 300), "3 200 М", font(F_HEAD_B, 40), PAL_ALPS["rim"], 0.95)
    T.text((56, 348), "НАД УРОВНЕМ МОРЯ", font(F_MONO, 12), INK_DIM, 0.8, tracking=0.2)
    T.text((W - 56, 300), "N 45°55′", font(F_MONO, 13), INK_DIM, 0.85, tracking=0.1, anchor="ra")
    T.text((W - 56, 322), "E 06°52′", font(F_MONO, 13), INK_DIM, 0.85, tracking=0.1, anchor="ra")
    T.text((56, 992), "Высота. Ветер. Холод.\nТы — в своём климате.", font(F_HEAD, 62), INK, 1.0, spacing=1.08)
    T.rule(56, 1258, 300, 1258, PAL_ALPS["cold"], 0.9, 1.2)
    T.text((56, 1278), "ЛЫЖИ · СНОУБОРД · ГОРЫ", font(F_MONO, 13), INK_DIM, 0.95, tracking=0.2)
    T.text((W - 56, 1278), "FUNCTION", font(F_MONO, 13), PAL_ALPS["rim"], 0.95, tracking=0.3, anchor="ra")
    downscale_save(img, os.path.join(OUT, name))


def wordmark_mask(w, h, text, f, cy, tracking):
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    tw = sum(f.getlength(c) for c in text) + tracking * f.size * (len(text) - 1)
    x = (w - tw) / 2
    for c in text:
        d.text((x, cy), c, font=f, fill=255, anchor="lm")
        x += f.getlength(c) + tracking * f.size
    return (np.asarray(img, np.float32) / 255.0 > 0.5).astype(np.float32)


def slide_final(W=1080, H=1350, name="05-soon.png", sheet=5, total=5):
    w, h = W * SS, H * SS
    f_mark = font("InterDisplay-Light.otf", 168)
    cy = 0.47 * h
    mask = wordmark_mask(w, h, "ТИТАН", f_mark, cy, 0.16)
    arr, _ = field_render(w, h, mask, PAL_CORE, spacing=11.0, growth=1.15, warp=0.5, seed=31, glow=0.7)
    img = finish(arr, seed=15)
    T = Typo(img)
    frame_marks(T, W, H, PAL_CORE, sheet, total, "ЛИСТ V · ЭКОСИСТЕМА «ЗДОРОВЬЕ ТИТАНА»" if SITE else "ЛИСТ V · СКОРО")
    T.text((W / 2, 0.47 * H + 150), "Скоро.", font(F_HEAD, 54), INK, 1.0, anchor="ma")
    img2 = darken_band(img, 1080, 1350, 0.8, w, h)
    T = Typo(img2)
    T.text((W / 2, 1150), "Город  ·  Зал  ·  Горы", font(F_HEAD_B, 26), INK, 0.92, anchor="ma")
    T.rule(W / 2 - 120, 1214, W / 2 + 120, 1214, PAL_CORE["warm"], 0.9, 1.2)
    T.text((W / 2, 1236), "ПОДПИШИСЬ, ЧТОБЫ БЫТЬ СРЕДИ ПЕРВЫХ", font(F_MONO, 13), INK_DIM, 0.95, tracking=0.2, anchor="ma")
    if SITE:
        T.text((W / 2, 1266), SITE.upper(), font(F_MONO, 15), PAL_CORE["rim"], 0.95, tracking=0.16, anchor="ma")
    else:
        T.text((W / 2, 1268), "ЭКОСИСТЕМА «ЗДОРОВЬЕ ТИТАНА»", font(F_MONO, 12), PAL_CORE["rim"], 0.85, tracking=0.2, anchor="ma")
    downscale_save(img2, os.path.join(OUT, name))


def story(W=1080, H=1920, name="story-1080x1920.png"):
    w, h = W * SS, H * SS
    fh = 0.50 * H * SS
    cx, top = w / 2, 0.205 * H * SS
    mask = silhouette_mask(PARKA, w, h, cx, top, fh)
    arr, _ = field_render(w, h, mask, PAL_CORE, spacing=13.0, growth=1.18, warp=0.6, seed=3)
    img = finish(arr, seed=16)
    draw_seams(img, PARKA, cx, top, fh, PAL_CORE["rim"], 0.28)
    img = darken_band(img, 0, 330, 0.85, w, h, top=True)
    img = darken_band(img, 1320, 1920, 0.86, w, h)
    T = Typo(img)
    m = 64
    # верхняя зона IG (~0–220px) остаётся под интерфейсом; текст ниже
    T.text((W / 2, 236), "Твоё тело — главный проект твоей жизни.", font(F_HEAD_B, 36), INK, 1.0, anchor="ma")
    T.rule(W / 2 - 40, 300, W / 2 + 40, 300, PAL_CORE["warm"], 0.9, 1.2)
    T.text((m, 1290), "−25", font(F_MONO, 14), PAL_CORE["cold"] * 1.6, 0.95)
    T.text((W - m, 1290), "+36,6 °C", font(F_MONO, 14), PAL_CORE["rim"], 0.95, anchor="ra")
    T.text((W / 2, 1390), "ТИТАН", font("InterDisplay-Thin.otf", 150), INK, 1.0, tracking=0.16, anchor="ma")
    T.text((W / 2, 1572), "Одежда, которая думает о теле. Скоро.", font(F_HEAD_B, 30), INK, 0.95, anchor="ma")
    T.text((W / 2, 1626), "ГОРОД · ЗАЛ · ГОРЫ", font(F_MONO, 14), INK_DIM, 0.95, tracking=0.3, anchor="ma")
    if SITE:
        T.text((W / 2, 1660), SITE.upper(), font(F_MONO, 16), PAL_CORE["rim"], 0.95, tracking=0.16, anchor="ma")
    downscale_save(img, os.path.join(OUT, name))


if __name__ == "__main__":
    which = sys.argv[2:] or ["cover", "city", "sport", "alps", "final", "story"]
    for k in which:
        {"cover": slide_cover, "city": slide_city, "sport": slide_sport, "alps": slide_alps,
         "final": slide_final, "story": story}[k]()
