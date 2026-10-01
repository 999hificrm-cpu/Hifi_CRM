from app.core.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
print("TABLES:", inspector.get_table_names())
