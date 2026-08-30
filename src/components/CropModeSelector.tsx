import React from "react";
import { UserCheck, Users, Sparkles, Crop, Maximize2, Monitor } from "lucide-react";
import { PortraitCropMode } from "../types";

interface CropModeSelectorProps {
  value: PortraitCropMode;
  onChange: (mode: PortraitCropMode) => void;
}

export const CropModeSelector: React.FC<CropModeSelectorProps> = ({ value, onChange }) => {
  const modes: {
    id: PortraitCropMode;
    label: string;
    badge: string;
    badgeColor: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
  }[] = [
    {
      id: "auto",
      label: "Smart Auto-Detect",
      badge: "Adaptif 2026",
      badgeColor: "bg-purple-500/20 text-purple-300 border-purple-500/30",
      description: "AI mendeteksi tipe video: Otomatis kunci pembicara utama jika Konferensi Pers/Monolog, atau Split Layar Atas-Bawah jika Podcast 2 orang.",
      icon: Sparkles,
    },
    {
      id: "speaker",
      label: "Smart Active Speaker",
      badge: "Konferensi Pers / Monolog",
      badgeColor: "bg-pink-500/20 text-pink-300 border-pink-500/30",
      description: "OpenCV menganalisis gerak mulut & posisi wajah untuk mengunci 1 pembicara aktif di tengah keramaian/panggung.",
      icon: UserCheck,
    },
    {
      id: "split",
      label: "Dual Podcast Split",
      badge: "Wawancara / Podcast",
      badgeColor: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
      description: "Menumpuk 2 pembicara (Host di atas & Tamu di bawah) dalam format vertikal 9:16 1080x1920.",
      icon: Users,
    },
    {
      id: "crop",
      label: "Center Crop",
      badge: "Klasik",
      badgeColor: "bg-slate-700 text-slate-300 border-slate-600",
      description: "Memotong tepat di tengah-tengah video 1080x1920 tanpa deteksi wajah.",
      icon: Crop,
    },
    {
      id: "pad",
      label: "Pillarbox / Pad",
      badge: "No Crop",
      badgeColor: "bg-slate-700 text-slate-300 border-slate-600",
      description: "Menambahkan bilah hitam di atas dan bawah tanpa memotong visual video asli.",
      icon: Maximize2,
    },
    {
      id: "off",
      label: "Rasio Asli",
      badge: "Original",
      badgeColor: "bg-slate-700 text-slate-300 border-slate-600",
      description: "Mempertahankan dimensi dan aspect ratio asli video sumber.",
      icon: Monitor,
    },
  ];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
          <UserCheck className="w-4 h-4 text-pink-400" />
          Mode Potret Vertikal 9:16 (Smart Cropping)
        </label>
        <span className="text-[11px] text-pink-400 font-medium">Auto-Tracking Aktif</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {modes.map((m) => {
          const Icon = m.icon;
          const isSelected = value === m.id;
          return (
            <button
              key={m.id}
              type="button"
              onClick={() => onChange(m.id)}
              className={`p-3 rounded-xl border text-left transition-all relative flex flex-col justify-between ${
                isSelected
                  ? "bg-pink-500/10 border-pink-500 ring-1 ring-pink-500/50 shadow-md shadow-pink-500/10"
                  : "bg-slate-950/80 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60 text-slate-300"
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-1 mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <div
                      className={`w-6 h-6 rounded-lg flex items-center justify-center ${
                        isSelected ? "bg-pink-500 text-white" : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-xs font-semibold text-white">{m.label}</span>
                  </div>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full border font-medium whitespace-nowrap ${m.badgeColor}`}>
                    {m.badge}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-snug">{m.description}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
