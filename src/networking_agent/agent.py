"""Create a Claude agent tailored for networking analytics."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from boto3 import Session
from claude_agent_sdk.agent import Agent
from claude_agent_sdk.memory import ShortTermMemory
from claude_agent_sdk.orchestration import AgentOrchestrator
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.helpers.aws4auth import AWSV4SignerAuth

from .config import AgentConfig
from .bedrock import BedrockClaudeClient
from .tools.opensearch import OpenSearchQueryTool
from .tools.sql import AthenaSQLTool


LOGGER = logging.getLogger(__name__)


@dataclass
class NetworkingAgent:
    """High level interface that wires the Claude agent and tools."""

    config: AgentConfig

    def _build_boto_session(self) -> Session:
        profile = self.config.aws_profile or os.getenv("AWS_PROFILE")
        LOGGER.info("Initializing boto3 session with profile=%s", profile)
        if profile:
            return Session(profile_name=profile)
        return Session()

    def _build_llm(self, boto_session: Session) -> BedrockClaudeClient:
        LOGGER.debug(
            "Creating Bedrock Claude client for model %s in region %s",
            self.config.model,
            self.config.bedrock.region,
        )
        return BedrockClaudeClient(
            model=self.config.model,
            session=boto_session,
            region_name=self.config.bedrock.region,
            endpoint_url=self.config.bedrock.endpoint_url,
            max_tokens=self.config.bedrock.max_tokens,
            temperature=self.config.bedrock.temperature,
            guardrail_id=self.config.bedrock.guardrail_id,
            guardrail_version=self.config.bedrock.guardrail_version,
        )

    def _build_tools(self, llm: BedrockClaudeClient, boto_session: Session) -> list[Any]:
        LOGGER.debug("Creating tool instances")
        sql_tool = AthenaSQLTool(
            llm=llm,
            database=self.config.athena.database,
            workgroup=self.config.athena.workgroup,
            output_s3_uri=self.config.athena.output_s3_uri,
            catalog=self.config.athena.catalog,
            boto3_session=boto_session,
        )
        auth = None
        if self.config.opensearch.username and self.config.opensearch.password:
            auth = (self.config.opensearch.username, self.config.opensearch.password)
        elif self.config.opensearch.region:
            credentials = boto_session.get_credentials()
            if credentials is None:
                msg = "Unable to resolve AWS credentials for signing OpenSearch requests."
                raise RuntimeError(msg)
            auth = AWSV4SignerAuth(credentials, self.config.opensearch.region, self.config.opensearch.service)
        search_client = OpenSearch(
            hosts=self.config.opensearch.hosts,
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )
        opensearch_tool = OpenSearchQueryTool(
            llm=llm,
            client=search_client,
            default_index=self.config.opensearch.default_index,
        )
        return [sql_tool, opensearch_tool]

    def create(self) -> AgentOrchestrator:
        boto_session = self._build_boto_session()
        llm = self._build_llm(boto_session)
        tools = self._build_tools(llm, boto_session)
        memory = ShortTermMemory(window=self.config.memory_window)
        agent = Agent(
            name="Networking Q&A Assistant",
            system_prompt=self.config.system_prompt,
            tools=tools,
            client=llm,
            memory=memory,
            tags=self.config.tags,
        )
        LOGGER.info("Agent created with %d tools", len(tools))
        return AgentOrchestrator(agent=agent, max_turns=self.config.max_turns)


def create_networking_agent(config: AgentConfig) -> AgentOrchestrator:
    """Factory for building the orchestrator from configuration."""

    return NetworkingAgent(config).create()
