# SQL Layer

This folder contains the raw SQL scripts that define the database schema, load the synthetic CSVs, and create the KPI/diagnostic views.  

**The recommended way to apply these scripts is via the single entry‑point `scripts/run_pipeline.py`, which runs them in the correct order automatically.**  

You can still execute any of the `.sql` files manually (e.g., with `psql`) for debugging or learning purposes, but it isn’t required for the normal workflow.

Run these files in order after generating the CSVs with:

```powershell
python src\generate_data.py
