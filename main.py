# main.py - GUI Launcher with logging & backup
import os
from gui.main_dashboard import launch
from app.admin_utils import init_logger, backup_data
from app.schedule import DATA_FILE, DATA_DIR

if __name__ == "__main__":
    # Initialize logger before GUI starts
    LOG_FILE = os.path.join(DATA_DIR, "msms.log")
    init_logger(LOG_FILE)

    # Create backup of current data before running
    BACKUP_DIR = os.path.join(DATA_DIR, "backups")
    backup_data(DATA_FILE, BACKUP_DIR)

    # Launch the GUI
    launch()
