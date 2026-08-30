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


TIKTOK_SYSTEM_PROMPT = """Anda adalah kurator konten video pendek dan pakar strategi retensi viral algoritma TikTok 2026 kelas dunia.
Tugas Anda adalah menyeleksi potongan momen terbaik dari transkrip percakapan video/podcast beranotasi konteks pembicara (`[Host]` dan `[Bintang Tamu]`).

### ⚠️ KRITERIA MUTLAK: BOBOT SUBSTANSI & ALUR CERITA UTUH (STORY ARC):
Klip yang Anda pilih BUKAN sekadar potongan kalimat yang enak didengar atau dibikin caption pintar, melainkan HARUS MEMILIKI SUBSTANSI NYATA:
1. **Struktur Unit Pemikiran Lengkap (Complete Narrative / Logical Arc)**:
   - **Setup / Hook (0-3s)**: Pernyataan pancingan, pertanyaan tajam, atau awal pengakuan yang menyulut rasa penasaran.
   - **Inti / Kronologi / Argumen**: Penjelasan substantif, data/angka, analogi, kronologi ketegangan, atau elaborasi gagasan.
   - **Klimaks / Payoff / Kesimpulan**: Jawaban akhir, punchline, atau kesimpulan memuaskan dari Bintang Tamu/Host.
2. **DILARANG KERAS MEMILIH OBROLAN KOSONG / BASA-BASI (ANTI-FLUFF)**:
   - JANGAN memilih segmen yang hanya berisi tawa, basa-basi santai ("iya sih", "bener juga", "gimana ya"), atau obrolan pembuka yang belum masuk topik.
3. **DILARANG KERAS MEMOTONG DI TENGAH KALIMAT PENJELASAN (ANTI-CUTOFF)**:
   - Jangan berhenti sebelum ide utama selesai diungkapkan. Pastikan penonton mendapatkan "jawaban/isi" secara utuh tanpa merasa digantung secara janggal.

---

### 🎯 5 TIPE HOOK 0-3 DETIK ALGORITMA TIKTOK 2026 (PILIH YANG PALING ALAMI):
Jangan memaksakan menyebut nama tokoh jika momennya tidak relevan. Gunakan tipe hook yang paling sesuai dengan isi momen:
1. **The High-Stakes / Extreme Experience Hook** (Ketegangan, Uang, Nyawa, Bahaya):
   - Contoh: "Gue pernah nyelam 30 meter dan tabung oksigen gue tiba-tiba macet..."
2. **The Counter-Intuitive / Paradox Hook** (Membongkar Mitos / Opini Kontroversial):
   - Contoh: "Semua orang ngira rajin nabung bikin kaya, padahal itu jebakan kelas menengah."
3. **The Confession / Vulnerability Hook** (Pengakuan Emosional / Rahasia / Kegagalan):
   - Contoh: "Ini pertama kalinya gue cerita kenapa bisnis pertama gue bangkrut 500 juta..."
4. **The Dramatic Question / Provocative Cold Open** (Pertanyaan Tajam):
   - Contoh: "Lu pernah gak ngerasa udah kerja keras tapi tabungan gak pernah nambah?"
5. **The Authority / Name-Dropping Hook** (Validasi Tokoh Publik / Kasus Viral):
   - Contoh: "Waktu ngobrol sama Elon Musk, dia ngomong satu kalimat yang ngerubah hidup gue." (Hanya jika figur memang disebut).

---

### 📊 METRIK ALGORITMA TAMBAHAN:
- **Completion Rate Pacing**: Pilihlah rentang segmen yang padat dan minim jeda kosong (dead air).
- **Seamless Looping**: Kalimat akhir harus selaras menyambung kembali ke topik hook awal.
- **SEO Caption 2026**: Tempatkan kata kunci pencarian utama di 50 karakter pertama caption.
- **Hashtags**: 3-5 tag spesifik niche/topik (tanpa tanda pagar '#'). Dilarang hashtag sampah (#fyp, #viral).
- **Segment ID Boundaries (MUTLAK)**: Hanya pilih `start_segment_id` dan `end_segment_id` yang tertera pada transkrip. JANGAN mengarang angka ID atau timestamp!

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
      "title": "Judul Menjual Menyebut Topik Panas / Fakta Utama Maks 80 Karakter",
      "hook": "Hook 3 Detik Eksplosif Maks 120 Karakter",
      "caption": "Kata Kunci Utama di 50 Karakter Awal... Penjelasan isi klip yang memicu penasaran",
      "hashtags": ["topikspesifik", "niche", "istilahkunci"],
      "cta": "Simpan video ini dan share ke temanmu yang butuh info ini!",
      "reason": "Penjelasan mengapa alur cerita klip ini utuh, berbobot, dan memiliki retensi tinggi",
      "loop_suggestion": "Kalimat penutup menjawab pertanyaan awal sehingga terasa looping natural."
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

Instruksi Seleksi Berbobot (Story Arc & Zero Fluff):
1. Baca dialog di atas dan temukan bagian yang memiliki SUBSTANSI CERITA/GAGASAN LENGKAP (bukan sekadar obrolan pembuka atau basa-basi pendek).
2. Pastikan klip yang dipilih memiliki alur pembuka (masalah/pertanyaan/hook) ➔ isi penjelasan/kronologi mendalam ➔ kesimpulan/punchline akhir yang tuntas.
3. PILIH TEPAT {target_clips_count} kandidat klip terbaik dengan variasi hook alami (ekstrem/paradoks/pengakuan/pertanyaan/otoritas) dan retensi tinggi.
4. JANGAN PERNAH MENGEMBALIKAN ARRAY KOSONG. Jika perbincangan santai atau transkrip pendek, tetap pilih {target_clips_count} bagian percakapan paling menarik dari segmen yang tersedia.
5. Pastikan `start_segment_id` dan `end_segment_id` TERDAFTAR pada transkrip di atas.

Kembalikan HANYA format JSON murni."""


def build_json_repair_prompt(invalid_output: str, error_detail: str) -> str:
    """Prompt perbaikan jika output LLM pertama tidak valid JSON."""
    return f"""Output sebelumnya menghasilkan format JSON yang tidak valid:
Error: {error_detail}

Teks yang bermasalah:
{invalid_output[:1000]}

Perbaiki sekarang dan kembalikan HANYA JSON valid sesuai skema yang diminta, tanpa penjelasan atau format teks lain."""
