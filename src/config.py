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

# Bersihkan GROQ_BASE_URL dari environment jika mengarah ke domain Groq resmi
# Ini mencegah library `groq` SDK menduplikasi jalur '/openai/v1/openai/v1'
if "GROQ_BASE_URL" in os.environ:
    current_base = os.environ.get("GROQ_BASE_URL", "").strip()
    if "api.groq.com" in current_base or current_base.endswith("/openai/v1") or not current_base:
        os.environ.pop("GROQ_BASE_URL", None)


class Settings:
    """Kelas penampung konfigurasi global aplikasi."""

    # Konfigurasi Groq (Transkripsi Whisper & Default LLM)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_BASE_URL: Optional[str] = None
    GROQ_WHISPER_MODEL: str = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3").strip()
    GROQ_LLM_MODEL: str = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile").strip()

    # Konfigurasi Universal LLM (Meta AI Muse Spark, OpenAI, DeepSeek, OpenRouter, Groq, Ollama, Custom)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto").strip().lower()
    LLM_API_KEY: str = (
        os.getenv("MODEL_API_KEY", "") or
        os.getenv("LLM_API_KEY", "") or
        os.getenv("OPENAI_API_KEY", "") or
        os.getenv("DEEPSEEK_API_KEY", "") or
        os.getenv("OPENROUTER_API_KEY", "") or
        os.getenv("GROQ_API_KEY", "") or
        os.getenv("API_KEY", "")
    ).strip()
    LLM_BASE_URL: Optional[str] = (
        os.getenv("LLM_BASE_URL", "") or
        os.getenv("OPENAI_BASE_URL", "") or
        os.getenv("OPENAI_API_BASE", "") or
        os.getenv("BASE_URL", "") or
        os.getenv("OLLAMA_BASE_URL", "")
    ).strip() or None
    LLM_MODEL: str = (
        os.getenv("LLM_MODEL", "") or
        os.getenv("OPENAI_MODEL", "") or
        os.getenv("MODEL", "") or
        os.getenv("GROQ_LLM_MODEL", "")
    ).strip()

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
    DEFAULT_NICHE: str = os.getenv("DEFAULT_NICHE", "auto").strip()

    # Lokasi Berkas Cookies YouTube / Platform Eksternal (jika ada berkas valid)
    _cookie_env = os.getenv("COOKIES_FILE", "")
    COOKIES_FILE: Optional[Path] = (
        Path(_cookie_env) if (_cookie_env and Path(_cookie_env).is_file())
        else (Path("cookies.txt") if Path("cookies.txt").is_file() else None)
    )

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
        if "GROQ_BASE_URL" in os.environ:
            current_base = os.environ.get("GROQ_BASE_URL", "").strip()
            if "api.groq.com" in current_base or current_base.endswith("/openai/v1") or not current_base:
                os.environ.pop("GROQ_BASE_URL", None)
        cls.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
        cls.GROQ_BASE_URL = None
        cls.GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3").strip()
        cls.GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile").strip()
        cls.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower()
        cls.LLM_API_KEY = (
            os.getenv("MODEL_API_KEY", "") or
            os.getenv("LLM_API_KEY", "") or
            os.getenv("OPENAI_API_KEY", "") or
            os.getenv("DEEPSEEK_API_KEY", "") or
            os.getenv("OPENROUTER_API_KEY", "") or
            os.getenv("GROQ_API_KEY", "") or
            os.getenv("API_KEY", "")
        ).strip()
        cls.LLM_BASE_URL = (
            os.getenv("LLM_BASE_URL", "") or
            os.getenv("OPENAI_BASE_URL", "") or
            os.getenv("OPENAI_API_BASE", "") or
            os.getenv("BASE_URL", "") or
            os.getenv("OLLAMA_BASE_URL", "")
        ).strip() or None
        cls.LLM_MODEL = (
            os.getenv("LLM_MODEL", "") or
            os.getenv("OPENAI_MODEL", "") or
            os.getenv("MODEL", "") or
            os.getenv("GROQ_LLM_MODEL", "")
        ).strip()
        cls.FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg").strip()
        cls.FFPROBE_PATH = os.getenv("FFPROBE_PATH", "ffprobe").strip()
        cls.OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
        cls.CACHE_DIR = Path(os.getenv("CACHE_DIR", "cache"))
        cls.LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))

    @classmethod
    def get_groq_client(cls):
        """Membuat instance Groq client resmi untuk Whisper atau Groq LLM."""
        from groq import Groq
        if "GROQ_BASE_URL" in os.environ:
            current_base = os.environ.get("GROQ_BASE_URL", "").strip()
            if "api.groq.com" in current_base or current_base.endswith("/openai/v1") or not current_base:
                os.environ.pop("GROQ_BASE_URL", None)
        
        key = cls.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
        return Groq(api_key=key)

    @classmethod
    def resolve_effective_llm_config(cls) -> tuple[str, str, Optional[str], str]:
        """
        Mengidentifikasi provider, api_key, base_url, dan model name yang aktif.
        Returns: (provider_name, api_key, base_url, model_name)
        """
        provider = cls.LLM_PROVIDER.lower()
        api_key = cls.LLM_API_KEY
        base_url = cls.LLM_BASE_URL
        model = cls.LLM_MODEL

        # Normalisasi base_url jika ada
        if base_url:
            base_url = base_url.strip().rstrip("/")
            if base_url.endswith("/chat/completions"):
                base_url = base_url[:-len("/chat/completions")].rstrip("/")

        # Deteksi otomatis provider berdasarkan base_url atau API key
        if provider in ("auto", "", "none"):
            if os.getenv("MODEL_API_KEY"):
                provider = "meta"
            elif base_url:
                if "meta.ai" in base_url:
                    provider = "meta"
                elif "deepseek.com" in base_url:
                    provider = "deepseek"
                elif "openrouter.ai" in base_url:
                    provider = "openrouter"
                elif "api.groq.com" in base_url:
                    provider = "groq"
                elif "openai.com" in base_url:
                    provider = "openai"
                else:
                    provider = "custom"
            elif model and "muse" in model.lower():
                provider = "meta"
            elif api_key.startswith("sk-") and len(api_key) > 30 and not api_key.startswith("gsk_"):
                if model and "deepseek" in model.lower():
                    provider = "deepseek"
                elif model and ("claude" in model.lower() or "/" in model):
                    provider = "openrouter"
                else:
                    provider = "openai"
            elif api_key.startswith("gsk_") or cls.GROQ_API_KEY:
                provider = "groq"
            elif model:
                # User menentukan model kustom (seperti muse spark / llama / mistral)
                provider = "custom"
            else:
                provider = "groq"

        # Tentukan default base_url & model sesuai provider
        if provider in ("meta", "meta-ai"):
            base_url = base_url or "https://api.meta.ai/v1"
            model = model or "muse-spark-1.2-contributor"
        elif provider == "deepseek":
            base_url = base_url or "https://api.deepseek.com"
            model = model or "deepseek-chat"
        elif provider == "openrouter":
            base_url = base_url or "https://openrouter.ai/api/v1"
            model = model or "google/gemini-2.5-flash"
        elif provider == "openai":
            base_url = base_url or "https://api.openai.com/v1"
            model = model or "gpt-4o-mini"
        elif provider == "groq":
            base_url = None
            model = model or "llama-3.3-70b-versatile"
            if model == "openai/gpt-oss-120b":
                model = "llama-3.3-70b-versatile"
            api_key = cls.GROQ_API_KEY or api_key
        else:
            # Custom OpenAI-compatible endpoint (e.g. Meta Muse Spark, Ollama, vLLM, LM Studio)
            model = model or "muse-spark-1.2-contributor"
            if not base_url:
                base_url = "https://api.meta.ai/v1"
            # Jika menggunakan custom base_url tetapi api_key kosong, gunakan dummy key agar SDK OpenAI tidak error (hanya jika bukan server remote ber-auth seperti Meta AI)
            if not api_key and not ("meta.ai" in base_url):
                api_key = "EMPTY"

        # Jika provider selain groq memiliki base_url tapi api_key kosong (misal server lokal Ollama/vLLM), isi dummy key
        if base_url and not api_key:
            api_key = "EMPTY"

        return provider, api_key, base_url, model


# Pastikan folder output, cache, dan logs langsung dibuat saat diimpor
Settings.ensure_directories()
