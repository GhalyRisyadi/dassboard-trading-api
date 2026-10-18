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

Server perlu akses internet ke `data-api.binance.vision` (alamat Binance khusus data pasar publik).

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
| `BINANCE_URL`  | `https://data-api.binance.vision` | Alamat dasar API Binance, mis. ` https://api.binance.com` |

Daftar pair, timeframe, dan periode EMA ada di `app/services/signals.py`.

## Tes

```bash
python -m pytest -q
```

## Jika `/signals` menjawab HTTP 502

Penyebabnya ada di baris log terminal tempat `uvicorn` berjalan, berbunyi
`Binance market-data request failed symbol=... category=... error=...`.
Cara membacanya:

| Isi log                                                                    | Artinya                                        |
|----------------------------------------------------------------------------|------------------------------------------------|
| `category=connection_error ... error=[Errno -2] Name or service not known` | Nama domain tidak bisa di-resolve (DNS)        |
| `category=connection_error ... error=All connection attempts failed`       | Koneksi ditolak atau tidak ada rute            |
| `category=connection_error ... error=[SSL: CERTIFICATE_VERIFY_FAILED] ...` | Sertifikat tidak cocok (mis. halaman blokir)   |
| `category=data_or_processing_error ... error_type=JSONDecodeError`         | Yang diterima bukan JSON (mis. halaman blokir) |
| `category=http_status status_code=451`                                     | Binance menolak berdasarkan wilayah            |
| `category=http_status status_code=429`                                     | Terlalu sering memanggil, tunggu sebentar      |
| `category=timeout`                                                         | Koneksi tidak dijawab sampai waktu habis       |

Pesan error lengkap hanya ditulis ke log, tidak pernah dikirim ke klien.

Tes tidak memanggil Binance sungguhan; responsnya ditiru dengan format yang sama.
