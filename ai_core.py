"""SAP AI Core OAuth and OpenAI-compatible client configuration."""

from __future__ import annotations

import os
import time
import logging

import httpx
from openai import OpenAI

_access_token: str | None = None
_expires_at = 0.0
logger = logging.getLogger(__name__)


def model_name() -> str:
    """Return the model configured by the selected AI Core deployment."""
    return os.getenv("AICORE_MODEL_NAME", "gpt-4.1-nano")


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be configured.")
    return value


def _token() -> str:
    global _access_token, _expires_at
    if _access_token and time.time() < _expires_at:
        return _access_token

    response = httpx.post(
        f"{_required('AICORE_AUTH_URL').rstrip('/')}/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(_required("AICORE_CLIENT_ID"), _required("AICORE_CLIENT_SECRET")),
        timeout=15,
    )
    response.raise_for_status()
    token_data = response.json()
    _access_token = token_data["access_token"]
    _expires_at = time.time() + int(token_data.get("expires_in", 300)) - 60
    return _access_token


def client() -> OpenAI:
    """Create an OpenAI-compatible AI Core client with a fresh OAuth token."""
    deployment_id = _required("AICORE_DEPLOYMENT_ID")
    base_url = f"{_required('AICORE_BASE_URL').rstrip('/')}/v2/inference/deployments/{deployment_id}/"
    logger.info(
        "AI Core inference endpoint=%s model=%s resource_group=%s",
        base_url,
        model_name(),
        os.getenv("AICORE_RESOURCE_GROUP", "default"),
    )
    return OpenAI(
        base_url=base_url,
        api_key=_token(),
        default_headers={"AI-Resource-Group": os.getenv("AICORE_RESOURCE_GROUP", "default")},
    )