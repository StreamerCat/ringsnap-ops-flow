"""
CRM adapter — contact and task management.
# TODO: implement with real CRM credentials (currently stub only)
Supports generic CRM operations. Specific CRM integration TBD (HubSpot, etc.)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from .base import BaseAdapter

logger = logging.getLogger(__name__)


class CrmAdapter(BaseAdapter):
    """
    Generic CRM adapter for contact upsert and task creation.
    Used by provisioning, onboarding, and rescue flows.
    """

    def __init__(self, api_key: str = "", crm_type: str = "stub"):
        stub = not api_key or crm_type == "stub"
        super().__init__(stub=stub)
        self._crm_type = crm_type
        # TODO: initialize real CRM client based on crm_type

    def upsert_contact(self, contact_data: dict[str, Any]) -> str:
        """
        Create or update a CRM contact.
        Returns the CRM contact ID.
        Protected: always call after checkout completion, not before.
        """
        if self.is_stub:
            self._log_stub("upsert_contact", email=contact_data.get("email"))
            return f"crm_contact_stub_{str(uuid.uuid4())[:8]}"

        # TODO: implement for chosen CRM
        raise NotImplementedError(f"CRM type '{self._crm_type}' not yet implemented")

    def create_task(self, task_data: dict[str, Any]) -> str:
        """
        Create a task/follow-up in the CRM.
        Returns the task ID.
        Safe to call for: rescue tasks, callback recommendations, manual review flags.
        """
        if self.is_stub:
            self._log_stub("create_task", title=task_data.get("title", ""))
            return f"crm_task_stub_{str(uuid.uuid4())[:8]}"

        raise NotImplementedError(f"CRM type '{self._crm_type}' not yet implemented")

    def update_deal_stage(self, deal_id: str, stage: str) -> bool:
        """Update deal/opportunity stage in CRM."""
        if self.is_stub:
            self._log_stub("update_deal_stage", deal_id=deal_id, stage=stage)
            return True
        return False

    def log_call_outcome(self, contact_id: str, call_data: dict[str, Any]) -> bool:
        """Log a call outcome to the CRM contact record."""
        if self.is_stub:
            self._log_stub("log_call_outcome", contact_id=contact_id)
            return True
        return False
