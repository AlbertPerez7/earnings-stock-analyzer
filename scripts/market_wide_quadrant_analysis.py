from __future__ import annotations

import csv
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parent.parent if _THIS.parent.name == "scripts" else _THIS.parent

QDIR = PROJECT_ROOT / "output" / "quadrants"

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
# Absolute overnight gap thresholds (|Close->Open| %) to test.
# For each threshold, only earnings events where the gap exceeds that
# level are included, allowing assessment of whether stronger reactions
# are associated with more consistent continuation behaviour.
THRESHOLDS = [5, 7, 8, 9, 10, 11]

SCEN_KEYS = ["pos_then_up", "pos_then_down", "neg_then_up", "neg_then_down"]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    QDIR.mkdir(parents=True, exist_ok=True)

    # Accumulate counts for every threshold in a single pass over all files.
    stats: dict[int, dict] = {
        th: {"total": 0, "counts": {k: 0 for k in SCEN_KEYS}}
        for th in THRESHOLDS
    }
    bad_files: list[str] = []

    for path in sorted(QDIR.glob("*_quadrants_detailed.csv")):
        try:
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        c2o = float(row["close_to_open_pct"])
                        o2c = float(row["open_to_close_pct"])
                    except (KeyError, ValueError):
                        continue

                    # Skip events with undefined intraday direction
                    if o2c == 0:
                        continue

                    # Prefer the pre-computed scenario label when available;
                    # fall back to re-deriving it from the raw return signs.
                    scenario = row.get("scenario", "").strip()
                    if scenario not in SCEN_KEYS:
                        if c2o > 0 and o2c > 0:
                            scenario = "pos_then_up"
                        elif c2o > 0 and o2c < 0:
                            scenario = "pos_then_down"
                        elif c2o < 0 and o2c > 0:
                            scenario = "neg_then_up"
                        elif c2o < 0 and o2c < 0:
                            scenario = "neg_then_down"
                        else:
                            continue  # c2o == 0, no directional gap

                    abs_gap = abs(c2o)
                    for th in THRESHOLDS:
                        if abs_gap >= th:
                            stats[th]["total"] += 1
                            stats[th]["counts"][scenario] += 1

        except Exception:
            bad_files.append(path.name)
            logger.exception("Failed to read %s", path.name)

    # Write one output CSV per threshold
    for th in THRESHOLDS:
        total  = stats[th]["total"]
        counts = stats[th]["counts"]

        if total == 0:
            logger.warning("No earnings events with |C->O| >= %d%% found.", th)
            continue

        perc = {k: round(100 * counts[k] / total, 4) for k in SCEN_KEYS}
        continuation  = perc["pos_then_up"] + perc["neg_then_down"]
        reversal      = perc["pos_then_down"] + perc["neg_then_up"]
        momentum_bias = round(continuation - reversal, 4)

        out_path = QDIR / f"quadrants_market_gap{th}_averages.csv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Metric", "Value"])
            w.writerow(["threshold_gap_pct", th])
            w.writerow(["total_events", total])
            for k in SCEN_KEYS:
                w.writerow([f"count_{k}", counts[k]])
            for k in SCEN_KEYS:
                w.writerow([f"pct_{k}", perc[k]])
            w.writerow(["continuation_pct", round(continuation, 4)])
            w.writerow(["reversal_pct", round(reversal, 4)])
            w.writerow(["momentum_bias_pct", momentum_bias])

        logger.info("Wrote results for |gap| >= %d%% -> %s", th, out_path)

    if bad_files:
        logger.warning("Skipped %d file(s) due to read errors:", len(bad_files))
        for name in bad_files:
            logger.warning("  - %s", name)


if __name__ == "__main__":
    main()
