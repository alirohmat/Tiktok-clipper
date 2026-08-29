/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  Video,
  Play,
  CheckCircle,
  Terminal,
  FileText,
  Settings as SettingsIcon,
  Copy,
  Check,
  Sparkles,
  Hash,
  Clock,
  AlertCircle,
  Share2,
  Bookmark,
  Flame,
  Cpu,
  ArrowRight,
  ShieldCheck,
  Download,
  RefreshCw,
  Layers,
  Sliders,
  ExternalLink,
  HelpCircle,
  FolderOpen
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<'generator' | 'strategy' | 'inspector' | 'env' | 'guide'>('generator');
  
  // State Generator Perintah
  const [sourceType, setSourceType] = useState<'input' | 'url'>('input');
  const [inputVal, setInputVal] = useState('podcast_bisnis_eps12.mp4');
  const [urlVal, setUrlVal] = useState('https://www.youtube.com/watch?v=sample-video');
  const [niche, setNiche] = useState('bisnis');
  const [numClips, setNumClips] = useState(3);
  const [minDur, setMinDur] = useState(15);
  const [maxDur, setMaxDur] = useState(60);
  const [subtitles, setSubtitles] = useState(true);
  const [vertical, setVertical] = useState('auto');
  const [analyzeOnly, setAnalyzeOnly] = useState(false);
  const [debug, setDebug] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState(false);

  // State Inspector Preview
  const [inspectorFile, setInspectorFile] = useState<'summary' | 'manifest' | 'transcript' | 'srt' | 'clip_json'>('summary');
  const [selectedClipIdx, setSelectedClipIdx] = useState(0);

  // Buat String Command CLI
  const generateCommand = () => {
    const parts = ['python main.py'];
    if (sourceType === 'input') {
      parts.push(`--input "${inputVal || 'video.mp4'}"`);
    } else {
      parts.push(`--url "${urlVal || 'https://...'}"`);
    }
    if (niche !== 'umum') parts.push(`--niche ${niche}`);
    if (numClips !== 3) parts.push(`--num-clips ${numClips}`);
    if (minDur !== 15) parts.push(`--min-duration ${minDur}`);
    if (maxDur !== 60) parts.push(`--max-duration ${maxDur}`);
    if (!subtitles) parts.push('--no-subtitles');
    if (vertical !== 'auto') parts.push(`--vertical ${vertical}`);
    if (analyzeOnly) parts.push('--analyze-only');
    if (debug) parts.push('--debug');
    return parts.join(' ');
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(true);
    setTimeout(() => setCopiedCmd(false), 2000);
  };

  // Contoh Data Klip
  const sampleClips = [
    {
      index: 1,
      title: "Rahasia Cashflow Bisnis Pemula",
      slug: "01-rahasia-cashflow-bisnis-pemula",
      duration: 38.4,
      start: "01:14",
      end: "01:52",
      score: 94,
      hook: "90% bisnis pemula bangkrut di tahun pertama cuma karena salah paham soal uang dingin!",
      caption: "Rahasia Cashflow Bisnis Pemula yang wajib dipahami sebelum buka usaha! Jangan sampai modal habis di awal. Simak tips pembagian rekening operasional ini.",
      hashtags: ["bisnispemula", "keuanganusaha", "belajarbisnis", "tipsusaha"],
      cta: "Save video ini biar nggak bingung pas mulai hitung modal nanti!",
      loop: "Di akhir video menyebutkan pembagian 3 rekening, yang langsung menjadi jawaban dari masalah bangkrut di hook awal.",
      reason: "Hook 3 detik sangat emosional dan relevan bagi target audiens wirausaha dengan penyelesaian masalah praktis.",
      transcriptText: "Banyak orang mikir buka bisnis itu cuma soal jualan laku atau enggak. Padahal 90 persen bisnis pemula bangkrut di tahun pertama cuma karena salah paham soal uang dingin! Pisahin rekening pribadi sama rekening operasional sejak hari pertama..."
    },
    {
      index: 2,
      title: "Trik Pricing Anti Perang Harga",
      slug: "02-trik-pricing-anti-perang-harga",
      duration: 42.1,
      start: "04:30",
      end: "05:12",
      score: 89,
      hook: "Jangan pernah nurunin harga kalau kompetitor kamu banting harga gila-gilaan!",
      caption: "Trik Pricing Anti Perang Harga untuk UMKM. Cara jualan produk premium tanpa takut kalah saing dengan produk murah di marketplace.",
      hashtags: ["strategipricing", "umkmindonesia", "omsetnaik", "branding"],
      cta: "Share ke partner bisnis kamu biar gak ikut-ikutan banting harga!",
      loop: "Kalimat penutup 'fokus ke nilai bukan diskon' langsung menyambung ke hook awal 'jangan turunin harga'.",
      reason: "Menjawab ketakutan terbesar pelaku usaha (perang harga) dengan solusi anchoring value.",
      transcriptText: "Kalau kompetitor kamu turun harga 50%, kamu jangan ikutan panik. Buat bundle paket bernilai tinggi yang nggak bisa dibandingin head to head sama produk mereka..."
    },
    {
      index: 3,
      title: "Mindset Rekrut Karyawan Pertama",
      slug: "03-mindset-rekrut-karyawan-pertama",
      duration: 29.5,
      start: "08:15",
      end: "08:44",
      score: 85,
      hook: "Kapan waktu paling tepat buat rekrut karyawan pertama?",
      caption: "Mindset Rekrut Karyawan Pertama yang efektif. Kapan saat yang pas delegasi tugas tanpa membebani keuangan usaha?",
      hashtags: ["manajemenbisnis", "hiringtips", "scaleup", "timkerja"],
      cta: "Ketik di kolom komentar, kamu udah punya berapa tim sekarang?",
      loop: "Kriteria omset stabil di akhir klip menjawab pertanyaan waktu yang tepat di hook awal.",
      reason: "Topik actionable, durasi padat di bawah 30 detik untuk completion rate optimal.",
      transcriptText: "Bukan pas kamu capek, tapi pas waktu kamu lebih berharga untuk strategi daripada ngerjain hal teknis yang berulang..."
    }
  ];

  const currentClip = sampleClips[selectedClipIdx];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header Utama */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 via-rose-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-pink-500/20">
              <Video className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-white">TikTok Clipper</h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-pink-500/20 text-pink-400 border border-pink-500/30 font-medium">
                  Algoritma 2026
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 font-medium">
                  Groq AI Powered
                </span>
              </div>
              <p className="text-xs text-slate-400">CLI Python & Web Companion untuk Otomasi Klip Vertikal Pendek</p>
            </div>
          </div>

          {/* Navigasi Tab */}
          <nav className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => setActiveTab('generator')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all font-medium ${
                activeTab === 'generator'
                  ? 'bg-gradient-to-r from-pink-500 to-rose-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              CLI Generator
            </button>
            <button
              onClick={() => setActiveTab('strategy')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all font-medium ${
                activeTab === 'strategy'
                  ? 'bg-gradient-to-r from-pink-500 to-rose-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Flame className="w-3.5 h-3.5" />
              Strategi 2026
            </button>
            <button
              onClick={() => setActiveTab('inspector')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all font-medium ${
                activeTab === 'inspector'
                  ? 'bg-gradient-to-r from-pink-500 to-rose-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Output Inspector
            </button>
            <button
              onClick={() => setActiveTab('env')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all font-medium ${
                activeTab === 'env'
                  ? 'bg-gradient-to-r from-pink-500 to-rose-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <SettingsIcon className="w-3.5 h-3.5" />
              .env Config
            </button>
            <button
              onClick={() => setActiveTab('guide')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all font-medium ${
                activeTab === 'guide'
                  ? 'bg-gradient-to-r from-pink-500 to-rose-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <HelpCircle className="w-3.5 h-3.5" />
              Panduan
            </button>
          </nav>
        </div>
      </header>

      {/* Konten Utama */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full">
        {/* TAB 1: CLI GENERATOR & BUILDER */}
        {activeTab === 'generator' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Form Konfigurasi Perintah */}
            <div className="lg:col-span-7 space-y-5">
              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-5">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-pink-400" />
                    <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Konfigurasi Parameter CLI</h2>
                  </div>
                  <span className="text-xs text-slate-400">main.py options</span>
                </div>

                {/* Pilihan Sumber Video */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">Sumber Video</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setSourceType('input')}
                      className={`p-2.5 rounded-xl border text-xs font-medium flex items-center justify-center gap-2 transition-all ${
                        sourceType === 'input'
                          ? 'bg-pink-500/15 border-pink-500 text-pink-300 shadow-sm'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <FolderOpen className="w-3.5 h-3.5" />
                      File Lokal (--input)
                    </button>
                    <button
                      type="button"
                      onClick={() => setSourceType('url')}
                      className={`p-2.5 rounded-xl border text-xs font-medium flex items-center justify-center gap-2 transition-all ${
                        sourceType === 'url'
                          ? 'bg-cyan-500/15 border-cyan-500 text-cyan-300 shadow-sm'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      Tautan URL (--url)
                    </button>
                  </div>

                  {sourceType === 'input' ? (
                    <div className="mt-2">
                      <input
                        type="text"
                        value={inputVal}
                        onChange={(e) => setInputVal(e.target.value)}
                        placeholder="video.mp4 atau jalur/ke/video.mp4"
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-pink-500 font-mono"
                      />
                      <p className="text-[11px] text-slate-500 mt-1">Mendukung format MP4, MKV, MOV, WebM, dll.</p>
                    </div>
                  ) : (
                    <div className="mt-2">
                      <input
                        type="text"
                        value={urlVal}
                        onChange={(e) => setUrlVal(e.target.value)}
                        placeholder="https://www.youtube.com/watch?v=..."
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
                      />
                      <p className="text-[11px] text-slate-500 mt-1">Otomatis diunduh dengan yt-dlp (max 1080p, audio m4a).</p>
                    </div>
                  )}
                </div>

                {/* Niche & Jumlah Klip */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">Niche Konten (--niche)</label>
                    <select
                      value={niche}
                      onChange={(e) => setNiche(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-pink-500"
                    >
                      <option value="umum">Umum (Default)</option>
                      <option value="bisnis">Bisnis & Finansial</option>
                      <option value="edukasi">Edukasi & Tutorial</option>
                      <option value="motivasi">Motivasi & Self-Improvement</option>
                      <option value="teknologi">Teknologi & Gadget</option>
                      <option value="komedi">Komedi & Hiburan</option>
                      <option value="kuliner">Kuliner & Resep</option>
                      <option value="kesehatan">Kesehatan & Kebugaran</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300 flex justify-between">
                      <span>Jumlah Klip (--num-clips)</span>
                      <span className="text-pink-400 font-mono">{numClips} klip</span>
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={numClips}
                      onChange={(e) => setNumClips(parseInt(e.target.value))}
                      className="w-full accent-pink-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                      <span>1 klip</span>
                      <span>3 (hemat)</span>
                      <span>10 klip</span>
                    </div>
                  </div>
                </div>

                {/* Durasi Min / Max */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300 flex justify-between">
                      <span>Min Durasi (--min-duration)</span>
                      <span className="text-cyan-400 font-mono">{minDur}s</span>
                    </label>
                    <input
                      type="range"
                      min="10"
                      max="30"
                      value={minDur}
                      onChange={(e) => setMinDur(parseInt(e.target.value))}
                      className="w-full accent-cyan-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300 flex justify-between">
                      <span>Max Durasi (--max-duration)</span>
                      <span className="text-cyan-400 font-mono">{maxDur}s</span>
                    </label>
                    <input
                      type="range"
                      min="30"
                      max="120"
                      value={maxDur}
                      onChange={(e) => setMaxDur(parseInt(e.target.value))}
                      className="w-full accent-cyan-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                    />
                  </div>
                </div>

                {/* Opsi Video Vertikal & Subtitle */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">Format Vertikal (--vertical)</label>
                    <select
                      value={vertical}
                      onChange={(e) => setVertical(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-pink-500"
                    >
                      <option value="auto">auto (Otomatis crop jika landscape)</option>
                      <option value="crop">crop (Center crop 1080x1920)</option>
                      <option value="pad">pad (Skala + Black bar atas-bawah)</option>
                      <option value="off">off (Biarkan rasio asli)</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">Subtitle Hardsub (--subtitles)</label>
                    <button
                      type="button"
                      onClick={() => setSubtitles(!subtitles)}
                      className={`w-full p-2 rounded-xl border text-xs font-medium flex items-center justify-between px-3 transition-all ${
                        subtitles
                          ? 'bg-pink-500/15 border-pink-500 text-pink-300'
                          : 'bg-slate-950 border-slate-800 text-slate-500'
                      }`}
                    >
                      <span>{subtitles ? 'Bakar Teks ke Video (Aktif)' : 'File .srt Saja (Nonaktif)'}</span>
                      <span className={`w-2 h-2 rounded-full ${subtitles ? 'bg-pink-400' : 'bg-slate-600'}`}></span>
                    </button>
                  </div>
                </div>

                {/* Flags Tambahan */}
                <div className="flex flex-wrap items-center gap-4 pt-1 text-xs">
                  <label className="flex items-center gap-2 cursor-pointer text-slate-400 hover:text-slate-200">
                    <input
                      type="checkbox"
                      checked={analyzeOnly}
                      onChange={(e) => setAnalyzeOnly(e.target.checked)}
                      className="rounded bg-slate-950 border-slate-800 text-pink-500 focus:ring-0"
                    />
                    <span>--analyze-only (Hanya analisis JSON & summary)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-slate-400 hover:text-slate-200">
                    <input
                      type="checkbox"
                      checked={debug}
                      onChange={(e) => setDebug(e.target.checked)}
                      className="rounded bg-slate-950 border-slate-800 text-pink-500 focus:ring-0"
                    />
                    <span>--debug (Log detail teknis)</span>
                  </label>
                </div>
              </div>
            </div>

            {/* Kotak Perintah Terformat & Diagnostic Box */}
            <div className="lg:col-span-5 space-y-5">
              {/* Box Terminal Command */}
              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-xs font-semibold text-white uppercase tracking-wider">Perintah Siap Dijalankan</h3>
                  </div>
                  <button
                    onClick={() => handleCopy(generateCommand())}
                    className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-pink-500/20 text-pink-300 hover:bg-pink-500/30 border border-pink-500/30 transition-all"
                  >
                    {copiedCmd ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedCmd ? 'Tersalin!' : 'Salin Perintah'}
                  </button>
                </div>

                <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80 font-mono text-xs text-pink-300 break-all leading-relaxed shadow-inner">
                  {generateCommand()}
                </div>

                <div className="text-[11px] text-slate-400 space-y-1">
                  <p>💡 <strong>Cara menjalankan:</strong> Buka terminal / CMD di folder proyek, lalu paste perintah di atas.</p>
                </div>
              </div>

              {/* Box Quick Actions */}
              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-3">
                <h3 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  Perintah Cepat Tambahan
                </h3>

                <div className="space-y-2">
                  <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-semibold text-slate-200">Pemeriksaan Sistem (--check)</div>
                      <div className="font-mono text-[11px] text-slate-500">python main.py --check</div>
                    </div>
                    <button
                      onClick={() => handleCopy('python main.py --check')}
                      className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
                      title="Salin"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-semibold text-slate-200">Eksekusi Windows Otomatis (.bat)</div>
                      <div className="font-mono text-[11px] text-slate-500">run_windows.bat</div>
                    </div>
                    <button
                      onClick={() => handleCopy('run_windows.bat')}
                      className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
                      title="Salin"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Status Environment Container */}
              <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-4 text-xs space-y-2">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    FFmpeg & FFprobe
                  </span>
                  <span className="text-emerald-400 font-mono">v4.4.2 Siap</span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    Python Runtime
                  </span>
                  <span className="text-emerald-400 font-mono">3.10+ Siap</span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    Pustaka Eksternal
                  </span>
                  <span className="text-emerald-400 font-mono">Typer, Rich, Groq, yt-dlp</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: STRATEGI TIKTOK 2026 */}
        {activeTab === 'strategy' && (
          <div className="space-y-6">
            <div className="bg-gradient-to-r from-pink-950/40 via-purple-950/40 to-slate-900 border border-pink-900/40 rounded-2xl p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-pink-500/20 border border-pink-500/30 flex items-center justify-center shrink-0">
                  <Flame className="w-6 h-6 text-pink-400" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">Prinsip Algoritma TikTok 2026 pada AI Clipper</h2>
                  <p className="text-xs text-slate-300 mt-1 max-w-3xl leading-relaxed">
                    Setiap detik video dipindai oleh model AI Groq LLM (temperature 0.2) dengan kriteria evaluasi ketat berikut untuk memastikan klip memiliki probabilitas retensi dan sebaran organik tertinggi:
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-pink-500/15 border border-pink-500/30 flex items-center justify-center text-pink-400 font-bold text-xs">
                  01
                </div>
                <h3 className="text-sm font-bold text-white">Hook 3 Detik Pertama</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Menghilangkan basa-basi intro (&quot;halo guys&quot;, &quot;kembali lagi&quot;). Klip harus dimulai dari pertanyaan tajam, fakta mengejutkan, atau pernyataan paradoks yang menghentikan scroll.
                </p>
              </div>

              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-xs">
                  02
                </div>
                <h3 className="text-sm font-bold text-white">High Completion Rate & Payoff</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Struktur klip dipastikan memiliki klimaks dan penyelesaian (payoff) yang tuntas. Mencegah klip terpotong nanggung yang menyebabkan kekecewaan penonton.
                </p>
              </div>

              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 font-bold text-xs">
                  03
                </div>
                <h3 className="text-sm font-bold text-white">Save & Share Worthy</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Algoritma memprioritaskan momen edukatif, tutorial langkah demi langkah, template, atau checklist yang mendorong penonton menekan tombol <em>Save/Bookmark</em>.
                </p>
              </div>

              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-xs">
                  04
                </div>
                <h3 className="text-sm font-bold text-white">SEO Caption Terindeks</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Kata kunci utama wajib muncul di 50 karakter pertama caption. Panjang ideal 120–220 karakter untuk menangkap penelusuran kata kunci TikTok Search Bar.
                </p>
              </div>

              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400 font-bold text-xs">
                  05
                </div>
                <h3 className="text-sm font-bold text-white">Hashtags Terfokus (3-5)</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Bebas dari hashtag sampah seperti #fyp, #viral, #foryou. Sistem menghasilkan tag niche spesifik yang memperjelas kategorisasi klip ke audiens tertarget.
                </p>
              </div>

              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 font-bold text-xs">
                  06
                </div>
                <h3 className="text-sm font-bold text-white">Seamless Loop Suggestion</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Menyediakan panduan bagaimana kalimat akhir klip dapat berkesinambungan menjawab kalimat awal sehingga penonton menonton video lebih dari satu kali.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: OUTPUT INSPECTOR & SIMULASI PREVIEW */}
        {activeTab === 'inspector' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Simulasi TikTok Phone Player */}
            <div className="lg:col-span-4 flex flex-col items-center">
              <div className="w-[280px] sm:w-[300px] h-[560px] bg-slate-900 rounded-[36px] border-4 border-slate-800 shadow-2xl relative overflow-hidden flex flex-col justify-between p-4">
                {/* Background Video Mockup */}
                <div className="absolute inset-0 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
                  <div className="text-center space-y-2 p-4">
                    <div className="w-14 h-14 rounded-full bg-pink-500/20 border border-pink-500/40 flex items-center justify-center mx-auto text-pink-400">
                      <Play className="w-6 h-6 translate-x-0.5" />
                    </div>
                    <span className="text-xs font-semibold text-slate-400 block">1080x1920 (9:16 Vertikal)</span>
                    <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 font-mono">
                      Loudnorm EBU R128 Active
                    </span>
                  </div>
                </div>

                {/* Top Overlay */}
                <div className="relative z-10 flex justify-between items-center text-[11px] text-white/80 font-medium">
                  <span className="bg-black/40 backdrop-blur-sm px-2 py-0.5 rounded-md">Klip #{currentClip.index}</span>
                  <span className="bg-pink-500/80 px-2 py-0.5 rounded-md font-bold text-white text-[10px]">⭐ {currentClip.score}/100</span>
                </div>

                {/* Subtitle Box Simulation */}
                <div className="relative z-10 my-auto text-center px-2">
                  <span className="inline-block bg-black/80 text-yellow-300 text-xs font-bold px-3 py-1.5 rounded-lg shadow-lg border border-yellow-400/30">
                    &ldquo;{currentClip.hook}&rdquo;
                  </span>
                </div>

                {/* Bottom Overlay & Actions */}
                <div className="relative z-10 space-y-2">
                  <div className="flex justify-between items-end">
                    <div className="space-y-1 max-w-[200px]">
                      <div className="text-xs font-bold text-white flex items-center gap-1">
                        @tiktokclipper_bot
                        <CheckCircle className="w-3 h-3 text-cyan-400" />
                      </div>
                      <p className="text-[10px] text-white/90 line-clamp-2 leading-tight font-light">
                        {currentClip.caption}
                      </p>
                      <div className="flex flex-wrap gap-1 text-[9px] text-cyan-300 font-mono">
                        {currentClip.hashtags.map((h) => (
                          <span key={h}>#{h}</span>
                        ))}
                      </div>
                    </div>

                    {/* Right TikTok Action Icons */}
                    <div className="flex flex-col items-center gap-3 text-white">
                      <div className="flex flex-col items-center">
                        <Flame className="w-5 h-5 text-pink-500" />
                        <span className="text-[9px] font-bold">94K</span>
                      </div>
                      <div className="flex flex-col items-center">
                        <Bookmark className="w-5 h-5 text-yellow-400" />
                        <span className="text-[9px] font-bold">12K</span>
                      </div>
                      <div className="flex flex-col items-center">
                        <Share2 className="w-5 h-5 text-cyan-400" />
                        <span className="text-[9px] font-bold">4.8K</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Selector Klip */}
              <div className="flex items-center gap-2 mt-4">
                {sampleClips.map((c, i) => (
                  <button
                    key={c.index}
                    onClick={() => setSelectedClipIdx(i)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium border transition-all ${
                      selectedClipIdx === i
                        ? 'bg-pink-500 border-pink-400 text-white shadow-sm'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                    }`}
                  >
                    Klip #{c.index}
                  </button>
                ))}
              </div>
            </div>

            {/* File Viewer Simulator */}
            <div className="lg:col-span-8 space-y-4">
              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-4">
                {/* Header Selector File Output */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-1.5 text-xs">
                    <button
                      onClick={() => setInspectorFile('summary')}
                      className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                        inspectorFile === 'summary'
                          ? 'bg-pink-500/20 text-pink-300 border border-pink-500/30'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                    >
                      summary.md
                    </button>
                    <button
                      onClick={() => setInspectorFile('clip_json')}
                      className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                        inspectorFile === 'clip_json'
                          ? 'bg-pink-500/20 text-pink-300 border border-pink-500/30'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                    >
                      {currentClip.slug}.json
                    </button>
                    <button
                      onClick={() => setInspectorFile('srt')}
                      className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                        inspectorFile === 'srt'
                          ? 'bg-pink-500/20 text-pink-300 border border-pink-500/30'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                    >
                      {currentClip.slug}.srt
                    </button>
                    <button
                      onClick={() => setInspectorFile('manifest')}
                      className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                        inspectorFile === 'manifest'
                          ? 'bg-pink-500/20 text-pink-300 border border-pink-500/30'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                    >
                      manifest.json
                    </button>
                  </div>

                  <button
                    onClick={() => {
                      let textToCopy = '';
                      if (inspectorFile === 'summary') textToCopy = currentClip.caption;
                      else if (inspectorFile === 'clip_json') textToCopy = JSON.stringify(currentClip, null, 2);
                      else if (inspectorFile === 'srt') textToCopy = `1\n00:00:00,000 --> 00:00:03,500\n${currentClip.hook}`;
                      else textToCopy = JSON.stringify({ app_version: "1.0.0", clips_count: sampleClips.length }, null, 2);
                      handleCopy(textToCopy);
                    }}
                    className="flex items-center gap-1 text-xs text-slate-400 hover:text-white bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800"
                  >
                    <Copy className="w-3 h-3" />
                    Salin Konten
                  </button>
                </div>

                {/* Konten File Terpilih */}
                <div className="bg-slate-950 rounded-xl p-4 border border-slate-800/80 font-mono text-xs overflow-x-auto max-h-[420px] overflow-y-auto leading-relaxed">
                  {inspectorFile === 'summary' && (
                    <div className="space-y-4 font-sans text-slate-200">
                      <div className="border-b border-slate-800 pb-2">
                        <h3 className="text-sm font-bold text-pink-400">## Klip #{currentClip.index}: {currentClip.title}</h3>
                        <p className="text-xs text-slate-400">Durasi: {currentClip.duration}s ({currentClip.start} - {currentClip.end}) | Skor: {currentClip.score}/100</p>
                      </div>

                      <div>
                        <span className="text-xs font-semibold text-yellow-400 uppercase tracking-wider block mb-1">🎯 Hook 3 Detik:</span>
                        <blockquote className="border-l-2 border-yellow-400 pl-3 italic text-slate-300 bg-yellow-950/20 py-1.5 rounded-r-lg">
                          &ldquo;{currentClip.hook}&rdquo;
                        </blockquote>
                      </div>

                      <div>
                        <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider block mb-1">📝 Caption SEO TikTok:</span>
                        <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 text-xs text-slate-200 select-all">
                          {currentClip.caption}
                        </div>
                      </div>

                      <div>
                        <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider block mb-1">🏷️ Rekomendasi Hashtags:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {currentClip.hashtags.map(t => (
                            <span key={t} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-xs">
                              #{t}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider block mb-1">🔄 Saran Seamless Loop:</span>
                        <p className="text-xs text-slate-300 bg-purple-950/20 p-2.5 rounded-lg border border-purple-900/30">
                          {currentClip.loop}
                        </p>
                      </div>
                    </div>
                  )}

                  {inspectorFile === 'clip_json' && (
                    <pre className="text-pink-300">
                      {JSON.stringify(currentClip, null, 2)}
                    </pre>
                  )}

                  {inspectorFile === 'srt' && (
                    <pre className="text-emerald-300 space-y-2">
{`1
00:00:00,000 --> 00:00:03,420
${currentClip.hook}

2
00:00:03,420 --> 00:00:08,150
Pisahin rekening pribadi sama rekening operasional sejak hari pertama.

3
00:00:08,150 --> 00:00:15,000
Bagi jadi 3 pos: pos modal putar, pos darurat usaha, dan pos gaji founder.

4
00:00:15,000 --> 00:00:${Math.round(currentClip.duration)},000
Simpan video ini biar bisnis kamu nggak boncos di awal.`}
                    </pre>
                  )}

                  {inspectorFile === 'manifest' && (
                    <pre className="text-cyan-300">
{JSON.stringify({
  "app_version": "1.0.0",
  "created_at": new Date().toISOString(),
  "source_type": "file",
  "source_input": "podcast_bisnis_eps12.mp4",
  "source_duration": 940.5,
  "source_resolution": "1920x1080",
  "niche": "bisnis",
  "total_segments": 142,
  "target_clips_count": 3,
  "successful_clips_count": 3,
  "settings": {
    "min_duration": 15,
    "max_duration": 60,
    "vertical": "auto",
    "subtitles": true
  }
}, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: .ENV CONFIGURATOR */}
        {activeTab === 'env' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-6 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <SettingsIcon className="w-5 h-5 text-pink-400" />
                  <div>
                    <h2 className="text-base font-bold text-white">Konfigurasi .env</h2>
                    <p className="text-xs text-slate-400">File pengaturan lingkungan aplikasi TikTok Clipper</p>
                  </div>
                </div>
                <button
                  onClick={() => handleCopy(`GROQ_API_KEY=\nGROQ_BASE_URL=https://api.groq.com/openai/v1\nGROQ_WHISPER_MODEL=whisper-large-v3\nGROQ_LLM_MODEL=openai/gpt-oss-120b\nFFMPEG_PATH=ffmpeg\nFFPROBE_PATH=ffprobe\nOUTPUT_DIR=output\nCACHE_DIR=cache\nLOG_DIR=logs\nDEFAULT_MIN_DURATION=15\nDEFAULT_MAX_DURATION=60\nDEFAULT_NUM_CLIPS=3\nDEFAULT_NICHE=umum`)}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-pink-500/20 text-pink-300 hover:bg-pink-500/30 border border-pink-500/30"
                >
                  <Copy className="w-3.5 h-3.5" />
                  Salin .env.example
                </button>
              </div>

              <div className="space-y-4 text-xs">
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-slate-300 space-y-2">
                  <div><span className="text-pink-400 font-bold">GROQ_API_KEY</span>=<span className="text-yellow-400">&quot;gsk_...&quot;</span> <span className="text-slate-500"># Wajib: Dapatkan gratis di console.groq.com</span></div>
                  <div><span className="text-pink-400 font-bold">GROQ_BASE_URL</span>=https://api.groq.com/openai/v1</div>
                  <div><span className="text-pink-400 font-bold">GROQ_WHISPER_MODEL</span>=whisper-large-v3 <span className="text-slate-500"># Model transkripsi suara</span></div>
                  <div><span className="text-pink-400 font-bold">GROQ_LLM_MODEL</span>=openai/gpt-oss-120b <span className="text-slate-500"># Model AI seleksi klip</span></div>
                  <div><span className="text-cyan-400 font-bold">FFMPEG_PATH</span>=ffmpeg <span className="text-slate-500"># Path executable ffmpeg</span></div>
                  <div><span className="text-cyan-400 font-bold">FFPROBE_PATH</span>=ffprobe <span className="text-slate-500"># Path executable ffprobe</span></div>
                  <div><span className="text-emerald-400 font-bold">OUTPUT_DIR</span>=output <span className="text-slate-500"># Folder hasil klip</span></div>
                  <div><span className="text-emerald-400 font-bold">CACHE_DIR</span>=cache <span className="text-slate-500"># Folder cache transkrip & analisis</span></div>
                  <div><span className="text-emerald-400 font-bold">LOG_DIR</span>=logs <span className="text-slate-500"># Folder log app.log</span></div>
                  <div><span className="text-slate-400 font-bold">DEFAULT_MIN_DURATION</span>=15</div>
                  <div><span className="text-slate-400 font-bold">DEFAULT_MAX_DURATION</span>=60</div>
                  <div><span className="text-slate-400 font-bold">DEFAULT_NUM_CLIPS</span>=3</div>
                  <div><span className="text-slate-400 font-bold">DEFAULT_NICHE</span>=umum</div>
                </div>

                <div className="bg-pink-950/20 border border-pink-900/30 p-3.5 rounded-xl text-slate-300 space-y-1">
                  <div className="font-semibold text-pink-400 flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4" />
                    Keamanan API Key & Kuota Gratis Groq:
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Aplikasi otomatis menerapkan jeda 2 detik antar panggilan API dan mekanisme exponential backoff (2s, 4s, 8s) untuk memastikan akun free-tier Groq tidak terkena batas rate-limit.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: PANDUAN LENGKAP */}
        {activeTab === 'guide' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-6 shadow-xl space-y-5">
              <h2 className="text-base font-bold text-white border-b border-slate-800 pb-3">
                Panduan Menjalankan TikTok Clipper di Komputer Anda
              </h2>

              <div className="space-y-4 text-xs text-slate-300">
                <div className="flex gap-3">
                  <div className="w-6 h-6 rounded-full bg-pink-500/20 text-pink-400 font-bold flex items-center justify-center shrink-0 border border-pink-500/30">1</div>
                  <div>
                    <h3 className="font-bold text-white text-sm">Persiapan Lingkungan (Untuk Pengguna Windows)</h3>
                    <p className="text-slate-400 mt-1">Cukup jalankan file batch otomatis:</p>
                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono text-pink-300 mt-1.5 inline-block">
                      setup_windows.bat
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="w-6 h-6 rounded-full bg-pink-500/20 text-pink-400 font-bold flex items-center justify-center shrink-0 border border-pink-500/30">2</div>
                  <div>
                    <h3 className="font-bold text-white text-sm">Instalasi Manual (Linux / macOS / Windows)</h3>
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-slate-300 mt-1.5 space-y-1">
                      <div>python -m venv venv</div>
                      <div>source venv/bin/activate  <span className="text-slate-500"># atau venv\Scripts\activate di Windows</span></div>
                      <div>pip install -r requirements.txt</div>
                      <div>cp .env.example .env</div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="w-6 h-6 rounded-full bg-pink-500/20 text-pink-400 font-bold flex items-center justify-center shrink-0 border border-pink-500/30">3</div>
                  <div>
                    <h3 className="font-bold text-white text-sm">Diagnosis Kesiapan</h3>
                    <p className="text-slate-400 mt-1">Jalankan perintah berikut untuk memastikan Python, FFmpeg, dan Groq API Key terkonfigurasi:</p>
                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono text-emerald-300 mt-1.5 inline-block">
                      python main.py --check
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="w-6 h-6 rounded-full bg-pink-500/20 text-pink-400 font-bold flex items-center justify-center shrink-0 border border-pink-500/30">4</div>
                  <div>
                    <h3 className="font-bold text-white text-sm">Mulai Memotong Video</h3>
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-slate-300 mt-1.5 space-y-1">
                      <div className="text-pink-400"># Dari file lokal:</div>
                      <div>python main.py --input &quot;podcast.mp4&quot; --niche edukasi --num-clips 3</div>
                      <div className="text-cyan-400 pt-2"># Dari link YouTube:</div>
                      <div>python main.py --url &quot;https://youtu.be/xxxx&quot; --niche bisnis</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-wrap items-center justify-between gap-2">
          <span>TikTok Clipper © 2026 • AI Short-Form Video Automation</span>
          <span className="font-mono text-[11px] text-slate-400">FFmpeg • Groq Whisper • Groq LLM • Typer</span>
        </div>
      </footer>
    </div>
  );
}
