#!/usr/bin/env python3

import sys
from pathlib import Path

# ---- FIX: zajistit, aby imports from engines.* fungovaly v GitHub Actions ----
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
# ------------------------------------------------------------------------------

import json
from engines.intent.loader import _normalize_raw
from engines.intent.definition import IntentDefinition
