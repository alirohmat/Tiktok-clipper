# 🎬 TikTok Clipper (Versi CLI & Web 2026)

Aplikasi CLI Python dan Web Studio sederhana, cepat, dan stabil untuk mengubah video panjang (atau tautan URL video) menjadi beberapa klip pendek vertikal TikTok 9:16 yang dipilih secara otomatis oleh AI berdasarkan **Strategi Algoritma TikTok 2026**.

---

## 🌟 Fitur Utama
- **Otomatisasi Penuh**: Mengunduh video (opsional), mengekstrak audio, mentranskripsi dengan Groq Whisper, menganalisis momen terbaik dengan LLM AI (Groq, DeepSeek, OpenRouter, OpenAI, dll.), dan memotong klip dengan FFmpeg.
- **Strategi TikTok 2026**:
  - Deteksi Hook tajam 3 detik pertama (*Extreme Statement, Paradox, Confession, Question, Authority*).
  - Prioritas klip berpotensi *high completion rate*, *save-worthy*, dan *share-worthy* dengan kelengkapan *Story Arc* (Awal $\rightarrow$ Tengah $\rightarrow$ Akhir).
  - Caption ramah SEO dengan kata kunci di 50 karakter pertama.
  - 3–5 hashtag terarah tanpa simbol `#` (bebas dari hashtag sampah seperti `#fyp`).
  - Saran looping video (*seamless loop*).
  - Call To Action (CTA) natural.
- **Dukungan Universal LLM (OpenAI-Compatible)**:
  - Gunakan **Groq** (default, super cepat), **DeepSeek** (`deepseek-chat`, `deepseek-reasoner`), **OpenRouter**, atau **OpenAI** (`gpt-4o`, `gpt-4o-mini`) untuk terbebas dari batasan rate-limit tier gratis.
- **Smart Speaker Tracking & Anti-Empty-Center Crop (OpenCV + FFmpeg)**:
  - **`auto`**: Otomatis mendeteksi tipe video (kunci pembicara pada konferensi pers/monolog, atau split layar atas-bawah pada podcast 2 orang).
  - **`speaker`**: Pelacakan gerak mulut (*Lip Motion Analysis*) untuk mengunci 1 pembicara aktif di tengah keramaian/panggung.
  - **`split`**: Dual-Speaker Split Screen Vertikal (Atas: Host, Bawah: Tamu) untuk podcast 2 orang. Dilengkapi **Anti-Empty-Center Protection** agar video tidak memotong ruang kosong di antara kedua orang.
  - **`crop`**: Center crop 1080x1920 klasik.
  - **`pad`**: Menyesuaikan rasio dengan bar hitam atas-bawah.
  - **`off`**: Mempertahankan rasio asli video.
- **Transkrip & Subtitle Presisi**:
  - Menghasilkan file transkrip utuh (`transcript.json`, `transcript.srt`).
  - Menghasilkan file subtitle per klip dengan timestamp relatif.
  - Pilihan membakar subtitle langsung ke video (*hardsub*) atau file terpisah.
- **Normalisasi Audio**: Audio diproses dengan standar broadcast EBU R128 (`loudnorm -16 LUFS`) agar suara jernih dan konsisten.
- **Fail-Proof Guarantee**: Dilengkapi *Adaptive Narrative Sizing* dan *Smart Heuristic Fallback* agar proses pemotongan 100% selalu sukses tanpa pernah terhenti di tengah jalan.

---

## 📋 Persyaratan Sistem
1. **Python 3.10+** (Direkomendasikan Python 3.11 atau lebih baru).
2. **FFmpeg & FFprobe** terpasang di sistem dan terdaftar pada PATH lingkungan.
3. **Groq API Key** (Dapat dibuat gratis di [https://console.groq.com](https://console.groq.com)) untuk Whisper transkripsi super cepat.
4. *(Opsional)* **API Key LLM Lain** (DeepSeek, OpenRouter, Together AI, OpenAI) jika ingin analisis LLM yang lebih pintar dan bebas limit.

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

Buka file `.env` dengan teks editor (Notepad/VS Code), lalu masukkan konfigurasi Anda:

```env
# API Key untuk Transkripsi Kilat Whisper
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_WHISPER_MODEL=whisper-large-v3

# --- Konfigurasi LLM (Pilih salah satu provider): ---
# 1. Menggunakan Groq (Default)
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile

# 2. ATAU Menggunakan DeepSeek (Rekomendasi Pintar & Hemat Kuota)
# LLM_PROVIDER=deepseek
# LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
# LLM_BASE_URL=https://api.deepseek.com/v1
# LLM_MODEL=deepseek-chat

# 3. ATAU Menggunakan OpenRouter
# LLM_PROVIDER=openrouter
# LLM_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
# LLM_BASE_URL=https://openrouter.ai/api/v1
# LLM_MODEL=anthropic/claude-3.5-sonnet

# 4. ATAU Menggunakan OpenAI
# LLM_PROVIDER=openai
# LLM_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
# LLM_MODEL=gpt-4o-mini

# Konfigurasi Default Clipping
DEFAULT_MIN_DURATION=15
DEFAULT_MAX_DURATION=60
DEFAULT_NUM_CLIPS=3
DEFAULT_NICHE=auto
DEFAULT_VERTICAL_MODE=auto
```

---

## 🔍 Pemeriksaan Sistem (--check)
Sebelum memproses video, jalankan diagnosa untuk memastikan semua dependensi siap:

```bash
python -m src.cli --check
# atau
python main.py --check
```

---

## 💡 Panduan Lengkap Penggunaan CLI

### 1. Perintah Dasar
```bash
# Memotong video dari URL (YouTube / Direct Video Link):
python -m src.cli --url "https://www.youtube.com/watch?v=XXXXXX" --num-clips 6

# Memotong video dari file lokal di komputer:
python -m src.cli --input "podcast_episode_1.mp4" --num-clips 5
```

---

### 2. Menggunakan Provider LLM Lain (DeepSeek, OpenRouter, OpenAI, dll.)
Untuk menghindari limit rate-limit tier Groq dan mendapatkan hasil hook yang lebih berbobot, Anda dapat mengoper parameter LLM langsung lewat CLI:

```bash
# Menggunakan DeepSeek Chat:
python -m src.cli --url "https://youtu.be/..." \
  --llm-provider deepseek \
  --llm-model deepseek-chat \
  --llm-api-key "sk-xxxx..." \
  --llm-base-url "https://api.deepseek.com/v1"

# Menggunakan OpenRouter:
python -m src.cli --url "https://youtu.be/..." \
  --llm-provider openrouter \
  --llm-model "meta-llama/llama-3.3-70b-instruct" \
  --llm-api-key "sk-or-v1-xxxx..."

# Menggunakan OpenAI GPT-4o Mini:
python -m src.cli --url "https://youtu.be/..." \
  --llm-provider openai \
  --llm-model gpt-4o-mini \
  --llm-api-key "sk-proj-xxxx..."
```

---

### 3. Memilih Mode Crop Vertikal 9:16 (`--vertical`)

| Mode | Kapan Digunakan? | Deskripsi |
| :--- | :--- | :--- |
| **`auto`** *(Default)* | Podcast, Konferensi Pers, Interview | AI otomatis mendeteksi: kunci 1 pembicara pada monolog/konferensi pers, atau split atas-bawah pada podcast 2 orang. |
| **`speaker`** | Konferensi Pers / Monolog Panggung | OpenCV melacak gerak bibir & mengunci 1 pembicara aktif di tengah keramaian. |
| **`split`** | Podcast 2 Orang (Host & Guest) | Layar dibagi 2 (Atas: Host, Bawah: Tamu) dengan perlindungan anti-ruang kosong. |
| **`crop`** | Konten Umum / Landscape | Center crop 1080x1920 klasik. |
| **`pad`** | Video yang tidak ingin terpotong | Menambahkan bar hitam atas-bawah (*Letterbox*). |
| **`off`** | Mempertahankan rasio asli | Tidak mengubah orientasi video (tetap 16:9 / rasio asal). |

*Contoh Perintah:*
```bash
# Mode Split Screen Vertikal untuk podcast 2 orang:
python -m src.cli --url "https://youtu.be/..." --vertical split --num-clips 4

# Mode Smart Speaker Tracking untuk konferensi pers:
python -m src.cli --input "konferensi_pers.mp4" --vertical speaker --num-clips 3
```

---

### 4. Menyesuaikan Niche Konten & Durasi Klip
```bash
# Menargetkan niche Bisnis dengan durasi 30 - 60 detik:
python -m src.cli --url "https://youtu.be/..." \
  --niche bisnis \
  --min-duration 30 \
  --max-duration 60 \
  --num-clips 5
```
*Daftar Niche yang Didukung:* `auto` (deteksi otomatis), `umum`, `edukasi`, `bisnis`, `cerita`, `hiburan`, `teknologi`, `kesehatan`, `motivasi`.

---

### 5. Opsi Tambahan CLI

```bash
# Mode Analisis Saja (Dapatkan timestamp, hook, & caption tanpa menunggu render video FFmpeg):
python -m src.cli --input "podcast.mp4" --analyze-only

# Matikan pembakaran subtitle ke video (hanya simpan file .srt terpisah):
python -m src.cli --input "podcast.mp4" --no-subtitles

# Tentukan folder output kustom:
python -m src.cli --input "podcast.mp4" --output-dir "my_tiktok_clips"

# Mode Debug Log:
python -m src.cli --input "podcast.mp4" --debug
```

---

## 📂 Struktur Output
Setiap proses pemotongan akan membuat folder khusus di dalam direktori `output/`:

```text
output/2026-08-30_07-15_url-video/
  ├── source/
  │   └── source_video.mp4      <- Video sumber asli
  ├── audio/
  │   └── audio.mp3             <- Audio 16kHz mono yang diekstrak
  ├── transcript/
  │   ├── transcript.json       <- Transkrip utuh dengan stempel waktu per segmen
  │   └── transcript.srt        <- Subtitle SRT keseluruhan video
  ├── analysis/
  │   └── analysis.json         <- Hasil analisis detail AI LLM (Hook, Retensi, Alasan)
  ├── clips/
  │   ├── 01-hook-utama.mp4     <- Klip video hasil potongan vertikal 9:16
  │   ├── 01-hook-utama.srt     <- Subtitle relatif khusus klip 1
  │   ├── 01-hook-utama.json    <- Metadata klip (hook, caption SEO, hashtags, CTA)
  │   └── 02-tips-bisnis.mp4
  ├── summary.md                <- Dokumen ringkasan lengkap siap salin ke TikTok
  └── manifest.json             <- Catatan log pemrosesan teknis
```

---

## 🛠️ Panduan Troubleshooting

| Masalah | Penyebab | Solusi Praktis |
| :--- | :--- | :--- |
| **`FFmpeg CLI: Tidak Ditemukan`** | FFmpeg belum terinstal atau belum masuk PATH | Instal FFmpeg, lalu tambahkan folder `bin` ke System PATH. Restart terminal. |
| **`Rate Limit 429 dari Groq`** | Kuota request token gratis Groq tercapai | Gunakan provider lain dengan opsi `--llm-provider deepseek` atau `--llm-provider openrouter` di CLI / `.env`. |
| **`Video 2 Orang Terpotong di Tengah`** | Ruang kosong antara 2 orang terpotong oleh center crop | Gunakan mode `--vertical split` atau `--vertical auto`. Sistem otomatis membagi layar atas-bawah tanpa memotong ruang kosong di tengah. |
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

