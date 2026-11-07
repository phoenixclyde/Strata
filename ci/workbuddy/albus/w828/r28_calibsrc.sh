cd /home/albus/strata166/src028
echo "--- head 60 ---"
sed -n '36,80p' tools/calibrate.py
echo "--- main / entry ---"
grep -n 'def main' tools/calibrate.py
grep -n 'if __name__' tools/calibrate.py
echo "--- subprocess/exe ---"
grep -n 'Popen' tools/calibrate.py | head -8
grep -n 'exe' tools/calibrate.py | head -20
echo "--- tail ---"
tail -40 tools/calibrate.py
