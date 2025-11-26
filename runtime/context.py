"""
Základní datové struktury pro běh agenta.

TODO:
- definovat CaseContext (fakta, role uživatele, jurisdikce, doména)
- definovat UserProfile (laik / advokát)
- definovat EngineRequest / EngineResponse pro jednotlivé moduly
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CaseContext:
    user_query: str
    role: str = "client"        # 'client' | 'advokat'
    domain: Optional[str] = None  # 'civil', 'trestni', 'rodina', ...
    risk_level: Optional[str] = None  # 'low' | 'medium' | 'high'
    intent: Optional[str] = None  # 'legal_explanation', 'document_drafting', ...

    facts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineResult:
    name: str
    data: Dict[str, Any]
    notes: List[str] = field(default_factory=list)
