"""
Modul Model Data (Pydantic)
Mendefinisikan skema data untuk transkrip, segmen, hasil analisis LLM, probe media, dan metadata klip.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Segment(BaseModel):
    """Mewakili satu segmen transkrip audio dengan stempel waktu."""
    id: int = Field(..., description="ID unik sekuensial untuk segmen")
    start: float = Field(..., description="Waktu mulai dalam detik")
    end: float = Field(..., description="Waktu selesai dalam detik")
    text: str = Field(..., description="Teks hasil transkripsi")
    seek: Optional[float] = 0.0
    temperature: Optional[float] = 0.0
    avg_logprob: Optional[float] = 0.0
    compression_ratio: Optional[float] = 0.0
    no_speech_prob: Optional[float] = 0.0


class TranscriptData(BaseModel):
    """Data lengkap transkrip audio dari Groq Whisper."""
    text: str = Field(..., description="Teks utuh transkrip")
    segments: List[Segment] = Field(default_factory=list, description="Daftar segmen dengan timestamp")
    language: Optional[str] = Field(default="id", description="Bahasa yang terdeteksi")
    duration: Optional[float] = Field(default=0.0, description="Total durasi transkrip dalam detik")


class PodcastContext(BaseModel):
    """Konteks pembicara dan figur publik yang terdeteksi otomatis dari intro/percakapan."""
    host: Optional[str] = Field(default="Host", description="Nama host/pewawancara podcast")
    guest: Optional[str] = Field(default="Bintang Tamu", description="Nama bintang tamu / narasumber")
    guest_role: Optional[str] = Field(default="", description="Profesi atau latar belakang bintang tamu")
    main_topic: Optional[str] = Field(default="", description="Topik utama perbincangan")
    key_entities: List[str] = Field(default_factory=list, description="Figur publik / nama tokoh / istilah penting yang disebut")


class ClipCandidate(BaseModel):
    """Format kandidat klip yang dihasilkan oleh Groq LLM."""
    start_segment_id: int = Field(..., description="ID segmen awal yang dipilih LLM")
    end_segment_id: int = Field(..., description="ID segmen akhir yang dipilih LLM")
    score: int = Field(..., description="Skor potensi viral/kualitas (0-100)")
    title: str = Field(..., max_length=80, description="Judul singkat klip (maks 80 karakter)")
    hook: str = Field(..., max_length=120, description="Hook 3 detik pertama (maks 120 karakter)")
    caption: str = Field(..., description="Caption SEO dengan kata kunci di awal")
    hashtags: List[str] = Field(..., description="3-5 hashtag relevan tanpa tanda pagar")
    cta: str = Field(..., description="Call To Action natural")
    reason: str = Field(..., description="Alasan klip ini dipilih")
    loop_suggestion: str = Field(..., description="Saran transisi akhir video ke awal video")


class ClipAnalysisResult(BaseModel):
    """Kumpulan kandidat klip yang dikembalikan oleh LLM."""
    clips: List[ClipCandidate] = Field(default_factory=list, description="Daftar klip yang direkomendasikan")


class ValidatedClip(BaseModel):
    """Klip yang telah divalidasi stempel waktunya dan siap dirender."""
    index: int
    title: str
    slug: str
    start_time: float
    end_time: float
    duration: float
    start_segment_id: int
    end_segment_id: int
    score: int
    hook: str
    caption: str
    hashtags: List[str]
    cta: str
    reason: str
    loop_suggestion: str
    transcript_text: str
    segments: List[Segment]
    output_video_path: Optional[str] = None
    output_srt_path: Optional[str] = None
    output_json_path: Optional[str] = None
    subtitles_burned: bool = False
    render_success: bool = False
    error_message: Optional[str] = None


class MediaProbeResult(BaseModel):
    """Hasil pemeriksaan ffprobe terhadap file video."""
    duration: float = 0.0
    width: int = 0
    height: int = 0
    has_audio: bool = False
    audio_codec: Optional[str] = None
    video_codec: Optional[str] = None
    fps: Optional[float] = 0.0
    aspect_ratio: Optional[str] = "16:9"
    is_landscape: bool = True


class RunManifest(BaseModel):
    """Manifest lengkap catatan eksekusi pemotongan video."""
    app_version: str = "1.0.0"
    created_at: str
    source_type: str  # 'file' atau 'url'
    source_input: str
    source_video_path: str
    source_duration: float
    source_resolution: str
    niche: str
    total_segments: int
    target_clips_count: int
    successful_clips_count: int
    settings: Dict[str, Any]
    clips: List[Dict[str, Any]]
