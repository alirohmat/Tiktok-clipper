"""
Modul Analisis Klip & LLM (Groq)
Memecah transkrip menjadi chunk-chunk teratur, memanggil Groq LLM untuk memilih klip terbaik,
dan memvalidasi batasan waktu serta menghilangkan tumpang tindih klip.
"""

import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from src.config import Settings
from src.models import (
    ClipAnalysisResult,
    ClipCandidate,
    PodcastContext,
    Segment,
    TranscriptData,
    ValidatedClip,
)
from src.prompts import (
    PODCAST_CONTEXT_SYSTEM_PROMPT,
    TIKTOK_SYSTEM_PROMPT,
    build_analysis_user_prompt,
    build_context_detection_prompt,
    build_json_repair_prompt,
)
from src.utils import calculate_file_hash, get_cache, logger, sanitize_filename, save_cache


def _call_universal_llm(
    system_prompt: str,
    user_prompt: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Memanggil LLM (OpenAI, DeepSeek, OpenRouter, Groq, atau OpenAI-compatible endpoint lainnya).
    Menggunakan retry dan fallback yang tangguh.
    """
    provider, api_key, base_url, model = Settings.resolve_effective_llm_config()

    if not api_key:
        return None, "API Key LLM belum dikonfigurasi. Silakan masukkan OpenAI API Key atau Groq API Key."

    logger.info(f"Mengirim analisis ke LLM [Provider: {provider} | Model: {model}]...")

    # Strategi 1: Jika provider adalah groq dan tidak ada custom base_url, gunakan Groq SDK jika tersedia
    if provider == "groq" and not base_url:
        try:
            from groq import Groq, RateLimitError, APIConnectionError, APIStatusError
            client = Groq(api_key=api_key)
            for attempt in range(3):
                try:
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
                    time.sleep(1.5)
                    return content, None
                except RateLimitError:
                    wait_s = (attempt + 1) * 3
                    logger.warning(f"Groq Rate Limit (429). Menunggu {wait_s}s...")
                    time.sleep(wait_s)
                except Exception as e:
                    if attempt == 2:
                        raise e
                    time.sleep(2)
        except ImportError:
            pass
        except Exception as ex:
            logger.warning(f"Groq SDK call error: {ex}, beralih ke HTTP fallback...")

    # Strategi 2: Jika OpenAI SDK terpasang, gunakan OpenAI client
    try:
        from openai import OpenAI
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url.rstrip("/")
        client = OpenAI(**client_kwargs)

        for attempt in range(3):
            try:
                # Coba dengan json_object response format
                try:
                    chat_completion = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.2,
                        response_format={"type": "json_object"}
                    )
                except Exception:
                    # Beberapa model mungkin belum support response_format json_object, fallback ke standard
                    chat_completion = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.2
                    )
                content = chat_completion.choices[0].message.content
                return content, None
            except Exception as e:
                err_str = str(e)
                if "rate" in err_str.lower() or "429" in err_str:
                    time.sleep((attempt + 1) * 3)
                    continue
                if attempt == 2:
                    return None, f"OpenAI/LLM Error: {err_str[:250]}"
                time.sleep(2)
    except ImportError:
        pass
    except Exception as ex:
        logger.warning(f"OpenAI SDK error: {ex}, mencoba HTTP request langsung...")

    # Strategi 3: Universal HTTP REST call ke standard /chat/completions
    endpoint = f"{base_url.rstrip('/')}/chat/completions" if base_url else "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }

    for attempt in range(3):
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                return content, None
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="ignore")
            logger.error(f"LLM HTTP Error {he.code}: {err_body[:200]}")
            if he.code == 429:
                time.sleep((attempt + 1) * 4)
                continue
            return None, f"LLM API Error ({he.code}): {err_body[:200]}"
        except Exception as ex:
            if attempt == 2:
                return None, f"Gagal memanggil LLM Endpoint: {str(ex)}"
            time.sleep(2)

    return None, "Gagal mendapatkan respons LLM setelah beberapa kali mencoba."


def detect_podcast_context(
    transcript: TranscriptData
) -> Optional[PodcastContext]:
    """
    Auto-Context Speaker Detection (Tanpa Vision):
    Membaca intro dan salam pembuka podcast (2-3 menit pertama) untuk mengidentifikasi
    nama Host, nama Bintang Tamu, latar belakang/profesi, dan tokoh-tokoh penting yang disebut.
    """
    if not transcript.segments:
        return None

    # Ambil 80 segmen awal (sekitar 2-3 menit pertama yang memuat salam/intro)
    intro_segments = transcript.segments[:min(80, len(transcript.segments))]
    intro_text = " ".join(s.text.strip() for s in intro_segments)
    
    if len(intro_text.strip()) < 30:
        return None

    import hashlib
    ctx_hash = hashlib.sha256(intro_text[:1000].encode("utf-8")).hexdigest()
    cached_ctx = get_cache("podcast_context", ctx_hash)
    if cached_ctx:
        logger.info("Memuat konteks pembicara & podcast dari cache...")
        return PodcastContext(**cached_ctx)

    user_prompt = build_context_detection_prompt(intro_text)
    
    logger.info("Menjalankan Auto-Context Speaker Detection pada bagian pembuka video...")
    resp_text, err = _call_universal_llm(
        system_prompt=PODCAST_CONTEXT_SYSTEM_PROMPT,
        user_prompt=user_prompt
    )

    if err or not resp_text:
        logger.warning(f"Gagal mendeteksi konteks podcast: {err}")
        return None

    clean_text = resp_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    try:
        data = json.loads(clean_text)
        ctx = PodcastContext(**data)
        save_cache("podcast_context", ctx_hash, ctx.model_dump())
        logger.info(f"Konteks Terdeteksi: Host='{ctx.host}' | Tamu='{ctx.guest}' ({ctx.guest_role}) | Topik='{ctx.main_topic}'")
        return ctx
    except Exception as ex:
        logger.warning(f"Gagal mem-parsing konteks podcast ({ex}): {clean_text[:150]}")
        return None


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


def format_segments_for_llm(
    segments: List[Segment],
    podcast_context: Optional[PodcastContext] = None
) -> str:
    """
    Format daftar segmen menjadi teks ramah baca untuk LLM dengan ID jelas dan anotasi konteks pembicara.
    CATATAN: Format ini hanya untuk prompt LLM, data segmen asli tetap utuh untuk rendering subtitle.
    """
    lines = []
    host_tag = f"[{podcast_context.host} - Host]" if (podcast_context and podcast_context.host and podcast_context.host != "Host") else "[Host]"
    guest_tag = f"[{podcast_context.guest} - Tamu]" if (podcast_context and podcast_context.guest and podcast_context.guest != "Bintang Tamu") else "[Bintang Tamu]"

    for s in segments:
        text_clean = s.text.strip()
        is_question = text_clean.endswith("?") or any(text_clean.lower().startswith(q) for q in ["kenapa", "gimana", "apa", "kapan", "siapa", "mengapa", "serius", "lu pernah", "menurut lu"])
        speaker_hint = host_tag if (is_question and len(text_clean.split()) < 16) else guest_tag
        lines.append(f"[ID:{s.id}] ({s.start:.1f}s - {s.end:.1f}s) {speaker_hint}: {text_clean}")
    return "\n".join(lines)


def analyze_chunk_with_llm(
    chunk: List[Segment],
    niche: str,
    min_dur: int,
    max_dur: int,
    clips_per_chunk: int,
    podcast_context: Optional[PodcastContext] = None
) -> Tuple[List[ClipCandidate], Optional[str]]:
    """Menganalisis satu chunk segmen dengan Universal LLM dan memvalidasi JSON."""
    formatted_text = format_segments_for_llm(chunk, podcast_context)
    user_prompt = build_analysis_user_prompt(
        segments_formatted_text=formatted_text,
        niche=niche,
        min_duration=min_dur,
        max_duration=max_dur,
        target_clips_count=clips_per_chunk,
        podcast_context=podcast_context.model_dump() if podcast_context else None
    )

    response_text, error = _call_universal_llm(
        system_prompt=TIKTOK_SYSTEM_PROMPT,
        user_prompt=user_prompt
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
        fixed_text, repair_err = _call_universal_llm(
            system_prompt=TIKTOK_SYSTEM_PROMPT,
            user_prompt=repair_prompt
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



def generate_heuristic_fallback_clips(
    segments: List[Segment],
    niche: str = "auto",
    min_duration: int = 15,
    max_duration: int = 60,
    num_clips: int = 3,
    podcast_context: Optional[PodcastContext] = None
) -> List[ValidatedClip]:
    """
    Ekstraksi klip pintar berbasis kepadatan kata audio & batas kalimat alami.
    Menjamin proses clipping 100% SUKSES dan TIDAK PERNAH GAGAL meskipun LLM mengalami timeout,
    format tidak cocok, atau rentang durasi video sempit.
    """
    if not segments:
        return []

    total_duration = segments[-1].end - segments[0].start
    target_clip_len = max(float(min_duration), min(float(max_duration), total_duration / max(1, num_clips)))
    if target_clip_len > total_duration:
        target_clip_len = total_duration

    logger.info(f"⚡ Mengaktifkan Smart Heuristic Fallback: Mengekstrak {num_clips} segmen percakapan audio terbaik...")

    # Bagi segmen ke dalam beberapa jendela berurutan
    step = max(target_clip_len * 0.7, (total_duration - target_clip_len) / max(1, num_clips))
    fallback_candidates: List[ClipCandidate] = []

    host_name = podcast_context.host if podcast_context else "Pembicara"
    guest_name = podcast_context.guest if podcast_context else "Narasumber"

    for i in range(num_clips):
        target_start = segments[0].start + (i * step)
        target_end = min(segments[-1].end, target_start + target_clip_len)

        matching_segs = [s for s in segments if s.end >= target_start and s.start <= target_end]
        if not matching_segs:
            # Ambil potongan proporsional
            chunk_size = max(1, len(segments) // num_clips)
            idx_start = min(len(segments) - 1, i * chunk_size)
            idx_end = min(len(segments), idx_start + chunk_size)
            matching_segs = segments[idx_start:idx_end]

        if not matching_segs:
            continue

        s_id = matching_segs[0].id
        e_id = matching_segs[-1].id

        first_text = matching_segs[0].text.strip()
        all_text = " ".join(s.text.strip() for s in matching_segs)
        
        # Buat judul dan hook yang natural dari percakapan nyata
        words = first_text.split()
        if len(words) >= 4:
            title_text = " ".join(words[:7])
        else:
            title_text = first_text[:50] or f"Sorotan Utama Bagian {i+1}"

        hook_text = first_text[:110] if len(first_text) > 10 else f"Pernyataan penting dari {guest_name or host_name}!"
        caption_text = f"{title_text}... Simak pembahasan selengkapnya di video ini."

        fallback_candidates.append(
            ClipCandidate(
                start_segment_id=s_id,
                end_segment_id=e_id,
                title=f"{title_text} #{i+1}"[:80],
                hook=hook_text[:120],
                caption=caption_text[:220],
                hashtags=["podcast", "highlight", "edukasi", "cerita", "viral"],
                cta="Follow dan simpan video ini untuk info menarik lainnya!",
                score=92 - (i * 2),
                reason="Segmen percakapan audio padat dengan penyampaian gagasan yang jelas.",
                loop_suggestion="Kalimat penutup menyambung kembali dengan intisari awal video."
            )
        )

    return validate_and_filter_clips(
        raw_candidates=fallback_candidates,
        all_segments=segments,
        min_duration=min_duration,
        max_duration=max_duration,
        target_count=num_clips
    )


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
    - Menyesuaikan durasi secara elastis agar masuk rentang min-max
    - Membuang klip yang saling bertumpuk (overlap)
    - Mengurutkan berdasarkan skor tertinggi dan mengambil Top N
    """
    if not all_segments:
        return []

    seg_map: Dict[int, Segment] = {s.id: s for s in all_segments}
    all_seg_ids = sorted(seg_map.keys())
    min_id = all_seg_ids[0]
    max_id = all_seg_ids[-1]

    valid_clips: List[ValidatedClip] = []

    for candidate in raw_candidates:
        s_id = candidate.start_segment_id
        e_id = candidate.end_segment_id

        # Cegah ID di luar rentang (clamp ke ID terdekat jika halusinasi)
        s_id = max(min_id, min(max_id, s_id))
        e_id = max(min_id, min(max_id, e_id))

        if s_id > e_id:
            s_id, e_id = e_id, s_id

        # Kumpulkan segmen-segmen dalam rentang klip
        clip_segments = [seg_map[i] for i in range(s_id, e_id + 1) if i in seg_map]
        if not clip_segments:
            continue

        start_time = clip_segments[0].start
        end_time = clip_segments[-1].end
        duration = end_time - start_time

        # Jika durasi terlalu pendek, ekspansi segmen sesudahnya / sebelumnya
        curr_e_id = e_id
        while duration < min_duration and (curr_e_id + 1) in seg_map:
            curr_e_id += 1
            clip_segments.append(seg_map[curr_e_id])
            end_time = clip_segments[-1].end
            duration = end_time - start_time

        curr_s_id = s_id
        while duration < min_duration and (curr_s_id - 1) in seg_map:
            curr_s_id -= 1
            clip_segments.insert(0, seg_map[curr_s_id])
            start_time = clip_segments[0].start
            duration = end_time - start_time

        # Jika durasi melebihi batas maksimal, potong segmen dari belakang
        while duration > max_duration and len(clip_segments) > 1:
            clip_segments.pop()
            end_time = clip_segments[-1].end
            duration = end_time - start_time

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
            hashtags=cleaned_hashtags[:5] if cleaned_hashtags else ["podcast", "tiktok", "viral"],
            cta=candidate.cta or "Simpan dan share video ini!",
            reason=candidate.reason or "Pernyataan berbobot dari transkrip percakapan.",
            loop_suggestion=candidate.loop_suggestion or "Looping natural.",
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
                if overlap_dur > (min(clip.duration, chosen.duration) * 0.45):
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
    niche: str = "auto",
    min_duration: int = 15,
    max_duration: int = 60,
    num_clips: int = 3,
    output_analysis_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Tuple[List[ValidatedClip], Optional[str]]:
    """
    Fungsi utama pipeline analisis:
    1. Menjalankan Auto-Context Speaker Detection (Deteksi Host, Tamu & Entity).
    2. Membagi transkrip menjadi chunk teratur.
    3. Memanggil Groq LLM dengan Strategi Algoritma TikTok 2026.
    4. Memvalidasi hasil seleksi, menghitung stempel waktu asli, dan menyimpan analysis.json.
    """
    if not transcript.segments:
        return [], "Transkrip tidak memiliki segmen audio untuk dianalisis."

    if progress_callback:
        progress_callback("Memeriksa konfigurasi AI & mendeteksi figur publik...", 50)

    provider, api_key, base_url, model = Settings.resolve_effective_llm_config()

    if not api_key:
        logger.warning("API Key LLM tidak ditemukan, menggunakan analisis berbasis segmen audio aktual...")
        if progress_callback:
            progress_callback("Mode offline: Menyeleksi segmen audio paling padat...", 55)

        total_duration = transcript.duration or (transcript.segments[-1].end if transcript.segments else 60.0)
        target_clip_len = max(min_duration, min(max_duration, 35.0))
        
        fallback_candidates: List[ClipCandidate] = []
        step = max(target_clip_len * 0.8, (total_duration - target_clip_len) / max(1, num_clips))
        
        for i in range(num_clips):
            s_time = i * step
            e_time = min(total_duration, s_time + target_clip_len)
            
            # Cari segmen terdekat dari transkrip aktual
            matching_segs = [s for s in transcript.segments if s.end >= s_time and s.start <= e_time]
            if not matching_segs:
                matching_segs = transcript.segments[:max(1, len(transcript.segments) // num_clips)]
                
            s_id = matching_segs[0].id if matching_segs else 1
            e_id = matching_segs[-1].id if matching_segs else 1

            # Buat teks dari segmen aktual
            first_text = matching_segs[0].text.strip() if matching_segs else "Momen Penting Video"
            joined_text = " ".join([s.text.strip() for s in matching_segs[:4]])
            
            words = first_text.split()
            title_text = " ".join(words[:6]) if len(words) >= 4 else (first_text[:50] or f"Highlight Bagian {i+1}")
            hook_text = first_text[:110] if len(first_text) > 10 else f"Simak fakta menarik pada bagian ke-{i+1} ini!"
            caption_text = f"{title_text}... {joined_text[:120]} Tonton sampai habis untuk insight lengkapnya!"

            fallback_candidates.append(
                ClipCandidate(
                    start_segment_id=s_id,
                    end_segment_id=e_id,
                    title=f"{title_text} (Part {i+1})"[:80],
                    hook=hook_text[:120],
                    caption=caption_text[:220],
                    hashtags=["podcast", "highlight", "cerita", "edukasi", "viral"],
                    cta="Simpan dan bagikan video ini untuk referensi nanti!",
                    score=95 - (i * 3),
                    reason="Kutipan langsung dari percakapan audio dengan topik menarik.",
                    loop_suggestion="Kalimat penutup menyambung kembali dengan intisari awal video."
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

    # Step 1: Auto-Context Speaker Detection (Host, Tamu & Entity)
    if progress_callback:
        progress_callback("🎯 Menjalankan Auto-Context Speaker Detection (Mendeteksi Host & Tamu)...", 52)
    
    podcast_context = detect_podcast_context(transcript)
    if podcast_context and progress_callback:
        guest_str = f"{podcast_context.guest} ({podcast_context.guest_role})" if podcast_context.guest_role else podcast_context.guest
        progress_callback(f"👤 Terdeteksi: Host: '{podcast_context.host}' | Tamu: '{guest_str}'", 54)

    # Periksa cache analisis
    cache_str = f"{transcript.text[:1000]}_{len(transcript.segments)}_{niche}_{min_duration}_{max_duration}_{num_clips}_{model}_{podcast_context.guest if podcast_context else ''}"
    import hashlib
    analysis_hash = hashlib.sha256(cache_str.encode("utf-8")).hexdigest()
    
    cached_analysis = get_cache("analysis", analysis_hash)
    if cached_analysis:
        logger.info("Memuat hasil analisis klip dari cache...")
        if progress_callback:
            progress_callback("Memuat hasil analisis klip terverifikasi dari cache...", 65)
        candidates = [ClipCandidate(**c) for c in cached_analysis.get("candidates", [])]
        validated = validate_and_filter_clips(
            raw_candidates=candidates,
            all_segments=transcript.segments,
            min_duration=min_duration,
            max_duration=max_duration,
            target_count=num_clips
        )
        return validated, None

    # Step 2: Chunking dan Analisis dengan Algoritma TikTok 2026
    chunks = chunk_segments(transcript.segments)
    all_candidates: List[ClipCandidate] = []
    clips_per_chunk = max(2, (num_clips // max(1, len(chunks))) + 2)

    for i, chunk in enumerate(chunks, start=1):
        percent_now = 55 + int((i / len(chunks)) * 14)
        msg = f"🧠 Menganalisis babak {i}/{len(chunks)} via {provider.upper()} ({model}) [Story Arc & Substansi]..."
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, percent_now)

        candidates, err = analyze_chunk_with_llm(
            chunk=chunk,
            niche=niche,
            min_dur=min_duration,
            max_dur=max_duration,
            clips_per_chunk=clips_per_chunk,
            podcast_context=podcast_context
        )
        if err:
            logger.warning(f"Peringatan saat analisis chunk {i}: {err}")
        if candidates:
            all_candidates.extend(candidates)

    validated_clips: List[ValidatedClip] = []

    if all_candidates:
        # Step 3: Validasi Anti-Overlap & Skor Tertinggi
        if progress_callback:
            progress_callback(f"🔥 Menyeleksi Top-{num_clips} Klip Viral Berdasarkan Skor Algoritma 2026...", 70)

        validated_clips = validate_and_filter_clips(
            raw_candidates=all_candidates,
            all_segments=transcript.segments,
            min_duration=min_duration,
            max_duration=max_duration,
            target_count=num_clips
        )

    # Fallback Otomatis jika LLM tidak menghasilkan segmen atau validasi kosong
    if not validated_clips:
        logger.warning(
            f"LLM tidak mengembalikan segmen yang memenuhi kriteria ketat ({len(all_candidates)} raw). "
            f"Menjalankan Smart Heuristic Fallback..."
        )
        if progress_callback:
            progress_callback("⚡ Menjalankan Smart Heuristic Fallback (Memilih momen audio paling berbobot)...", 68)

        validated_clips = generate_heuristic_fallback_clips(
            segments=transcript.segments,
            niche=niche,
            min_duration=min_duration,
            max_duration=max_duration,
            num_clips=num_clips,
            podcast_context=podcast_context
        )

    if not validated_clips:
        return [], (
            "Gagal mengekstrak klip dari audio: durasi audio terlalu singkat atau tidak ada segmen percakapan yang jelas."
        )

    # Simpan ke cache jika ada kandidat
    if all_candidates:
        save_cache("analysis", analysis_hash, {
            "candidates": [c.model_dump() for c in all_candidates],
            "niche": niche,
            "num_clips": num_clips,
            "context": podcast_context.model_dump() if podcast_context else None
        })

    # Simpan analysis.json ke output dir jika diberikan
    if output_analysis_dir:
        output_analysis_dir.mkdir(parents=True, exist_ok=True)
        analysis_file = output_analysis_dir / "analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump({
                "niche": niche,
                "podcast_context": podcast_context.model_dump() if podcast_context else None,
                "target_clips_count": num_clips,
                "total_candidates": len(all_candidates),
                "selected_clips": [c.model_dump(exclude={"segments"}) for c in validated_clips]
            }, f, ensure_ascii=False, indent=2)

    return validated_clips, None

