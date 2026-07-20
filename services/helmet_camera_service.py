from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
import time

from PIL import Image, ImageDraw

from core.app_context import context
from services.logging_service import LoggingService
from services.time_service import TimeService
from services.video_metadata_service import VideoMetadataService


logger = LoggingService.get_logger("intelligence")


class HelmetCameraService:

    SOURCE_IDENTITY = "Helmet Camera"
    DEFAULT_ROOT = r"E:\Jonathan\Videos\Helmet Cam"
    ANALYSIS_VERSION = "helmet-camera-technical-v1"
    MAX_SEGMENTS = 10
    DISPLAY_SEGMENTS = 3
    SOURCE_ROTATION_DEFAULTS = {
        str(Path(DEFAULT_ROOT)).lower(): 180
    }

    def __init__(self, database=None, metadata_service=None):

        self.db = database or context.database
        self.video = metadata_service or VideoMetadataService()

    ############################################################

    def source_status(self, root_path=None):

        root = Path(root_path or self.DEFAULT_ROOT)
        available = root.exists() and root.is_dir()
        rows = []

        if available:
            rows = self.db.media_rows_under_path(
                str(root),
                limit=5000
            )

        source = {
            "root_path": str(root),
            "source_identity": self.SOURCE_IDENTITY,
            "available": available,
            "last_scanned_at": TimeService.utc_now_iso(),
            "media_count": len(rows),
            "notes": (
                "Helmet camera source available."
                if available
                else "Helmet camera drive or folder is unavailable."
            )
        }
        self.db.save_helmet_camera_source(source)
        return source

    ############################################################

    def scan_source(self, root_path=None, progress_callback=None):

        root = Path(root_path or self.DEFAULT_ROOT)

        if not root.exists() or not root.is_dir():
            source = self.source_status(str(root))
            return {
                "available": False,
                "source": source,
                "inserted": 0,
                "processed": 0,
                "message": source["notes"]
            }

        processed = 0
        inserted = 0
        duplicates = 0
        failed = 0

        for path in self._video_files(root):
            processed += 1

            try:
                was_inserted = self.db.add_media({
                    "filename": path.name,
                    "path": str(path),
                    "extension": path.suffix.lower(),
                    "type": "video",
                    "size": path.stat().st_size,
                    "sha256": self._source_identity(path),
                    "duration_seconds": 0,
                    "width": 0,
                    "height": 0,
                    "frame_rate": 0,
                    "orientation": "",
                    "codec": "",
                    "thumbnail_status": "metadata_pending"
                })
                if was_inserted:
                    inserted += 1
                else:
                    duplicates += 1
            except Exception as ex:
                failed += 1
                logger.warning(
                    "Helmet camera index failed path=%s error=%s",
                    path,
                    ex
                )

            if progress_callback:
                progress_callback(processed, 0)

        source = self.source_status(str(root))
        return {
            "available": True,
            "source": source,
            "processed": processed,
            "inserted": inserted,
            "duplicates": duplicates,
            "failed": failed,
            "skipped": 0,
            "provider_calls": 0
        }

    ############################################################

    def helmet_videos(self, root_path=None, limit=200):

        root = root_path or self.DEFAULT_ROOT
        return [
            row for row in self.db.media_rows_under_path(root, limit=limit)
            if row.get("media_type") == "video"
        ]

    ############################################################

    def analyze_video(self, media_id, video_path=None):

        started = time.perf_counter()
        media = self.db.get_media_details(media_id) or {}
        path = video_path or media.get("path", "")
        metadata = self.video.inspect(path)
        rotation = self.effective_rotation(path, metadata)
        metadata["effective_display_rotation"] = rotation
        try:
            self.db.update_media_video_metadata(media_id, metadata)
        except Exception:
            pass
        samples = self._sample_technical_frames(path, metadata, rotation)
        segments = self._candidate_segments(media_id, path, metadata, samples)
        self.db.save_helmet_camera_segments(media_id, segments)

        result = {
            "media_id": media_id,
            "filename": media.get("filename", Path(path).name),
            "path": path,
            "source_identity": self.SOURCE_IDENTITY,
            "metadata": metadata,
            "sample_count": len(samples),
            "candidate_count": len(segments),
            "top_segments": segments[:self.DISPLAY_SEGMENTS],
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "provider_calls": 0,
            "analysis_version": self.ANALYSIS_VERSION,
            "source_preserved": True,
            "permanent_frames_stored": False
        }
        logger.info(
            "Helmet camera technical pass media_id=%s segments=%s elapsed=%s",
            media_id,
            len(segments),
            result["elapsed_seconds"]
        )
        return result

    ############################################################

    def create_contact_sheet(self, video_path, segment, max_frames=4, size=(640, 360)):

        start = float(segment.get("start_seconds") or 0)
        end = float(segment.get("end_seconds") or start)
        rotation = self.effective_rotation(video_path)
        duration = max(0.1, end - start)
        timestamps = [
            start + (duration * fraction)
            for fraction in (0.10, 0.35, 0.65, 0.90)
        ][:int(max_frames or 4)]
        frames = []

        for timestamp in timestamps:
            frame = self.video.read_frame(video_path, timestamp)
            if not frame:
                continue
            image, actual = frame
            image = self.apply_rotation(image, rotation)
            image.thumbnail(size, Image.Resampling.LANCZOS)
            frames.append((image.copy(), actual))

        if not frames:
            return None

        width = max(image.width for image, _actual in frames)
        height = max(image.height for image, _actual in frames)
        sheet = Image.new("RGB", (width * len(frames), height + 28), "#111111")
        draw = ImageDraw.Draw(sheet)

        for index, (image, actual) in enumerate(frames):
            x = index * width
            sheet.paste(image.convert("RGB"), (x, 0))
            draw.text((x + 8, height + 6), self._timecode(actual), fill="#ffffff")

        return sheet

    ############################################################

    def create_preview_clip(self, source_path, segment, output_dir=None):

        source = Path(source_path)
        output = Path(output_dir or tempfile.gettempdir()) / "mfr_helmet_preview"
        output.mkdir(parents=True, exist_ok=True)
        start = float(segment.get("start_seconds") or 0)
        end = float(segment.get("end_seconds") or start)
        duration = max(0.1, end - start)
        rotation = self.effective_rotation(source_path)
        target = output / (
            f"preview_{source.stem}_{int(start):04d}_{int(end):04d}.mp4"
        )
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(round(start, 3)),
            "-i",
            str(source),
            "-t",
            str(round(duration, 3)),
            "-vf",
            self.ffmpeg_rotation_filter(rotation),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            str(target)
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120,
                check=False
            )
            return {
                "success": completed.returncode == 0,
                "preview_path": str(target),
                "temporary": True,
                "source_preserved": True,
                "rotation": rotation,
                "start_seconds": start,
                "end_seconds": end,
                "stderr": completed.stderr[-1000:]
            }
        except FileNotFoundError:
            return self._create_cv2_preview_clip(
                source,
                target,
                start,
                duration,
                rotation,
                "FFmpeg is not available on PATH; used OpenCV silent preview fallback."
            )

    ############################################################

    def semantic_screen_segments(self, media_id, segments=None, limit=5):

        selected = list(segments or self.db.helmet_camera_segments(media_id, limit=limit))[:limit]
        screened = []

        for segment in selected:
            enriched = dict(segment)
            enriched.update(self._semantic_profile(enriched))
            screened.append(enriched)

        return screened

    ############################################################

    def export_segment(
        self,
        source_path,
        segment,
        output_dir="exports/helmet_cam",
        preserve_audio=True
    ):

        source = Path(source_path)
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        start = float(segment.get("start_seconds") or 0)
        end = float(segment.get("end_seconds") or start)
        duration = max(0.1, end - start)
        target = output / (
            f"{source.stem}_{int(start):04d}_{int(end):04d}{source.suffix}"
        )
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(round(start, 3)),
            "-i",
            str(source),
            "-t",
            str(round(duration, 3)),
            "-vf",
            self.ffmpeg_rotation_filter(
                self.effective_rotation(source_path)
            ),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            str(target)
        ]
        if preserve_audio:
            command[-1:-1] = ["-c:a", "aac"]
        else:
            command[-1:-1] = ["-an"]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120,
                check=False
            )
            return {
                "success": completed.returncode == 0,
                "output_path": str(target),
                "source_path": str(source),
                "start_seconds": start,
                "end_seconds": end,
                "source_preserved": True,
                "stderr": completed.stderr[-1000:]
            }
        except FileNotFoundError:
            return {
                "success": False,
                "output_path": "",
                "source_path": str(source),
                "source_preserved": True,
                "stderr": "FFmpeg is not available on PATH."
            }

    ############################################################

    def reel_package(self, media_id, segment):

        media = self.db.get_media_details(media_id) or {}
        risks = segment.get("risk_flags") or []
        profile = self._semantic_profile(segment)
        activity = profile.get("visible_activity_summary", "a short operational moment")
        caption = (
            f"A firefighter's-eye view of {activity.lower()}. "
            "Training and readiness are built one practical task at a time."
        )

        return {
            "media_id": media_id,
            "filename": media.get("filename", ""),
            "source_path": media.get("path", ""),
            "clip_start": segment.get("start_seconds", 0),
            "clip_end": segment.get("end_seconds", 0),
            "cover_frame_seconds": segment.get("cover_frame_seconds", 0),
            "instagram_reel_caption": caption,
            "facebook_reel_caption": caption,
            "hook_text": profile.get("suggested_hook", "A look from the helmet camera."),
            "on_screen_text_plan": [
                profile.get("suggested_hook", "Helmet camera view"),
                profile.get("recommended_tone", "Behind-the-scenes"),
                "Morden"
            ],
            "accessibility_description": segment.get("visual_summary", ""),
            "trimming_notes": profile.get("suggested_adjustment", segment.get("reason_selected", "")),
            "risk_warnings": risks,
            "recommended_music_mood": profile.get("music_mood", "steady, upbeat, non-lyrical"),
            "posting_angle": profile.get("recommended_caption_angle", ""),
            "target_audience": profile.get("best_audience", ""),
            "content_family": profile.get("classification", ""),
            "orientation_correction": self.effective_rotation(media.get("path", "")),
            "review_required": True,
            "publication_draft": {
                "status": "draft",
                "automatic_publish": False
            }
        }

    ############################################################

    def _sample_technical_frames(self, path, metadata, rotation=0):

        duration = float(metadata.get("duration") or 0)

        if duration <= 0:
            return []

        interval = 5.0 if duration <= 360 else 10.0
        timestamps = []
        current = 0.0

        while current < duration:
            timestamps.append(round(current, 3))
            current += interval

        samples = []
        previous = None

        for timestamp in timestamps:
            frame = self.video.read_frame(path, timestamp)
            if not frame:
                continue
            image, actual = frame
            image = self.apply_rotation(image, rotation)
            metrics = self._frame_metrics(image, previous)
            metrics["timestamp"] = round(actual, 3)
            samples.append(metrics)
            previous = image

        return samples

    def _video_files(self, root):

        extensions = VideoMetadataService.VIDEO_EXTENSIONS

        for path in Path(root).rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in extensions:
                yield path

    def _source_identity(self, path):

        try:
            stat = path.stat()
            source = f"helmet|{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
        except Exception:
            source = f"helmet|{path}"

        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def _frame_metrics(self, image, previous=None):

        try:
            import cv2
            import numpy as np

            array = np.array(image.convert("RGB"))
            gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
            brightness = float(gray.mean())
            blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            black_ratio = float((gray < 18).sum()) / float(gray.size or 1)
            motion = 0.0

            if previous is not None:
                previous_gray = cv2.cvtColor(
                    np.array(previous.convert("RGB")),
                    cv2.COLOR_RGB2GRAY
                )
                motion = float(cv2.absdiff(gray, previous_gray).mean())

            return {
                "brightness": round(brightness, 3),
                "blur": round(blur, 3),
                "black_ratio": round(black_ratio, 4),
                "motion": round(motion, 3)
            }
        except Exception:
            return {
                "brightness": 0,
                "blur": 0,
                "black_ratio": 0,
                "motion": 0
            }

    def _candidate_segments(self, media_id, path, metadata, samples):

        duration = float(metadata.get("duration") or 0)

        if duration <= 0:
            return []

        ranked = []

        for sample in samples:
            center = float(sample.get("timestamp") or 0)
            start = max(0, center - 6)
            end = min(duration, start + 16)
            if end - start < 6:
                start = max(0, end - 8)

            motion_score = min(100, int(float(sample.get("motion") or 0) * 4))
            clarity_score = min(100, int(float(sample.get("blur") or 0) / 8))
            brightness = float(sample.get("brightness") or 0)
            exposure_score = max(0, 100 - int(abs(115 - brightness)))
            black_ratio = float(sample.get("black_ratio") or 0)
            obstruction_penalty = int(black_ratio * 100)
            semantic = self._semantic_scores(
                motion_score,
                clarity_score,
                exposure_score,
                black_ratio,
                center,
                duration
            )
            technical = max(
                0,
                int(
                    motion_score * 0.35 +
                    clarity_score * 0.30 +
                    exposure_score * 0.25 +
                    10 -
                    obstruction_penalty
                )
            )
            risks = self._risk_flags(sample)
            severe_risks = [
                risk for risk in risks
                if risk in (
                    "mostly_black_or_obstructed",
                    "privacy_or_sensitivity_review_required"
                )
            ]
            risk_penalty = 35 if severe_risks else 8 if risks else 0
            reel_score = max(
                0,
                min(
                    100,
                    int(
                        technical * 0.42 +
                        semantic["action_hook"] * 0.16 +
                        semantic["story_coherence"] * 0.13 +
                        semantic["public_interest"] * 0.11 +
                        semantic["behind_the_scenes"] * 0.10 +
                        semantic["human_team_value"] * 0.08 -
                        risk_penalty
                    )
                )
            )
            profile = self._semantic_profile({
                **semantic,
                "reel_score": reel_score,
                "motion_score": motion_score,
                "clarity_score": clarity_score,
                "exposure_score": exposure_score,
                "risk_flags": risks,
                "start_seconds": start,
                "end_seconds": end
            })

            ranked.append({
                "media_id": media_id,
                "source_path": path,
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "duration_seconds": round(end - start, 3),
                "reel_score": reel_score,
                "technical_score": technical,
                "motion_score": motion_score,
                "clarity_score": clarity_score,
                "exposure_score": exposure_score,
                "audio_score": 0,
                "risk_level": (
                    "manual_review"
                    if severe_risks
                    else "quality_review" if risks else "low"
                ),
                "risk_flags": risks,
                "reason_selected": profile.get("why_this_clip_works", ""),
                "visual_summary": profile.get("visible_activity_summary", ""),
                "cover_frame_seconds": round(center, 3),
                "status": "manual_review_only" if severe_risks else "candidate",
                "analysis_version": self.ANALYSIS_VERSION,
                "generated_at": TimeService.utc_now_iso()
            })

        ranked.sort(
            key=lambda item: (
                item["reel_score"],
                item["technical_score"],
                -item["start_seconds"]
            ),
            reverse=True
        )
        return self._dedupe_segments(ranked)[:self.MAX_SEGMENTS]

    def _dedupe_segments(self, segments):

        selected = []

        for segment in segments:
            start = float(segment.get("start_seconds") or 0)
            if any(abs(start - float(item.get("start_seconds") or 0)) < 8 for item in selected):
                continue
            selected.append(segment)

        return selected

    def _risk_flags(self, sample):

        flags = []

        if float(sample.get("black_ratio") or 0) > 0.65:
            flags.append("mostly_black_or_obstructed")

        if float(sample.get("blur") or 0) < 35:
            flags.append("quality_review_blur_or_unstable")

        return flags

    def _reason(self, motion, clarity, exposure, risks):

        parts = []

        if motion >= 35:
            parts.append("motion/activity peak")
        if clarity >= 45:
            parts.append("usable clarity")
        if exposure >= 55:
            parts.append("usable exposure")
        if risks:
            severe = any(
                risk in (
                    "mostly_black_or_obstructed",
                    "privacy_or_sensitivity_review_required"
                )
                for risk in risks
            )
            parts.append(
                "manual review required due to sensitivity risk"
                if severe
                else "quality review recommended for stability or trim"
            )

        return ", ".join(parts) or "bounded technical candidate"

    ############################################################

    def effective_rotation(self, path, metadata=None, override=None):

        if override is not None:
            return self._normalize_rotation(override)

        metadata = metadata or {}
        for key in ("rotation", "display_rotation", "effective_display_rotation"):
            if metadata.get(key) is not None:
                return self._normalize_rotation(metadata.get(key))

        text = str(path or "").lower()
        for root, rotation in self.SOURCE_ROTATION_DEFAULTS.items():
            if text.startswith(root):
                return self._normalize_rotation(rotation)

        return 0

    def apply_rotation(self, image, rotation):

        rotation = self._normalize_rotation(rotation)

        if rotation == 90:
            return image.rotate(-90, expand=True)
        if rotation == 180:
            return image.rotate(180, expand=True)
        if rotation == 270:
            return image.rotate(90, expand=True)

        return image

    def ffmpeg_rotation_filter(self, rotation):

        rotation = self._normalize_rotation(rotation)

        if rotation == 90:
            return "transpose=1,scale='min(960,iw)':-2"
        if rotation == 180:
            return "hflip,vflip,scale='min(960,iw)':-2"
        if rotation == 270:
            return "transpose=2,scale='min(960,iw)':-2"

        return "scale='min(960,iw)':-2"

    def _create_cv2_preview_clip(
        self,
        source,
        target,
        start,
        duration,
        rotation,
        note
    ):

        cap = None
        writer = None

        try:
            import cv2
            import numpy as np

            cap = cv2.VideoCapture(str(source))
            if not cap.isOpened():
                return {
                    "success": False,
                    "preview_path": "",
                    "temporary": True,
                    "source_preserved": True,
                    "rotation": rotation,
                    "stderr": "Unable to open source video for preview fallback."
                }

            fps = float(cap.get(cv2.CAP_PROP_FPS) or 15)
            fps = max(1, min(30, fps))
            frame_count = int(duration * fps)
            start_frame = int(max(0, start) * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            first = True

            for _index in range(frame_count):
                ok, frame = cap.read()
                if not ok or frame is None:
                    break

                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image = self.apply_rotation(image, rotation)
                image.thumbnail((960, 540), Image.Resampling.LANCZOS)
                array = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)

                if first:
                    target = target.with_suffix(".mp4")
                    writer = cv2.VideoWriter(
                        str(target),
                        cv2.VideoWriter_fourcc(*"mp4v"),
                        fps,
                        (array.shape[1], array.shape[0])
                    )
                    first = False

                writer.write(array)

            if writer is not None:
                writer.release()
                writer = None

            success = Path(target).exists() and Path(target).stat().st_size > 0
            return {
                "success": success,
                "preview_path": str(target) if success else "",
                "temporary": True,
                "source_preserved": True,
                "rotation": rotation,
                "audio_preserved": False,
                "stderr": note
            }

        except Exception as ex:
            return {
                "success": False,
                "preview_path": "",
                "temporary": True,
                "source_preserved": True,
                "rotation": rotation,
                "stderr": str(ex)
            }

        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            if writer is not None:
                try:
                    writer.release()
                except Exception:
                    pass

    def _normalize_rotation(self, value):

        try:
            value = int(float(value or 0))
        except Exception:
            value = 0

        value = value % 360
        if value in (0, 90, 180, 270):
            return value

        return min((0, 90, 180, 270), key=lambda item: abs(item - value))

    def _semantic_scores(self, motion, clarity, exposure, black_ratio, center, duration):

        action = min(100, max(20, int(motion * 1.3)))
        clarity_value = min(100, max(10, clarity))
        story = min(100, max(25, int((action + clarity_value + exposure) / 3)))
        public = min(100, max(20, int(story * 0.75 + action * 0.25)))
        behind = min(100, max(35, int(55 + min(25, motion / 2))))
        team = min(100, max(30, int(50 + min(30, motion / 2))))
        educational = min(100, max(25, int((clarity_value + exposure) / 2)))
        personality = 45 if black_ratio < 0.35 and clarity_value > 25 else 20
        payoff = 70 if center > duration * 0.20 and center < duration * 0.90 else 45

        return {
            "action_hook": action,
            "visual_clarity": clarity_value,
            "story_coherence": story,
            "operational_interest": max(action, educational),
            "public_interest": public,
            "fire_service_interest": max(action, story),
            "human_team_value": team,
            "behind_the_scenes": behind,
            "light_hearted_personality": personality,
            "educational_value": educational,
            "audio_value": 35,
            "ending_payoff": payoff,
            "uniqueness": max(35, min(90, action + 10)),
            "privacy_risk": 35 if black_ratio < 0.10 and clarity_value > 70 else 15,
            "sensitivity_risk": 20,
            "repetition_risk": 10
        }

    def _semantic_profile(self, segment):

        risks = segment.get("risk_flags") or []
        score = int(segment.get("reel_score") or 0)
        action = int(segment.get("action_hook") or segment.get("motion_score") or 0)
        behind = int(segment.get("behind_the_scenes") or 0)
        personality = int(segment.get("light_hearted_personality") or 0)
        educational = int(segment.get("educational_value") or segment.get("exposure_score") or 0)

        severe_risks = [
            risk for risk in risks
            if risk in (
                "mostly_black_or_obstructed",
                "privacy_or_sensitivity_review_required"
            )
        ]

        if severe_risks:
            classification = "Manual Review Only"
        elif action >= 55:
            classification = "Strong Reel Candidate" if score >= 70 else "Good Operational Clip"
        elif personality >= 45:
            classification = "Good Light-Hearted Clip"
        elif behind >= educational:
            classification = "Good Behind-the-Scenes Clip"
        elif educational >= 55:
            classification = "Educational Clip"
        else:
            classification = "Weak Candidate" if score < 35 else "Good Behind-the-Scenes Clip"

        tone = {
            "Strong Reel Candidate": "Action-focused",
            "Good Operational Clip": "Action-focused",
            "Good Behind-the-Scenes Clip": "Behind-the-scenes",
            "Good Light-Hearted Clip": "Light-hearted",
            "Educational Clip": "Educational",
            "Manual Review Only": "Professional",
            "Weak Candidate": "Behind-the-scenes"
        }.get(classification, "Behind-the-scenes")

        summary = self._activity_summary(classification, action, educational)
        why_not = (
            "Manual review is required before public use."
            if risks
            else "The clip may need trimming if the action does not start quickly."
        )

        return {
            "overall_reel_potential": score,
            "classification": classification,
            "visible_activity_summary": summary,
            "recommended_tone": tone,
            "suggested_hook": self._suggested_hook(classification),
            "strongest_reason": self._reason(
                segment.get("motion_score", 0),
                segment.get("clarity_score", 0),
                segment.get("exposure_score", 0),
                risks
            ),
            "why_this_clip_works": (
                f"{classification}: {summary} The segment has bounded evidence "
                "for action, preparation, or behind-the-scenes value."
            ),
            "why_it_may_not_work": why_not,
            "suggested_adjustment": "Trim to the first clear action and end before the pace drops.",
            "recommended_caption_angle": f"{tone} look at practical MFR readiness.",
            "best_audience": "Morden residents and MFR followers",
            "music_mood": "steady, upbeat, non-lyrical"
        }

    def _activity_summary(self, classification, action, educational):

        if classification in ("Strong Reel Candidate", "Good Operational Clip"):
            return "helmet-camera action with movement, task focus, and operational rhythm"
        if classification == "Good Light-Hearted Clip":
            return "a lighter behind-the-scenes moment that may show team personality"
        if classification == "Educational Clip" or educational >= 55:
            return "a short process or training moment that can support public education"

        return "behind-the-scenes preparation and routine fire-service work"

    def _suggested_hook(self, classification):

        if classification in ("Strong Reel Candidate", "Good Operational Clip"):
            return "A firefighter's-eye view."
        if classification == "Good Light-Hearted Clip":
            return "A lighter moment behind the scenes."
        if classification == "Educational Clip":
            return "A quick look at the process."

        return "Behind the scenes at MFR."

    def _timecode(self, seconds):

        seconds = int(float(seconds or 0))
        minutes = seconds // 60
        remainder = seconds % 60
        return f"{minutes}:{remainder:02d}"
