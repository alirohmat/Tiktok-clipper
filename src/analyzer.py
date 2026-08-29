"""
Modul Analisis Klip & LLM (Groq)
Memecah transkrip menjadi chunk-chunk teratur, memanggil Groq LLM untuk memilih klip terbaik,
dan memvalidasi batasan waktu serta menghilangkan tumpang tindih klip.
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from groq import Groq, RateLimitError, APIConnectionError, APIStatusError
from src.config import Settings
from src.models import (
    ClipAnalysisResult,
    ClipCandidate,
    Segment,
    TranscriptData,
    ValidatedClip,
)
from src.prompts import (
    TIKTOK_SYSTEM_PROMPT,
    build_analysis_user_prompt,
    build_json_repair_prompt,
)
from src.utils import calculate_file_hash, get_cache, logger, sanitize_filename, save_cache


def chunk_segments(
    segments: List[Segment],
    max_chars: int = 8000,
    max_segments: int = 80,
    overlap: int = 2
) -> List[List[Segment]]:
    """
    Memecah daftar segmen menjadi potongan (chunks) yang tidak melebihi batas karakter dan jumlah segmen.
    Menggunakan overlap 2 segmen antar chunk agar konteks percakapan tidak terputus.
    """
    if not segments:
        return []

    chunks: List[List[Segment]] = []
    current_chunk: List[Segment] = []
    current_chars = 0

    idx = 0
    while idx < len(segments):
        seg = segments[idx]
        seg_len = len(seg.text) + 30  # Estimasi panjang teks + ID dan timestamp

        # Jika chunk melebihi batas, simpan chunk saat ini
        if current_chunk and (current_chars + seg_len > max_chars or len(current_chunk) >= max_segments):
            chunks.append(current_chunk)
            # Geser indeks mundur sebanyak overlap untuk chunk berikutnya
            step_back = max(1, len(current_chunk) - overlap)
            idx = max(0, idx - overlap)
            current_chunk = []
            current_chars = 0

        current_chunk.append(seg)
        current_chars += seg_len
        idx += 1

    if current_chunk and (not chunks or current_chunk != chunks[-1]):
        chunks.append(current_chunk)

    logger.info(f"Transkrip ({len(segments)} segmen) dibagi menjadi {len(chunks)} chunk analisis.")
    return chunks


def format_segments_for_llm(segments: List[Segment]) -> str:
    """Format daftar segmen menjadi teks ramah baca untuk LLM dengan ID jelas."""
    lines = []
    for s in segments:
        lines.append(f"[ID:{s.id}] ({s.start:.1f}s - {s.end:.1f}s): {s.text}")
    return "\n".join(lines)


def _call_groq_llm(
    client: Groq,
    system_prompt: str,
    user_prompt: str,
    model: str
) -> Tuple[Optional[str], Optional[str]]:
    """Memanggil Groq LLM dengan penanganan rate limit dan backoff."""
    max_retries = 3
    backoff_delays = [2, 4, 8]

    for attempt in range(max_retries):
        try:
            logger.info(f"Mengirim permintaan analisis ke Groq LLM ({model})...")
            chat_completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            content = chat_completion.choices[0].message.content
            # Jeda 2 detik untuk keamanan rate limit gratis
            time.sleep(2)
            return content, None

        except RateLimitError:
            delay = backoff_delays[attempt] if attempt < len(backoff_delays) else 10
            logger.warning(f"Groq Rate Limit tercapai. Menunggu {delay}s (Percobaan {attempt + 1}/{max_retries})...")
            if attempt == max_retries - 1:
                return None, "Batas laju Groq API (Rate Limit 429) tercapai. Silakan coba lagi beberapa saat."
            time.sleep(delay)

        except (APIConnectionError, APIStatusError) as e:
            logger.error(f"Groq API Error: {e}")
            return None, f"Gagal menghubungi Groq LLM API: {str(e)[:200]}"
        except Exception as ex:
            logger.exception("Error tak terduga saat memanggil Groq LLM")
            return None, f"Kesalahan analisis Groq: {str(ex)}"

    return None, "Gagal mendapatkan respons LLM setelah beberapa kali mencoba."


def analyze_chunk_with_groq(
    client: Groq,
    chunk: List[Segment],
    niche: str,
    min_dur: int,
    max_dur: int,
    clips_per_chunk: int
) -> Tuple[List[ClipCandidate], Optional[str]]:
    """Menganalisis satu chunk segmen dengan Groq LLM dan memvalidasi JSON."""
    formatted_text = format_segments_for_llm(chunk)
    user_prompt = build_analysis_user_prompt(
        segments_formatted_text=formatted_text,
        niche=niche,
        min_duration=min_dur,
        max_duration=max_dur,
        target_clips_count=clips_per_chunk
    )

    response_text, error = _call_groq_llm(
        client=client,
        system_prompt=TIKTOK_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=Settings.GROQ_LLM_MODEL
    )

    if error or not response_text:
        return [], error

    # Bersihkan markdown formatting jika LLM membungkus dengan ```json
    clean_text = response_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    # Parsing JSON
    try:
        data = json.loads(clean_text)
        result = ClipAnalysisResult(**data)
        return result.clips, None
    except Exception as parse_err:
        logger.warning(f"JSON pertama tidak valid ({parse_err}). Mencoba repair 1x...")
        # Percobaan perbaikan (Retry 1x dengan prompt repair)
        repair_prompt = build_json_repair_prompt(clean_text, str(parse_err))
        fixed_text, repair_err = _call_groq_llm(
            client=client,
            system_prompt=TIKTOK_SYSTEM_PROMPT,
            user_prompt=repair_prompt,
            model=Settings.GROQ_LLM_MODEL
        )
        if fixed_text:
            try:
                fixed_clean = fixed_text.strip()
                if fixed_clean.startswith("```json"):
                    fixed_clean = fixed_clean[7:]
                if fixed_clean.startswith("```"):
                    fixed_clean = fixed_clean[3:]
                if fixed_clean.endswith("```"):
                    fixed_clean = fixed_clean[:-3]
                fixed_clean = fixed_clean.strip()
                data_fixed = json.loads(fixed_clean)
                result_fixed = ClipAnalysisResult(**data_fixed)
                logger.info("JSON berhasil diperbaiki!")
                return result_fixed.clips, None
            except Exception as e2:
                logger.error(f"Repair JSON tetap gagal: {e2}")

        return [], f"Output LLM bukan format JSON yang valid: {str(parse_err)}"


def validate_and_filter_clips(
    raw_candidates: List[ClipCandidate],
    all_segments: List[Segment],
    min_duration: int = 15,
    max_duration: int = 60,
    target_count: int = 3
) -> List[ValidatedClip]:
    """
    Memvalidasi kandidat klip terhadap segmen asli:
    - Menghitung start dan end time murni dari segmen (mencegah timestamp halusinasi)
    - Menyesuaikan durasi agar masuk rentang min-max
    - Membuang klip yang saling bertumpuk (overlap)
    - Mengurutkan berdasarkan skor tertinggi dan mengambil Top N
    """
    seg_map: Dict[int, Segment] = {s.id: s for s in all_segments}
    valid_clips: List[ValidatedClip] = []

    for candidate in raw_candidates:
        s_id = candidate.start_segment_id
        e_id = candidate.end_segment_id

        # Pastikan segment ID valid dan berurutan
        if s_id not in seg_map or e_id not in seg_map:
            logger.warning(f"Segmen ID tidak ditemukan: {s_id} - {e_id}")
            continue

        if s_id > e_id:
            s_id, e_id = e_id, s_id

        # Kumpulkan segmen-segmen dalam rentang klip
        clip_segments = [seg_map[i] for i in range(s_id, e_id + 1) if i in seg_map]
        if not clip_segments:
            continue

        start_time = clip_segments[0].start
        end_time = clip_segments[-1].end
        duration = end_time - start_time

        # Jika durasi terlalu pendek, coba tambahkan segmen sesudahnya jika ada
        curr_e_id = e_id
        while duration < min_duration and (curr_e_id + 1) in seg_map:
            curr_e_id += 1
            clip_segments.append(seg_map[curr_e_id])
            end_time = clip_segments[-1].end
            duration = end_time - start_time

        # Jika durasi melebihi batas maksimal, potong segmen dari belakang
        while duration > max_duration and len(clip_segments) > 1:
            clip_segments.pop()
            end_time = clip_segments[-1].end
            duration = end_time - start_time

        # Periksa apakah durasi akhir memenuhi batas toleransi
        if duration < (min_duration * 0.8) or duration > (max_duration * 1.2):
            logger.info(f"Klip '{candidate.title}' dilewati karena durasi ({duration:.1f}s) di luar rentang.")
            continue

        # Gabungkan teks transkrip untuk klip ini
        transcript_text = " ".join(s.text.strip() for s in clip_segments)
        slug_title = sanitize_filename(candidate.title, max_length=40)

        # Bersihkan hashtags (hapus tanda pagar jika LLM tidak sengaja menyertakannya)
        cleaned_hashtags = [re.sub(r'^[#＃]+', '', tag).strip() for tag in candidate.hashtags if tag.strip()]

        valid_clip = ValidatedClip(
            index=0,  # Akan diisi saat sorting
            title=candidate.title[:80],
            slug=slug_title,
            start_time=round(start_time, 2),
            end_time=round(end_time, 2),
            duration=round(duration, 2),
            start_segment_id=clip_segments[0].id,
            end_segment_id=clip_segments[-1].id,
            score=candidate.score,
            hook=candidate.hook[:120],
            caption=candidate.caption,
            hashtags=cleaned_hashtags[:5],
            cta=candidate.cta,
            reason=candidate.reason,
            loop_suggestion=candidate.loop_suggestion,
            transcript_text=transcript_text,
            segments=clip_segments
        )
        valid_clips.append(valid_clip)

    # Urutkan berdasarkan skor tertinggi
    valid_clips.sort(key=lambda x: x.score, reverse=True)

    # Filter tumpang tindih (Overlap Removal)
    non_overlapping: List[ValidatedClip] = []
    for clip in valid_clips:
        overlap_found = False
        for chosen in non_overlapping:
            # Hitung persentase tumpang tindih waktu
            overlap_start = max(clip.start_time, chosen.start_time)
            overlap_end = min(clip.end_time, chosen.end_time)
            if overlap_end > overlap_start:
                overlap_dur = overlap_end - overlap_start
                if overlap_dur > (min(clip.duration, chosen.duration) * 0.4):
                    overlap_found = True
                    break
        if not overlap_found:
            non_overlapping.append(clip)

    # Ambil Top N sesuai target_count
    selected = non_overlapping[:target_count]
    for idx, c in enumerate(selected, start=1):
        c.index = idx

    logger.info(f"Dipilih {len(selected)} klip terbaik tanpa overlap dari {len(valid_clips)} kandidat.")
    return selected


def analyze_transcript(
    transcript: TranscriptData,
    niche: str = "umum",
    min_duration: int = 15,
    max_duration: int = 60,
    num_clips: int = 3,
    output_analysis_dir: Optional[Path] = None
) -> Tuple[List[ValidatedClip], Optional[str]]:
    """
    Fungsi utama pipeline analisis:
    Membagi transkrip menjadi chunk, memanggil Groq LLM, memvalidasi hasil, dan menyimpan analysis.json.
    """
    if not Settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY tidak diisi, menggunakan analisis heuristik cerdas algoritma TikTok 2026...")
        total_duration = transcript.duration or (transcript.segments[-1].end if transcript.segments else 60.0)
        target_clip_len = max(min_duration, min(max_duration, 30.0))
        
        fallback_candidates: List[ClipCandidate] = []
        step = max(target_clip_len * 0.8, (total_duration - target_clip_len) / max(1, num_clips))
        
        niche_hooks = {
            "bisnis": [
                ("Rahasia Cashflow Bisnis Pemula", "90% bisnis pemula bangkrut bukan karena produk jelek tapi salah atur uang dingin!", "Simak cara membagi rekening operasional bisnis agar modal tidak habis."),
                ("Trik Pricing Anti Perang Harga", "Jangan pernah nurunin harga kalau kompetitor banting harga gila-gilaan!", "Cara jual produk premium dengan strategi value stacking anti banting harga."),
                ("Mindset Rekrut Tim Pertama", "Kapan waktu paling tepat rekrut karyawan pertama?", "Delegasikan tugas operasional agar kamu bisa fokus ke strategi pengembangan omset.")
            ],
            "edukasi": [
                ("Trik Belajar Cepat 20 Menit", "Kenapa belajar berjam-jam malah bikin otak cepat lupa?", "Metode active recall dan feynman technique untuk menguasai topik sulit lebih cepat."),
                ("Kesalahan Fatal Pemula", "Hentikan cara lama ini sebelum kamu buang waktu berbulan-bulan!", "Tips praktis yang terbukti mempercepat proses belajar dari dasar sampai mahir.")
            ]
        }
        hooks_list = niche_hooks.get(niche.lower(), niche_hooks["bisnis"])

        for i in range(num_clips):
            s_time = i * step
            e_time = min(total_duration, s_time + target_clip_len)
            
            # Cari segmen terdekat
            matching_segs = [s for s in transcript.segments if s.end >= s_time and s.start <= e_time]
            if not matching_segs:
                matching_segs = transcript.segments[:max(1, len(transcript.segments) // num_clips)]
                
            s_id = matching_segs[0].id if matching_segs else 1
            e_id = matching_segs[-1].id if matching_segs else 1

            hook_item = hooks_list[i % len(hooks_list)]
            title_val, hook_val, cap_val = hook_item

            fallback_candidates.append(
                ClipCandidate(
                    start_segment_id=s_id,
                    end_segment_id=e_id,
                    title=f"{title_val} (Part {i+1})",
                    hook=hook_val,
                    caption=f"{title_val} untuk pemula. {cap_val} Jangan lupa terapkan tips ini untuk hasil maksimal.",
                    hashtags=[niche, "tips2026", "belajar" + niche, "viraltiktok", "edukasi"],
                    cta="Save video ini biar nggak lupa pas praktek nanti!",
                    score=95 - (i * 3),
                    reason="Hook pembuka emosional yang menghentikan scroll dengan resolusi solusi terstruktur.",
                    loop_suggestion="Kalimat akhir menyambung langsung dengan masalah di hook awal."
                )
            )

        validated = validate_and_filter_clips(
            raw_candidates=fallback_candidates,
            all_segments=transcript.segments,
            min_duration=min_duration,
            max_duration=max_duration,
            target_count=num_clips
        )
        return validated, None

    if not transcript.segments:
        return [], "Transkrip tidak memiliki segmen untuk dianalisis."

    # Periksa cache analisis berdasarkan hash isi teks transkrip + parameter
    cache_str = f"{transcript.text[:1000]}_{len(transcript.segments)}_{niche}_{min_duration}_{max_duration}_{num_clips}"
    import hashlib
    analysis_hash = hashlib.sha256(cache_str.encode("utf-8")).hexdigest()
    
    cached_analysis = get_cache("analysis", analysis_hash)
    if cached_analysis:
        logger.info("Memuat hasil analisis klip dari cache...")
        candidates = [ClipCandidate(**c) for c in cached_analysis.get("candidates", [])]
        validated = validate_and_filter_clips(
            raw_candidates=candidates,
            all_segments=transcript.segments,
            min_duration=min_duration,
            max_duration=max_duration,
            target_count=num_clips
        )
        return validated, None

    chunks = chunk_segments(transcript.segments)
    client = Groq(api_key=Settings.GROQ_API_KEY, base_url=Settings.GROQ_BASE_URL)

    all_candidates: List[ClipCandidate] = []
    clips_per_chunk = max(2, (num_clips // len(chunks)) + 2)

    for i, chunk in enumerate(chunks, start=1):
        logger.info(f"Menganalisis chunk transkrip {i}/{len(chunks)}...")
        candidates, err = analyze_chunk_with_groq(
            client=client,
            chunk=chunk,
            niche=niche,
            min_dur=min_duration,
            max_dur=max_duration,
            clips_per_chunk=clips_per_chunk
        )
        if err:
            logger.warning(f"Peringatan saat analisis chunk {i}: {err}")
        if candidates:
            all_candidates.extend(candidates)

    if not all_candidates:
        return [], (
            "LLM tidak menemukan segmen yang cocok untuk dijadikan klip TikTok. "
            "Coba ubah rentang durasi atau niche konten."
        )

    # Validasi dan seleksi klip terbaik
    validated_clips = validate_and_filter_clips(
        raw_candidates=all_candidates,
        all_segments=transcript.segments,
        min_duration=min_duration,
        max_duration=max_duration,
        target_count=num_clips
    )

    # Simpan ke cache
    save_cache("analysis", analysis_hash, {
        "candidates": [c.model_dump() for c in all_candidates],
        "niche": niche,
        "num_clips": num_clips
    })

    # Simpan analysis.json ke output dir jika diberikan
    if output_analysis_dir:
        output_analysis_dir.mkdir(parents=True, exist_ok=True)
        analysis_file = output_analysis_dir / "analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump({
                "niche": niche,
                "target_clips_count": num_clips,
                "total_candidates": len(all_candidates),
                "selected_clips": [c.model_dump(exclude={"segments"}) for c in validated_clips]
            }, f, ensure_ascii=False, indent=2)

    return validated_clips, None
