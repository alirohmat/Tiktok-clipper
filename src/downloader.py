"""
Modul Downloader Video (yt-dlp)
Mengunduh video dari URL (YouTube, TikTok, Instagram, Twitter, dll) secara aman dan stabil.
"""

from pathlib import Path
from typing import Optional, Tuple
import yt_dlp
from src.utils import logger, console, sanitize_filename


def download_video_from_url(url: str, output_dir: Path) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
    """
    Mengunduh video dari URL menggunakan yt-dlp.
    
    Args:
        url: Tautan video target
        output_dir: Direktori tempat menyimpan file video
        
    Returns:
        Tuple (path_video_terunduh, judul_video, pesan_error)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(output_dir / "source_video.%(ext)s")
    
    ydl_opts = {
        # Format video: Utamakan MP4 1080p, audio m4a/aac
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best',
        'outtmpl': out_template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'retries': 3,
        'socket_timeout': 30,
    }

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
        
        # Berikan saran praktis berdasarkan jenis error
        solusi = "Saran: Pastikan URL bersifat publik. Jika platform memblokir bot, silakan unduh video secara manual lalu jalankan dengan flag --input 'nama_file.mp4'."
        if "Private video" in err_msg or "Sign in" in err_msg:
            return None, None, f"Video bersifat privat atau membutuhkan login.\n{solusi}"
        elif "HTTP Error 429" in err_msg:
            return None, None, f"Terkena batasan laju (Rate Limit) dari server video.\n{solusi}"
        else:
            return None, None, f"Gagal mengunduh video: {err_msg[:200]}\n{solusi}"

    except Exception as ex:
        logger.exception("Error tak terduga saat mengunduh video")
        return None, None, f"Terjadi kesalahan saat mengunduh: {str(ex)}\nSaran: Gunakan opsi file lokal --input 'video.mp4'"
