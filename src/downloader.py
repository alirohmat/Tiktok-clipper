"""
Modul Downloader Video (yt-dlp & Direct HTTP/HTTPS Stream)
Mengunduh video dari URL langsung (Direct MP4/WebM/MKV Podcast, Google Drive, Dropbox, CDN)
maupun platform streaming (YouTube, TikTok, Instagram, dll) secara aman, cepat, dan stabil.
Mendukung ekstraksi cookies otomatis untuk mengatasi proteksi bot/login platform video.
"""

import os
import re
import json
import shutil
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple
from src.config import Settings
from src.utils import logger, console, sanitize_filename


def _get_url_cache_dir(url: str) -> Path:
    """Mendapatkan direktori cache khusus untuk URL berdasarkan hash SHA-256."""
    clean_key = url.strip()
    url_hash = hashlib.sha256(clean_key.encode('utf-8')).hexdigest()[:16]
    cache_dir = Settings.CACHE_DIR / "downloads" / url_hash
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _check_cached_download(url: str) -> Tuple[Optional[Path], Optional[str]]:
    """Mengecek apakah URL target sudah pernah diunduh dan tersimpan di cache."""
    cache_dir = _get_url_cache_dir(url)
    meta_file = cache_dir / "meta.json"
    cached_videos = [f for f in cache_dir.glob("source_video.*") if f.is_file() and f.stat().st_size > 10240]
    
    if cached_videos:
        video_file = cached_videos[0]
        title = "cached_video"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    title = meta.get("title", title)
            except Exception:
                pass
        return video_file, title
        
    return None, None


def _save_to_download_cache(url: str, downloaded_file: Path, title: str):
    """Menyimpan berkas video dan metadata ke persistent cache."""
    try:
        cache_dir = _get_url_cache_dir(url)
        target_cache_file = cache_dir / f"source_video{downloaded_file.suffix}"
        
        # Salin jika lokasi berbeda
        if downloaded_file.resolve() != target_cache_file.resolve():
            shutil.copy2(downloaded_file, target_cache_file)
            
        meta_file = cache_dir / "meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "url": url,
                "title": title,
                "filename": target_cache_file.name,
                "file_size": target_cache_file.stat().st_size
            }, f, indent=2)
        logger.info(f"💾 Video berhasil disimpan ke cache unduhan: {target_cache_file.name} ({target_cache_file.stat().st_size / (1024*1024):.1f} MB)")
    except Exception as e:
        logger.warning(f"Gagal menyimpan video ke cache unduhan: {e}")


def _find_available_cookies_file() -> Optional[Path]:
    """Mencari berkas cookies.txt yang valid (bukan direktori) untuk autentikasi yt-dlp."""
    potential_paths = [
        Settings.COOKIES_FILE,
        Path("cookies.txt"),
        Path("youtube_cookies.txt"),
        Settings.CACHE_DIR / "cookies.txt",
        Path.home() / ".cookies.txt",
    ]
    for p in potential_paths:
        if p is not None:
            try:
                path_obj = Path(p)
                # WAJIB pastikan path adalah berkas (is_file) dan bukan direktori untuk mencegah [Errno 21]
                if path_obj.exists() and path_obj.is_file() and path_obj.stat().st_size > 0:
                    logger.info(f"Menggunakan berkas cookies: {path_obj.resolve()}")
                    return path_obj
            except Exception:
                continue
    return None


def _is_direct_video_url(url: str) -> bool:
    """Mengecek apakah URL merupakan link direct file video atau cloud storage direct link."""
    if not url:
        return False
    clean_url = url.split("?")[0].lower()
    
    # Platform media sosial & video streaming TIDAK BOLEH diproses sebagai file HTTP langsung
    streaming_domains = (
        "youtube.com", "youtu.be", "tiktok.com", "instagram.com",
        "facebook.com", "fb.watch", "twitter.com", "x.com",
        "twitch.tv", "vimeo.com", "bilibili.com", "dailymotion.com",
        "reddit.com", "threads.net", "pinterest.com"
    )
    if any(domain in url.lower() for domain in streaming_domains):
        return False

    video_extensions = ('.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v', '.ts', '.flv', '.3gp')
    if any(clean_url.endswith(ext) for ext in video_extensions):
        return True
    
    # Dropbox direct link
    if "dropbox.com" in url and ("dl=1" in url or "raw=1" in url):
        return True

    # Google Drive direct export download
    if "drive.google.com" in url and ("export=download" in url or "confirm=t" in url):
        return True

    # Layanan direct download / API download CDN murni
    if any(k in url.lower() for k in ["savenow.to", "googlevideo.com"]) and not any(d in url.lower() for d in streaming_domains):
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


def _extract_filename_from_cd(cd_header: Optional[str]) -> Optional[str]:
    """Mengekstrak nama file dari header Content-Disposition HTTP."""
    if not cd_header:
        return None
    match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)["\']?', cd_header, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        return Path(name).stem
    return None


def _download_direct_http_file(url: str, output_path: Path) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
    """Mengunduh berkas video langsung melalui HTTP/HTTPS streaming, mendukung chunked encoding & dynamic URLs."""
    normalized_url = _normalize_direct_url(url)
    logger.info(f"Mengunduh direct video stream dari: {normalized_url[:80]}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'identity',
    }
    
    req = urllib.request.Request(normalized_url, headers=headers)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Hapus file jika sebelumnya adalah direktori atau file rusak
    if output_path.exists():
        try:
            if output_path.is_dir():
                import shutil
                shutil.rmtree(output_path)
            else:
                output_path.unlink()
        except Exception:
            pass
            
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            content_type = response.headers.get('content-type', '').lower()
            content_disposition = response.headers.get('content-disposition', '')
            content_length = response.headers.get('content-length')
            
            # Jika respon ternyata adalah halaman HTML (bukan stream video), batalkan
            if 'text/html' in content_type or 'application/xhtml+xml' in content_type:
                logger.warning(f"URL mengembalikan halaman HTML ({content_type}), bukan video stream.")
                return None, None, "URL yang dimasukkan mengembalikan halaman web (HTML), bukan file video stream."
                
            total_bytes = int(content_length) if content_length and content_length.isdigit() else 0
            downloaded = 0
            block_size = 1024 * 1024  # 1MB buffer
            
            with open(output_path, 'wb') as out_file:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_bytes > 0 and downloaded % (5 * 1024 * 1024) < block_size:
                        pct = (downloaded / total_bytes) * 100
                        logger.info(f"Direct download progress: {pct:.1f}% ({downloaded / (1024*1024):.1f}/{total_bytes / (1024*1024):.1f} MB)")
                    elif total_bytes == 0 and downloaded % (5 * 1024 * 1024) < block_size:
                        logger.info(f"Direct download stream: {downloaded / (1024*1024):.1f} MB terunduh...")

        if output_path.exists() and output_path.is_file() and output_path.stat().st_size > 1024:
            cd_title = _extract_filename_from_cd(content_disposition)
            if cd_title:
                file_title = cd_title
            else:
                raw_path_stem = Path(urllib.parse.urlparse(url).path).stem
                file_title = raw_path_stem if raw_path_stem and len(raw_path_stem) > 3 else "direct_podcast_video"
            return output_path, sanitize_filename(file_title, max_length=50), None
        else:
            return None, None, "File video langsung yang diunduh kosong atau tidak valid."
            
    except Exception as e:
        logger.warning(f"Gagal direct HTTP download ({e}), beralih ke yt-dlp engine...")
        if output_path.exists() and output_path.is_file():
            try:
                output_path.unlink()
            except Exception:
                pass
        return None, None, str(e)


def download_video_from_url(url: str, output_dir: Path) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
    """
    Mengunduh video dari URL (Direct File Link, Cloud Storage, atau platform seperti YouTube/TikTok).
    Menggunakan cache lokal agar link yang sama tidak diunduh ulang (anti-spam / anti rate-limit).
    
    Args:
        url: Tautan video target (Direct MP4, YouTube, TikTok, Google Drive, Dropbox, dll)
        output_dir: Direktori tempat menyimpan file video
        
    Returns:
        Tuple (path_video_terunduh, judul_video, pesan_error)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 0. Anti-Spam Check: Cek apakah URL sudah ada di cache lokal
    cached_video, cached_title = _check_cached_download(url)
    if cached_video and cached_video.is_file():
        target_in_run = output_dir / f"source_video{cached_video.suffix}"
        try:
            if target_in_run.resolve() != cached_video.resolve():
                shutil.copy2(cached_video, target_in_run)
            logger.info(
                f"⚡ Video ditemukan di cache lokal! Menggunakan file cache ({cached_video.name}) "
                f"tanpa mengunduh ulang untuk mencegah spam dan menghemat kuota."
            )
            return target_in_run, cached_title or "cached_video", None
        except Exception as e:
            logger.warning(f"Gagal menyalin dari cache ({e}), melanjutkan proses unduh...")

    out_template = str(output_dir / "source_video.%(ext)s")
    direct_target = output_dir / "source_video.mp4"
    
    # 1. Cek apakah ini tautan file direct (contoh .mp4, direct CDN, dropbox, drive)
    if _is_direct_video_url(url):
        dl_path, title, err = _download_direct_http_file(url, direct_target)
        if dl_path and not err:
            _save_to_download_cache(url, dl_path, title or "direct_video")
            return dl_path, title or "direct_video", None

    # 2. Gunakan yt-dlp untuk semua URL streaming & fallback
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
        'cachedir': False,  # WAJIB False untuk mencegah yt-dlp membuat cache yang konflik dengan folder ./cache [Errno 21]
        'paths': {
            'home': str(output_dir),
            'temp': str(output_dir),
        },
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

    # Pasang berkas cookie jika ditemukan berkas valid
    cookies_path = _find_available_cookies_file()
    if cookies_path and cookies_path.is_file():
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
            info_dict = ydl.extract_info(url, download=True)
            if not info_dict:
                return None, None, "Gagal mengekstrak informasi video dari URL yang diberikan."
            
            raw_title = info_dict.get('title', 'source_video')
            video_title = sanitize_filename(raw_title, max_length=40)
            
            # Cari file hasil unduhan
            expected_mp4 = output_dir / "source_video.mp4"
            if expected_mp4.exists() and expected_mp4.is_file():
                _save_to_download_cache(url, expected_mp4, video_title)
                return expected_mp4, video_title, None
                
            # Jika format lain terdownload (misal mkv/webm), cari file pertama di folder
            downloaded_files = [f for f in output_dir.glob("source_video.*") if f.is_file()]
            if downloaded_files:
                _save_to_download_cache(url, downloaded_files[0], video_title)
                return downloaded_files[0], video_title, None
                
            return None, video_title, "File video tidak ditemukan setelah proses unduhan selesai."

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Gagal mengunduh video dari URL: {err_msg}")
        
        # Penjelasan ramah & panduan solusi
        if "Errno 21" in err_msg:
            return None, None, (
                "Terjadi konflik direktori saat mengunduh video ([Errno 21]).\n\n"
                "💡 SOLUSI REKOMENDASI:\n"
                "1. Gunakan tab 'Tautan Direct Video Podcast' untuk tautan file direct MP4 / Google Drive / Dropbox.\n"
                "2. Atau pilih tab 'Unggah File Lokal' untuk mengunggah file video dari laptop Anda."
            )
        elif "Sign in to confirm you’re not a bot" in err_msg or "Sign in" in err_msg or "Private video" in err_msg:
            pesan = (
                "Platform memblokir unduhan langsung dari server cloud (Deteksi Bot / Verifikasi Login).\n\n"
                "💡 SOLUSI REKOMENDASI:\n"
                "1. Gunakan Link File Langsung (Direct MP4 URL):\n"
                "   Pilih tab 'Tautan Direct Video Podcast' di Web UI.\n"
                "2. Unggah File Lokal (Paling Mudah & Stabil):\n"
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
            return None, None, f"{err_msg[:250]}\n💡 Solusi: Gunakan tab 'Tautan Direct Video' atau 'Unggah File Lokal'."


