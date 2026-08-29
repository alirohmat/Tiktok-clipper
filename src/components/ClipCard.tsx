import React, { useState, useRef } from "react";
import {
  Play,
  Pause,
  Download,
  Copy,
  Check,
  Flame,
  FileText,
  Volume2,
  VolumeX,
  Maximize,
  RotateCcw,
  Sparkles,
  Bookmark,
} from "lucide-react";
import { ClipItem } from "../types";

interface ClipCardProps {
  clip: ClipItem;
  jobId: string;
}

export const ClipCard: React.FC<ClipCardProps> = ({ clip, jobId }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [copiedCaption, setCopiedCaption] = useState(false);
  const [copiedTags, setCopiedTags] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const videoUrl = clip.video_filename
    ? `/api/media/${jobId}/${clip.video_filename}`
    : null;
  const srtUrl = clip.srt_filename
    ? `/api/media/${jobId}/${clip.srt_filename}`
    : null;

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleFullscreen = () => {
    if (!videoRef.current) return;
    if (videoRef.current.requestFullscreen) {
      videoRef.current.requestFullscreen();
    }
  };

  const handleCopyCaption = () => {
    navigator.clipboard.writeText(clip.caption);
    setCopiedCaption(true);
    setTimeout(() => setCopiedCaption(false), 2000);
  };

  const handleCopyTags = () => {
    const formatted = clip.hashtags.map((t) => (t.startsWith("#") ? t : `#${t}`)).join(" ");
    navigator.clipboard.writeText(formatted);
    setCopiedTags(true);
    setTimeout(() => setCopiedTags(false), 2000);
  };

  return (
    <div
      id={`clip-card-${clip.index}`}
      className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl flex flex-col md:flex-row gap-5"
    >
      {/* 9:16 Vertical Video Player Container */}
      <div className="w-full md:w-56 shrink-0 flex flex-col items-center">
        <div className="w-full max-w-[240px] aspect-[9/16] bg-slate-950 rounded-2xl border-2 border-slate-800 relative overflow-hidden shadow-2xl flex items-center justify-center group">
          {videoUrl ? (
            <video
              ref={videoRef}
              src={videoUrl}
              loop
              playsInline
              className="w-full h-full object-cover"
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />
          ) : (
            <div className="p-4 text-center text-slate-500 text-xs">
              <FilmIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <span>Video belum dirender</span>
            </div>
          )}

          {/* Floating Top Badge */}
          <div className="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between pointer-events-none z-10">
            <span className="bg-black/60 backdrop-blur-sm px-2 py-0.5 rounded-md text-[10px] font-bold text-white">
              Klip #{clip.index}
            </span>
            <span className="bg-pink-500/90 px-2 py-0.5 rounded-md text-[10px] font-bold text-white flex items-center gap-1 shadow">
              <Flame className="w-3 h-3" />
              {clip.score}/100
            </span>
          </div>

          {/* Center Play Button Overlay */}
          {videoUrl && !isPlaying && (
            <button
              onClick={togglePlay}
              className="absolute inset-0 m-auto w-12 h-12 rounded-full bg-pink-500/90 hover:bg-pink-500 text-white flex items-center justify-center shadow-lg transition-transform hover:scale-110 z-10"
              aria-label="Putar Video"
            >
              <Play className="w-5 h-5 translate-x-0.5" />
            </button>
          )}

          {/* Video Bottom Overlay Controls */}
          {videoUrl && (
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-2 flex items-center justify-between text-white opacity-0 group-hover:opacity-100 transition-opacity z-10">
              <button
                onClick={togglePlay}
                className="p-1 rounded hover:bg-white/20"
                title={isPlaying ? "Pause" : "Play"}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>

              <div className="flex items-center gap-1">
                <button
                  onClick={toggleMute}
                  className="p-1 rounded hover:bg-white/20"
                  title={isMuted ? "Unmute" : "Mute"}
                >
                  {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </button>
                <button
                  onClick={handleFullscreen}
                  className="p-1 rounded hover:bg-white/20"
                  title="Fullscreen"
                >
                  <Maximize className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Download Action Buttons under video */}
        <div className="w-full max-w-[240px] flex items-center gap-2 mt-3">
          {videoUrl && (
            <a
              href={videoUrl}
              download={`${clip.slug || "clip"}.mp4`}
              className="flex-1 py-1.5 px-2 bg-gradient-to-r from-pink-500 to-rose-600 hover:from-pink-600 hover:to-rose-700 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 shadow-sm transition-all text-center"
            >
              <Download className="w-3.5 h-3.5" />
              Unduh MP4
            </a>
          )}
          {srtUrl && (
            <a
              href={srtUrl}
              download={`${clip.slug || "clip"}.srt`}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs border border-slate-700 flex items-center justify-center"
              title="Unduh Subtitle SRT"
            >
              <FileText className="w-4 h-4" />
            </a>
          )}
        </div>
      </div>

      {/* Metadata & TikTok 2026 Strategy Breakdown */}
      <div className="flex-1 space-y-3.5 text-xs">
        <div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-sm font-bold text-white">{clip.title}</h4>
            <span className="text-[11px] font-mono text-slate-400">
              Durasi: {clip.duration}s ({Math.floor(clip.start_time / 60)}:
              {String(Math.floor(clip.start_time % 60)).padStart(2, "0")} -{" "}
              {Math.floor(clip.end_time / 60)}:
              {String(Math.floor(clip.end_time % 60)).padStart(2, "0")})
            </span>
          </div>
        </div>

        {/* Hook 3 Detik */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-yellow-400 uppercase tracking-wider flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              Hook 3 Detik Pertama (Stop-Scroll):
            </span>
          </div>
          <blockquote className="border-l-2 border-yellow-400 pl-3 italic text-slate-200 bg-yellow-950/20 py-1.5 rounded-r-lg">
            &ldquo;{clip.hook}&rdquo;
          </blockquote>
        </div>

        {/* Caption SEO TikTok */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-cyan-400 uppercase tracking-wider">
              Caption SEO TikTok (Algoritma 2026):
            </span>
            <button
              onClick={handleCopyCaption}
              className="flex items-center gap-1 text-[11px] text-cyan-300 hover:text-cyan-200 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800/40"
            >
              {copiedCaption ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              {copiedCaption ? "Tersalin!" : "Salin Caption"}
            </button>
          </div>
          <p className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-slate-200 leading-relaxed font-sans">
            {clip.caption}
          </p>
        </div>

        {/* Hashtags & CTA */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider">
                Hashtags Niche Terfokus:
              </span>
              <button
                onClick={handleCopyTags}
                className="text-[10px] text-emerald-400 hover:text-emerald-300"
              >
                {copiedTags ? "Tersalin!" : "Salin Semua"}
              </button>
            </div>
            <div className="flex flex-wrap gap-1">
              {clip.hashtags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px] font-mono"
                >
                  #{tag.replace(/^#/, "")}
                </span>
              ))}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] font-semibold text-pink-400 uppercase tracking-wider">
              Call To Action (CTA):
            </span>
            <div className="p-2 rounded-xl bg-pink-500/10 border border-pink-500/20 text-pink-200 text-[11px]">
              {clip.cta || "Save & Share video ini untuk dipelajari kembali!"}
            </div>
          </div>
        </div>

        {/* Loop Strategy */}
        {clip.loop_suggestion && (
          <div className="bg-purple-950/20 border border-purple-900/30 p-2.5 rounded-xl text-[11px] text-purple-200">
            <span className="font-semibold text-purple-300 mr-1">🔄 Seamless Loop Strategy:</span>
            {clip.loop_suggestion}
          </div>
        )}
      </div>
    </div>
  );
};

function FilmIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <path d="M7 3v18" />
      <path d="M3 7.5h4" />
      <path d="M3 12h18" />
      <path d="M3 16.5h4" />
      <path d="M17 3v18" />
      <path d="M17 7.5h4" />
      <path d="M17 16.5h4" />
    </svg>
  );
}
