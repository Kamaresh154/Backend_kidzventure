"""
Exotel integration service for KidzVenture.
Account SID: saraban1  |  Region: Singapore  |  Subdomain: api.exotel.com

Exotel Call Flow:
  Frontend calls POST /calls/exotel/initiate
    → Backend calls Exotel REST API to place the call
    → Exotel calls your agent's phone first, then bridges to customer
    → After call ends, Exotel POSTs to your webhook with recording URL
    → Webhook saves recording_url to CallLog in DB
"""

import base64
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


class ExotelService:
    """
    Wraps Exotel REST API v2 (Singapore region).

    Exotel REST API base URL for Singapore:
      https://<account_sid>:<api_token>@api.exotel.com/v1/Accounts/<account_sid>/
    """

    def __init__(
        self,
        account_sid: str,       # "saraban1"
        api_key: str,           # API KEY (username) from dashboard
        api_token: str,         # API TOKEN (password) from dashboard
        caller_id: str,         # Your Exotel virtual number / ExoPhone
        subdomain: str = "api.exotel.com",
    ):
        self.account_sid = account_sid
        self.api_key = api_key
        self.api_token = api_token
        self.caller_id = caller_id
        self.base_url = f"https://{subdomain}/v1/Accounts/{account_sid}"
        # Basic auth: api_key:api_token
        credentials = base64.b64encode(f"{api_key}:{api_token}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def make_call(
        self,
        to_number: str,
        agent_number: str,
        webhook_url: str,
        status_callback_url: str | None = None,
    ) -> dict:
        """
        Initiate an outbound call via Exotel.

        Exotel's call flow with two phones:
          1. Exotel calls `agent_number` (agent picks up)
          2. Exotel bridges to `to_number` (customer)
          3. Both are connected — call is recorded
          4. On call end → POST to webhook_url with RecordingUrl

        Args:
            to_number:            Customer phone, e.g. "+919876543210"
            agent_number:         Agent's mobile, e.g. "+918220927361"
            webhook_url:          Your backend URL for call status/recording
            status_callback_url:  Optional separate URL for mid-call status

        Returns:
            Exotel API response dict with CallSid, Status, etc.
        """
        # Ensure E.164 format for India
        to_number = _to_e164(to_number)
        agent_number = _to_e164(agent_number)
        caller_id = _to_e164(self.caller_id)

        payload = {
            "From": agent_number,           # Agent's phone gets called first
            "To": to_number,                # Customer number
            "CallerId": caller_id,          # Your Exotel ExoPhone shown to customer
            "StatusCallback": webhook_url,  # Exotel POSTs here on call end
            "Record": "true",              # Auto-record the call
            "RecordingChannels": "dual",    # Record both sides separately
        }
        if status_callback_url:
            payload["StatusCallbackEvents[0]"] = "terminal"

        url = f"{self.base_url}/Calls/connect.json"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=payload, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("Exotel call initiated: %s", data)
            return data.get("Call", data)

    async def get_call_details(self, call_sid: str) -> dict:
        """Fetch call details by CallSid (to get recording URL manually)."""
        url = f"{self.base_url}/Calls/{call_sid}.json"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            return resp.json().get("Call", {})

    async def get_recordings(self, call_sid: str) -> list[dict]:
        """List recordings for a call."""
        url = f"{self.base_url}/Calls/{call_sid}/Recordings.json"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=self._headers)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()
            return data.get("RecordingList", {}).get("Recording", [])


def _to_e164(number: str) -> str:
    """Convert Indian phone numbers to E.164 (+91XXXXXXXXXX)."""
    number = number.strip().replace(" ", "").replace("-", "")
    if number.startswith("+"):
        return number
    if number.startswith("0"):
        number = number[1:]
    if len(number) == 10:
        return f"+91{number}"
    return number


def parse_exotel_webhook(form_data: dict) -> dict:
    """
    Parse the POST data Exotel sends to your webhook after a call ends.

    Exotel sends these fields (among others):
      CallSid           - unique call ID
      CallStatus        - completed / no-answer / busy / failed
      Direction         - outbound-api
      From              - agent number
      To                - customer number
      CallDuration      - seconds
      RecordingUrl      - MP3 URL (if recording enabled)
      StartTime         - epoch or ISO
      EndTime           - epoch or ISO
    """
    return {
        "call_sid": form_data.get("CallSid", ""),
        "status": _map_status(form_data.get("CallStatus", "completed")),
        "duration_secs": int(form_data.get("CallDuration", 0)),
        "recording_url": form_data.get("RecordingUrl"),
        "from_number": form_data.get("From", ""),
        "to_number": form_data.get("To", ""),
        "direction": form_data.get("Direction", "outbound-api"),
        "started_at": _parse_time(form_data.get("StartTime")),
        "ended_at": _parse_time(form_data.get("EndTime")),
    }


def _map_status(exotel_status: str) -> str:
    """Map Exotel call status to our DB status."""
    mapping = {
        "completed": "completed",
        "no-answer": "no-answer",
        "busy": "missed",
        "failed": "missed",
        "canceled": "missed",
        "in-progress": "in-progress",
        "initiated": "initiated",
        "ringing": "initiated",
    }
    return mapping.get(exotel_status.lower(), "completed")


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Exotel sends epoch int as string
        if value.isdigit():
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now(timezone.utc)