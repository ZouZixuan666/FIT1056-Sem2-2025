from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class Admin:
    staffID: str   # e.g., "A001"
    name: str
    def __post_init__(self):
        self.userID = self.staffID
        
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Admin":
        return Admin(
            staffID=d["staffID"],
            name=d.get("name", ""),
        )
