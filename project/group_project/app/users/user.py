from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class User(ABC):
    userID: str
    name: str

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert the user object into a serializable dict"""
        return asdict(self)

    @staticmethod
    @abstractmethod
    def from_dict(data: Dict[str, Any]):
        """Reconstruct user object from dict"""
        pass
