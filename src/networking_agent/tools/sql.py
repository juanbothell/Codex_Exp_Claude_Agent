"""Tooling for generating and running Athena SQL queries."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import awswrangler as wr
from boto3 import Session

from claude_agent_sdk.tools import Tool


LOGGER = logging.getLogger(__name__)


@dataclass
class AthenaSQLTool(Tool):
    """Tool that converts a natural language networking question into Athena SQL."""

    name: str = "generate_and_execute_sql"
    description: str = (
        "Translate a natural language networking analytics question into an AWS "
        "Athena SQL query, execute it, and return the results."
    )
    llm: Any = None
    database: str = ""
    workgroup: str = "primary"
    output_s3_uri: str = ""
    catalog: str | None = None
    boto3_session: Session | None = None

    def __post_init__(self) -> None:
        if self.llm is None:
            msg = "AthenaSQLTool requires an initialized Claude client in the `llm` field."
            raise ValueError(msg)

    def _ensure_session(self) -> Session:
        if self.boto3_session is not None:
            return self.boto3_session
        profile = os.getenv("AWS_PROFILE")
        LOGGER.debug("Using AWS profile: %s", profile)
        self.boto3_session = Session(profile_name=profile) if profile else Session()
        return self.boto3_session

    def _question_to_sql(self, question: str) -> str:
        prompt = (
            "You are an expert networking data analyst. Convert the following question "
            "into a syntactically correct Athena SQL query. Only generate the SQL query.\n"
            f"Question: {question}\nSQL:"
        )
        LOGGER.debug("Generating SQL for question: %s", question)
        response = self.llm.complete(prompt)
        if hasattr(response, "text"):
            raw_text = response.text
        elif hasattr(response, "content"):
            raw_text = response.content
        else:
            raw_text = str(response)
        sql = raw_text.strip()
        LOGGER.debug("Generated SQL: %s", sql)
        return sql

    def _run_sql(self, sql: str) -> Any:
        LOGGER.info("Executing Athena query")
        session = self._ensure_session()
        df = wr.athena.read_sql_query(
            sql,
            database=self.database,
            workgroup=self.workgroup,
            ctas_approach=False,
            s3_output=self.output_s3_uri,
            catalog=self.catalog,
            boto3_session=session,
        )
        if df.empty:
            LOGGER.info("Query returned no rows")
            return "The query did not return any rows."
        markdown = df.to_markdown(index=False)
        LOGGER.debug("Returning %d rows", len(df))
        return markdown

    def __call__(self, question: str, **_: Any) -> Any:
        sql = self._question_to_sql(question)
        return self._run_sql(sql)
