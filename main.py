# Import all the needed libraries
import hashlib
import zlib
import os
import sqlite3
import datetime
import argparse
from pathlib import Path
# Import the 2 update functions from the database.py file
from database import update_1st_table, update_2nd_table

# ANSI Escape Codes for terminal coloring
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# This function is loading the .ignore file IF it exists
def load_the_ignore_files() -> list:
    ignore = []
    try:
        with open(".ignore", "r") as ign:
            for line in ign:
                cleaned_line = line.strip()
                if cleaned_line:
                    ignore.append(cleaned_line)
    except FileNotFoundError:
        # Fallback if .ignore doesn't exist yet
        pass
    return ignore  
# Save the list of files we want to ignore because we will need it later on
ignore = load_the_ignore_files()
DATABASE_FILE = "database.db" # This variable is just to avoid hardcoding the database name when creating a connection

def stage_file(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        # After we read the binary data of the file we hash the info and we compress the data for storage efficiency
        hash_object = hashlib.sha1(content)
        hex_digest = hash_object.hexdigest()

        compressed_data = zlib.compress(content)
        # We update the 1st table with the information we got
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
            # Get some needed file information (Absolute path, relative path, item_name and also the extension)
            abs_path = os.path.abspath(item.path)
            relative_path = os.path.relpath(abs_path, project_root)
            item_name = os.path.basename(relative_path)
            _, item_ext = os.path.splitext(relative_path)
            # This if statement makes sure we do ignore all the wanted files + database and hidden files
            if item_name.startswith('.') or item_ext == ".db" or item_name in ignore:
                continue
            
            elif item.is_file():
                file_hash = stage_file(relative_path)
                entries.append(("file", relative_path, file_hash))
            
            elif item.is_dir():
                sub_tree_hash = scan_directory(relative_path, root_tree_hash)
                entries.append(("tree", relative_path, sub_tree_hash))
        # We sort the entries to avoid any system reading order problems -> Go into the README.md to learn more
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

def create_commit_hash(tree_hash: str, parent_hash, message: str, time: str) -> str:
    metadata = f"tree: {tree_hash} | parent: {parent_hash} | message: {message} | time: {time}"
    commit_hash = hashlib.sha1(metadata.encode('utf-8')).hexdigest()
    return commit_hash

def get_latest_commit_hash():
    conn = sqlite3.connect(DATABASE_FILE)
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

# This function just uses already built functions to get data and store them in the database
def create_commit(message: str, folder_path: str) -> None:
    tree_hash = scan_directory(folder_path)
    parent_hash = get_latest_commit_hash()
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    commit_hash = create_commit_hash(tree_hash, parent_hash, message, current_time)
    
    conn = sqlite3.connect(DATABASE_FILE)
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

# This function links/bridges 2 sql tables so that we can pull the information we need about the files 
def get_tracked_files(commit_hash):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    query = """
    SELECT te.file_path, te.blob_hash 
    FROM tree_entries te
    JOIN commits c ON te.tree_hash = c.tree_hash
    WHERE c.hash = ?;
    """
    cursor.execute(query, (commit_hash,))
    result = cursor.fetchall()
    conn.close()

    return dict(result)

# Function that will allow us later to make the comparisons we need to declare whether a file is Untracked, Modified or Deleted -> Go to the README for more information
def get_live_files(dir_path: str) -> dict:
    project_root = os.path.abspath(".")
    live_files = {}
    
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if d not in ignore and not d.startswith('.')]   
        
        for file in files:
            _, file_ext = os.path.splitext(file)
            if file.startswith('.') or file_ext == ".db" or file in ignore:
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

# We make the comparisons between the hashes of the files and add the files to the correct list
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
        print(f"\n{YELLOW}🟡 Modified files:{RESET}")
        for file in modified:
            print(f"  {YELLOW}modified:   {file}{RESET}")
            
    if untracked:
        print(f"\n{GREEN}🟢 Untracked files (New):{RESET}")
        for file in untracked:
            print(f"  {GREEN}untracked:  {file}{RESET}")
            
    if deleted:
        print(f"\n{RED}🔴 Deleted files:{RESET}")
        for file in deleted:
            print(f"  {RED}deleted:    {file}{RESET}")
            
    if not modified and not untracked and not deleted:
        print(f"\n{GREEN}Nothing changed. Working tree completely clean!{RESET}")
    print("----------------------\n")

# We go inside our database and pull information about all the past commits (Date, commit_hash and message)
def vcs_log() -> None:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    query = "SELECT hash, timestamp, message FROM commits ORDER BY timestamp DESC;"
    cursor.execute(query)
    all_commits = cursor.fetchall()
    conn.close()
    
    if not all_commits:
        print("\n No commits found. Create one using --commit!")
        return

    print(f"\n--- COMMIT LOG ({len(all_commits)} commits) ---")
    
    for row in all_commits:
        commit_hash = row[0]
        date = row[1]
        message = row[2]
        
        print(f"\n{YELLOW}Commit {commit_hash}{RESET}")
        print(f"Date:    {date}")
        print(f"Message: {message}")
        print("-" * 50)

# From this function we get the "blueprint" that your workspace had when you hit the commit command
def get_files_from_commit(commit_hash: str) -> dict:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    query = """
        SELECT te.file_path, te.blob_hash 
        FROM tree_entries te
        JOIN commits c ON te.tree_hash = c.tree_hash
        WHERE c.hash = ?;
    """
    cursor.execute(query, (commit_hash,))
    rows = cursor.fetchall()
    conn.close()
    return dict(rows)

# Here we get the file <<blueprint>>, the hash and the compressed data
def get_compressed_blob(hash: str) -> bytes:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    query = "SELECT compressed_data FROM blobs WHERE hash = ?;" 
    cursor.execute(query, (hash,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Now that we have everything we need, we just simply "connect" everything together to make the final checkout function
def vcs_checkout(commit_hash: str) -> None:
    file_map = get_files_from_commit(commit_hash)
    
    if not file_map:
        print(f"{RED}Error: Commit hash '{commit_hash}' not found or contains no tracked files.{RESET}")
        return
        
    print(f"Time traveling to commit {commit_hash[:8]}...")
    
    for file_path, blob_hash in file_map.items():
        compressed_data = get_compressed_blob(blob_hash)
        if compressed_data is None:
            print(f"{YELLOW}Warning: Missing blob data for {file_path}{RESET}")
            continue
            
        original_content = zlib.decompress(compressed_data)
        
        # Verify subfolders are generated recursively before writing contents
        file_dir = os.path.dirname(file_path)
        if file_dir:
            os.makedirs(file_dir, exist_ok=True)
            
        with open(file_path, "wb") as f:
            f.write(original_content)
            
    print(f"{GREEN}Checkout successful! Working environment restored.{RESET}")

if __name__ == "__main__":
    # Force Windows environments to load terminal formatting safely
    if os.name == 'nt':
        os.system('color')

    parser = argparse.ArgumentParser(
        description="MyOwnGit - A custom Version Control System built from scratch."
    )

    parser.add_argument(
        "--status", 
        action="store_true", 
        help="Show the working tree status (Modified, Untracked, and Deleted files)."
    )

    parser.add_argument(
        "--commit", 
        type=str, 
        metavar="MESSAGE", 
        help="Record a new snapshot of the project layout with a descriptive message."
    )
    
    parser.add_argument(
        "--log",
        action="store_true",
        help="Show your past activity/past commits"
    )

    parser.add_argument(
        "--checkout",
        type=str,
        metavar="COMMIT_HASH",
        help="Time travel your workspace files to match a distinct historical commit hash snapshot."
    )

    args = parser.parse_args()
    folder_path = Path(".")

    if args.status:
        vcs_status(folder_path)
    elif args.commit:
        create_commit(args.commit, folder_path)
    elif args.log:
        vcs_log()
    elif args.checkout:
        vcs_checkout(args.checkout)
    else:
        parser.print_help()