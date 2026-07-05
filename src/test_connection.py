from sqlalchemy import create_engine, text
import os

engine = create_engine(
    f"postgresql+psycopg://postgres:{os.getenv('PG_PASSWORD')}@localhost:5432/profitability_diagnostics"
)

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())