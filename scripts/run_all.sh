#!/bin/bash
# Run all three variants and save outputs to runs/
set -e

echo "=== Run 1: Baseline ==="
python -m research_agent.cli run --ticker SRVCABLE --pack data/research_pack --as-of 2026-09-23 --variant baseline --out runs/run_1_baseline
cp prompts/*.md runs/run_1_baseline/prompts/

echo ""
echo "=== Run 2: Triage ==="
python -m research_agent.cli run --ticker SRVCABLE --pack data/research_pack --as-of 2026-09-23 --variant triage --out runs/run_2_triage
cp prompts/*.md runs/run_2_triage/prompts/

echo ""
echo "=== Run 3: Full ==="
python -m research_agent.cli run --ticker SRVCABLE --pack data/research_pack --as-of 2026-09-23 --variant full --out runs/run_3_verify
cp prompts/*.md runs/run_3_verify/prompts/

echo ""
echo "All runs complete."
