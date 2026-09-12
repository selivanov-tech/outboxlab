import time

import httpx

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_EXPIRY_SKEW_SECONDS = 60.0


class GoogleAccessTokenProvider:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> None:
        self._client = client
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._token: str | None = None
        self._expires_at = 0.0

    async def token(self) -> str:
        if self._token is not None and time.monotonic() < self._expires_at:
            return self._token

        response = await self._client.post(
            _TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        payload = response.json()

        token: str = payload["access_token"]
        ttl = float(payload.get("expires_in", 3600))
        self._token = token
        self._expires_at = time.monotonic() + ttl - _EXPIRY_SKEW_SECONDS
        return token
