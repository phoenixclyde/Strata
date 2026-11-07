#!/bin/bash
# W828 A/B: 0.1.53 vs 0.1.54narrow, both with the production args. Sequenced, logs kept per arm.
set -u
TMP=/home/albus/strata166/tmp
DATA=/home/albus/strata166/data
cd "$TMP" || exit 1
for arm in "$@"; do
  case "$arm" in
    a153)  cfg=/data/w828_a153.json ;;
    b154n) cfg=/data/w828_b154n.json ;;
    b154w) cfg=/data/w828_b154w.json ;;
    b154n2) cfg=/data/w828_b154n2.json ;;
    b154n4) cfg=/data/w828_b154n4.json ;;
    b154na) cfg=/data/w828_b154na.json ;;
    b154nh) cfg=/data/w828_b154nh.json ;;
    *) echo "unknown arm $arm"; continue ;;
  esac
  bash "$TMP/w828_arm.sh" "$arm" "$cfg" "w828$arm" 900 1 2>&1 | tee -a "$DATA/w828_ab_$arm.txt"
  echo "---- arm $arm done $(date +%H:%M:%S) ----" | tee -a "$DATA/w828_ab_$arm.txt"
done
