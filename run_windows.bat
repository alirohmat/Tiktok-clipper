@echo off
chcp 65001 >nul
title TikTok Clipper 2026 - Launcher

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:MENU
cls
echo ================================================================
echo               🎬 TIKTOK CLIPPER CLI 2026 🎬
echo      Otomasi Klip Pendek Berdasarkan Strategi Algoritma 2026
echo ================================================================
echo.
echo  [1] Periksa Sistem & API Key (--check)
echo  [2] Potong Video dari File Lokal (.mp4)
echo  [3] Potong Video dari URL (YouTube / TikTok / dll)
echo  [4] Analisis Saja Tanpa Render Video (--analyze-only)
echo  [5] Buka Folder Output
echo  [6] Keluar
echo.
set /p opt="Pilih menu [1-6]: "

if "%opt%"=="1" (
    echo.
    python main.py --check
    echo.
    pause
    goto MENU
)

if "%opt%"=="2" (
    echo.
    set /p infile="Masukkan nama / path file video lokal (contoh: video.mp4): "
    set /p iniche="Masukkan niche [edukasi/bisnis/motivasi/komedi/umum] (default: umum): "
    set /p inclips="Jumlah klip [default: 3]: "
    if "%iniche%"=="" set iniche=umum
    if "%inclips%"=="" set inclips=3
    echo.
    echo Menjalankan pemotongan video...
    python main.py --input "%infile%" --niche "%iniche%" --num-clips %inclips%
    echo.
    pause
    goto MENU
)

if "%opt%"=="3" (
    echo.
    set /p inurl="Masukkan URL video: "
    set /p iniche="Masukkan niche [edukasi/bisnis/motivasi/komedi/umum] (default: umum): "
    set /p inclips="Jumlah klip [default: 3]: "
    if "%iniche%"=="" set iniche=umum
    if "%inclips%"=="" set inclips=3
    echo.
    echo Mengunduh dan memproses video...
    python main.py --url "%inurl%" --niche "%iniche%" --num-clips %inclips%
    echo.
    pause
    goto MENU
)

if "%opt%"=="4" (
    echo.
    set /p insrc="Masukkan file video lokal atau URL: "
    set /p iniche="Masukkan niche [default: umum]: "
    if "%iniche%"=="" set iniche=umum
    echo.
    echo Menganalisis...
    if exist "%insrc%" (
        python main.py --input "%insrc%" --niche "%iniche%" --analyze-only
    ) else (
        python main.py --url "%insrc%" --niche "%iniche%" --analyze-only
    )
    echo.
    pause
    goto MENU
)

if "%opt%"=="5" (
    if not exist "output" mkdir output
    explorer output
    goto MENU
)

if "%opt%"=="6" (
    exit /b 0
)

goto MENU
