"""Verify local setup: Python version, env, data files, imports, and app entrypoints."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass


def check(name, condition, fix=None):
    status = "✅" if condition else "❌"
    print(f"  {status} {name}")
    if not condition and fix:
        print(f"     Fix: {fix}")
    return condition


print("\n🧬 Clinical Trial Intelligence - Setup Check\n")
print("ENVIRONMENT:")
check("Python 3.11+", sys.version_info >= (3, 11), "Install Python 3.11")
check(
    ".env file exists",
    os.path.exists(os.path.join(ROOT, ".env")),
    "Run: cp .env.example .env",
)
key = os.getenv("ANTHROPIC_API_KEY")
check(
    "ANTHROPIC_API_KEY set",
    bool(key and key != "your_anthropic_api_key_here"),
    "Add your key to .env (optional, app works in demo mode without it)",
)
gkey = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
check(
    "GEMINI_API_KEY or GOOGLE_API_KEY set",
    bool(gkey and gkey not in ("your_gemini_api_key_here", "your_google_api_key_here")),
    "Add Gemini key to .env (optional, used for RAG when set)",
)

print("\nDATA:")
check(
    "Demo CSV exists",
    os.path.exists(os.path.join(ROOT, "data/processed/demo_trials.csv")),
    "Run: python scripts/generate_demo_data.py",
)
check(
    "DuckDB exists",
    os.path.exists(os.path.join(ROOT, "data/trials.duckdb")),
    "Run: python scripts/generate_demo_data.py",
)
check(
    "data/raw/ directory",
    os.path.exists(os.path.join(ROOT, "data/raw")),
    "Run: mkdir -p data/raw",
)

print("\nPACKAGES:")
packages = [
    "streamlit",
    "duckdb",
    "pandas",
    "numpy",
    "econml",
    "dowhy",
    "shap",
    "faiss",
    "sentence_transformers",
    "plotly",
    "jinja2",
]
for pkg in packages:
    try:
        __import__(pkg.replace("-", "_"))
        check(pkg, True)
    except ImportError:
        check(pkg, False, f"pip install {pkg}")

print("\nAPP FILES:")
app_files = [
    "app/Main.py",
    "app/pages/01_Data_Explorer.py",
    "app/pages/02_Causal_Analysis.py",
    "app/pages/03_Trial_Simulator.py",
    "app/pages/04_RAG_Assistant.py",
    "app/pages/05_Report_Generator.py",
]
for f in app_files:
    check(f, os.path.exists(os.path.join(ROOT, f)))

print("\n")
if all(
    [
        os.path.exists(os.path.join(ROOT, "data/processed/demo_trials.csv")),
        os.path.exists(os.path.join(ROOT, "app/Main.py")),
    ]
):
    print("🚀 Ready to run: streamlit run app/Main.py\n")
else:
    print("⚠️  Fix the issues above before running the app.\n")
