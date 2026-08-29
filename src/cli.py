"""
Modul Antarmuka Perintah Baris (CLI Typer & Rich)
Mengatur argumen terminal, validasi awal, pemeriksaan sistem (--check),
serta alur orkestrasi pemotongan video dari awal sampai akhir.
"""

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from src.config import Settings
from src.downloader import download_video_from_url
from src.editor import render_all_clips
from src.metadata import save_run_metadata
from src.models import MediaProbeResult
from src.transcriber import extract_audio, probe_media, transcribe_audio
from src.analyzer import analyze_transcript
from src.utils import logger, sanitize_filename, seconds_to_display_time

# Inisialisasi Aplikasi CLI Typer
app = typer.Typer(
    name="tiktok-clipper",
    help="Alat otomatis untuk memotong video panjang menjadi klip TikTok pendek dengan strategi 2026.",
    add_completion=False
)

console = Console()


def perform_system_check() -> bool:
    """
    Menjalankan pemeriksaan kesiapan sistem (--check):
    - Versi Python
    - Ketersediaan binary FFmpeg & FFprobe
    - Validasi GROQ_API_KEY
    - Ketersediaan folder kerja
    """
    console.print("\n[bold cyan]🔍 Memeriksa Lingkungan & Kesiapan Sistem TikTok Clipper...[/bold cyan]\n")

    table = Table(title="Hasil Diagnosis Sistem", show_header=True, header_style="bold magenta")
    table.add_column("Komponen", style="cyan", width=25)
    table.add_column("Status", width=15)
    table.add_column("Keterangan", style="dim")

    all_passed = True

    # 1. Cek Python
    py_version = sys.version.split()[0]
    is_py_ok = sys.version_info >= (3, 10)
    table.add_row(
        "Python Runtime",
        "[green]✅ Siap[/green]" if is_py_ok else "[red]❌ Kurang[/red]",
        f"Versi {py_version} (Rekomendasi 3.11+)"
    )
    if not is_py_ok:
        all_passed = False

    # 2. Cek FFmpeg
    ffmpeg_ok = bool(shutil.which(Settings.FFMPEG_PATH))
    table.add_row(
        "FFmpeg CLI",
        "[green]✅ Terpasang[/green]" if ffmpeg_ok else "[red]❌ Tidak Ditemukan[/red]",
        f"Path: {Settings.FFMPEG_PATH}" if ffmpeg_ok else "Unduh di https://ffmpeg.org/download.html"
    )
    if not ffmpeg_ok:
        all_passed = False

    # 3. Cek FFprobe
    ffprobe_ok = bool(shutil.which(Settings.FFPROBE_PATH))
    table.add_row(
        "FFprobe CLI",
        "[green]✅ Terpasang[/green]" if ffprobe_ok else "[red]❌ Tidak Ditemukan[/red]",
        f"Path: {Settings.FFPROBE_PATH}" if ffprobe_ok else "Biasanya sudah satu paket dengan FFmpeg"
    )
    if not ffprobe_ok:
        all_passed = False

    # 4. Cek GROQ_API_KEY
    has_api_key = bool(Settings.GROQ_API_KEY)
    key_display = f"Terisi ({Settings.GROQ_API_KEY[:4]}...)" if has_api_key else "Kosong di .env"
    table.add_row(
        "Groq API Key",
        "[green]✅ Terisi[/green]" if has_api_key else "[yellow]⚠️ Belum Diisi[/yellow]",
        f"{key_display} (Dapatkan gratis di https://console.groq.com)"
    )

    # 5. Cek Direktori
    dirs_ok = True
    try:
        Settings.ensure_directories()
    except Exception:
        dirs_ok = False
    table.add_row(
        "Direktori Kerja",
        "[green]✅ Siap[/green]" if dirs_ok else "[red]❌ Gagal[/red]",
        f"output/, cache/, logs/"
    )

    console.print(table)

    if all_passed and has_api_key:
        console.print("\n[bold green]🎉 Semua pemeriksaan sistem berhasil! Aplikasi siap digunakan.[/bold green]\n")
    elif all_passed and not has_api_key:
        console.print("\n[bold yellow]⚠️ Perhatian: Harap isi GROQ_API_KEY di file .env sebelum memproses video.[/bold yellow]\n")
    else:
        console.print("\n[bold red]❌ Ditemukan beberapa kendala pada sistem. Silakan perbaiki komponen yang bermasalah di atas.[/bold red]\n")

    return all_passed


@app.command()
def main_cli(
    input_file: Optional[Path] = typer.Option(
        None,
        "--input", "-i",
        help="Jalur file video lokal yang ingin dipotong (misal: video.mp4)",
        exists=False
    ),
    url: Optional[str] = typer.Option(
        None,
        "--url", "-u",
        help="Tautan/URL video internet (YouTube, TikTok, X, dll)"
    ),
    niche: str = typer.Option(
        Settings.DEFAULT_NICHE,
        "--niche", "-n",
        help="Kategori atau topik konten (edukasi, bisnis, motivasi, komedi, teknologi, umum)"
    ),
    num_clips: int = typer.Option(
        Settings.DEFAULT_NUM_CLIPS,
        "--num-clips", "-c",
        help="Jumlah klip terbaik yang ingin dihasilkan (default: 3)"
    ),
    min_duration: int = typer.Option(
        Settings.DEFAULT_MIN_DURATION,
        "--min-duration",
        help="Durasi minimal setiap klip dalam detik (default: 15)"
    ),
    max_duration: int = typer.Option(
        Settings.DEFAULT_MAX_DURATION,
        "--max-duration",
        help="Durasi maksimal setiap klip dalam detik (default: 60)"
    ),
    subtitles: bool = typer.Option(
        True,
        "--subtitles/--no-subtitles",
        help="Bakar teks subtitle otomatis ke dalam video (hardsub)"
    ),
    vertical: str = typer.Option(
        "speaker",
        "--vertical",
        help="Format vertikal 9:16: 'speaker' (Active Speaker Tracking), 'split' (Dual Podcast Split), 'auto' (Smart Face Detect), 'crop' (Center Crop), 'pad' (Pillarbox), 'off' (Asli)"
    ),
    analyze_only: bool = typer.Option(
        False,
        "--analyze-only",
        help="Hanya jalankan transkripsi dan analisis AI tanpa merender file video baru"
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Tampilkan log teknis mendalam di terminal"
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Jalankan pemeriksaan kesehatan sistem, FFmpeg, dan konfigurasi API"
    )
):
    """
    TikTok Clipper: Ubah video panjang menjadi klip TikTok vertikal otomatis dengan AI.
    """
    if debug:
        logger.setLevel(os.environ.get("LOG_LEVEL", "DEBUG"))

    # Jika opsi --check dipanggil
    if check:
        perform_system_check()
        raise typer.Exit()

    # Validasi Sumber Input: Harus ada tepat satu sumber
    if not input_file and not url:
        console.print(Panel(
            "[bold yellow]Silakan tentukan sumber video yang ingin diproses![/bold yellow]\n\n"
            "Gunakan opsi:\n"
            "  • [cyan]--input 'video.mp4'[/cyan] (untuk file video lokal)\n"
            "  • [cyan]--url 'https://...'[/cyan] (untuk tautan video online)\n"
            "  • [cyan]--check[/cyan] (untuk memeriksa sistem)",
            title="⚠️ Input Diperlukan",
            border_style="yellow"
        ))
        raise typer.Exit(code=1)

    if input_file and url:
        console.print("[bold red]❌ Error: Pilih salah satu saja antara --input ATAU --url, tidak bisa keduanya sekaligus.[/bold red]")
        raise typer.Exit(code=1)

    # Validasi GROQ_API_KEY
    if not Settings.GROQ_API_KEY:
        console.print(Panel(
            "[bold red]GROQ_API_KEY belum terpasang di file .env![/bold red]\n\n"
            "1. Dapatkan API Key gratis di [link=https://console.groq.com]https://console.groq.com[/link]\n"
            "2. Buka file [bold].env[/bold] dan masukkan kunci Anda:\n"
            "   [cyan]GROQ_API_KEY=gsk_...[/cyan]",
            title="Kunci API Dibutuhkan",
            border_style="red"
        ))
        raise typer.Exit(code=1)

    # Buat nama folder output unik: YYYY-MM-DD_HH-MM_slug
    timestamp_prefix = datetime.now().strftime("%Y-%m-%d_%H-%M")
    source_name = input_file.stem if input_file else "url-video"
    slug_name = sanitize_filename(source_name, max_length=30)
    run_folder_name = f"{timestamp_prefix}_{slug_name}"
    run_output_dir = Settings.OUTPUT_DIR / run_folder_name
    run_output_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel(
        f"[bold green]🎬 TikTok Clipper Dimulai[/bold green]\n"
        f"• Folder Output : [cyan]{run_output_dir}[/cyan]\n"
        f"• Target Niche  : [magenta]{niche}[/magenta]\n"
        f"• Target Klip   : [yellow]{num_clips} klip[/yellow] ({min_duration}s - {max_duration}s)\n"
        f"• Mode Vertikal : [blue]{vertical}[/blue] | Subtitle: [blue]{'Aktif' if subtitles else 'Nonaktif'}[/blue]",
        border_style="green"
    ))

    # Struktur folder per run
    source_dir = run_output_dir / "source"
    audio_dir = run_output_dir / "audio"
    transcript_dir = run_output_dir / "transcript"
    analysis_dir = run_output_dir / "analysis"
    clips_dir = run_output_dir / "clips"

    video_file_to_process: Optional[Path] = None

    # Step 1: Penyiapan File Sumber Video
    if url:
        console.print("\n[bold cyan]⬇️ Mengunduh video dari tautan (Direct Stream / Platform)...[/bold cyan]")
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Sedang mengunduh file video...", total=None)
            downloaded_video, title_slug, err_dl = download_video_from_url(url, source_dir)
            progress.update(task, completed=True)

        if err_dl or not downloaded_video:
            console.print(f"\n[bold red]❌ Gagal Mengunduh Video:[/bold red]\n{err_dl}")
            raise typer.Exit(code=1)

        video_file_to_process = downloaded_video
        console.print(f"[green]✅ Video berhasil diunduh:[/green] {downloaded_video.name}")
    else:
        # File lokal
        if not input_file.exists():
            console.print(f"[bold red]❌ File video lokal tidak ditemukan:[/bold red] {input_file}")
            raise typer.Exit(code=1)

        source_dir.mkdir(parents=True, exist_ok=True)
        target_copy = source_dir / input_file.name
        try:
            shutil.copy2(input_file, target_copy)
            video_file_to_process = target_copy
        except Exception:
            video_file_to_process = input_file
        console.print(f"[green]✅ Menggunakan video lokal:[/green] {video_file_to_process.name}")

    # Step 2: Probe Media dengan FFprobe
    console.print("\n[bold cyan]🔍 Memeriksa format & audio video...[/bold cyan]")
    probe_result, err_probe = probe_media(video_file_to_process)
    if err_probe or not probe_result:
        console.print(f"\n[bold red]❌ Gagal Memeriksa Video:[/bold red]\n{err_probe}")
        raise typer.Exit(code=1)

    console.print(
        f"[green]✅ Media valid:[/green] Durasi {probe_result.duration:.1f}s | "
        f"Resolusi {probe_result.width}x{probe_result.height} ({'Landscape' if probe_result.is_landscape else 'Portrait'})"
    )

    # Step 3: Ekstraksi Audio 16kHz Mono
    console.print("\n[bold cyan]🎙️ Mengekstrak audio untuk transkripsi...[/bold cyan]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Mengekstrak audio (16kHz mono)...", total=None)
        extracted_audio, err_audio = extract_audio(video_file_to_process, audio_dir)
        progress.update(task, completed=True)

    if err_audio or not extracted_audio:
        console.print(f"\n[bold red]❌ Gagal Ekstraksi Audio:[/bold red]\n{err_audio}")
        raise typer.Exit(code=1)

    console.print(f"[green]✅ Audio berhasil diekstrak:[/green] {extracted_audio.name}")

    # Step 4: Transkripsi Audio dengan Groq Whisper
    console.print("\n[bold cyan]🧠 Mentranskripsi percakapan dengan Groq Whisper...[/bold cyan]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task(f"Mengirim ke {Settings.GROQ_WHISPER_MODEL}...", total=None)
        
        def cli_transcribe_cb(msg: str, _percent: int):
            progress.update(task, description=msg)

        transcript_data, err_transcribe = transcribe_audio(extracted_audio, transcript_dir, progress_callback=cli_transcribe_cb)
        progress.update(task, completed=True)

    if err_transcribe or not transcript_data:
        console.print(f"\n[bold red]❌ Gagal Transkripsi:[/bold red]\n{err_transcribe}")
        raise typer.Exit(code=1)

    console.print(
        f"[green]✅ Transkripsi selesai:[/green] {len(transcript_data.segments)} segmen percakapan terdeteksi. "
        f"(Disimpan ke transcript.json & transcript.srt)"
    )

    # Step 5: Analisis AI & Seleksi Klip TikTok 2026
    console.print("\n[bold cyan]🤖 Menganalisis momen terbaik dengan Groq LLM (Strategi 2026)...[/bold cyan]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task(f"Menganalisis hook & nilai viral ({Settings.GROQ_LLM_MODEL})...", total=None)
        validated_clips, err_analyze = analyze_transcript(
            transcript=transcript_data,
            niche=niche,
            min_duration=min_duration,
            max_duration=max_duration,
            num_clips=num_clips,
            output_analysis_dir=analysis_dir
        )
        progress.update(task, completed=True)

    if err_analyze or not validated_clips:
        console.print(f"\n[bold red]❌ Gagal Analisis Klip:[/bold red]\n{err_analyze}")
        raise typer.Exit(code=1)

    console.print(f"[green]✅ Ditemukan {len(validated_clips)} klip dengan hook & potensi viral tertinggi![/green]")

    # Tampilkan tabel kandidat klip
    table_clips = Table(title="Rekomendasi Klip TikTok 2026", show_header=True, header_style="bold green")
    table_clips.add_column("#", style="dim", width=4)
    table_clips.add_column("Judul Klip", style="bold cyan")
    table_clips.add_column("Waktu", width=14)
    table_clips.add_column("Durasi", width=8)
    table_clips.add_column("Skor", width=6)
    table_clips.add_column("Hook 3 Detik", style="italic yellow")

    for c in validated_clips:
        t_range = f"{seconds_to_display_time(c.start_time)} - {seconds_to_display_time(c.end_time)}"
        table_clips.add_row(
            str(c.index),
            c.title,
            t_range,
            f"{c.duration:.1f}s",
            f"{c.score}",
            c.hook[:50] + "..." if len(c.hook) > 50 else c.hook
        )
    console.print(table_clips)

    # Step 6: Rendering Klip Video dengan FFmpeg (Kecuali --analyze-only)
    if not analyze_only:
        console.print("\n[bold cyan]✂️ Merender klip video dengan FFmpeg...[/bold cyan]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            render_task = progress.add_task(f"Memotong {len(validated_clips)} klip...", total=len(validated_clips))
            
            for c in validated_clips:
                progress.update(render_task, description=f"Merender Klip #{c.index}: {c.title[:25]}...")
                from src.editor import render_single_clip
                render_single_clip(
                    source_video=video_file_to_process,
                    clip=c,
                    output_clips_dir=clips_dir,
                    probe=probe_result,
                    burn_subtitles=subtitles,
                    vertical_mode=vertical
                )
                progress.advance(render_task)
    else:
        console.print("\n[bold yellow]ℹ️ Mode --analyze-only aktif. Proses render video dilewati.[/bold yellow]")

    # Step 7: Simpan Metadata Akhir (summary.md & manifest.json)
    settings_dict = {
        "niche": niche,
        "num_clips": num_clips,
        "min_duration": min_duration,
        "max_duration": max_duration,
        "subtitles": subtitles,
        "vertical": vertical,
        "analyze_only": analyze_only
    }
    save_run_metadata(
        output_dir=run_output_dir,
        source_type="url" if url else "file",
        source_input=url if url else str(input_file),
        source_video_path=video_file_to_process,
        niche=niche,
        probe=probe_result,
        total_segments=len(transcript_data.segments),
        clips=validated_clips,
        settings_dict=settings_dict
    )

    # Ringkasan Akhir
    successful_renders = sum(1 for c in validated_clips if c.render_success)
    console.print("\n" + "=" * 60)
    console.print(Panel(
        f"[bold green]🎉 Pemrosesan TikTok Clipper Selesai![/bold green]\n\n"
        f"📁 Direktori Hasil : [bold cyan]{run_output_dir}[/bold cyan]\n"
        f"📄 Ringkasan & Caption: [bold yellow]{run_output_dir / 'summary.md'}[/bold yellow]\n"
        f"📊 Manifest Sistem   : [bold blue]{run_output_dir / 'manifest.json'}[/bold blue]\n"
        f"🎬 Klip Berhasil     : [green]{successful_renders}/{len(validated_clips)} video[/green]\n\n"
        f"[italic]Buka file summary.md untuk langsung menyalin caption, hashtag, dan hook saat mengunggah ke TikTok![/italic]",
        border_style="green",
        title="✨ Sukses"
    ))
