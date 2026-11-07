import io

# 1) ledger KW token fix
p = "deploy/PROGRESS.tsv"
s = io.open(p, encoding="utf-8").read()
if "\tKW:3.8|实测" in s:
    s = s.replace("\tKW:3.8|实测", "\tKW:3.8|口径", 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("P443 kw -> KW:3.8|口径")
else:
    print("kw pattern not found (maybe already fixed)")

# 2) report fixes
r = "albus/w1038/reply.md"
t = io.open(r, encoding="utf-8").read()

a = "prompt 借 2606 槽（7.62 GiB）"
b = "the prompt path borrows 2606 槽（7.62 GiB）"
if a in t:
    t = t.replace(a, b, 1)
    print("F6 borrows fixed")

APPEND = """

---

## 附：本轮 config 明细（未变，逐项列出，便于与上一轮逐字对差）

`args`（37 项，`--kv` 为本次唯一改动项，已还原）：

`--pack /data/packs/ud-q4_k_xl`、`--native /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf`、
`--expert-profile /src/data/expert-profile.bin`、`--expert-cache auto`、`--pcie-frac 0.20`、`--spec 4`、`--spec-min-p 0.70`、`--mtp /data/mtp/rt`、
`--max-context 262144`、`--kv k8v4`、`--prefill auto:16384`、`--prompt-cache-every 8192`、`--expert-profile-save /data/profiles/q4kxl-learned.bin`、
`--conversation-cache-mib 4096`、`--vision`、`--mtp-window 8192`、`--vram-reserve-mib 832`、`--ple-io mmap`、`--pool-workers 10`
（以上为 `--flag` 形态的 19 个；其余 18 项为其取值与 `--serve` 等开关，合计 37。）

`env`（9 项）：

`HSA_OVERRIDE_GFX_VERSION=9.0.6`、`STRATA_PREFILL_CPU_SHARE=auto`、`STRATA_PREFILL_CPU_SHARE_MAX=3072`、
`STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt`、`STRATA_GFX906_TUNED=1`、`STRATA_CKPT_MOVE_PARK=1`、
`STRATA_DECODE_TIMING=1`、`STRATA_SPEC_DEPTH=1`、`STRATA_PREFILL_TIMING=1`
"""

if "## 附：本轮 config 明细" not in t:
    t = t.rstrip("\n") + APPEND
    print("appendix added")

io.open(r, "w", encoding="utf-8", newline="\n").write(t)
print("len", len(t))
