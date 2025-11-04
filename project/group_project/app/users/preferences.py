from typing import List, Dict, Any

class Preferences:
    def __init__(self, patientID: str, dietaryNeeds: List[str] = None, 
                 culturalNeeds: str = "", religiousNeeds: List[str] = None):
        self.patientID = patientID
        self.dietaryNeeds = dietaryNeeds or []
        self.culturalNeeds = culturalNeeds
        self.religiousNeeds = religiousNeeds or []

    def addPreference(self, category: str, value: Any):
        if category == "dietary":
            self.dietaryNeeds.append(value)
        elif category == "religious":
            self.religiousNeeds.append(value)
        elif category == "cultural":
            self.culturalNeeds = value
        else:
            raise ValueError("Invalid category")
        self._validatePreference()

    def editPreference(self, new_data: Dict[str, Any]):
        for key, val in new_data.items():
            if hasattr(self, key):
                setattr(self, key, val)
        self._validatePreference()

    def _validatePreference(self) -> bool:
        return isinstance(self.dietaryNeeds, list) and isinstance(self.religiousNeeds, list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patientID": self.patientID,
            "dietaryNeeds": self.dietaryNeeds,
            "culturalNeeds": self.culturalNeeds,
            "religiousNeeds": self.religiousNeeds
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            patientID=data["patientID"],
            dietaryNeeds=data.get("dietaryNeeds", []),
            culturalNeeds=data.get("culturalNeeds", ""),
            religiousNeeds=data.get("religiousNeeds", [])
        )
