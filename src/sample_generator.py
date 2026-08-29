"""
Modul Generator Video Sampel Uji Coba
Menghasilkan video simulasi podcast/wawancara 2 pembicara dengan FFmpeg
untuk pengujian instan fitur Active Speaker Tracking & Pemotongan Klip TikTok.
"""

import subprocess
from pathlib import Path
from src.config import Settings
from src.utils import logger


def generate_sample_podcast_video(output_path: Path, duration: int = 45) -> bool:
    """
    Membuat video sintetis 1920x1080 (30fps) dengan 2 panel pembicara (Host Kiri, Bintang Tamu Kanan)
    dan trek audio sintetis yang jelas untuk menguji speaker tracking dan pemotongan.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and output_path.stat().st_size > 10000:
        return True

    logger.info(f"Membuat video sampel podcast ({duration} detik) di {output_path}...")

    # Rancang visual 1920x1080 dengan FFmpeg lavfi filter:
    # Dua figur/box pembicara di kiri dan kanan dengan teks judul
    vf_script = (
        f"color=c=0x0f172a:s=1920x1080:d={duration}[bg];"
        f"color=c=0x1e293b:s=600x700:d={duration}[box_left];"
        f"color=c=0x1e293b:s=600x700:d={duration}[box_right];"
        f"color=c=0xec4899:s=180x180:d={duration}[face_l];"
        f"color=c=0x06b6d4:s=180x180:d={duration}[face_r];"
        f"[bg][box_left]overlay=200:200[bg1];"
        f"[bg1][box_right]overlay=1120:200[bg2];"
        f"[bg2][face_l]overlay=410:320[bg3];"
        f"[bg3][face_r]overlay=1330:320[bg4];"
        f"[bg4]drawtext=text='HOST \\(Pembicara 1\\)':fontcolor=white:fontsize=32:x=350:y=550,"
        f"drawtext=text='GUEST \\(Pembicara 2\\)':fontcolor=white:fontsize=32:x=1270:y=550,"
        f"drawtext=text='PODCAST BISNIS & STRATEGI VIRAL 2026':fontcolor=0xf43f5e:fontsize=44:x=(w-text_w)/2:y=80,"
        f"drawtext=text='Waktu\\: %{{pts\\:hms}}':fontcolor=0x94a3b8:fontsize=28:x=(w-text_w)/2:y=960[v_out]"
    )

    cmd = [
        Settings.FFMPEG_PATH,
        "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:beep_factor=4:duration={duration}",
        "-f", "lavfi",
        "-i", f"color=c=0x0f172a:s=1920x1080:d={duration}",
        "-filter_complex", vf_script,
        "-map", "[v_out]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        str(output_path)
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info("Video sampel podcast berhasil dibuat.")
        return True
    except Exception as e:
        logger.warning(f"Pembuatan sampel video podcast gagal: {e}")
        return False
