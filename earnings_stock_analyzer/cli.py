from __future__ import annotations

import argparse



def get_cli_args() -> argparse.Namespace:
    """Parse CLI arguments for analysis scripts."""
    parser = argparse.ArgumentParser(
        description="Analyze post-earnings reactions for one ticker or a batch universe."
    )
    parser.add_argument(
        "ticker",
        nargs="?",
        type=str,
        help="Stock ticker (e.g. AAPL). If omitted, caller may use an external CSV universe.",
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["library", "api"],
        default="library",
        help="Earnings-event source. Default: library.",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Alpha Vantage API key. Overrides environment variable ALPHAVANTAGE_API_KEY.",
    )
    parser.add_argument(
        "--require-api",
        action="store_true",
        help="Raise an error if --source api is selected but no API key is available.",
    )
    return parser.parse_args()
