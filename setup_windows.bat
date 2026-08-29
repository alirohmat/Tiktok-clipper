@echo off
chcp 65001 >nul
echo ========================================================
echo   TikTok Clipper - Skrip Instalasi Otomatis (Windows)
echo ========================================================
echo.

:: 1. Cek instalasi Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python belum terinstal atau belum ditambahkan ke PATH!
    echo Silakan unduh Python di https://www.python.org/downloads/
    echo Pastikan mencentang "Add python.exe to PATH" saat instalasi.
    pause
    exit /b 1
)

echo [1/4] Membuat Virtual Environment (venv)...
if not exist "venv" (
    python -m venv venv
    echo     Virtual environment 'venv' berhasil dibuat.
) else (
    echo     Virtual environment 'venv' sudah ada.
)

echo [2/4] Mengaktifkan virtual environment & upgrade pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo [3/4] Menginstal pustaka yang dibutuhkan (requirements.txt)...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menginstal dependencies. Periksa koneksi internet Anda.
    pause
    exit /b 1
)

echo [4/4] Memeriksa file .env...
if not exist ".env" (
    copy .env.example .env >nul
    echo     File .env berhasil dibuat dari .env.example.
    echo     PENTING: Buka file .env dan masukkan GROQ_API_KEY Anda!
) else (
    echo     File .env sudah ada.
)

echo.
echo ========================================================
echo   Instalasi Selesai! Menjalankan Pemeriksaan Sistem...
echo ========================================================
python main.py --check

echo.
echo Untuk mulai memotong video, jalankan: run_windows.bat
echo atau buka terminal lalu ketik:
echo   venv\Scripts\activate
echo   python main.py --input "video.mp4" --niche edukasi
echo.
pause
