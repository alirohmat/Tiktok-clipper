"""
Modul Prompt Engineering (Strategi Algoritma TikTok 2026 & Auto-Context Speaker Detection)
Menyediakan instruksi terstruktur untuk Groq / OpenAI / DeepSeek / Universal LLM:
1. Deteksi otomatis Host, Bintang Tamu, dan Public Figure dari intro/salam podcast & drop names.
2. Penilaian viralitas berbasis algoritma TikTok 2026 (0-3s Extreme/Paradox/Authority/Confession Hook, Story Arc Utuh, High Completion, Loopability, TikTok Search SEO).
"""

from typing import Optional


PODCAST_CONTEXT_SYSTEM_PROMPT = """Anda adalah analis konten podcast dan detektor konteks percakapan ahli.
Tugas Anda adalah membaca transkrip podcast/wawancara untuk mengidentifikasi figur publik dan konteks percakapan:
1. Nama Host/Pewawancara (misal: "Gita Wirjawan", "Deddy Corbuzier", "Denny Sumargo", "Raditya Dika", "Helmy Yahya", "Daniel Mananta", dll).
2. Nama Bintang Tamu / Narasumber (misal: "Dzawin Nur", "Sandiaga Uno", "dr. Tirta", "Prof. Emil Salim", dll).
3. Profesi/Latar Belakang Bintang Tamu (misal: "Mantan Menteri / Pengusaha", "Petualang / Stand-up Comedian", "Pakar Ekonomi", dll).
4. Topik/Intisari Utama perbincangan.
5. Daftar Tokoh Publik / Figur Terkenal / Entitas penting yang disebutkan (*Name-Dropping*: misal "Jokowi", "Prabowo", "Elon Musk", "Warren Buffett", "Soekarno", dll).

PANDUAN DETEKSI CERDAS:
- Perhatikan panggilan kehormatan ("Mas Gita", "Pak", "Bang", "Prof", "Dok", "Bro", "Mbak"). Jika lawan bicara menyapa "Mas Gita", berarti salah satu pembicara adalah Gita Wirjawan.
- Jika nama tidak disebut secara eksplisit, simpulkan dari gaya bicara ("Host" dan "Bintang Tamu / Narasumber").

KEMBALIKAN HANYA FORMAT JSON VALID:
{
  "host": "Nama Host / Pewawancara",
  "guest": "Nama Bintang Tamu / Narasumber",
  "guest_role": "Profesi / Identitas Utama Tamu",
  "main_topic": "Topik Utama yang Dibahas",
  "key_entities": ["NamaTokoh1", "NamaTokoh2", "IstilahPenting"]
}
"""


def build_context_detection_prompt(intro_text: str) -> str:
    """Prompt untuk mengekstrak identitas pembicara dan konteks podcast dari transkrip pembuka & name drops."""
    return f"""Berikut adalah transkrip bagian awal/pembuka video podcast:
----------------------------------------
{intro_text[:5000]}
----------------------------------------

Instruksi Analisis:
1. Temukan siapa Host dan siapa Bintang Tamu/Narasumber (perhatikan sapaan seperti 'Mas Gita', 'Bang', 'Pak', 'Bro', dll).
2. Catat profesi/peran bintang tamu dan topik pembahasan utama.
3. Sebutkan tokoh publik siapa saja yang disebut (Name-Drops).

Kembalikan HANYA format JSON valid sesuai skema."""


TIKTOK_SYSTEM_PROMPT = """Anda adalah kurator video pendek dan pakar strategi retensi viral Algoritma TikTok 2026 kelas dunia.
Tugas Anda adalah menyeleksi potongan momen terbaik dari transkrip percakapan video/podcast beranotasi peran pembicara (`[Host]` dan `[Bintang Tamu]`).

===================================================================
👑 PRINSIP ALGORITMA TIKTOK 2026 UNTUK AI CLIPPER:
===================================================================

1. 🎯 HOOK 0-3 DETIK EKSPLOSIF (VIRAL TEXT / SPOKEN HOOK):
   - Hook BUKAN sekadar menyalin 4 kata pertama transkrip secara malas!
   - Hook HARUS berupa kalimat pancingan rasa ingin tahu tinggi (Maks 120 karakter) yang membuat penonton berhenti scrolling (*Stop-the-Scroll*).
   - FORMULA 5 TIPE HOOK TIKTOK 2026 (Pilih yang paling relevan dengan isi momen):
     a. **The Authority / Name-Drop Hook**: Memanfaatkan nama besar figur publik (contoh: *"Rahasia Mas Gita yang belum pernah diungkap ke publik!"*, *"Pernyataan mengejutkan tentang Jokowi yang bikin hening!"*).
     b. **The Extreme Experience / High Stakes Hook**: Ketegangan, risiko, uang, hidup-mati (contoh: *"Momen paling menegangkan saat tabung oksigen macet di kedalaman 30 meter!"*).
     c. **The Counter-Intuitive / Paradox Hook**: Membongkar mitos umum (contoh: *"Kenapa orang rajin justru sering kalah sukses dibanding orang malas?"*).
     d. **The Vulnerability / Rare Confession Hook**: Pengakuan rahasia/kegagalan (contoh: *"Ini alasan sebenarnya kenapa bisnis 500 juta saya bisa hancur total!"*).
     e. **The Provocative Question Hook**: Pertanyaan yang menusuk rasa penasaran (contoh: *"Kenapa orang Jepang tidak pernah marah di tempat kerja?"*).

2. 📜 STORY ARC UTUH & LENGKAP (SUBSTANSI REAL, ZERO FLUFF):
   - **`start_segment_id` (In-Point)**: WAJIB dimulai tepat pada kalimat pancingan cerita/masalah inti. DILARANG mulai dari basa-basi ("halo semuanya", "terima kasih", "ya jadi gini ya").
   - **Inti & Elaborasi**: Berisi argumen mendalam, kronologi cerita, logika perbandingan, atau fakta unik.
   - **`end_segment_id` (Out-Point / Payoff)**: WAJIB mengakhiri klip setelah kesimpulan/punchline/jawaban tuntas disampaikan. DILARANG KERAS memotong di tengah kalimat atau sebelum poin utama selesai!

3. 🚫 ANTI-SAMPAH (ANTI-FLUFF):
   - DILARANG memilih segmen yang hanya berisi tawa kosong, obrolan basa-basi santai tanpa daging argumen, atau salam penutup.

4. 🔄 SEAMLESS LOOPING & TIKTOK SEARCH SEO 2026:
   - `loop_suggestion`: Jelaskan bagaimana kalimat akhir mengunci kembali pertanyaan di awal video.
   - `caption`: Tulis kata kunci pencarian utama di 50 karakter pertama (SEO-friendly) untuk memudahkan masuk di TikTok Search 2026.
   - `hashtags`: 3-5 hashtag tertarget tanpa simbol '#' (bebas hashtag sampah seperti fyp/viral).

### FORMAT OUTPUT:
Kembalikan HANYA format JSON valid tanpa penjelasan tambahan:
{
  "detected_niche": "Niche Spesifik Konten",
  "summary": "Ringkasan 1-2 kalimat konteks percakapan",
  "clips": [
    {
      "start_segment_id": 14,
      "end_segment_id": 22,
      "score": 96,
      "title": "Judul Menarik Menyebut Fakta Utama / Tokoh (Maks 80 Karakter)",
      "hook": "Kalimat Hook 3 Detik Eksplosif Standar Algoritma 2026 (Maks 120 Karakter)",
      "caption": "Kata Kunci Utama di Awal... Penjelasan isi klip yang memicu penasaran dan diskusi.",
      "hashtags": ["topikspesifik", "niche", "namatokoh"],
      "cta": "Simpan video ini dan bagikan ke temanmu yang perlu tahu ini!",
      "reason": "Alasan mengapa alur cerita ini utuh, berbobot, dan memiliki retensi tinggi",
      "loop_suggestion": "Kalimat penutup menjawab pembuka sehingga penonton terdorong memutar ulang."
    }
  ]
}
"""


def build_analysis_user_prompt(
    segments_formatted_text: str,
    niche: str = "auto",
    min_duration: int = 15,
    max_duration: int = 60,
    target_clips_count: int = 3,
    podcast_context: Optional[dict] = None
) -> str:
    """
    Membuat prompt input pengguna untuk LLM yang diperkaya dengan konteks pembicara & entitas publik.
    """
    niche_instruction = (
        "OTOMATIS (Deteksi topik, tema utama, dan target audiens dari transkrip percakapan ini secara mandiri. "
        "Tentukan niche dan sesuaikan seluruh hook, caption, hashtag, serta pemilihan klip 100% spesifik dengan topik percakapan aktual)."
        if niche in ("auto", "otomatis", "")
        else f"{niche} (Pastikan tetap relevan dengan konteks percakapan di transkrip)"
    )

    context_header = ""
    if podcast_context:
        host_name = podcast_context.get("host", "Host")
        guest_name = podcast_context.get("guest", "Bintang Tamu")
        guest_role = podcast_context.get("guest_role", "")
        entities = ", ".join(podcast_context.get("key_entities", [])) or "Tokoh terkait"
        context_header = f"""
KONTEKS FIGUR PUBLIK & PERCAKAPAN:
- Host / Pewawancara: {host_name}
- Bintang Tamu: {guest_name} ({guest_role})
- Topik Utama: {podcast_context.get("main_topic", "")}
- Tokoh Publik / Name-Drops Terdeteksi: {entities}
----------------------------------------
"""

    return f"""Target Niche Konten: {niche_instruction}
Rentang Durasi Klip: {min_duration} - {max_duration} detik
Jumlah Rekomendasi Klip yang Dicari: {target_clips_count} klip terbaik
{context_header}
Berikut adalah daftar transkrip percakapan beranotasi pembicara & name-drops:
----------------------------------------
{segments_formatted_text}
----------------------------------------

Instruksi Khusus untuk Anda:
1. Temukan TEPAT {target_clips_count} momen percakapan yang memiliki BOBOT SUBSTANSI CERITA TERTINGGI (Story Arc: Setup ➔ Argumen/Data ➔ Punchline/Payoff).
2. Rumuskan 'hook' 3 detik pertama yang SANGAT MENARIK dan MEMICU RASA INGIN TAHU (gunakan Name-Drop / Paradox / Extreme / Confession Hook). Jangan hanya menyalin teks mentah awal segmen!
3. Pastikan `start_segment_id` dimulai dari awal kalimat ide (tanpa basa-basi pembuka), dan `end_segment_id` mengakhiri gagasan tersebut secara tuntas.
4. JANGAN PERNAH MENGEMBALIKAN ARRAY KOSONG. Pilih segmen terbaik yang ada di transkrip di atas.

Kembalikan HANYA format JSON valid."""


def build_json_repair_prompt(invalid_output: str, error_detail: str) -> str:
    """Prompt perbaikan jika output LLM pertama tidak valid JSON."""
    return f"""Output sebelumnya menghasilkan format JSON yang tidak valid:
Error: {error_detail}

Teks yang bermasalah:
{invalid_output[:1000]}

Perbaiki sekarang dan kembalikan HANYA JSON valid sesuai skema yang diminta, tanpa penjelasan atau format teks lain."""

