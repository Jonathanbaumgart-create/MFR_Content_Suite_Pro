from pathlib import Path
import json
import math

from PIL import Image

from media.image_dimensions import ImageDimensions
from services.logging_service import LoggingService


logger = LoggingService.get_logger("application")


class VideoMetadataService:

    VIDEO_EXTENSIONS = {
        ".mp4",
        ".mov",
        ".m4v",
        ".avi",
        ".mkv",
        ".wmv"
    }

    DEFAULT_THUMBNAIL_SIZE = 420
    DEFAULT_KEYFRAME_COUNT = 5

    def is_video(self, path):

        return Path(path).suffix.lower() in self.VIDEO_EXTENSIONS

    ############################################################

    def inspect(self, path):

        path = Path(path)
        metadata = self._base_metadata(path)

        if not self.is_video(path):
            metadata["error"] = "Unsupported video extension"
            return metadata

        cap = None

        try:
            import cv2

            cap = cv2.VideoCapture(str(path))

            if not cap.isOpened():
                metadata["error"] = "Unable to open video"
                return metadata

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            frame_rate = float(cap.get(cv2.CAP_PROP_FPS) or 0)
            duration = (
                frame_count / frame_rate
                if frame_count > 0 and frame_rate > 0
                else 0
            )

            metadata.update(
                {
                    "width": width,
                    "height": height,
                    "frame_rate": round(frame_rate, 3),
                    "duration": round(duration, 3),
                    "frame_count": frame_count,
                    "orientation": self._orientation(width, height),
                    "thumbnail_status": "pending"
                }
            )

            metadata.update(
                self._mediainfo(path)
            )

            return metadata

        except Exception as ex:
            metadata["error"] = str(ex)
            logger.warning(
                "Video metadata inspection failed path=%s error=%s",
                path,
                ex
            )
            return metadata

        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

    ############################################################

    def create_thumbnail(self, path, thumbnail_path, size=None):

        size = int(size or self.DEFAULT_THUMBNAIL_SIZE)
        frame = self.representative_frame(path)

        if frame is None:
            return False

        image, _timestamp = frame

        try:
            image = image.convert("RGB")
            image.thumbnail(
                (size, size),
                Image.Resampling.LANCZOS
            )
            thumbnail_path = Path(thumbnail_path)
            thumbnail_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )
            image.save(
                thumbnail_path,
                format="JPEG",
                quality=92,
                optimize=True,
                subsampling=0
            )
            return True

        except Exception as ex:
            logger.warning(
                "Video thumbnail save failed path=%s error=%s",
                path,
                ex
            )
            return False

    ############################################################

    def representative_frame(self, path):

        metadata = self.inspect(path)
        duration = float(metadata.get("duration") or 0)
        candidates = []

        if duration > 0:
            candidates.extend(
                [
                    duration * 0.10,
                    duration * 0.50,
                    min(duration * 0.90, max(0, duration - 0.25))
                ]
            )

        candidates.append(0)

        for timestamp in self._unique_timestamps(candidates):
            frame = self.read_frame(path, timestamp)

            if frame is None:
                continue

            image, actual = frame

            if not self._mostly_black(image):
                return image, actual

        return None

    ############################################################

    def keyframes(self, path, max_frames=None):

        max_frames = int(max_frames or self.DEFAULT_KEYFRAME_COUNT)
        metadata = self.inspect(path)
        duration = float(metadata.get("duration") or 0)

        if duration <= 0:
            timestamps = [0]
        else:
            timestamps = [
                0,
                duration * 0.25,
                duration * 0.50,
                duration * 0.75,
                max(0, duration - 0.25)
            ]

        frames = []
        fingerprints = set()

        for timestamp in self._unique_timestamps(timestamps):

            if len(frames) >= max_frames:
                break

            frame = self.read_frame(path, timestamp)

            if frame is None:
                continue

            image, actual = frame
            fingerprint = self._fingerprint(image)

            if fingerprint in fingerprints:
                continue

            fingerprints.add(fingerprint)
            frames.append(
                {
                    "timestamp": round(actual, 3),
                    "image": image,
                    "size": image.size
                }
            )

        return frames

    ############################################################

    def read_frame(self, path, timestamp):

        cap = None

        try:
            import cv2

            cap = cv2.VideoCapture(str(path))

            if not cap.isOpened():
                return None

            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            target_index = 0

            if fps > 0:
                target_index = int(max(0, timestamp) * fps)

            if frame_count > 0:
                target_index = min(
                    target_index,
                    max(0, frame_count - 1)
                )

            cap.set(
                cv2.CAP_PROP_POS_FRAMES,
                target_index
            )
            ok, frame = cap.read()

            if not ok or frame is None:
                return None

            frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )
            image = Image.fromarray(frame)
            actual = target_index / fps if fps > 0 else float(timestamp or 0)
            return image.copy(), actual

        except Exception as ex:
            logger.warning(
                "Video frame read failed path=%s timestamp=%s error=%s",
                path,
                timestamp,
                ex
            )
            return None

        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

    ############################################################

    def video_analysis_from_metadata(self, media_id, path, metadata=None):

        metadata = metadata or self.inspect(path)
        duration = float(metadata.get("duration") or 0)
        orientation = metadata.get("orientation") or "unknown"
        dimensions = self._dimensions_text(metadata)
        keyframes = self.keyframes(path)
        timestamps = [
            frame["timestamp"]
            for frame in keyframes
        ]

        description = (
            "Video media stored for bounded review. "
            f"Duration {self._duration_text(duration)}, "
            f"{orientation} orientation, {dimensions}. "
            "No temporal activity is inferred until reviewed."
        )

        analysis = {
            "media_id": media_id,
            "description": description,
            "scene_type": "video_metadata",
            "activity": "requires_review",
            "people_count": 0,
            "apparatus": [],
            "equipment": [],
            "keywords": [
                "video",
                "metadata",
                orientation,
                "requires_review"
            ],
            "community_score": 25,
            "recruitment_score": 15,
            "education_score": 15,
            "technical_score": 10,
            "overall_score": 25,
            "facebook_caption": "",
            "instagram_caption": "",
            "model": "video-metadata-stage1",
            "analysis_duration": 0,
            "provider": "video_metadata",
            "retry_count": 0,
            "failure_reason": "",
            "raw_response": json.dumps(
                {
                    "metadata": metadata,
                    "keyframe_timestamps": timestamps
                }
            ),
            "parse_status": "metadata_only",
            "parse_warnings": [
                "Video analysis is metadata-only until human review or bounded frame analysis."
            ],
            "confidence": 0.45,
            "people": [],
            "activities": [],
            "setting": "unknown",
            "indoor_outdoor": "unknown",
            "safety_concerns": [],
            "public_use_risks": [
                "Review footage manually before publication."
            ],
            "visible_text": [],
            "uncertain_observations": [
                "No full temporal video understanding has been performed."
            ],
            "structured_field_completeness": 0.4,
            "request_metadata": metadata,
            "preprocessing_metadata": {
                "stage": "video_stage1_metadata",
                "bounded_keyframes": len(keyframes),
                "keyframe_timestamps": timestamps
            },
            "provider_attempts": [],
            "provider_response_excerpt": "",
            "provider_status_code": 0,
            "prompt_version": "video_stage1",
            "analysis_version": "video_stage1",
            "quality_state": "review_required",
            "trust_state": "unreviewed_real",
            "review_status": "review_required",
            "quality_warnings": [
                "Metadata-only video intelligence requires human review."
            ],
            "media_context": "video"
        }

        return analysis

    ############################################################

    def _base_metadata(self, path):

        try:
            stat = path.stat()
            size = stat.st_size
            created = stat.st_ctime
            modified = stat.st_mtime
        except Exception:
            size = 0
            created = 0
            modified = 0

        return {
            "media_type": "video",
            "path": str(path),
            "file_size": size,
            "created_timestamp": created,
            "modified_timestamp": modified,
            "duration": 0,
            "width": 0,
            "height": 0,
            "frame_rate": 0,
            "orientation": "unknown",
            "codec": "",
            "thumbnail_status": "unavailable"
        }

    ############################################################

    def _mediainfo(self, path):

        try:
            from pymediainfo import MediaInfo

            info = MediaInfo.parse(str(path))

            for track in info.tracks:

                if track.track_type != "Video":
                    continue

                codec = (
                    getattr(track, "codec", None) or
                    getattr(track, "format", None) or
                    ""
                )
                duration_ms = getattr(track, "duration", None)
                extras = {
                    "codec": codec,
                    "capture_time": (
                        getattr(track, "encoded_date", None) or
                        getattr(track, "tagged_date", None) or
                        ""
                    )
                }

                if duration_ms:
                    extras["duration"] = round(float(duration_ms) / 1000, 3)

                return extras

        except Exception:
            return {}

        return {}

    ############################################################

    def _orientation(self, width, height):

        if width <= 0 or height <= 0:
            return "unknown"

        if width == height:
            return "square"

        if width > height:
            return "landscape"

        return "portrait"

    ############################################################

    def _mostly_black(self, image):

        try:
            sample_size = ImageDimensions.fit_size(
                image.size,
                (32, 32),
                allow_upscale=False
            )
            sample = image.resize(sample_size)
            pixels = list(sample.convert("L").getdata())
            average = sum(pixels) / max(1, len(pixels))
            return average < 8
        except Exception:
            return False

    ############################################################

    def _fingerprint(self, image):

        try:
            small = image.resize((8, 8)).convert("L")
            pixels = list(small.getdata())
            average = sum(pixels) / len(pixels)
            return "".join(
                "1" if pixel > average else "0"
                for pixel in pixels
            )
        except Exception:
            return ""

    ############################################################

    def _unique_timestamps(self, timestamps):

        seen = set()

        for value in timestamps:
            try:
                value = max(0, float(value))
            except Exception:
                value = 0

            rounded = round(value, 3)

            if rounded in seen:
                continue

            seen.add(rounded)
            yield rounded

    ############################################################

    def _duration_text(self, duration):

        if duration <= 0:
            return "unknown"

        minutes = int(duration // 60)
        seconds = int(math.floor(duration % 60))

        if minutes:
            return f"{minutes}:{seconds:02d}"

        return f"{seconds}s"

    ############################################################

    def _dimensions_text(self, metadata):

        width = int(metadata.get("width") or 0)
        height = int(metadata.get("height") or 0)

        if width and height:
            return f"{width}x{height}"

        return "dimensions unknown"
