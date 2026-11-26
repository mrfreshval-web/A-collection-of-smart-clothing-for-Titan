"""Оригинальный саундтрек для видео «Титан» (15 с), синтезирован кодом, все права у проекта.

Тёмный кинематографичный пульс: суббас, «удары сердца» на каждую долю, мрачный пэд,
свуши на сменах сцен (каждые 2 с), нарастание к 12 с и удар на появлении логотипа.
Запуск: python3 soundtrack.py out.wav
"""
import sys
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt
import wave

SR = 48000
DUR = 15.0
BPM = 120
BEAT = 60 / BPM
HIT = 12.0  # появление логотипа
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)


def env_adsr(n, a, d, s, r, sus_len):
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    S = max(int(sus_len * SR), 0)
    e = np.concatenate([np.linspace(0, 1, A, False), np.linspace(1, s, D, False), np.full(S, s), np.linspace(s, 0, R)])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def lp(x, f, order=4):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def place(buf, snd, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(snd))
    buf[i:j] += snd[: j - i]


def kick(len_s=0.5, f0=110, f1=42, amp=1.0, click=0.3):
    n = int(len_s * SR)
    tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-tt * 7)
    cl = rng.standard_normal(n) * np.exp(-tt * 400) * click
    return (np.tanh(1.6 * body) + lp(cl, 4000)) * amp


def heartbeat(amp):
    """«Тук-тук»: два мягких низких удара."""
    s = np.zeros(int(0.6 * SR))
    place(s, kick(0.45, 90, 40, 1.0, 0.15), 0)
    place(s, kick(0.45, 80, 38, 0.65, 0.1), 0.16)
    return s * amp


def saw(freq, tt):
    return 2 * ((tt * freq) % 1.0) - 1


def pad(freqs, start, length, amp):
    n = int(length * SR)
    tt = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.13):
            x += saw(f * (1 + det / 100 * 6), tt + rng.random())
    x = lp(x, 900) * env_adsr(n, 0.6, 0.4, 0.8, 0.8, length - 1.8)
    return x / len(freqs) / 3 * amp


def noise_sweep(length, f_from, f_to, amp, rev=False):
    n = int(length * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    seg = 2048
    for k in range(0, n, seg):
        p = k / n
        if rev:
            p = 1 - p
        fc = f_from * (f_to / f_from) ** p
        lo, hi = max(fc * 0.6, 40), min(fc * 1.6, SR / 2 - 100)
        out[k:k + seg] = bp(x[max(0, k - 512):k + seg], lo, hi)[-len(x[k:k + seg]):]
    e = np.linspace(0, 1, n) ** 2 if not rev else np.linspace(1, 0, n) ** 1.5
    return out * e * amp


def reverb(x, secs=2.2, mix=0.25):
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.2)
    ir = lp(ir, 5000)
    wet = fftconvolve(x, ir)[: len(x)]
    wet /= np.max(np.abs(wet)) + 1e-9
    return x * (1 - mix) + wet * mix * np.max(np.abs(x))


def main(path):
    L = np.zeros(N)
    R = np.zeros(N)

    # 1. Суббас-дрон (ля, 55 Гц) с медленным открытием фильтра, гаснет перед ударом
    drone = np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 110 * t + 0.3)
    drone = np.tanh(1.4 * drone) * np.clip(t / 2.0, 0, 1) * np.where(t < HIT - 0.05, 0.22, 0.0)
    L += drone
    R += drone

    # 2. Сердцебиение на каждую сильную долю, учащается к удару
    beat_t = 0.5
    while beat_t < HIT - 0.3:
        intensity = 0.22 + 0.3 * (beat_t / HIT)
        hb = heartbeat(intensity)
        place(L, hb, beat_t)
        place(R, hb, beat_t)
        step = BEAT * 2 if beat_t < 4 else BEAT  # сначала через долю, потом каждую долю
        beat_t += step

    # 3. Мрачный пэд: Am → F → Dm → E по 2 с, на сменах сцен
    chords = [[110, 130.81, 164.81], [87.31, 110, 130.81], [73.42, 87.31, 110], [82.41, 103.83, 123.47]]
    for i in range(6):
        c = chords[i % 4]
        p = pad(c, i * 2.0, 2.4, 0.16 + 0.03 * i)
        place(L, p, i * 2.0)
        place(R, np.roll(p, 240), i * 2.0)

    # 4. Свуши на сменах сцен
    for k in range(1, 6):
        sw = noise_sweep(0.45, 300, 4000, 0.12)
        place(L, sw, k * 2.0 - 0.45)
        place(R, sw * 0.8, k * 2.0 - 0.45)

    # 5. Нарастание к логотипу: шумовой подъём + тиканье 16-ми
    rise = noise_sweep(2.0, 200, 9000, 0.35)
    place(L, rise, HIT - 2.0)
    place(R, rise, HIT - 2.0)
    tick_t = HIT - 2.0
    while tick_t < HIT - 0.05:
        tk = hp(rng.standard_normal(int(0.03 * SR)), 6000) * np.exp(-np.arange(int(0.03 * SR)) / SR * 150) * 0.15
        place(L, tk, tick_t)
        place(R, tk * 0.7, tick_t + 0.004)
        tick_t += BEAT / 4

    # 6. Удар на логотипе: саб-дроп + бочка + металлический отзвук
    boom = kick(2.5, 70, 28, 2.2, 0.6)
    place(L, boom, HIT)
    place(R, boom, HIT)
    n = int(2.8 * SR)
    tt = np.arange(n) / SR
    metal = sum(np.sin(2 * np.pi * f * tt) for f in (220, 331, 497, 743)) * np.exp(-tt * 1.6) * 0.07
    place(L, metal, HIT)
    place(R, np.roll(metal, 400), HIT)
    final_pad = pad([55, 110, 164.81, 220], HIT, DUR - HIT, 0.4)
    place(L, final_pad, HIT)
    place(R, np.roll(final_pad, 300), HIT)

    # Мастеринг: реверб, мягкий лимитер, фейды
    L, R = reverb(L), reverb(R)
    fade = np.clip((DUR - t) / 1.2, 0, 1) * np.clip(t / 0.05, 0, 1)
    st = np.stack([L * fade, R * fade], 1)
    st = np.tanh(st * 1.1) / np.tanh(1.1)
    st = st / (np.max(np.abs(st)) + 1e-9) * 0.89  # около −1 дБFS
    data = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("saved", path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "soundtrack.wav")
