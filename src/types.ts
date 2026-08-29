export type PortraitCropMode = "speaker" | "split" | "auto" | "crop" | "pad" | "off";

export type SourceInputType = "direct" | "upload" | "url" | "sample";

export type ContentNiche =
  | "auto"
  | "bisnis"
  | "edukasi"
  | "motivasi"
  | "teknologi"
  | "komedi"
  | "kuliner"
  | "kesehatan"
  | "umum";

export interface ClipItem {
  index: number;
  title: string;
  slug: string;
  start_time: number;
  end_time: number;
  duration: number;
  score: number;
  hook: string;
  caption: string;
  hashtags: string[];
  cta: string;
  reason: string;
  loop_suggestion?: string;
  transcript_text?: string;
  output_video_path?: string;
  output_srt_path?: string;
  video_filename?: string;
  srt_filename?: string;
  render_success?: boolean;
}

export interface JobLog {
  timestamp: number;
  message: string;
  stage: string;
}

export interface JobData {
  id: string;
  status: "pending" | "running" | "completed" | "error";
  progress: number;
  stage: string;
  message: string;
  sourceType: string;
  sourceLabel: string;
  niche: string;
  vertical: PortraitCropMode;
  subtitles: boolean;
  numClips: number;
  startTime: number;
  endTime?: number;
  logs: JobLog[];
  probeData?: {
    duration: number;
    resolution: string;
    aspect_ratio: string;
    is_landscape: boolean;
    fps: number;
  };
  transcriptData?: {
    text_preview: string;
    total_segments: number;
    language: string;
  };
  analysisData?: {
    clips_found: number;
    titles: string[];
  };
  clips?: ClipItem[];
  error?: string;
}

export interface SystemStatus {
  hasGroqKey: boolean;
  hasGeminiKey: boolean;
  defaultNiche: string;
  opencvEnabled: boolean;
  speakerTrackingSupported: boolean;
  version: string;
  status: string;
}
