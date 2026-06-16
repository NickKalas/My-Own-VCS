import sqlite3

DB_FILE = 'database.db'
def init_the_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE blobs (
        hash TEXT PRIMARY KEY,
        compressed_data BLOB)
    """)

    cursor.execute("""
    CREATE TABLE tree_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tree_hash TEXT,               -- Grouping identifier for a specific snapshot
        file_path TEXT,               -- e.g., "src/main.py"
        blob_hash TEXT,               -- Points to the file's content in the blobs table
        FOREIGN KEY(blob_hash) REFERENCES blobs(hash)
    );
    """)

    cursor.execute("""
    CREATE TABLE commits (
        hash TEXT PRIMARY KEY,        -- Unique hash of the commit metadata
        parent_hash TEXT,             -- Points to the previous commit (allows branching history)
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
    INSERT OR IGNORE INTO blobs (hash,compressed_data)
    VALUES (?,?)
    """, (SHA1_HASH, BLOB))

    conn.commit()
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

def update_3rd_table(hash, parent_path, tree_hash, message):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO commits (hash, parent_hash, tree_hash, message)
    VALUES (?,?,?,?)
    """, (hash, parent_path, tree_hash, message))

    conn.commit()
    conn.close()