import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from services.ai_service import AIService
from services.logging_service import LoggingService
from services.time_service import TimeService
from services.video_metadata_service import VideoMetadataService


logger = LoggingService.get_logger("intelligence")


@dataclass
class VideoIntelligence:

    media_id: int = 0
    video_summary: str = ""
    primary_activity: str = "unknown"
    secondary_activity: str = "unknown"
    estimated_scene_count: int = 0
    representative_frames: list = field(default_factory=list)
    identified_apparatus: list = field(default_factory=list)
    identified_ppe: list = field(default_factory=list)
    identified_tools: list = field(default_factory=list)
    training_evolution: str = ""
    incident_category: str = "unknown"
    program: str = ""
    campaign: str = ""
    community_event: str = ""
    estimated_audience: list = field(default_factory=list)
    communications_themes: list = field(default_factory=list)
    story_potential: int = 0
    education_score: int = 0
    recruitment_score: int = 0
    community_score: int = 0
    operations_score: int = 0
    reel_potential: int = 0
    reel_explanation: str = ""
    clip_recommendations: list = field(default_factory=list)
    cover_recommendation: dict = field(default_factory=dict)
    story_category: str = "Unknown"
    trust_state: str = "unreviewed_real"
    confidence: float = 0
    review_state: str = "review_required"
    explanation: str = ""
    analysis_version: str = "video-intelligence-v1"
    generated_at: str = ""

    def to_dict(self):

        return asdict(self)


class VideoIntelligenceService:

    ANALYSIS_VERSION = "video-intelligence-v1"
    SHORT_VIDEO_SECONDS = 30
    DEFAULT_LONG_INTERVAL_SECONDS = 12
    DEFAULT_MAX_FRAMES = 5
    DEFAULT_MAX_ANALYZED_FRAMES = 3

    PPE_TERMS = {
        "helmet",
        "turnout gear",
        "scba",
        "gloves",
        "hood",
        "ppe",
        "high visibility vest",
        "eye protection"
    }
    EQUIPMENT_TERMS = {
        "hose",
        "ladder",
        "nozzle",
        "hydrant",
        "pump",
        "fan",
        "thermal camera",
        "medical bag",
        "rope",
        "rescue equipment",
        "extrication"
    }
    APPARATUS_TERMS = {
        "engine",
        "pumper",
        "rescue",
        "ladder",
        "tanker",
        "command",
        "utility",
        "brush truck",
        "ambulance"
    }

    def __init__(
        self,
        database=None,
        ai_service=None,
        vision_service=None,
        metadata_service=None,
        filesystem_service=None,
        config=None
    ):

        self.db = database
        self.ai = ai_service or AIService()
        self.vision = vision_service
        self.video = metadata_service or VideoMetadataService()
        self.filesystem = filesystem_service
        self.config = config or {}

    ############################################################

    def generate_and_save(
        self,
        media_id,
        video_path,
        metadata=None,
        effective_intelligence=None,
        analyze_frames=True
    ):

        result = self.generate(
            media_id,
            video_path,
            metadata=metadata,
            effective_intelligence=effective_intelligence,
            analyze_frames=analyze_frames
        )

        if self.db:
            self.db.save_video_intelligence(media_id, result)

        return result

    ############################################################

    def generate(
        self,
        media_id,
        video_path,
        metadata=None,
        effective_intelligence=None,
        analyze_frames=True
    ):

        started = time.perf_counter()
        metadata = metadata or self.video.inspect(video_path)
        duration = float(metadata.get("duration") or 0)
        timestamps = self.sample_timestamps(metadata)
        frames = self._read_sampled_frames(video_path, timestamps)
        observations = []

        if analyze_frames and self.vision and self.vision.provider_key() != "mock":
            observations = self._analyze_frames(
                frames[:self._max_analyzed_frames()],
                media_id
            )

        if not observations:
            observations = self._metadata_observations(metadata, frames)

        filesystem = self._filesystem_context(media_id)
        effective = effective_intelligence or self._effective(media_id)
        intelligence = self._build_intelligence(
            media_id,
            metadata,
            frames,
            observations,
            filesystem,
            effective
        )
        intelligence["analysis_duration"] = round(
            time.perf_counter() - started,
            3
        )

        logger.info(
            "Video intelligence generated media_id=%s frames=%s analyzed=%s reel=%s elapsed=%s",
            media_id,
            len(frames),
            len(observations),
            intelligence.get("reel_potential", 0),
            intelligence["analysis_duration"]
        )

        return intelligence

    ############################################################

    def sample_timestamps(self, metadata):

        duration = float(metadata.get("duration") or 0)

        if duration <= 0:
            return [0]

        if duration < self.SHORT_VIDEO_SECONDS:
            candidates = [
                0,
                duration * 0.20,
                duration * 0.40,
                duration * 0.60,
                duration * 0.80,
                max(0, duration - 0.10)
            ]
        else:
            interval = float(
                self.config.get(
                    "video_sample_interval_seconds",
                    self.DEFAULT_LONG_INTERVAL_SECONDS
                ) or self.DEFAULT_LONG_INTERVAL_SECONDS
            )
            candidates = [0]
            current = interval

            while current < duration:
                candidates.append(current)
                current += interval

            candidates.extend(
                [
                    duration * 0.33,
                    duration * 0.66,
                    max(0, duration - 0.10)
                ]
            )

        return self._bounded_unique_timestamps(
            candidates,
            duration,
            self._max_frames()
        )

    ############################################################

    def _read_sampled_frames(self, video_path, timestamps):

        frames = []
        previous_fingerprint = ""

        for timestamp in timestamps:
            frame = self.video.read_frame(video_path, timestamp)

            if frame is None:
                continue

            image, actual = frame
            fingerprint = self.video._fingerprint(image)
            scene_changed = bool(
                previous_fingerprint and fingerprint != previous_fingerprint
            )
            previous_fingerprint = fingerprint
            frames.append(
                {
                    "timestamp": round(float(actual), 3),
                    "position": self._position_label(actual, timestamps),
                    "size": image.size,
                    "scene_changed": scene_changed,
                    "fingerprint": fingerprint,
                    "image": image
                }
            )

        return frames

    ############################################################

    def _analyze_frames(self, frames, media_id):

        observations = []
        prompt_context = self._prompt_context(media_id)

        with tempfile.TemporaryDirectory() as temp_dir:
            for index, frame in enumerate(frames, start=1):
                frame_path = Path(temp_dir) / f"video_frame_{index:02d}.jpg"

                try:
                    frame["image"].save(
                        frame_path,
                        format="JPEG",
                        quality=90
                    )
                    context = (
                        "This is one representative frame sampled from a video. "
                        "Describe only visible evidence in this frame. "
                        f"Frame timestamp: {self._timecode(frame['timestamp'])}.\n"
                        + prompt_context
                    )
                    analysis = self.ai.analyze_image(
                        str(frame_path),
                        self.vision,
                        prompt_context=context
                    )
                    observations.append(
                        self._observation_from_analysis(frame, analysis)
                    )

                except Exception as ex:
                    observations.append(
                        {
                            "timestamp": frame["timestamp"],
                            "timecode": self._timecode(frame["timestamp"]),
                            "description": "",
                            "people_count": 0,
                            "apparatus": [],
                            "equipment": [],
                            "activities": [],
                            "setting": "",
                            "confidence": 0,
                            "failure": type(ex).__name__,
                            "failure_reason": str(ex)[:240]
                        }
                    )
                    logger.warning(
                        "Video frame analysis failed media_id=%s timestamp=%s error=%s",
                        media_id,
                        frame["timestamp"],
                        type(ex).__name__
                    )

        return observations

    ############################################################

    def _metadata_observations(self, metadata, frames):

        orientation = metadata.get("orientation") or "unknown"
        duration = float(metadata.get("duration") or 0)
        return [
            {
                "timestamp": frame.get("timestamp", 0),
                "timecode": self._timecode(frame.get("timestamp", 0)),
                "description": (
                    "Representative video frame sampled for bounded review."
                ),
                "people_count": 0,
                "apparatus": [],
                "equipment": [],
                "activities": ["requires_review"],
                "setting": orientation,
                "confidence": 0.35,
                "duration_seconds": duration
            }
            for frame in frames
        ] or [
            {
                "timestamp": 0,
                "timecode": "00:00",
                "description": "Video metadata available; no frame decoded.",
                "people_count": 0,
                "apparatus": [],
                "equipment": [],
                "activities": ["requires_review"],
                "setting": orientation,
                "confidence": 0.2
            }
        ]

    ############################################################

    def _build_intelligence(
        self,
        media_id,
        metadata,
        frames,
        observations,
        filesystem,
        effective
    ):

        values = self._merge_terms(observations, filesystem, effective)
        duration = float(metadata.get("duration") or 0)
        orientation = metadata.get("orientation") or "unknown"
        story_category = self._story_category(values, filesystem, effective)
        primary_activity = self._primary_activity(values, story_category)
        secondary_activity = self._secondary_activity(values, primary_activity)
        scene_count = max(
            1,
            len({frame.get("fingerprint") for frame in frames if frame.get("fingerprint")})
        )
        communications_themes = self._communications_themes(
            story_category,
            values,
            filesystem,
            effective
        )
        scores = self._scores(
            duration,
            orientation,
            story_category,
            values,
            frames,
            effective
        )
        cover = self._cover_recommendation(frames, observations, values)
        clips = self._clip_recommendations(duration, story_category, frames)
        confidence = self._confidence(observations, filesystem, effective)
        explanation = self._explanation(
            story_category,
            primary_activity,
            scores,
            confidence,
            filesystem
        )
        dto = VideoIntelligence(
            media_id=int(media_id or 0),
            video_summary=self._summary(story_category, primary_activity, duration),
            primary_activity=primary_activity,
            secondary_activity=secondary_activity,
            estimated_scene_count=scene_count,
            representative_frames=[
                {
                    "timestamp": frame.get("timestamp", 0),
                    "timecode": self._timecode(frame.get("timestamp", 0)),
                    "position": frame.get("position", ""),
                    "scene_changed": bool(frame.get("scene_changed"))
                }
                for frame in frames
            ],
            identified_apparatus=sorted(values["apparatus"]),
            identified_ppe=sorted(values["ppe"]),
            identified_tools=sorted(values["equipment"]),
            training_evolution=self._training_evolution(values),
            incident_category=self._incident_category(values, story_category),
            program=filesystem.get("public_education_program", ""),
            campaign=filesystem.get("campaign", ""),
            community_event=filesystem.get("community_event", ""),
            estimated_audience=self._audience(story_category, values),
            communications_themes=communications_themes,
            story_potential=scores["story_potential"],
            education_score=scores["education_score"],
            recruitment_score=scores["recruitment_score"],
            community_score=scores["community_score"],
            operations_score=scores["operations_score"],
            reel_potential=scores["reel_potential"],
            reel_explanation=scores["reel_explanation"],
            clip_recommendations=clips,
            cover_recommendation=cover,
            story_category=story_category,
            trust_state=effective.get("trust_state") or "unreviewed_real",
            confidence=confidence,
            review_state=effective.get("review_status") or "review_required",
            explanation=explanation,
            generated_at=TimeService.utc_now_iso()
        ).to_dict()
        dto.update(
            {
                "duration_seconds": duration,
                "analyzed_frame_count": len(observations),
                "frame_timestamps": [
                    frame.get("timestamp", 0)
                    for frame in frames
                ],
                "people_observed": sorted(values["people"]),
                "apparatus_observed": sorted(values["apparatus"]),
                "equipment_observed": sorted(values["equipment"]),
                "activities_observed": sorted(values["activities"]),
                "settings_observed": sorted(values["settings"]),
                "visible_text": sorted(values["visible_text"]),
                "uncertain_observations": sorted(values["uncertain"]),
                "likely_content_category": story_category,
                "provider": (
                    self.vision.provider_key()
                    if self.vision and hasattr(self.vision, "provider_key")
                    else "metadata"
                ),
                "model": (
                    self.vision.model_name()
                    if self.vision and hasattr(self.vision, "model_name")
                    else "video-intelligence-metadata"
                ),
                "analysis_version": self.ANALYSIS_VERSION,
                "raw_frame_outputs": self._safe_frame_outputs(observations)
            }
        )
        return dto

    ############################################################

    def _merge_terms(self, observations, filesystem, effective):

        values = {
            "people": set(),
            "apparatus": set(),
            "equipment": set(),
            "ppe": set(),
            "activities": set(),
            "settings": set(),
            "visible_text": set(),
            "uncertain": set(),
            "all": set()
        }

        for observation in observations:
            for key, target in (
                ("people", "people"),
                ("apparatus", "apparatus"),
                ("equipment", "equipment"),
                ("activities", "activities"),
                ("visible_text", "visible_text"),
                ("uncertain_observations", "uncertain")
            ):
                for value in self._list(observation.get(key)):
                    self._add_term(values[target], value)

            self._add_term(values["settings"], observation.get("setting"))
            self._add_term(values["all"], observation.get("description"))

        for key in (
            "root_category",
            "subcategory",
            "incident_type",
            "training_type",
            "public_education_program",
            "campaign",
            "community_event",
            "apparatus_name"
        ):
            self._add_term(values["all"], filesystem.get(key))
            self._add_term(values["activities"], filesystem.get(key))

        for key in (
            "normalized_scene",
            "incident_type",
            "primary_activity",
            "search_text"
        ):
            self._add_term(values["all"], effective.get(key))
            self._add_term(values["activities"], effective.get(key))

        for key, target in (
            ("apparatus_tags", "apparatus"),
            ("equipment_tags", "equipment"),
            ("ppe_tags", "ppe"),
            ("people_tags", "people"),
            ("content_tags", "activities"),
            ("recommended_uses", "activities")
        ):
            for value in self._list(effective.get(key)):
                self._add_term(values[target], value)

        for collection in ("apparatus", "equipment", "activities", "settings", "all"):
            for value in list(values[collection]):
                lower = value.lower()
                if any(term in lower for term in self.PPE_TERMS):
                    values["ppe"].add(value)
                if any(term in lower for term in self.EQUIPMENT_TERMS):
                    values["equipment"].add(value)
                if any(term in lower for term in self.APPARATUS_TERMS):
                    values["apparatus"].add(value)
                values["all"].add(value)

        return values

    ############################################################

    def _scores(self, duration, orientation, story_category, values, frames, effective):

        communications = self._score(effective.get("communications_score"))
        if not communications:
            communications = self._score(effective.get("intelligence_score"))

        visual_interest = min(
            100,
            35 +
            len(values["equipment"]) * 8 +
            len(values["apparatus"]) * 8 +
            len(values["people"]) * 6 +
            max(0, len(frames) - 1) * 4
        )
        length_score = self._length_score(duration)
        platform = 88 if orientation == "portrait" else 76
        story = min(
            100,
            max(communications, 45) +
            (15 if story_category != "Unknown" else 0) +
            (10 if values["equipment"] or values["apparatus"] else 0)
        )
        training = 75 if story_category == "Training" else 35
        education = 70 if story_category in ("Public Education", "Fire Prevention", "Program", "Campaign") else 35
        recruitment = 70 if story_category in ("Recruitment", "Training", "Community") else 35
        community = 78 if story_category in ("Community", "Public Education", "Program") else 38
        operations = 78 if story_category in ("Incident", "Operations", "Training") else 35
        reel = round(
            visual_interest * 0.25 +
            length_score * 0.20 +
            platform * 0.15 +
            story * 0.20 +
            max(training, community, operations, recruitment) * 0.20
        )
        reel = max(0, min(100, reel))

        return {
            "story_potential": int(story),
            "education_score": int(education),
            "recruitment_score": int(recruitment),
            "community_score": int(community),
            "operations_score": int(operations),
            "reel_potential": int(reel),
            "reel_explanation": (
                f"Reel score balances visual interest {visual_interest}, "
                f"length fit {length_score}, platform fit {platform}, "
                f"and story clarity {story}."
            )
        }

    ############################################################

    def _story_category(self, values, filesystem, effective):

        text = " ".join(
            sorted(values["all"] | values["activities"])
        ).lower()
        root = str(filesystem.get("root_category") or "").lower()

        categories = (
            ("training", "Training"),
            ("incident", "Incident"),
            ("fire", "Incident"),
            ("public education", "Public Education"),
            ("education", "Public Education"),
            ("recruit", "Recruitment"),
            ("community", "Community"),
            ("apparatus", "Apparatus"),
            ("prevention", "Fire Prevention"),
            ("program", "Program"),
            ("campaign", "Campaign"),
            ("operation", "Operations")
        )

        for token, label in categories:
            if token in text or token in root:
                return label

        incident = str(effective.get("incident_type") or "").strip()
        if incident and incident.lower() not in ("unknown", "none"):
            return incident.replace("_", " ").title()

        return "Unknown"

    def _primary_activity(self, values, story_category):

        if story_category != "Unknown":
            return story_category.lower().replace(" ", "_")

        for value in sorted(values["activities"]):
            if value and value != "unknown":
                return value

        return "unknown"

    def _secondary_activity(self, values, primary):

        for value in sorted(values["activities"]):
            if value and value != primary:
                return value

        return "unknown"

    def _incident_category(self, values, story_category):

        if story_category in ("Incident", "Operations"):
            return story_category

        for value in sorted(values["activities"]):
            if "fire" in value.lower() or "mvc" in value.lower():
                return value

        return "unknown"

    def _training_evolution(self, values):

        text = " ".join(values["all"] | values["equipment"]).lower()

        if "ladder" in text:
            return "ladder evolution"

        if "hose" in text:
            return "hose evolution"

        if "scba" in text:
            return "SCBA training"

        if "training" in text:
            return "training evolution"

        return ""

    def _communications_themes(self, story_category, values, filesystem, effective):

        themes = {
            story_category,
            filesystem.get("campaign", ""),
            filesystem.get("public_education_program", "")
        }

        if values["people"]:
            themes.add("people")

        if values["equipment"]:
            themes.add("technical education")

        for value in self._list(effective.get("content_themes")):
            themes.add(value)

        return sorted(theme for theme in themes if theme and theme != "Unknown")[:8]

    def _audience(self, story_category, values):

        audiences = ["Morden residents"]

        if story_category == "Recruitment":
            audiences.append("prospective volunteers")

        if story_category in ("Training", "Operations"):
            audiences.append("fire-service followers")

        if story_category in ("Public Education", "Fire Prevention", "Program"):
            audiences.append("families and educators")

        return audiences

    ############################################################

    def _clip_recommendations(self, duration, story_category, frames):

        if duration <= 0:
            return []

        windows = []
        starts = [frame.get("timestamp", 0) for frame in frames[:3]] or [0]

        for start in starts:
            start = max(0, min(float(start or 0), max(0, duration - 4)))
            end = min(duration, start + (14 if duration <= 45 else 18))
            if end - start < 3:
                continue

            windows.append(
                {
                    "start_seconds": round(start, 2),
                    "end_seconds": round(end, 2),
                    "start": self._timecode(start),
                    "end": self._timecode(end),
                    "reason": (
                        f"Bounded {story_category.lower()} segment with representative visual context."
                    )
                }
            )

        return windows[:3]

    def _cover_recommendation(self, frames, observations, values):

        if not frames:
            return {}

        selected = frames[min(1, len(frames) - 1)]
        reason = "Representative frame with clearer mid-video context."

        if values["apparatus"]:
            reason = "Frame likely supports apparatus visibility."
        elif values["equipment"]:
            reason = "Frame likely supports visible equipment or action."
        elif values["people"]:
            reason = "Frame likely supports firefighter or community presence."

        return {
            "timestamp_seconds": selected.get("timestamp", 0),
            "timecode": self._timecode(selected.get("timestamp", 0)),
            "reason": reason
        }

    ############################################################

    def _confidence(self, observations, filesystem, effective):

        scores = [
            float(item.get("confidence") or 0)
            for item in observations
            if item.get("confidence") is not None
        ]
        base = sum(scores) / len(scores) if scores else 0.25

        if filesystem.get("filesystem_confidence"):
            base = max(base, min(0.75, filesystem.get("filesystem_confidence", 0) / 100))

        if effective.get("trust_state") in ("approved_real", "corrected_real"):
            base = max(base, 0.75)

        return round(max(0, min(1, base)), 3)

    def _explanation(self, story_category, primary_activity, scores, confidence, filesystem):

        pieces = [
            f"Story category is {story_category} based on sampled frames and stored intelligence.",
            f"Primary activity is {primary_activity}.",
            f"Reel potential is {scores['reel_potential']} because bounded frame sampling found communications value without decoding every frame.",
            f"Confidence is {confidence}."
        ]

        if filesystem.get("root_category"):
            pieces.append(
                "Filesystem context contributed " +
                str(filesystem.get("root_category"))
            )

        return " ".join(pieces)

    def _summary(self, story_category, primary_activity, duration):

        return (
            f"{story_category} video candidate with primary activity "
            f"{primary_activity}; duration {self._timecode(duration)}."
        )

    ############################################################

    def _filesystem_context(self, media_id):

        if self.db and hasattr(self.db, "get_filesystem_intelligence"):
            try:
                return self.db.get_filesystem_intelligence(media_id) or {}
            except Exception:
                return {}

        return {}

    def _effective(self, media_id):

        if self.db and hasattr(self.db, "get_media_intelligence"):
            try:
                return self.db.get_media_intelligence(media_id) or {}
            except Exception:
                return {}

        return {}

    def _prompt_context(self, media_id):

        if self.filesystem and hasattr(self.filesystem, "prompt_context"):
            try:
                return self.filesystem.prompt_context(media_id)
            except Exception:
                return ""

        return ""

    ############################################################

    def _observation_from_analysis(self, frame, analysis):

        return {
            "timestamp": frame.get("timestamp", 0),
            "timecode": self._timecode(frame.get("timestamp", 0)),
            "description": analysis.get("description", ""),
            "people_count": analysis.get("people_count", 0),
            "people": self._list(analysis.get("people")),
            "apparatus": self._list(analysis.get("apparatus")),
            "equipment": self._list(analysis.get("equipment")),
            "activities": self._list(analysis.get("activities")),
            "setting": analysis.get("setting", ""),
            "visible_text": self._list(analysis.get("visible_text")),
            "uncertain_observations": self._list(
                analysis.get("uncertain_observations")
            ),
            "confidence": analysis.get("confidence", 0),
            "parse_status": analysis.get("parse_status", "")
        }

    def _safe_frame_outputs(self, observations):

        safe = []

        for item in observations:
            safe.append(
                {
                    key: value
                    for key, value in item.items()
                    if key not in ("path", "image")
                }
            )

        return safe

    ############################################################

    def _bounded_unique_timestamps(self, values, duration, limit):

        seen = set()
        results = []

        for value in values:
            value = max(0, min(float(value or 0), max(0, duration)))
            rounded = round(value, 3)

            if rounded in seen:
                continue

            seen.add(rounded)
            results.append(rounded)

        if len(results) <= limit:
            return results

        step = max(1, len(results) // limit)
        sampled = results[::step][:limit - 1]
        if results[-1] not in sampled:
            sampled.append(results[-1])

        return sampled[:limit]

    def _max_frames(self):

        return max(
            1,
            int(self.config.get("video_max_frames", self.DEFAULT_MAX_FRAMES))
        )

    def _max_analyzed_frames(self):

        return max(
            0,
            int(
                self.config.get(
                    "video_max_analyzed_frames",
                    self.DEFAULT_MAX_ANALYZED_FRAMES
                )
            )
        )

    def _position_label(self, timestamp, timestamps):

        if not timestamps:
            return "unknown"

        maximum = max(float(value or 0) for value in timestamps) or 1
        ratio = float(timestamp or 0) / maximum

        if ratio < 0.25:
            return "beginning"

        if ratio < 0.75:
            return "middle"

        return "end"

    def _length_score(self, duration):

        if duration <= 0:
            return 30

        if 7 <= duration <= 45:
            return 95

        if duration <= 90:
            return 80

        if duration <= 180:
            return 60

        return 42

    def _timecode(self, seconds):

        seconds = int(max(0, float(seconds or 0)))
        minutes = seconds // 60
        remainder = seconds % 60
        return f"{minutes:02d}:{remainder:02d}"

    def _list(self, value):

        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, tuple):
            return list(value)

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []

            try:
                decoded = json.loads(text)
                if isinstance(decoded, list):
                    return decoded
            except Exception:
                pass

            return [
                part.strip()
                for part in text.replace(";", ",").split(",")
                if part.strip()
            ]

        return [value]

    def _add_term(self, target, value):

        for item in self._list(value):
            text = str(item or "").strip()
            if text:
                target.add(text)

    def _score(self, value):

        try:
            return int(float(value or 0))
        except Exception:
            return 0
