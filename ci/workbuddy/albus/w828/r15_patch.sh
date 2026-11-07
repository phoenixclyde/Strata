cd /home/albus/strata166
python3 - <<'PY'
p='/home/albus/strata166/src028/include/strata/platform/hip_compat/strata_hip.h'
s=open(p,encoding='utf-8').read()
anchor='#define cudaStreamCreateWithFlags hipStreamCreateWithFlags\n'
assert s.count(anchor)==1, s.count(anchor)
if 'cudaStreamCreateWithPriority' in s:
    print('already patched')
else:
    add = (anchor +
           '// W828 (gfx906 compat layer, upstream 0.1.54 ships these two calls in src/core/dflash2.cpp):\n'
           '// the wave32 HIP backend gets them from hipify, the compat header has to name them.\n'
           '#define cudaStreamCreateWithPriority hipStreamCreateWithPriority\n'
           '#define cudaDeviceGetStreamPriorityRange hipDeviceGetStreamPriorityRange\n')
    open(p,'w',encoding='utf-8').write(s.replace(anchor, add))
    print('patched', p)
PY
grep -n -A1 'W828 (gfx906' /home/albus/strata166/src028/include/strata/platform/hip_compat/strata_hip.h
