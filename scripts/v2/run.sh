#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
bash scripts/v2/fetch_inputs.sh
python3 scripts/v2/analytics.py && python3 scripts/v2/sim2.py
python3 scripts/v2/build.py && (python3 scripts/v2/bio.py || echo "bio skipped") && python3 scripts/v2/merge_pp.py && python3 scripts/v2/td_v2.py && python3 scripts/v2/guard.py
