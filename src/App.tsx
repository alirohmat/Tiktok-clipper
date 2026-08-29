/**
 * TikTok Clipper Web Studio 2026
 * Generator Klip Vertikal Pendek Otomatis dengan AI & Active Speaker Tracking
 */

import React, { useState, useEffect, useRef } from "react";
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
  FolderOpen,
  UploadCloud,
  Film,
  UserCheck,
  History,
  Zap,
  Loader2,
} from "lucide-react";
import {
  PortraitCropMode,
  SourceInputType,
  ContentNiche,
  JobData,
  SystemStatus,
} from "./types";
import { CropModeSelector } from "./components/CropModeSelector";
import { JobProgress } from "./components/JobProgress";
import { ClipCard } from "./components/ClipCard";

export default function App() {
  const [activeTab, setActiveTab] = useState<
    "studio" | "history" | "strategy" | "cli" | "env" | "guide"
  >("studio");

  // Form State
  const [sourceType, setSourceType] = useState<SourceInputType>("sample");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [urlVal, setUrlVal] = useState("https://www.youtube.com/watch?v=sample-podcast");
  const [niche, setNiche] = useState<ContentNiche>("bisnis");
  const [numClips, setNumClips] = useState(2);
  const [minDur, setMinDur] = useState(15);
  const [maxDur, setMaxDur] = useState(60);
  const [subtitles, setSubtitles] = useState(true);
  const [vertical, setVertical] = useState<PortraitCropMode>("speaker");
  const [groqApiKey, setGroqApiKey] = useState("");

  // Generation & Active Job State
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [currentJob, setCurrentJob] = useState<JobData | null>(null);
  const [jobsHistory, setJobsHistory] = useState<JobData[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedCmd, setCopiedCmd] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Safe helper to fetch and parse JSON without crashing on HTML error pages
  const safeFetchJson = async <T = any>(
    url: string,
    options?: RequestInit
  ): Promise<{ ok: boolean; status: number; data?: T; error?: string }> => {
    try {
      const res = await fetch(url, options);
      const contentType = res.headers.get("content-type") || "";

      let data: any = null;
      if (contentType.includes("application/json")) {
        data = await res.json().catch(() => null);
      } else {
        const text = await res.text().catch(() => "");
        try {
          data = JSON.parse(text);
        } catch {
          // If response is not valid JSON (e.g., HTML error page from proxy)
          if (!res.ok) {
            return {
              ok: false,
              status: res.status,
              error:
                text.length > 0 && text.length < 150 && !text.includes("<")
                  ? text
                  : `Server mengembalikan status ${res.status} (${res.statusText || "Gagal berkomunikasi dengan server"}).`,
            };
          }
        }
      }

      if (!res.ok) {
        const errMsg = data?.error || data?.message || `HTTP ${res.status}: ${res.statusText || "Terjadi kesalahan"}`;
        return { ok: false, status: res.status, data, error: errMsg };
      }

      return { ok: true, status: res.status, data };
    } catch (e: any) {
      return {
        ok: false,
        status: 0,
        error: e?.message || "Gagal menghubungi server.",
      };
    }
  };

  // Fetch System Status & Existing Jobs on mount
  useEffect(() => {
    fetchSystemStatus();
    fetchJobsList();
  }, []);

  // Poll current job status
  useEffect(() => {
    if (!activeJobId) return;

    const checkJob = async () => {
      try {
        const res = await safeFetchJson<JobData>(`/api/jobs/${activeJobId}`);
        if (!res.ok || !res.data) return;
        const data = res.data;
        setCurrentJob(data);

        if (data.status === "completed" || data.status === "error") {
          setIsGenerating(false);
          fetchJobsList(); // Refresh history
          if (pollingRef.current) clearInterval(pollingRef.current);
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
    };

    checkJob();
    pollingRef.current = setInterval(checkJob, 1500);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [activeJobId]);

  const fetchSystemStatus = async () => {
    try {
      const res = await safeFetchJson<SystemStatus>("/api/system-status");
      if (res.ok && res.data) {
        setSystemStatus(res.data);
      }
    } catch (e) {
      console.warn("Could not fetch system status:", e);
    }
  };

  const fetchJobsList = async () => {
    try {
      const res = await safeFetchJson<{ jobs: JobData[] }>("/api/jobs");
      if (res.ok && res.data?.jobs) {
        setJobsHistory(res.data.jobs);
        // If there's an existing completed job and no active job selected yet, show the latest one
        if (!activeJobId && res.data.jobs.length > 0) {
          const latest = res.data.jobs[0];
          setActiveJobId(latest.id);
          setCurrentJob(latest);
        }
      }
    } catch (e) {
      console.warn("Could not fetch jobs history:", e);
    }
  };

  const handleStartGeneration = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsGenerating(true);

    try {
      const formData = new FormData();
      formData.append("sourceType", sourceType);
      formData.append("niche", niche);
      formData.append("numClips", String(numClips));
      formData.append("minDuration", String(minDur));
      formData.append("maxDuration", String(maxDur));
      formData.append("vertical", vertical);
      formData.append("subtitles", String(subtitles));
      if (groqApiKey.trim()) {
        formData.append("groqApiKey", groqApiKey.trim());
      }

      if (sourceType === "upload") {
        if (!selectedFile) {
          setErrorMessage("Silakan pilih file video lokal terlebih dahulu.");
          setIsGenerating(false);
          return;
        }
        formData.append("videoFile", selectedFile);
      } else if (sourceType === "url") {
        if (!urlVal.trim()) {
          setErrorMessage("Silakan masukkan tautan URL video.");
          setIsGenerating(false);
          return;
        }
        formData.append("url", urlVal.trim());
      }

      const res = await safeFetchJson<{ success: boolean; jobId: string; error?: string }>("/api/generate", {
        method: "POST",
        body: formData,
      });

      if (!res.ok || !res.data?.success) {
        throw new Error(res.error || res.data?.error || "Gagal memulai pembuatan video.");
      }

      setActiveJobId(res.data.jobId);
      // Scroll smoothly to progress card
      setTimeout(() => {
        const el = document.getElementById("job-progress-card");
        if (el) el.scrollIntoView({ behavior: "smooth" });
      }, 300);
    } catch (err: any) {
      setErrorMessage(err.message || "Terjadi kesalahan saat memulai proses.");
      setIsGenerating(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(true);
    setTimeout(() => setCopiedCmd(false), 2000);
  };

  const generateCLICommand = () => {
    const parts = ["python main.py"];
    if (sourceType === "upload") {
      parts.push(`--input "${selectedFile?.name || "video.mp4"}"`);
    } else if (sourceType === "url") {
      parts.push(`--url "${urlVal || "https://..."}"`);
    } else {
      parts.push(`--input "sample_podcast.mp4"`);
    }
    if (niche !== "umum") parts.push(`--niche ${niche}`);
    if (numClips !== 3) parts.push(`--num-clips ${numClips}`);
    if (minDur !== 15) parts.push(`--min-duration ${minDur}`);
    if (maxDur !== 60) parts.push(`--max-duration ${maxDur}`);
    if (!subtitles) parts.push("--no-subtitles");
    if (vertical !== "speaker") parts.push(`--vertical ${vertical}`);
    return parts.join(" ");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-pink-500 selection:text-white">
      {/* Header Utama */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 via-rose-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-pink-500/20">
              <Video className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-white">TikTok Clipper</h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-pink-500/20 text-pink-300 border border-pink-500/30 font-medium">
                  Smart Speaker Tracking
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-medium hidden sm:inline">
                  Strategi TikTok 2026
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Otomasi Pemotongan Klip Vertikal 9:16 dengan AI & Pelacakan Pembicara Aktif
              </p>
            </div>
          </div>

          {/* Navigasi Tab */}
          <nav className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              id="tab-studio"
              onClick={() => setActiveTab("studio")}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all font-medium ${
                activeTab === "studio"
                  ? "bg-gradient-to-r from-pink-500 to-rose-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              Studio Generator
            </button>
            <button
              id="tab-history"
              onClick={() => setActiveTab("history")}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all font-medium ${
                activeTab === "history"
                  ? "bg-gradient-to-r from-pink-500 to-rose-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <History className="w-3.5 h-3.5" />
              Riwayat Klip ({jobsHistory.length})
            </button>
            <button
              id="tab-strategy"
              onClick={() => setActiveTab("strategy")}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all font-medium ${
                activeTab === "strategy"
                  ? "bg-gradient-to-r from-pink-500 to-rose-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Flame className="w-3.5 h-3.5" />
              Strategi 2026
            </button>
            <button
              id="tab-cli"
              onClick={() => setActiveTab("cli")}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all font-medium ${
                activeTab === "cli"
                  ? "bg-gradient-to-r from-pink-500 to-rose-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              CLI Terminal
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">
        {/* TAB 1: STUDIO GENERATOR */}
        {activeTab === "studio" && (
          <div className="space-y-6">
            {/* Generator Form Card */}
            <form onSubmit={handleStartGeneration} className="space-y-6">
              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 sm:p-6 shadow-xl space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-pink-500/20 text-pink-400 flex items-center justify-center">
                      <Sliders className="w-4 h-4" />
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                        Generator Video Klip TikTok
                      </h2>
                      <p className="text-xs text-slate-400">
                        Pilih sumber video, atur mode cropping wajah pembicara, dan buat klip instan.
                      </p>
                    </div>
                  </div>

                  {systemStatus && (
                    <div className="flex items-center gap-2 text-[11px] bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                      <span className="text-slate-300">OpenCV Face Tracker:</span>
                      <span className="text-emerald-400 font-semibold">Aktif</span>
                    </div>
                  )}
                </div>

                {/* 1. Sumber Input Video */}
                <div className="space-y-3">
                  <label className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                    <Film className="w-4 h-4 text-cyan-400" />
                    1. Sumber Video Sumber
                  </label>

                  {/* Tabs Pemilih Sumber */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    <button
                      id="source-btn-sample"
                      type="button"
                      onClick={() => setSourceType("sample")}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        sourceType === "sample"
                          ? "bg-pink-500/15 border-pink-500 text-pink-300 ring-1 ring-pink-500/30"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center gap-2 font-semibold text-xs text-white mb-1">
                        <Sparkles className="w-4 h-4 text-pink-400" />
                        Video Sampel Podcast (1-Click)
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Uji coba instan dengan podcast 2 pembicara (Host & Guest) tanpa perlu upload.
                      </p>
                    </button>

                    <button
                      id="source-btn-upload"
                      type="button"
                      onClick={() => setSourceType("upload")}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        sourceType === "upload"
                          ? "bg-cyan-500/15 border-cyan-500 text-cyan-300 ring-1 ring-cyan-500/30"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center gap-2 font-semibold text-xs text-white mb-1">
                        <UploadCloud className="w-4 h-4 text-cyan-400" />
                        Unggah File Lokal (MP4/MOV)
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Pilih video dari komputer/perangkat Anda untuk dipotong.
                      </p>
                    </button>

                    <button
                      id="source-btn-url"
                      type="button"
                      onClick={() => setSourceType("url")}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        sourceType === "url"
                          ? "bg-purple-500/15 border-purple-500 text-purple-300 ring-1 ring-purple-500/30"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center gap-2 font-semibold text-xs text-white mb-1">
                        <ExternalLink className="w-4 h-4 text-purple-400" />
                        Tautan Video (URL / YouTube)
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Unduh otomatis dengan yt-dlp dari YouTube, TikTok, dll.
                      </p>
                    </button>
                  </div>

                  {/* Input Source Body */}
                  {sourceType === "upload" && (
                    <div className="mt-2">
                      <div
                        onClick={() => fileInputRef.current?.click()}
                        className="border-2 border-dashed border-slate-700 hover:border-cyan-500 rounded-2xl p-6 text-center cursor-pointer bg-slate-950/60 transition-colors"
                      >
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept="video/*"
                          onChange={handleFileChange}
                          className="hidden"
                        />
                        <UploadCloud className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
                        {selectedFile ? (
                          <div className="space-y-1">
                            <span className="text-xs font-semibold text-white block">
                              {selectedFile.name}
                            </span>
                            <span className="text-[11px] text-slate-400 font-mono">
                              Ukuran: {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                            </span>
                          </div>
                        ) : (
                          <div className="space-y-1">
                            <span className="text-xs font-semibold text-slate-300 block">
                              Klik untuk memilih file video lokal atau drag & drop di sini
                            </span>
                            <span className="text-[11px] text-slate-500">
                              Format: MP4, MOV, MKV, WebM, AVI (Maksimal 2GB)
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {sourceType === "url" && (
                    <div className="mt-2 space-y-2">
                      <input
                        type="text"
                        value={urlVal}
                        onChange={(e) => setUrlVal(e.target.value)}
                        placeholder="https://www.youtube.com/watch?v=..."
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                      />
                      <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-xl p-2.5 text-[11px] text-amber-300">
                        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                        <div>
                          <p className="font-semibold text-amber-200">Tips Tautan YouTube:</p>
                          <p className="text-amber-300/90 leading-relaxed">
                            Jika YouTube memblokir unduhan server dengan pesan <em>"Sign in to confirm you're not a bot"</em>, gunakan tab <strong>"Unggah File Lokal"</strong> untuk memproses file MP4 secara langsung tanpa batasan bot YouTube.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {sourceType === "sample" && (
                    <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800 text-xs text-slate-300 flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-pink-500/20 flex items-center justify-center text-pink-400 font-bold">
                          🎬
                        </div>
                        <div>
                          <span className="font-semibold text-white block">
                            Podcast Simulasi Bisnis & Strategi 2026
                          </span>
                          <span className="text-[11px] text-slate-400">
                            Durasi 35 detik, 2 pembicara berhadapan dengan dialog terstruktur.
                          </span>
                        </div>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-pink-500/20 text-pink-300 border border-pink-500/30">
                        Siap Uji Coba Instan
                      </span>
                    </div>
                  )}
                </div>

                {/* 2. Mode Cropping Speaker Tracking */}
                <CropModeSelector value={vertical} onChange={setVertical} />

                {/* 3. Parameter Niche & Pemotongan */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">Niche Konten</label>
                    <select
                      value={niche}
                      onChange={(e) => setNiche(e.target.value as ContentNiche)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-pink-500"
                    >
                      <option value="bisnis">Bisnis & Finansial</option>
                      <option value="edukasi">Edukasi & Tutorial</option>
                      <option value="motivasi">Motivasi & Mindset</option>
                      <option value="teknologi">Teknologi & AI</option>
                      <option value="komedi">Komedi & Hiburan</option>
                      <option value="kuliner">Kuliner & Resep</option>
                      <option value="kesehatan">Kesehatan & Fitness</option>
                      <option value="umum">Umum</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300 flex justify-between">
                      <span>Jumlah Klip</span>
                      <span className="text-pink-400 font-mono font-bold">{numClips} klip</span>
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="6"
                      value={numClips}
                      onChange={(e) => setNumClips(parseInt(e.target.value))}
                      className="w-full accent-pink-500 h-2 bg-slate-800 rounded-lg cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                      <span>1</span>
                      <span>2 (Rekomendasi)</span>
                      <span>6</span>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300 flex justify-between">
                      <span>Rentang Durasi</span>
                      <span className="text-cyan-400 font-mono font-bold">
                        {minDur}s - {maxDur}s
                      </span>
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        min="5"
                        max="60"
                        value={minDur}
                        onChange={(e) => setMinDur(parseInt(e.target.value) || 15)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-100 font-mono text-center"
                        placeholder="Min (s)"
                      />
                      <input
                        type="number"
                        min="15"
                        max="180"
                        value={maxDur}
                        onChange={(e) => setMaxDur(parseInt(e.target.value) || 60)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-100 font-mono text-center"
                        placeholder="Max (s)"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">Subtitle Hardsub</label>
                    <button
                      type="button"
                      onClick={() => setSubtitles(!subtitles)}
                      className={`w-full py-2 px-3 rounded-xl border text-xs font-medium flex items-center justify-between transition-all ${
                        subtitles
                          ? "bg-pink-500/15 border-pink-500 text-pink-300"
                          : "bg-slate-950 border-slate-800 text-slate-500"
                      }`}
                    >
                      <span>{subtitles ? "Teks Otomatis Aktif" : "Hanya Video"}</span>
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${
                          subtitles ? "bg-pink-400" : "bg-slate-600"
                        }`}
                      />
                    </button>
                  </div>
                </div>

                {/* Error Banner */}
                {errorMessage && (
                  <div className="p-3 bg-rose-500/15 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{errorMessage}</span>
                  </div>
                )}

                {/* Tombol Generate Utama */}
                <div className="pt-2">
                  <button
                    id="btn-generate-video"
                    type="submit"
                    disabled={isGenerating}
                    className="w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-pink-500 via-rose-500 to-cyan-500 hover:from-pink-600 hover:via-rose-600 hover:to-cyan-600 disabled:opacity-50 text-white font-bold text-sm tracking-wide shadow-xl shadow-pink-500/25 flex items-center justify-center gap-2.5 transition-all transform hover:scale-[1.005] active:scale-[0.995]"
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>Sedang Memproses Video & Pelacakan Pembicara...</span>
                      </>
                    ) : (
                      <>
                        <Zap className="w-5 h-5 text-yellow-300 fill-yellow-300" />
                        <span>⚡ GENERATE VIDEO KLIP TIKTOK SEKARANG</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>

            {/* Live Progress Card */}
            {currentJob && <JobProgress job={currentJob} />}

            {/* Generated Clips Gallery */}
            {currentJob && currentJob.clips && currentJob.clips.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Flame className="w-5 h-5 text-pink-500" />
                    <h3 className="text-base font-bold text-white">
                      Hasil Klip Video ({currentJob.clips.length} Klip Siap Diunduh)
                    </h3>
                  </div>
                  <span className="text-xs text-slate-400">
                    Format Vertikal 9:16 (1080x1920) dengan Loudnorm EBU R128
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-5">
                  {currentJob.clips.map((clip) => (
                    <ClipCard key={clip.index} clip={clip} jobId={currentJob.id} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: RIWAYAT KLIP */}
        {activeTab === "history" && (
          <div className="space-y-4">
            <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white">Riwayat Pemotongan Video</h2>
                <p className="text-xs text-slate-400">
                  Daftar seluruh proses generate video yang telah dilakukan sebelumnya.
                </p>
              </div>
              <button
                onClick={fetchJobsList}
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Segarkan
              </button>
            </div>

            {jobsHistory.length === 0 ? (
              <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80 space-y-2">
                <Film className="w-10 h-10 text-slate-600 mx-auto" />
                <h3 className="text-sm font-bold text-slate-300">Belum Ada Riwayat Klip</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Klik tab <strong>Studio Generator</strong> untuk membuat klip pertama Anda.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {jobsHistory.map((job) => (
                  <div
                    key={job.id}
                    className="bg-slate-900/80 rounded-2xl border border-slate-800 p-4 space-y-3 hover:border-slate-700 transition-all flex flex-col justify-between"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                          {job.id}
                        </span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                            job.status === "completed"
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : job.status === "error"
                              ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                              : "bg-pink-500/20 text-pink-300 border border-pink-500/30"
                          }`}
                        >
                          {job.status}
                        </span>
                      </div>

                      <h4 className="text-xs font-bold text-white line-clamp-1">{job.sourceLabel}</h4>

                      <div className="text-[11px] text-slate-400 space-y-1">
                        <div>Niche: <strong className="text-slate-200 capitalize">{job.niche}</strong></div>
                        <div>Mode: <strong className="text-slate-200 capitalize">{job.vertical}</strong></div>
                        <div>Jumlah Klip: <strong className="text-pink-400">{job.clips?.length || job.numClips} klip</strong></div>
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        setActiveJobId(job.id);
                        setCurrentJob(job);
                        setActiveTab("studio");
                      }}
                      className="w-full py-2 bg-pink-500/15 hover:bg-pink-500/25 text-pink-300 rounded-xl text-xs font-semibold border border-pink-500/30 flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Play className="w-3.5 h-3.5" />
                      Buka & Putar Klip
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: STRATEGI TIKTOK 2026 */}
        {activeTab === "strategy" && (
          <div className="space-y-6">
            <div className="bg-gradient-to-r from-pink-950/40 via-purple-950/40 to-slate-900 border border-pink-900/40 rounded-2xl p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-pink-500/20 border border-pink-500/30 flex items-center justify-center shrink-0">
                  <Flame className="w-6 h-6 text-pink-400" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">Prinsip Algoritma TikTok 2026 pada AI Clipper</h2>
                  <p className="text-xs text-slate-300 mt-1 max-w-3xl leading-relaxed">
                    Setiap detik video dipindai oleh AI dengan kriteria evaluasi ketat berikut untuk memastikan klip memiliki probabilitas retensi dan sebaran organik tertinggi:
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
                  Menghilangkan basa-basi intro. Klip harus dimulai dari pertanyaan tajam, fakta mengejutkan, atau paradoks yang menghentikan scroll seketika.
                </p>
              </div>

              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-xs">
                  02
                </div>
                <h3 className="text-sm font-bold text-white">Smart Active Speaker Follow</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Format vertikal 9:16 dipotong cerdas dengan deteksi wajah OpenCV sehingga subjek yang sedang berbicara selalu berada tepat di tengah layar.
                </p>
              </div>

              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 font-bold text-xs">
                  03
                </div>
                <h3 className="text-sm font-bold text-white">Save & Share Worthy</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Algoritma memprioritaskan momen edukatif, checklist, dan panduan yang mendorong penonton menekan tombol Bookmark untuk disimpan.
                </p>
              </div>

              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-xs">
                  04
                </div>
                <h3 className="text-sm font-bold text-white">SEO Caption Terindeks</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Kata kunci utama wajib muncul di 50 karakter pertama caption untuk menangkap penelusuran kata kunci TikTok Search Bar.
                </p>
              </div>

              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400 font-bold text-xs">
                  05
                </div>
                <h3 className="text-sm font-bold text-white">Hashtags Niche Spesifik</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Bebas dari hashtag sampah seperti #fyp atau #viral. Menghasilkan tag niche spesifik yang memperjelas kategorisasi klip ke audiens tertarget.
                </p>
              </div>

              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="w-8 h-8 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 font-bold text-xs">
                  06
                </div>
                <h3 className="text-sm font-bold text-white">Seamless Loop Strategy</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Kalimat akhir klip berkesinambungan menjawab kalimat awal sehingga penonton menonton video lebih dari satu kali secara natural.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: CLI TERMINAL */}
        {activeTab === "cli" && (
          <div className="space-y-6">
            <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-sm font-bold text-white">CLI Command Generator</h3>
                </div>
                <button
                  onClick={() => handleCopy(generateCLICommand())}
                  className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg bg-pink-500/20 text-pink-300 hover:bg-pink-500/30 border border-pink-500/30"
                >
                  {copiedCmd ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedCmd ? "Tersalin!" : "Salin Perintah"}
                </button>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-pink-300 break-all leading-relaxed shadow-inner">
                {generateCLICommand()}
              </div>

              <div className="text-xs text-slate-400 space-y-1">
                <p>
                  💡 <strong>Cara Eksekusi CLI:</strong> Anda dapat menjalankan perintah di atas langsung di terminal sistem dengan Python 3.11+.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-900/50 py-4 text-center text-xs text-slate-500">
        TikTok Clipper v2.0 &bull; Algoritma TikTok 2026 &bull; Active Speaker Tracking with OpenCV & FFmpeg
      </footer>
    </div>
  );
}
