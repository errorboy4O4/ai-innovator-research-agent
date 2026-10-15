"""CLI entry point for the research agent."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").date()


def cmd_run(args):
    """Run the research agent pipeline."""
    from .pipeline import run_pipeline

    pack_dir = Path(args.pack)
    if not pack_dir.is_dir():
        print(f"Error: pack directory not found: {pack_dir}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out) if args.out else Path("out")
    as_of = _parse_date(args.as_of)

    if getattr(args, "dry_run", False):
        from .pipeline import run_scan

        run_scan(pack_dir, as_of)
        return

    brief, trace = run_pipeline(
        ticker=args.ticker,
        pack_dir=pack_dir,
        as_of=as_of,
        out_dir=out_dir,
        variant=args.variant,
    )
    print(f"\n{'=' * 60}")
    print(f"BRIEF ({trace.variant} variant, {trace.brief_word_count} words)")
    print(f"{'=' * 60}\n")
    print(brief)


def cmd_scan(args):
    """Run sanitise + scan only (no API key needed)."""
    from .pipeline import run_scan

    pack_dir = Path(args.pack)
    if not pack_dir.is_dir():
        print(f"Error: pack directory not found: {pack_dir}", file=sys.stderr)
        sys.exit(1)

    as_of = _parse_date(args.as_of)
    run_scan(pack_dir, as_of)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    load_dotenv()
    _setup_logging()

    parser = argparse.ArgumentParser(
        prog="research-agent",
        description="AI research agent for source-grounded investment briefs",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    run_parser = subparsers.add_parser("run", help="Run the full pipeline")
    run_parser.add_argument("--ticker", required=True, help="NSE ticker symbol")
    run_parser.add_argument("--pack", required=True, help="Path to research pack directory")
    run_parser.add_argument("--as-of", default="2026-09-23", help="As-of date (YYYY-MM-DD)")
    run_parser.add_argument("--out", default="out", help="Output directory")
    run_parser.add_argument(
        "--variant",
        choices=["baseline", "triage", "full"],
        default="full",
        help="Pipeline variant to run",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run ingest and sanitise only without LLM API key",
    )
    run_parser.set_defaults(func=cmd_run)

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan documents (no API key needed)")
    scan_parser.add_argument("--pack", required=True, help="Path to research pack directory")
    scan_parser.add_argument("--as-of", default="2026-09-23", help="As-of date (YYYY-MM-DD)")
    scan_parser.set_defaults(func=cmd_scan)

    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
