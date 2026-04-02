import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# This file exists for HuggingFace Spaces compatibility
# The actual app is in app/main.py
if __name__ == "__main__":
    subprocess.run(["streamlit", "run", "app/main.py", "--server.port=7860"])
