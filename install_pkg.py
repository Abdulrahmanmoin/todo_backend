import subprocess
import sys

try:
    print("Starting installation...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "openai-agents", "--no-cache-dir"], capture_output=True, text=True)
    print("Return code:", result.returncode)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    with open("install_log_full.txt", "w") as f:
        f.write(f"Return code: {result.returncode}\n")
        f.write(f"STDOUT:\n{result.stdout}\n")
        f.write(f"STDERR:\n{result.stderr}\n")
except Exception as e:
    print(f"Exception: {e}")
