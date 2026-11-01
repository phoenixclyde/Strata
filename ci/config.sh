#!/bin/bash
# [Strata/gfx906] Single place for every path and name the pipeline uses.
# Nothing else in ci/ may hardcode these -- that is how the old one-off scripts drifted.

# --- repo / build ---------------------------------------------------------------
REPO=/home/albus/strata166/pr/strata-fork
BUILD=/home/albus/strata166/gfx029-build          # cmake build dir (container sees it as /out)
SRC_MOUNT=/src                                    # container path of $REPO

# --- runtime / production ------------------------------------------------------
DATA=/home/albus/strata166/data
BIN=$DATA/bin
CFG=$DATA/strata-huihui-ud-iq4_xs.json
CONTAINER=strata166-407
IMG=strata-gfx906:0.2.9-101
HEALTH=http://127.0.0.1:8090/health
ELOG=$DATA/strata-huihui-ud-iq4_xs.log

# --- pipeline state ------------------------------------------------------------
CI=/home/albus/strata166/ci
STATE=$CI/state
HISTORY=$STATE/prod_history.tsv
BACKUPS=$STATE/backups

# --- gates ---------------------------------------------------------------------
# Health must come back within this many seconds (measured: 233-290 s, seen 300+ once).
HEALTH_TIMEOUT=${HEALTH_TIMEOUT:-420}
# VRAM headroom: the engine must leave at least this much free, or the config grew.
VRAM_MIN_FREE_BYTES=${VRAM_MIN_FREE_BYTES:-300000000}
# The R-table rows a shape may declare.  Anything else is a typo, not a tuning choice.
ALLOWED_WAVE_ROWS="1 2 4"
# Tag prefix a deployable commit must carry.
TAG_PREFIX=mi50-

mkdir -p "$STATE" "$BACKUPS" 2>/dev/null || true
