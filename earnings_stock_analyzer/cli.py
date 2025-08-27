import argparse

# Command-line interface to get user input for ticker symbol and data source
def get_cli_args():
    parser = argparse.ArgumentParser(description="Analyze earnings data for a stock or multiple stocks.")
    parser.add_argument("ticker", nargs="?", type=str,
                        help="Stock ticker (e.g., AAPL) or a list (for batch). If omitted, uses CSV in /data.")
    parser.add_argument(
        "--source",
        type=str,
        choices=["library", "api"],
        default="library",
        help="Source of earnings data (default: library). Choose 'library' or 'api'."
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Alpha Vantage API key (overrides .env and environment)."
    )
    parser.add_argument(
        "--require-api",
        action="store_true",
        help="If set and --source api is chosen but no key is available, exit with error instead of falling back."
    )
    return parser.parse_args()
