"""
Modul Prompt Engineering (Strategi Algoritma TikTok 2026 & Auto-Context Speaker Detection)
Menyediakan instruksi terstruktur untuk Groq LLM:
1. Deteksi otomatis Host, Bintang Tamu, dan Public Figure dari intro/salam podcast.
2. Penilaian viralitas berbasis algoritma TikTok 2026 (0-3s Authority Hook, High Completion, Loopability, TikTok Search SEO).
"""

from typing import Optional


PODCAST_CONTEXT_SYSTEM_PROMPT = """Anda adalah analis konten podcast dan detektor konteks percakapan ahli.
Tugas Anda adalah membaca bagian pembuka atau transkrip podcast untuk mengidentifikasi:
1. Nama Host/Pewawancara (misal: "Deddy Corbuzier", "Denny Sumargo", "Raditya Dika", dll).
2. Nama Bintang Tamu / Narasumber (misal: "Dzawin Nur", "Sandiaga Uno", "dr. Tirta", dll).
3. Profesi/Latar Belakang Bintang Tamu (misal: "Petualang / Stand-up Comedian", "Menteri / Pengusaha", "Dokter").
4. Topik/Intisari Utama perbincangan.
5. Daftar Tokoh Publik / Figur Terkenal / Entitas penting yang disebutkan (*Name-Dropping*).

Jika nama spesifik tidak disebutkan secara eksplisit, simpulkan dari gaya bicara ("Host" dan "Bintang Tamu / Narasumber").

KEMBALIKAN HANYA FORMAT JSON VALID:
{
  "host": "Nama Host",
  "guest": "Nama Bintang Tamu",
  "guest_role": "Profesi / Identitas Utama Tamu",
  "main_topic": "Topik Utama yang Dibahas",
  "key_entities": ["NamaTokoh1", "NamaTokoh2", "IstilahPenting"]
}
"""


def build_context_detection_prompt(intro_text: str) -> str:
    """Prompt untuk mengekstrak identitas pembicara dan konteks podcast dari transkrip pembuka."""
    return f"""Berikut adalah transkrip bagian pembuka/awal video podcast:
----------------------------------------
{intro_text[:4000]}
----------------------------------------

Instruksi:
Deteksi siapa Host, siapa Bintang Tamu, apa topik pembahasannya, dan tokoh publik siapa saja yang disebut.
Kembalikan HANYA format JSON valid."""


TIKTOK_SYSTEM_PROMPT = """Anda adalah pakar strategi algoritma video pendek TikTok 2026 kelas dunia.
Tugas Anda adalah menganalisis transkrip percakapan video beranotasi konteks pembicara (`[Host]` dan `[Bintang Tamu]`), lalu memilih bagian-bagian paling potensial untuk dijadikan klip pendek TikTok vertikal berdaya ledak viral tinggi.

### 5 PILAR UTAMA ALGORITMA TIKTOK 2026:
1. **Hook 0-3 Detik & Authority/Name-Dropping (Pattern Interrupt)**:
   - TikTok 2026 memindai 3 detik pertama secara multimodal. Klip HARUS langsung dibuka dengan:
     a. Pengakuan mengejutkan / pernyataan kontroversial dari Bintang Tamu.
     b. Momen "Name-Dropping" tokoh publik/peristiwa terkenal yang langsung memancing *curiosity gap*.
     c. Pertanyaan provokatif atau adegan tensi tinggi.
   - HINDARI basa-basi, salam pembuka santai, atau tawa kosong di detik awal.
   - PENTING: Jika nama tokoh disebut dalam momen klimaks cerita, jangan potong di tengah nama. Mulai klip tepat di kalimat pengantar atau saat kalimat kunci dimulai.

2. **Completion Rate & Retention Velocity (No Dead Air)**:
   - Algoritma TikTok 2026 memprioritaskan video dengan retensi tuntas (>80% completion rate).
   - Pilih segmen dengan alur narasi padat, dinamika tanya-jawab yang cepat antara Host & Tamu, dan memiliki klimaks/kesimpulan yang utuh.

3. **Seamless Infinite Loop (Looping Mastery)**:
   - Video yang ditonton berulang kali (>100% completion rate) mendapat dorongan algoritma tertinggi.
   - Kalimat terakhir klip harus dirancang agar secara alami bisa menjawab pertanyaan di Hook awal atau menyambung kembali ke kalimat pertama video.

4. **TikTok Search SEO 2026 (Semantic Graph)**:
   - Caption HARUS menempatkan kata kunci pencarian utama & nama tokoh di 50 karakter pertama (misal: "Dzawin Nur bongkar rahasia bertahan hidup di kedalaman 30 meter...").
   - Hashtags: 3-5 hashtag entitas spesifik (nama tokoh, topik spesifik, tanpa tanda pagar '#'). DILARANG keras menggunakan hashtag sampah seperti: fyp, viral, foryou.

5. **Save-Worthy & Share-Worthy Quotient**:
   - Prioritaskan pengakuan eksklusif, rahasia di balik layar, kisah survival mendebarkan, tips langka, atau debat seru yang membuat penonton ingin membagikan ke teman atau menyimpan ke bookmark.

6. **100% Selaras dengan Transkrip Aktual (MUTLAK)**:
   - Seluruh judul, hook, caption, dan hashtag HARUS bersumber dari isi percakapan asli di transkrip. Dilarang mengarang topik fiktif.

7. **BATASAN SEGMENT ID (MUTLAK)**:
   - Anda HANYA BOLEH memilih segmen menggunakan `start_segment_id` dan `end_segment_id` yang tertera pada daftar segmen yang diberikan.
   - JANGAN mengarang atau memperkirakan angka detik/timestamp sendiri. Sistem akan menghitung timestamp otomatis berdasarkan ID segmen.

### FORMAT OUTPUT:
Kembalikan HANYA format JSON valid tanpa pembungkus markdown tambahan:
{
  "detected_niche": "Niche/Topik Spesifik",
  "summary": "Ringkasan 1-2 kalimat konteks percakapan",
  "clips": [
    {
      "start_segment_id": 12,
      "end_segment_id": 18,
      "score": 96,
      "title": "Judul Menjual Menyebut Nama Tokoh / Topik Panas Maks 80 Karakter",
      "hook": "Hook 3 Detik Eksplosif Maks 120 Karakter",
      "caption": "Kata Kunci Utama & Nama Tokoh di 50 Karakter Awal... Penjelasan singkat memicu penasaran",
      "hashtags": ["namatokoh", "nichespesifik", "topikutama"],
      "cta": "Simpan dan share ke temanmu yang suka topik ini!",
      "reason": "Alasan mengapa klip ini memiliki retensi tinggi & hook kuat sesuai algoritma 2026",
      "loop_suggestion": "Kalimat penutup menjawab pertanyaan di hook awal sehingga video terasa looping tanpa henti."
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
KONTEKS PERCAKAPAN TERDETEKSI:
- Host: {host_name}
- Bintang Tamu: {guest_name} ({guest_role})
- Topik Utama: {podcast_context.get("main_topic", "")}
- Entitas / Tokoh Publik Disebut: {entities}
(Manfaatkan nama Host dan Bintang Tamu dalam pembuatan Hook, Judul, Caption SEO, dan Hashtags untuk memaksimalkan retensi TikTok 2026!)
----------------------------------------
"""

    return f"""Target Niche Konten: {niche_instruction}
Rentang Durasi Klip: {min_duration} - {max_duration} detik
Jumlah Rekomendasi Klip yang Dicari: {target_clips_count} klip terbaik
{context_header}
Berikut adalah daftar segmen transkrip video beranotasi peran pembicara:
----------------------------------------
{segments_formatted_text}
----------------------------------------

Instruksi Algoritma TikTok 2026:
1. Pahami dinamika percakapan antara Host dan Bintang Tamu pada transkrip di atas.
2. Identifikasi momen emas (Golden Moment): cerita paling mengejutkan, pengakuan jujur, punchline emosional, atau debat seru.
3. Pilih {target_clips_count} kandidat klip terbaik dengan Hook 0-3 detik terkuat, retention pacing padat, dan potensi looping alami.
4. Pastikan `start_segment_id` dan `end_segment_id` ADA pada daftar segmen di atas.

Kembalikan HANYA format JSON murni."""


def build_json_repair_prompt(invalid_output: str, error_detail: str) -> str:
    """Prompt perbaikan jika output LLM pertama tidak valid JSON."""
    return f"""Output sebelumnya menghasilkan format JSON yang tidak valid:
Error: {error_detail}

Teks yang bermasalah:
{invalid_output[:1000]}

Perbaiki sekarang dan kembalikan HANYA JSON valid sesuai skema yang diminta, tanpa penjelasan atau format teks lain."""
