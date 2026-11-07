#!/bin/bash
S=/home/albus/strata166/pr/strata-fork/serve/server.py
echo "=== parallel_slots() ==="
sed -n '3670,3730p' "$S"
echo
echo "=== admission: _admit_next and the single turn ==="
sed -n '1861,1920p' "$S"
