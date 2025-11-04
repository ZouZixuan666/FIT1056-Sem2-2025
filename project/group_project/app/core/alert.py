from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
@dataclass
class Alert:
    alertID: str
    patientID: str
    staffID: str
    timestamp: str
    message: str
    severity: str  # "low","medium","high"
    isRead: bool = False

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]):
        return Alert(
            alertID=d["alertID"],
            patientID=d["patientID"],
            staffID=d["staffID"],
            timestamp=d["timestamp"],
            message=d.get("message", ""),
            severity=d.get("severity", "low"),
            isRead=d.get("isRead", False),
        )

    def mark_as_read(self) -> None:
        """
        Mark this alert as read/acknowledged by the staff.
        """
        self.isRead = True