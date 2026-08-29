# ==============================================================================
# 🎬 Dockerfile untuk TikTok Clipper Web Studio (AI Video Generator 2026)
# Multi-stage build: Node.js (Vite + React + Express) & Python 3 (FFmpeg + OpenCV + AI)
# ==============================================================================

# ------------------------------------------------------------------------------
# Tahap 1: Builder (Kompilasi Frontend Vite & Backend Server Bundle)
# ------------------------------------------------------------------------------
FROM node:20-bookworm-slim AS builder

WORKDIR /app

# Salin konfigurasi dependensi Node.js
COPY package.json package-lock.json* bun.lock* ./
COPY tsconfig.json vite.config.ts ./

# Pasang dependensi build
RUN npm install

# Salin source code frontend dan server
COPY index.html ./
COPY src/ ./src/
COPY server.ts ./

# Kompilasi Frontend ke dist/ dan server ke dist/server.cjs
RUN npm run build

# ------------------------------------------------------------------------------
# Tahap 2: Production Runtime (Node.js + Python + FFmpeg + OpenCV Headless)
# ------------------------------------------------------------------------------
FROM node:20-bookworm-slim AS runner

WORKDIR /app

# Atur environment variable untuk production
ENV NODE_ENV=production \
    PORT=3000 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    FFMPEG_PATH=ffmpeg \
    FFPROBE_PATH=ffprobe \
    OUTPUT_DIR=/app/output \
    CACHE_DIR=/app/cache \
    LOG_DIR=/app/logs

# Pasang paket sistem yang dibutuhkan:
# - ffmpeg: untuk manipulasi audio/video, crop 9:16, loudnorm, dan burn subtitle
# - python3 & pip: untuk menjalankan backend pipeline kecerdasan buatan
# - libgl1 & libglib2.0-0: dependensi C untuk OpenCV face detection & speaker tracking
# - curl & ca-certificates: untuk healthcheck dan unduhan HTTPS aman
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    python3 \
    python3-pip \
    python3-venv \
    libgl1 \
    libglib2.0-0 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Salin berkas konfigurasi Python & pasang pustaka AI
COPY requirements.txt ./
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Salin dependensi Node.js produksi & hasil build dari Tahap 1
COPY package.json ./
RUN npm install --omit=dev --ignore-scripts

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/src ./src
COPY --from=builder /app/index.html ./index.html
COPY main.py metadata.json ./
COPY assets ./assets

# Buat folder kerja untuk output video, cache upload, dan log
RUN mkdir -p /app/output /app/cache/uploads /app/logs

# Buka Port 3000 untuk antarmuka Web UI & API
EXPOSE 3000

# Healthcheck untuk memverifikasi layanan Express & API siap melayani request
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/api/system-status || exit 1

# Menjalankan Express Production Server
CMD ["npm", "start"]
