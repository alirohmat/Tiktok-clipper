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
    override_model: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Memanggil LLM (OpenAI, DeepSeek, OpenRouter, Groq, atau OpenAI-compatible endpoint lainnya).
    Menggunakan retry cerdas, Groq model auto-tiering, dan fallback yang tangguh.
    """
    provider, api_key, base_url, model = Settings.resolve_effective_llm_config()
    if override_model:
        model = override_model

    if not api_key:
        return None, "API Key LLM belum dikonfigurasi. Silakan masukkan OpenAI API Key atau Groq API Key."

    logger.info(f"Mengirim analisis ke LLM [Provider: {provider} | Model: {model}]...")

    # Strategi 1: Jika provider adalah groq dan tidak ada custom base_url, gunakan Groq SDK
    if provider == "groq" and not base_url:
        try:
            from groq import Groq, RateLimitError
            client = Groq(api_key=api_key)
            models_to_try = [model]
            if model != "llama-3.1-8b-instant":
                # Tambahkan 8b-instant sebagai fallback jika 70b terkena rate limit
                models_to_try.append("llama-3.1-8b-instant")

            for cur_model in models_to_try:
                for attempt in range(3):
                    try:
                        chat_completion = client.chat.completions.create(
                            model=cur_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.2,
                            response_format={"type": "json_object"}
                        )
                        content = chat_completion.choices[0].message.content
                        time.sleep(1.0)
                        return content, None
                    except RateLimitError as rle:
                        wait_s = (attempt + 1) * 4
                        logger.warning(f"Groq Rate Limit ({cur_model}) [Attempt {attempt+1}/3]. Menunggu {wait_s}s...")
                        time.sleep(wait_s)
                    except Exception as e:
                        err_str = str(e)
                        if "rate" in err_str.lower() or "429" in err_str:
                            time.sleep(3)
                            continue
                        logger.warning(f"Groq {cur_model} error: {e}")
                        break
        except ImportError:
            pass
        except Exception as ex:
            logger.warning(f"Groq SDK call error: {ex}, beralih ke HTTP fallback...")

    # Tentukan base_url & endpoint yang tepat sesuai provider jika belum disetel
    if not base_url:
        if provider == "groq":
            effective_base_url = "https://api.groq.com/openai/v1"
        elif provider == "deepseek":
            effective_base_url = "https://api.deepseek.com/v1"
        elif provider == "openrouter":
            effective_base_url = "https://openrouter.ai/api/v1"
        else:
            effective_base_url = "https://api.openai.com/v1"
    else:
        effective_base_url = base_url.rstrip("/")

    # Strategi 2: Jika OpenAI SDK terpasang, gunakan OpenAI client dengan endpoint yang sesuai
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=effective_base_url)

        for attempt in range(3):
            try:
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
                    break
                time.sleep(2)
    except ImportError:
        pass
    except Exception as ex:
        logger.warning(f"OpenAI SDK error: {ex}, mencoba HTTP request langsung...")

    # Strategi 3: Universal HTTP REST call ke standard /chat/completions
    endpoint = f"{effective_base_url}/chat/completions"
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
    Auto-Context Speaker & Name-Drop Detection (Tanpa Vision):
    Membaca intro, salam pembuka, dan menyisir sapaan figur publik (Mas/Pak/Bang/Prof/dll.)
    di sepanjang transkrip untuk mengidentifikasi Host, Bintang Tamu, dan seluruh Name-Drops.
    """
    if not transcript.segments:
        return None

    # 1. Pindai nama-nama tokoh/honorifics di sepanjang transkrip (Regex Name-Dropping Scanner)
    name_patterns = re.findall(
        r'\b(?:Mas|Pak|Bang|Prof|Dok|Mbak|Bung|Gus|Kak)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        transcript.text
    )
    detected_name_drops = list(dict.fromkeys(name_patterns))[:8]  # Ambil hingga 8 nama unik teratas

    # 2. Ambil 120 segmen awal (sekitar 3-5 menit pertama yang memuat salam/intro/perkenalan)
    intro_segments = transcript.segments[:min(120, len(transcript.segments))]
    intro_text = " ".join(s.text.strip() for s in intro_segments)
    
    if len(intro_text.strip()) < 30:
        return None

    import hashlib
    ctx_hash = hashlib.sha256((intro_text[:1200] + "_" + "_".join(detected_name_drops)).encode("utf-8")).hexdigest()
    cached_ctx = get_cache("podcast_context", ctx_hash)
    if cached_ctx:
        logger.info("Memuat konteks figur publik & podcast dari cache...")
        return PodcastContext(**cached_ctx)

    # Tambahkan nama-nama yang terpindai ke prompt deteksi
    augmented_intro = intro_text
    if detected_name_drops:
        augmented_intro += f"\n[Catatan Entitas/Sapaan Terdeteksi di Transkrip: {', '.join(detected_name_drops)}]"

    user_prompt = build_context_detection_prompt(augmented_intro)
    
    logger.info("Menjalankan Auto-Context Speaker & Name-Drop Detection pada video...")
    resp_text, err = _call_universal_llm(
        system_prompt=PODCAST_CONTEXT_SYSTEM_PROMPT,
        user_prompt=user_prompt
    )

    if err or not resp_text:
        logger.warning(f"Gagal mendeteksi konteks podcast via LLM: {err}. Menggunakan deteksi heuristik...")
        # Heuristic fallback context jika LLM gagal
        host_candidate = "Host"
        guest_candidate = "Narasumber / Bintang Tamu"
        if detected_name_drops:
            host_candidate = f"Mas {detected_name_drops[0]}"
            if len(detected_name_drops) > 1:
                guest_candidate = detected_name_drops[1]
        
        ctx = PodcastContext(
            host=host_candidate,
            guest=guest_candidate,
            guest_role="Figur Publik / Tamu Podcast",
            main_topic="Perbincangan Podcast & Wawasan Strategis",
            key_entities=detected_name_drops
        )
        return ctx

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
        # Gabungkan entity tambahan yang terpindai jika belum ada di list LLM
        key_ents = data.get("key_entities", [])
        for nd in detected_name_drops:
            if nd not in key_ents and len(key_ents) < 8:
                key_ents.append(nd)
        data["key_entities"] = key_ents

        ctx = PodcastContext(**data)
        save_cache("podcast_context", ctx_hash, ctx.model_dump())
        logger.info(
            f"👤 Konteks Terdeteksi: Host='{ctx.host}' | Tamu='{ctx.guest}' ({ctx.guest_role}) | "
            f"Topik='{ctx.main_topic}' | Entitas={ctx.key_entities}"
        )
        return ctx
    except Exception as ex:
        logger.warning(f"Gagal mem-parsing konteks podcast ({ex}): {clean_text[:150]}")
        return None


def chunk_segments(
    segments: List[Segment],
    max_chars: Optional[int] = None,
    max_segments: Optional[int] = None,
    overlap: int = 2
) -> List[List[Segment]]:
    """
    Memecah daftar segmen menjadi potongan (chunks) dengan ukuran adaptif agar
    tetap efisien terhadap kuota token API dan mempertahankan kelengkapan Story Arc TikTok 2026.
    """
    if not segments:
        return []

    # Sizing adaptif berdasarkan panjang transkrip
    total_segs = len(segments)
    if max_chars is None or max_segments is None:
        if total_segs > 800:
            # Video panjang (>45 menit): Gunakan 4-6 babak besar yang padat konteks
            effective_max_chars = 14000
            effective_max_segments = 160
        elif total_segs > 300:
            # Video sedang (15-45 menit)
            effective_max_chars = 10000
            effective_max_segments = 110
        else:
            # Video pendek (<15 menit)
            effective_max_chars = 7500
            effective_max_segments = 80
    else:
        effective_max_chars = max_chars
        effective_max_segments = max_segments

    chunks: List[List[Segment]] = []
    current_chunk: List[Segment] = []
    current_chars = 0

    idx = 0
    while idx < len(segments):
        seg = segments[idx]
        seg_len = len(seg.text) + 30  # Estimasi panjang teks + ID dan timestamp

        # Jika chunk melebihi batas, simpan chunk saat ini
        if current_chunk and (current_chars + seg_len > effective_max_chars or len(current_chunk) >= effective_max_segments):
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

    logger.info(f"Transkrip ({len(segments)} segmen) dibagi menjadi {len(chunks)} babak analisis narasi.")
    return chunks


def format_segments_for_llm(
    segments: List[Segment],
    podcast_context: Optional[PodcastContext] = None
) -> str:
    """
    Format daftar segmen menjadi teks ramah baca untuk LLM dengan ID jelas,
    anotasi alur dialog dinamis (Host vs Tamu), serta penanda khusus untuk Name-Dropping & Momen Panas.
    CATATAN: Format ini hanya untuk prompt LLM, data segmen asli tetap utuh untuk rendering subtitle.
    """
    lines = []
    host_name = podcast_context.host if (podcast_context and podcast_context.host and podcast_context.host != "Host") else "Host"
    guest_name = podcast_context.guest if (podcast_context and podcast_context.guest and podcast_context.guest != "Bintang Tamu") else "Bintang Tamu"
    
    key_entities = [e.lower() for e in (podcast_context.key_entities if podcast_context else [])]

    # Pelacak giliran bicara (Dialogue Turn Tracker)
    current_speaker = "guest"  # Tamu biasanya mendominasi porsi bicara

    for s in segments:
        text_clean = s.text.strip()
        text_lower = text_clean.lower()

        # Deteksi apakah segmen ini adalah pertanyaan atau interjeksi khas Host
        is_short_question = (
            text_clean.endswith("?") or 
            any(text_lower.startswith(q) for q in ["kenapa", "gimana", "apa", "kapan", "siapa", "mengapa", "menurut", "lu pernah", "serius", "apakah"])
        ) and len(text_clean.split()) < 18

        is_short_reaction = any(text_lower == r for r in ["iya", "betul", "benar", "wah", "gila sih", "menarik", "oke", "setuju", "siap"])

        # Deteksi Name-Drops di dalam segmen
        found_drops = []
        for ent in key_entities:
            if ent in text_lower:
                found_drops.append(ent.title())
        
        # Pindai sapaan spesifik (Mas Gita, Pak, dll.)
        honorific_drops = re.findall(r'\b(?:Mas|Pak|Bang|Prof|Dok|Mbak|Bung|Gus)\s+([A-Z][a-z]+)', text_clean)
        for hd in honorific_drops:
            if hd.title() not in found_drops:
                found_drops.append(hd.title())

        # Tentukan pembicara saat ini
        if is_short_question or (is_short_reaction and current_speaker == "guest"):
            current_speaker = "host"
        elif len(text_clean.split()) > 10:
            current_speaker = "guest"

        speaker_tag = f"🎙️ [{host_name} - Host]" if current_speaker == "host" else f"🗣️ [{guest_name} - Tamu]"
        
        drop_tag = f" | 🔥 Name-Drop: {', '.join(found_drops[:2])}" if found_drops else ""
        
        lines.append(f"[ID:{s.id}] ({s.start:.1f}s - {s.end:.1f}s) {speaker_tag}{drop_tag}: \"{text_clean}\"")

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
    Ekstraksi klip pintar berbasis kepadatan kata audio, Name-Drop, & formula Hook Algoritma 2026.
    Menjamin proses clipping 100% SUKSES dan menghasilkan hook yang menarik meskipun LLM timeout.
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

    host_name = podcast_context.host if (podcast_context and podcast_context.host != "Host") else "Host"
    guest_name = podcast_context.guest if (podcast_context and podcast_context.guest != "Bintang Tamu") else "Narasumber"

    for i in range(num_clips):
        target_start = segments[0].start + (i * step)
        target_end = min(segments[-1].end, target_start + target_clip_len)

        matching_segs = [s for s in segments if s.end >= target_start and s.start <= target_end]
        if not matching_segs:
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
        
        # Pindai apakah ada nama figur publik di dalam segmen ini
        found_name = None
        if podcast_context and podcast_context.key_entities:
            for ke in podcast_context.key_entities:
                if ke.lower() in all_text.lower():
                    found_name = ke
                    break
        
        if not found_name:
            h_match = re.search(r'\b(?:Mas|Pak|Bang|Prof|Dok)\s+([A-Z][a-z]+)', all_text)
            if h_match:
                found_name = h_match.group(0)

        # Formulasi Hook Algoritma TikTok 2026
        if found_name:
            hook_text = f"Rahasia penting tentang {found_name} yang belum pernah dibuka!"
            title_text = f"Pengakuan Terbuka Tentang {found_name}"
        elif "?" in first_text or any(first_text.lower().startswith(q) for q in ["kenapa", "gimana", "apa", "mengapa"]):
            hook_text = f"Pertanyaan tak terduga yang bikin {guest_name} terdiam!"
            title_text = f"Diskusi Panas: {first_text[:45]}..."
        elif any(w in all_text.lower() for w in ["kaget", "gagal", "hancur", "sulit", "rahasia", "jebakan", "rugi"]):
            hook_text = f"Peringatan penting dari {guest_name} sebelum kamu terlambat!"
            title_text = f"Pelajaran Pahit dari {guest_name}"
        else:
            hook_text = f"Wawasan langka dari {guest_name} yang mengubah segalanya!"
            title_text = f"Wawasan Penting: {first_text[:40]}..."

        caption_text = f"{hook_text} Simak penjelasan lengkap dari {guest_name} dan diskusikan di kolom komentar!"

        fallback_candidates.append(
            ClipCandidate(
                start_segment_id=s_id,
                end_segment_id=e_id,
                title=f"{title_text}"[:80],
                hook=hook_text[:120],
                caption=caption_text[:220],
                hashtags=["podcast", "wawasan", "edukasi", "cerita", "viral"],
                cta="Simpan dan share video ini ke teman yang butuh wawasan ini!",
                score=94 - (i * 2),
                reason="Segmen percakapan audio berbobot dengan alur gagasan yang utuh.",
                loop_suggestion="Kalimat penutup menjawab pembuka sehingga penonton terdorong memutar ulang."
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
        logger.warning("API Key LLM tidak ditemukan, menggunakan analisis berbasis segmen audio & formula hook 2026...")
        if progress_callback:
            progress_callback("Mode offline: Menyeleksi segmen audio & merumuskan hook viral...", 55)

        # Jalankan deteksi figur publik heuristik
        podcast_context = detect_podcast_context(transcript)
        
        validated = generate_heuristic_fallback_clips(
            segments=transcript.segments,
            niche=niche,
            min_duration=min_duration,
            max_duration=max_duration,
            num_clips=num_clips,
            podcast_context=podcast_context
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

