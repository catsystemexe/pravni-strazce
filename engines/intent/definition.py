# engines/intent/definition.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class IntentDefinition:
    intent_id: str
    label_cs: str
    domain: str
    subdomains: List[str]
    description_cs: str
    keywords: List[str]
    negative_keywords: List[str]
    risk_patterns: List[Dict[str, Any]]
    basic_questions: List[str]
    safety_questions: List[str]
    normative_references: List[str]
    conclusion_skeletons: Dict[str, str]
    notes: Optional[str] = None
    version: Optional[str] = None