# dashboard-trading-api

Backend untuk dashboard trading crypto. Menghitung sinyal dari data candle Binance.

## Menjalankan

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Dokumentasi interaktif: http://localhost:8000/docs

Server perlu akses internet ke `api.binance.com`. Tidak butuh API key karena hanya memakai data publik.

## Endpoint

| Method | Path       | Keterangan                                              |
|--------|------------|---------------------------------------------------------|
| GET    | `/health`  | Cek server hidup                                        |
| GET    | `/signals` | Daftar sinyal terbaru, satu per pair, format `Signal`   |

Bentuk `Signal` harus selalu sama dengan `src/types/signals.ts` di repo frontend.
Jika Binance tidak bisa dijangkau untuk semua pair, `/signals` menjawab HTTP 502.

## Logika sinyal

Strategi persilangan EMA (Exponential Moving Average) 12 dan 26 pada candle 1 jam:

- **BUY**: EMA 12 memotong ke atas EMA 26 pada candle terakhir yang sudah selesai.
- **SELL**: EMA 12 memotong ke bawah EMA 26 pada candle terakhir yang sudah selesai.
- **HOLD**: tidak ada persilangan baru.

Candle yang sedang berjalan sengaja tidak dipakai karena harganya masih berubah.
Ini strategi berbasis aturan, bukan model AI, dan tidak menghasilkan probabilitas,
sehingga `confidence` bernilai `null`. Hasilnya bukan saran trading.

## Konfigurasi

| Variabel       | Default                 | Fungsi                                          |
|----------------|-------------------------|-------------------------------------------------|
| `CORS_ORIGINS` | `http://localhost:5173` | Alamat frontend yang diizinkan, dipisah koma    |
| `BINANCE_URL`  | `https://api.binance.com` | Alamat dasar API Binance, mis. `https://data-api.binance.vision` |

Daftar pair, timeframe, dan periode EMA ada di `app/services/signals.py`.

## Tes

```bash
python -m pytest -q
```

## Jika `/signals` menjawab HTTP 502

Penyebabnya ada di baris log terminal tempat `uvicorn` berjalan, berbunyi
`Gagal menghitung sinyal BTCUSDT: ...`. Cara membacanya:

| Isi log                                                | Artinya                                          |
|--------------------------------------------------------|--------------------------------------------------|
| `ConnectError('[Errno -2] Name or service not known')` | Nama domain tidak bisa di-resolve (DNS)          |
| `ConnectError('All connection attempts failed')`       | Koneksi ditolak atau tidak ada rute              |
| `ConnectError('[SSL: CERTIFICATE_VERIFY_FAILED] ...')` | Sertifikat TLS tidak cocok (mis. halaman blokir) |
| `JSONDecodeError('Expecting value ...')`               | Yang diterima bukan JSON (mis. halaman blokir)   |
| `HTTPStatusError(... '451' ...)`                       | Binance menolak berdasarkan wilayah              |
| `HTTPStatusError(... '429' ...)`                       | Terlalu sering memanggil, tunggu sebentar        |
| `ConnectTimeout()`                                     | Koneksi tidak dijawab sampai waktu habis         |

Tes tidak memanggil Binance sungguhan; responsnya ditiru dengan format yang sama.