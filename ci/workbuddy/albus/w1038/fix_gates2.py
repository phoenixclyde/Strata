import io

# 1) ledger KW: needs >= 3 characters
p = "deploy/PROGRESS.tsv"
s = io.open(p, encoding="utf-8").read()
if "\tKW:3.8|口径" in s:
    s = s.replace("\tKW:3.8|口径", "\tKW:3.8|独立口径", 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("P443 kw -> KW:3.8|独立口径")

# 2) report: 3a / 3b rows inside the section-一 table
r = "albus/w1038/reply.md"
t = io.open(r, encoding="utf-8").read()

row3a = ("| 3a args 明细 | 37 项；本轮只有 `--kv` 一项被改过并已逐字节还原（`k8v4` → `int8` → `k8v4`）："
         "`--pack` `--native` `--expert-profile` `--expert-cache` `--pcie-frac` `--spec` `--spec-min-p` `--mtp` "
         "`--max-context` `--kv` `--prefill` `--prompt-cache-every` `--expert-profile-save` `--conversation-cache-mib` "
         "`--vision` `--mtp-window` `--vram-reserve-mib` `--ple-io` `--pool-workers`（19 个 `--flag`） |")
row3b = ("| 3b env 明细 | 9 项，本轮未动：`HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` "
         "`STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` "
         "`STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` "
         "`STRATA_PREFILL_TIMING=1` |")

anchor = "| 8 | 本轮改动 |"
i = t.find(anchor)
assert i >= 0, "anchor row 8 not found"
j = t.find("\n", i)
ins = "\n" + row3a + "\n" + row3b
if "| 3a args 明细" not in t:
    t = t[:j] + ins + t[j:]
    print("3a/3b rows inserted into section 一")

io.open(r, "w", encoding="utf-8", newline="\n").write(t)
print("len", len(t))
