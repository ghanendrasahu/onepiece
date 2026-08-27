"""OAuth2 social login providers (Google, GitHub).

Implements the OAuth2 authorization code flow for social login:
1. Client redirects user to provider's authorization URL
2. User authorizes the app
3. Provider redirects back with an authorization code
4. Backend exchanges the code for an access token
5. Backend uses the token to fetch user info
6. Backend creates/finds user and issues JWT

For development, supports a mock mode that bypasses the real OAuth flow.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


@dataclass
class SocialUserInfo:
    """User info returned from a social provider."""

    provider: str
    provider_user_id: str
    email: str
    name: str
    avatar_url: str | None = None


class SocialProvider(Protocol):
    """Protocol for social login providers."""

    @property
    def name(self) -> str: ...

    async def exchange_code(self, code: str, redirect_uri: str) -> SocialUserInfo: ...

    def get_authorization_url(self, redirect_uri: str, state: str) -> str: ...


class GoogleProvider:
    """Google OAuth2 provider.

    Setup:
    1. Go to https://console.cloud.google.com/apis/credentials
    2. Create OAuth 2.0 Client ID
    3. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self._client_id = client_id or os.getenv("GOOGLE_CLIENT_ID")
        self._client_secret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "google"

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        return (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={self._client_id}&"
            f"redirect_uri={redirect_uri}&"
            "response_type=code&"
            "scope=openid email profile&"
            f"state={state}"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> SocialUserInfo:
        if not self._client_id or not self._client_secret:
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET required")

        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)

        # Exchange code for tokens
        token_resp = await self._client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        # Fetch user info
        user_resp = await self._client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        user_resp.raise_for_status()
        user = user_resp.json()

        return SocialUserInfo(
            provider="google",
            provider_user_id=user["id"],
            email=user["email"],
            name=user.get("name", user["email"].split("@")[0]),
            avatar_url=user.get("picture"),
        )

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


class GitHubProvider:
    """GitHub OAuth2 provider.

    Setup:
    1. Go to https://github.com/settings/developers
    2. Create OAuth App
    3. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET env vars
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self._client_id = client_id or os.getenv("GITHUB_CLIENT_ID")
        self._client_secret = client_secret or os.getenv("GITHUB_CLIENT_SECRET")
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "github"

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        return (
            "https://github.com/login/oauth/authorize?"
            f"client_id={self._client_id}&"
            f"redirect_uri={redirect_uri}&"
            "scope=user:email&"
            f"state={state}"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> SocialUserInfo:
        if not self._client_id or not self._client_secret:
            raise ValueError("GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET required")

        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)

        # Exchange code for token
        token_resp = await self._client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        if "error" in tokens:
            raise ValueError(f"GitHub OAuth error: {tokens['error_description']}")

        access_token = tokens["access_token"]

        # Fetch user info
        user_resp = await self._client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        user_resp.raise_for_status()
        user = user_resp.json()

        # Fetch primary email if not public
        email = user.get("email")
        if not email:
            emails_resp = await self._client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            emails_resp.raise_for_status()
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary")), None)
            if primary:
                email = primary["email"]

        if not email:
            raise ValueError("GitHub account has no verified email")

        return SocialUserInfo(
            provider="github",
            provider_user_id=str(user["id"]),
            email=email,
            name=user.get("name") or user.get("login", email.split("@")[0]),
            avatar_url=user.get("avatar_url"),
        )

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


class MockSocialProvider:
    """Mock provider for development/testing without real OAuth setup.

    Accepts any code and returns a fake user based on the code value.
    """

    @property
    def name(self) -> str:
        return "mock"

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        return f"{redirect_uri}?code=mock-code-{state}&state={state}"

    async def exchange_code(self, code: str, redirect_uri: str) -> SocialUserInfo:
        # Extract email from mock code or use default
        if "mock-code-" in code:
            email = f"{code.replace('mock-code-', '')}@example.com"
        else:
            email = f"{code}@example.com"

        return SocialUserInfo(
            provider="mock",
            provider_user_id=f"mock-{code}",
            email=email,
            name=email.split("@")[0],
            avatar_url=None,
        )


def build_social_provider(provider_name: str) -> SocialProvider:
    """Build the appropriate social provider."""
    if provider_name == "google":
        provider = GoogleProvider()
        if not provider._client_id:
            log.info("Google OAuth not configured, using mock provider")
            return MockSocialProvider()
        return provider
    elif provider_name == "github":
        provider = GitHubProvider()
        if not provider._client_id:
            log.info("GitHub OAuth not configured, using mock provider")
            return MockSocialProvider()
        return provider
    else:
        log.warning("Unknown social provider: %s, using mock", provider_name)
        return MockSocialProvider()
