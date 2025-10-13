# app/admin_utils.py
import logging
import shutil
import datetime
import os

def init_logger(log_file="msms.log"):
    """Configures the root logger to write to a file."""
    # TODO: Configure basic logging. Set the level to INFO.
    # Set the format to include a timestamp, level name, and message.
    # Set the output file (handler).
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=log_file,
        filemode='a' # Append to the log file
    )
    print(f"Logging configured. Outputting to {log_file}")

def backup_data(data_path="data/msms.json", backup_dir="data/backups"):
    """Creates a timestamped backup of the main data file."""
    # TODO: Check if the backup directory exists, and create it if it doesn't.
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # TODO: Create a timestamp string (e.g., YYYY-MM-DD_HH-MM-SS).
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"msms_backup_{timestamp}.json"
    backup_filepath = os.path.join(backup_dir, backup_filename)
    
    try:
        # TODO: Use shutil.copy() to copy the data_path to the backup_filepath.
        shutil.copy(data_path, backup_filepath)
        # Use the logging module to record this event.
        logging.info(f"Data successfully backed up to {backup_filepath}")
        return True
    except Exception as e:
        # Log any errors that occur during the backup process.
        logging.error(f"Failed to create backup: {e}")
        return False