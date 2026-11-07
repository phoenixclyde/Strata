#!/bin/bash
# W828b ABBA driver: ta (default) / tb (adapt 1/80/0.97), long decodes, phase ruler on both arms.
set -u
TMP=/home/albus/strata166/tmp
DATA=/home/albus/strata166/data
cd "$TMP" || exit 1
for arm in "$@"; do
  case "$arm" in
    ta) cfg=/data/w828_ta.json ;;
    tb) cfg=/data/w828_tb.json ;;
    tc) cfg=/data/w828_tc.json ;;
    td) cfg=/data/w828_td.json ;;
    te) cfg=/data/w828_te.json ;;
    tf) cfg=/data/w828_tf.json ;;
    tg) cfg=/data/w828_tg.json ;;
    th) cfg=/data/w828_th.json ;;
    tk) cfg=/data/w828_tk.json ;;
    tl) cfg=/data/w828_tl.json ;;
    tm) cfg=/data/w828_tm.json ;;
    *) echo "unknown arm $arm"; continue ;;
  esac
  bash "$TMP/w828_arm2.sh" "$arm" "$cfg" "w828$arm" 900 2>&1 | tee -a "$DATA/w828_ab2_$arm.txt"
  echo "---- $arm done $(date +%H:%M:%S) ----" | tee -a "$DATA/w828_ab2_$arm.txt"
done
