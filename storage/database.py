import sqlite3

def init_db():
    conn = sqlite3.connect("signals.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            ticker TEXT,
            intent TEXT,
            confidence REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn