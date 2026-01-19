import csv
from pathlib import Path

# Project root auto-detect (works if this file is in root or in /scripts)
THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parent if THIS.parent.name != "scripts" else THIS.parent.parent

QDIR = PROJECT_ROOT / "output" / "quadrants"

# Thresholds to analyze
THRESHOLDS = [5, 7, 8, 9, 10, 11]

# Internal scenario names
SCEN_KEYS = ["pos_then_up", "pos_then_down", "neg_then_up", "neg_then_down"]


def is_detailed_csv(p: Path) -> bool:
    return p.name.endswith("_quadrants_detailed.csv")


def main():
    QDIR.mkdir(parents=True, exist_ok=True)

    # For each threshold store: total_events, counts per scenario
    stats = {
        th: {
            "total": 0,
            "counts": {k: 0 for k in SCEN_KEYS}
        }
        for th in THRESHOLDS
    }

    bad_files = []

    # ---- SINGLE PASS THROUGH ALL FILES ----
    for path in sorted(QDIR.glob("*_quadrants_detailed.csv")):
        if not is_detailed_csv(path):
            continue

        try:
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        c2o = float(row["close_to_open_pct"])
                        o2c = float(row["open_to_close_pct"])
                    except (KeyError, ValueError):
                        continue

                    if o2c == 0:
                        continue  # direction undefined

                    # Determine scenario
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
                            continue

                    # Evaluate this event for ALL thresholds
                    abs_gap = abs(c2o)
                    for th in THRESHOLDS:
                        if abs_gap >= th:
                            stats[th]["total"] += 1
                            stats[th]["counts"][scenario] += 1

        except Exception:
            bad_files.append(path.name)
            continue

    # ---- WRITE RESULTS FOR EACH THRESHOLD ----
    for th in THRESHOLDS:
        out_path = QDIR / f"quadrants_market_gap{th}_averages.csv"
        total = stats[th]["total"]
        counts = stats[th]["counts"]

        if total == 0:
            print(f"❗ No earnings events with |C→O| >= {th}% found.")
            continue

        perc = {k: round(100 * counts[k] / total, 4) for k in SCEN_KEYS}

        continuation = perc["pos_then_up"] + perc["neg_then_down"]
        reversal = perc["pos_then_down"] + perc["neg_then_up"]
        momentum_bias = round(continuation - reversal, 4)

        with out_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Metric", "Value"])
            w.writerow(["threshold_gap_pct", th])
            w.writerow(["total_events", total])
            for k in SCEN_KEYS:
                w.writerow([f"count_{k}", counts[k]])
            for k in SCEN_KEYS:
                w.writerow([f"pct_{k}", perc[k]])
            w.writerow(["momentum_bias_pct", momentum_bias])

        print(f"✅ Wrote results for >= {th}% gap → {out_path}")

    if bad_files:
        print("\n⚠️ Skipped files due to read errors:")
        for name in bad_files:
            print(" -", name)


if __name__ == "__main__":
    main()
