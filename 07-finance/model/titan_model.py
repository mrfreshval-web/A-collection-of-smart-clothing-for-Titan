"""Финансовая модель «Титан» v0.1 (07-finance).

Запуск: python3 titan_model.py  -> пишет CSV в ./out и печатает сводку.
Все входы — в словарях ниже; у каждого входа в комментарии стоит источник
([F#] — 07-finance/sources.md, [T-S#] — 04-tech/99-sources.md,
[R-S#] — 01-research/sources.md) или пометка [Гипотеза] / [Расчёт].
Модель поквартальная: 2027Q1 … 2031Q4 (20 кварталов). Валюта — USD.
"""
import csv
import copy
import os

YEARS = [2027, 2028, 2029, 2030, 2031]
Q = [(y, q) for y in YEARS for q in (1, 2, 3, 4)]

# --------------------------------------------------------------------------
# 1. Изделия. bom = FOB Азия, партия 10 000 шт., середина диапазона 04-tech.
# --------------------------------------------------------------------------
SKUS = {
    # id: line, name, msrp, bom, freight/unit, season, units by year (база)
    "SC-1": dict(line="Smart Casual", name="Жилет с подогревом + Ядро Lite + Тепло",
                 msrp=345, bom=68.5, freight=1.2, season="winter",
                 units=[2200, 7000, 12000, 17000, 22000]),
    "SC-5": dict(line="Smart Casual", name="Перчатки городские с подогревом",
                 msrp=195, bom=30.5, freight=0.4, season="winter",
                 units=[1800, 6000, 9500, 13000, 16000]),
    "SC-2": dict(line="Smart Casual", name="Пуховик/парка + Ядро Lite + Тепло",
                 msrp=895, bom=104.0, freight=3.0, season="winter",
                 units=[0, 0, 3000, 6500, 10000]),
    "FN-1": dict(line="Function", name="Горнолыжные перчатки с подогревом",
                 msrp=325, bom=36.5, freight=0.4, season="winter",
                 units=[0, 2500, 6000, 9000, 12000]),
    "FN-2": dict(line="Function", name="Носки с подогревом",
                 msrp=245, bom=20.0, freight=0.3, season="winter",
                 units=[0, 2000, 5000, 7500, 10000]),
    "FN-4": dict(line="Function", name="Мембранная куртка + Ядро + Тепло Function",
                 msrp=1195, bom=186.5, freight=3.0, season="winter",
                 units=[0, 0, 0, 1500, 3500]),
    "SP-1K": dict(line="Sport", name="Компрессионная майка + Ядро (комплект)",
                  msrp=295, bom=77.0, freight=0.5, season="flat",
                  units=[0, 0, 2500, 7000, 12000]),
    "SP-1": dict(line="Sport", name="Майка без модуля (повторная покупка)",
                 msrp=165, bom=43.5, freight=0.3, season="flat",
                 units=[0, 0, 500, 3500, 8000]),
    "HNG": dict(line="Экосистема", name="Умная вешалка с чехлом",
                msrp=299, bom=77.5, freight=2.5, season="hanger",
                units=[0, 0, 1000, 2500, 4500]),
}
LAUNCH_YEAR = {k: next((YEARS[i] for i, u in enumerate(v["units"]) if u > 0), None)
               for k, v in SKUS.items()}

SEASON = {  # доля годовых продаж по кварталам [Гипотеза: зимний пик Q4, проверит 08-gtm по T6]
    "winter": [0.20, 0.05, 0.15, 0.60],
    "flat": [0.25, 0.25, 0.25, 0.25],
    "hanger": [0.20, 0.15, 0.20, 0.45],
}
SEASON_2027 = [0.0, 0.0, 0.0, 1.0]  # первая партия отгружается только в Q4 2027

# --------------------------------------------------------------------------
# 2. Общие допущения (база).
# --------------------------------------------------------------------------
A = dict(
    # Себестоимость
    small_batch_premium=0.20,   # +20 % к BOM в год запуска (партия < 10 000) [Гипотеза]
    learning=0.05,              # −5 % BOM в год после запуска (кривая обучения) [Гипотеза]
    bom_mult=1.0,               # множитель для чувствительности (04-tech: ±30 %)
    duty_us=0.25,               # пошлина США на FOB: MFN 6201.40 4,4–27,7 % [F10] + надбавка 12,5 % по Вьетнаму [F9, Н] [Расчёт/Гипотеза]
    duty_eu=0.08,               # ЕС: MFN гл. 62 до 12 % [Гипотеза], снижение по EVFTA к 2027–2030 [F11]
    duty_other=0.10,            # прочие рынки [Гипотеза]
    mix_us=0.45, mix_eu=0.35, mix_other=0.20,  # география продаж [Гипотеза; Сев. Америка 42–45 % рынка подогрева, R-S5/R-S6]
    packaging=3.0,              # упаковка, $/шт. [Гипотеза]
    qc=0.015,                   # инспекция на фабрике, % FOB [Гипотеза]
    # Каналы и цены
    d2c_share=[1.00, 0.80, 0.70, 0.65, 0.60],  # доля D2C в штуках [Гипотеза; у Canada Goose DTC 75,7 % выручки, F1]
    wholesale_price=0.50,       # оптовая цена = 50 % розничной [Гипотеза: стандарт keystone]
    d2c_discount=0.10,          # средняя скидка D2C [Гипотеза]
    crowd_discount=0.25,        # ранняя цена краудфандинга 2027 [Гипотеза]
    crowd_fee=0.09,             # Kickstarter 5 % + обработка платежей 3–5 % [F5]
    price_mult=1.0,
    # Переменные расходы D2C
    payment=0.027, payment_fix=0.30,  # Shopify Payments 2,5–2,9 % + $0,30 [F6]
    units_per_order=1.25,       # [Гипотеза]
    pickpack=5.0,               # $/заказ, 3PL $3,05–6,50 без доставки [F7]
    ship_out=14.0,              # $/заказ, бесплатная доставка: $8–18 по США [F7], выше для межд. [Гипотеза]
    return_rate=0.18,           # доля возвратов D2C: одежда 15–25 % [F8], электроника ~10 % [F12] [Расчёт]
    return_cost=20.0,           # обработка и обратная доставка, $/возврат [F7: $10–65; Гипотеза]
    return_writeoff=0.20,       # доля возвращённых шт., которые нельзя продать как новые [Гипотеза]
    markdown_share=0.12,        # доля D2C-штук, распроданных в конце сезона [Гипотеза]
    markdown_depth=0.40,        # глубина скидки на распродаже [Гипотеза]
    obsolescence=0.02,          # списание устаревших остатков, % себестоимости [Гипотеза]
    warranty=0.03,              # гарантийный резерв, % выручки [Гипотеза; проверить по факту]
    wh_allowance=0.03,          # возвраты/уценки опта, % оптовой выручки [Гипотеза]
    wh_freight=2.0,             # доставка до партнёра, $/шт. [Гипотеза]
    wh_coop=0.05,               # совместный маркетинг с партнёрами, % оптовой выручки [Гипотеза]
    # Маркетинг
    cac=[70, 120, 125, 130, 135],  # $ на нового D2C-клиента: одежда $90–120 [F13], электроника $100–377 [F13]; 2027 — краудфандинг [Гипотеза]
    cac_mult=1.0,
    new_share=[1.00, 0.85, 0.75, 0.70, 0.65],  # доля заказов от новых клиентов; эффект «Ядра» [Гипотеза]
    brand_mkt=[0.6e6, 1.0e6, 1.6e6, 2.2e6, 2.8e6],  # контент, PR, выставки (ISPO, CES) [Гипотеза]
    # Постоянные расходы (команда ИИ + обязательные подрядчики)
    ai_compute=[0.25e6, 0.35e6, 0.5e6, 0.65e6, 0.8e6],   # [Гипотеза]
    contractors=[0.6e6, 0.9e6, 1.3e6, 1.7e6, 2.1e6],     # директор/подписант, инженеры ОТК на фабрике, поддержка 2-й линии, бухгалтер [Гипотеза]
    rnd=[1.8e6, 1.5e6, 2.0e6, 1.6e6, 1.4e6],             # дизайн-хаус электроники, прошивка, прототипы, лекала [Гипотеза]
    certification=[0.30e6, 0.25e6, 0.35e6, 0.25e6, 0.20e6],  # $50 тыс.+ на семейство с батареей и радио [F14]
    ip=[0.15e6, 0.20e6, 0.25e6, 0.25e6, 0.25e6],         # патенты, товарные знаки [Гипотеза]
    gna=[0.20e6, 0.35e6, 0.50e6, 0.65e6, 0.80e6],        # страхование ответственности, юристы, аудит [Гипотеза]
    matuta=[0.30e6, 0.30e6, 0.40e6, 0.40e6, 0.50e6],     # интеграция с MATUTA, облако, прошивка OTA [Гипотеза]
    platform=[0.05e6, 0.08e6, 0.12e6, 0.15e6, 0.18e6],   # Shopify, SaaS, склад (фикс.) [F6, F19]
    capex=[0.25e6, 0.20e6, 0.35e6, 0.30e6, 0.30e6],      # пресс-формы корпусов, оснастка, стенды теста [F15, Гипотеза]
    dep_years=3,
    tax=0.21,                   # налог на прибыль (ставка США) с переносом убытков [Гипотеза: юрисдикцию выбирает 06-ops-legal]
    # Оборотный капитал
    deposit=0.30,               # предоплата фабрике за 2 квартала до продажи, остаток 70 % — за 1 квартал [Гипотеза: типовые условия]
    safety_stock=0.10,          # запас сверх продаж, доля годового объёма [Гипотеза]
    preorder_share_2027=0.60,   # доля отгрузок Q4 2027, оплаченных заранее (краудфандинг в Q3) [Гипотеза]
    volume_mult=1.0,
    opening_cash=0.0,
    min_cash_quarters=2,        # подушка = 2 квартала постоянных расходов [Гипотеза]
)


def run(a=None, skus=None):
    a = copy.deepcopy(A if a is None else a)
    skus = copy.deepcopy(SKUS if skus is None else skus)
    duty = a["duty_us"] * a["mix_us"] + a["duty_eu"] * a["mix_eu"] + a["duty_other"] * a["mix_other"]
    rows = []      # по кварталам
    sku_year = []  # по изделиям и годам
    for yi, y in enumerate(YEARS):
        for qi in range(4):
            r = dict(year=y, q=qi + 1, units=0, units_d2c=0, units_wh=0, rev_d2c=0, rev_wh=0,
                     cogs=0, var_d2c=0, var_wh=0, returns_cost=0, warranty=0, orders=0)
            rows.append(r)
    for k, s in skus.items():
        ly = LAUNCH_YEAR[k]
        for yi, y in enumerate(YEARS):
            units = s["units"][yi] * a["volume_mult"]
            if units == 0:
                continue
            years_since = y - ly
            bom = s["bom"] * a["bom_mult"] * (1 - a["learning"]) ** years_since
            if years_since == 0:
                bom *= 1 + a["small_batch_premium"]
            landed = bom * (1 + duty + a["qc"]) + s["freight"] + a["packaging"]
            d2c = units * a["d2c_share"][yi]
            wh = units - d2c
            msrp = s["msrp"] * a["price_mult"]
            if y == 2027:
                p_d2c = msrp * (1 - a["crowd_discount"])
                fee = a["crowd_fee"]
            else:
                p_d2c = msrp * ((1 - a["d2c_discount"]) * (1 - a["markdown_share"])
                                + (1 - a["markdown_depth"]) * a["markdown_share"])
                fee = a["payment"]
            kept = d2c * (1 - a["return_rate"])
            returned = d2c * a["return_rate"]
            rev_d2c = kept * p_d2c
            rev_wh = wh * msrp * a["wholesale_price"] * (1 - a["wh_allowance"])
            orders = d2c / a["units_per_order"]
            # себестоимость проданного: оставленные + списанные возвраты + опт
            cogs = (kept + returned * a["return_writeoff"] + wh) * landed * (1 + a["obsolescence"])
            var_d2c = (d2c * p_d2c * fee + orders * (a["payment_fix"] + a["pickpack"] + a["ship_out"]))
            ret_cost = returned * a["return_cost"]
            var_wh = wh * a["wh_freight"] + rev_wh * a["wh_coop"]
            warr = (rev_d2c + rev_wh) * a["warranty"]
            sku_year.append(dict(sku=k, line=s["line"], year=y, units=round(units), units_d2c=round(d2c),
                                 units_wh=round(wh), msrp=msrp, landed_cogs=round(landed, 2),
                                 revenue=round(rev_d2c + rev_wh), cogs=round(cogs),
                                 gross_margin=round((rev_d2c + rev_wh - cogs) / (rev_d2c + rev_wh), 3)))
            prof = SEASON_2027 if y == 2027 else SEASON[s["season"]]
            for qi in range(4):
                r = rows[yi * 4 + qi]
                f = prof[qi]
                r["units"] += units * f; r["units_d2c"] += d2c * f; r["units_wh"] += wh * f
                r["rev_d2c"] += rev_d2c * f; r["rev_wh"] += rev_wh * f; r["cogs"] += cogs * f
                r["var_d2c"] += var_d2c * f; r["var_wh"] += var_wh * f
                r["returns_cost"] += ret_cost * f; r["warranty"] += warr * f; r["orders"] += orders * f
                r.setdefault("purchase_value", 0)
                # стоимость закупки для этого квартала продаж (все шт., включая возвраты под списание)
                r["purchase_value"] += units * landed * f
    # маркетинг и постоянные расходы
    for i, r in enumerate(rows):
        yi = YEARS.index(r["year"])
        new_cust = r["orders"] * a["new_share"][yi]
        r["new_customers"] = new_cust
        r["mkt_perf"] = new_cust * a["cac"][yi] * a["cac_mult"]
        # маркетинг бренда распределяется равномерно, в 2027 — с упором на Q3 (кампания)
        bw = [0.15, 0.15, 0.40, 0.30] if r["year"] == 2027 else [0.25] * 4
        r["mkt_brand"] = a["brand_mkt"][yi] * bw[r["q"] - 1]
        fixed = sum(a[x][yi] for x in ("ai_compute", "contractors", "rnd", "certification", "ip", "gna", "matuta", "platform"))
        r["fixed"] = fixed / 4
    # P&L, налоги, амортизация
    dep_sched = [0.0] * len(rows)
    for yi in range(len(YEARS)):
        c = a["capex"][yi]
        for j in range(yi * 4, min(len(rows), yi * 4 + a["dep_years"] * 4)):
            dep_sched[j] += c / (a["dep_years"] * 4)
    nol = 0.0
    for i, r in enumerate(rows):
        yi = YEARS.index(r["year"])
        r["revenue"] = r["rev_d2c"] + r["rev_wh"]
        r["gross_profit"] = r["revenue"] - r["cogs"]
        r["contribution"] = r["gross_profit"] - r["var_d2c"] - r["var_wh"] - r["returns_cost"] - r["warranty"] - r["mkt_perf"]
        r["ebitda"] = r["contribution"] - r["mkt_brand"] - r["fixed"]
        r["dep"] = dep_sched[i]
        r["ebit"] = r["ebitda"] - r["dep"]
        r["capex"] = a["capex"][yi] / 4
    # налог по годам
    for yi, y in enumerate(YEARS):
        ebit_y = sum(r["ebit"] for r in rows if r["year"] == y)
        taxable = ebit_y - nol
        if taxable > 0:
            tax = taxable * a["tax"]; nol = 0
        else:
            tax = 0; nol = -taxable if ebit_y < 0 else nol - ebit_y
        for r in rows:
            if r["year"] == y:
                r["tax"] = tax / 4
                r["net_income"] = r["ebit"] - r["tax"]
    # денежный поток: закупки с предоплатой, предзаказы 2027, дебиторка опта
    n = len(rows)
    pay = [0.0] * (n + 2)
    for i, r in enumerate(rows):
        pv = r["purchase_value"]
        if i - 2 >= 0:
            pay[i - 2] += pv * a["deposit"]
        else:
            pay[0] += pv * a["deposit"]
        pay[max(i - 1, 0)] += pv * (1 - a["deposit"])
    # закупки под продажи 2032 Q1–Q2 (за горизонтом): тот же квартал 2031 × рост, не выше +30 %
    # [Гипотеза] — иначе последний год выглядит лучше, чем есть
    p30 = sum(r["purchase_value"] for r in rows if r["year"] == YEARS[-2])
    p31 = sum(r["purchase_value"] for r in rows if r["year"] == YEARS[-1])
    g = min(p31 / p30, 1.3) if p30 else 1.0
    nq1, nq2 = rows[-4]["purchase_value"] * g, rows[-3]["purchase_value"] * g
    pay[n - 2] += nq1 * a["deposit"]
    pay[n - 1] += nq1 * (1 - a["deposit"]) + nq2 * a["deposit"]
    # страховой запас: оплачивается в Q2 каждого года, как доля годовой закупки (прирост к прошлому году)
    prev_ss = 0
    for yi, y in enumerate(YEARS):
        ann = sum(r["purchase_value"] for r in rows if r["year"] == y)
        ss = ann * a["safety_stock"]
        pay[yi * 4 + 1] += max(ss - prev_ss, 0)
        prev_ss = ss
    cash = a["opening_cash"]
    for i, r in enumerate(rows):
        inflow_d2c = r["rev_d2c"]
        if r["year"] == 2027 and r["q"] == 3:
            inflow_d2c = rows[i + 1]["rev_d2c"] * a["preorder_share_2027"]
        if r["year"] == 2027 and r["q"] == 4:
            inflow_d2c = r["rev_d2c"] * (1 - a["preorder_share_2027"])
        inflow_wh = rows[i - 1]["rev_wh"] if i > 0 else 0  # опт платит через ~60–90 дней
        outflow_ops = (r["var_d2c"] + r["var_wh"] + r["returns_cost"] + r["warranty"] + r["mkt_perf"]
                       + r["mkt_brand"] + r["fixed"] + r["tax"])
        r["purchases_paid"] = pay[i]
        r["cash_flow"] = inflow_d2c + inflow_wh - outflow_ops - pay[i] - r["capex"]
        cash += r["cash_flow"]
        r["cum_cash_pre_funding"] = cash
    trough = min(r["cum_cash_pre_funding"] for r in rows)
    trough_q = next(f"{r['year']}Q{r['q']}" for r in rows if r["cum_cash_pre_funding"] == trough)
    buffer = a["min_cash_quarters"] * max(r["fixed"] + r["mkt_brand"] for r in rows if r["year"] <= 2028)
    years = []
    for y in YEARS:
        rs = [r for r in rows if r["year"] == y]
        s = lambda k: sum(r[k] for r in rs)
        years.append(dict(year=y, units=s("units"), revenue=s("revenue"), rev_d2c=s("rev_d2c"), rev_wh=s("rev_wh"),
                          cogs=s("cogs"), gross_profit=s("gross_profit"),
                          var_costs=s("var_d2c") + s("var_wh") + s("returns_cost") + s("warranty"),
                          mkt_perf=s("mkt_perf"), contribution=s("contribution"), mkt_brand=s("mkt_brand"),
                          fixed=s("fixed"), ebitda=s("ebitda"), dep=s("dep"), ebit=s("ebit"), tax=s("tax"),
                          net_income=s("net_income"), capex=s("capex"), purchases_paid=s("purchases_paid"),
                          cash_flow=s("cash_flow"), cum_cash_end=rs[-1]["cum_cash_pre_funding"],
                          new_customers=s("new_customers"),
                          mer=s("revenue") / max(s("mkt_perf") + s("mkt_brand"), 1)))
    first_pos_q = next((f"{r['year']}Q{r['q']}" for r in rows
                        if sum(x["ebitda"] for x in rows if x["year"] == r["year"]) > 0), None)
    ebitda_pos_year = next((yy["year"] for yy in years if yy["ebitda"] > 0), None)
    # квартал, после которого накопленный денежный поток больше не падает
    cf_pos_year = next((yy["year"] for yy in years if yy["cash_flow"] > 0), None)
    return dict(rows=rows, years=years, sku_year=sku_year, trough=trough, trough_q=trough_q,
                buffer=buffer, need=-trough + buffer, ebitda_pos_year=ebitda_pos_year,
                cf_pos_year=cf_pos_year, duty=duty)


def scenario(name):
    a = copy.deepcopy(A)
    if name == "conservative":
        a.update(volume_mult=0.55, cac_mult=1.25, price_mult=0.95, return_rate=0.22)
    elif name == "optimistic":
        a.update(volume_mult=1.5, cac_mult=0.85, return_rate=0.15)
    return a


def unit_economics(a=None, year=2029):
    a = copy.deepcopy(A if a is None else a)
    duty = a["duty_us"] * a["mix_us"] + a["duty_eu"] * a["mix_eu"] + a["duty_other"] * a["mix_other"]
    yi = YEARS.index(year)
    out = []
    for k, s in SKUS.items():
        ly = LAUNCH_YEAR[k]
        ys = max(year - ly, 1)  # устойчивое состояние: после года запуска
        bom = s["bom"] * (1 - a["learning"]) ** ys
        landed = bom * (1 + duty + a["qc"]) + s["freight"] + a["packaging"]
        p = s["msrp"] * ((1 - a["d2c_discount"]) * (1 - a["markdown_share"])
                         + (1 - a["markdown_depth"]) * a["markdown_share"])
        net = p * (1 - a["return_rate"])
        cogs = landed * (1 - a["return_rate"] + a["return_rate"] * a["return_writeoff"]) * (1 + a["obsolescence"])
        var = p * a["payment"] + (a["payment_fix"] + a["pickpack"] + a["ship_out"]) / a["units_per_order"] \
            + a["return_rate"] * a["return_cost"] + net * a["warranty"]
        contrib = net - cogs - var
        cac_unit = a["cac"][yi] / a["units_per_order"]
        wh_net = s["msrp"] * a["wholesale_price"] * (1 - a["wh_allowance"])
        wh_contrib = wh_net - landed - a["wh_freight"] - wh_net * a["wh_coop"] - wh_net * a["warranty"]
        out.append(dict(sku=k, line=s["line"], name=s["name"], msrp=s["msrp"], bom_fob=round(bom, 1),
                        landed=round(landed, 1), d2c_net=round(net, 1), d2c_gm=round((net - cogs) / net, 3),
                        d2c_var=round(var, 1), d2c_contrib_pre_cac=round(contrib, 1),
                        cac_per_unit=round(cac_unit, 1), d2c_contrib_after_cac=round(contrib - cac_unit, 1),
                        wh_net=round(wh_net, 1), wh_gm=round((wh_net - landed) / wh_net, 3),
                        wh_contrib=round(wh_contrib, 1),
                        breakeven_cac=round(contrib * a["units_per_order"], 0)))
    return out


def sensitivity():
    base = run()
    b5 = base["years"][-1]["ebitda"]; bneed = base["need"]
    cases = [
        ("Объём продаж −30 % / +30 %", dict(volume_mult=0.7), dict(volume_mult=1.3)),
        ("Себестоимость BOM +30 % / −30 %", dict(bom_mult=1.3), dict(bom_mult=0.7)),
        ("Розничная цена −10 % / +10 %", dict(price_mult=0.9), dict(price_mult=1.1)),
        ("CAC +30 % / −30 %", dict(cac_mult=1.3), dict(cac_mult=0.7)),
        ("Пошлина США +20 п.п. / −15 п.п.", dict(duty_us=0.45), dict(duty_us=0.10)),
        ("Возвраты 25 % / 12 %", dict(return_rate=0.25), dict(return_rate=0.12)),
        ("Доля D2C −15 п.п. / +15 п.п.", "d2c-", "d2c+"),
        ("Постоянные расходы +25 % / −25 %", "fix+", "fix-"),
    ]
    res = []
    for label, lo, hi in cases:
        vals = []
        for ch in (lo, hi):
            a = copy.deepcopy(A)
            if isinstance(ch, dict):
                a.update(ch)
            elif ch in ("d2c-", "d2c+"):
                d = -0.15 if ch == "d2c-" else 0.15
                a["d2c_share"] = [min(1.0, max(0.0, x + d)) if i > 0 else x for i, x in enumerate(a["d2c_share"])]
            else:
                m = 1.25 if ch == "fix+" else 0.75
                for kk in ("ai_compute", "contractors", "rnd", "certification", "ip", "gna", "matuta", "platform"):
                    a[kk] = [x * m for x in a[kk]]
            r = run(a)
            vals.append((r["years"][-1]["ebitda"], r["need"]))
        res.append(dict(factor=label, ebitda2031_low=round(vals[0][0]), ebitda2031_high=round(vals[1][0]),
                        need_low=round(vals[0][1]), need_high=round(vals[1][1])))
    return b5, bneed, res


def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v) if isinstance(v, float) and abs(v) > 10 else
                            (round(v, 3) if isinstance(v, float) else v)) for k, v in r.items()})


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "out"); os.makedirs(out, exist_ok=True)
    summary = []
    for sc in ("conservative", "base", "optimistic"):
        r = run(scenario(sc))
        write_csv(os.path.join(out, f"pnl_annual_{sc}.csv"), r["years"])
        write_csv(os.path.join(out, f"quarterly_{sc}.csv"), r["rows"],
                  ["year", "q", "units", "revenue", "rev_d2c", "rev_wh", "cogs", "gross_profit", "mkt_perf",
                   "contribution", "mkt_brand", "fixed", "ebitda", "purchases_paid", "cash_flow", "cum_cash_pre_funding"])
        write_csv(os.path.join(out, f"sku_{sc}.csv"), r["sku_year"])
        summary.append((sc, r))
        print(f"\n=== {sc}: средняя пошлина {r['duty']:.1%}; дно кассы {r['trough']/1e6:.1f} млн в {r['trough_q']}; "
              f"подушка {r['buffer']/1e6:.1f}; потребность {r['need']/1e6:.1f} млн; EBITDA>0 с {r['ebitda_pos_year']}; "
              f"CF>0 с {r['cf_pos_year']}")
        for y in r["years"]:
            print(f"{y['year']}: шт {y['units']:>8.0f} выручка {y['revenue']/1e6:6.1f} ВП {y['gross_profit']/y['revenue'] if y['revenue'] else 0:5.1%} "
                  f"контриб {y['contribution']/1e6:6.1f} EBITDA {y['ebitda']/1e6:6.1f} ({y['ebitda']/y['revenue'] if y['revenue'] else 0:6.1%}) "
                  f"MER {y['mer']:4.1f} нов.клиенты {y['new_customers']:7.0f} ЧП {y['net_income']/1e6:6.1f} CF {y['cash_flow']/1e6:6.1f} касса {y['cum_cash_end']/1e6:6.1f}")
    ue = unit_economics()
    write_csv(os.path.join(out, "unit_economics_2029_base.csv"), ue)
    for u in ue:
        print(u)
    b5, bneed, sens = sensitivity()
    write_csv(os.path.join(out, "sensitivity_base.csv"), sens)
    print("\nБаза EBITDA 2031", round(b5 / 1e6, 2), "потребность", round(bneed / 1e6, 2))
    for s in sens:
        print(s)
