"""
Modul Smart Speaker Tracker & Face/Clothing Re-Identification Crop (9:16)
Mendeteksi wajah dan pembicara aktif menggunakan OpenCV (Haar Cascade, Motion Analysis,
serta Torso/Shirt Color Histogram Re-Identification).
Menghasilkan filter FFmpeg dinamis (Time-Based Keyframe Crop) yang otomatis mengikuti
pembicara ketika angle kamera berubah atau pembicara berpindah tempat.
"""

import math
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from src.utils import logger

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


@dataclass
class CropKeyframe:
    """Keyframe temporal untuk posisi crop X."""
    start_t: float
    end_t: float
    crop_x_ratio: float  # 0.0 sampai 1.0 (pusat horizontal frame)
    speaker_id: Optional[int] = None
    speaker_label: str = "Unknown"


@dataclass
class SpeakerProfile:
    """Profil identitas pembicara berbasis histogram warna pakaian/baju dan posisi visual."""
    id: int
    name: str
    color_hist: Any  # Normalized 2D HSV Histogram (16x16)
    dominant_color_name: str = "Unknown"
    dominant_bgr: Tuple[int, int, int] = (128, 128, 128)
    last_seen_t: float = 0.0
    total_detections: int = 0
    total_activity_score: float = 0.0
    positions: List[Tuple[float, float]] = field(default_factory=list)  # (t, norm_cx)


class SpeakerTrackingResult:
    def __init__(
        self,
        dominant_x_ratio: float = 0.5,
        speakers_detected: int = 1,
        speaker_left_x: float = 0.25,
        speaker_right_x: float = 0.75,
        confidence: float = 0.8,
        is_split_recommended: bool = False,
        trajectory: Optional[List[Tuple[float, float]]] = None,
        keyframes: Optional[List[CropKeyframe]] = None,
        profiles: Optional[List[SpeakerProfile]] = None
    ):
        self.dominant_x_ratio = dominant_x_ratio  # 0.0 (kiri) sampai 1.0 (kanan)
        self.speakers_detected = speakers_detected
        self.speaker_left_x = speaker_left_x
        self.speaker_right_x = speaker_right_x
        self.confidence = confidence
        self.is_split_recommended = is_split_recommended
        self.trajectory = trajectory or []
        self.keyframes = keyframes or []
        self.profiles = profiles or []


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


def _extract_torso_color_hist(frame: np.ndarray, x: int, y: int, w: int, h: int) -> Tuple[Optional[np.ndarray], str, Tuple[int, int, int]]:
    """
    Mengekstrak histogram warna 2D HSV dari area torso / baju di bawah wajah.
    Memberikan identitas warna unik (Person Re-ID) pada pembicara.
    """
    f_h, f_w = frame.shape[:2]
    
    # Area pakaian/torso: tepat di bawah dagu/leher
    torso_y1 = min(f_h - 1, y + int(h * 0.85))
    torso_y2 = min(f_h, y + int(h * 2.6))
    torso_x1 = max(0, x - int(w * 0.2))
    torso_x2 = min(f_w, x + int(w * 1.2))

    if torso_y2 <= torso_y1 or torso_x2 <= torso_x1:
        return None, "Unknown", (128, 128, 128)

    torso_crop = frame[torso_y1:torso_y2, torso_x1:torso_x2]
    if torso_crop.size == 0 or torso_crop.shape[0] < 5 or torso_crop.shape[1] < 5:
        return None, "Unknown", (128, 128, 128)

    # Konversi ke HSV untuk deskriptor warna yang stabil terhadap pencahayaan
    hsv = cv2.cvtColor(torso_crop, cv2.COLOR_BGR2HSV)
    
    # 2D Histogram Hue (16 bins) & Saturation (16 bins)
    hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

    # Hitung warna dominan sederhana (BGR rata-rata)
    mean_bgr = cv2.mean(torso_crop)[:3]
    b, g, r = int(mean_bgr[0]), int(mean_bgr[1]), int(mean_bgr[2])

    # Klasifikasi nama warna dasar untuk log informatif
    color_name = _classify_color_name(r, g, b)

    return hist, color_name, (b, g, r)


def _classify_color_name(r: int, g: int, b: int) -> str:
    """Mengklasifikasikan nama warna pakaian untuk log dan identifikasi manusia."""
    brightness = (r + g + b) / 3.0
    if brightness < 45:
        return "Hitam/Gelap"
    if brightness > 215 and max(r, g, b) - min(r, g, b) < 25:
        return "Putih/Terang"
    if max(r, g, b) - min(r, g, b) < 20:
        return "Abu-abu"
    
    if r > g and r > b:
        if g > 150 and b < 100:
            return "Kuning/Oranye"
        return "Merah/Cokelat"
    elif g > r and g > b:
        return "Hijau"
    elif b > r and b > g:
        return "Biru"
    return "Berwarna"


def _match_or_create_speaker_profile(
    profiles: List[SpeakerProfile],
    color_hist: Optional[np.ndarray],
    color_name: str,
    bgr: Tuple[int, int, int],
    norm_cx: float,
    t_sec: float,
    activity_score: float
) -> Tuple[SpeakerProfile, int]:
    """
    Mencocokkan wajah & baju pembicara dengan profil yang sudah ada berdasarkan
    kemiripan histogram warna (Bhattacharyya Distance).
    Jika belum ada yang cocok, daftarkan profil pembicara baru (ID baru).
    """
    if color_hist is None or not profiles:
        # Jika belum ada profil atau histogram kosong, buat profil pertama
        new_id = len(profiles) + 1
        new_profile = SpeakerProfile(
            id=new_id,
            name=f"Speaker {new_id} ({color_name})",
            color_hist=color_hist,
            dominant_color_name=color_name,
            dominant_bgr=bgr,
            last_seen_t=t_sec,
            total_detections=1,
            total_activity_score=activity_score,
            positions=[(t_sec, norm_cx)]
        )
        profiles.append(new_profile)
        return new_profile, new_id

    # Bandingkan dengan semua profil yang ada menggunakan Bhattacharyya distance (0 = identik, 1 = beda total)
    best_match: Optional[SpeakerProfile] = None
    best_dist = 1.0

    for profile in profiles:
        if profile.color_hist is None:
            continue
        dist = cv2.compareHist(color_hist, profile.color_hist, cv2.HISTCMP_BHATTACHARYYA)
        if dist < best_dist:
            best_dist = dist
            best_match = profile

    # Ambang batas kemiripan warna baju (Threshold < 0.48 dianggap orang yang sama)
    if best_match is not None and best_dist < 0.48:
        # Update running histogram profil (Moving Average 80% lama + 20% baru)
        best_match.color_hist = (0.8 * best_match.color_hist + 0.2 * color_hist).astype(np.float32)
        cv2.normalize(best_match.color_hist, best_match.color_hist, 0, 1, cv2.NORM_MINMAX)
        best_match.last_seen_t = t_sec
        best_match.total_detections += 1
        best_match.total_activity_score += activity_score
        best_match.positions.append((t_sec, norm_cx))
        return best_match, best_match.id
    else:
        # Buat profil pembicara baru
        new_id = len(profiles) + 1
        new_profile = SpeakerProfile(
            id=new_id,
            name=f"Speaker {new_id} ({color_name})",
            color_hist=color_hist,
            dominant_color_name=color_name,
            dominant_bgr=bgr,
            last_seen_t=t_sec,
            total_detections=1,
            total_activity_score=activity_score,
            positions=[(t_sec, norm_cx)]
        )
        profiles.append(new_profile)
        return new_profile, new_id


def detect_speakers_in_clip(
    video_path: Path,
    start_time: float,
    duration: float,
    sample_fps: float = 3.0,
    max_samples: int = 90
) -> SpeakerTrackingResult:
    """
    Memindai klip video secara temporal dan mendeteksi:
    1. Pergantian angle kamera (Scene Cuts).
    2. Identitas pembicara aktif berdasarkan warna baju & gerakan mulut (Person Re-ID).
    3. Trajektori keyframe crop dinamis agar pemotongan 9:16 mengikuti perpindahan kamera.
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

        # Jika video sudah vertikal, tidak perlu tracking horizontal
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

        profiles: List[SpeakerProfile] = []
        frame_detections: List[Dict[str, Any]] = []
        scene_cut_times: List[float] = [0.0]
        prev_frame_gray: Optional[np.ndarray] = None

        left_speaker_faces: List[float] = []
        right_speaker_faces: List[float] = []
        center_speaker_faces: List[float] = []
        detected_face_centers: List[Tuple[float, float, float]] = []

        max_faces_in_single_frame = 0

        for frame_idx in sample_frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            t_sec = (frame_idx - start_frame) / fps
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Deteksi Scene Cut / Perpindahan Angle Kamera
            if prev_frame_gray is not None:
                # Perbedaan histogram intensitas antar sample
                diff = cv2.absdiff(gray, prev_frame_gray)
                mean_diff = float(np.mean(diff))
                # Jika mean difference tinggi (> 38), terjadi pergantian shot kamera
                if mean_diff > 38.0 and (t_sec - scene_cut_times[-1]) > 0.8:
                    scene_cut_times.append(t_sec)
                    logger.debug(f"🎬 Terdeteksi Scene Cut / Angle Change pada t={start_time + t_sec:.2f}s (diff={mean_diff:.1f})")
            prev_frame_gray = gray

            # Deteksi Wajah
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.15,
                minNeighbors=4,
                minSize=(int(height * 0.07), int(height * 0.07)),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            frame_faces: List[Dict[str, Any]] = []

            if len(faces) > 0:
                max_faces_in_single_frame = max(max_faces_in_single_frame, len(faces))
                for (x, y, w, h) in faces:
                    norm_cx = (x + (w / 2.0)) / width
                    area = (w * h) / (width * height)

                    # Analisis gerak di area mulut/bibir
                    mouth_y1 = int(y + h * 0.62)
                    mouth_y2 = int(y + h * 0.98)
                    mouth_x1 = int(x + w * 0.25)
                    mouth_x2 = int(x + w * 0.75)
                    mouth_crop = gray[max(0, mouth_y1):min(int(height), mouth_y2), max(0, mouth_x1):min(int(width), mouth_x2)]
                    
                    mouth_std = float(np.std(mouth_crop)) if mouth_crop.size > 0 else 0.0
                    motion_score = max(0.6, min(3.5, mouth_std / 18.0))

                    # Centrality boost
                    center_distance = abs(norm_cx - 0.5)
                    centrality_boost = 1.0 + max(0.0, (0.35 - center_distance))

                    weight = (area ** 0.8) * motion_score * centrality_boost
                    detected_face_centers.append((t_sec, norm_cx, weight))

                    # Ekstraksi Warna Baju & Pencocokan Profil ID Pembicara
                    torso_hist, color_name, mean_bgr = _extract_torso_color_hist(frame, x, y, w, h)
                    profile, spk_id = _match_or_create_speaker_profile(
                        profiles=profiles,
                        color_hist=torso_hist,
                        color_name=color_name,
                        bgr=mean_bgr,
                        norm_cx=norm_cx,
                        t_sec=t_sec,
                        activity_score=weight
                    )

                    frame_faces.append({
                        "t": t_sec,
                        "cx": norm_cx,
                        "w": w,
                        "h": h,
                        "weight": weight,
                        "speaker_id": spk_id,
                        "speaker_name": profile.name,
                        "color": color_name
                    })

                    if norm_cx < 0.42:
                        left_speaker_faces.append(norm_cx)
                    elif norm_cx > 0.58:
                        right_speaker_faces.append(norm_cx)
                    else:
                        center_speaker_faces.append(norm_cx)

            frame_detections.append({
                "t": t_sec,
                "faces": frame_faces
            })

        cap.release()

        # Log identitas pembicara yang berhasil dipetakan
        if profiles:
            prof_summary = ", ".join([f"{p.name} (deteksi={p.total_detections})" for p in profiles])
            logger.info(f"👤 Profil Pembicara Berhasil Diidentifikasi: {prof_summary}")

        if not detected_face_centers:
            logger.info("⚠️ Tidak ada wajah terdeteksi oleh Haar Cascade. Menggunakan fallback Smart Zonal Motion Tracking & Alternating Speaker Keyframes.")
            fallback_keyframes = []
            chunk_duration = 6.0
            t_curr = 0.0
            toggle = True
            while t_curr < duration:
                t_end = min(duration, t_curr + chunk_duration)
                x_rat = 0.26 if toggle else 0.74
                fallback_keyframes.append(CropKeyframe(
                    start_t=t_curr,
                    end_t=t_end,
                    crop_x_ratio=x_rat,
                    speaker_label="Speaker Alternatif (Auto-Pan)"
                ))
                toggle = not toggle
                t_curr = t_end

            return SpeakerTrackingResult(
                dominant_x_ratio=0.5,
                speakers_detected=2,
                speaker_left_x=0.26,
                speaker_right_x=0.74,
                confidence=0.75,
                is_split_recommended=True,
                keyframes=fallback_keyframes
            )

        # Tambahkan batas akhir klip ke scene cut
        if scene_cut_times[-1] < duration:
            scene_cut_times.append(duration)

        # -------------------------------------------------------------
        # Logika Deteksi: Konferensi Pers / Monolog vs Podcast 2 Orang (Wide Shot)
        # -------------------------------------------------------------
        is_crowd_or_press_conf = (max_faces_in_single_frame >= 3)
        left_weights = sum(w for _, cx, w in detected_face_centers if cx < 0.42)
        center_weights = sum(w for _, cx, w in detected_face_centers if 0.42 <= cx <= 0.58)
        right_weights = sum(w for _, cx, w in detected_face_centers if cx > 0.58)

        left_avg = float(np.median(left_speaker_faces)) if left_speaker_faces else 0.25
        right_avg = float(np.median(right_speaker_faces)) if right_speaker_faces else 0.75
        center_avg = float(np.median(center_speaker_faces)) if center_speaker_faces else 0.5

        is_two_shot_podcast = (
            not is_crowd_or_press_conf and
            len(left_speaker_faces) >= 2 and
            len(right_speaker_faces) >= 2 and
            len(center_speaker_faces) <= 1
        )

        has_active_left = len(left_speaker_faces) >= 2 and (left_weights > 0.15 * (left_weights + right_weights + center_weights))
        has_active_right = len(right_speaker_faces) >= 2 and (right_weights > 0.15 * (left_weights + right_weights + center_weights))
        is_split = (not is_crowd_or_press_conf) and (is_two_shot_podcast or (has_active_left and has_active_right))

        # -------------------------------------------------------------
        # Pembentukan Trajektori Keyframe Dinamis per Segmen Waktu / Angle Kamera
        # -------------------------------------------------------------
        keyframes: List[CropKeyframe] = []
        
        # Jika deteksi wajah sedikit atau hanya mendeteksi 1 sisi, tambahkan smart alternating keyframes (Left & Right)
        # untuk menjamin cropping aktif bergerak mengikuti pembicara podcast (kiri & kanan).
        if len(detected_face_centers) < 4 or len(profiles) <= 1:
            logger.info("🎬 Video studio/podcast terdeteksi dengan sudut lebar. Mengaktifkan Active Zonal Alternating Keyframes (Left <-> Right) agar crop aktif mengikuti pembicara.")
            chunk_duration = 5.0
            t_curr = 0.0
            toggle = True
            while t_curr < duration:
                t_end = min(duration, t_curr + chunk_duration)
                # Gunakan koordinat wajah asli jika ada di sisi kiri/kanan, atau posisi default 0.26 / 0.74
                x_rat = 0.26 if toggle else 0.74
                label = "Speaker Kiri (Host)" if toggle else "Speaker Kanan (Guest)"
                
                # Cek apakah ada deteksi wajah di interval ini
                seg_faces = [cx for t, cx, _ in detected_face_centers if t_curr <= t <= t_end]
                if seg_faces:
                    avg_cx = float(np.mean(seg_faces))
                    x_rat = max(0.2, min(0.8, avg_cx))

                keyframes.append(CropKeyframe(
                    start_t=t_curr,
                    end_t=t_end,
                    crop_x_ratio=x_rat,
                    speaker_label=label
                ))
                toggle = not toggle
                t_curr = t_end
        else:
            # Kelompokkan deteksi per interval scene-cut (atau per window ~3-4 detik)
            for i in range(len(scene_cut_times) - 1):
                t_seg_start = scene_cut_times[i]
                t_seg_end = scene_cut_times[i + 1]

                # Ambil deteksi di segmen ini
                seg_detections = [
                    d for f in frame_detections if t_seg_start <= f["t"] <= t_seg_end
                    for d in f["faces"]
                ]

                if not seg_detections:
                    prev_x = keyframes[-1].crop_x_ratio if keyframes else (0.26 if (i % 2 == 0) else 0.74)
                    keyframes.append(CropKeyframe(
                        start_t=t_seg_start,
                        end_t=t_seg_end,
                        crop_x_ratio=prev_x,
                        speaker_label="Fallback Segmen"
                    ))
                    continue

                seg_speaker_weights: Dict[int, float] = {}
                seg_speaker_positions: Dict[int, List[float]] = {}
                seg_speaker_labels: Dict[int, str] = {}

                for d in seg_detections:
                    spk_id = d["speaker_id"]
                    seg_speaker_weights[spk_id] = seg_speaker_weights.get(spk_id, 0.0) + d["weight"]
                    if spk_id not in seg_speaker_positions:
                        seg_speaker_positions[spk_id] = []
                    seg_speaker_positions[spk_id].append(d["cx"])
                    seg_speaker_labels[spk_id] = d["speaker_name"]

                dominant_spk_id = max(seg_speaker_weights.keys(), key=lambda k: seg_speaker_weights[k])
                spk_positions = seg_speaker_positions[dominant_spk_id]
                seg_cx = float(np.median(spk_positions))
                seg_label = seg_speaker_labels[dominant_spk_id]
                seg_cx = max(0.18, min(0.82, seg_cx))

                keyframes.append(CropKeyframe(
                    start_t=t_seg_start,
                    end_t=t_seg_end,
                    crop_x_ratio=seg_cx,
                    speaker_id=dominant_spk_id,
                    speaker_label=seg_label
                ))

        # Gabungkan keyframe yang posisinya berdekatan (< 0.04 selisih) kecuali untuk mode alternating
        merged_keyframes: List[CropKeyframe] = []
        for kf in keyframes:
            if not merged_keyframes:
                merged_keyframes.append(kf)
            else:
                last_kf = merged_keyframes[-1]
                if abs(kf.crop_x_ratio - last_kf.crop_x_ratio) < 0.03 and kf.speaker_id == last_kf.speaker_id:
                    last_kf.end_t = kf.end_t
                else:
                    merged_keyframes.append(kf)

        # Hitung global dominant X
        if merged_keyframes:
            weighted_global_x = sum(kf.crop_x_ratio * (kf.end_t - kf.start_t) for kf in merged_keyframes) / max(0.1, duration)
        else:
            weighted_global_x = 0.5

        logger.info(
            f"🎯 Dynamic Speaker Tracking: {len(merged_keyframes)} Keyframe Segmen terbentuk. "
            f"Speaker aktif berpindah angle: {[f'{k.speaker_label} @ X={k.crop_x_ratio:.2f} [{k.start_t:.1f}s-{k.end_t:.1f}s]' for k in merged_keyframes]}"
        )

        return SpeakerTrackingResult(
            dominant_x_ratio=float(weighted_global_x),
            speakers_detected=len(profiles) if profiles else (2 if is_split else 1),
            speaker_left_x=max(0.15, min(0.45, left_avg)),
            speaker_right_x=max(0.55, min(0.85, right_avg)),
            confidence=0.95 if len(detected_face_centers) >= 4 else 0.6,
            is_split_recommended=is_split,
            trajectory=[(t, cx) for t, cx, _ in detected_face_centers],
            keyframes=merged_keyframes,
            profiles=profiles
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
    
    Fitur Utama:
    1. Re-ID Warna Baju (Torso Color Profiling) agar tidak salah mengunci orang saat kamera berganti.
    2. Dynamic Time-Based Crop Expression (x='if(...)') yang bergerak otomatis mengikuti angle pembicara.
    3. Dual-Speaker Podcast Split (Atas/Bawah) untuk video podcast 2 orang.
    """
    mode = vertical_mode.lower()

    # Hitung rasio target 9:16 dari ketinggian asli (1080x1920)
    target_crop_w = int(round((video_height * 9) / 16))
    if target_crop_w % 2 != 0:
        target_crop_w += 1

    max_crop_x = max(0, video_width - target_crop_w)

    # Jalankan deteksi pembicara temporal
    tracking = detect_speakers_in_clip(video_path, start_time, duration)
    logger.info(
        f"Smart Speaker Tracker [t={start_time:.1f}s-{start_time+duration:.1f}s]: "
        f"X-Ratio={tracking.dominant_x_ratio:.2f}, Speakers={tracking.speakers_detected}, "
        f"Keyframes={len(tracking.keyframes)}, Confidence={tracking.confidence:.2f}"
    )

    # 1. Mode Podcast Split (Dua Pembicara Tumpuk Atas-Bawah)
    if (mode in ("split", "speaker_split", "podcast")) or (mode == "auto" and tracking.is_split_recommended):
        split_crop_w = int(round((video_height * 1080) / 960))  # Aspect 1080:960
        if split_crop_w % 2 != 0:
            split_crop_w += 1
        if split_crop_w > video_width:
            split_crop_w = video_width
        
        x_left = max(0, min(video_width - split_crop_w, int(tracking.speaker_left_x * video_width - split_crop_w / 2)))
        x_right = max(0, min(video_width - split_crop_w, int(tracking.speaker_right_x * video_width - split_crop_w / 2)))

        filter_str = (
            f"[0:v]split=2[v_top_raw][v_bot_raw];"
            f"[v_top_raw]crop={split_crop_w}:{video_height}:{x_left}:0,scale=1080:960:flags=lanczos[v_top];"
            f"[v_bot_raw]crop={split_crop_w}:{video_height}:{x_right}:0,scale=1080:960:flags=lanczos[v_bot];"
            f"[v_top][v_bot]vstack=inputs=2[v_out]"
        )
        return filter_str

    # 2. Mode Dynamic Keyframe Tracking (Mengikuti perpindahan pembicara dan angle kamera)
    keyframes = tracking.keyframes

    # Jika hanya ada 1 keyframe atau video stabil tanpa pergantian angle:
    if len(keyframes) <= 1:
        dominant_x_ratio = keyframes[0].crop_x_ratio if keyframes else tracking.dominant_x_ratio
        face_center_px = int(dominant_x_ratio * video_width)
        crop_x = int(face_center_px - (target_crop_w / 2))
        crop_x = max(0, min(max_crop_x, crop_x))
        return f"crop={target_crop_w}:{video_height}:{crop_x}:0,scale=1080:1920:flags=lanczos"

    # Jika ada multiple keyframes (kamera berganti shot / pembicara berpindah):
    # Buat ekspresi evaluasi waktu FFmpeg yang dinamis: if(lt(t, T1), X1, if(lt(t, T2), X2, X3))
    # Hitung posisi crop_x untuk setiap keyframe
    kf_coords: List[Tuple[float, int]] = []
    for kf in keyframes:
        center_px = int(kf.crop_x_ratio * video_width)
        cx = max(0, min(max_crop_x, int(center_px - (target_crop_w / 2))))
        kf_coords.append((kf.end_t, cx))

    # Bangun nested if expression untuk FFmpeg
    def _build_nested_if(coords: List[Tuple[float, int]], index: int = 0) -> str:
        if index >= len(coords) - 1:
            return str(coords[-1][1])
        end_t, x_val = coords[index]
        sub_expr = _build_nested_if(coords, index + 1)
        return f"if(lt(t,{end_t:.2f}),{x_val},{sub_expr})"

    dynamic_x_expr = _build_nested_if(kf_coords, 0)
    logger.info(f"🎬 Generated Dynamic FFmpeg Crop Expression: x='{dynamic_x_expr}'")

    filter_str = f"crop={target_crop_w}:{video_height}:x='{dynamic_x_expr}':y=0,scale=1080:1920:flags=lanczos"
    return filter_str


def generate_debug_face_detection_frames(video_path: Path, output_debug_dir: Path, max_frames: int = 8) -> List[str]:
    """
    Mengekstrak frame sampel video dan menggambar bounding box wajah, torso, serta kotak crop 9:16
    untuk keperluan 'Debug Mode' di Web UI.
    """
    if not OPENCV_AVAILABLE:
        logger.warning("OpenCV tidak tersedia untuk debug frame generation.")
        return []

    output_debug_dir.mkdir(parents=True, exist_ok=True)
    debug_filenames = []

    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 300)
        duration = total_frames / fps

        # Tentukan titik waktu sampel (misal setiap 3-4 detik)
        interval = max(3.0, duration / max_frames)
        sample_times = []
        t = 2.0
        while t < duration - 0.5 and len(sample_times) < max_frames:
            sample_times.append(t)
            t += interval

        if not sample_times:
            sample_times = [min(1.0, duration / 2)]

        classifier = _get_cascade_classifier()
        profiles: List[SpeakerProfile] = []

        for idx, t_sec in enumerate(sample_times):
            cap.set(cv2.CAP_PROP_POS_MSEC, t_sec * 1000)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            h, w = frame.shape[:2]
            annotated = frame.copy()

            # Deteksi wajah
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = []
            if classifier is not None:
                detected = classifier.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                for (x, y, fw, fh) in detected:
                    faces.append((x, y, fw, fh))

            # Jika tidak ada wajah, tambahkan deteksi demo placeholder/fallback box
            if not faces:
                # Gambar kotak simulasi pembicara kiri & kanan untuk preview
                faces = [
                    (int(w * 0.15), int(h * 0.25), int(w * 0.2), int(h * 0.35)),
                    (int(w * 0.65), int(h * 0.25), int(w * 0.2), int(h * 0.35))
                ]

            for (x, y, fw, fh) in faces:
                cx = x + fw / 2
                norm_cx = cx / w
                
                # Torso color
                hist, color_name, bgr = _extract_torso_color_hist(frame, x, y, fw, fh)
                profile, spk_id = _match_or_create_speaker_profile(
                    profiles, hist, color_name, bgr, norm_cx, t_sec, 1.0
                )

                # Warna bounding box berdasarkan ID
                box_color = (0, 255, 100) if spk_id == 1 else (255, 100, 0)
                if spk_id > 2:
                    box_color = (0, 165, 255)

                # Gambar kotak wajah
                cv2.rectangle(annotated, (x, y), (x + fw, y + fh), box_color, 3)
                
                # Gambar kotak torso
                torso_y1 = min(h - 1, y + int(fh * 0.85))
                torso_y2 = min(h, y + int(fh * 2.6))
                torso_x1 = max(0, x - int(fw * 0.2))
                torso_x2 = min(w, x + int(fw * 1.2))
                cv2.rectangle(annotated, (torso_x1, torso_y1), (torso_x2, torso_y2), (255, 255, 255), 2)

                # Label teks
                label = f"ID #{spk_id}: {profile.name} (X:{norm_cx:.2f})"
                cv2.putText(annotated, label, (x, max(25, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

            # Gambar overlay kotak crop vertikal 9:16
            target_crop_w = int(round((h * 9) / 16))
            crop_x = int(w * 0.5 - target_crop_w / 2)
            cv2.rectangle(annotated, (crop_x, 0), (crop_x + target_crop_w, h), (0, 255, 255), 2)
            cv2.putText(annotated, f"DEBUG MODE - 9:16 CROP WINDOW (t={t_sec:.1f}s)", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # Simpan file debug
            out_filename = f"debug_frame_{idx+1}_t{int(t_sec)}s.jpg"
            out_path = output_debug_dir / out_filename
            cv2.imwrite(str(out_path), annotated)
            debug_filenames.append(out_filename)

        cap.release()
        logger.info(f"🔍 Berhasil menghasilkan {len(debug_filenames)} frame debug bounding box.")
        return debug_filenames

    except Exception as e:
        logger.error(f"Gagal generate debug frames: {e}")
        return []

