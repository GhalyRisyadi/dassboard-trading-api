def ema(values: list[float], period: int) -> list[float]:
    """Exponential Moving Average (rata-rata pergerakan eksponensial).

    Nilai pertama adalah rata-rata biasa dari `period` data pertama, lalu tiap data
    berikutnya dihitung rekursif. Elemen ke-i hasilnya sesuai dengan data ke-(i + period - 1),
    jadi hasilnya lebih pendek `period - 1` dari masukan. Kalau data kurang dari
    `period`, hasilnya list kosong.
    """
    if period < 1:
        raise ValueError("period harus minimal 1")
    if len(values) < period:
        return []

    k = 2 / (period + 1)
    result = [sum(values[:period]) / period]
    for value in values[period:]:
        result.append(value * k + result[-1] * (1 - k))
    return result