import React, { useState } from "react";
import {
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Terminal,
  ChevronDown,
  ChevronUp,
  Cpu,
  Sparkles,
  Film,
  FileText,
} from "lucide-react";
import { JobData } from "../types";

interface JobProgressProps {
  job: JobData;
}

export const JobProgress: React.FC<JobProgressProps> = ({ job }) => {
  const [showLogs, setShowLogs] = useState(false);

  const steps = [
    { id: 1, name: "Inisialisasi", icon: Cpu, threshold: 5 },
    { id: 2, name: "Analisis Media", icon: Film, threshold: 25 },
    { id: 3, name: "Transkripsi AI", icon: FileText, threshold: 50 },
    { id: 4, name: "Seleksi Hook 2026", icon: Sparkles, threshold: 65 },
    { id: 5, name: "Smart Crop & Render", icon: Film, threshold: 75 },
    { id: 6, name: "Selesai", icon: CheckCircle2, threshold: 100 },
  ];

  const isCompleted = job.status === "completed";
  const isError = job.status === "error";

  return (
    <div
      id="job-progress-card"
      className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-4"
    >
      {/* Top Header Status */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          {isCompleted ? (
            <div className="w-8 h-8 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          ) : isError ? (
            <div className="w-8 h-8 rounded-xl bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <AlertCircle className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-xl bg-pink-500/20 border border-pink-500/30 flex items-center justify-center text-pink-400">
              <Loader2 className="w-5 h-5 animate-spin" />
            </div>
          )}

          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white">
                {isCompleted
                  ? "Proses Pemotongan Selesai!"
                  : isError
                  ? "Terjadi Kesalahan"
                  : `Sedang Memproses: ${job.stage}`}
              </h3>
              <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {job.id}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{job.message}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-xs font-bold text-pink-400 font-mono">
              {Math.round(job.progress)}%
            </span>
            <span className="text-[11px] text-slate-500 block">
              Mode: {job.vertical}
            </span>
          </div>
        </div>
      </div>

      {/* Animated Progress Bar */}
      <div className="space-y-1.5">
        <div className="w-full h-2.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800 p-0.5">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isError
                ? "bg-rose-500"
                : isCompleted
                ? "bg-gradient-to-r from-emerald-500 to-teal-400"
                : "bg-gradient-to-r from-pink-500 via-rose-500 to-cyan-400 animate-pulse"
            }`}
            style={{ width: `${Math.max(5, Math.min(100, job.progress))}%` }}
          />
        </div>
      </div>

      {/* Step Pills */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 pt-1">
        {steps.map((step) => {
          const StepIcon = step.icon;
          const isPassed = job.progress >= step.threshold || isCompleted;
          const isCurrent = !isCompleted && !isError && job.progress >= step.threshold - 15 && job.progress < step.threshold + 10;
          return (
            <div
              key={step.id}
              className={`p-2 rounded-xl border text-center transition-all ${
                isPassed
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                  : isCurrent
                  ? "bg-pink-500/15 border-pink-500 text-pink-300 animate-pulse"
                  : "bg-slate-950/60 border-slate-800 text-slate-500"
              }`}
            >
              <div className="flex items-center justify-center gap-1 text-[11px] font-medium">
                <StepIcon className="w-3.5 h-3.5" />
                <span className="truncate">{step.name}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Collapsible Terminal Logs */}
      <div className="border-t border-slate-800 pt-3">
        <button
          type="button"
          onClick={() => setShowLogs(!showLogs)}
          className="w-full flex items-center justify-between text-xs text-slate-400 hover:text-slate-200 py-1"
        >
          <span className="flex items-center gap-1.5 font-mono">
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            Live Execution Logs ({job.logs?.length || 0} baris)
          </span>
          {showLogs ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showLogs && (
          <div className="mt-2 bg-slate-950 rounded-xl p-3 border border-slate-800/80 font-mono text-[11px] text-slate-300 max-h-48 overflow-y-auto space-y-1 leading-relaxed">
            {job.logs?.map((log, idx) => (
              <div key={idx} className="flex gap-2">
                <span className="text-slate-600 shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className="text-pink-400 shrink-0">[{log.stage}]</span>
                <span className="text-slate-300 break-all">{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
