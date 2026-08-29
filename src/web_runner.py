"""
Web Runner Pipeline untuk TikTok Clipper
Menjalankan pipeline pemotongan video dari Web UI dengan pembaruan status JSON ke stdout.
"""

import sys
import os
from pathlib import Path

# Pastikan direktori root masuk ke sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import argparse
import time
from typing import Optional

from src.config import Settings
from src.downloader import download_video_from_url
from src.transcriber import probe_media, extract_audio, transcribe_audio
from src.analyzer import analyze_transcript
from src.editor import render_all_clips
from src.metadata import save_run_metadata
from src.sample_generator import generate_sample_podcast_video
from src.utils import logger, sanitize_filename


def emit_event(event_type: str, data: dict):
    """Kirim event JSON terstruktur ke stdout untuk Express server."""
    payload = {"event": event_type, "timestamp": time.time(), **data}
    print(f"__EVENT_JSON__{json.dumps(payload, ensure_ascii=False)}__EVENT_JSON__", flush=True)


def run_pipeline(
    input_source: str,
    output_dir: Path,
    niche: str = "auto",
    min_duration: int = 15,
    max_duration: int = 60,
    num_clips: int = 3,
    vertical_mode: str = "speaker",
    subtitles: bool = True,
    groq_api_key: Optional[str] = None,
    is_sample: bool = False
):
    if groq_api_key and groq_api_key.strip():
        Settings.GROQ_API_KEY = groq_api_key.strip()
        os.environ["GROQ_API_KEY"] = groq_api_key.strip()

    # Bersihkan GROQ_BASE_URL dari environment
    if "GROQ_BASE_URL" in os.environ:
        current_base = os.environ.get("GROQ_BASE_URL", "").strip()
        if "api.groq.com" in current_base or current_base.endswith("/openai/v1") or not current_base:
            os.environ.pop("GROQ_BASE_URL", None)

    run_start_time = time.time()
    run_id = output_dir.name
    output_dir.mkdir(parents=True, exist_ok=True)

    emit_event("progress", {"percent": 5, "stage": "Inisialisasi", "message": f"Mempersiapkan pipeline untuk run {run_id}..."})

    # Step 1: Input resolution
    video_path: Optional[Path] = None
    if is_sample or input_source.startswith("sample:"):
        sample_path = Settings.CACHE_DIR / "sample_podcast_demo.mp4"
        emit_event("progress", {"percent": 10, "stage": "Sample Video", "message": "Menyiapkan video sampel podcast 2 pembicara..."})
        generate_sample_podcast_video(sample_path, duration=35)
        video_path = sample_path
    elif input_source.startswith("http://") or input_source.startswith("https://"):
        emit_event("progress", {"percent": 15, "stage": "Unduh Video", "message": f"Mengunduh video dari tautan: {input_source[:60]}..."})
        source_dir = output_dir / "source"
        dl_path, title_slug, err_dl = download_video_from_url(input_source, source_dir)
        if err_dl or not dl_path:
            emit_event("error", {"message": f"Gagal mengunduh video: {err_dl}"})
            return 1
        video_path = dl_path
    else:
        # File lokal
        local_path = Path(input_source)
        if not local_path.exists():
            emit_event("error", {"message": f"File video tidak ditemukan di: {input_source}"})
            return 1
        video_path = local_path

    # Step 2: Probe Media
    emit_event("progress", {"percent": 25, "stage": "Analisis Media", "message": "Memeriksa resolusi, format, dan trek audio video..."})
    probe_res, probe_err = probe_media(video_path)
    if probe_err or not probe_res:
        emit_event("error", {"message": f"Inspeksi media gagal: {probe_err}"})
        return 1

    emit_event("probe", {
        "duration": probe_res.duration,
        "resolution": f"{probe_res.width}x{probe_res.height}",
        "aspect_ratio": probe_res.aspect_ratio,
        "is_landscape": probe_res.is_landscape,
        "fps": probe_res.fps
    })

    # Step 3: Ekstraksi Audio
    emit_event("progress", {"percent": 35, "stage": "Ekstraksi Audio", "message": "Mengekstrak audio 16kHz mono..."})
    audio_dir = output_dir / "audio"
    audio_path, audio_err = extract_audio(video_path, audio_dir)
    if audio_err or not audio_path:
        emit_event("error", {"message": f"Ekstraksi audio gagal: {audio_err}"})
        return 1

    # Step 4: Transkripsi Whisper
    emit_event("progress", {"percent": 45, "stage": "Transkripsi AI", "message": "Menjalankan transkripsi Whisper dengan timestamp presisi..."})
    transcript_dir = output_dir / "transcript"
    
    def on_transcribe_progress(msg: str, percent: int):
        emit_event("progress", {"percent": percent, "stage": "Transkripsi AI", "message": msg})

    transcript_data, trans_err = transcribe_audio(audio_path, transcript_dir, progress_callback=on_transcribe_progress)
    if trans_err or not transcript_data:
        emit_event("error", {"message": f"Transkripsi gagal: {trans_err}"})
        return 1

    emit_event("transcript", {
        "text_preview": transcript_data.text[:200] + ("..." if len(transcript_data.text) > 200 else ""),
        "total_segments": len(transcript_data.segments),
        "language": transcript_data.language
    })

    # Step 5: Analisis AI & Seleksi Klip TikTok 2026 (Auto-Context Speaker Detection)
    emit_event("progress", {"percent": 50, "stage": "Analisis Konten 2026", "message": f"Menganalisis hook, retensi & strategi niche {niche}..."})
    analysis_dir = output_dir / "analysis"

    def on_analysis_progress(msg: str, percent: int):
        emit_event("progress", {"percent": percent, "stage": "Analisis AI & Konteks Tokoh", "message": msg})

    validated_clips, analysis_err = analyze_transcript(
        transcript=transcript_data,
        niche=niche,
        min_duration=min_duration,
        max_duration=max_duration,
        num_clips=num_clips,
        output_analysis_dir=analysis_dir,
        progress_callback=on_analysis_progress
    )
    if analysis_err or not validated_clips:
        emit_event("error", {"message": f"Analisis klip gagal: {analysis_err}"})
        return 1

    emit_event("analysis", {
        "clips_found": len(validated_clips),
        "titles": [c.title for c in validated_clips]
    })

    # Step 6: Rendering FFmpeg dengan Smart Speaker Tracking & 9:16 Crop
    emit_event("progress", {
        "percent": 75,
        "stage": "Rendering Video & Smart Crop",
        "message": f"Merender {len(validated_clips)} klip dengan mode crop: {vertical_mode}..."
    })

    clips_dir = output_dir / "clips"
    rendered_clips = render_all_clips(
        source_video=video_path,
        clips=validated_clips,
        output_clips_dir=clips_dir,
        probe=probe_res,
        burn_subtitles=subtitles,
        vertical_mode=vertical_mode
    )

    # Step 7: Simpan Metadata Final
    emit_event("progress", {"percent": 95, "stage": "Penyelesaian Metadata", "message": "Menyusun file metadata, SRT, dan rekap TikTok..."})
    save_run_metadata(
        output_dir=output_dir,
        source_type="url" if (input_source.startswith("http://") or input_source.startswith("https://")) else "file",
        source_input=input_source,
        source_video_path=video_path,
        niche=niche,
        probe=probe_res,
        total_segments=len(transcript_data.segments) if transcript_data else 0,
        clips=rendered_clips,
        settings_dict={
            "min_duration": min_duration,
            "max_duration": max_duration,
            "num_clips": num_clips,
            "vertical": vertical_mode,
            "subtitles": subtitles
        }
    )

    # Format hasil klip untuk Web UI
    clips_payload = []
    for c in rendered_clips:
        clip_dict = c.model_dump(exclude={"segments"})
        if c.output_video_path:
            clip_dict["video_filename"] = Path(c.output_video_path).name
        if c.output_srt_path:
            clip_dict["srt_filename"] = Path(c.output_srt_path).name
        clips_payload.append(clip_dict)

    emit_event("complete", {
        "run_id": run_id,
        "total_rendered": sum(1 for c in rendered_clips if c.render_success),
        "clips": clips_payload,
        "elapsed_seconds": round(time.time() - run_start_time, 2)
    })

    emit_event("progress", {"percent": 100, "stage": "Selesai", "message": "Semua klip berhasil dibuat dan siap diunduh!"})
    return 0


def main():
    parser = argparse.ArgumentParser(description="TikTok Clipper Web Runner")
    parser.add_argument("--input", required=True, help="Path file video lokal atau URL")
    parser.add_argument("--output-dir", required=True, help="Direktori output")
    parser.add_argument("--niche", default="auto", help="Niche konten (auto / bisnis / edukasi / motivasi / teknologi / umum)")
    parser.add_argument("--min-duration", type=int, default=15, help="Durasi minimal detik")
    parser.add_argument("--max-duration", type=int, default=60, help="Durasi maksimal detik")
    parser.add_argument("--num-clips", type=int, default=3, help="Jumlah klip")
    parser.add_argument("--vertical", default="speaker", help="Mode vertikal 9:16 (speaker, split, auto, crop, pad, off)")
    parser.add_argument("--subtitles", action="store_true", default=True, help="Bakar subtitle hardsub")
    parser.add_argument("--no-subtitles", dest="subtitles", action="store_false")
    parser.add_argument("--groq-key", default=None, help="Groq API Key override")
    parser.add_argument("--sample", action="store_true", default=False, help="Gunakan sampel video simulasi")

    args = parser.parse_args()

    exit_code = run_pipeline(
        input_source=args.input,
        output_dir=Path(args.output_dir),
        niche=args.niche,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        num_clips=args.num_clips,
        vertical_mode=args.vertical,
        subtitles=args.subtitles,
        groq_api_key=args.groq_key,
        is_sample=args.sample
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
