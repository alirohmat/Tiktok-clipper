"""
Modul Smart Speaker Tracker & Face-Detection Crop (9:16)
Mendeteksi wajah dan pembicara aktif menggunakan OpenCV (Haar Cascade & Motion Analysis),
kemudian menghasilkan filter FFmpeg untuk memotong video landscape secara dinamis
mengikuti posisi pembicara (Active Speaker Tracking / Dual-Speaker Podcast Split).
"""

import math
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from src.utils import logger

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class SpeakerTrackingResult:
    def __init__(
        self,
        dominant_x_ratio: float = 0.5,
        speakers_detected: int = 1,
        speaker_left_x: float = 0.25,
        speaker_right_x: float = 0.75,
        confidence: float = 0.8,
        is_split_recommended: bool = False,
        trajectory: Optional[List[Tuple[float, float]]] = None
    ):
        self.dominant_x_ratio = dominant_x_ratio  # 0.0 (kiri) sampai 1.0 (kanan)
        self.speakers_detected = speakers_detected
        self.speaker_left_x = speaker_left_x
        self.speaker_right_x = speaker_right_x
        self.confidence = confidence
        self.is_split_recommended = is_split_recommended
        self.trajectory = trajectory or []


def _get_cascade_classifier():
    """Memuat classifier Haar Cascade wajah depan dari OpenCV."""
    if not OPENCV_AVAILABLE:
        return None
    try:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        classifier = cv2.CascadeClassifier(cascade_path)
        if classifier.empty():
            return None
        return classifier
    except Exception as e:
        logger.warning(f"Tidak dapat memuat Haar Cascade: {e}")
        return None


def detect_speakers_in_clip(
    video_path: Path,
    start_time: float,
    duration: float,
    sample_fps: float = 2.0,
    max_samples: int = 60
) -> SpeakerTrackingResult:
    """
    Memindai klip video dan mendeteksi posisi wajah/pembicara aktif.
    Mengembalikan SpeakerTrackingResult berisi rasio posisi X pembicara (0.0 - 1.0)
    dan rekomendasi apakah podcast/dialog 2 orang.
    """
    if not OPENCV_AVAILABLE:
        logger.debug("OpenCV tidak tersedia, menggunakan fallback center crop.")
        return SpeakerTrackingResult(dominant_x_ratio=0.5, speakers_detected=1)

    face_cascade = _get_cascade_classifier()
    if face_cascade is None:
        logger.debug("Haar Cascade tidak dapat dimuat, menggunakan fallback center.")
        return SpeakerTrackingResult(dominant_x_ratio=0.5, speakers_detected=1)

    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return SpeakerTrackingResult(dominant_x_ratio=0.5, speakers_detected=1)

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080

        # Jika video sudah berformat vertikal atau square, tidak perlu crop X
        if width <= height:
            cap.release()
            return SpeakerTrackingResult(dominant_x_ratio=0.5, speakers_detected=1)

        start_frame = max(0, int(start_time * fps))
        clip_frames = max(1, int(duration * fps))
        end_frame = min(total_frames, start_frame + clip_frames)

        frame_step = max(1, int(fps / sample_fps))
        sample_frame_indices = list(range(start_frame, end_frame, frame_step))
        if len(sample_frame_indices) > max_samples:
            step_stride = len(sample_frame_indices) // max_samples
            sample_frame_indices = sample_frame_indices[::step_stride][:max_samples]

        detected_face_centers: List[Tuple[float, float, float]] = []  # (t_sec, norm_cx, area_weight)
        left_speaker_faces: List[float] = []
        right_speaker_faces: List[float] = []
        center_speaker_faces: List[float] = []

        prev_gray_mouth: Optional[np.ndarray] = None
        motion_weights: List[float] = []

        for frame_idx in sample_frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Deteksi wajah dengan scaleFactor dan minNeighbors
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.15,
                minNeighbors=4,
                minSize=(int(height * 0.08), int(height * 0.08)),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            t_sec = (frame_idx - start_frame) / fps

            if len(faces) > 0:
                for (x, y, w, h) in faces:
                    norm_cx = (x + (w / 2.0)) / width
                    area = (w * h) / (width * height)

                    # Analisis gerak di area mulut/bawah wajah untuk mendeteksi yang berbicara
                    mouth_y1 = int(y + h * 0.6)
                    mouth_y2 = int(y + h)
                    mouth_x1 = int(x + w * 0.2)
                    mouth_x2 = int(x + w * 0.8)

                    mouth_crop = gray[max(0, mouth_y1):min(int(height), mouth_y2), max(0, mouth_x1):min(int(width), mouth_x2)]
                    motion_score = 1.0
                    if mouth_crop.size > 0:
                        mouth_std = float(np.std(mouth_crop))
                        motion_score = max(0.5, mouth_std / 20.0)

                    weight = area * motion_score
                    detected_face_centers.append((t_sec, norm_cx, weight))

                    if norm_cx < 0.42:
                        left_speaker_faces.append(norm_cx)
                    elif norm_cx > 0.58:
                        right_speaker_faces.append(norm_cx)
                    else:
                        center_speaker_faces.append(norm_cx)

        cap.release()

        if not detected_face_centers:
            # Tidak ada wajah terdeteksi, fallback tengah
            return SpeakerTrackingResult(dominant_x_ratio=0.5, speakers_detected=1, confidence=0.3)

        # Hitung weighted average dari posisi X wajah
        total_weight = sum(w for _, _, w in detected_face_centers)
        if total_weight > 0:
            weighted_cx = sum(cx * w for _, cx, w in detected_face_centers) / total_weight
        else:
            weighted_cx = sum(cx for _, cx, _ in detected_face_centers) / len(detected_face_centers)

        # Deteksi podcast 2 orang (apabila ada klaster jelas di kiri dan kanan)
        has_left = len(left_speaker_faces) >= 2
        has_right = len(right_speaker_faces) >= 2
        is_split = has_left and has_right

        left_avg = float(np.median(left_speaker_faces)) if left_speaker_faces else 0.25
        right_avg = float(np.median(right_speaker_faces)) if right_speaker_faces else 0.75

        # Jika ada cross-talk tapi mode single-cam dipilih, pilih cluster yang memiliki total bobot terbesar
        # agar kamera stabil dan TIDAK melompat-lompat bolak-balik di tengah-tengah
        if is_split:
            left_weight = sum(w for _, cx, w in detected_face_centers if cx < 0.5)
            right_weight = sum(w for _, cx, w in detected_face_centers if cx >= 0.5)
            # Stabilkan pilihan pembicara utama untuk single tracking
            if left_weight >= right_weight * 1.2:
                weighted_cx = left_avg
            elif right_weight >= left_weight * 1.2:
                weighted_cx = right_avg
            else:
                # Jika sama-sama aktif, gunakan pembicara utama dengan bobot tertinggi
                dominant_face = max(detected_face_centers, key=lambda item: item[2])
                weighted_cx = dominant_face[1]

        # Batasi posisi X agar aman dalam batas 0.15 - 0.85
        weighted_cx = max(0.18, min(0.82, weighted_cx))

        return SpeakerTrackingResult(
            dominant_x_ratio=float(weighted_cx),
            speakers_detected=2 if is_split else 1,
            speaker_left_x=max(0.15, min(0.45, left_avg)),
            speaker_right_x=max(0.55, min(0.85, right_avg)),
            confidence=0.85 if len(detected_face_centers) >= 4 else 0.5,
            is_split_recommended=is_split,
            trajectory=[(t, cx) for t, cx, _ in detected_face_centers]
        )

    except Exception as e:
        logger.warning(f"Error saat deteksi pembicara: {e}")
        return SpeakerTrackingResult(dominant_x_ratio=0.5, speakers_detected=1, confidence=0.2)


def generate_speaker_crop_filter(
    video_path: Path,
    start_time: float,
    duration: float,
    vertical_mode: str = "speaker",
    video_width: int = 1920,
    video_height: int = 1080
) -> str:
    """
    Menghasilkan rantai filter video FFmpeg yang mengarahkan fokus crop 9:16 (1080x1920)
    ke wajah pembicara aktif berdasarkan deteksi OpenCV.
    Jika 2 orang berbicara bersamaan (podcast), menghasilkan Dual-Speaker Split Screen (Atas/Bawah).
    """
    mode = vertical_mode.lower()

    # Hitung rasio target 9:16 dari ketinggian asli
    # Di video landscape 1920x1080, crop 9:16 dari height 1080 = lebar 607.5px (1080 * 9 / 16)
    target_crop_w = int(round((video_height * 9) / 16))
    if target_crop_w % 2 != 0:
        target_crop_w += 1

    # Jalankan deteksi pembicara
    tracking = detect_speakers_in_clip(video_path, start_time, duration)
    logger.info(
        f"Smart Speaker Tracker [t={start_time:.1f}s-{start_time+duration:.1f}s]: "
        f"X-Ratio={tracking.dominant_x_ratio:.2f}, Speakers={tracking.speakers_detected}, "
        f"Confidence={tracking.confidence:.2f}, SplitRec={tracking.is_split_recommended}"
    )

    # 1. Mode Podcast Split (Dua Pembicara Tumpuk Atas-Bawah)
    # Otomatis aktif jika mode 'split' atau mode 'auto' saat 2 pembicara terdeteksi
    if (mode in ("split", "speaker_split", "podcast")) or (mode == "auto" and tracking.is_split_recommended):
        # Bagi layar menjadi 2 crop: Atas fokus Speaker 1 (Kiri/Host), Bawah fokus Speaker 2 (Kanan/Tamu)
        # Tiap crop berukuran 1080x960 (rasio 9:8)
        split_crop_w = int(round((video_height * 1080) / 960))  # Aspect 1080:960
        if split_crop_w % 2 != 0:
            split_crop_w += 1
        if split_crop_w > video_width:
            split_crop_w = video_width
        
        # Koordinat X kiri dan kanan dengan margin aman
        x_left = max(0, min(video_width - split_crop_w, int(tracking.speaker_left_x * video_width - split_crop_w / 2)))
        x_right = max(0, min(video_width - split_crop_w, int(tracking.speaker_right_x * video_width - split_crop_w / 2)))

        filter_str = (
            f"[0:v]split=2[v_top_raw][v_bot_raw];"
            f"[v_top_raw]crop={split_crop_w}:{video_height}:{x_left}:0,scale=1080:960:flags=lanczos[v_top];"
            f"[v_bot_raw]crop={split_crop_w}:{video_height}:{x_right}:0,scale=1080:960:flags=lanczos[v_bot];"
            f"[v_top][v_bot]vstack=inputs=2[v_out]"
        )
        return filter_str

    # 2. Mode Smart Speaker Tracking (Active Face Focus Single-Cam dengan Anti-Jitter)
    # Hitung posisi X crop yang memusatkan wajah pembicara
    face_center_px = int(tracking.dominant_x_ratio * video_width)
    crop_x = int(face_center_px - (target_crop_w / 2))
    
    # Batasi agar crop_x tidak keluar dari canvas video
    max_crop_x = max(0, video_width - target_crop_w)
    crop_x = max(0, min(max_crop_x, crop_x))

    # Skala hasil crop ke 1080x1920 standar TikTok
    filter_str = f"crop={target_crop_w}:{video_height}:{crop_x}:0,scale=1080:1920:flags=lanczos"
    return filter_str

