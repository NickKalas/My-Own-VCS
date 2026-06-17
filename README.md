# MyOwnGit 🛠️

A lightweight, fully functional custom **Version Control System (VCS)** built from scratch in Python. Inspired by the internal architecture of Git, this tool uses content-addressable storage, zlib data compression, and a relational SQLite backend to track file changes, check directory states, and handle workspace time travel.

---

## 🚀 Core Features

* **Content-Addressable Blob Storage:** Files are identified entirely by their `SHA-1` cryptographic hashes rather than their arbitrary disk names.
* **Data Compression:** Implements `zlib` storage optimization to minimize memory and disk footprints on the host system.
* **Tree Architecture:** Re-creates structural directory layouts cleanly using deterministic tree entry snapshots.
* **Workspace Diagnostics (`--status`):** Real-time comparative logic to track **🟢 Untracked**, **🟡 Modified**, and **🔴 Deleted** files.
* **Time Travel Engine (`--checkout`):** Reconstructs and fully overwrites local physical workspaces to perfectly mirror historical commits.

---

## 🏗️ Architectural Insights

### Deterministic Tree Layout (Why We Sort)
When calculating the root hash signature for a directory layout, the program relies on alphabetical item sorting (`entries.sort()`). This is a critical design feature. Operating systems read disk items non-deterministically; without explicit ordering, identical directories could generate mismatched tree states across distinct environments. Sorting strips this OS inconsistency completely out of the equation.

### Relational Database Bridge
Instead of duplicating file records heavily across unique saves, the architecture links an internal historical timeline table (`commits`) down to file blueprints (`tree_entries`) on demand via optimized SQLite `JOIN` query lookups, keeping storage light and performance lightning-fast.

---

## 🔍 Core Engine Code Tour

Here is a breakdown of what each function does inside the core engine (`main.py`):

### 📋 Environment & Configuration
* **`load_the_ignore_files()`**: Reads the local `.ignore` file line-by-line, strips whitespace, and extracts user-defined rules into a global exclusion list. It includes a fallback mechanism to prevent crashes if no `.ignore` asset is found.

### 🗜️ Core Hashing & Scanning
* **`stage_file(file_path)`**: Opens a file in binary mode, generates its unique `SHA-1` checksum fingerprint, compresses its contents using `zlib`, and saves it to the database using `update_1st_table`. Returns the file's hash identifier.
* **`scan_directory(dir_path)`**: Recursively drills down through your project directories using `os.scandir`. It bypasses hidden and ignored assets, stages files, builds a deterministic sorted "manifesto string" representing the snapshot layout, and saves file paths to `update_2nd_table`. Returns a single root `tree_hash`.
* **`create_commit_hash(tree_hash, parent_hash, message, time)`**: Takes all relevant commit metadata strings, links them together, and outputs a unique `SHA-1` signature representing that specific state in your project's timeline.

### ⏱️ Timeline & History Logging
* **`get_latest_commit_hash()`**: Queries the database to find the absolute newest commit based on timestamp sequence. This is used to determine what the `parent_hash` should be for incoming commits.
* **`create_commit(message, folder_path)`**: The orchestrator for making a save point. It builds a directory layout tree, logs the parent link, timestamps the event, computes the new commit hash, and writes a permanent record into the `commits` database table.
* **`vcs_log()`**: Fetches a clean list of all past save data from the database sorted chronologically backwards (`ORDER BY timestamp DESC`) and renders your project's entire historical timeline explicitly using colored shell components.

### 🎯 Workspace Comparison Matrix
* **`get_tracked_files(commit_hash)`**: Performs a relational SQL `JOIN` query connecting `tree_entries` and `commits`. It maps the snapshot blueprint associated with a target commit back into a fast key-value Python dictionary (`{file_path: content_hash}`).
* **`get_live_files(dir_path)`**: Uses `os.walk` to scrape your active physical workstation drive right now. It ignores blacklisted rules, calculates on-the-fly `SHA-1` file hashes, and returns a live footprint dictionary.
* **`vcs_status(folder_path)`**: The evaluation center. It takes the dictionaries from `get_tracked_files` and `get_live_files`, cross-references their paths and content fingerprints side-by-side, and prints out modified (yellow), untracked (green), or deleted (red) items.

### ⏳ Time Travel System
* **`get_files_from_commit(commit_hash)`**: Targets a precise, historical user-selected commit hash to safely extract the specific path-to-blob database mapping for that snapshot in history.
* **`get_compressed_blob(hash)`**: Pulls the raw, compressed `zlib` binary stream out of the database's `blobs` storage table for a target file hash.
* **`vcs_checkout(commit_hash)`**: Our time-travel mechanic. It fetches a targeted historical blueprint, reads the matching compressed blobs, runs `zlib.decompress()`, automatically re-creates any missing subfolders locally, and overwrites your workspace to flawlessly reflect the past.

---

## 🛠️ CLI Command Guide

Run the system directly from your project terminal:

### 1. Check Working Tree Status
Scans your workspace against your latest commit to identify local mutations.

**`python main.py --status`**

### 2. Take a Snapshot (Commit)

Hashes, compresses, and logs your live files into the database under a descriptive timestamp.
Bash

**`python main.py --commit "Fixed scanner folder layout filter bug"`**

### 3. Review History Logs

Prints a chronological, descending history map of your project's lifetime timeline.
Bash

**`python main.py --log`**

### 4. Travel Back in Time (Checkout)

Pulls historical blueprints, processes binary decompression, and reconstructs workspace states instantly.
Bash

**`python main.py --checkout <COMMIT_HASH>`**

### 5. Clear Database (Destructive)
Completely destroys the underlying SQLite `database.db` repository container. Features a strict terminal verification wall to prevent accidental data erasure.

**`python main.py --clear`**

### 🛑 Ignore Rules

The engine natively skips all underlying hidden files, system files, and database entities. You can declare additional file exclusions or operational directories to omit globally by establishing a local .ignore asset in your root workspace path.
Plaintext

# Example .ignore structure
secret_keys.txt\n
node_modules\n
dist
