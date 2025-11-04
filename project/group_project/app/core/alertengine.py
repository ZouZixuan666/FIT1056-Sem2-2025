from app. database.database_Manager import DatabaseManager
from app. logging.logentry import LogEntry
from app. core.alert import Alert
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

class AlertEngine:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def evaluate(self, log: LogEntry) -> Optional[Alert]:
        # Example rules:
        # - temperature > 38.0 => high severity
        # - heartRate > 120 => medium/high depending
        msg = None
        severity = "low"
        if log.temperature is not None and log.temperature > 38.0:
            msg = f"High temperature: {log.temperature}°C"
            severity = "high"
        elif log.heartRate is not None and log.heartRate > 120:
            msg = f"High heart rate: {log.heartRate} bpm"
            severity = "medium"

        if msg:
            alert = Alert(
                alertID=f"A{len(self.db.alerts)+1:06d}",
                patientID=log.patientID,
                staffID=log.staffID,
                timestamp=datetime.utcnow().isoformat() + "Z",
                message=msg,
                severity=severity,
                isRead=False,
            )
            self.db.add_alert(alert)
            return alert
        return None
    
    def generateAlert(self, patientID: str, staffID: str, msg: str, severity: str = "low") -> Alert:
        """
        Manually create an alert (e.g., system or user triggered).
        """
        alert = Alert(
            alertID=f"A{uuid.uuid4().hex[:8].upper()}",
            patientID=patientID,
            staffID=staffID,
            timestamp=datetime.utcnow().isoformat() + "Z",
            message=msg.strip(),
            severity=severity,
            isRead=False,
        )
        self.db.add_alert(alert)
        return alert
    
    def getAlertsByStaff(self, staffID: str) -> List[Alert]:
        """
        Retrieve all alerts assigned to a specific staff member.
        """
        return self.db.get_alerts_for_staff(staffID)
    
    def getUnreadAlertsByStaff(self, staffID: str) -> List[Alert]:
        """
        Returns unread alerts for a specific staff member.
        """
        return [a for a in self.db.alerts if a.staffID == staffID and not a.isRead]

    def getAlertsBySeverity(self, severity: str) -> List[Alert]:
        """
        Returns alerts filtered by severity (e.g. 'low', 'medium', 'high').
        """
        return [a for a in self.db.alerts if a.severity.lower() == severity.lower()]
    
    def markAlertAsRead(self, alertID: str) -> bool:
        """
        Marks a specific alert as read and persists the change to disk.
        Returns True if successful, False if alert not found.
        """
        for alert in self.db.alerts:
            if alert.alertID == alertID:
                alert.mark_as_read()
                self.db.save_all()
                return True
        return False