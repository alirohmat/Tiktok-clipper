# 📊 PANDUAN & MATERI PRESENTASI DETAIL: TIKTOK CLIPPER 2026

Dokumen ini memuat materi presentasi lengkap, terstruktur, dan mendalam (*Presentation Outline & Pitch Deck Content*) mengenai aplikasi **TikTok Clipper 2026**.

---

## 📑 DAFTAR ISI (AGENDA PRESENTASI)

1. **Slide 1: Eksekutif Summary & Identitas Produk**
2. **Slide 2: Latar Belakang & Masalah Kreator Konten**
3. **Slide 3: Solusi & Nilai Utama (Unique Value Proposition)**
4. **Slide 4: Arsitektur & Pipeline Otomatisasi (End-to-End Flow)**
5. **Slide 5: Formula Algoritma TikTok 2026 (Hook, Story Arc, SEO)**
6. **Slide 6: Teknologi Computer Vision & Smart Cropping 9:16 (OpenCV + FFmpeg)**
7. **Slide 7: Integrasi Fleksibel Multi-LLM (Universal AI Engine)**
8. **Slide 8: Antarmuka Web Studio & Fitur Interaktif (UI/UX)**
9. **Slide 9: Struktur Output & Metadata Ekspor**
10. **Slide 10: Mekanisme Keandalan & Penanganan Error (Fail-Safe)**
11. **Slide 11: Tech Stack & Spesifikasi Sistem**
12. **Slide 12: Dampak Bisnis, Efisiensi Waktu, & Penutup (Q&A)**

---

## 🖥️ SLIDE 1: EKSEKUTIF SUMMARY & IDENTITAS PRODUK

### Judul
**TikTok Clipper 2026 — AI-Powered Viral Video Automation & Smart 9:16 Cropper**

### Ringkasan Eksekutif
TikTok Clipper adalah platform otomatisasi terpadu yang mengubah video berdurasi panjang (podcast, wawancara, webinar, talkshow, ceramah) menjadi klip vertikal pendek berformat 9:16 (*Shorts / TikTok / Reels*) yang siap viral dan dioptimalkan secara matematis untuk algoritma retensi TikTok 2026.

### Poin Kunci
- **Otomatisasi Penuh**: Dari audio extraction, transkripsi kata demi kata, analisis psikologi hook, pelacakan wajah pembicara, hingga rendering video 9:16.
- **Dual Interface**: Dilengkapi Web Studio modern (React 19) dan CLI Python berkecepatan tinggi.
- **Standar Ekspor Lengkap**: Menghasilkan video MP4, subtitle SRT, metadata SEO, dan dokumen ringkasan siap salin.

---

## 🖥️ SLIDE 2: LATAR BELAKANG & MASALAH KREATOR KONTEN

### Tantangan Kurasi Konten Manual
1. **Waktu Editing yang Terlalu Lama**: Menonton video podcast 1-2 jam dan mencari momen emas membutuhkan waktu rata-rata 3-5 jam per video.
2. **Tingkat Retensi Rendah (*Drop-off Rate*)**: Pemotongan manual sering kali menyisakan intro yang lambat (*"Halo teman-teman..."*) sehingga penonton langsung swipe-away dalam 2 detik pertama.
3. **Storyline Terpotong (*Incomplete Arc*)**: Sering kali video dipotong sebelum argumen tuntas, merusak kepuasan penonton.
4. **Isu Framing Format Horizontal ke Vertikal**: Video podcast biasanya horizontal (16:9). Memotong tengah secara asal sering kali menyisakan ruang kosong di antara kedua pembicara (*Empty Center Problem*).
5. **Kelemahan SEO Pencarian TikTok**: Kreator sering kali bingung merumuskan caption dan hashtag spesifik tanpa terjebak hashtag usang seperti `#fyp`.

---

## 🖥️ SLIDE 3: SOLUSI & NILAI UTAMA (UNIQUE VALUE PROPOSITION)

### 💡 Solusi yang Dihadirkan
| Masalah | Solusi Otomatisasi TikTok Clipper |
| :--- | :--- |
| Editing manual 3–5 jam | Selesai dalam hitungan menit secara otomatis |
| Penonton swipe di detik awal | 5 Formula Hook Psikologis (0–3 detik pertama) |
| Kalimat terpotong | Deteksi *Story Arc* utuh (Setup $\rightarrow$ Eskalasi $\rightarrow$ Konklusi) |
| Wajah pembicara terpotong di 16:9 | Computer Vision: Active Speaker Tracking & Anti-Empty-Center Split |
| Indexing pencarian lemah | Auto-generate TikTok Search SEO (Keyword-rich 50 Karakter Pertama) |

---

## 🖥️ SLIDE 4: ARSITEKTUR & PIPELINE OTOMATISASI

Sistem mengeksekusi 6 tahapan pemrosesan terisolasi (*end-to-end pipeline*):

```text
       [ Sumber Video: File / URL / Demo ]
                        │
                        ▼
   [ 1. Ekstraksi Audio & Normalisasi (FFmpeg) ]
   - Ekstrak MP3 16kHz Mono
   - Normalisasi Loudness ke -16 LUFS (Standar Platform)
                        │
                        ▼
   [ 2. Transkripsi Presisi Kata (Groq Whisper v3) ]
   - Menghasilkan Segment & Word-level Timestamps
   - Menghasilkan master transcript.json dan transcript.srt
                        │
                        ▼
   [ 3. Analisis Semantik & Kurasi AI (Universal LLM) ]
   - Ekstraksi Host, Narasumber, Tokoh & Topik Utama
   - Evaluasi Momen Berdasarkan Formula Hook 2026
   - Penentuan Titik Potong Tepat (Zero Fluff)
                        │
                        ▼
   [ 4. Smart Cropping & Vision Engine (OpenCV) ]
   - Analisis Wajah & Gerak Bibir (Lip-Motion)
   - Pembagian Layar Dual-Speaker (Anti-Empty-Center)
                        │
                        ▼
   [ 5. Pemotongan & Rendering Video (FFmpeg) ]
   - Pemotongan Lossless / Re-encode 9:16 (1080x1920)
   - Sinkronisasi Subtitle Relatif (.srt) & Hardsub Opsional
                        │
                        ▼
   [ 6. Output Terorganisir & Siap Posting ]
   - Folder Run Unik berisi MP4, SRT, JSON Metadata, & Summary.md
```

---

## 🖥️ SLIDE 5: FORMULA ALGORITMA TIKTOK 2026

Aplikasi dirancang dengan pemahaman mendalam terhadap parameter retensi algoritma TikTok modern:

### 1. Formula 5 Tipe Hook (0–3 Detik Pertama)
- **The Authority / Name-Drop Hook**: Mengangkat kredibilitas nama besar atau figur industri.
- **The Extreme / High Stakes Hook**: Membuka langsung dengan momen berisiko tinggi atau emosional.
- **The Counter-Intuitive / Paradox Hook**: Membongkar mitos umum yang dipercaya banyak orang.
- **The Vulnerability / Rare Confession Hook**: Pengakuan personal, kegagalan, atau rahasia dapur.
- **The Provocative Question Hook**: Pertanyaan tajam yang memicu rasa ingin tahu mendalam.

### 2. Story Arc Utuh (*Zero Fluff*)
- Menghilangkan basa-basi pembuka (*"Oke jadi gini...", "Halo halo..."*).
- Memastikan durasi klip berkisar 15–180 detik dengan penyelesaian gagasan yang tuntas.

### 3. TikTok Search SEO & Seamless Looping
- **SEO Caption**: Menyisipkan kata kunci pencarian utama pada 50 karakter pertama caption.
- **Clean Hashtags**: Menghasilkan 3–5 hashtag relevan tanpa karakter `#` (bebas spam tag).
- **Loop Strategy**: Rekomendasi bagaimana mengaitkan kalimat terakhir agar video berputar mulus tanpa jeda.

---

## 🖥️ SLIDE 6: TEKNOLOGI VISION & SMART CROPPING 9:16

Didukung oleh OpenCV dan filter visual FFmpeg untuk memastikan framing gambar vertikal sempurna:

| Mode Cropping | Deskripsi Teknis & Penggunaan |
| :--- | :--- |
| **`auto` (Cerdas)** | Secara otomatis mendeteksi apakah video berupa monolog/pidato (1 pembicara) atau podcast dialog (2 pembicara), lalu memilih mode terbaik. |
| **`speaker`** | **Active Speaker Tracking**: Menggunakan Haar Cascade dan analisis variasi intensitas area bibir (*Lip Motion*) untuk mengarahkan kamera ke orang yang sedang aktif berbicara. |
| **`split`** | **Dual-Speaker Split-Screen**: Membagi layar 9:16 menjadi dua bagian (Host di atas, Tamu di bawah) dengan perlindungan *Anti-Empty-Center* agar tidak mengambil ruang kosong di tengah panggung. |
| **`crop`** | Pemotongan tengah statis (*Center Crop*) 9:16 untuk video dengan pembicara selalu di tengah. |
| **`pad`** | Mode *Letterbox*: Mempertahankan seluruh area video asli dengan menambahkan bantalan hitam di atas dan bawah. |
| **`off`** | Mempertahankan rasio aspek dan resolusi asli video sumber. |

---

## 🖥️ SLIDE 7: INTEGRASI FLEKSIBEL MULTI-LLM (UNIVERSAL AI)

Aplikasi mendukung berbagai penyedia model kecerdasan buatan (*Provider-Agnostic*):

1. **Groq Cloud (Default)**:
   - Whisper: `whisper-large-v3` (transkripsi ultra-cepat).
   - LLM: `llama-3.3-70b-versatile` / `llama-3.1-8b-instant`.
2. **DeepSeek**:
   - `deepseek-chat` (V3) & `deepseek-reasoner` (R1) untuk penalaran semantik mendalam dengan biaya sangat hemat.
3. **OpenRouter**:
   - Mendukung ratusan model global (Claude 3.5 Sonnet, Mistral, Qwen, dll.).
4. **OpenAI Direct**:
   - `gpt-4o`, `gpt-4o-mini`, dan `whisper-1`.
5. **Google Gemini (Server-side)**:
   - Terintegrasi melalui Google GenAI SDK.

---

## 🖥️ SLIDE 8: ANTARMUKA WEB STUDIO & FITUR INTERAKTIF

Antarmuka web dibangun untuk kenyamanan kreator konten profesional:

- **Fleksibilitas Input Sumber Video**:
  - Input tautan langsung / URL YouTube.
  - Upload file lokal drag-and-drop (mendukung file besar hingga 2 GB).
  - *Demo Simulator 2 Pembicara* bawaan untuk pengujian instan tanpa kuota.
- **Kustomisasi Parameter**:
  - Pilihan niche: *Bisnis, Edukasi, Teknologi, Cerita/Curhat, Hiburan, Motivasi, Otomatis*.
  - Pengaturan durasi minimal & maksimal klip (15 s/d 180 detik).
  - Target jumlah klip (1 s/d 10 klip).
  - Pemilihan gaya cropping dan opsi hardsub subtitle.
- **Monitoring Progres Real-Time**:
  - Terminal log interaktif dan progress bar tahap demi tahap via streaming SSE.
- **Interactive Clip Card**:
  - Pemutar video dengan dukungan *Byte-Range Streaming* (seeking instan).
  - Tombol **1-Click Copy** untuk Salin Judul, Hook, Caption SEO, Hashtag, dan Call-to-Action (CTA).
  - Unduh mandiri file MP4, SRT, atau JSON metadata.
- **Riwayat Pekerjaan (*Job History*)**:
  - Menyimpan dan memuat ulang hasil generate sebelumnya tanpa perlu merender ulang.

---

## 🖥️ SLIDE 9: STRUKTUR OUTPUT & METADATA EKSPOR

Setiap proses menghasilkan folder terstruktur di dalam direktori `output/run-[timestamp]-[id]/`:

```text
output/run-20260830083011-abcd/
│
├── source/                      # File video asli sumber
├── audio/                       # Ekstraksi audio mono 16kHz (-16 LUFS)
├── transcript/
│   ├── transcript.json          # Transkrip lengkap dengan timestamp kata
│   └── transcript.srt           # Subtitle penuh video sumber
│
├── analysis/
│   └── llm_decision.json        # Log keputusan pemilihan momen oleh AI
│
├── clips/                       # HASIL AKHIR KLIP SIAP POSTING
│   ├── 01-judul-momen-emas.mp4  # Video vertikal 9:16 (1080x1920)
│   ├── 01-judul-momen-emas.srt  # Subtitle khusus klip ini
│   ├── 01-judul-momen-emas.json # Metadata lengkap (Hook, SEO, Hashtags)
│   ├── 02-judul-momen-kedua.mp4
│   └── ...
│
├── summary.md                   # Rekap presentasi & tabel konten siap posting
└── manifest.json                # Log teknis status pekerjaan
```

---

## 🖥️ SLIDE 10: MEKANISME KEANDALAN & FAIL-SAFE

Sistem didesain dengan ketahanan tingkat tinggi (*Zero-Failure Architecture*):

1. **Heuristic Fallback Engine**:
   - Jika koneksi API LLM eksternal mengalami *rate-limit* atau *timeout*, sistem secara otomatis beralih ke analisis berbasis algoritma kepadatan teks lokal (*Text Density & TF-IDF*) sehingga proses rendering video tetap selesai.
2. **Adaptive Timestamp Expansion**:
   - Jika titik potong transkrip terlalu mepet dengan batas minimum, sistem secara cerdas memperluas durasi ke kalimat sebelum/sesudahnya agar tuturan terdengar natural.
3. **Subtitles Graceful Fallback**:
   - Jika pustaka `libass` FFmpeg tidak terpasang di sistem operasi host, aplikasi tetap menghasilkan video MP4 bersih dan menyediakan file SRT mandiri tanpa menyebabkan error fatal.

---

## 🖥️ SLIDE 11: TECH STACK & SPESIFIKASI SISTEM

- **Frontend**: React 19, TypeScript, Tailwind CSS, Motion, Lucide Icons, Vite.
- **Backend API & Streaming**: Node.js, Express, Multer, Server-Sent Events (SSE).
- **Core Processing Engine**: Python 3.10+, FFmpeg, FFprobe, OpenCV (`cv2`), NumPy.
- **AI & Speech Models**: Groq Whisper Large v3, Universal OpenAI-Compatible API, Google GenAI SDK.
- **Deployment Ready**: Dockerfile, Docker Compose, Windows batch launcher (`run_windows.bat`), Linux/macOS support.

---

## 🖥️ SLIDE 12: DAMPAK BISNIS, EFISIENSI & PENUTUP

### Nilai Bisnis & Efisiensi Waktu
- ⏱️ **Penghematan Waktu**: Mengurangi 90% waktu kerja tim konten (dari 4 jam menjadi kurang dari 5 menit per episode).
- 📈 **Peningkatan Retensi**: Memaksimalkan *3-second view rate* dan *completion rate* akun media sosial melalui hook berbasis data.
- 🚀 **Skalabilitas Konten**: Memungkinkan 1 podcast panjang dipecah menjadi 5–10 konten siap unggah di TikTok, Instagram Reels, dan YouTube Shorts setiap harinya.

---

### ❓ Sesi Tanya Jawab (Q&A) & Uji Coba Langsung
*Terima kasih! Sistem siap diuji coba melalui Web Studio maupun Terminal CLI.*
