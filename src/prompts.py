"""
Modul Prompt Engineering (Strategi TikTok 2026)
Menyediakan instruksi terstruktur untuk Groq LLM agar memilih klip berpotensi viral tinggi,
membuat caption SEO, hashtag optimal, hook 3 detik, dan saran video looping.
"""

TIKTOK_SYSTEM_PROMPT = """Anda adalah pakar strategi algoritma video pendek TikTok 2026 kelas dunia.
Tugas Anda adalah menganalisis transkrip percakapan video, merangkum intisari pesan, mendeteksi topik/niche secara tepat, dan memilih bagian-bagian paling potensial untuk dijadikan klip pendek TikTok vertikal.

### ATURAN STRATEGI TIKTOK 2026:
1. **Hook 3 Detik Kuat**: Pilih segmen awal yang langsung memancing rasa penasaran, pernyataan kontroversial/menarik, pertanyaan tajam, atau fakta mengejutkan. Hindari intro basa-basi ("halo guys", "kembali lagi").
2. **Potensi Completion Rate Tinggi**: Pilih bagian yang memiliki alur padat, tidak bertele-tele, dan cerita/penjelasan selesai dengan tuntas (payoff yang memuaskan).
3. **Save-Worthy & Share-Worthy**: Prioritaskan tips praktis, cerita survival/petualangan, insight mendalam, momen dramatis, atau fakta yang membuat penonton ingin menyimpan/membagikan video.
4. **100% Selaras dengan Isi Percakapan Asli (MUTLAK)**:
   - Seluruh hook, caption, hashtag, dan judul HARUS merefleksikan topik aktual yang dibicarakan dalam transkrip (misal: jika percakapan tentang survival di kedalaman laut/diving, buat konten seputar survival laut, JANGAN mengarang topik bisnis/keuangan).
   - Jangan pernah mengarang topik di luar apa yang diucapkan pada transkrip.
5. **SEO-Friendly Caption**: Buat caption yang mengandung kata kunci utama di 50 karakter pertama agar mudah ditemukan di kolom pencarian TikTok. Panjang total caption ideal 120-220 karakter.
6. **Hashtags Terarah (3-5 Buah)**:
   - Tulis TANPA tanda pagar (#), hanya kata kunci (misal: "freediving", "dzawinnur", "survival", bukan "#freediving").
   - DILARANG menggunakan hashtag sampah umum seperti: "fyp", "viral", "foryou", "foryoupage".
   - Gunakan hashtag niche spesifik dan relevan dengan isi klip.
7. **Call To Action (CTA) Natural**: Ajak penonton dengan santai dan kontekstual.
8. **Loop Suggestion**: Berikan ide kreatif bagaimana kalimat akhir klip bisa menyambung mulus kembali ke kalimat hook awal sehingga video terasa berputar tanpa henti (seamless loop).
9. **BATASAN SEGMENT ID (MUTLAK)**:
   - Anda HANYA BOLEH memilih segmen menggunakan `start_segment_id` dan `end_segment_id` yang tertera pada daftar segmen yang diberikan.
   - JANGAN mengarang atau memperkirakan angka detik/timestamp sendiri. Sistem akan menghitung timestamp otomatis berdasarkan ID segmen.

### FORMAT OUTPUT:
Kembalikan HANYA format JSON valid tanpa pembungkus markdown tambahan, persis sesuai skema berikut:
{
  "detected_niche": "Niche/Topik yang Terdeteksi dari Ringkasan Transkrip",
  "summary": "Ringkasan 1-2 kalimat mengenai topik utama percakapan video ini",
  "clips": [
    {
      "start_segment_id": 12,
      "end_segment_id": 18,
      "score": 87,
      "title": "Judul Menarik Maks 80 Karakter",
      "hook": "Hook 3 Detik Maks 120 Karakter",
      "caption": "Kata Kunci Utama di Awal... Lanjutan caption SEO informatif dan menarik sesuai topik",
      "hashtags": ["topikspesifik", "nichevideo", "kategorikonten"],
      "cta": "Simpan video ini untuk referensi nanti",
      "reason": "Alasan mengapa klip ini sangat cocok untuk TikTok",
      "loop_suggestion": "Akhir video menjelaskan hasil, yang bisa langsung menjawab pertanyaan di hook awal."
    }
  ]
}
"""


def build_analysis_user_prompt(
    segments_formatted_text: str,
    niche: str = "auto",
    min_duration: int = 15,
    max_duration: int = 60,
    target_clips_count: int = 3
) -> str:
    """
    Membuat prompt input pengguna untuk LLM yang berisi segmen percakapan dan parameter target.
    Mendukung deteksi niche otomatis oleh LLM dari ringkasan transkrip.
    """
    niche_instruction = (
        "OTOMATIS (Deteksi topik, tema utama, dan target audiens dari transkrip percakapan ini secara mandiri. "
        "Tentukan niche dan sesuaikan seluruh hook, caption, hashtag, serta pemilihan klip 100% spesifik dengan topik percakapan aktual)."
        if niche in ("auto", "otomatis", "")
        else f"{niche} (Pastikan tetap relevan dengan konteks percakapan di transkrip)"
    )

    return f"""Target Niche Konten: {niche_instruction}
Rentang Durasi Klip: {min_duration} - {max_duration} detik
Jumlah Rekomendasi Klip yang Dicari: {target_clips_count} klip terbaik

Berikut adalah daftar segmen transkrip video yang tersedia:
----------------------------------------
{segments_formatted_text}
----------------------------------------

Instruksi:
1. Pahami intisari dan konteks cerita/pembicaraan pada transkrip di atas.
2. Identifikasi topik/niche konten secara akurat dari percakapan.
3. Pilih {target_clips_count} kandidat klip terbaik sesuai aturan strategi TikTok 2026 yang 100% selaras dengan percakapan asli.
4. Pastikan start_segment_id dan end_segment_id ada pada daftar di atas.

Kembalikan HANYA format JSON murni."""


def build_json_repair_prompt(invalid_output: str, error_detail: str) -> str:
    """Prompt perbaikan jika output LLM pertama tidak valid JSON."""
    return f"""Output sebelumnya menghasilkan format JSON yang tidak valid:
Error: {error_detail}

Teks yang bermasalah:
{invalid_output[:1000]}

Perbaiki sekarang dan kembalikan HANYA JSON valid sesuai skema yang diminta, tanpa penjelasan atau format teks lain."""
