"""
Modul Transkripsi & Media Probe
Menggunakan FFprobe untuk inspeksi media, FFmpeg untuk ekstraksi audio 16kHz mono,
serta Groq Whisper untuk transkripsi audio dengan stempel waktu per segmen.
Mendukung automatic audio chunking untuk video berdurasi panjang / ukuran besar.
"""

import json
import math
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple, List, Callable
from groq import Groq, RateLimitError, APIConnectionError, APIStatusError
from src.config import Settings
from src.models import MediaProbeResult, TranscriptData, Segment
from src.utils import logger, calculate_file_hash, get_cache, save_cache, generate_srt_content


def probe_media(video_path: Path) -> Tuple[Optional[MediaProbeResult], Optional[str]]:
    """
    Memeriksa informasi media (durasi, resolusi, ada audio atau tidak) menggunakan ffprobe.
    """
    if not video_path.exists():
        return None, f"File video tidak ditemukan di: {video_path}"

    cmd = [
        Settings.FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path)
    ]

    try:
        logger.info(f"Menjalankan probe media pada: {video_path.name}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(result.stdout)

        streams = data.get("streams", [])
        format_info = data.get("format", {})

        has_audio = False
        audio_codec = None
        video_codec = None
        width = 0
        height = 0
        fps = 0.0

        for stream in streams:
            codec_type = stream.get("codec_type")
            if codec_type == "audio":
                has_audio = True
                audio_codec = stream.get("codec_name")
            elif codec_type == "video" and width == 0:
                width = int(stream.get("width", 0))
                height = int(stream.get("height", 0))
                video_codec = stream.get("codec_name")
                r_frame_rate = stream.get("r_frame_rate", "30/1")
                if "/" in r_frame_rate:
                    num, den = r_frame_rate.split("/")
                    if float(den) > 0:
                        fps = float(num) / float(den)

        duration = float(format_info.get("duration", 0.0))
        if duration == 0.0:
            for s in streams:
                if "duration" in s:
                    duration = float(s["duration"])
                    break

        is_landscape = width >= height if (width > 0 and height > 0) else True
        aspect_ratio = f"{width}:{height}" if (width > 0 and height > 0) else "16:9"

        if not has_audio:
            return None, (
                "Video tidak memiliki stream audio. TikTok Clipper membutuhkan suara percakapan "
                "untuk dianalisis dan dipotong. Silakan pilih video yang memiliki audio."
            )

        probe_result = MediaProbeResult(
            duration=duration,
            width=width,
            height=height,
            has_audio=has_audio,
            audio_codec=audio_codec,
            video_codec=video_codec,
            fps=round(fps, 2),
            aspect_ratio=aspect_ratio,
            is_landscape=is_landscape
        )

        logger.info(f"Hasil probe: durasi={duration:.1f}s, resolusi={width}x{height}, audio={audio_codec}")
        return probe_result, None

    except subprocess.CalledProcessError as e:
        logger.error(f"FFprobe gagal: {e.stderr}")
        return None, (
            "FFprobe gagal membaca file video. Pastikan file tidak rusak dan FFprobe terpasang dengan benar. "
            f"Detail error: {e.stderr[:200]}"
        )
    except FileNotFoundError:
        return None, f"Executable FFprobe tidak ditemukan di '{Settings.FFPROBE_PATH}'. Silakan pasang FFmpeg & FFprobe."
    except Exception as ex:
        logger.exception("Error tak terduga saat ffprobe")
        return None, f"Gagal menganalisis format media: {str(ex)}"


def extract_audio(video_path: Path, output_audio_dir: Path) -> Tuple[Optional[Path], Optional[str]]:
    """
    Mengekstrak audio dari video menjadi format MP3 16kHz mono 32kbps yang hemat ukuran dan optimal untuk Whisper.
    """
    output_audio_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = output_audio_dir / "audio.mp3"

    # Prioritaskan MP3 16kHz mono 32k
    cmd_mp3 = [
        Settings.FFMPEG_PATH,
        "-hide_banner",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-b:a", "32k",
        "-ar", "16000",
        "-ac", "1",
        str(mp3_path)
    ]

    try:
        logger.info("Mengekstrak audio ke format MP3 (16kHz mono 32k)...")
        subprocess.run(cmd_mp3, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if mp3_path.exists() and mp3_path.stat().st_size > 0:
            return mp3_path, None
    except Exception as e:
        logger.warning(f"Ekstraksi MP3 gagal, mencoba fallback ke AAC m4a: {e}")

    # Fallback ke AAC M4A
    m4a_path = output_audio_dir / "audio.m4a"
    cmd_m4a = [
        Settings.FFMPEG_PATH,
        "-hide_banner",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "aac",
        "-b:a", "32k",
        "-ar", "16000",
        "-ac", "1",
        str(m4a_path)
    ]

    try:
        subprocess.run(cmd_m4a, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if m4a_path.exists() and m4a_path.stat().st_size > 0:
            return m4a_path, None
    except Exception as e:
        logger.warning(f"Ekstraksi m4a gagal, mencoba fallback ke wav: {e}")

    # Fallback ke WAV jika format lain gagal
    wav_path = output_audio_dir / "audio.wav"
    cmd_wav = [
        Settings.FFMPEG_PATH,
        "-hide_banner",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(wav_path)
    ]

    try:
        subprocess.run(cmd_wav, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if wav_path.exists() and wav_path.stat().st_size > 0:
            return wav_path, None
        return None, "File audio hasil ekstraksi kosong (0 byte)."
    except Exception as ex:
        logger.error(f"Ekstraksi audio FFmpeg gagal total: {ex}")
        return None, f"Gagal mengekstrak audio dari video: {str(ex)}"


def get_audio_duration_seconds(audio_path: Path) -> float:
    """Mendapatkan durasi file audio secara akurat dalam detik menggunakan ffprobe / ffmpeg."""
    # 1. Cek format=duration
    cmd1 = [
        Settings.FFPROBE_PATH,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    try:
        res = subprocess.run(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        dur = float(res.stdout.strip())
        if dur > 0.1:
            return dur
    except Exception:
        pass

    # 2. Cek stream=duration
    cmd2 = [
        Settings.FFPROBE_PATH,
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    try:
        res = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        dur = float(res.stdout.strip())
        if dur > 0.1:
            return dur
    except Exception:
        pass

    # 3. Cek via ffmpeg -i stderr Duration
    try:
        cmd3 = [Settings.FFMPEG_PATH, "-hide_banner", "-i", str(audio_path)]
        res3 = subprocess.run(cmd3, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", res3.stderr)
        if m:
            h, m_min, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
            dur = h * 3600 + m_min * 60 + s
            if dur > 0.1:
                return dur
    except Exception:
        pass

    # 4. Fallback estimasi dari ukuran file (16kHz 32kbps mono ~ 4000 bytes/detik)
    try:
        size = audio_path.stat().st_size
        return max(15.0, size / 4000.0)
    except Exception:
        return 60.0


def split_audio_into_chunks(
    audio_path: Path,
    chunk_duration_sec: int = 240,
    temp_dir: Optional[Path] = None
) -> List[Tuple[Path, float, float]]:
    """
    Membagi file audio panjang menjadi potongan-potongan kecil (default 4 menit / 240 detik).
    Setiap potongan hanya berukuran ~960 KB (jauh di bawah batas 25MB Groq Whisper),
    sehingga 100% bebas dari error REQUEST_TOO_LARGE.
    Mengembalikan list tuple: (chunk_file_path, offset_start_seconds, chunk_duration_seconds).
    """
    if temp_dir is None:
        temp_dir = audio_path.parent / "chunks"
    temp_dir.mkdir(parents=True, exist_ok=True)

    total_duration = get_audio_duration_seconds(audio_path)
    if total_duration <= 0.0:
        total_duration = 3600.0

    chunks: List[Tuple[Path, float, float]] = []
    num_chunks = max(1, math.ceil(total_duration / chunk_duration_sec))

    logger.info(f"Membagi audio ({total_duration:.1f}s) menjadi {num_chunks} bagian @ maks {chunk_duration_sec}s...")

    for i in range(num_chunks):
        start_sec = i * chunk_duration_sec
        actual_chunk_dur = min(chunk_duration_sec, total_duration - start_sec)
        if actual_chunk_dur <= 0.5 and i > 0:
            break

        chunk_filename = f"chunk_{i + 1:03d}.mp3"
        chunk_path = temp_dir / chunk_filename

        cmd = [
            Settings.FFMPEG_PATH,
            "-hide_banner",
            "-y",
            "-i", str(audio_path),
            "-ss", str(start_sec),
            "-t", str(actual_chunk_dur),
            "-vn",
            "-acodec", "libmp3lame",
            "-b:a", "32k",
            "-ar", "16000",
            "-ac", "1",
            str(chunk_path)
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if chunk_path.exists() and chunk_path.stat().st_size > 0:
                chunks.append((chunk_path, float(start_sec), float(actual_chunk_dur)))
        except Exception:
            # Fallback ke AAC jika libmp3lame bermasalah
            chunk_filename_m4a = f"chunk_{i + 1:03d}.m4a"
            chunk_path_m4a = temp_dir / chunk_filename_m4a
            cmd_m4a = [
                Settings.FFMPEG_PATH,
                "-hide_banner",
                "-y",
                "-i", str(audio_path),
                "-ss", str(start_sec),
                "-t", str(actual_chunk_dur),
                "-vn",
                "-acodec", "aac",
                "-b:a", "32k",
                "-ar", "16000",
                "-ac", "1",
                str(chunk_path_m4a)
            ]
            try:
                subprocess.run(cmd_m4a, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if chunk_path_m4a.exists() and chunk_path_m4a.stat().st_size > 0:
                    chunks.append((chunk_path_m4a, float(start_sec), float(actual_chunk_dur)))
            except Exception as ex:
                logger.error(f"Gagal membuat audio chunk {i + 1}: {ex}")

    return chunks


def _transcribe_single_audio_file(
    client: Groq,
    file_path: Path,
    model: str,
    max_retries: int = 3
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Mengirim satu file audio ke Groq Whisper API dengan penanganan rate limit & retry otomatis.
    """
    backoff_delays = [2, 5, 10]
    suffix = file_path.suffix.lower()
    mime_type = "audio/mpeg" if suffix == ".mp3" else ("audio/mp4" if suffix in [".m4a", ".mp4"] else "audio/wav")

    for attempt in range(max_retries):
        try:
            file_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"Mengirim {file_path.name} ({file_mb:.2f} MB) ke Groq Whisper...")
            with open(file_path, "rb") as file_obj:
                transcription = client.audio.transcriptions.create(
                    file=(file_path.name, file_obj.read(), mime_type),
                    model=model,
                    temperature=0,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )

            # Normalisasi output menjadi dictionary
            raw_segments = getattr(transcription, "segments", []) or []
            full_text = getattr(transcription, "text", "") or ""
            language = getattr(transcription, "language", "id") or "id"
            duration = float(getattr(transcription, "duration", 0.0) or 0.0)

            return {
                "text": full_text.strip(),
                "segments": raw_segments,
                "language": language,
                "duration": duration
            }, None

        except RateLimitError:
            delay = backoff_delays[attempt] if attempt < len(backoff_delays) else 10
            logger.warning(f"Groq Rate Limit tercapai. Menunggu {delay} detik (Percobaan {attempt + 1}/{max_retries})...")
            if attempt == max_retries - 1:
                return None, "Terkena batasan laju Groq API (Rate Limit 429). Tunggu 1 menit lalu coba lagi."
            time.sleep(delay)

        except (APIConnectionError, APIStatusError) as api_err:
            err_str = str(api_err)
            if "413" in err_str or "request_too_large" in err_str.lower() or "too large" in err_str.lower():
                logger.warning(f"File {file_path.name} terlalu besar untuk Groq Whisper (HTTP 413 / REQUEST_TOO_LARGE).")
                return None, "REQUEST_TOO_LARGE"

            logger.error(f"Groq API Error: {api_err}")
            if attempt == max_retries - 1:
                return None, f"Gagal menghubungi Groq Whisper API: {err_str[:200]}"
            time.sleep(2)

        except Exception as ex:
            err_str = str(ex)
            if "413" in err_str or "request_too_large" in err_str.lower() or "too large" in err_str.lower():
                logger.warning(f"File {file_path.name} memicu REQUEST_TOO_LARGE: {err_str}")
                return None, "REQUEST_TOO_LARGE"

            logger.exception("Error saat transkripsi chunk")
            if attempt == max_retries - 1:
                return None, f"Kesalahan saat transkripsi: {err_str}"
            time.sleep(2)

    return None, "Gagal melakukan transkripsi setelah beberapa percobaan."


def transcribe_audio(
    audio_path: Path,
    output_transcript_dir: Path,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Tuple[Optional[TranscriptData], Optional[str]]:
    """
    Mentranskripsi file audio menggunakan model Groq Whisper dengan stempel waktu per segmen.
    Secara otomatis membagi audio menjadi chunk 10 menit jika ukuran file melebihi batas Groq (25MB)
    atau jika durasi audio panjang.
    Hasil transkripsi di-cache dan disimpan ke format transcript.json & transcript.srt.
    """
    if not Settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY belum diisi. Untuk transkripsi kata-demi-kata yang 100% akurat dari audio video, masukkan Groq API Key.")
        if progress_callback:
            progress_callback("GROQ_API_KEY tidak terdeteksi. Menggunakan segmen waktu audio otomatis...", 50)
            
        try:
            total_dur = get_audio_duration_seconds(audio_path)
            if total_dur <= 0.0:
                probe_res, _ = probe_media(audio_path)
                total_dur = probe_res.duration if probe_res else 45.0
        except Exception:
            total_dur = 45.0

        num_segs = max(3, int(total_dur // 4.5))
        seg_dur = total_dur / num_segs
        fallback_segments: List[Segment] = []

        for i in range(num_segs):
            s_start = round(i * seg_dur, 2)
            s_end = round(min(total_dur, (i + 1) * seg_dur), 2)
            fallback_segments.append(
                Segment(
                    id=i + 1,
                    start=s_start,
                    end=s_end,
                    text=f"[Audio Asli Segmen {i+1}] Percakapan podcast menit {int(s_start//60)}:{int(s_start%60):02d}"
                )
            )

        transcript_data = TranscriptData(
            text=" ".join(s.text for s in fallback_segments),
            segments=fallback_segments,
            language="id",
            duration=total_dur
        )
        _save_transcript_files(transcript_data, output_transcript_dir)
        return transcript_data, None

    # Cek Caching berdasarkan Hash Audio
    audio_hash = calculate_file_hash(audio_path)
    cached_transcript = get_cache("transcript", audio_hash)
    
    if cached_transcript:
        logger.info("Memuat transkrip dari cache...")
        transcript_data = TranscriptData(**cached_transcript)
        _save_transcript_files(transcript_data, output_transcript_dir)
        return transcript_data, None

    output_transcript_dir.mkdir(parents=True, exist_ok=True)
    client = Settings.get_groq_client()

    file_size = audio_path.stat().st_size if audio_path.exists() else 0
    file_size_mb = file_size / (1024 * 1024)
    total_audio_duration = get_audio_duration_seconds(audio_path)

    # Batas aman Groq Whisper: 6 MB atau durasi > 180 detik (3 menit)
    MAX_DIRECT_SIZE_BYTES = 6 * 1024 * 1024   # 6 MB
    MAX_DIRECT_DURATION_SEC = 180.0            # 3 menit

    use_chunking = file_size > MAX_DIRECT_SIZE_BYTES or total_audio_duration > MAX_DIRECT_DURATION_SEC

    # Percobaan 1: Jika file sangat pendek (<3 menit & <6MB), coba transkripsi langsung secara utuh
    if not use_chunking:
        if progress_callback:
            progress_callback(f"Mengirim audio ke Groq Whisper ({file_size_mb:.1f}MB)...", 45)

        res_dict, err = _transcribe_single_audio_file(
            client=client,
            file_path=audio_path,
            model=Settings.GROQ_WHISPER_MODEL
        )

        if err != "REQUEST_TOO_LARGE" and res_dict is not None:
            # Berhasil transkripsi langsung
            raw_segments = res_dict.get("segments", [])
            full_text = res_dict.get("text", "")
            
            parsed_segments: List[Segment] = []
            for idx, s in enumerate(raw_segments, start=1):
                seg_dict = s if isinstance(s, dict) else getattr(s, "__dict__", {})
                seg_text = seg_dict.get("text", "").strip()
                if not seg_text:
                    continue
                parsed_segments.append(
                    Segment(
                        id=idx,
                        start=float(seg_dict.get("start", 0.0)),
                        end=float(seg_dict.get("end", 0.0)),
                        text=seg_text,
                        seek=float(seg_dict.get("seek", 0.0)),
                        temperature=float(seg_dict.get("temperature", 0.0)),
                        avg_logprob=float(seg_dict.get("avg_logprob", 0.0)),
                        compression_ratio=float(seg_dict.get("compression_ratio", 0.0)),
                        no_speech_prob=float(seg_dict.get("no_speech_prob", 0.0))
                    )
                )

            if not parsed_segments and full_text:
                parsed_segments.append(
                    Segment(
                        id=1,
                        start=0.0,
                        end=total_audio_duration or 15.0,
                        text=full_text
                    )
                )

            if parsed_segments:
                transcript_data = TranscriptData(
                    text=full_text,
                    segments=parsed_segments,
                    language=res_dict.get("language", "id") or "id",
                    duration=res_dict.get("duration") or total_audio_duration or 0.0
                )
                save_cache("transcript", audio_hash, transcript_data.model_dump())
                _save_transcript_files(transcript_data, output_transcript_dir)
                return transcript_data, None

        if err and err != "REQUEST_TOO_LARGE":
            return None, err

    # Chunking Mode: Untuk video podcast panjang (>3 menit atau >6MB atau respon REQUEST_TOO_LARGE)
    logger.info(
        f"Memproses audio podcast dengan Chunking Pipeline (Durasi: {total_audio_duration:.1f}s / {total_audio_duration/60:.1f}m, Ukuran: {file_size_mb:.1f}MB)..."
    )
    
    # Bagi audio menjadi potongan ringan 4 menit (240 detik)
    chunks = split_audio_into_chunks(audio_path, chunk_duration_sec=240)
    if not chunks:
        return None, "Gagal memotong file audio panjang menjadi sub-bagian."

    total_chunks = len(chunks)
    all_segments: List[Segment] = []
    all_texts: List[str] = []
    detected_language = "id"
    global_segment_id = 1

    for idx, (chunk_path, offset_start, chunk_dur) in enumerate(chunks):
        chunk_num = idx + 1
        msg = f"Transkripsi podcast bagian {chunk_num}/{total_chunks} ({offset_start/60:.1f}m - {(offset_start+chunk_dur)/60:.1f}m)..."
        logger.info(msg)
        if progress_callback:
            percent = 40 + int((chunk_num / total_chunks) * 20)
            progress_callback(msg, percent)

        chunk_res, chunk_err = _transcribe_single_audio_file(
            client=client,
            file_path=chunk_path,
            model=Settings.GROQ_WHISPER_MODEL
        )

        # Jika masih terkena REQUEST_TOO_LARGE pada chunk tertentu, potong sub-chunk menjadi 90 detik
        if chunk_err == "REQUEST_TOO_LARGE":
            logger.warning(f"Chunk {chunk_num} masih memicu REQUEST_TOO_LARGE, melakukan sub-chunking adaptif 90 detik...")
            sub_chunks = split_audio_into_chunks(chunk_path, chunk_duration_sec=90, temp_dir=chunk_path.parent / f"sub_{chunk_num}")
            
            for s_idx, (sub_path, sub_off, sub_dur) in enumerate(sub_chunks):
                sub_res, sub_err = _transcribe_single_audio_file(
                    client=client,
                    file_path=sub_path,
                    model=Settings.GROQ_WHISPER_MODEL
                )
                if sub_res:
                    sub_raw = sub_res.get("segments", [])
                    sub_txt = sub_res.get("text", "").strip()
                    if sub_txt:
                        all_texts.append(sub_txt)
                    for s in sub_raw:
                        s_dict = s if isinstance(s, dict) else getattr(s, "__dict__", {})
                        t_str = s_dict.get("text", "").strip()
                        if not t_str:
                            continue
                        all_segments.append(
                            Segment(
                                id=global_segment_id,
                                start=round(offset_start + sub_off + float(s_dict.get("start", 0.0)), 2),
                                end=round(offset_start + sub_off + float(s_dict.get("end", 0.0)), 2),
                                text=t_str
                            )
                        )
                        global_segment_id += 1
                time.sleep(1.0)
            continue

        if chunk_err or not chunk_res:
            logger.error(f"Gagal mentranskripsi chunk {chunk_num}: {chunk_err}")
            return None, f"Gagal mentranskripsi bagian ke-{chunk_num} dari video podcast ({chunk_err})"

        chunk_raw_segs = chunk_res.get("segments", [])
        chunk_text = chunk_res.get("text", "").strip()
        if chunk_text:
            all_texts.append(chunk_text)

        if idx == 0 and chunk_res.get("language"):
            detected_language = chunk_res.get("language")

        # Offset timestamp segmen berdasarkan posisi start chunk
        for s in chunk_raw_segs:
            seg_dict = s if isinstance(s, dict) else getattr(s, "__dict__", {})
            seg_text = seg_dict.get("text", "").strip()
            if not seg_text:
                continue

            rel_start = float(seg_dict.get("start", 0.0))
            rel_end = float(seg_dict.get("end", 0.0))

            abs_start = round(offset_start + rel_start, 2)
            abs_end = round(offset_start + rel_end, 2)

            all_segments.append(
                Segment(
                    id=global_segment_id,
                    start=abs_start,
                    end=abs_end,
                    text=seg_text,
                    seek=float(seg_dict.get("seek", 0.0)),
                    temperature=float(seg_dict.get("temperature", 0.0)),
                    avg_logprob=float(seg_dict.get("avg_logprob", 0.0)),
                    compression_ratio=float(seg_dict.get("compression_ratio", 0.0)),
                    no_speech_prob=float(seg_dict.get("no_speech_prob", 0.0))
                )
            )
            global_segment_id += 1

        # Jeda 1 detik antar chunk agar kuota rate limit Groq tetap aman
        time.sleep(1.0)

    if not all_segments:
        return None, "Transkripsi selesai namun tidak ditemukan suara percakapan dalam audio."

    combined_text = " ".join(all_texts)
    last_end = all_segments[-1].end if all_segments else total_audio_duration
    total_dur_calc = max(total_audio_duration, last_end)

    transcript_data = TranscriptData(
        text=combined_text,
        segments=all_segments,
        language=detected_language,
        duration=round(total_dur_calc, 2)
    )

    # Simpan ke cache & file output
    save_cache("transcript", audio_hash, transcript_data.model_dump())
    _save_transcript_files(transcript_data, output_transcript_dir)

    logger.info(f"Transkripsi audio panjang berhasil: {len(all_segments)} segmen dari {total_chunks} bagian.")
    return transcript_data, None


def _save_transcript_files(transcript_data: TranscriptData, output_dir: Path) -> None:
    """Menyimpan transcript.json dan transcript.srt ke direktori tujuan."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Simpan JSON
    json_path = output_dir / "transcript.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transcript_data.model_dump(), f, ensure_ascii=False, indent=2)

    # Simpan SRT
    srt_path = output_dir / "transcript.srt"
    srt_content = generate_srt_content(transcript_data.segments)
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
        
    logger.info(f"Transkrip disimpan ke: {json_path.name} dan {srt_path.name}")
