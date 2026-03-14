"""Base adapter with stub mode support."""

from __future__ import annotations

import logging
from abc import ABC

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """
    Base class for all external service adapters.

    When is_stub is True, methods return realistic dummy data
    so the system can run in CI and development without real credentials.
    """

    def __init__(self, stub: bool = True):
        self._stub = stub

    @property
    def is_stub(self) -> bool:
        return self._stub

    def _log_stub(self, method: str, **kwargs) -> None:
        logger.debug("[STUB] %s.%s %s", self.__class__.__name__, method, kwargs)
