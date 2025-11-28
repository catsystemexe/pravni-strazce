#!/usr/bin/env bash
set -e

# Zapnout LLM režimy pro celou pipeline
export CORE_LEGAL_USE_LLM=1
export PIPELINE_USE_LLM=1
export PRAVNI_STRAZCE_LLM_JUDIKATURA=1

python demo.py