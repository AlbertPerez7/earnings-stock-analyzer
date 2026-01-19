import csv
from pathlib import Path
from datetime import datetime, date

# -------------------------------------------
# Detect project root even if script is in /scripts
# -------------------------------------------
THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parent.parent if THIS.parent.name == "scripts" else THIS.parent

QDIR = PROJECT_ROOT / "output" / "quadrants"
OUT_PATH = PROJECT_ROOT / "output" / "analysis" / "top25_quadrants_momentum_bias.csv"


# Només considerarem earnings fins a final de 2017
CUTOFF_DATE = date(2017, 12, 31)

# Mínim nombre d'earnings "considered" (no zeros) perquè un ticker entri al rànquing
MIN_CONSIDERED = 40


def main():
    if not QDIR.exists():
        print(f"❌ ERROR: Quadrants directory not found: {QDIR}")
        return

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    results = []

    # Ara treballarem amb *_quadrants_detailed.csv en lloc de *_quadrants_summary.csv
    for path in sorted(QDIR.glob("*_quadrants_detailed.csv")):
        ticker = path.stem.split("_")[0].upper()

        # Comptadors
        total_earnings = 0          # tots els earnings fins al 2020 (encara que tinguin 0)
        considered = 0              # earnings amb c2o != 0 i o2c != 0

        pos_then_up = 0
        pos_then_down = 0
        neg_then_up = 0
        neg_then_down = 0

        try:
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        d = datetime.strptime(row["date"].strip(), "%Y-%m-%d").date()
                        if d > CUTOFF_DATE:
                            # Ignorem earnings posteriors a 31/12/2020
                            continue

                        c2o = float(row["close_to_open_pct"])
                        o2c = float(row["open_to_close_pct"])
                    except Exception:
                        # Si hi ha cap error de format, saltem aquesta fila
                        continue

                    total_earnings += 1

                    # "Considered" = earnings on ambdues variacions no són 0
                    if c2o == 0 or o2c == 0:
                        continue

                    considered += 1

                    # Classificació per quadrants (momentum)
                    if c2o > 0 and o2c > 0:
                        pos_then_up += 1
                    elif c2o > 0 and o2c <= 0:
                        pos_then_down += 1
                    elif c2o <= 0 and o2c > 0:
                        neg_then_up += 1
                    else:  # c2o <= 0 and o2c <= 0
                        neg_then_down += 1

        except Exception as e:
            print(f"⚠️ Error reading {path.name}: {e}")
            continue

        # Si no hi ha earnings abans de 2021, o no arriba al mínim, saltem
        if considered < MIN_CONSIDERED:
            # print(f"Skipping {ticker}: only {considered} considered earnings before 2021")
            continue

        # Calculem percentatges (en %)
        pos_up_pct = 100.0 * pos_then_up / considered
        pos_down_pct = 100.0 * pos_then_down / considered
        neg_up_pct = 100.0 * neg_then_up / considered
        neg_down_pct = 100.0 * neg_then_down / considered

        continuation = pos_up_pct + neg_down_pct
        reversal = pos_down_pct + neg_up_pct
        momentum_bias = continuation - reversal

        results.append(
            {
                "ticker": ticker,
                "considered": considered,
                "total_earnings": total_earnings,
                "pos_then_up": pos_up_pct,
                "pos_then_down": pos_down_pct,
                "neg_then_up": neg_up_pct,
                "neg_then_down": neg_down_pct,
                "continuation": continuation,
                "reversal": reversal,
                "momentum_bias": momentum_bias,
            }
        )

    if not results:
        print("❌ No valid quadrant detailed files found (or none with ≥ "
              f"{MIN_CONSIDERED} earnings before {CUTOFF_DATE}).")
        return

    # Ordenem per momentum_bias i agafem TOP 25
    results.sort(key=lambda r: r["momentum_bias"], reverse=True)
    top25 = results[:25]

    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "rank",
                "ticker",
                "considered",
                "total_earnings",
                "pos_then_up",
                "pos_then_down",
                "neg_then_up",
                "neg_then_down",
                "continuation",
                "reversal",
                "momentum_bias",
            ]
        )
        for i, r in enumerate(top25, start=1):
            w.writerow(
                [
                    i,
                    r["ticker"],
                    r["considered"],
                    r["total_earnings"],
                    r["pos_then_up"],
                    r["pos_then_down"],
                    r["neg_then_up"],
                    r["neg_then_down"],
                    r["continuation"],
                    r["reversal"],
                    r["momentum_bias"],
                ]
            )

    print(f"✅ Wrote TOP 25 momentum-bias stocks (≥{MIN_CONSIDERED} earnings, "
          f"data ≤ {CUTOFF_DATE}) to:\n   {OUT_PATH}\n")
    print("Top 5 preview:")
    for r in top25[:5]:
        print(
            f"  {r['ticker']}: momentum_bias={r['momentum_bias']:.4f} "
            f"(continuation={r['continuation']:.2f}%, "
            f"reversal={r['reversal']:.2f}%, "
            f"considered={r['considered']}, "
            f"total_earnings={r['total_earnings']})"
        )


if __name__ == "__main__":
    main()
