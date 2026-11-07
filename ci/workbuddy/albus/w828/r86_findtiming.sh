echo "--- config keys ---"
python3 -c "
import json;c=json.load(open('/home/albus/strata166/data/w828_ta.json'))
print(sorted(c.keys()))
print('log =', c.get('log'))
"
echo "--- decode timing in the engine log ---"
grep -a "strata decode timing" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -4 | cut -c1-230
echo "--- count ---"
grep -ac "strata decode timing" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "--- spec depth / suffix lines ---"
grep -a "spec depth\|suffix drafts" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -3 | cut -c1-200
echo "--- trace dir ---"
ls -la /home/albus/strata166/data/w828_trace/ | head
