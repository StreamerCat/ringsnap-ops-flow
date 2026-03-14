"""
PostHog telemetry client for RingSnap Ops Flow.

Fire-and-forget event capture. Never raises — telemetry must never block
or fail the ops pipeline. All calls are non-blocking (posthog SDK queues
events in a background thread).

Usage:
    from .adapters.posthog_client import capture
    capture("lead-123", "ops_lead_scored", {"lead_score": 82, "plan": "core"})
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_posthog = None
_initialized = False


def _init() -> Any:
    """Lazy-initialize the PostHog client. Returns the posthog module or None."""
    global _posthog, _initialized
    if _initialized:
        return _posthog

    _initialized = True
    try:
        import posthog as ph

        from ..config import settings

        api_key = settings.posthog_api_key
        if not api_key:
            logger.debug("posthog_client.disabled no POSTHOG_API_KEY set")
            _posthog = None
            return None

        ph.project_api_key = api_key
        ph.host = settings.posthog_host
        ph.disabled = False
        # Suppress posthog's own noisy logging
        logging.getLogger("posthog").setLevel(logging.WARNING)
        _posthog = ph
        logger.info("posthog_client.initialized host=%s", settings.posthog_host)
    except ImportError:
        logger.debug("posthog_client.import_failed posthog package not installed")
        _posthog = None

    return _posthog


def capture(
    distinct_id: str,
    event: str,
    properties: Optional[dict] = None,
) -> None:
    """
    Send a PostHog event. Fire-and-forget — never raises.

    Args:
        distinct_id: The entity this event is about (entity_id, account_id, or
                     "ringsnap-ops-flow" for system-level events).
        event: Event name (e.g. "ops_lead_scored").
        properties: Arbitrary key-value pairs to attach to the event.
    """
    try:
        ph = _init()
        if ph is None:
            return
        ph.capture(
            distinct_id=distinct_id or "ringsnap-ops-flow",
            event=event,
            properties=properties or {},
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("posthog_client.capture_error event=%s error=%s", event, exc)
