echo "--- strata_hip.h md5 ---"
md5sum /home/albus/strata166/src0271/include/strata/platform/hip_compat/strata_hip.h /home/albus/strata166/src028/include/strata/platform/hip_compat/strata_hip.h
echo "--- dflash2.cpp md5 ---"
md5sum /home/albus/strata166/src0271/src/core/dflash2.cpp /home/albus/strata166/src028/src/core/dflash2.cpp
echo "--- 0.1.53 compile cmd for dflash2.cpp ---"
python3 - <<'PY'
import json
for tag in ('build-0271','build-028'):
    p='/home/albus/strata166/src0271/%s/compile_commands.json'%tag if tag=='build-0271' else '/home/albus/strata166/src028/%s/compile_commands.json'%tag
    try:
        cc=json.load(open(p))
    except Exception as e:
        print(tag,'no compile_commands',e); continue
    for e in cc:
        if e['file'].endswith('src/core/dflash2.cpp'):
            cmd=e.get('command') or ' '.join(e.get('arguments',[]))
            print(tag, '->', cmd[:700])
            print()
PY
echo "--- does hip_compat have the two names anywhere? ---"
grep -rn 'StreamPriorityRange\|CreateWithPriority' /home/albus/strata166/src028/include/ | head
