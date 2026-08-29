# 🎬 TikTok Clipper (Versi CLI 2026)

Aplikasi CLI Python sederhana, cepat, dan stabil untuk mengubah video panjang (atau tautan URL video) menjadi beberapa klip pendek vertikal TikTok 9:16 yang dipilih secara otomatis oleh AI berdasarkan **Strategi Algoritma TikTok 2026**.

---

## 🌟 Fitur Utama
- **Otomatisasi Penuh**: Mengunduh video (opsional), mengekstrak audio, mentranskripsi dengan Groq Whisper, menganalisis momen terbaik dengan Groq LLM, dan memotong klip dengan FFmpeg.
- **Strategi TikTok 2026**:
  - Deteksi Hook tajam 3 detik pertama.
  - Prioritas klip berpotensi *high completion rate*, *save-worthy*, dan *share-worthy*.
  - Caption ramah SEO dengan kata kunci di 50 karakter pertama.
  - 3–5 hashtag terarah tanpa simbol `#` (bebas dari hashtag sampah seperti `#fyp`).
  - Saran looping video (*seamless loop*).
  - Call To Action (CTA) natural.
- **Transkrip & Subtitle Presisi**:
  - Menghasilkan file transkrip utuh (`transcript.json`, `transcript.srt`).
  - Menghasilkan file subtitle per klip dengan timestamp relatif.
  - Pilihan membakar subtitle langsung ke video (*hardsub*) atau file terpisah.
- **Format Vertikal Otomatis (9:16)**:
  - `auto`: Otomatis center crop video landscape ke 1080x1920.
  - `crop`: Center crop 1080x1920.
  - `pad`: Menyesuaikan rasio dengan bar hitam atas-bawah.
  - `off`: Mempertahankan rasio asli video.
- **Normalisasi Audio**: Audio diproses dengan standar broadcast EBU R128 (`loudnorm`) agar suara konsisten dan jernih.
- **Aman Kuota Gratis Groq**: Jeda permintaan berurutan, caching berbasis hash file, dan mekanisme retry otomatis dengan backoff.
- **Ramah Non-Programmer**: Tampilan terminal interaktif berwarna menggunakan Rich dan skrip `.bat` otomatis untuk pengguna Windows.

---

## 📋 Persyaratan Sistem
1. **Python 3.10+** (Direkomendasikan Python 3.11 atau lebih baru).
2. **FFmpeg & FFprobe** terpasang di sistem dan terdaftar pada PATH lingkungan.
3. **Groq API Key** (Dapat dibuat gratis di [https://console.groq.com](https://console.groq.com)).

---

## 🚀 Panduan Instalasi Langkah-demi-Langkah

### 1. Pasang Python
- **Windows**: Unduh dari [python.org](https://www.python.org/downloads/). **Pastikan Anda mencentang opsi "Add python.exe to PATH"** pada tahap awal instalasi.
- **macOS**: `brew install python`
- **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install python3 python3-pip python3-venv`

### 2. Pasang FFmpeg & FFprobe
- **Windows**:
  - Unduh build rilis dari [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) (pilih `ffmpeg-release-essentials.zip`).
  - Ekstrak folder, lalu tambahkan folder `bin` (yang berisi `ffmpeg.exe` dan `ffprobe.exe`) ke Environment Variables (PATH) Windows.
  - Atau instal via winget: `winget install Gyan.FFmpeg`
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### 3. Buat Virtual Environment (Direkomendasikan)
Buka terminal/CMD di direktori proyek ini:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Pasang Pustaka Python
```bash
pip install -r requirements.txt
```

### 5. Konfigurasi File `.env`
Salin file template `.env.example` menjadi `.env`:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Buka file `.env` dengan teks editor (Notepad/VS Code), lalu masukkan Groq API Key Anda:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_WHISPER_MODEL=whisper-large-v3
GROQ_LLM_MODEL=openai/gpt-oss-120b
FFMPEG_PATH=ffmpeg
FFPROBE_PATH=ffprobe
OUTPUT_DIR=output
CACHE_DIR=cache
LOG_DIR=logs
DEFAULT_MIN_DURATION=15
DEFAULT_MAX_DURATION=60
DEFAULT_NUM_CLIPS=3
DEFAULT_NICHE=umum
```

---

## 🔍 Pemeriksaan Sistem (--check)
Sebelum memproses video, jalankan diagnosa untuk memastikan semua dependensi siap:

```bash
python main.py --check
```

---

## 💡 Contoh Penggunaan

### 1. Memotong Video dari File Lokal
```bash
python main.py --input "video_podcast.mp4" --niche edukasi --num-clips 3
```

### 2. Memotong Video Langsung dari URL (YouTube / TikTok / dll)
```bash
python main.py --url "https://www.youtube.com/watch?v=XXXXXX" --niche bisnis --num-clips 3
```

### 3. Menyesuaikan Durasi Klip & Format Vertikal
```bash
# Durasi 30 - 60 detik dengan center crop
python main.py --input "rekaman.mp4" --min-duration 30 --max-duration 60 --vertical crop

# Mempertahankan rasio asli (tanpa crop vertikal) dan tanpa hardsub:
python main.py --input "rekaman.mp4" --vertical off --no-subtitles
```

### 4. Mode Analisis Saja (Tanpa Merender Ulang Video)
Jika Anda hanya ingin membaca rekomendasi hook, caption SEO, dan timestamp tanpa menunggu proses render FFmpeg:
```bash
python main.py --input "podcast.mp4" --analyze-only
```

---

## 📂 Struktur Output
Setiap proses pemotongan akan membuat folder khusus di dalam direktori `output/`:

```text
output/2026-08-28_20-15_judul-video/
  ├── source/
  │   └── source_video.mp4      <- Video sumber asli
  ├── audio/
  │   └── audio.m4a             <- Audio 16kHz mono yang diekstrak
  ├── transcript/
  │   ├── transcript.json       <- Transkrip utuh dengan stempel waktu per segmen
  │   └── transcript.srt        <- Subtitle SRT keseluruhan video
  ├── analysis/
  │   └── analysis.json         <- Hasil analisis detail AI Groq LLM
  ├── clips/
  │   ├── 01-hook-utama.mp4     <- Klip video hasil potongan vertikal 9:16
  │   ├── 01-hook-utama.srt     <- Subtitle relatif khusus klip 1
  │   ├── 01-hook-utama.json    <- Metadata klip (hook, caption, hashtags, CTA)
  │   └── 02-tips-bisnis.mp4
  ├── summary.md                <- Dokumen ringkasan lengkap untuk di-copy ke TikTok
  └── manifest.json             <- Catatan log pemrosesan teknis
```

---

## 🛠️ Panduan Troubleshooting

| Masalah | Penyebab | Solusi Praktis |
| :--- | :--- | :--- |
| **`FFmpeg CLI: Tidak Ditemukan`** | FFmpeg belum terinstal atau belum masuk PATH | Instal FFmpeg, lalu tambahkan folder `bin` ke System PATH. Restart terminal. |
| **`GROQ_API_KEY belum diisi`** | Nilai API key kosong di file `.env` | Buat API key gratis di [console.groq.com](https://console.groq.com) lalu simpan di `.env`. |
| **`Video tidak memiliki stream audio`** | Video sumber tidak memiliki rekaman suara | Gunakan video yang memiliki suara percakapan jelas. |
| **`Rate Limit 429 dari Groq`** | Kuota request gratis per menit tercapai | Aplikasi otomatis melakukan retry dengan jeda. Jika tetap terjadi, tunggu 1-2 menit lalu ulangi. |
| **`Gagal mengunduh URL`** | Video privat, butuh login, atau pembatasan bot | Unduh video secara manual melalui browser, lalu gunakan flag `--input "file.mp4"`. |
| **`Subtitle gagal dibakar ke video`** | FFmpeg belum dikompilasi dengan pustaka `libass` | Aplikasi akan otomatis beralih ke video bersih dan tetap menyimpan file `.srt` terpisah di folder `clips/`. |

---

## ⚖️ Peringatan Hak Cipta & Etika Konten
- Aplikasi ini dibuat untuk keperluan kurasi, edukasi, dan produktivitas konten pribadi.
- **Hormati Hak Cipta**: Pastikan Anda memiliki hak atau izin dari pemilik konten asli sebelum mengunggah ulang klip video ke media sosial.
- **Pemberian Atribusi**: Sertakan kredit atau tag ke pembuat video asli pada caption video TikTok Anda.

---

## 📜 Lisensi
Lisensi MIT. Bebas digunakan dan dimodifikasi untuk kebutuhan konten kreator dan tim editorial.
