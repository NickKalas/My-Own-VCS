import hashlib
import zlib
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

if __name__ == "__main__":
    stage_file("test.txt")