#!/usr/bin/env python3
"""
TikTok Clipper - Entry Point Utama
Menjalankan CLI Typer untuk memotong video panjang menjadi klip TikTok pendek otomatis.

Penggunaan:
    python main.py --check
    python main.py --input "video.mp4" --niche edukasi --num-clips 3
    python main.py --url "https://..." --niche bisnis --num-clips 3
"""

import sys
from src.cli import app

if __name__ == "__main__":
    app()
