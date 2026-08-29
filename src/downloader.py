"""
Modul Downloader Video (yt-dlp)
Mengunduh video dari URL (YouTube, TikTok, Instagram, Twitter, dll) secara aman dan stabil.
Mendukung ekstraksi cookies otomatis untuk mengatasi proteksi bot/login platform video.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
import yt_dlp
from src.config import Settings
from src.utils import logger, console, sanitize_filename


def _find_available_cookies_file() -> Optional[Path]:
    """Mencari berkas cookies.txt yang tersedia di sistem untuk autentikasi yt-dlp."""
    potential_paths = [
        Settings.COOKIES_FILE,
        Path("cookies.txt"),
        Path("youtube_cookies.txt"),
        Settings.CACHE_DIR / "cookies.txt",
        Path.home() / ".cookies.txt",
    ]
    for p in potential_paths:
        if p and p.exists() and p.stat().st_size > 0:
            logger.info(f"Menggunakan berkas cookies: {p.resolve()}")
            return p
    return None


def download_video_from_url(url: str, output_dir: Path) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
    """
    Mengunduh video dari URL menggunakan yt-dlp dengan fallback player clients dan dukungan cookies.
    
    Args:
        url: Tautan video target (YouTube, TikTok, Instagram, dll)
        output_dir: Direktori tempat menyimpan file video
        
    Returns:
        Tuple (path_video_terunduh, judul_video, pesan_error)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(output_dir / "source_video.%(ext)s")
    
    ydl_opts = {
        # Format video: Utamakan MP4 1080p/720p dengan audio m4a/aac
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best',
        'outtmpl': out_template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'retries': 3,
        'socket_timeout': 30,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web_creator', 'mweb'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    }

    # Pasang berkas cookie jika ditemukan
    cookies_path = _find_available_cookies_file()
    if cookies_path:
        ydl_opts['cookiefile'] = str(cookies_path)

    video_title = "source_video"

    try:
        logger.info(f"Memulai proses unduh video dari URL: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Ekstrak info meta terlebih dahulu
            info_dict = ydl.extract_info(url, download=True)
            if not info_dict:
                return None, None, "Gagal mengekstrak informasi video dari URL yang diberikan."
            
            raw_title = info_dict.get('title', 'source_video')
            video_title = sanitize_filename(raw_title, max_length=40)
            
            # Cari file hasil unduhan
            expected_mp4 = output_dir / "source_video.mp4"
            if expected_mp4.exists():
                return expected_mp4, video_title, None
                
            # Jika format lain terdownload (misal mkv/webm), cari file pertama di folder
            downloaded_files = list(output_dir.glob("source_video.*"))
            if downloaded_files:
                return downloaded_files[0], video_title, None
                
            return None, video_title, "File video tidak ditemukan setelah proses unduhan selesai."

    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e)
        logger.error(f"Gagal mengunduh video dari URL: {err_msg}")
        
        # Penjelasan ramah & panduan solusi
        if "Sign in to confirm you’re not a bot" in err_msg or "Sign in" in err_msg or "Private video" in err_msg:
            pesan = (
                "YouTube memblokir unduhan langsung dari server (Deteksi Bot / Verifikasi Login Google).\n\n"
                "💡 SOLUSI REKOMENDASI (Pilih salah satu):\n"
                "1. Unggah File Langsung (Paling Mudah):\n"
                "   Unduh video ke laptop Anda (atau gunakan video MP4 yang sudah ada), lalu pilih tab 'Unggah Video Lokal' di Web UI atau gunakan flag: --input 'file_video.mp4' di CLI.\n"
                "2. Gunakan Berkas cookies.txt:\n"
                "   Ekspor cookies dari browser Anda (menggunakan ekstensi seperti 'Get cookies.txt LOCALLY') lalu simpan file tersebut sebagai 'cookies.txt' di folder proyek."
            )
            return None, None, pesan
        elif "HTTP Error 429" in err_msg:
            return None, None, (
                "Terkena batasan laju (Rate Limit HTTP 429) dari platform video.\n"
                "Solusi: Tunggu beberapa saat sebelum mencoba kembali, atau unggah video secara manual via tab 'Unggah Video Lokal'."
            )
        else:
            return None, None, f"Gagal mengunduh video: {err_msg[:250]}\nSolusi: Gunakan tab 'Unggah Video Lokal' untuk memproses file MP4 langsung."

    except Exception as ex:
        logger.exception("Error tak terduga saat mengunduh video")
        return None, None, f"Terjadi kesalahan saat mengunduh: {str(ex)}\nSaran: Gunakan opsi file lokal --input 'video.mp4'"

