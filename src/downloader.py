"""
Modul Downloader Video (yt-dlp & Direct HTTP/HTTPS Stream)
Mengunduh video dari URL langsung (Direct MP4/WebM/MKV Podcast, Google Drive, Dropbox, CDN)
maupun platform streaming (YouTube, TikTok, Instagram, dll) secara aman, cepat, dan stabil.
Mendukung ekstraksi cookies otomatis untuk mengatasi proteksi bot/login platform video.
"""

import os
import re
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple
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


def _is_direct_video_url(url: str) -> bool:
    """Mengecek apakah URL merupakan link direct file video atau cloud storage direct link."""
    clean_url = url.split("?")[0].lower()
    video_extensions = ('.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v', '.ts')
    if any(clean_url.endswith(ext) for ext in video_extensions):
        return True
    
    # Dropbox direct link
    if "dropbox.com" in url and ("dl=1" in url or "raw=1" in url):
        return True
        
    return False


def _normalize_direct_url(url: str) -> str:
    """Menormalisasi link cloud storage (Dropbox, Google Drive) menjadi direct download link."""
    url = url.strip()
    
    # Dropbox: ubah dl=0 jadi dl=1
    if "dropbox.com" in url:
        if "dl=0" in url:
            url = url.replace("dl=0", "dl=1")
        elif "dl=1" not in url and "raw=1" not in url:
            url = f"{url}{'&' if '?' in url else '?'}dl=1"
            
    # Google Drive: ubah link share menjadi direct export download
    if "drive.google.com" in url:
        file_id_match = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(r"id=([a-zA-Z0-9_-]+)", url)
        if file_id_match:
            file_id = file_id_match.group(1)
            url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
            
    return url


def _download_direct_http_file(url: str, output_path: Path) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
    """Mengunduh berkas video langsung melalui HTTP/HTTPS streaming."""
    normalized_url = _normalize_direct_url(url)
    logger.info(f"Mengunduh direct video stream dari: {normalized_url[:80]}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'identity',
    }
    
    req = urllib.request.Request(normalized_url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=45) as response, open(output_path, 'wb') as out_file:
            content_length = response.headers.get('content-length')
            total_bytes = int(content_length) if content_length and content_length.isdigit() else 0
            downloaded = 0
            block_size = 1024 * 1024  # 1MB buffer
            
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                if total_bytes > 0 and downloaded % (5 * 1024 * 1024) < block_size:
                    pct = (downloaded / total_bytes) * 100
                    logger.info(f"Direct download progress: {pct:.1f}% ({downloaded / (1024*1024):.1f}/{total_bytes / (1024*1024):.1f} MB)")

        if output_path.exists() and output_path.stat().st_size > 1024:
            file_title = Path(urllib.parse.urlparse(url).path).stem or "direct_podcast_video"
            return output_path, sanitize_filename(file_title, max_length=40), None
        else:
            return None, None, "File video langsung yang diunduh kosong atau tidak valid."
            
    except Exception as e:
        logger.warning(f"Gagal direct HTTP download ({e}), beralih ke yt-dlp engine...")
        if output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                pass
        return None, None, str(e)


def download_video_from_url(url: str, output_dir: Path) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
    """
    Mengunduh video dari URL (Direct File Link, Cloud Storage, atau platform seperti YouTube/TikTok).
    
    Args:
        url: Tautan video target (Direct MP4, YouTube, TikTok, Google Drive, Dropbox, dll)
        output_dir: Direktori tempat menyimpan file video
        
    Returns:
        Tuple (path_video_terunduh, judul_video, pesan_error)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(output_dir / "source_video.%(ext)s")
    direct_target = output_dir / "source_video.mp4"
    
    # 1. Cek apakah ini tautan file direct (contoh .mp4, direct CDN, dropbox, drive)
    if _is_direct_video_url(url):
        dl_path, title, err = _download_direct_http_file(url, direct_target)
        if dl_path and not err:
            return dl_path, title or "direct_video", None

    # 2. Gunakan yt-dlp untuk semua URL lainnya (atau fallback dari direct download)
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
        try:
            import yt_dlp
        except ImportError:
            return None, None, (
                "Modul yt-dlp belum terpasang di environment Python.\n"
                "💡 Solusi:\n"
                "1. Gunakan tab 'Tautan Direct Video Podcast' atau 'Unggah File Lokal' di Web UI.\n"
                "2. Atau pasang yt-dlp dengan: pip install yt-dlp"
            )

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

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Gagal mengunduh video dari URL: {err_msg}")
        
        # Penjelasan ramah & panduan solusi
        if "Sign in to confirm you’re not a bot" in err_msg or "Sign in" in err_msg or "Private video" in err_msg:
            pesan = (
                "YouTube memblokir unduhan langsung dari server (Deteksi Bot / Verifikasi Login Google).\n\n"
                "💡 SOLUSI REKOMENDASI (Pilih salah satu):\n"
                "1. Gunakan Link File Langsung (Direct MP4 URL):\n"
                "   Pilih tab 'Tautan Direct Video Podcast' untuk mengunduh video langsung dari server/CDN tanpa batasan YouTube.\n"
                "2. Unggah File Lokal (Paling Mudah):\n"
                "   Unduh video ke laptop Anda, lalu pilih tab 'Unggah File Lokal' di Web UI.\n"
                "3. Gunakan Berkas cookies.txt:\n"
                "   Ekspor cookies dari browser Anda lalu simpan sebagai 'cookies.txt' di folder proyek."
            )
            return None, None, pesan
        elif "HTTP Error 429" in err_msg:
            return None, None, (
                "Terkena batasan laju (Rate Limit HTTP 429) dari platform video.\n"
                "Solusi: Tunggu beberapa saat sebelum mencoba kembali, atau gunakan Link File Direct / Unggah Video Lokal."
            )
        else:
            return None, None, f"Gagal mengunduh video: {err_msg[:250]}\nSolusi: Gunakan Link Direct MP4 atau tab 'Unggah Video Lokal'."


