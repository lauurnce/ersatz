"""Digi-Key OAuth2 client credentials flow with token refresh."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from ersatz.providers.errors import AuthError, MissingCredentialsError, ProviderResponseError
from ersatz.providers.http import HttpClient

# Refresh this long before the token expires, so a request never carries a
# token that runs out in flight.
REFRESH_MARGIN = timedelta(seconds=60)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TokenManager:
    def __init__(
        self,
        http: HttpClient,
        token_url: str,
        client_id: str,
        client_secret: str,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        if not client_id or not client_secret:
            raise MissingCredentialsError(
                "digikey",
                "DIGIKEY_CLIENT_ID and DIGIKEY_CLIENT_SECRET must be set in .env",
            )
        self._http = http
        self._url = token_url
        self._id = client_id
        self._secret = client_secret
        self._clock = clock
        self._token: str | None = None
        self._expires_at = datetime.min.replace(tzinfo=UTC)

    def token(self) -> str:
        """Return a valid access token, fetching a new one when needed."""
        if self._token is None or self._clock() >= self._expires_at - REFRESH_MARGIN:
            self._fetch()
        assert self._token is not None  # noqa: S101 - set by _fetch
        return self._token

    def invalidate(self) -> None:
        """Forget the token, for example after the API answered 401."""
        self._token = None

    def _fetch(self) -> None:
        response = self._http.request(
            "POST",
            self._url,
            data={
                "client_id": self._id,
                "client_secret": self._secret,
                "grant_type": "client_credentials",
            },
        )
        if response.status_code in (400, 401, 403):
            raise AuthError(
                "digikey",
                f"token request rejected (HTTP {response.status_code}); "
                "check DIGIKEY_CLIENT_ID, DIGIKEY_CLIENT_SECRET and the sandbox setting",
            )
        if response.status_code != 200:
            raise ProviderResponseError(
                "digikey", f"token request failed with HTTP {response.status_code}"
            )
        body = response.json()
        try:
            self._token = str(body["access_token"])
            lifetime = int(body["expires_in"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderResponseError("digikey", "token response missing fields") from exc
        self._expires_at = self._clock() + timedelta(seconds=lifetime)
