# 治理第一步：建 huihui 目录 + 放入"已证实属于 huihui"的文件（mmproj 与分片1）+ 写溯源说明
import base64, hashlib, io, os, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
HUI = "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF"
BASE = "/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS"
F1 = "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
MM = "mmproj-Qwen3.8-Flash-Next-BF16.gguf"


def run(script, t=600):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(script.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


PROV = """# 溯源说明 ---- /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF

本目录按 /models 的 ModelScope 约定 `{owner}/{repo}/` 建；内容**只放已用 sha256 证实属于该仓的文件**。
核验方式：与 hf-mirror 给出的该仓 LFS oid（sha256）逐字节对撞。

| 文件 | size | sha256 | 判定 |
|---|---|---|---|
| mmproj-Qwen3.8-Flash-Next-BF16.gguf | 907543008 | b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0 | **与本仓同文件完全一致** |
| unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf | 10946624 | 5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4 | **与本仓同文件完全一致**（该片在本仓与 base 仓逐字节相同，是元数据/分词器部分） |

**未放入（重要）**：`unsloth-UD-IQ4_XS/` 的 00002、00003 两片。原因是：
- 本仓这两片的 sha256 = c67b468b3b83bc12... / 130560b6a447e0fe...（abliterated 重量化产物，**与 base 不同**）；
- 而我们手上（现役 = /models/unsloth/... = D 盘那份）这两片的全量 sha256 = 577a38a2392b40ca...
  / d4634e6d84f0ebb0...，**等于上游 setup.py 钉死的官方 base 值**。
=> 即：**我们目前手里没有本仓真正 abliterated 的那两片**；要拿本仓完整模型，需按以下 oid 核准下载：
  unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf  (49835229856, c67b468b3b83bc12...)
  unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf  (43836407744, 130560b6a447e0fe...)
（注意：本仓 abliterated 件与 base 件的 **size 完全相同**，只有内容不同 => 只比 size 分不出来，必须比 sha256。）

相关：本工作区记账见 .workbuddy/memory/2026-10-08.md 的 W714f/W714g 段；参数真值见 deploy/params/PARAM_REGISTER.tsv。
"""

print("=== 1) 166: 建 huihui 目录 + 放 mmproj 与分片1（复制，独立 inode）===")
sc = """set -u
mkdir -p '%(hui)s/unsloth-UD-IQ4_XS'
cp --remove-destination '%(base)s/%(mm)s' '%(hui)s/%(mm)s'
cp --remove-destination '%(base)s/%(f1)s' '%(hui)s/unsloth-UD-IQ4_XS/%(f1)s'
echo '--- 落位结果 ---'; ls -l '%(hui)s' '%(hui)s/unsloth-UD-IQ4_XS'
echo '--- sha256 复核（mmproj 应 b1a82259...；分片1 应 5ce89370...）---'
sha256sum '%(hui)s/%(mm)s' '%(hui)s/unsloth-UD-IQ4_XS/%(f1)s'
echo '--- 盘 ---'; df -h /home | tail -1
""" % {"hui": HUI, "base": BASE, "mm": MM, "f1": F1}
rc, out, err = run(sc, 600)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])

print("=== 2) 写入溯源说明 PROVENANCE.md ===")
b64 = base64.b64encode(PROV.encode("utf-8")).decode("ascii")
sc2 = "set -u\nbase64 -d > '%s/PROVENANCE.md' <<'__P__'\n%s\n__P__\nwc -c '%s/PROVENANCE.md'\n" % (HUI, b64, HUI)
rc, out, err = run(sc2, 300)
print(out)
if err.strip():
    print("ERR:", err.strip()[-200:])

print("=== 3) 164 上 /models 现有相关目录一览 ===")
rc, out, err = run("ls -l /models/ | head -20; echo ---; du -sh /models/huihui-ai /models/unsloth 2>/dev/null", 300)
print(out)
