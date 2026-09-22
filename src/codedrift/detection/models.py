from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class APIChange:
    change_type: str
    qualified_name: str

    old_value: Optional[str] = None
    new_value: Optional[str] = None

    parameter_name: Optional[str] = None

    severity: str = "MEDIUM"

    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiffResult:
    changes: list[APIChange]

    def to_dict(self) -> dict:
        return {
            "total_changes": len(self.changes),
            "changes": [
                change.to_dict()
                for change in self.changes
            ],
        }