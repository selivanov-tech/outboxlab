import base64
import logging

import httpx
import pytest

from app.contexts.messaging.infrastructure.gmail.access_token import (
    GoogleAccessTokenProvider,
)
from app.contexts.messaging.infrastructure.gmail.receiver import (
    GmailApiReceiver,
    parse_message,
)


def _token(client: httpx.AsyncClient) -> GoogleAccessTokenProvider:
    return GoogleAccessTokenProvider(
        client, client_id="id", client_secret="secret", refresh_token="refresh"
    )


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_parse_message_extracts_fields() -> None:
    data = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "yes interested",
        "internalDate": "1700000000000",
        "payload": {
            "headers": [
                {"name": "From", "value": "Lead Person <Lead@Example.com>"},
                {"name": "Subject", "value": "Re: Hi"},
                {"name": "In-Reply-To", "value": "<abc@example.com>"},
                {"name": "References", "value": "<abc@example.com> <def@example.com>"},
            ]
        },
    }

    message = parse_message(data)

    assert message.provider_message_id == "m1"
    assert message.provider_thread_id == "t1"
    assert message.from_email == "lead@example.com"
    assert message.subject == "Re: Hi"
    assert message.snippet == "yes interested"
    assert message.in_reply_to_header == "<abc@example.com>"
    assert message.references_header == "<abc@example.com> <def@example.com>"
    assert message.received_at.year == 2023


def _message_response(message_id: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": message_id,
            "threadId": "t1",
            "labelIds": ["INBOX"],
            "snippet": "hi",
            "internalDate": "1700000000000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "lead@example.com"},
                    {"name": "Subject", "value": "Re: Hi"},
                ]
            },
        },
    )


async def test_fetch_new_bootstrap_returns_empty_and_baseline() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth2" in request.url.host:
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        if request.url.path.endswith("/profile"):
            return httpx.Response(200, json={"historyId": "5000"})
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        receiver = GmailApiReceiver(client, _token(client))
        result = await receiver.fetch_new(
            mailbox_email="ops@example.com", since_cursor=None
        )

    assert result.new_cursor == "5000"
    assert result.messages == ()


async def test_fetch_new_paginates_and_skips_deleted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        params = dict(request.url.params)
        if "oauth2" in request.url.host:
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        if path.endswith("/history"):
            if params.get("pageToken") == "page2":
                return httpx.Response(
                    200,
                    json={
                        "historyId": "5100",
                        "history": [
                            {
                                "messagesAdded": [
                                    {"message": {"id": "m2", "threadId": "t2"}}
                                ]
                            }
                        ],
                    },
                )
            return httpx.Response(
                200,
                json={
                    "historyId": "5050",
                    "nextPageToken": "page2",
                    "history": [
                        {"messagesAdded": [{"message": {"id": "m1", "threadId": "t1"}}]}
                    ],
                },
            )
        if path.endswith("/messages/m1"):
            return _message_response("m1")
        if path.endswith("/messages/m2"):
            return httpx.Response(404)
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        receiver = GmailApiReceiver(client, _token(client))
        result = await receiver.fetch_new(
            mailbox_email="ops@example.com", since_cursor="4000"
        )

    assert result.new_cursor == "5100"
    assert [m.provider_message_id for m in result.messages] == ["m1"]


async def test_fetch_new_rebaselines_on_stale_history() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "oauth2" in request.url.host:
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        if path.endswith("/history"):
            return httpx.Response(404, json={"error": "history id is too old"})
        if path.endswith("/profile"):
            return httpx.Response(200, json={"historyId": "9999"})
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        receiver = GmailApiReceiver(client, _token(client))
        result = await receiver.fetch_new(
            mailbox_email="ops@example.com", since_cursor="100"
        )

    assert result.new_cursor == "9999"
    assert result.messages == ()


def _labeled_message(
    message_id: str, labels: list[str], from_email: str
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": message_id,
            "threadId": "t1",
            "labelIds": labels,
            "snippet": "hi",
            "internalDate": "1700000000000",
            "payload": {
                "headers": [
                    {"name": "From", "value": from_email},
                    {"name": "Subject", "value": "Re: Hi"},
                ]
            },
        },
    )


async def test_fetch_new_filters_sent_non_inbox_and_self() -> None:
    added = [
        {"message": {"id": "keep"}},
        {"message": {"id": "sent"}},
        {"message": {"id": "notinbox"}},
        {"message": {"id": "self"}},
    ]
    bodies = {
        "keep": _labeled_message("keep", ["INBOX"], "lead@example.com"),
        "sent": _labeled_message("sent", ["SENT", "INBOX"], "ops@example.com"),
        "notinbox": _labeled_message("notinbox", ["DRAFT"], "lead@example.com"),
        "self": _labeled_message("self", ["INBOX"], "Ops <ops@example.com>"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "oauth2" in request.url.host:
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        if path.endswith("/history"):
            return httpx.Response(
                200, json={"historyId": "5100", "history": [{"messagesAdded": added}]}
            )
        for message_id, response in bodies.items():
            if path.endswith(f"/messages/{message_id}"):
                return response
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        receiver = GmailApiReceiver(client, _token(client))
        result = await receiver.fetch_new(
            mailbox_email="ops@example.com", since_cursor="4000"
        )

    assert [m.provider_message_id for m in result.messages] == ["keep"]


def test_parse_message_extracts_dequoted_body() -> None:
    body = (
        "Yes, I'm interested — let's talk.\n"
        "\n"
        "On Mon, Jun 2, 2025 at 10:00 AM Me <ops@example.com> wrote:\n"
        "> our pitch, book a call\n"
    )
    data = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["INBOX"],
        "snippet": "short preview",
        "internalDate": "1700000000000",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "lead@example.com"},
                {"name": "Subject", "value": "Re: Hi"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64url(body)}},
                {"mimeType": "text/html", "body": {"data": _b64url("<p>x</p>")}},
            ],
        },
    }

    message = parse_message(data)

    assert message.body_text == "Yes, I'm interested — let's talk."
    assert message.snippet == "short preview"


def test_parse_message_body_empty_without_plain_part() -> None:
    data = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["INBOX"],
        "snippet": "preview",
        "internalDate": "1700000000000",
        "payload": {
            "mimeType": "text/html",
            "headers": [{"name": "From", "value": "lead@example.com"}],
            "body": {"data": _b64url("<p>html only</p>")},
        },
    }

    assert parse_message(data).body_text == ""


async def test_fetch_new_logs_warning_on_history_expired(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth2" in request.url.host:
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        if request.url.path.endswith("/history"):
            return httpx.Response(404, json={"error": "history id is too old"})
        if request.url.path.endswith("/profile"):
            return httpx.Response(200, json={"historyId": "9999"})
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        receiver = GmailApiReceiver(client, _token(client))
        with caplog.at_level(logging.WARNING):
            result = await receiver.fetch_new(
                mailbox_email="ops@example.com", since_cursor="100"
            )

    assert result.new_cursor == "9999"
    assert "history expired" in caplog.text
