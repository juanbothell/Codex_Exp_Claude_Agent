# Networking Claude Agent

This project provides a networking-focused question answering assistant built with the
[Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk). The agent is equipped with
specialized tooling for translating natural language requests into:

* AWS Athena SQL queries executed via `awswrangler`.
* OpenSearch DSL queries executed against an OpenSearch cluster.

The assistant is designed for infrastructure and networking investigations, allowing analysts to
mix conversational reasoning with direct access to structured data sources.

## Getting started

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Provide AWS credentials via the `AWS_PROFILE` environment variable or your usual boto3
   configuration files. The agent will automatically pick up the profile when instantiating the
   Athena and OpenSearch clients.

3. Launch the CLI, specifying the Athena and OpenSearch connection details:

   ```bash
   python main.py \
     --athena-database network_analytics \
     --athena-output s3://my-query-results/athena/ \
    --opensearch-host https://search-network.example.com \
    --opensearch-index network-logs-* \
    --aws-profile networking
   ```

   Additional options are available via `python main.py --help`.

## Configuration

The agent is configured via the `AgentConfig` dataclass defined in
`src/networking_agent/config.py`. The configuration controls the Claude model, Athena and
OpenSearch connection settings, and prompt/memory parameters. The helper function
`create_networking_agent` wires these together into an `AgentOrchestrator` ready to answer
questions.

## Tooling overview

* `AthenaSQLTool` – Converts networking questions into Athena SQL using the Claude LLM, executes
  them via AWS Wrangler, and returns results in Markdown.
* `OpenSearchQueryTool` – Converts investigative questions into OpenSearch DSL, runs the search, and
  returns the raw JSON response.

Both tools rely on the Claude Agent SDK's tool interface, so they can be composed into broader
workflows or reused independently if needed.
