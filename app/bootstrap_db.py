from pathlib import Path
from sqlalchemy import text
from .db import engine

def run_sql_file(path: str):
    sql = Path(path).read_text(encoding="utf-8")
    with engine.begin() as conn:
        for stmt in filter(None, [s.strip() for s in sql.split(";")]):
            conn.execute(text(stmt))

if __name__ == "__main__":
    run_sql_file("schema.sql")
    if Path("seed.sql").exists():
        run_sql_file("seed.sql")
    print("DB bootstrap done.")
