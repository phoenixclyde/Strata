import sys
sys.path.insert(0, "albus/r5")
from _rsh import sh
print(sh(r'''
F=$(ls -t /home/albus/strata166/data/w801_gain_*.txt | head -1)
echo "file=$F"
grep -cE "^=== ARM" $F
grep -E "^=== ARM|^ +(46|237|529|1954) |^BUILD|args_gain|envsnap" $F | tail -40
''', t=90))
