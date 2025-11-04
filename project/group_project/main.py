# main.py - GUI Launcher
# Usage: python main.py
import subprocess, sys
from gui.main_dashboard import launch
from pathlib import Path



HERE = Path(__file__).resolve().parent
entry = HERE / "gui" / "main_dashboard.py"
cmd = [sys.executable, "-m", "streamlit", "run", str(entry)]
if __name__ == "__main__":
    launch()
raise SystemExit(subprocess.call(cmd))

