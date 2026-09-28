# OSB-Style Plant Performance Analysis

Portfolio analysis of **synthetic** manufacturing operations data.
No employer or production data is in this repository.

**Target role:** Manufacturing / Continuous Improvement Data Analyst  
**Credential in progress:** IBM Data Analyst Professional Certificate (Coursera)

## Question
Is night-shift output lower than day-shift after we account for scheduled time and downtime — and which line drives the gap?

## Data
- Source: generated dataset (see `data/` and `src/generate_*.py`)
- Grain: one row per line × shift × date
- Window: [N] days, [3] lines, Day / Night
- Fields: date, line, shift, units_produced, downtime_minutes, [scheduled_minutes if you have it]

This dataset is synthetic. Findings demonstrate method. They are not mill results.

## Method
- pandas load + dtype / datetime checks
- categorical cleanup on Line and Shift
- production aggregated by line and by line × shift
- [optional] units per scheduled hour so a shorter night crew is not called “worse”

## Finding (Module 1)
Night shift produced **[X]% to [Y]% fewer units** than Day across all three lines.
Line_3 had the largest gap (**~[Z]%**).

Caveats:
- [Sample size: N shift-days]
- Downtime is / is not netted out of units
- If the generator includes a night factor, this finding confirms the pipeline, not a root cause

Next measurement: downtime minutes and stop codes by shift (Module 3), then OEE.

## Stack
Python, pandas, Jupyter

## How to run
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook notebooks/01_foundations.ipynb
