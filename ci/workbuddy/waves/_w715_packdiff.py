# 对比 huihui pack 与 base pack；读 strata_vision.cpp 参数；看编译进度；查现役 PLE
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

SC = r'''set -u
C=strata166-406
B=/home/albus/strata166/data/packs/ud-iq4_xs
H=/home/albus/strata166/data/packs/huihui-ud-iq4_xs
echo "===== 1) 两 pack 文件清单对比 ====="
for f in compat-bf16.json conversions.json dense.bin index.txt native_experts.txt; do
  bs=$(stat -c %s "$B/$f" 2>/dev/null || echo -)
  hs=$(stat -c %s "$H/$f" 2>/dev/null || echo -)
  if [ "$bs" = "$hs" ]; then tag="同 size"; else tag="SIZE-DIFF"; fi
  echo "$f  base=$bs  huihui=$hs  [$tag]"
done
echo "--- tokenizer ---"
ls "$B/tokenizer"; echo "vs"; ls "$H/tokenizer"
echo
echo "===== 2) sha256 对撞 ====="
for f in dense.bin index.txt native_experts.txt; do
  a=$(sha256sum "$B/$f" | cut -d' ' -f1)
  b=$(sha256sum "$H/$f" | cut -d' ' -f1)
  echo "--- $f"
  echo "    base  = $a"
  echo "    huihui= $b"
  if [ "$a" = "$b" ]; then echo "    => 逐字节相同"; else echo "    => 不同"; fi
done
echo
echo "===== 3) compat-bf16.json / conversions.json 行数差异 ====="
for f in compat-bf16.json conversions.json; do
  n=$(diff "$B/$f" "$H/$f" | wc -l)
  echo "$f: diff 行数 = $n"
done
echo
echo "===== 4) strata_vision.cpp 参数 ====="
docker exec $C sh -c 'grep -n -E "mmproj|--model|--gpu|--threads|max-tokens|min-tokens|Usage|argv" /src/tools/vision/strata_vision.cpp | head -40'
echo
echo "===== 5) vision 编译进度 ====="
tail -c 300 /home/albus/strata166/data/_vision_build.log 2>/dev/null
ls -l /home/albus/strata166/data/vision/ 2>/dev/null || echo "(产物未生成)"
echo
echo "===== 6) 现役日志里的 PLE 行 ====="
grep -i 'ple' /home/albus/strata166/data/strata-ud-iq4_xs.log 2>/dev/null | tail -8
echo "(命中 $(grep -ci 'ple' /home/albus/strata166/data/strata-ud-iq4_xs.log 2>/dev/null || echo 0) 行)"
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=900)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w715_packdiff.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
