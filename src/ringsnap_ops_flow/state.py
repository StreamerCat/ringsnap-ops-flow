"""
Shared state schema for RingSnap Ops Flow.
All state transitions flow through these Pydantic models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PendingSignupStatus(str, Enum):
    QUALIFIED = "qualified"
    LINK_SENT = "link_sent"
    CHECKOUT_OPENED = "checkout_opened"
    CHECKOUT_COMPLETED = "checkout_completed"
    ACCOUNT_CREATED = "account_created"
    PROVISIONED = "provisioned"
    ACTIVATED = "activated"
    EXPIRED = "expired"
    FAILED = "failed"


class ProvisioningStage(str, Enum):
    NOT_STARTED = "not_started"
    STAGE1_RUNNING = "stage1_running"
    STAGE1_COMPLETE = "stage1_complete"
    STAGE2_RUNNING = "stage2_running"
    STAGE2_COMPLETE = "stage2_complete"
    FAILED = "failed"
    PAUSED = "paused"


class OnboardingStep(str, Enum):
    NOT_STARTED = "not_started"
    ACCOUNT_SETUP = "account_setup"
    PHONE_ASSIGNED = "phone_assigned"
    ASSISTANT_CONFIGURED = "assistant_configured"
    TEST_CALL_COMPLETED = "test_call_completed"
    COMPLETED = "completed"
    STALLED = "stalled"


class OpsEventType(str, Enum):
    QUALIFIED_LEAD = "qualified_lead_wants_trial_or_paid"
    PAYMENT_FAILURE = "payment_failure"
    SIGNUP_FAILURE = "signup_or_account_creation_failure"
    PROVISIONING_FAILURE = "provisioning_failure"
    ONBOARDING_STALLED = "onboarding_stalled"
    ABUSE_RISK_SPIKE = "abuse_or_risk_spike"
    DAILY_DIGEST = "daily_founder_digest"
    BATCHED_INSIGHTS = "batched_product_insight_job"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Sub-state models
# ---------------------------------------------------------------------------


class PendingSignupState(BaseModel):
    """State for a single lead in the phone sales → checkout funnel."""

    id: Optional[str] = None
    account_id: Optional[str] = None
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    business_name: Optional[str] = None
    trade: Optional[str] = None
    selected_plan: str = ""
    status: PendingSignupStatus = PendingSignupStatus.QUALIFIED
    stripe_checkout_session_id: Optional[str] = None
    checkout_link: Optional[str] = None
    link_sent_at: Optional[datetime] = None
    checkout_completed_at: Optional[datetime] = None
    rescue_attempts: int = 0
    vapi_call_id: Optional[str] = None
    lead_score: Optional[int] = None
    is_high_intent: bool = False
    is_high_fit: bool = False
    sales_rep_id: Optional[str] = None
    failure_reason: Optional[str] = None
    failure_phase: Optional[str] = None
    lead_data: dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ProvisioningState(BaseModel):
    """State for account provisioning (two-stage)."""

    account_id: Optional[str] = None
    stage: ProvisioningStage = ProvisioningStage.NOT_STARTED
    stage1_done: bool = False
    stage2_done: bool = False
    # Exact step where failure occurred (for precise rescue)
    failure_point: Optional[str] = None
    retry_count: int = 0
    marked_for_manual_review: bool = False
    stage2_globally_paused: bool = False
    last_error: Optional[str] = None
    validation_errors: list[str] = Field(default_factory=list)


class OnboardingState(BaseModel):
    """State for post-activation onboarding."""

    account_id: Optional[str] = None
    current_step: OnboardingStep = OnboardingStep.NOT_STARTED
    steps_completed: list[str] = Field(default_factory=list)
    stall_detected: bool = False
    stall_at_hours: Optional[float] = None
    reopen_attempted: bool = False
    callback_recommended: bool = False
    started_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None


class CampaignHealthState(BaseModel):
    """Aggregated outbound campaign health metrics."""

    # Rates (0.0 to 1.0)
    checkout_completion_rate: float = 1.0
    activation_rate: float = 1.0
    provisioning_success_rate: float = 1.0
    # Counts (last 24h window)
    qualified_leads_count: int = 0
    links_sent_count: int = 0
    checkout_completed_count: int = 0
    activation_failures_count: int = 0
    stalled_pending_signups_count: int = 0
    # Flags
    safe_mode_active: bool = False
    stage2_paused: bool = False
    outbound_pause_recommended: bool = False
    # When safe mode was activated
    safe_mode_activated_at: Optional[datetime] = None


class ExecutionCountState(BaseModel):
    """Per-module execution counters for cost tracking."""

    # {module_name: count_today}
    counts_today: dict[str, int] = Field(default_factory=dict)
    # {module_name: estimated_cost_usd_today}
    costs_today: dict[str, float] = Field(default_factory=dict)
    total_cost_today_usd: float = 0.0
    budget_alert_fired: bool = False
    reset_at: Optional[datetime] = None

    def increment(self, module_name: str, cost_usd: float = 0.0) -> None:
        self.counts_today[module_name] = self.counts_today.get(module_name, 0) + 1
        self.costs_today[module_name] = self.costs_today.get(module_name, 0.0) + cost_usd
        self.total_cost_today_usd += cost_usd

    def get_count(self, module_name: str) -> int:
        return self.counts_today.get(module_name, 0)


class DigestState(BaseModel):
    """Data assembled for the daily founder digest."""

    date: Optional[str] = None
    # Funnel metrics
    qualified_leads: int = 0
    checkout_links_sent: int = 0
    checkout_completed: int = 0
    trials_activated: int = 0
    activation_failures: int = 0
    stalled_pending_signups: int = 0
    # Recovery
    failed_recovery_count: int = 0
    manual_review_count: int = 0
    # Estimated waste prevented (USD) by not provisioning before checkout
    estimated_waste_prevented_usd: float = 0.0
    # Cost metrics
    total_llm_cost_usd: float = 0.0
    executions_by_module: dict[str, int] = Field(default_factory=dict)
    # Health flags
    safe_mode_active: bool = False
    outbound_pause_recommended: bool = False
    stage2_paused: bool = False
    # Formatted markdown output (populated by executive_digest crew)
    digest_markdown: Optional[str] = None
    generated_at: Optional[datetime] = None


class AlertState(BaseModel):
    """Pending alerts to be dispatched."""

    alerts: list[dict[str, Any]] = Field(default_factory=list)

    def add(self, severity: AlertSeverity, message: str, module: str, entity_id: Optional[str] = None) -> None:
        self.alerts.append(
            {
                "severity": severity.value,
                "message": message,
                "module": module,
                "entity_id": entity_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def has_critical(self) -> bool:
        return any(a["severity"] == AlertSeverity.CRITICAL.value for a in self.alerts)


# ---------------------------------------------------------------------------
# Inbound event schema
# ---------------------------------------------------------------------------


class OpsEvent(BaseModel):
    """Inbound event payload from Supabase Edge Functions or cron."""

    event_type: OpsEventType
    entity_id: Optional[str] = None
    account_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = "supabase_function"
    idempotency_key: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Root state (passed through the CrewAI Flow)
# ---------------------------------------------------------------------------


class OpsFlowState(BaseModel):
    """Root shared state for the RingSnap Ops Flow."""

    # The triggering event
    event: Optional[OpsEvent] = None

    # Per-entity states (populated as flow progresses)
    pending_signup: PendingSignupState = Field(default_factory=PendingSignupState)
    provisioning: ProvisioningState = Field(default_factory=ProvisioningState)
    onboarding: OnboardingState = Field(default_factory=OnboardingState)
    campaign_health: CampaignHealthState = Field(default_factory=CampaignHealthState)
    execution_counts: ExecutionCountState = Field(default_factory=ExecutionCountState)
    digest: DigestState = Field(default_factory=DigestState)
    alerts: AlertState = Field(default_factory=AlertState)

    # Flow control
    flow_id: Optional[str] = None
    skip_reason: Optional[str] = None
    should_abort: bool = False
    crew_result: Optional[str] = None
