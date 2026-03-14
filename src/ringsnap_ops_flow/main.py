"""
RingSnap Ops Flow — FastAPI entry point.

Endpoints:
  POST /ops/event   ← receives events from Supabase Edge Functions
  POST /ops/digest  ← triggers daily founder digest (cron)
  GET  /ops/health  ← health check
  GET  /ops/status  ← execution counters + campaign health

For AMP deployment, the RingSnapOpsFlow class is the entrypoint.
For self-hosted/serverless, run with: uvicorn ringsnap_ops_flow.main:app
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .adapters.posthog_client import capture as ph_capture
from .config import settings
from .event_gate import EVENT_TO_MODULE, get_gate
from .state import OpsEvent, OpsEventType, OpsFlowState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RingSnap Ops Flow",
    description="Phase 1 GTM Ops orchestration service",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------


def _verify_webhook_secret(request: Request) -> None:
    """Verify the ops webhook secret from the incoming request."""
    if not settings.ops_webhook_secret:
        return  # No secret configured — allow in dev/stub mode
    incoming = request.headers.get("x-ops-secret", "")
    if not secrets.compare_digest(incoming, settings.ops_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid ops webhook secret")


# ---------------------------------------------------------------------------
# Background task: route event to appropriate flow
# ---------------------------------------------------------------------------


async def _process_event(event: OpsEvent) -> None:
    """Async background handler. Routes event to the right flow."""
    gate = get_gate()
    module = EVENT_TO_MODULE.get(event.event_type.value, "unknown")

    allowed, reason = gate.should_process(
        event_type=event.event_type.value,
        entity_id=event.entity_id,
        module_name=module,
    )

    if not allowed:
        logger.info("main.event_dropped event_type=%s reason=%s", event.event_type.value, reason)
        return

    state = OpsFlowState(event=event, flow_id=str(uuid.uuid4()))
    start_time = datetime.now(timezone.utc)

    try:
        if event.event_type == OpsEventType.QUALIFIED_LEAD:
            from .flows.sales_activation_flow import SalesActivationFlow
            flow = SalesActivationFlow(state=state)
            flow.kickoff()

        elif event.event_type in (
            OpsEventType.PAYMENT_FAILURE,
            OpsEventType.PROVISIONING_FAILURE,
            OpsEventType.ONBOARDING_STALLED,
        ):
            from .flows.recovery_flow import RecoveryFlow
            flow = RecoveryFlow(state=state)
            flow.kickoff()

        elif event.event_type in (OpsEventType.DAILY_DIGEST, OpsEventType.BATCHED_INSIGHTS):
            from .flows.digest_flow import DigestFlow
            flow = DigestFlow(state=state)
            flow.kickoff()

        elif event.event_type == OpsEventType.ABUSE_RISK_SPIKE:
            context = json.dumps(event.payload, indent=2, default=str)
            if not settings.is_stub_mode:
                from .crews.abuse_guard.crew import run
                run(context)
            else:
                logger.info("main.abuse_guard_stub payload=%s", context[:100])

        elif event.event_type == OpsEventType.SIGNUP_FAILURE:
            context = json.dumps(event.payload, indent=2, default=str)
            if not settings.is_stub_mode:
                from .crews.signup_conversion_guard.crew import run
                run(context)

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        gate.record_execution(module_name=module, event_type=event.event_type.value)
        logger.info(
            "main.event_processed event_type=%s module=%s elapsed_s=%.2f",
            event.event_type.value,
            module,
            elapsed,
        )
        ph_capture(
            event.entity_id or event.account_id or "ringsnap-ops-flow",
            "ops_event_processed",
            {
                "event_type": event.event_type.value,
                "module": module,
                "elapsed_s": round(elapsed, 2),
                "source": event.source,
                "environment": settings.environment,
            },
        )

    except Exception as e:
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.error(
            "main.event_failed event_type=%s module=%s elapsed_s=%.2f error=%s",
            event.event_type.value,
            module,
            elapsed,
            e,
        )
        ph_capture(
            event.entity_id or event.account_id or "ringsnap-ops-flow",
            "ops_event_failed",
            {
                "event_type": event.event_type.value,
                "module": module,
                "elapsed_s": round(elapsed, 2),
                "error": str(e)[:200],
                "environment": settings.environment,
            },
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/ops/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "ringsnap-ops-flow",
        "version": "0.1.0",
        "stub_mode": settings.is_stub_mode,
        "ops_flow_enabled": settings.ops_flow_enabled,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ops/status")
async def status() -> dict:
    gate = get_gate()
    return {
        "daily_execution_counts": gate.get_daily_counts(),
        "daily_cost_usd": round(gate.get_daily_cost_usd(), 6),
        "safe_mode_active": gate.is_safe_mode(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/ops/event")
async def receive_event(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Receive an ops event from Supabase Edge Functions.
    Validates the webhook secret, gates the event, and processes in background.
    """
    _verify_webhook_secret(request)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        event = OpsEvent(**body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid event payload: {e}")

    # Quick gate check before queuing
    gate = get_gate()
    module = EVENT_TO_MODULE.get(event.event_type.value, "unknown")
    allowed, reason = gate.should_process(
        event_type=event.event_type.value,
        entity_id=event.entity_id,
        module_name=module,
    )

    if not allowed:
        return {"status": "dropped", "reason": reason, "event_type": event.event_type.value}

    # Re-set the debounce (it was consumed in the check above)
    # We use idempotency_key to prevent duplicate processing
    background_tasks.add_task(_process_event, event)

    return {
        "status": "accepted",
        "event_type": event.event_type.value,
        "module": module,
        "flow_id": str(uuid.uuid4()),
    }


@app.post("/ops/digest")
async def trigger_digest(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """Trigger the daily founder digest. Called by external cron."""
    _verify_webhook_secret(request)

    event = OpsEvent(
        event_type=OpsEventType.DAILY_DIGEST,
        source="cron",
        timestamp=datetime.now(timezone.utc),
    )
    background_tasks.add_task(_process_event, event)

    return {"status": "accepted", "event_type": "daily_founder_digest"}


# ---------------------------------------------------------------------------
# AMP Flow entrypoint
# ---------------------------------------------------------------------------


class RingSnapOpsFlow:
    """
    CrewAI AMP deployment entrypoint.
    Use this class in crewai.yaml as the entrypoint.
    """

    def kickoff(self, event_data: Optional[dict] = None) -> str:
        """Process a single event synchronously (for AMP)."""
        import asyncio

        if not event_data:
            logger.warning("ringsnap_ops_flow.kickoff called with no event_data")
            return json.dumps({"status": "no_event"})

        try:
            event = OpsEvent(**event_data)
        except Exception as e:
            return json.dumps({"status": "error", "detail": str(e)})

        # Run in event loop
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_process_event(event))
        loop.close()

        return json.dumps({"status": "processed", "event_type": event.event_type.value})


def run_server() -> None:
    """Start the FastAPI server. Called by the poetry script."""
    import uvicorn
    uvicorn.run(
        "ringsnap_ops_flow.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
        log_level="info",
    )


if __name__ == "__main__":
    run_server()
