# Manufacturing Analytics Portfolio

Portfolio project applying data analytics skills to manufacturing operations data, built alongside the IBM Data Analytics Professional Certificate. Goal: transition from plant operations (dryer tech, OSB manufacturing) into a Manufacturing Data Analyst role.

**Note:** All data in this repo is synthetic/generated for practice purposes — not real production data from any employer.

## Module 1: Data Foundations
- Loaded daily production data (date, line, shift, units produced, downtime) using pandas
- Validated data types and converted dates to proper datetime format
- Checked categorical fields (Line, Shift) for inconsistencies
- Aggregated total units produced by line, and by line + shift

**Finding:** Night shift production is consistently lower than Day shift across all three lines (7–10% gap), with Line_3 showing the largest drop (~10%). This kind of gap is worth investigating further — staffing, fatigue, or equipment warm-up could be contributing factors.

## Tech Stack
- Python, pandas, Jupyter Notebook

## Roadmap
- Module 2: OEE (Overall Equipment Effectiveness) tracking
- Module 3: Downtime root cause analysis
- Module 4: Quality/defect analytics
- Module 5: Downtime cost & ROI modeling
- Module 6: Integrated weekly plant performance report
