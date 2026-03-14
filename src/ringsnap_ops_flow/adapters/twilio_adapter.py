"""
Twilio adapter — SMS sending for checkout link delivery.
# TODO: implement with real TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
"""

from __future__ import annotations

import logging
from typing import Optional

from .base import BaseAdapter

logger = logging.getLogger(__name__)


class TwilioAdapter(BaseAdapter):
    """
    Wraps Twilio REST API for SMS sending.
    Real implementation requires TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_FROM_NUMBER.
    """

    def __init__(self, account_sid: str = "", auth_token: str = "", from_number: str = ""):
        stub = not (account_sid and auth_token and from_number)
        super().__init__(stub=stub)
        self._client = None
        self._from_number = from_number
        if not stub:
            try:
                from twilio.rest import Client
                self._client = Client(account_sid, auth_token)
                logger.info("twilio_adapter.connected")
            except ImportError:
                logger.warning("twilio_adapter.twilio_not_installed using_stub=True")
                self._stub = True

    def send_sms(self, to: str, body: str) -> bool:
        """
        Send an SMS message.
        Returns True on success.
        Protected: do not send to real numbers in stub mode.
        """
        if self.is_stub:
            self._log_stub("send_sms", to=to, body_preview=body[:50])
            return True

        try:
            msg = self._client.messages.create(
                to=to,
                from_=self._from_number,
                body=body,
            )
            logger.info("twilio_adapter.sms_sent sid=%s to=%s", msg.sid, to)
            return True
        except Exception as e:
            logger.error("twilio_adapter.send_failed to=%s error=%s", to, e)
            return False

    def check_number_availability(self, area_code: str, count: int = 5) -> list[str]:
        """
        Check available phone numbers in a given area code.
        Returns list of E.164 phone numbers.
        """
        if self.is_stub:
            self._log_stub("check_number_availability", area_code=area_code)
            return [f"+1{area_code}5550{i:04d}" for i in range(min(count, 3))]

        # TODO: use existing phone pool first before purchasing new numbers
        # This is a telecom resource management decision — see telecom_resource_manager crew
        available = self._client.available_phone_numbers("US").local.list(
            area_code=area_code,
            limit=count,
        )
        return [n.phone_number for n in available]
