import express from "express";
import path from "path";
import fs from "fs";
import { spawn } from "child_process";
import multer from "multer";
import { createServer as createViteServer } from "vite";

const app = express();
const PORT = 3000;

// Setup directories
const ROOT_DIR = process.cwd();
const CACHE_DIR = path.join(ROOT_DIR, "cache");
const UPLOADS_DIR = path.join(CACHE_DIR, "uploads");
const OUTPUT_DIR = path.join(ROOT_DIR, "output");

[CACHE_DIR, UPLOADS_DIR, OUTPUT_DIR].forEach((dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, UPLOADS_DIR);
  },
  filename: (_req, file, cb) => {
    const safeName = file.originalname.replace(/[^a-zA-Z0-9._-]/g, "_");
    const uniqueName = `${Date.now()}_${safeName}`;
    cb(null, uniqueName);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 1024 * 1024 * 1024 * 2 }, // 2GB max
});

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

interface JobLog {
  timestamp: number;
  message: string;
  stage: string;
}

interface JobState {
  id: string;
  status: "pending" | "running" | "completed" | "error";
  progress: number;
  stage: string;
  message: string;
  sourceType: string;
  sourceLabel: string;
  niche: string;
  vertical: string;
  subtitles: boolean;
  numClips: number;
  startTime: number;
  endTime?: number;
  logs: JobLog[];
  probeData?: any;
  transcriptData?: any;
  analysisData?: any;
  clips?: any[];
  error?: string;
}

const activeJobs = new Map<string, JobState>();

// Load existing runs from output directory on startup
function loadExistingJobs() {
  try {
    if (!fs.existsSync(OUTPUT_DIR)) return;
    const entries = fs.readdirSync(OUTPUT_DIR, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isDirectory()) {
        const runId = entry.name;
        const metaPath = path.join(OUTPUT_DIR, runId, "run_metadata.json");
        if (fs.existsSync(metaPath)) {
          try {
            const raw = fs.readFileSync(metaPath, "utf-8");
            const data = JSON.parse(raw);
            const clipsDir = path.join(OUTPUT_DIR, runId, "clips");
            const clips: any[] = [];
            if (Array.isArray(data.clips)) {
              for (const c of data.clips) {
                const clipObj = { ...c };
                if (c.slug) {
                  const prefix = `${String(c.index).padStart(2, "0")}-${c.slug}`;
                  clipObj.video_filename = `${prefix}.mp4`;
                  clipObj.srt_filename = `${prefix}.srt`;
                }
                clips.push(clipObj);
              }
            }

            activeJobs.set(runId, {
              id: runId,
              status: "completed",
              progress: 100,
              stage: "Selesai",
              message: "Proses telah selesai sebelumnya.",
              sourceType: data.source_input?.startsWith("http") ? "url" : "upload",
              sourceLabel: data.source_input || runId,
              niche: data.niche || "umum",
              vertical: data.vertical_mode || "speaker",
              subtitles: data.subtitles_burned !== false,
              numClips: clips.length,
              startTime: Date.now() - 3600000,
              endTime: Date.now() - 3500000,
              logs: [{ timestamp: Date.now(), stage: "Selesai", message: "Klip siap diputar." }],
              clips,
              probeData: data.probe,
            });
          } catch (e) {
            // Ignore invalid JSON in directory
          }
        }
      }
    }
  } catch (err) {
    console.error("Error loading existing jobs:", err);
  }
}

loadExistingJobs();

// API: System Status
app.get("/api/system-status", async (_req, res) => {
  const hasGroqKey = Boolean(process.env.GROQ_API_KEY && process.env.GROQ_API_KEY.trim());
  const hasGeminiKey = Boolean(process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY.trim());
  
  res.json({
    hasGroqKey,
    hasGeminiKey,
    defaultNiche: process.env.DEFAULT_NICHE || "bisnis",
    opencvEnabled: true,
    speakerTrackingSupported: true,
    version: "2.0.0-ai2026",
    status: "ready"
  });
});

// API: List All Jobs
app.get("/api/jobs", (_req, res) => {
  const list = Array.from(activeJobs.values()).sort((a, b) => b.startTime - a.startTime);
  res.json({ jobs: list });
});

// API: Get Specific Job Status
app.get("/api/jobs/:jobId", (req, res) => {
  const job = activeJobs.get(req.params.jobId);
  if (!job) {
    return res.status(404).json({ error: "Job tidak ditemukan." });
  }
  res.json(job);
});

// API: Start Video Generation
app.post("/api/generate", (req, res, next) => {
  upload.single("videoFile")(req, res, (uploadErr) => {
    if (uploadErr) {
      if (uploadErr instanceof multer.MulterError) {
        if (uploadErr.code === "LIMIT_FILE_SIZE") {
          return res.status(400).json({ error: "Ukuran file video melebihi batas maksimal (2GB)." });
        }
        return res.status(400).json({ error: `Kesalahan unggah: ${uploadErr.message}` });
      }
      return res.status(400).json({ error: uploadErr.message || "Gagal mengunggah file video." });
    }

    try {
      const {
        sourceType = "sample",
        url = "",
        niche = "bisnis",
        numClips = "3",
        minDuration = "15",
        maxDuration = "60",
        vertical = "speaker",
        subtitles = "true",
        groqApiKey = "",
        llmProvider = "",
        llmApiKey = "",
        llmBaseUrl = "",
        llmModel = "",
      } = req.body || {};

    const parsedNumClips = Math.max(1, Math.min(10, parseInt(numClips, 10) || 3));
    const parsedMinDur = Math.max(5, Math.min(120, parseInt(minDuration, 10) || 15));
    const parsedMaxDur = Math.max(parsedMinDur + 5, Math.min(180, parseInt(maxDuration, 10) || 60));
    const burnSubtitles = subtitles === "true" || subtitles === true;

    const timestampStr = new Date().toISOString().replace(/[-:T.]/g, "").slice(0, 14);
    const runId = `run-${timestampStr}-${Math.random().toString(36).substring(2, 6)}`;
    const runOutputDir = path.join(OUTPUT_DIR, runId);

    let inputSource = "";
    let sourceLabel = "";

    if (sourceType === "upload") {
      if (!req.file) {
        return res.status(400).json({ error: "Harap unggah file video valid." });
      }
      inputSource = req.file.path;
      sourceLabel = req.file.originalname;
    } else if (sourceType === "url" || sourceType === "direct") {
      if (!url || !url.trim()) {
        return res.status(400).json({ error: "Harap masukkan URL video atau link direct podcast yang valid." });
      }
      inputSource = url.trim();
      sourceLabel = url.trim();
    } else {
      inputSource = "sample:podcast";
      sourceLabel = "Simulasi Podcast 2 Pembicara (Smart Crop Demo)";
    }

    const jobState: JobState = {
      id: runId,
      status: "running",
      progress: 5,
      stage: "Inisialisasi",
      message: "Memulai pipeline pemotongan video TikTok...",
      sourceType,
      sourceLabel,
      niche,
      vertical,
      subtitles: burnSubtitles,
      numClips: parsedNumClips,
      startTime: Date.now(),
      logs: [
        {
          timestamp: Date.now(),
          stage: "Inisialisasi",
          message: `Job ${runId} dimulai. Mode Cropping: ${vertical}, Niche: ${niche}`,
        },
      ],
      clips: [],
    };

    activeJobs.set(runId, jobState);

    // Build arguments for src/web_runner.py
    const pyArgs = [
      "-u",
      path.join(ROOT_DIR, "src", "web_runner.py"),
      "--input",
      inputSource,
      "--output-dir",
      runOutputDir,
      "--niche",
      niche,
      "--min-duration",
      String(parsedMinDur),
      "--max-duration",
      String(parsedMaxDur),
      "--num-clips",
      String(parsedNumClips),
      "--vertical",
      vertical,
    ];

    if (burnSubtitles) {
      pyArgs.push("--subtitles");
    } else {
      pyArgs.push("--no-subtitles");
    }

    if (sourceType === "sample") {
      pyArgs.push("--sample");
    }

    if (groqApiKey && groqApiKey.trim()) {
      pyArgs.push("--groq-key", groqApiKey.trim());
    }

    if (llmProvider && llmProvider.trim()) {
      pyArgs.push("--llm-provider", llmProvider.trim());
    }

    if (llmApiKey && llmApiKey.trim()) {
      pyArgs.push("--llm-key", llmApiKey.trim());
    }

    if (llmBaseUrl && llmBaseUrl.trim()) {
      pyArgs.push("--llm-base-url", llmBaseUrl.trim());
    }

    if (llmModel && llmModel.trim()) {
      pyArgs.push("--llm-model", llmModel.trim());
    }


    const pythonBin = "python3";
    const pyProcess = spawn(pythonBin, pyArgs, {
      cwd: ROOT_DIR,
      env: { ...process.env, PYTHONPATH: ROOT_DIR },
    });

    let buffer = "";

    pyProcess.stdout.on("data", (chunk: Buffer) => {
      buffer += chunk.toString("utf-8");
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        // Parse structured JSON events
        if (trimmed.includes("__EVENT_JSON__")) {
          const parts = trimmed.split("__EVENT_JSON__");
          for (let i = 1; i < parts.length; i += 2) {
            try {
              const eventData = JSON.parse(parts[i]);
              if (eventData.event === "progress") {
                jobState.progress = eventData.percent || jobState.progress;
                jobState.stage = eventData.stage || jobState.stage;
                jobState.message = eventData.message || jobState.message;
                jobState.logs.push({
                  timestamp: Date.now(),
                  stage: jobState.stage,
                  message: jobState.message,
                });
              } else if (eventData.event === "probe") {
                jobState.probeData = eventData;
              } else if (eventData.event === "transcript") {
                jobState.transcriptData = eventData;
              } else if (eventData.event === "analysis") {
                jobState.analysisData = eventData;
              } else if (eventData.event === "complete") {
                jobState.status = "completed";
                jobState.progress = 100;
                jobState.stage = "Selesai";
                jobState.endTime = Date.now();
                jobState.clips = eventData.clips || [];
                jobState.message = `Berhasil merender ${eventData.total_rendered || 0} klip!`;
                jobState.logs.push({
                  timestamp: Date.now(),
                  stage: "Selesai",
                  message: jobState.message,
                });
              } else if (eventData.event === "error") {
                jobState.status = "error";
                jobState.error = eventData.message;
                jobState.message = eventData.message;
                jobState.logs.push({
                  timestamp: Date.now(),
                  stage: "Error",
                  message: eventData.message,
                });
              }
            } catch (jsonErr) {
              console.error("JSON event parse error:", jsonErr);
            }
          }
        } else {
          // Standard stdout logger line
          jobState.logs.push({
            timestamp: Date.now(),
            stage: jobState.stage,
            message: trimmed,
          });
        }
      }
    });

    pyProcess.stderr.on("data", (chunk: Buffer) => {
      const errStr = chunk.toString("utf-8").trim();
      if (errStr) {
        jobState.logs.push({
          timestamp: Date.now(),
          stage: "Log",
          message: errStr,
        });
      }
    });

    pyProcess.on("close", (code) => {
      if (code !== 0 && jobState.status !== "completed") {
        jobState.status = "error";
        jobState.error = jobState.error || `Proses berakhir dengan kode keluar ${code}`;
        jobState.message = jobState.error;
      }
    });

    return res.json({
      success: true,
      jobId: runId,
      message: "Proses pemotongan klip berhasil dimulai.",
    });
  } catch (err: any) {
    console.error("Generate API error:", err);
    return res.status(500).json({ error: err.message || "Gagal memulai pembuatan video." });
  }
  });
});

// API: Stream & Serve Output Media (MP4, SRT, JSON, MD) with Byte-Range Support
app.get("/api/media/:jobId/:filename", (req, res) => {
  const { jobId, filename } = req.params;
  const safeJobId = jobId.replace(/[^a-zA-Z0-9_-]/g, "");
  const safeFilename = filename.replace(/[^a-zA-Z0-9._-]/g, "");

  // Look in clips folder first, then run root folder
  let targetPath = path.join(OUTPUT_DIR, safeJobId, "clips", safeFilename);
  if (!fs.existsSync(targetPath)) {
    targetPath = path.join(OUTPUT_DIR, safeJobId, safeFilename);
  }

  if (!fs.existsSync(targetPath)) {
    return res.status(404).send("File media tidak ditemukan.");
  }

  const stat = fs.statSync(targetPath);
  const fileSize = stat.size;
  const ext = path.extname(safeFilename).toLowerCase();

  let contentType = "application/octet-stream";
  if (ext === ".mp4") contentType = "video/mp4";
  else if (ext === ".srt") contentType = "text/plain; charset=utf-8";
  else if (ext === ".json") contentType = "application/json; charset=utf-8";
  else if (ext === ".md") contentType = "text/markdown; charset=utf-8";

  // Handle Range requests for smooth HTML5 video seeking
  const range = req.headers.range;
  if (range && ext === ".mp4") {
    const parts = range.replace(/bytes=/, "").split("-");
    const start = parseInt(parts[0], 10);
    const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
    const chunksize = end - start + 1;
    const file = fs.createReadStream(targetPath, { start, end });

    res.writeHead(206, {
      "Content-Range": `bytes ${start}-${end}/${fileSize}`,
      "Accept-Ranges": "bytes",
      "Content-Length": chunksize,
      "Content-Type": contentType,
    });
    file.pipe(res);
  } else {
    res.writeHead(200, {
      "Content-Length": fileSize,
      "Content-Type": contentType,
      "Accept-Ranges": "bytes",
      "Content-Disposition": ext === ".mp4" ? `inline; filename="${safeFilename}"` : `attachment; filename="${safeFilename}"`,
    });
    fs.createReadStream(targetPath).pipe(res);
  }
});

// Fallback for unmatched API routes - guarantees JSON response, preventing Vite HTML fallback for APIs
app.all("/api/*", (req, res) => {
  res.status(404).json({ error: `API route ${req.method} ${req.path} tidak ditemukan.` });
});

// Global API error handler
app.use((err: any, _req: express.Request, res: express.Response, next: express.NextFunction) => {
  if (res.headersSent) {
    return next(err);
  }
  console.error("Global Express error:", err);
  res.status(err.status || 500).json({
    error: err.message || "Terjadi kesalahan internal pada server.",
  });
});

// Vite Middleware & Static Serving Setup
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true, host: "0.0.0.0", port: PORT },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`TikTok Clipper Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
