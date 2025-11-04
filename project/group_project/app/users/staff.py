from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from app.users.user import User

@dataclass
class Staff:
    staffID: str
    name: str
    role: str  # "admin", "care"
    assignedPatients: List[str] = None

    def __post_init__(self):
        self.userID = self.staffID
        if self.assignedPatients is None:
            self.assignedPatients = []

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]):
        return Staff(
            staffID=d["staffID"],
            name=d.get("name", ""),
            role=d.get("role", "care"),
            assignedPatients=d.get("assignedPatients", []),
        )
