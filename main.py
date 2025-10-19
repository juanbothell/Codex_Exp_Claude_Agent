"""CLI entry point for the networking Claude agent."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from networking_agent import create_networking_agent
from networking_agent.config import AgentConfig, AthenaConfig, OpenSearchConfig

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="claude-3-opus")
    parser.add_argument("--athena-database", required=True)
    parser.add_argument("--athena-workgroup", default="primary")
    parser.add_argument("--athena-output", required=True)
    parser.add_argument("--athena-catalog")
    parser.add_argument("--opensearch-host", action="append", required=True)
    parser.add_argument("--opensearch-user")
    parser.add_argument("--opensearch-password")
    parser.add_argument("--opensearch-region")
    parser.add_argument("--opensearch-index")
    parser.add_argument("--aws-profile")
    parser.add_argument("--system-prompt")
    parser.add_argument("--max-turns", type=int, default=16)
    parser.add_argument("--memory-window", type=int, default=8)
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> AgentConfig:
    athena = AthenaConfig(
        database=args.athena_database,
        workgroup=args.athena_workgroup,
        output_s3_uri=args.athena_output,
        catalog=args.athena_catalog,
    )
    opensearch = OpenSearchConfig(
        hosts=args.opensearch_host,
        username=args.opensearch_user,
        password=args.opensearch_password,
        region=args.opensearch_region,
        default_index=args.opensearch_index,
    )
    system_prompt = args.system_prompt or AgentConfig.__dataclass_fields__["system_prompt"].default
    return AgentConfig(
        model=args.model,
        athena=athena,
        opensearch=opensearch,
        aws_profile=args.aws_profile,
        system_prompt=system_prompt,
        max_turns=args.max_turns,
        memory_window=args.memory_window,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config = build_config(args)
    orchestrator = create_networking_agent(config)
    LOGGER.info("Agent ready. Enter networking questions (Ctrl-D to exit).")
    try:
        while True:
            question = input("network-agent> ").strip()
            if not question:
                continue
            response = orchestrator.run(question)
            if isinstance(response, (dict, list)):
                print(json.dumps(response, indent=2))
            else:
                print(response)
    except EOFError:
        LOGGER.info("Session terminated by user")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
