# app/logging/patient_Log.py
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.validator import Validator, atomic_write_json, read_json_file
from app.core.audit import audit
from typing import List, Dict, Any, Callable, Optional
class PatientLog:
    """
    Handles creation, retrieval, and filtering of patient logs.
    Logs are stored in JSON format for reliability and portability.
    """

    def __init__(self, path: str = "data/patient_logs.json"):
        self.path = path
        
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        # Initialize file if it doesn't exist
        if not os.path.exists(self.path):
            self._save_logs([])

    def _load_logs(self) -> List[Dict[str, Any]]:
        """Read and return all logs."""
        try:
            return read_json_file(self.path)
        except Exception as e:
            # Log the error and return empty list as fallback
            audit("patient.log.read_error", None, None, {"error": str(e)})
            return []

    def _save_logs(self, logs: List[Dict[str, Any]]):
        """Write the logs safely to disk."""
        try:
            atomic_write_json(self.path, logs)
        except Exception as e:
            audit("patient.log.write_error", None, None, {"error": str(e)})
            raise

    def add_log(self, log_entry: Dict[str, Any]):
        """
        Add a new log entry after validating its structure.
        Required fields: logID, patientID, staffID
        Optional: temperature, note, timestamp
        """
        # Validate the log entry structure
        Validator.validate_log_entry_dict(log_entry)

        # Assign timestamp if missing
        if "timestamp" not in log_entry:
            log_entry["timestamp"] = datetime.utcnow().isoformat() + "Z"

        logs = self._load_logs()
        
        # Check for duplicate logID
        if any(log.get("logID") == log_entry.get("logID") for log in logs):
            raise ValueError(f"Log with ID {log_entry.get('logID')} already exists")
        
        logs.append(log_entry)
        self._save_logs(logs)

        # Audit trail
        audit(
            "patient.log.add",
            who=log_entry.get("staffID"),
            role="staff",
            details={
                "patient": log_entry.get("patientID"), 
                "logID": log_entry.get("logID")
            },
        )

    def get_logs(self) -> List[Dict[str, Any]]:
        """Return all logs."""
        return self._load_logs()

    def find_by_patient(self, patient_id: str) -> List[Dict[str, Any]]:
        """Retrieve all logs related to a specific patient."""
        Validator.validate_patient_id(patient_id)
        logs = self._load_logs()
        return [log for log in logs if log.get("patientID") == patient_id]

    def find_by_staff(self, staff_id: str) -> List[Dict[str, Any]]:
        """Retrieve all logs recorded by a specific staff member."""
        Validator.validate_staff_id(staff_id)
        logs = self._load_logs()
        return [log for log in logs if log.get("staffID") == staff_id]
    
    def find_by_date(self, start: str, end: str):
        logs = self._load_logs()
        return [
            log for log in logs
            if start <= log.get("timestamp", "") <= end
        ]
    # ---------------------------------------------------------
    # FILTER FUNCTIONS FOR RESEARCHERS
    # ---------------------------------------------------------
    def filter_by_metric(
        self, 
        metric: str, 
        comparison: Callable[[float], bool]
    ):
        """
        Filters patients whose logs contain metric values meeting a condition.
        Example:
            filter_by_metric("temperature", lambda t: t > 38.0)
        """
        logs = self._load_logs()
        matching_ids = set()
        for log in logs:
            value = getattr(log, metric, None)
            if value is not None and comparison(value):
                matching_ids.add(log.patientID)
        return list(matching_ids)

    def find_patient_ids_by_note_keyword(self, keyword: str) -> list[str]:
        """
        Return a list of unique patient IDs that have at least one log entry
        containing the given keyword in their notes (case-insensitive).

        Example:
            find_patient_ids_by_note_keyword("fever") 
            → ["P001", "P004", "P010"]
        """
        keyword = keyword.lower()
        logs = self._load_logs()
        matched_ids = {
            log["patientID"]
            for log in logs
            if keyword in log.get("notes", "").lower()
        }
        return list(matched_ids)
    
    def delete_log(self, log_id: str, deleted_by: Optional[str] = None, 
                   role: Optional[str] = None) -> bool:
        """
        Delete a log entry by its logID.
        
        Args:
            log_id: The ID of the log to delete
            deleted_by: The staff/admin ID performing the deletion
            role: The role of the person deleting (staff/admin)
            
        Returns:
            True if deleted, False if not found
        """
        Validator.require_field("logID", log_id)
        
        logs = self._load_logs()
        
        # Find the log to be deleted (for audit trail)
        deleted_log = next((log for log in logs if log.get("logID") == log_id), None)
        
        updated_logs = [log for log in logs if log.get("logID") != log_id]

        if len(updated_logs) == len(logs):
            return False  # logID not found

        self._save_logs(updated_logs)
        
        # Enhanced audit trail with who performed the deletion
        audit(
            "patient.log.delete", 
            who=deleted_by, 
            role=role, 
            details={
                "logID": log_id,
                "patientID": deleted_log.get("patientID") if deleted_log else None
            }
        )
        return True