#!/usr/bin/env bash
# Inputs for the v2 build. Nothing here is committed: raw files stay in /tmp.
set -euo pipefail
RAW=${SL_RAW:-/tmp/nflraw}; BL=${SL_BL:-/tmp/bl}; mkdir -p "$RAW" "$BL"
for f in props_nfl games_nfl nfl_dvp analyst_nfl prop_prices; do curl -fsSL "https://betlab.sportslabshq.com/data/$f.json" -o "$BL/$f.json"; done
R=https://github.com/nflverse/nflverse-data/releases/download
curl -fsSL "$R/pbp/play_by_play_2025.parquet" -o "$RAW/pbp_2025.parquet"
curl -fsSL "$R/pbp/play_by_play_2026.parquet" -o "$RAW/pbp_2026.parquet"
curl -fsSL "$R/players/players.csv" -o "$RAW/players.csv"
curl -fsSL "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv" -o "$RAW/games.csv"
