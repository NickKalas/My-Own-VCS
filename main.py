import hashlib
import zlib
import os
import sqlite3
import datetime
from pathlib import Path
from database import update_1st_table, update_2nd_table
def load_the_ignore_files() -> list:
    ignore = []
    with open(".ignore", "r") as ign:
        for line in ign:
            cleaned_line = line.strip()
            if cleaned_line:
                ignore.append(cleaned_line)
    return ignore  
ignore = load_the_ignore_files()

def stage_file(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        hash_object = hashlib.sha1(content)
        hex_digest = hash_object.hexdigest()

        compressed_data = zlib.compress(content)

        update_1st_table(hex_digest, compressed_data)
        return hex_digest

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' could not be found.")
    except Exception as e:
        print(f"An unexpected error occurred while staging {file_path}: {e}")

def scan_directory(dir_path: str, root_tree_hash: str = None) -> str:
    project_root = os.path.abspath(".")
    try:
        entries = []
        for item in os.scandir(dir_path):
            abs_path = os.path.abspath(Path(item))
            relative_path = os.path.relpath(abs_path, project_root)
            item_name = os.path.basename(relative_path)

            if item_name.startswith('.') or item_name in ignore:
                continue
            
            elif item.is_file():
                file_hash = stage_file(relative_path)
                entries.append(("file", relative_path, file_hash))
            
            elif item.is_dir():
                sub_tree_hash = scan_directory(relative_path, root_tree_hash)
                entries.append(("tree", relative_path, sub_tree_hash))
        
        entries.sort()
        
        manifesto_lines = [f"{t} {p} {h}" for t, p, h in entries]
        manifesto_text = "\n".join(manifesto_lines)
        
        current_folder_hash = hashlib.sha1(manifesto_text.encode('utf-8')).hexdigest()
        
        if root_tree_hash is None:
            root_tree_hash = current_folder_hash

        for item_type, path, item_hash in entries:
            if item_type == "file":
                update_2nd_table(root_tree_hash, path, item_hash)
        
        return current_folder_hash

    except Exception as e:
        print(f"An error occurred: {e}")
        quit()

def create_commit_hash(tree_hash: str, parent_hash, message: str,time: str) -> str:
    metadata = f"tree: {tree_hash} | parent: {parent_hash} | message: {message} | time: {time}"
    commit_hash = hashlib.sha1(metadata.encode('utf-8')).hexdigest()
    
    return commit_hash
def get_latest_commit_hash():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    sql_command = "SELECT hash FROM commits ORDER BY timestamp DESC LIMIT 1;"
    
    cursor.execute(sql_command)
    
    result = cursor.fetchone()
    
    conn.close() 

    if result is not None:
        parent_hash = result[0]
    else:
        parent_hash = None

    return parent_hash

def create_commit(message: str, folder_path: str) -> None:
    tree_hash = scan_directory(folder_path)
    
    parent_hash = get_latest_commit_hash()
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    commit_hash = create_commit_hash(tree_hash, parent_hash, message, current_time)
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO commits (hash, tree_hash, parent_hash, message, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (commit_hash, tree_hash, parent_hash, message, current_time))
    
    conn.commit()
    conn.close()
    
    print(f"Commit successful!")
    print(f"  Commit Hash: {commit_hash}")
    print(f"  Parent Hash: {parent_hash}")

def get_tracked_files(commit_hash):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    query = """
    SELECT te.file_path, te.blob_hash 
    FROM tree_entries te
    JOIN commits c ON te.tree_hash = c.tree_hash
    WHERE c.hash = (
        SELECT hash FROM commits ORDER BY timestamp DESC LIMIT 1
    );
"""
    cursor.execute(query)
    result = cursor.fetchall()

    conn.close()
    print(result)

    return dict(result)

def get_live_files(dir_path: str) -> dict:
    project_root = os.path.abspath(".")
    live_files = {}
    
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if d not in ignore and not d.startswith('.')]
        
        for file in files:
            if file.startswith('.') or file in ignore:
                continue
                
            abs_path = os.path.abspath(os.path.join(root, file))
            relative_path = os.path.relpath(abs_path, project_root)
            
            try:
                with open(relative_path, "rb") as f:
                    content = f.read()
                file_hash = hashlib.sha1(content).hexdigest()
                live_files[relative_path] = file_hash
            except FileNotFoundError:
                continue
                
    return live_files

def vcs_status(folder_path: str) -> None:
    latest_commit = get_latest_commit_hash()
    
    if latest_commit is None:
        tracked_files = {}
    else:
        tracked_files = get_tracked_files(latest_commit)
        
    live_files = get_live_files(folder_path)
    
    untracked = []
    modified = []
    deleted = []
    
    for path, live_hash in live_files.items():
        if path not in tracked_files:
            untracked.append(path)
        elif tracked_files[path] != live_hash:
            modified.append(path)
            
    for path in tracked_files.keys():
        if path not in live_files:
            deleted.append(path)
            
    print("\n--- PROJECT STATUS ---")
    
    if modified:
        print("\n🟡 Modified files:")
        for file in modified:
            print(f"  modified:   {file}")
            
    if untracked:
        print("\n🟢 Untracked files (New):")
        for file in untracked:
            print(f"  untracked:  {file}")
            
    if deleted:
        print("\n🔴 Deleted files:")
        for file in deleted:
            print(f"  deleted:    {file}")
            
    if not modified and not untracked and not deleted:
        print("\nNothing changed. Working tree completely clean!")
    print("----------------------\n")


if __name__ == "__main__":
    folder_path = Path(".")
    vcs_status(folder_path)