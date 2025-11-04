from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from app.users.user import User
from app.users.preferences import Preferences

@dataclass
class Patient(User):
    patientID: str
    age: Optional[int] = None
    condition: Optional[str] = None
    assignedStaffID: Optional[str] = None
    preferences: Optional[Preferences] = None

    def __post_init__(self):
        # Keep userID consistent with patientID
        self.userID = self.patientID

    def getPreferences(self):
        return self.preferences

    def updatePreferences(self, new_prefs: Preferences):
        self.preferences = new_prefs

    def to_dict(self):
        data = asdict(self)
        if self.preferences:
            data["preferences"] = self.preferences.to_dict()
        return data

    @staticmethod
    def from_dict(d: Dict[str, Any]):
        # Ensure 'prefs' is always defined and robustly parsed
        prefs: Optional[Preferences] = None
        pref_data = d.get("preferences")
        if isinstance(pref_data, dict):
            try:
                prefs = Preferences.from_dict(pref_data)
            except Exception:
                prefs = None

        # Supply userID (required by base User dataclass)
        return Patient(
            userID=d.get("userID", d["patientID"]),
            name=d.get("name", ""),
            patientID=d["patientID"],
            age=d.get("age"),
            condition=d.get("condition"),
            assignedStaffID=d.get("assignedStaffID"),
            preferences=prefs,
        )
