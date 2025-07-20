from flask import g
import sqlite3

def init_db():
    from pathlib import Path

    db_path = Path(__file__).parent / 'users.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables if they do not exist
    print("1 Creating Users table if it does not exist")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            email_verified BOOLEAN DEFAULT FALSE,
            verification_token TEXT,
            verification_expires TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );''')

    print("2 Creating RefreshTokens table if it does not exist")
    cursor.execute('''CREATE TABLE IF NOT EXISTS RefreshTokens (
        id TEXT PRIMARY KEY,
        user_email TEXT NOT NULL,
        token_hash TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_email) REFERENCES Users (email)
    );
    ''')
    print("3 Creating BlacklistedTokens table if it does not exist")
    cursor.execute('''CREATE TABLE IF NOT EXISTS BlacklistedTokens (
        id TEXT PRIMARY KEY,
        token TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
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

def close_db(error=None):
    """Close the database connection at the end of request"""
    db = g.pop('db', None)
        
    if db is not None:
        db.close()