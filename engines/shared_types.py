"""
Společné typy pro všechny engines.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class EngineInput:
    context: Dict[str, Any]
    config: Dict[str, Any] | None = None


@dataclass
class EngineOutput:
    name: str
    payload: Dict[str, Any]
    notes: List[str] = field(default_factory=list)
