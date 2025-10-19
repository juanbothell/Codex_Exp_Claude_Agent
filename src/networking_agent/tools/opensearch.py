"""Tooling for generating and executing OpenSearch queries."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from opensearchpy import OpenSearch

from claude_agent_sdk.tools import Tool


LOGGER = logging.getLogger(__name__)


@dataclass
class OpenSearchQueryTool(Tool):
    """Generate and run OpenSearch DSL queries for networking analytics."""

    name: str = "generate_and_execute_opensearch_query"
    description: str = (
        "Translate a natural language networking investigation request into an "
        "OpenSearch query, execute it, and return the JSON results."
    )
    llm: Any = None
    client: OpenSearch | None = None
    default_index: str | None = None

    def __post_init__(self) -> None:
        if self.llm is None:
            msg = "OpenSearchQueryTool requires an initialized Claude client in the `llm` field."
            raise ValueError(msg)
        if self.client is None:
            msg = "OpenSearchQueryTool requires an initialized OpenSearch client."
            raise ValueError(msg)

    def _question_to_query(self, question: str) -> dict[str, Any]:
        prompt = (
            "You are a networking search expert. Convert the user's request into an "
            "OpenSearch query DSL JSON payload. Only respond with valid JSON.\n"
            f"Request: {question}\nJSON:"
        )
        LOGGER.debug("Generating OpenSearch query for question: %s", question)
        response = self.llm.complete(prompt)
        if hasattr(response, "text"):
            raw_text = response.text
        elif hasattr(response, "content"):
            raw_text = response.content
        else:
            raw_text = str(response)
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            msg = "Claude response was not valid JSON for OpenSearch query generation."
            LOGGER.error(msg)
            raise ValueError(msg) from exc
        LOGGER.debug("Generated query payload: %s", payload)
        return payload

    def _execute_query(self, query: dict[str, Any]) -> Any:
        LOGGER.info("Executing OpenSearch query")
        index = self.default_index or query.pop("index", None)
        if index is None:
            msg = "OpenSearch query must specify an index either in the tool config or payload."
            LOGGER.error(msg)
            raise ValueError(msg)
        result = self.client.search(index=index, body=query)
        LOGGER.debug("Received OpenSearch response")
        return json.dumps(result, indent=2, sort_keys=True)

    def __call__(self, question: str, **_: Any) -> Any:
        query = self._question_to_query(question)
        return self._execute_query(query)
