"""HuggingFace Spaces entrypoint.

HF Spaces with sdk=streamlit runs ``streamlit run app.py`` automatically.
We just re-exec the real entrypoint so the multi-page layout works.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))

port = os.environ.get("PORT", "7860")

if __name__ == "__main__":
    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run", "app/main.py",
            f"--server.port={port}",
            "--server.address=0.0.0.0",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ],
        check=True,
    )
