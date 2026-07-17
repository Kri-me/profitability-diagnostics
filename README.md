# Profitability Diagnostics — Apex Global

An end-to-end profitability investigation for a fictional e-commerce retailer. The central business question:

> Revenue has grown for 18 months. Margins are shrinking. Where is the business leaking value and what should be done about it?

The project generates synthetic data with intentionally embedded profit leaks, loads it into PostgreSQL, runs structured SQL diagnostics, validates findings with machine learning, simulates policy interventions, and presents the full investigation through a Streamlit dashboard.

---

## The Answer (Short Version)

Over 18 months, net revenue grew from ~$375K/month to ~$811K/month (+99%). Net margin fell from 27.1% to 22.6% — a 4.5-point structural decline. Three mechanisms drive this:

1. **Discount cannibalization** — high-discount orders (22–40% off) contribute just 1.93% net margin. $892K in discount giveaways produced $38K in profit.
2. **Marketing misallocation** — Paid Social, the largest acquisition channel (34% of customers), returns an LTV:CAC of 1.98×. Organic returns 100.68×.
3. **Structural cost leakage** — $302K in shipping subsidies absorbed below gross margin, plus 33%+ return rates in apparel categories.

Simulation shows that a discount cap + Paid Social reallocation recovers **$499K–$884K** in operating profit with no revenue increase required.

---

## Project Structure

```
profitability diagnostics/
│
├── src/
│   ├── generate_data.py          # Synthetic data generator (seeded, reproducible)
│   ├── db.py                     # SQLAlchemy engine via DATABASE_URL
│   ├── data_loaders.py           # View → DataFrame bridge (cached + CSV fallback)
│   │
│   ├── simulations/
│   │   ├── simulate.py           # Scenario engine: discount cap, marketing shift
│   │   └── compare.py            # Loads, normalises, ranks saved scenario JSONs
│   │
│   └── dashboard_app/
│       └── app.py                # Streamlit investigation dashboard (3 tabs)
│
├── sql/
│   ├── 01_schema.sql             # PostgreSQL DDL
│   ├── 02_load_csv.sql           # COPY commands (alternative to pipeline runner)
│   ├── 03_kpi_views.sql          # 11 reusable views — consistent profit formula
│   ├── 04_diagnostic_queries.sql # Ad-hoc investigative queries per hypothesis
│   └── 05_extra_diagnostic_views.sql
│
├── notebooks/
│   ├── 01_profit_drivers_eda.ipynb       # EDA + Linear Regression + Random Forest
│   └── 02_hypothesis_validation.ipynb   # Ridge + RF pipeline, driver importance export
│
├── scripts/
│   ├── run_pipeline.py           # Full pipeline: schema → load → views → export
│   └── run_sql.ps1               # PowerShell wrapper for psql
│
├── data/
│   ├── raw/                      # Generated CSVs (6 tables)
│   ├── exports/                  # Dashboard CSV fallback data
│   └── simulation_results/       # Saved scenario JSONs
│
└── docs/
    └── 03_executive_summary.md      # Full findings and recommendations
```

---

## Quickstart

### Prerequisites

- Python 3.10+
- PostgreSQL 14+

### Install dependencies

```powershell
pip install pandas numpy sqlalchemy psycopg streamlit plotly python-dotenv scikit-learn matplotlib seaborn
```

### Set database connection

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/profitability_diagnostics
```

Or set it for a PowerShell session:

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres@localhost:5432/profitability_diagnostics"
```

### Run the full pipeline

```powershell
# 1. Generate synthetic data
python src/generate_data.py

# 2. Load into PostgreSQL (schema + CSV + views)
python scripts/run_pipeline.py

# 3. Launch the dashboard
streamlit run src/dashboard_app/app.py
```

The dashboard runs on hardcoded findings from confirmed SQL outputs if no database connection is available — useful for offline demos.

---

## Analytical Approach

The investigation follows a four-layer methodology designed to move from description to causation to intervention:

### Layer 1 — SQL Diagnostics
Grouped aggregations across discount band, acquisition channel, region, and customer segment. Establishes where margin is leaking and quantifies each leak. All layers share a single consistent profit formula defined in `03_kpi_views.sql`.

### Layer 2 — Exploratory Analysis (`01_profit_drivers_eda.ipynb`)
Order-level EDA on 18,186 orders across 18 months. Computes derived features (`shipping_profit`, `gross_margin_pct`), profiles the distribution of `net_operating_profit` (mean $141, range −$628 to +$1,979), and fits a Linear Regression + Random Forest to identify the primary drivers of profit variance.

**Top drivers by combined importance (regression coefficient × RF importance):**

| Feature | Direction | RF Importance |
|---|---|---|
| `shipping_profit` | Negative | 0.274 |
| `discount_pct` | Negative | 0.257 |
| `gross_margin_pct` | Positive | 0.187 |
| `marketing_cost_per_order` | Negative | 0.098 |
| `unit_return_rate` | Negative | 0.057 |
| `state_region_Remote` | Negative | 0.021 |

### Layer 3 — Hypothesis Validation (`02_hypothesis_validation.ipynb`)
Formal Ridge Regression + Random Forest pipeline with train/test split, OneHotEncoding for categorical features, and a combined driver importance score (|ridge coefficient| + RF importance). Exports `driver_importance.csv` used by the dashboard's driver analysis chart.

### Layer 4 — Scenario Simulation
`simulate.py` applies levers to the full order dataset and recomputes `net_operating_profit` per order. Three scenarios tested:

| Scenario | Discount Cap | Paid Social Shift | Profit Recovery |
|---|---|---|---|
| Conservative | 15% | 50% | +$499K |
| Balanced | 9% | 35% | +$817K |
| Aggressive | 8% | 50% | +$884K |

Simulations reprice historical orders — they are not demand forecasts.

---

## Dashboard

Three tabs structured as an investigation narrative:

**① Business Problem** — establishes the revenue vs margin contradiction with headline KPIs and a dual-axis trend chart before showing any diagnostic evidence.

**② Investigation** — organised by stakeholder perspective within a single tab:
- 🔵 Finance: discount band breakdown
- 🟣 Marketing: LTV:CAC by channel
- 🟢 Operations: shipping deficit by region, return rates by subcategory
- Cross-functional: 14 loss-making segment combinations (all share Paid Social + High Discount)
- 🟡 Analytics: ML feature importance as statistical confirmation

**③ Decision Lab** — interactive scenario configurator (runs against live data), preset scenario comparison, and executive recommendations with evidence trails and an analysis confidence table.

---

## Data

Synthetic dataset, seeded with RNG(42) — fully reproducible.

| Table | Records | Key embedded pattern |
|---|---|---|
| `customers` | 4,000 | Paid Social customers get 4× higher rate of High discounts |
| `products` | 120 | Apparel subcategories carry elevated return risk |
| `orders` | 18,186 | High-discount share grows from ~10% → ~28% over 18 months |
| `order_items` | 30,271 | |
| `fulfillment` | 18,186 | Remote shipping cost ~$43, fee charged ~$6.40 |
| `marketing_spend` | 72 | 18 months × 4 channels |

---

## Key Design Decisions

**Why synthetic data?** Allows the full SQL → ML → simulation pipeline to be demonstrated without data access constraints or confidentiality limits. The business story is deliberate — two competing primary leaks (discounting and Paid Social efficiency) that the analysis has to separate rather than confirm a single obvious answer.

**Why is ML a validation layer, not the headline?** The causal structure is identifiable through SQL diagnostics. The notebooks confirm that the same variables hold as drivers after controlling for interactions — that confirmation is meaningful, but positioning ML as discovery would overstate what it adds here.

**Why hardcoded fallback data in the dashboard?** Portfolio demonstrations require reliable rendering regardless of whether a local PostgreSQL instance is running. All hardcoded values are sourced directly from confirmed SQL outputs.

---

## Notebooks — Running Notes

`02_hypothesis_validation.ipynb` requires the project root on `sys.path` to import `src.data_loaders`. Add this to the first cell if running outside the project directory:

```python
import sys
sys.path.append(r"C:\Users\kerry\OneDrive\Documents\profitability diagnostics")
```

Both notebooks use `.venv` as the kernel — activate it before launching Jupyter.

