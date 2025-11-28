#!/usr/bin/env bash
# Testy v čistém skeleton režimu – bez LLM hooku

unset CORE_LEGAL_USE_LLM
pytest -q