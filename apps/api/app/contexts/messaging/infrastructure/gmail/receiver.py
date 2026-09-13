import base64
import logging
import re
from datetime import UTC, datetime
from email.utils import parseaddr
from typing import Any

import httpx

from app.contexts.messaging.application.ports.email_receiver import (
    FetchedMessage,
    FetchResult,
)
from app.contexts.messaging.infrastructure.gmail.access_token import (
    GoogleAccessTokenProvider,
)

_logger = logging.getLogger(__name__)

_PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
_HISTORY_URL = "https://gmail.googleapis.com/gmail/v1/users/me/history"
_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

_BODY_MAX_CHARS = 2000
_QUOTE_HEADER = re.compile(r"^On\b.*\bwrote:\s*$")
_QUOTE_LINE_MARKERS = ("-----Original Message-----",)
_BOUNCE_SENDER_LOCAL_PARTS = frozenset({"mailer-daemon", "postmaster"})


class _HistoryGoneError(Exception):
    pass


class GmailApiReceiver:
    def __init__(
        self,
        client: httpx.AsyncClient,
        token_provider: GoogleAccessTokenProvider,
    ) -> None:
        self._client = client
        self._token_provider = token_provider

    async def fetch_new(
        self, *, mailbox_email: str, since_cursor: str | None
    ) -> FetchResult:
        if since_cursor is None:
            return FetchResult(new_cursor=await self._current_history_id(), messages=())

        try:
            message_ids, new_cursor = await self._added_message_ids(since_cursor)
        except _HistoryGoneError:
            rebaselined = await self._current_history_id()
            _logger.warning(
                "Gmail history expired (cursor=%s); rebaselined to %s, "
                "gap messages skipped",
                since_cursor,
                rebaselined,
            )
            return FetchResult(new_cursor=rebaselined, messages=())

        messages = []
        for message_id in message_ids:
            fetched = await self._get_message(message_id, mailbox_email)
            if fetched is not None:
                messages.append(fetched)
        return FetchResult(new_cursor=new_cursor, messages=tuple(messages))

    async def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {await self._token_provider.token()}"}

    async def _current_history_id(self) -> str:
        response = await self._client.get(_PROFILE_URL, headers=await self._auth())
        response.raise_for_status()
        return str(response.json()["historyId"])

    async def _added_message_ids(self, start_history_id: str) -> tuple[list[str], str]:
        ordered_ids: list[str] = []
        seen: set[str] = set()
        latest_history_id = start_history_id
        page_token: str | None = None

        while True:
            params: dict[str, str] = {
                "startHistoryId": start_history_id,
                "historyTypes": "messageAdded",
            }
            if page_token:
                params["pageToken"] = page_token
            response = await self._client.get(
                _HISTORY_URL, headers=await self._auth(), params=params
            )
            if response.status_code == 404:
                raise _HistoryGoneError
            response.raise_for_status()
            data = response.json()

            if data.get("historyId"):
                latest_history_id = str(data["historyId"])
            for record in data.get("history", []):
                for added in record.get("messagesAdded", []):
                    message_id = added.get("message", {}).get("id")
                    if message_id and message_id not in seen:
                        seen.add(message_id)
                        ordered_ids.append(message_id)

            page_token = data.get("nextPageToken")
            if not page_token:
                return ordered_ids, latest_history_id

    async def _get_message(
        self, message_id: str, mailbox_email: str
    ) -> FetchedMessage | None:
        response = await self._client.get(
            f"{_MESSAGES_URL}/{message_id}",
            headers=await self._auth(),
            params={"format": "full"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        labels = data.get("labelIds", [])
        if "SENT" in labels or "INBOX" not in labels:
            return None
        fetched = parse_message(data)
        if fetched.from_email == mailbox_email.lower():
            return None
        return fetched


def parse_message(data: dict[str, Any]) -> FetchedMessage:
    payload = data.get("payload", {})
    headers = {
        header["name"].lower(): header["value"] for header in payload.get("headers", [])
    }
    received_at = datetime.fromtimestamp(
        int(data.get("internalDate", "0")) / 1000, tz=UTC
    )
    from_email = parseaddr(headers.get("from", ""))[1].lower()
    return FetchedMessage(
        provider_message_id=data["id"],
        provider_thread_id=data["threadId"],
        from_email=from_email,
        subject=headers.get("subject", ""),
        snippet=data.get("snippet", ""),
        in_reply_to_header=headers.get("in-reply-to"),
        references_header=headers.get("references"),
        received_at=received_at,
        body_text=_extract_body(payload),
        is_bounce=_is_bounce(headers, payload, from_email),
    )


def _is_bounce(
    headers: dict[str, str], payload: dict[str, Any], from_email: str
) -> bool:
    if "x-failed-recipients" in headers:
        return True
    if from_email.split("@", 1)[0] in _BOUNCE_SENDER_LOCAL_PARTS:
        return True
    auto_submitted = headers.get("auto-submitted", "").strip().lower()
    return auto_submitted.startswith("auto-") and _has_delivery_status(payload)


def _has_delivery_status(part: dict[str, Any]) -> bool:
    mime_type = part.get("mimeType", "").lower()
    if mime_type == "message/delivery-status":
        return True
    part_headers = {
        header["name"].lower(): header["value"] for header in part.get("headers", [])
    }
    content_type = part_headers.get("content-type", "").lower().replace('"', "")
    if (
        mime_type == "multipart/report"
        and "report-type=delivery-status" in content_type
    ):
        return True
    return any(_has_delivery_status(sub) for sub in part.get("parts", []))


def _extract_body(payload: dict[str, Any]) -> str:
    raw = _first_plain_text(payload)
    if raw is None:
        return ""
    return _strip_quotes(raw)[:_BODY_MAX_CHARS]


def _first_plain_text(part: dict[str, Any]) -> str | None:
    if part.get("mimeType") == "text/plain":
        data = part.get("body", {}).get("data")
        if data:
            return _decode_base64url(data)
    for sub in part.get("parts", []):
        found = _first_plain_text(sub)
        if found is not None:
            return found
    return None


def _decode_base64url(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _strip_quotes(body: str) -> str:
    kept: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith(">")
            or stripped.startswith("From:")
            or stripped in _QUOTE_LINE_MARKERS
            or _QUOTE_HEADER.match(stripped)
        ):
            break
        kept.append(line)
    return "\n".join(kept).strip()
