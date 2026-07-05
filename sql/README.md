# SQL Layer

Run these files in order after generating the CSVs with:

```powershell
python src\generate_data.py
```

## Files

1. `01_schema.sql` creates the PostgreSQL tables, keys, constraints, and indexes.
2. `02_load_csv.sql` loads the generated CSVs from `data/`.
3. `03_kpi_views.sql` creates reusable KPI views for revenue, margin, LTV, and CAC analysis.
4. `04_diagnostic_queries.sql` contains the business investigation queries for the four profit leak hypotheses.

## Suggested psql Flow

```powershell
createdb profitability_diagnostics
psql -d profitability_diagnostics -f sql\01_schema.sql
psql -d profitability_diagnostics -f sql\02_load_csv.sql
psql -d profitability_diagnostics -f sql\03_kpi_views.sql
psql -d profitability_diagnostics -f sql\04_diagnostic_queries.sql
```

If `psql` is not available by name, use the full PostgreSQL 18 path:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -d profitability_diagnostics -f sql\01_schema.sql
```

The diagnostic query outputs are meant to become the backbone of the technical report and dashboard.
