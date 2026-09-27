"""
Generate a synthetic OSB strand-dryer production dataset for OEE analysis.

All parameters are derived from published, publicly available industry figures.
No proprietary or employer-internal information is used. See DATA_DICTIONARY.md
for the full derivation and source list.

Outputs
-------
osb_dryer_shifts.csv    one row per date / shift / dryer (PLC-derived)
osb_downtime_events.csv one row per logged downtime event (operator-entered)

The two files are deliberately NOT perfectly reconcilable. See the note at the
bottom of this file.
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260101)

# ----------------------------------------------------------------------------
# Equipment parameters
# ----------------------------------------------------------------------------
# Nameplate rate derived from a 600 MMSF/yr mill (published mill capacities run
# 400-860 MMSF/yr on a 3/8-in basis). See DATA_DICTIONARY.md for the arithmetic.
DRYERS = {
    "DRYER_1": {"ideal_rate": 26.0, "reliability": 0.90, "age_penalty": True},
    "DRYER_2": {"ideal_rate": 29.0, "reliability": 1.00, "age_penalty": False},
}

SHIFTS = ["Day", "Night"]
SHIFT_MINUTES = 720  # 12-hour shifts

START = pd.Timestamp("2026-01-01")
END = pd.Timestamp("2026-06-30")

# ----------------------------------------------------------------------------
# Downtime reason codes
# ----------------------------------------------------------------------------
# (reason, category, mean_minutes, relative_frequency)
MAJOR = [
    ("Spark detection trip", "Fire/Safety", 95, 0.9),
    ("Burner flame-out", "Process", 70, 1.0),
    ("Drag chain failure", "Mechanical", 150, 0.5),
    ("Discharge conveyor bearing", "Mechanical", 130, 0.4),
    ("Cyclone plug", "Process", 80, 0.8),
    ("Drive motor fault", "Electrical", 110, 0.5),
    ("Screen change", "Changeover", 60, 1.1),
]
MEDIUM = [
    ("Wet bin plug", "Process", 25, 2.0),
    ("Moisture control out of spec", "Process", 22, 2.4),
    ("Dryer plug / material buildup", "Process", 28, 1.8),
    ("Belt tracking", "Mechanical", 18, 1.6),
    ("ID fan damper fault", "Mechanical", 20, 1.0),
    ("Temperature control loop fault", "Electrical", 24, 1.0),
]
SHORT = [
    ("Minor jam clearing", "Mechanical", 4, 5.0),
    ("Sensor fault reset", "Electrical", 3, 4.0),
    ("Operator adjustment", "Process", 5, 4.5),
]

BLOCKED_REASONS = [
    ("Green end down - flaker", "Starved"),
    ("Wet bin empty", "Starved"),
    ("Press down", "Blocked"),
    ("Dry bin full", "Blocked"),
]


def draw_events(rng, pool, n):
    """Draw n downtime events from a reason pool, returning (reason, cat, min)."""
    if n <= 0:
        return []
    weights = np.array([p[3] for p in pool], dtype=float)
    weights /= weights.sum()
    idx = rng.choice(len(pool), size=n, p=weights)
    out = []
    for i in idx:
        reason, cat, mean, _ = pool[i]
        # lognormal spread around the mean duration, floored at 1 minute
        minutes = float(rng.lognormal(mean=np.log(mean), sigma=0.45))
        out.append((reason, cat, max(1.0, round(minutes))))
    return out


def planned_minutes(rng, date, shift):
    """Planned production time. Maintenance and market curtailment come out here."""
    # Planned maintenance: 2nd and 4th Sunday of each month, day shift
    if date.dayofweek == 6 and shift == "Day":
        week_of_month = (date.day - 1) // 7 + 1
        if week_of_month in (2, 4):
            return 240
    # Market-driven curtailment: two weeks in May, reduced schedule
    if pd.Timestamp("2026-05-11") <= date <= pd.Timestamp("2026-05-22"):
        return 480
    return SHIFT_MINUTES


def seasonal_performance(date):
    """
    Winter furnish carries higher green moisture content, so the dryer has to
    slow down to hit target MC. Improves through spring.
    """
    day_of_year = date.dayofyear
    return 0.865 + 0.055 * min(1.0, day_of_year / 150.0)


def main():
    dates = pd.date_range(START, END, freq="D")
    shift_rows = []
    event_rows = []
    event_id = 1

    for date in dates:
        for shift in SHIFTS:
            for dryer, cfg in DRYERS.items():
                planned = planned_minutes(RNG, date, shift)
                rate = cfg["ideal_rate"]
                scale = planned / SHIFT_MINUTES

                # --- unplanned downtime -------------------------------------
                rel = cfg["reliability"]
                n_major = RNG.poisson(0.16 * scale / rel)
                n_medium = RNG.poisson(1.05 * scale / rel)
                n_short = RNG.poisson(4.20 * scale / rel)

                events = (
                    draw_events(RNG, MAJOR, n_major)
                    + draw_events(RNG, MEDIUM, n_medium)
                    + draw_events(RNG, SHORT, n_short)
                )
                downtime = sum(e[2] for e in events)
                downtime = min(downtime, planned * 0.75)  # cap pathological shifts

                # --- blocked / starved --------------------------------------
                blocked = 0.0
                blocked_events = []
                if RNG.random() < 0.42:
                    n_blk = 1 + RNG.poisson(0.5)
                    for _ in range(n_blk):
                        reason, kind = BLOCKED_REASONS[RNG.integers(len(BLOCKED_REASONS))]
                        mins = max(5.0, round(RNG.lognormal(np.log(38), 0.6)))
                        blocked_events.append((reason, kind, mins))
                    blocked = sum(e[2] for e in blocked_events)
                blocked = min(blocked, max(0.0, planned - downtime - 30))

                run_time = max(0.0, planned - downtime - blocked)

                # --- performance while running -------------------------------
                perf = seasonal_performance(date)
                if cfg["age_penalty"] and shift == "Night":
                    # DRYER_1 night shift drifts down over the period
                    elapsed = (date - START).days / (END - START).days
                    perf -= 0.075 * elapsed
                perf += RNG.normal(0, 0.022)
                perf = float(np.clip(perf, 0.60, 0.99))

                output = rate / 60.0 * run_time * perf

                # --- quality --------------------------------------------------
                # Off-spec MC concentrated around restarts; more stops, more rework
                restart_pressure = min(1.0, len(events) / 8.0)
                rework_pct = np.clip(RNG.normal(0.016 + 0.020 * restart_pressure, 0.006), 0.002, 0.09)
                # Over-drying produces fines; worse when pushing rate hard
                fines_pct = np.clip(RNG.normal(0.011 + 0.020 * max(0, perf - 0.90), 0.004), 0.001, 0.05)

                rework = output * rework_pct
                fines = output * fines_pct

                shift_rows.append(
                    {
                        "Date": date.date().isoformat(),
                        "Shift": shift,
                        "Dryer_ID": dryer,
                        "Planned_Time_Min": int(planned),
                        "Downtime_Min": int(round(downtime)),
                        "Blocked_Starved_Min": int(round(blocked)),
                        "Ideal_Rate_BDT_Hr": rate,
                        "Output_BDT": round(output, 2),
                        "Rework_BDT": round(rework, 2),
                        "Fines_BDT": round(fines, 2),
                    }
                )

                # --- operator downtime log ------------------------------------
                # Operators reliably log long stops, sometimes log medium ones,
                # and essentially never log micro-stops. This is what creates
                # the unaccounted-time gap against Downtime_Min.
                for reason, cat, mins in events:
                    if mins >= 15:
                        logged = True
                    elif mins >= 8:
                        logged = RNG.random() < 0.60
                    else:
                        logged = RNG.random() < 0.10
                    if not logged:
                        continue
                    # Operators round to the nearest 5 minutes
                    reported = max(5, int(round(mins / 5.0) * 5))
                    event_rows.append(
                        {
                            "Event_ID": event_id,
                            "Date": date.date().isoformat(),
                            "Shift": shift,
                            "Dryer_ID": dryer,
                            "Reason": reason,
                            "Category": cat,
                            "Duration_Min": reported,
                        }
                    )
                    event_id += 1

                for reason, kind, mins in blocked_events:
                    event_rows.append(
                        {
                            "Event_ID": event_id,
                            "Date": date.date().isoformat(),
                            "Shift": shift,
                            "Dryer_ID": dryer,
                            "Reason": reason,
                            "Category": kind,
                            "Duration_Min": int(mins),
                        }
                    )
                    event_id += 1

    shifts = pd.DataFrame(shift_rows)
    events = pd.DataFrame(event_rows)

    shifts.to_csv("osb_dryer_shifts.csv", index=False)
    events.to_csv("osb_downtime_events.csv", index=False)

    return shifts, events


if __name__ == "__main__":
    shifts, events = main()
    print(f"shift rows:  {len(shifts)}")
    print(f"event rows:  {len(events)}")