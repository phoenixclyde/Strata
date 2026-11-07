# 链接治理：实体唯一化 + /weights 软链视图 + huihui 补 MTP 软链；删除前 fail-closed 校验
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

SC = r'''set -u
W=/home/albus/strata166/weights
U=/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS
H=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF
HU=$H/unsloth-UD-IQ4_XS
MM=mmproj-Qwen3.8-Flash-Next-BF16.gguf
SH1=Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf
SH2=Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf
SH3=Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf
MMOID=b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0
S1OID=5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4

echo "=== 0) 删除前一致性校验（fail-closed）==="
a=$(sha256sum "$U/$MM" | cut -d' ' -f1)
b=$(sha256sum "$H/$MM" | cut -d' ' -f1)
c=$(sha256sum "$U/$SH1" | cut -d' ' -f1)
d=$(sha256sum "$HU/$SH1" | cut -d' ' -f1)
echo "mmproj  U=$a"
echo "mmproj  H=$b"
echo "00001   U=$c"
echo "00001   HU=$d"
[ "$a" = "$b" ] || { echo "ABORT: mmproj 两侧不一致"; exit 1; }
[ "$c" = "$d" ] || { echo "ABORT: 00001 两侧不一致"; exit 1; }
[ "$a" = "$MMOID" ] || { echo "ABORT: mmproj 不是 huihui 那份"; exit 1; }
[ "$c" = "$S1OID" ] || { echo "ABORT: 00001 不是预期值"; exit 1; }
echo "校验通过，开始整理"

echo "=== 1) 软链化（ln -sfn 会先撤掉旧的名字，硬链接名撤掉后由引用计数决定实体是否释放）==="
ln -sfn "$U/$SH1" "$W/$SH1"
ln -sfn "$U/$SH2" "$W/$SH2"
ln -sfn "$U/$SH3" "$W/$SH3"
ln -sfn "$H/$MM"  "$W/$MM"
ln -sfn "$H/$MM"  "$U/$MM"
ln -sfn "$U/$SH1" "$HU/$SH1"
ln -sfn /data/mtp "$H/mtp"
echo done

echo "=== 3) 结果（inode / 类型 / 目标）==="
ls -li "$W"
echo "--- $U ---"; ls -li "$U"
echo "--- $H ---"; ls -li "$H"
echo "--- $HU ---"; ls -li "$HU"

echo "=== 4) 软链解析校验 ==="
for f in "$W/$SH1" "$W/$SH2" "$W/$SH3" "$W/$MM" "$HU/$SH1" "$H/mtp"; do
  t=$(readlink -f "$f" 2>/dev/null || true)
  if [ -n "$t" ] && [ -e "$t" ]; then echo "OK      $f  ->  $t"; else echo "BROKEN  $f  ->  $t"; fi
done

echo "=== 5) 可用性复核（关键路径仍可读 + sha256 抽验）==="
sha256sum "$H/$MM" "$U/$SH1" "$HU/$SH2" 2>/dev/null
echo "--- huihui 三片经软链/实体均可见 ---"
ls -l "$HU"
echo "=== 6) 空间 ==="
df -h / | tail -1
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=900)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w714_linktidy.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-500:])
