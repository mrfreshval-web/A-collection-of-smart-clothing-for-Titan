"""Генератор схем зон для 05-design (SVG, без зависимостей).

Запуск: python3 zones.py <папка_вывода>
Схемы условные: пропорции фигуры и размеры зон — иллюстрация к тексту
02-platform-construction.md, а не лекала.
"""
import sys
from pathlib import Path

W, H = 1380, 900
BG, INK, DIM, LINE = "#0C0F13", "#ECE7DF", "#8F8A84", "#2A3038"
HEAT, VENT, PORT, SENS, LIGHT, NOGO = "#E9A25C", "#7FB8EE", "#F3C48C", "#B9CBD8", "#FF5A3C", "#5E2A33"
FONT = "Geist Mono, ui-monospace, monospace"


def body(cx, top, sleeves=True, legs=True):
    """Условный силуэт: голова, торс, руки, ноги. Возвращает SVG-фрагмент."""
    s = []
    s.append(f'<ellipse cx="{cx}" cy="{top+38}" rx="30" ry="38" fill="#14181E" stroke="{LINE}" stroke-width="2"/>')
    t = top + 84
    torso = (f"M{cx-95},{t+10} Q{cx-100},{t} {cx-60},{t-6} L{cx+60},{t-6} Q{cx+100},{t} {cx+95},{t+10} "
             f"L{cx+85},{t+300} L{cx-85},{t+300} Z")
    s.append(f'<path d="{torso}" fill="#14181E" stroke="{LINE}" stroke-width="2"/>')
    if sleeves:
        for sx in (-1, 1):
            x0 = cx + sx * 95
            arm = (f"M{x0},{t+10} L{x0+sx*40},{t+40} L{x0+sx*62},{t+290} L{x0+sx*30},{t+295} "
                   f"L{x0+sx*8},{t+90} Z")
            s.append(f'<path d="{arm}" fill="#14181E" stroke="{LINE}" stroke-width="2"/>')
            s.append(f'<ellipse cx="{x0+sx*46}" cy="{t+315}" rx="17" ry="24" fill="#14181E" stroke="{LINE}" stroke-width="2"/>')
    if legs:
        for sx in (-1, 1):
            leg = (f"M{cx+sx*85},{t+300} L{cx+sx*80},{t+560} L{cx+sx*20},{t+560} L{cx+sx*6},{t+300} Z")
            s.append(f'<path d="{leg}" fill="#101318" stroke="{LINE}" stroke-width="2"/>')
            s.append(f'<rect x="{min(cx+sx*80, cx+sx*20)}" y="{t+560}" width="60" height="22" rx="8" fill="#101318" stroke="{LINE}" stroke-width="2"/>')
    s.append(f'<line x1="{cx}" y1="{t-6}" x2="{cx}" y2="{t+300}" stroke="{LINE}" stroke-dasharray="4 6"/>')
    return "\n".join(s), t


def zone(x, y, w, h, color, code, kind="fill", r=8):
    if kind == "fill":
        rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}" fill-opacity="0.38" stroke="{color}" stroke-width="2"/>'
    elif kind == "hatch":
        rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#hatch-{color[1:]})" stroke="{color}" stroke-width="2"/>'
    else:  # dashed outline
        rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="6 5"/>'
    label = f'<text x="{x+w/2}" y="{y+h/2+5}" text-anchor="middle" font-family="{FONT}" font-size="14" fill="{INK}">{code}</text>'
    return rect + label


def circle(cx, cy, r, color, code, dashed=False):
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    fill = "none" if dashed else color
    op = "" if dashed else ' fill-opacity="0.85"'
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{op} stroke="{color}" stroke-width="2"{dash}/>'
            f'<text x="{cx}" y="{cy-r-8}" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{INK}">{code}</text>')


def light(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LIGHT}" stroke-width="5" stroke-linecap="round" opacity="0.9"/>'


def doc(title, subtitle, content, legend):
    defs = "<defs>" + "".join(
        f'<pattern id="hatch-{c[1:]}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        f'<line x1="0" y1="0" x2="0" y2="8" stroke="{c}" stroke-width="3" opacity="0.7"/></pattern>'
        for c in (VENT, NOGO)) + "</defs>"
    leg = []
    y = 150
    for color, kind, text in legend:
        if kind == "circle":
            leg.append(f'<circle cx="932" cy="{y-5}" r="9" fill="{color}"/>')
        elif kind == "line":
            leg.append(f'<line x1="920" y1="{y-5}" x2="946" y2="{y-5}" stroke="{color}" stroke-width="5" stroke-linecap="round"/>')
        elif kind == "hatch":
            leg.append(f'<rect x="920" y="{y-15}" width="26" height="18" rx="4" fill="url(#hatch-{color[1:]})" stroke="{color}"/>')
        elif kind == "dash":
            leg.append(f'<rect x="920" y="{y-15}" width="26" height="18" rx="4" fill="none" stroke="{color}" stroke-dasharray="4 3" stroke-width="2"/>')
        else:
            leg.append(f'<rect x="920" y="{y-15}" width="26" height="18" rx="4" fill="{color}" fill-opacity="0.38" stroke="{color}" stroke-width="2"/>')
        for i, part in enumerate(text.split("|")):
            leg.append(f'<text x="958" y="{y + i*18}" font-family="{FONT}" font-size="13" fill="{INK if i == 0 else DIM}">{part}</text>')
        y += 30 + 18 * (len(text.split("|")) - 1)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
{defs}
<rect width="{W}" height="{H}" fill="{BG}"/>
<text x="40" y="52" font-family="{FONT}" font-size="15" letter-spacing="4" fill="{DIM}">ТИТАН · 05-DESIGN · СХЕМА ЗОН</text>
<text x="40" y="90" font-family="Inter, Helvetica, Arial, sans-serif" font-size="30" fill="{INK}">{title}</text>
<text x="40" y="118" font-family="{FONT}" font-size="13" fill="{DIM}">{subtitle}</text>
<text x="250" y="160" text-anchor="middle" font-family="{FONT}" font-size="13" letter-spacing="3" fill="{DIM}">СПЕРЕДИ</text>
<text x="690" y="160" text-anchor="middle" font-family="{FONT}" font-size="13" letter-spacing="3" fill="{DIM}">СЗАДИ</text>
{content}
{''.join(leg)}
<text x="40" y="{H-24}" font-family="{FONT}" font-size="12" fill="{DIM}">Вид спереди: левая сторона человека — справа на рисунке. Схема условная, не лекало. Коды зон и источники: 05-design/02-platform-construction.md. Версия 0.1 · 28.11.2026</text>
</svg>'''


def smart_casual():
    F, B = 250, 690
    fb, t = body(F, 175)
    bb, _ = body(B, 175)
    c = [fb, bb]
    # спереди: грудь H3/H4, карманы H5/H6, воротник, Порт, Корона, вентиляция V5
    c.append(zone(F-78, t+40, 56, 60, HEAT, "H3"))
    c.append(zone(F+22, t+40, 56, 60, HEAT, "H4"))
    c.append(zone(F-82, t+205, 60, 62, HEAT, "H5"))
    c.append(zone(F+22, t+205, 60, 62, HEAT, "H6"))
    c.append(zone(F-30, t-4, 60, 14, HEAT, "H7", r=6))
    c.append(zone(F-20, t+40, 14, 60, VENT, "", kind="hatch", r=4))
    c.append(zone(F+6, t+40, 14, 60, VENT, "", kind="hatch", r=4))
    c.append(f'<text x="{F}" y="{t+120}" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{INK}">V5</text>')
    c.append(circle(F+58, t+175, 13, PORT, "ПОРТ (внутри)", dashed=False))
    c.append(circle(F+50, t+135, 9, INK, "КОРОНА"))
    # сзади: H1 две половины, H2 две половины, V1 кокетка
    c.append(zone(B-80, t+20, 160, 28, VENT, "V1", kind="hatch"))
    c.append(zone(B-72, t+62, 62, 80, HEAT, "H1"))
    c.append(zone(B+10, t+62, 62, 80, HEAT, "H1"))
    c.append(zone(B-78, t+200, 66, 46, HEAT, "H2"))
    c.append(zone(B+12, t+200, 66, 46, HEAT, "H2"))
    c.append(f'<text x="{B}" y="{t+290}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="{DIM}">позвоночник ±2 см свободен</text>')
    legend = [(HEAT, "fill", "Подогрев H1–H7|предел на коже 42 °C"),
              (VENT, "hatch", "Вентиляция V1, V5|открывается одной рукой"),
              (PORT, "circle", "Порт: Связка Ядро Lite + Тепло|внутренний карман, талия слева"),
              (INK, "circle", "Корона: одна кнопка|левая полочка, под планкой"),
              (DIM, "fill", "SC-1 жилет = климат-подклад|H1–H4 живут на нём")]
    return doc("Smart Casual · SC-1 жилет + SC-2 пуховик",
               "Город, −25…+15 °C. Торс выше пальцев [Sci: Brajkovic1998]; пот — центр спины [D1]",
               "\n".join(c), legend)


def function():
    F, B = 250, 690
    fb, t = body(F, 175)
    bb, _ = body(B, 175)
    c = [fb, bb]
    # чистая зона груди r=20 см вокруг лавинного датчика
    c.append(f'<circle cx="{F}" cy="{t+70}" r="78" fill="url(#hatch-{NOGO[1:]})" stroke="{NOGO}" stroke-width="2"/>')
    c.append(circle(F, t+70, 12, SENS, "ЛАВИННЫЙ ДАТЧИК"))
    c.append(zone(F-82, t+215, 58, 56, HEAT, "H5"))
    c.append(zone(F+24, t+215, 58, 56, HEAT, "H6"))
    c.append(circle(F-62, t+190, 12, PORT, "ПОРТ"))
    c.append(circle(F+92, t+22, 9, INK, ""))
    c.append(f'<text x="{F+120}" y="{t+8}" font-family="{FONT}" font-size="13" fill="{INK}">КОРОНА</text>')
    for sx in (-1, 1):
        c.append(zone(F + sx*108 - 9, t+40, 18, 70, VENT, "", kind="hatch", r=4))
    c.append(f'<text x="{F-150}" y="{t+80}" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{INK}">V3</text>')
    # бёдра H11 опция, перчатки H8
    c.append(zone(F-78, t+330, 56, 80, HEAT, "H11", kind="dash"))
    c.append(zone(F+22, t+330, 56, 80, HEAT, "H11", kind="dash"))
    c.append(circle(F-142, t+315, 17, HEAT, "H8"))
    c.append(circle(F+142, t+315, 17, HEAT, "H8"))
    c.append(zone(F-66, t+562, 40, 16, HEAT, "H9", r=4))
    c.append(zone(F+26, t+562, 40, 16, HEAT, "H9", r=4))
    # сзади
    c.append(zone(B-80, t+20, 160, 28, VENT, "V1", kind="hatch"))
    c.append(zone(B-72, t+62, 62, 80, HEAT, "H1"))
    c.append(zone(B+10, t+62, 62, 80, HEAT, "H1"))
    c.append(zone(B-78, t+200, 66, 46, HEAT, "H2"))
    c.append(zone(B+12, t+200, 66, 46, HEAT, "H2"))
    legend = [(HEAT, "fill", "Подогрев: H1, H2 (средний слой),|H5/H6 карманы, H8 кисти, H9 стопы"),
              (HEAT, "dash", "H11 бёдра — опция FN-5"),
              (VENT, "hatch", "Вентиляция V1 спина, V3 подмышки|v2: пьезо- или микровентилятор"),
              (NOGO, "hatch", "Чистая зона лавинного датчика|UIAA: > 20 см передача, > 50 см поиск"),
              (PORT, "circle", "Порт справа на талии|Связка Ядро + Тепло Function"),
              (INK, "circle", "Корона: левое плечо|удержание 5 с = Лавинный режим")]
    return doc("Function · система FN-3 + FN-4 + FN-1/FN-2",
               "Лыжи и сноуборд. «Спуск» и «Подъёмник»; лавинная безопасность [D3][D4]",
               "\n".join(c), legend)


def sport():
    F, B = 250, 690
    fb, t = body(F, 175, legs=True)
    bb, _ = body(B, 175, legs=True)
    c = [fb, bb]
    # электроды под грудью
    for i, dx in enumerate((-60, -10, 40)):
        c.append(zone(F+dx, t+118, 22, 30, SENS, "", r=5))
    c.append(f'<text x="{F}" y="{t+168}" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{INK}">ЭКГ под грудью</text>')
    # треугольник бра (Ж)
    c.append(f'<path d="M{F-22},{t+40} L{F+22},{t+40} L{F},{t+100} Z" fill="url(#hatch-{VENT[1:]})" stroke="{VENT}" stroke-width="2"/>')
    c.append(f'<text x="{F}" y="{t+30}" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{INK}">V4 (Ж)</text>')
    # Ядро сбоку слева (для зрителя — справа на фронтальном виде)
    c.append(circle(F+100, t+185, 13, PORT, "ЯДРО"))
    # свет: плечи спереди + атлетский индикатор
    c.append(light(F-25, t-4, F-90, t+12))
    c.append(light(F+25, t-4, F+90, t+12))
    c.append(circle(F+70, t+30, 6, LIGHT, ""))
    c.append(f'<text x="{F+150}" y="{t+30}" font-family="{FONT}" font-size="12" fill="{INK}">индикатор атлета</text>')
    # ЭМГ шорты
    for sx in (-1, 1):
        c.append(zone(F + sx*46 - 20, t+330, 40, 70, SENS, "", kind="dash"))
    c.append(f'<text x="{F}" y="{t+430}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="{DIM}">ЭМГ SP-3 (бета)</text>')
    # сзади: V1 сетка центр спины, V2 поясница, свет кокетки сегментами
    c.append(zone(B-40, t+60, 80, 120, VENT, "V1", kind="hatch"))
    c.append(zone(B-60, t+220, 120, 50, VENT, "V2", kind="hatch"))
    c.append(light(B-25, t-4, B-90, t+12))
    c.append(light(B+25, t-4, B+90, t+12))
    for i in range(5):
        x = B - 80 + i * 34
        c.append(f'<line x1="{x}" y1="{t+38}" x2="{x+24}" y2="{t+38}" stroke="{LIGHT}" stroke-width="6" stroke-linecap="round" opacity="{0.95 if i < 3 else 0.3}"/>')
    c.append(f'<text x="{B}" y="{t+58}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="{INK}">кокетка: 1–5 сегментов = зона</text>')
    legend = [(SENS, "fill", "Электроды ЭКГ, 2–3 зоны|раздельные лекала М/Ж"),
              (SENS, "dash", "Электроды ЭМГ в шортах — бета"),
              (VENT, "hatch", "Сетка и перфорация V1, V2, V4|по карте пота [D1][D2]"),
              (LIGHT, "line", "Свет зоны: плечи и кокетка|цвет + число сегментов [D8]"),
              (PORT, "circle", "Ядро сбоку слева на рёбрах|гипотеза, проверить в кроссфите")]
    return doc("Sport · SP-1 топ / SP-2 бра (база)",
               "Кроссфит и HYROX. Цвет зоны по умолчанию выключен — приватность",
               "\n".join(c), legend)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in (("zones-smart-casual.svg", smart_casual), ("zones-function.svg", function), ("zones-sport.svg", sport)):
        (out / name).write_text(fn(), encoding="utf-8")
        print("ok", out / name)
