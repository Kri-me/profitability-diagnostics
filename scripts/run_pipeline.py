import logging
# Suppress Streamlit's internal cache warnings
logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.ERROR)
import json
import os
import time
import psycopg
from pathlib import Path

# #region agent log
_DEBUG_LOG = Path.cwd() / "debug-4e1194.log"


def _debug_log(location, message, data, hypothesis_id):
    payload = {
        "sessionId": "4e1194",
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": message,
        "data": data,
        "hypothesisId": hypothesis_id,
    }
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except OSError:
        pass


# #endregion

DB_CONFIG = {
    "dbname": "profitability_diagnostics",
    "user": "postgres",
    "password": os.getenv("PG_PASSWORD"),
    "host": "localhost",
    "port": 5432,
}

SQL_STEPS = [
    "sql/01_schema.sql",
    "sql/03_kpi_views.sql",
    "sql/04_diagnostic_queries.sql",
]

CSV_LOADS = [
    ("customers", "data/customers.csv"),
    ("products", "data/products.csv"),
    ("orders", "data/orders.csv"),
    ("order_items", "data/order_items.csv"),
    ("fulfillment", "data/fulfillment.csv"),
    ("marketing_spend", "data/marketing_spend.csv"),
]

EXPORT_VIEW_NAMES = [
    "monthly_trend_view",
    "discount_cannibalization_view",
    "logistics_subsidization_view",
    "return_rate_trap_view",
    "channel_ltv_cac_view",
    "prioritization_helper_view",
]

OUTPUTS = {
    "monthly_trend": """
        SELECT * FROM monthly_trend_view ORDER BY order_month
    """,
    "discount_cannibalization": """
        SELECT * FROM discount_cannibalization_view ORDER BY net_margin_pct
    """,
    "logistics_subsidization": """
        SELECT * FROM logistics_subsidization_view ORDER BY shipping_profit
    """,
    "return_rate_trap": """
        SELECT * FROM return_rate_trap_view
        ORDER BY unit_return_rate_pct DESC, allocated_net_operating_profit
    """,
    "channel_ltv_cac": """
        SELECT * FROM channel_ltv_cac_view ORDER BY avg_ltv_after_customer_cac
    """,
    "prioritization_helper": """
        SELECT * FROM prioritization_helper_view
    """,
}

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


# -----------------------------
# SQL EXECUTION
# -----------------------------
def run_sql_file(conn, file_path):
    print(f"Running {file_path}...")

    sql = Path(file_path).read_text(encoding="utf-8")

    # split into individual SQL statements
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    # #region agent log
    _debug_log(
        "run_pipeline.py:run_sql_file",
        "sql file split into statements",
        {"file": file_path, "statement_count": len(statements)},
        "H3",
    )
    # #endregion

    try:
        with conn.cursor() as cur:
            for i, stmt in enumerate(statements):
                # #region agent log
                _debug_log(
                    "run_pipeline.py:run_sql_file",
                    "executing statement",
                    {
                        "file": file_path,
                        "index": i,
                        "preview": stmt[:120].replace("\n", " "),
                    },
                    "H3",
                )
                # #endregion
                cur.execute(stmt)

        conn.commit()

    except Exception as e:
        print("\n❌ REAL SQL ERROR DETECTED")
        print(f"File: {file_path}")
        print(e)

        conn.rollback()
        raise


# -----------------------------
# CSV LOADING
# -----------------------------
def load_csv(conn, table, file_path):
    print(f"Loading {file_path} → {table}...")

    try:
        with conn.cursor() as cur:
            with open(file_path, "r", encoding="utf-8") as f:
                with cur.copy(f"COPY {table} FROM STDIN WITH CSV HEADER") as copy:
                    copy.write(f.read())

        conn.commit()

    except Exception as e:
        print("\n❌ CSV LOAD ERROR")
        print(f"Table: {table}, File: {file_path}")
        print(e)

        conn.rollback()
        raise


# -----------------------------
# EXPORT RESULTS
# -----------------------------
def export_query(conn, name, query):
    print(f"Exporting {name}...")

    output_file = OUTPUT_DIR / f"{name}.csv"

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(",".join(colnames) + "\n")

        for row in rows:
            f.write(",".join(map(str, row)) + "\n")


# -----------------------------
# MAIN PIPELINE
# -----------------------------
def main():
    # #region agent log
    _debug_log(
        "run_pipeline.py:main",
        "pipeline started",
        {"cwd": str(Path.cwd()), "log_path": str(_DEBUG_LOG), "runId": "post-fix"},
        "H1",
    )
    # #endregion

    if not DB_CONFIG["password"]:
        raise ValueError("PG_PASSWORD is not set")

    with psycopg.connect(**DB_CONFIG) as conn:

        # 1. schema (fixed execution)
        run_sql_file(conn, "sql/01_schema.sql")

        # 2. load data
        for table, path in CSV_LOADS:
            load_csv(conn, table, path)

        # 3. views
        run_sql_file(conn, "sql/03_kpi_views.sql")

        # #region agent log
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )
            existing_views = [row[0] for row in cur.fetchall()]
        missing_export_views = [
            v for v in EXPORT_VIEW_NAMES if v not in existing_views
        ]
        _debug_log(
            "run_pipeline.py:main",
            "views after 03_kpi_views.sql",
            {
                "existing_views": existing_views,
                "expected_export_views": EXPORT_VIEW_NAMES,
                "missing_export_views": missing_export_views,
                "runId": "post-fix",
            },
            "H1",
        )
        # #endregion
        if missing_export_views:
            raise RuntimeError(
                "Missing export views after 03_kpi_views.sql: "
                f"{missing_export_views}. "
                "Ensure sql/03_kpi_views.sql includes the export view definitions."
            )

        # 4. diagnostics
        run_sql_file(conn, "sql/04_diagnostic_queries.sql")

        # 5. exports
        for name, query in OUTPUTS.items():
            # #region agent log
            _debug_log(
                "run_pipeline.py:export_query",
                "attempting export",
                {"export_name": name, "runId": "post-fix"},
                "H5",
            )
            # #endregion
            export_query(conn, name, query)
            # #region agent log
            _debug_log(
                "run_pipeline.py:export_query",
                "export succeeded",
                {
                    "export_name": name,
                    "output_file": str(OUTPUT_DIR / f"{name}.csv"),
                    "runId": "post-fix",
                },
                "H5",
            )
            # #endregion

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
