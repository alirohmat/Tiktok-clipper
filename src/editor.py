"""
Modul Editor Video & Subtitle (FFmpeg)
Memotong klip video secara presisi dengan re-encode, normalisasi audio EBU R128 (loudnorm),
pembuatan subtitle SRT relatif, pembakaran subtitle (hardsub), serta konversi vertikal (9:16).
"""

import json
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from src.config import Settings
from src.models import MediaProbeResult, ValidatedClip
from src.utils import generate_srt_content, logger
from src.speaker_tracker import generate_speaker_crop_filter, OPENCV_AVAILABLE


def _escape_ffmpeg_path(path_str: str) -> str:
    """Melakukan escape karakter khusus untuk filter FFmpeg (khususnya Windows & colon/slash)."""
    # Ganti backslash dengan forward slash
    s = path_str.replace("\\", "/")
    # Escape titik dua dan tanda kutip
    s = s.replace(":", "\\:").replace("'", "\\'")
    return s


def build_vertical_filter(
    vertical_mode: str,
    probe: Optional[MediaProbeResult],
    source_video: Optional[Path] = None,
    start_time: float = 0.0,
    duration: float = 30.0
) -> Optional[str]:
    """
    Menghasilkan string filter FFmpeg untuk format vertikal TikTok 9:16 (1080x1920).
    Mendukung deteksi pembicara aktif (speaker tracking) dan podcast split.
    """
    mode = vertical_mode.lower().replace("-", "_")
    if mode == "off":
        return None

    is_landscape = True
    width = 1920
    height = 1080
    if probe:
        is_landscape = probe.is_landscape
        width = probe.width
        height = probe.height

    if not is_landscape and mode in ("auto", "speaker", "smart_crop"):
        return None

    # Mode Smart Speaker Tracking / Active Speaker Follow
    if mode in ("speaker", "smart_crop", "face", "speaker_tracking") and source_video and source_video.exists():
        try:
            speaker_filter = generate_speaker_crop_filter(
                video_path=source_video,
                start_time=start_time,
                duration=duration,
                vertical_mode="speaker",
                video_width=width,
                video_height=height
            )
            return speaker_filter
        except Exception as e:
            logger.warning(f"Smart speaker crop gagal, fallback ke center crop: {e}")
            return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    # Mode Dual-Speaker Podcast Split (Tumpuk Atas & Bawah)
    if mode in ("split", "speaker_split", "podcast") and source_video and source_video.exists():
        try:
            split_filter = generate_speaker_crop_filter(
                video_path=source_video,
                start_time=start_time,
                duration=duration,
                vertical_mode="split",
                video_width=width,
                video_height=height
            )
            return split_filter
        except Exception as e:
            logger.warning(f"Dual-speaker split gagal, fallback ke center crop: {e}")
            return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    # Mode auto: coba deteksi pembicara terlebih dahulu, jika gagal center crop
    if mode == "auto":
        if source_video and source_video.exists() and OPENCV_AVAILABLE:
            try:
                auto_filter = generate_speaker_crop_filter(
                    video_path=source_video,
                    start_time=start_time,
                    duration=duration,
                    vertical_mode="auto",
                    video_width=width,
                    video_height=height
                )
                return auto_filter
            except Exception as e:
                logger.debug(f"Auto speaker crop fallback: {e}")
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    elif mode == "crop":
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    elif mode == "pad":
        return "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"

    return None


def render_single_clip(
    source_video: Path,
    clip: ValidatedClip,
    output_clips_dir: Path,
    probe: Optional[MediaProbeResult],
    burn_subtitles: bool = True,
    vertical_mode: str = "auto"
) -> Tuple[bool, Optional[str]]:
    """
    Merender satu klip video dengan FFmpeg:
    1. Membuat file subtitle SRT dengan timestamp relatif terhadap awal klip.
    2. Menjalankan FFmpeg dengan potongan waktu tepat (-ss dan -t).
    3. Normalisasi audio loudnorm (-af loudnorm=I=-16:TP=-1.5:LRA=11).
    4. Menyimpan file metadata JSON untuk klip tersebut.
    """
    output_clips_dir.mkdir(parents=True, exist_ok=True)
    
    # Nama file output aman
    file_prefix = f"{clip.index:02d}-{clip.slug}"
    video_out = output_clips_dir / f"{file_prefix}.mp4"
    srt_out = output_clips_dir / f"{file_prefix}.srt"
    json_out = output_clips_dir / f"{file_prefix}.json"

    # 1. Buat file SRT per klip (dengan offset relatif)
    srt_content = generate_srt_content(clip.segments, start_offset=clip.start_time)
    with open(srt_out, "w", encoding="utf-8") as f:
        f.write(srt_content)
    clip.output_srt_path = str(srt_out)

    # 2. Rancang rantai video filter
    # Deteksi apakah filter vertikal berupa filter complex multi-stream (seperti split atas-bawah podcast)
    v_filter = build_vertical_filter(
        vertical_mode=vertical_mode,
        probe=probe,
        source_video=source_video,
        start_time=clip.start_time,
        duration=clip.duration
    )

    # Filter Subtitle (Hardsub) jika diminta
    subtitle_filter = None
    if burn_subtitles and srt_out.exists():
        escaped_srt = _escape_ffmpeg_path(str(srt_out.resolve()))
        subtitle_filter = (
            f"subtitles='{escaped_srt}':force_style="
            f"'FontName=Arial,FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Alignment=2,MarginV=45'"
        )

    is_complex_filter = bool(v_filter and (";" in v_filter or "split=" in v_filter or "[0:v]" in v_filter))

    success = False
    error_msg = None
    subtitles_burned = False

    cmd_base = [
        Settings.FFMPEG_PATH,
        "-hide_banner",
        "-y",
        "-ss", str(clip.start_time),
        "-i", str(source_video),
        "-t", str(clip.duration),
    ]

    # Percobaan 1: Render dengan filter lengkap (Complex atau Simple)
    try:
        if is_complex_filter:
            # Rangkai filter complex: sambungkan vstack dengan filter subtitle jika aktif
            if subtitle_filter:
                # Ganti output tag [v_out] menjadi intermediate [v_stacked], lalu aplikasikan subtitle
                complex_graph = v_filter.replace("[v_out]", "[v_stacked]")
                complex_graph += f";[v_stacked]{subtitle_filter}[v_out]"
            else:
                complex_graph = v_filter

            cmd_full = cmd_base + [
                "-filter_complex", complex_graph,
                "-map", "[v_out]",
                "-map", "0:a?",
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "20",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-pix_fmt", "yuv420p",
                str(video_out)
            ]
        else:
            simple_filters = []
            if v_filter:
                simple_filters.append(v_filter)
            if subtitle_filter:
                simple_filters.append(subtitle_filter)

            if simple_filters:
                cmd_full = cmd_base + [
                    "-vf", ",".join(simple_filters),
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "20",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-movflags", "+faststart",
                    "-pix_fmt", "yuv420p",
                    str(video_out)
                ]
            else:
                cmd_full = cmd_base + [
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "20",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-movflags", "+faststart",
                    "-pix_fmt", "yuv420p",
                    str(video_out)
                ]

        logger.info(f"Merender klip {clip.index}: {clip.title} (dengan filter & normalisasi audio)...")
        subprocess.run(cmd_full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        success = True
        subtitles_burned = bool(subtitle_filter)

    except Exception as e:
        logger.warning(f"Render klip {clip.index} dengan filter penuh gagal, mencoba fallback: {e}")

    # Percobaan 2: Fallback hanya filter vertikal tanpa subtitle
    if not success and v_filter:
        try:
            if is_complex_filter:
                cmd_vonly = cmd_base + [
                    "-filter_complex", v_filter,
                    "-map", "[v_out]",
                    "-map", "0:a?",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "20",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-movflags", "+faststart",
                    "-pix_fmt", "yuv420p",
                    str(video_out)
                ]
            else:
                cmd_vonly = cmd_base + [
                    "-vf", v_filter,
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "20",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-movflags", "+faststart",
                    "-pix_fmt", "yuv420p",
                    str(video_out)
                ]

            logger.info(f"Merender klip {clip.index} (fallback vertikal tanpa hardsub)...")
            subprocess.run(cmd_vonly, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            success = True
            subtitles_burned = False
        except Exception as e:
            logger.warning(f"Fallback vertikal gagal: {e}")

    # Percobaan 3: Fallback dasar tanpa filter video apa pun
    if not success:
        cmd_basic = cmd_base + [
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            str(video_out)
        ]
        try:
            logger.info(f"Merender klip {clip.index} (fallback render dasar)...")
            subprocess.run(cmd_basic, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            success = True
            subtitles_burned = False
        except subprocess.CalledProcessError as cpe:
            error_msg = f"FFmpeg gagal merender klip {clip.index}: {cpe.stderr[:200]}"
            logger.error(error_msg)
        except Exception as ex:
            error_msg = f"Error tak terduga saat render klip {clip.index}: {str(ex)}"
            logger.error(error_msg)


    clip.render_success = success
    clip.subtitles_burned = subtitles_burned
    clip.output_video_path = str(video_out) if success else None
    clip.error_message = error_msg

    # 3. Simpan metadata JSON per klip
    clip_dict = clip.model_dump(exclude={"segments"})
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(clip_dict, f, ensure_ascii=False, indent=2)
    clip.output_json_path = str(json_out)

    return success, error_msg


def render_all_clips(
    source_video: Path,
    clips: List[ValidatedClip],
    output_clips_dir: Path,
    probe: Optional[MediaProbeResult],
    burn_subtitles: bool = True,
    vertical_mode: str = "auto"
) -> List[ValidatedClip]:
    """
    Merender semua klip yang telah divalidasi secara berurutan.
    Jika satu klip gagal, proses tetap berlanjut ke klip berikutnya tanpa crash.
    """
    rendered_results: List[ValidatedClip] = []

    for clip in clips:
        logger.info(f"Memproses klip #{clip.index}: '{clip.title}' ({clip.duration:.1f}s)...")
        ok, err = render_single_clip(
            source_video=source_video,
            clip=clip,
            output_clips_dir=output_clips_dir,
            probe=probe,
            burn_subtitles=burn_subtitles,
            vertical_mode=vertical_mode
        )
        if not ok:
            logger.warning(f"Peringatan: Klip #{clip.index} gagal dirender: {err}. Melanjutkan ke klip berikutnya.")
        rendered_results.append(clip)

    return rendered_results
