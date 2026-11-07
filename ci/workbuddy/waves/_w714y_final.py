# 收尾：mtp 软链改指宿主真实路径 + 追加 PROVENANCE 链接布局一节 + 终态验证
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
H = "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF"

SECTION = """
## 五、链接布局（2026-10-09 按「充分利用软连接」整理）

原则：每份内容只保留一个实体，其余一律软链接。注意 /home/albus/strata166/weights 本身是指向
/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS 的目录软链，所以 /weights 与 /models/unsloth 是同一份。

| 路径 | 类型 | 说明 |
|---|---|---|
| /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/{00001,00002,00003} | 实体 | base 三片（现役容器 strata166-406 在用） |
| /models/unsloth/.../mmproj-Qwen3.8-Flash-Next-BF16.gguf | 软链 | 指向本目录 mmproj（该文件属 huihui 仓，实体归本目录） |
| 本目录/mmproj-Qwen3.8-Flash-Next-BF16.gguf | 实体 | huihui 仓 mmproj |
| 本目录/unsloth-UD-IQ4_XS/{00002,00003} | 实体 | huihui abliterated 主体权重 |
| 本目录/unsloth-UD-IQ4_XS/00001 | 软链 | 指向 /models/unsloth/.../00001（两仓逐字节相同，不重复占空间） |
| /home/albus/strata166/weights | 目录软链 | 指向 /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS |
| 本目录/mtp | 软链 | 指向 /home/albus/strata166/data/mtp（容器内对应路径为 /data/mtp） |

MTP 说明：huihui 仓不提供 MTP，本模型复用 base 派生的 MTP
（mtp-inventory.json 自述源 = modelscope.cn/models/Qwen/Qwen3.8-Flash-Next；运行时格式在 mtp/rt）。
提醒：主模型若切成 abliterated，其权重已被消融，而 draft 仍是 base 派生 => 推测解码接受率需重测。

本次整理释放重复占用约 918 MB（907 MB 的 mmproj + 10.9 MB 的分片1）；
删除前已用全量 sha256 确认两侧内容逐字节相同，删除后关键路径 sha256 抽验不变。
"""

b64 = base64.b64encode(SECTION.encode("utf-8")).decode("ascii")
SC = r'''set -u
H=@H@
echo "=== 1) mtp 软链改指宿主真实路径 ==="
ln -sfn /home/albus/strata166/data/mtp "$H/mtp"
readlink "$H/mtp"

echo "=== 2) 追加 PROVENANCE 链接布局一节 ==="
base64 -d >> "$H/PROVENANCE.md" <<'__S__'
@B64@
__S__
echo "PROVENANCE.md 现 $(wc -c < "$H/PROVENANCE.md") B"

echo "=== 3) 终态：inode / 类型 ==="
ls -li "$H" "$H/unsloth-UD-IQ4_XS"
echo "--- /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS ---"
ls -li /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS
echo "--- /weights（目录软链）---"
ls -ld /home/albus/strata166/weights

echo "=== 4) 软链解析全绿校验 ==="
for f in "$H/mtp" "$H/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf" \
         /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/mmproj-Qwen3.8-Flash-Next-BF16.gguf \
         /home/albus/strata166/weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf; do
  t=$(readlink -f "$f" 2>/dev/null || true)
  if [ -n "$t" ] && [ -e "$t" ]; then echo "OK      $f"; else echo "BROKEN  $f -> $t"; fi
done

echo "=== 5) 关键 sha256 抽验（应为 huihui 值 / 两仓同值）==="
sha256sum "$H/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf" \
          "$H/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf" \
          /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf \
          "$H/mmproj-Qwen3.8-Flash-Next-BF16.gguf"

echo "=== 6) 空间（字节级）==="
df -B1 / | tail -1
echo "--- 各目录占用 ---"
du -sh --apparent-size "$H" /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS 2>/dev/null

echo "=== 7) 现役容器未受影响 ==="
docker ps --format '{{.Names}} {{.Status}}' | grep strata || true
'''
SC = SC.replace("@H@", H).replace("@B64@", b64)
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=600)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w714_final.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-500:])
