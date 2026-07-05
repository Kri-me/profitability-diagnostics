# Next Steps

## 1. Run SQL

```powershell
# Navigate to the project root directory
cd profitability-diagnostics
.\scripts\run_sql.ps1
```

Enter the PostgreSQL password when prompted.

## 2. Confirm Load Counts

Expected counts: customers 4000, products 120, orders 18186, order_items 30271, fulfillment 18186, marketing_spend 72.

## 3. Capture Key SQL Findings

Save the outputs from: monthly trend, discount cannibalization, logistics subsidization, return-rate trap, channel LTV/CAC, and prioritization helper.

## 4. Install Analysis Dependencies

```powershell
pip install pandas numpy sqlalchemy psycopg
```

## 5. Run Python Analysis Starter

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/profitability_diagnostics"
python src\analyze_sql_outputs.py
```

## 6. Next Build Tasks

- Create charts for monthly margin trend, discount band margin, shipping deficit by region, return rate by subcategory, and LTV/CAC by channel.
- Add a simulation script for discount caps and marketing spend reallocation.
- Build the Streamlit dashboard with Finance, Marketing, and Operations sections.
- Draft the executive summary once SQL findings are captured.
