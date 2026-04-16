"""Validation Result Information bundle"""

from dataclasses import dataclass
from enum import Enum, auto
from uuid import UUID


class ValidationCode(Enum):
    """Terse Validation reasons"""
    # TODO: consider flags for more thorough validation codes (combinations)
    # Will only be relevant if validation routines don't terminate early
    VALID = (auto(), "")
    CYCLE_FOUND = (auto(), "Cycle in data hierarchy.  Parent can be re-reached from children")
    ORIGIN_INVALID = (auto(), "Origin of Entry is either null or does not exist")
    TYPE_ERROR = (auto(), "Entry has data of invalid type")
    READBACK_INVALID = (auto(), "Entry has an invalid readback")
    UNFILLED_PLACEHOLDERS = (auto(), "Entry has unfilled placeholders, please fill before saving")

    def __init__(self, value, description: str):
        self._value_ = value
        self.description = description


@dataclass(frozen=True)
class ValidationResult:
    # UUID of entry being validated
    uuid: UUID
    # Reason for validation status
    code: ValidationCode = ValidationCode.VALID
    # Verbose reason, with information to supplement the ValidationCode
    reason: str = ""

    def __bool__(self) -> bool:
        return self.code is ValidationCode.VALID

    def __str__(self) -> str:
        msg = f"Entry with uuid {self.uuid}"
        if self:
            msg += "is valid"
        else:
            msg += f"is not valid: {self.reason}"

        return msg
