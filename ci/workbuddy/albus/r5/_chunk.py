import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== chunk lines (last 12) ==="
grep -a -E "prefill: .*chunk|chunks of|chunk [0-9]+" "$L" | tail -12 | cut -c1-200
echo "=== gemm warm / rocblas / f16 mentions ==="
grep -a -i -E "rocBLAS|prompt_f16|FP16 in and out|hipBLASLt" "$L" | tail -8 | cut -c1-220
echo "=== prefill header ==="
grep -a -E "^strata prefill" "$L" | tail -6 | cut -c1-220
'''))
