from services.time_service import TimeService


class CacheInvalidationService:

    _events = []
    _sequence = 0
    MAX_EVENTS = 500

    @classmethod
    def invalidate(cls, media_id=None, reason="", scopes=None):

        cls._sequence += 1
        event = {
            "sequence": cls._sequence,
            "media_id": media_id,
            "reason": reason,
            "scopes": list(scopes or []),
            "created_at": TimeService.utc_now_iso()
        }
        cls._events.append(event)
        cls._events = cls._events[-cls.MAX_EVENTS:]
        return event

    @classmethod
    def latest(cls, media_id=None):

        for event in reversed(cls._events):
            if media_id is None or event.get("media_id") == media_id:
                return dict(event)

        return {}

    @classmethod
    def changed_since(cls, sequence, media_id=None, scopes=None):

        scopes = set(scopes or [])

        for event in reversed(cls._events):
            if event.get("sequence", 0) <= int(sequence or 0):
                break

            if media_id is not None and event.get("media_id") not in (None, media_id):
                continue

            if scopes and not (scopes & set(event.get("scopes") or [])):
                continue

            return True

        return False
