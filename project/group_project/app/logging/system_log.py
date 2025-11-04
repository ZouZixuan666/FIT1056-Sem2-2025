from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any

@dataclass
class SystemLog:
    logID: str
    userID: str     # who triggered the event — can be "SYSTEM", staffID, etc.
    action: str     # description of what happened
    timestamp: str  # ISO timestamp

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SystemLog":
        return SystemLog(
            logID=d["logID"],
            userID=d["userID"],
            action=d["action"],
            timestamp=d["timestamp"]
        )
