from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS payment_transactions CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS billing_events CASCADE"))
    conn.commit()
print("Dropped.")
