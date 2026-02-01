#!/usr/bin/env python3
"""Entry point for the Resume Strategy & Tailoring Agent.

Usage:
    python agent.py              # Interactive CLI mode
    python agent.py --jd FILE    # Parse JD from file
    python agent.py --help       # Show help
"""

import argparse
import sys

from resume_agent.agent import ResumeTailoringAgent, interactive_cli


def main():
    parser = argparse.ArgumentParser(
        description="Resume Strategy & Tailoring Agent"
    )
    parser.add_argument(
        "--jd",
        type=str,
        help="Path to a file containing the job description",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="",
        help="Label for the output version (e.g., company name)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run without prompts (requires --jd)",
    )

    args = parser.parse_args()

    if args.jd:
        with open(args.jd, "r") as f:
            jd_text = f.read()

        agent = ResumeTailoringAgent()
        package = agent.run_full_loop(jd_text, label=args.label)
        output = agent.render_full_output(package)
        print(output)

        if not args.non_interactive:
            from resume_agent.icp import render_gap_map

            missing = [
                e for e in agent.gap_map if e.status in ("partial", "missing")
            ]
            if missing:
                print("\n--- Gaps detected. Run interactively to fill them. ---")
    else:
        interactive_cli()


if __name__ == "__main__":
    main()
