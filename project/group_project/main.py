# main.py - GUI Launcher
# Usage: python main.py
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
entry = HERE / "gui" / "main_dashboard.py"
cmd = [sys.executable, "-m", "streamlit", "run", str(entry)]
raise SystemExit(subprocess.call(cmd))
