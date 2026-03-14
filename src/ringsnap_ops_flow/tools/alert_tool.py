"""CrewAI tool for emitting alerts from within crew tasks."""

from __future__ import annotations

import logging
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AlertInput(BaseModel):
    severity: str = Field(description="Alert severity: info | warning | critical")
    message: str = Field(description="Alert message")
    module: str = Field(description="Module emitting the alert")
    entity_id: str = Field(default="", description="Entity ID (account_id, pending_signup_id, etc.)")


class AlertTool(BaseTool):
    """Emit an operational alert. Use for critical failures, threshold breaches, and recovery failures."""

    name: str = "emit_alert"
    description: str = "Emit an operational alert for a failure or threshold breach."
    args_schema: Type[BaseModel] = AlertInput

    def _run(self, severity: str, message: str, module: str, entity_id: str = "") -> str:
        log_fn = logger.critical if severity == "critical" else (logger.warning if severity == "warning" else logger.info)
        log_fn(
            "alert severity=%s module=%s entity_id=%s message=%s",
            severity,
            module,
            entity_id,
            message,
        )
        # TODO: send to Slack / PagerDuty / Resend email based on severity
        return f"Alert emitted: [{severity.upper()}] {message}"
