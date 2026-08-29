"""
Modul Metadata & Pelaporan
Menyimpan ringkasan Markdown (summary.md) dan manifest JSON (manifest.json) untuk hasil pemrosesan.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.models import MediaProbeResult, RunManifest, ValidatedClip
from src.utils import logger, seconds_to_display_time


def generate_summary_markdown(
    run_folder_name: str,
    source_input: str,
    niche: str,
    probe: Optional[MediaProbeResult],
    clips: List[ValidatedClip]
) -> str:
    """Membuat konten ringkasan lengkap berformat Markdown (summary.md)."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration_str = f"{probe.duration:.1f}s" if probe else "N/A"
    res_str = f"{probe.width}x{probe.height}" if probe else "N/A"

    lines = [
        f"# Ringkasan Klip TikTok - {run_folder_name}",
        f"",
        f"- **Tanggal Pemrosesan**: {now_str}",
        f"- **Sumber Video**: `{source_input}`",
        f"- **Durasi Asli**: {duration_str} ({res_str})",
        f"- **Niche Target**: {niche}",
        f"- **Total Klip Dihasilkan**: {len(clips)} klip",
        f"",
        f"---",
        f""
    ]

    for clip in clips:
        status_badge = "✅ Berhasil Dirender" if clip.render_success else "⚠️ Gagal Render Video"
        sub_badge = "Ya (Hardsub)" if clip.subtitles_burned else "Terpisah (.srt)"
        start_str = seconds_to_display_time(clip.start_time)
        end_str = seconds_to_display_time(clip.end_time)
        
        hashtag_text = " ".join([f"#{tag}" for tag in clip.hashtags])

        lines.extend([
            f"## Klip #{clip.index}: {clip.title}",
            f"",
            f"**Status**: {status_badge} | **Subtitle**: {sub_badge} | **Skor Potensi**: ⭐ **{clip.score}/100**  ",
            f"**Waktu**: `{start_str}` - `{end_str}` ({clip.duration:.1f} detik)  ",
            f"",
            f"### 🎯 Hook 3 Detik Pertama:",
            f"> \"{clip.hook}\"",
            f"",
            f"### 📝 Caption SEO TikTok:",
            f"```text",
            f"{clip.caption}",
            f"```",
            f"",
            f"### 🏷️ Rekomendasi Hashtags:",
            f"`{hashtag_text}`",
            f"",
            f"### 📣 Call To Action (CTA):",
            f"> {clip.cta}",
            f"",
            f"### 🔄 Saran Looping Video:",
            f"> {clip.loop_suggestion}",
            f"",
            f"### 💡 Alasan Pemilihan:",
            f"{clip.reason}",
            f"",
            f"---",
            f""
        ])

    lines.extend([
        f"## 📱 Panduan Upload TikTok 2026",
        f"1. **Upload di Jam Aktif Audience**: Cek analitik kreator akun Anda.",
        f"2. **Gunakan Sound Populer**: Tambahkan audio yang sedang tren dengan volume 5-10% di latar belakang.",
        f"3. **Salin Caption SEO**: Pastikan kata kunci utama berada di baris pertama.",
        f"4. **Gunakan Cover/Thumbnail Menarik**: Pasang teks hook besar di bagian atas video.",
        f"5. **Interaksi 30 Menit Pertama**: Balas komentar penonton sesegera mungkin untuk mendorong algoritma."
    ])

    return "\n".join(lines)


def save_run_metadata(
    output_dir: Path,
    source_type: str,
    source_input: str,
    source_video_path: Path,
    niche: str,
    probe: Optional[MediaProbeResult],
    total_segments: int,
    clips: List[ValidatedClip],
    settings_dict: Dict[str, Any]
) -> None:
    """Menyimpan summary.md dan manifest.json ke direktori output."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Simpan summary.md
    summary_content = generate_summary_markdown(
        run_folder_name=output_dir.name,
        source_input=source_input,
        niche=niche,
        probe=probe,
        clips=clips
    )
    summary_file = output_dir / "summary.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary_content)

    # 2. Simpan manifest.json
    manifest = RunManifest(
        app_version="1.0.0",
        created_at=datetime.now().isoformat(),
        source_type=source_type,
        source_input=source_input,
        source_video_path=str(source_video_path),
        source_duration=probe.duration if probe else 0.0,
        source_resolution=f"{probe.width}x{probe.height}" if probe else "N/A",
        niche=niche,
        total_segments=total_segments,
        target_clips_count=len(clips),
        successful_clips_count=sum(1 for c in clips if c.render_success),
        settings=settings_dict,
        clips=[c.model_dump(exclude={"segments"}) for c in clips]
    )

    manifest_file = output_dir / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(), f, ensure_ascii=False, indent=2)

    logger.info(f"Metadata berhasil disimpan: {summary_file.name} & {manifest_file.name}")
