"""
Retry handler — capped, non-looping retry logic.

Rules:
- Retries are capped at max_retries_per_workflow (default 3).
- When cap is hit, raises RetryCappedError so the caller can alert instead of looping.
- Only safe, non-destructive steps should be retried.
- Destructive steps (e.g. release phone number, delete account) must never be retried automatically.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional, TypeVar

from tenacity import RetryError, Retrying, stop_after_attempt, wait_exponential

from ..config import execution as exec_cfg

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryCappedError(Exception):
    """Raised when retry limit is reached. Caller should alert, not loop."""

    def __init__(self, entity_id: str, step: str, last_error: str):
        self.entity_id = entity_id
        self.step = step
        self.last_error = last_error
        super().__init__(f"Retry cap reached for entity={entity_id} step={step}: {last_error}")


class RetryResult:
    def __init__(self, success: bool, value: Any = None, error: Optional[str] = None, attempts: int = 0):
        self.success = success
        self.value = value
        self.error = error
        self.attempts = attempts


def attempt_retry(
    fn: Callable[[], T],
    entity_id: str,
    step: str,
    max_attempts: Optional[int] = None,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
) -> RetryResult:
    """
    Attempt fn() with exponential backoff. Raises RetryCappedError if all attempts fail.

    Args:
        fn: Zero-argument callable to attempt. Must be idempotent.
        entity_id: ID of the entity being retried (for logging).
        step: Name of the step being retried (for logging and alerts).
        max_attempts: Override for max attempts (defaults to config value).
        wait_min: Min wait between retries in seconds.
        wait_max: Max wait between retries in seconds.

    Returns:
        RetryResult with success=True and value set on success.

    Raises:
        RetryCappedError: When all attempts are exhausted.
    """
    limit = max_attempts or exec_cfg.max_retries_per_workflow
    last_error: str = ""
    attempts = 0

    try:
        for attempt in Retrying(
            stop=stop_after_attempt(limit),
            wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
            reraise=False,
        ):
            with attempt:
                attempts += 1
                logger.info(
                    "retry_handler.attempt entity_id=%s step=%s attempt=%d/%d",
                    entity_id,
                    step,
                    attempts,
                    limit,
                )
                try:
                    result = fn()
                    logger.info(
                        "retry_handler.success entity_id=%s step=%s attempts=%d",
                        entity_id,
                        step,
                        attempts,
                    )
                    return RetryResult(success=True, value=result, attempts=attempts)
                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        "retry_handler.attempt_failed entity_id=%s step=%s attempt=%d error=%s",
                        entity_id,
                        step,
                        attempts,
                        last_error,
                    )
                    raise  # let tenacity handle retry

    except RetryError:
        pass

    logger.error(
        "retry_handler.cap_reached entity_id=%s step=%s attempts=%d last_error=%s",
        entity_id,
        step,
        attempts,
        last_error,
    )
    raise RetryCappedError(entity_id=entity_id, step=step, last_error=last_error)


def is_retry_capped(current_attempts: int, max_attempts: Optional[int] = None) -> bool:
    """Check if the current attempt count has reached the cap."""
    limit = max_attempts or exec_cfg.max_retries_per_workflow
    return current_attempts >= limit
