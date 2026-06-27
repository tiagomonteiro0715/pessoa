"""Launcher: ensure Ollama is up, pull gemma4:e2b if missing, run the Streamlit UI."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from chat import ensure_model_pulled, ensure_server_env 

ensure_server_env()
ensure_model_pulled()
subprocess.run([sys.executable, "-m", "streamlit", "run",
                str(Path(__file__).parent / "src" / "app.py")])