import hashlib
import zlib
import os
from pathlib import Path
from database import update_1st_table

def stage_file(file_path: str) -> None:
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        hash_object = hashlib.sha1(content)
        hex_digest = hash_object.hexdigest()

        compressed_data = zlib.compress(content)

        update_1st_table(hex_digest, compressed_data)

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' could not be found.")
    except Exception as e:
        print(f"An unexpected error occurred while staging {file_path}: {e}")

def scan_directory(dir_path: str) -> str:
    try:
        for item in os.scandir(dir_path):
            file_path = os.path.abspath(Path(item))
            item_name = os.path.basename(file_path)

            if item_name.startswith('.') or item_name == "database.db":
                continue
            elif item.is_file():
                stage_file(file_path)
            elif item.is_dir():
                scan_directory(file_path)
            else:
                print("Something did not go well, try again!!!")
    except Exception as e:
        print(f"An error occured: {e}")
        quit()

if __name__ == "__main__":
    folder_path = Path("C:\\Users\\nikos\\OneDrive\\Desktop\\Automation\\my_own_git")
    scan_directory(folder_path)