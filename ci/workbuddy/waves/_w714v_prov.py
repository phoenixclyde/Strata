# 更新 huihui 目录的 PROVENANCE.md：三片齐全（实测 sha256）+ 判据更正 + 与现役的关系
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
HUI = "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF"

PROV = """# 溯源说明 - /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF

本目录按 /models 的 ModelScope 约定 `{owner}/{repo}/` 建；内容只放已用 sha256 证实属于该仓的文件。
核验方式：与 hf-mirror 给出的该仓 LFS oid 逐字节对撞（HF 的 LFS oid 就是文件内容的 sha256）。

## 一、内容清单（166 端实测 sha256 vs 上游仓 LFS oid）

| 文件 | size | 实测 sha256 | 上游 LFS oid | 判定 |
|---|---|---|---|---|
| mmproj-Qwen3.8-Flash-Next-BF16.gguf | 907543008 | b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0 | 同 | 一致 |
| unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf | 10946624 | 5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4 | 同 | 一致 |
| unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf | 49835229856 | c67b468b3b83bc12a987e455ec4a0c2c3937250da1c234ae1638d9505180c161 | 同 | 一致 |
| unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf | 43836407744 | 130560b6a447e0febf61de9b03476f52143160bc4bcbacc9bfa07d9538718e2c | 同 | 一致 |

来源：机主下载目录 D:/Qwen3.8-Flash-Next-UD-IQ4_XS（本机 Windows）。
2026-10-09 经 ssh 真传（原始字节、8 进程并行、块 2GiB、dd 按偏移直写），传后逐片全量 sha256 自证通过（非硬链接、非 reflink）。

## 二、与官方 base 的关系（重要）

同名的 unsloth-UD-IQ4_XS 三片，在官方 base 仓 unsloth/Qwen3.8-Flash-Next-GGUF 的 UD-IQ4_XS/ 下也有一套：

| 片 | base(unsloth 官方) | 本目录(huihui abliterated) | size |
|---|---|---|---|
| 00001 | 5ce89370... | 5ce89370... | 相同（元数据/分词器，abliteration 未触及） |
| 00002 | 577a38a2... | c67b468b... | 相同，内容不同 |
| 00003 | d4634e6d... | 130560b6... | 相同，内容不同 |

两仓的 mmproj 也不是同一个文件：base 用 mmproj-BF16.gguf(2e788f8c, 907542944)，
本仓用 mmproj-Qwen3.8-Flash-Next-BF16.gguf(b1a82259, 907543008)。

## 三、判据更正（勿再犯）

abliterated 与 base 的 00002/00003 的 size 完全相同，且 head/mid/tail 三处各 16MB 抽样哈希也完全相同。
所以「比 size」和「抽样哈希对撞」都区分不了这两版，唯一可判据是**全量 sha256**。
（本工作区 W714g 曾据「D 盘与现役抽样全同」推出「D 盘也是 base」，该结论错误，已由 W714r 以全量 sha256 更正。）

## 四、与 166 现役的关系（截至 2026-10-09）

现役容器 strata166-406 的 config 仍指向 /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/...-00001-of-00003.gguf，
即**主体仍是官方 base**（577a38a2/d4634e6d，166 端全量实测），只有 mmproj 取自本目录。
若要切换现役到本目录，需要：
1) 用 /src/tools/iq_pack.py 从本目录 00001 重生成 pack（--pack 是 native 的 301 个投影矩阵，与 native 强耦合，不能沿用 base 的 pack）；
2) 改 config 的 --pack / --native / tokenizer 指向新 pack 与本目录；
3) 重跑 expert-profile（warmup 学习）；
4) 重测基准（换权重等于换模型，既有读数作废）；
5) 注意 --mtp /data/mtp/rt 是官方 Qwen base 派生，换 abliterated 主模型后**推测解码接受率待测**。

相关记账：本工作区 .workbuddy/memory/2026-10-08.md 的 W714g / W714r 段；参数真值 deploy/params/PARAM_REGISTER.tsv。
"""

b64 = base64.b64encode(PROV.encode("utf-8")).decode("ascii")
sc = ("set -u\n"
      "base64 -d > '%s/PROVENANCE.md' <<'__P__'\n%s\n__P__\n"
      "echo written=$(wc -c < '%s/PROVENANCE.md')\n"
      "echo '--- 目录终态 ---'\n"
      "ls -l '%s' '%s/unsloth-UD-IQ4_XS'\n"
      "echo '--- sha256 小件复核 ---'\n"
      "sha256sum '%s/mmproj-Qwen3.8-Flash-Next-BF16.gguf' '%s/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf'\n"
      % (HUI, b64, HUI, HUI, HUI, HUI, HUI))
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(sc.encode()) + b"\n",
                   capture_output=True, timeout=600)
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
