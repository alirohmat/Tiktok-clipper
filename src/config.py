"""
Modul Konfigurasi
Membaca environment variables dari .env dan menyediakan pengaturan default untuk seluruh aplikasi.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Muat file .env jika ada
load_dotenv()


class Settings:
    """Kelas penampung konfigurasi global aplikasi."""

    # Konfigurasi Groq API
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip()
    GROQ_WHISPER_MODEL: str = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3").strip()
    GROQ_LLM_MODEL: str = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b").strip()

    # Jalur Executable FFmpeg & FFprobe
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg").strip()
    FFPROBE_PATH: str = os.getenv("FFPROBE_PATH", "ffprobe").strip()

    # Direktori Aplikasi
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "output"))
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", "cache"))
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))

    # Parameter Pemotongan Default
    DEFAULT_MIN_DURATION: int = int(os.getenv("DEFAULT_MIN_DURATION", "15"))
    DEFAULT_MAX_DURATION: int = int(os.getenv("DEFAULT_MAX_DURATION", "60"))
    DEFAULT_NUM_CLIPS: int = int(os.getenv("DEFAULT_NUM_CLIPS", "3"))
    DEFAULT_NICHE: str = os.getenv("DEFAULT_NICHE", "umum").strip()

    @classmethod
    def ensure_directories(cls) -> None:
        """Memastikan semua direktori kerja utama tersedia di sistem file."""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def reload_env(cls) -> None:
        """Memuat ulang file .env jika ada perubahan konfigurasi."""
        load_dotenv(override=True)
        cls.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
        cls.GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip()
        cls.GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3").strip()
        cls.GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b").strip()
        cls.FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg").strip()
        cls.FFPROBE_PATH = os.getenv("FFPROBE_PATH", "ffprobe").strip()
        cls.OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
        cls.CACHE_DIR = Path(os.getenv("CACHE_DIR", "cache"))
        cls.LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))


# Pastikan folder output, cache, dan logs langsung dibuat saat diimpor
Settings.ensure_directories()
