#!/usr/bin/env bash
# Testy s LLM hookem povoleným přes env proměnnou.
# Pozn: pytest sám LLM nevolá, ale můžeš tak ověřit, že se nic nerozbije
# když je CORE_LEGAL_USE_LLM=1 nastaveno.

export CORE_LEGAL_USE_LLM=1
pytest -q