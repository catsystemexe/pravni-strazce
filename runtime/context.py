"""
Základní datové struktury pro běh agenta.

Tady NENÍ právní logika, jen typy a struktury, se kterými pracuje orchestrátor a enginy.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class UserRole(str, Enum):
    CLIENT = "client"
    ADVOKAT = "advokat"


class LegalDomain(str, Enum):
    CIVIL = "civil"
    TRESTNI = "trestni"
    RODINA = "rodina"
    SPRAVNI = "spravni"
    PRACOVNI = "pracovni"
    SPOTREBITELSKE = "spotrebitelske"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class UserIntent(str, Enum):
    LEGAL_EXPLANATION = "legal_explanation"
    PROCEDURAL_STRATEGY = "procedural_strategy"
    DOCUMENT_DRAFTING = "document_drafting"
    CONTRACT_REVIEW = "contract_review"
    CASE_LAW_LOOKUP = "case_law_lookup"
    NEGOTIATION_LETTER = "negotiation_letter"
    STRATEGY_COACH = "strategy_coach"
    UNKNOWN = "unknown"


@dataclass
class CaseContext:
    """
    Vnitřní reprezentace "co řešíme":

    - user_query: původní dotaz
    - role: klient / advokát
    - domain: právní oblast
    - risk_level: low/medium/high
    - intent: typ požadavku (vysvětlení, dokument, strategie...)
    """

    user_query: str
    role: UserRole = UserRole.CLIENT
    domain: LegalDomain = LegalDomain.UNKNOWN
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    intent: UserIntent = UserIntent.UNKNOWN

    facts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Enum → value
        d["role"] = self.role.value
        d["domain"] = self.domain.value
        d["risk_level"] = self.risk_level.value
        d["intent"] = self.intent.value
        return d


@dataclass
class EngineResult:
    name: str
    data: Dict[str, Any]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data": self.data,
            "notes": self.notes,
        }
