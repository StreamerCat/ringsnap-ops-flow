"""
Vapi adapter — outbound call management and tool response handling.
# TODO: implement with real VAPI_API_KEY
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from .base import BaseAdapter

logger = logging.getLogger(__name__)

VAPI_BASE_URL = "https://api.vapi.ai"


class VapiAdapter(BaseAdapter):
    """
    HTTP client for Vapi AI API.
    Real implementation requires VAPI_API_KEY.
    """

    def __init__(self, api_key: str = ""):
        stub = not api_key
        super().__init__(stub=stub)
        self._api_key = api_key
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def send_tool_response(self, call_id: str, tool_call_id: str, result: Any) -> bool:
        """
        Send a tool call result back to an active Vapi call.
        Used to return checkout link data during the outbound call.
        """
        if self.is_stub:
            self._log_stub("send_tool_response", call_id=call_id, result_type=type(result).__name__)
            return True

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{VAPI_BASE_URL}/call/{call_id}/tool-calls/{tool_call_id}/response",
                    headers=self._headers,
                    json={"result": result},
                    timeout=10.0,
                )
                resp.raise_for_status()
                return True
            except Exception as e:
                logger.error("vapi_adapter.tool_response_failed call_id=%s error=%s", call_id, e)
                return False

    async def get_call_transcript(self, call_id: str) -> Optional[str]:
        """Retrieve the transcript for a completed call."""
        if self.is_stub:
            self._log_stub("get_call_transcript", call_id=call_id)
            return f"[STUB TRANSCRIPT for call {call_id}]"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{VAPI_BASE_URL}/call/{call_id}",
                    headers=self._headers,
                    timeout=15.0,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("transcript", "")
            except Exception as e:
                logger.error("vapi_adapter.transcript_failed call_id=%s error=%s", call_id, e)
                return None

    async def get_call_details(self, call_id: str) -> Optional[dict[str, Any]]:
        """Get full call details including outcome and metadata."""
        if self.is_stub:
            self._log_stub("get_call_details", call_id=call_id)
            return {
                "id": call_id,
                "status": "completed",
                "endedReason": "customer-ended-call",
                "summary": "[STUB] Call completed successfully",
                "duration": 300,
            }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{VAPI_BASE_URL}/call/{call_id}",
                    headers=self._headers,
                    timeout=15.0,
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error("vapi_adapter.get_call_failed call_id=%s error=%s", call_id, e)
                return None
