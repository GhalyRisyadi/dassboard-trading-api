# dashboard-trading-api

Backend untuk dashboard trading crypto. Saat ini baru menyediakan data sinyal contoh;
logika sinyal sungguhan dikerjakan bertahap.

## Menjalankan

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Dokumentasi interaktif: http://localhost:8000/docs

## Endpoint

| Method | Path       | Keterangan                                   |
|--------|------------|----------------------------------------------|
| GET    | `/health`  | Cek server hidup                             |
| GET    | `/signals` | Daftar sinyal (data contoh), format `Signal` |

Bentuk `Signal` harus selalu sama dengan `src/types/signals.ts` di repo frontend.

## Konfigurasi

| Variabel       | Default                 | Fungsi                                          |
|----------------|-------------------------|-------------------------------------------------|
| `CORS_ORIGINS` | `http://localhost:5173` | Alamat frontend yang diizinkan, dipisah koma    |

## Tes

```bash
python -m pytest -q
```