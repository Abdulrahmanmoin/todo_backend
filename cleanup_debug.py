import os

files_to_delete = [
    "import_test.txt", "test.txt", "pip_list.txt", "pip_list_new.txt", 
    "debug_out.txt", "ps_test.txt", "ps_out.txt", "script_out.txt", 
    "install_out.txt", "check_import.py", "install_log_full.txt", 
    "install_batch.log"
]

for file in files_to_delete:
    if os.path.exists(file):
        try:
            os.remove(file)
            print(f"Deleted {file}")
        except Exception as e:
            print(f"Failed to delete {file}: {e}")
    else:
        print(f"{file} not found")
