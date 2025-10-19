"""Utilities for invoking Claude models hosted on AWS Bedrock."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Iterable

from boto3 import Session
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

LOGGER = logging.getLogger(__name__)

ANTHROPIC_VERSION = "bedrock-2023-05-31"


@dataclass
class BedrockCompletion:
    """Lightweight completion object mimicking Anthropic's response."""

    text: str

    @property
    def content(self) -> str:
        """Alias used by various tools when reading the LLM output."""

        return self.text


class BedrockClaudeClient:
    """Minimal client for interacting with Claude models via AWS Bedrock."""

    def __init__(
        self,
        *,
        model: str,
        session: Session | None = None,
        region_name: str | None = None,
        endpoint_url: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        guardrail_id: str | None = None,
        guardrail_version: str | None = None,
    ) -> None:
        self.model = model
        self._session = session or Session()
        self._region_name = region_name
        self._endpoint_url = endpoint_url
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._guardrail_id = guardrail_id
        self._guardrail_version = guardrail_version
        self._client: BaseClient = self._session.client(
            "bedrock-runtime",
            region_name=region_name,
            endpoint_url=endpoint_url,
        )

    def _prepare_content(self, prompt: str) -> list[dict[str, Any]]:
        return [{"type": "text", "text": prompt}]

    def _prepare_system(self, system_prompt: str | None) -> list[dict[str, Any]] | None:
        if not system_prompt:
            return None
        return [{"type": "text", "text": system_prompt}]

    def _extract_text(self, content: Iterable[dict[str, Any]]) -> str:
        return "".join(part.get("text", "") for part in content if part.get("type") == "text")

    def complete(self, prompt: str, **kwargs: Any) -> BedrockCompletion:
        """Issue a text completion request to the Bedrock runtime."""

        max_tokens = int(kwargs.get("max_tokens", self._max_tokens))
        temperature = float(kwargs.get("temperature", self._temperature))
        system_prompt = kwargs.get("system") or kwargs.get("system_prompt")
        guardrail_id = kwargs.get("guardrail_id", self._guardrail_id)
        guardrail_version = kwargs.get("guardrail_version", self._guardrail_version)

        body: dict[str, Any] = {
            "anthropic_version": ANTHROPIC_VERSION,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": self._prepare_content(prompt),
                }
            ],
        }
        system_content = self._prepare_system(system_prompt)
        if system_content is not None:
            body["system"] = system_content
        if guardrail_id and guardrail_version:
            body["guardrailIdentifier"] = guardrail_id
            body["guardrailVersion"] = guardrail_version

        try:
            LOGGER.debug(
                "Invoking Bedrock Claude model %s in region=%s", self.model, self._region_name
            )
            response = self._client.invoke_model(
                modelId=self.model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
        except (BotoCoreError, ClientError) as exc:
            LOGGER.exception("Bedrock invocation failed")
            raise RuntimeError("Failed to invoke Claude model on Bedrock") from exc

        raw_body = response.get("body")
        if hasattr(raw_body, "read"):
            payload = raw_body.read()
        else:
            payload = raw_body
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        parsed = json.loads(payload)
        text = self._extract_text(parsed.get("content", []))
        return BedrockCompletion(text=text)


__all__ = ["BedrockClaudeClient", "BedrockCompletion"]
