"""
Modul Utilitas (Helper & Functions)
Menyediakan fungsi logging aman, formatting timestamp SRT, slugifikasi nama file aman Windows, serta sistem caching.
"""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from slugify import slugify
from rich.console import Console
from rich.logging import RichHandler
from src.config import Settings
from src.models import Segment

# Inisialisasi Rich Console
console = Console()

# Inisialisasi Logger Aplikasi
logger = logging.getLogger("tiktok_clipper")
logger.setLevel(logging.DEBUG)

# File Handler untuk logs/app.log
Settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file_path = Settings.LOG_DIR / "app.log"
file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def mask_sensitive_data(text: str) -> str:
    """Menyembunyikan kunci API atau informasi rahasia dari pesan log dan terminal."""
    if not text:
        return text
    # Jika API key ada di .env, samarkan kemunculannya
    if Settings.GROQ_API_KEY and Settings.GROQ_API_KEY in text:
        masked = Settings.GROQ_API_KEY[:4] + "..." + Settings.GROQ_API_KEY[-4:] if len(Settings.GROQ_API_KEY) > 8 else "***"
        text = text.replace(Settings.GROQ_API_KEY, masked)
    # Samarkan pola umum gsk_... (Groq API Key)
    text = re.sub(r'gsk_[a-zA-Z0-9]{20,}', r'gsk_***REDACTED***', text)
    return text


def sanitize_filename(name: str, max_length: int = 50) -> str:
    """
    Menghasilkan nama file yang aman untuk Windows dan Linux.
    Menghilangkan karakter terlarang: \\ / : * ? \" < > |
    """
    # Gunakan python-slugify untuk transliterasi dan pembersihan dasar
    clean_slug = slugify(name, lowercase=True, separator="-")
    
    # Hapus karakter illegal Windows yang mungkin tersisa
    clean_slug = re.sub(r'[\\/*?:"<>|]', '', clean_slug)
    clean_slug = re.sub(r'-+', '-', clean_slug).strip('-')
    
    if not clean_slug:
        clean_slug = "clip"
        
    return clean_slug[:max_length]


def seconds_to_srt_timestamp(seconds: float) -> str:
    """Mengubah nilai detik ke format timestamp SRT: HH:MM:SS,mmm."""
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def seconds_to_display_time(seconds: float) -> str:
    """Mengubah nilai detik ke format tampilan ramah pengguna: MM:SS atau HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def generate_srt_content(segments: List[Segment], start_offset: float = 0.0) -> str:
    """
    Membuat format teks SRT dari daftar segmen.
    Jika start_offset diberikan, timestamp akan dibuat relatif terhadap offset tersebut (untuk klip potongan).
    """
    srt_lines = []
    index = 1
    
    for seg in segments:
        seg_start = max(0.0, seg.start - start_offset)
        seg_end = max(seg_start + 0.1, seg.end - start_offset)
        
        start_ts = seconds_to_srt_timestamp(seg_start)
        end_ts = seconds_to_srt_timestamp(seg_end)
        text = seg.text.strip()
        
        if text:
            srt_lines.append(f"{index}")
            srt_lines.append(f"{start_ts} --> {end_ts}")
            srt_lines.append(text)
            srt_lines.append("")
            index += 1
            
    return "\n".join(srt_lines)


def calculate_file_hash(file_path: Path) -> str:
    """Menghitung hash SHA256 dari sebuah file untuk keperluan caching."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_cache(cache_type: str, cache_key: str) -> Optional[Dict[str, Any]]:
    """Membaca data cache jika tersedia."""
    try:
        cache_file = Settings.CACHE_DIR / f"{cache_type}_{cache_key}.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Menggunakan cache {cache_type} untuk key: {cache_key[:8]}")
            return data
    except Exception as e:
        logger.warning(f"Gagal membaca cache {cache_type}: {e}")
    return None


def save_cache(cache_type: str, cache_key: str, data: Dict[str, Any]) -> None:
    """Menyimpan data hasil proses ke folder cache."""
    try:
        Settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = Settings.CACHE_DIR / f"{cache_type}_{cache_key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Cache {cache_type} berhasil disimpan: {cache_file.name}")
    except Exception as e:
        logger.warning(f"Gagal menyimpan cache {cache_type}: {e}")
