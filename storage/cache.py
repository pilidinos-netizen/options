import sqlite3

def init_db():
    conn = sqlite3.connect("quant.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        ticker TEXT,
        intent TEXT,
        confidence REAL
    )
    """)
    conn.commit()
    return conn