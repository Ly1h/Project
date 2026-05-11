from __future__ import annotations

import argparse
from pathlib import Path

from .workflows import RepoGuardianWorkflow, ResearchFactoryWorkflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Workbench CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    repo = sub.add_parser("repo-guardian", help="Run repository diagnosis workflow")
    repo.add_argument("--workspace", required=True)
    repo.add_argument("--goal", required=True)

    research = sub.add_parser("research-factory", help="Generate research project artifacts")
    research.add_argument("--workspace", required=True)
    research.add_argument("--goal", required=True)

    args = parser.parse_args()

    if args.command == "repo-guardian":
        workflow = RepoGuardianWorkflow(Path(args.workspace), args.goal)
    elif args.command == "research-factory":
        workflow = ResearchFactoryWorkflow(Path(args.workspace), args.goal)
    else:
        raise SystemExit(f"Unknown command: {args.command}")

    state = workflow.run()
    print(f"Run ID: {state.run_id}")
    print(f"Workspace: {state.workspace}")
    print("Artifacts:")
    for name, path in state.artifacts.items():
        print(f"  - {name}: {path}")


if __name__ == "__main__":
    main()
