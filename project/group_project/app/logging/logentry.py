from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class LogEntry:
    logID: str
    patientID: str
    staffID: str
    timestamp: str  # ISO
    temperature: Optional[float] = None
    heartRate: Optional[int] = None
    bloodPressure: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]):
        return LogEntry(
            logID=d["logID"],
            patientID=d["patientID"],
            staffID=d["staffID"],
            timestamp=d["timestamp"],
            temperature=d.get("temperature"),
            heartRate=d.get("heartRate"),
            bloodPressure=d.get("bloodPressure"),
            notes=d.get("notes"),
        )