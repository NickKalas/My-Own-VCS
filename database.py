import sqlite3

DB_FILE = 'database.db'

def init_the_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Enforce database relational integrity
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blobs (
        hash TEXT PRIMARY KEY,
        compressed_data BLOB)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tree_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tree_hash TEXT,               -- Grouping identifier for a specific snapshot
        file_path TEXT,               -- e.g., "src/main.py"
        blob_hash TEXT,               -- Points to the file's content in the blobs table
        FOREIGN KEY(blob_hash) REFERENCES blobs(hash),
        UNIQUE(tree_hash, file_path)  -- Prevents duplicate records for unchanged files
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS commits (
        hash TEXT PRIMARY KEY,        -- Unique hash of the commit metadata
        parent_hash TEXT,             -- Points to the previous commit
        tree_hash TEXT,               -- Points to the snapshot layout in tree_entries
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(parent_hash) REFERENCES commits(hash)
    );
    """)
    conn.commit()
    conn.close()

init_the_db()

def update_1st_table(SHA1_HASH, BLOB):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO blobs (hash, compressed_data)
    VALUES (?,?)
    """, (SHA1_HASH, BLOB))

    conn.commit()
    if cursor.rowcount == 0:
        print(f"Deduplicated: {SHA1_HASH[:8]}... already exists. No space wasted!")
    else:
        print(f"New Blob Stored: {SHA1_HASH[:8]}...")
    conn.close()

def update_2nd_table(tree_hash, file_path, blob_hash):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO tree_entries (tree_hash, file_path, blob_hash)
    VALUES (?,?,?)
    """, (tree_hash, file_path, blob_hash))

    conn.commit()
    conn.close()