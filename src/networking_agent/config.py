"""Configuration models for the networking Claude agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AthenaConfig:
    """Settings required for running Athena queries."""

    database: str
    workgroup: str
    output_s3_uri: str
    catalog: Optional[str] = None


@dataclass
class OpenSearchConfig:
    """Connection information for OpenSearch."""

    hosts: list[str]
    username: Optional[str] = None
    password: Optional[str] = None
    region: Optional[str] = None
    service: str = "es"
    default_index: Optional[str] = None


@dataclass
class BedrockConfig:
    """Settings for communicating with AWS Bedrock."""

    region: Optional[str] = None
    endpoint_url: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.0
    guardrail_id: Optional[str] = None
    guardrail_version: Optional[str] = None


@dataclass
class AgentConfig:
    """Top level configuration for the networking agent."""

    model: str
    athena: AthenaConfig
    opensearch: OpenSearchConfig
    bedrock: BedrockConfig = field(default_factory=BedrockConfig)
    aws_profile: Optional[str] = None
    system_prompt: str = (
        "You are a senior networking domain expert who leverages structured "
        "data sources to answer analytical questions about networks, traffic, "
        "and infrastructure."
    )
    max_turns: int = 32
    memory_window: int = 10
    tags: list[str] = field(default_factory=lambda: ["networking", "analytics", "aws"])
