from flask import g
def init_db():
    import sqlite3
    from pathlib import Path

    db_path = Path(__file__).parent / 'users.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables if they do not exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    import sqlite3
    from pathlib import Path

    db_path = Path(__file__).parent / 'users.db'
    if not hasattr(g, 'db'):
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row  # to return rows as dictionaries
    return g.db

def close_db():
    """Close the database connection at the end of request"""
    db = g.pop('db', None)
        
    if db is not None:
        db.close()