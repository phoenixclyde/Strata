import io
import re

P="deploy/PROGRESS.tsv"
PLAN="deploy/W832_OPT_PLAN_V2.md"
MEM=".workbuddy/memory/2026-11-07.md"
HAND="albus/w1034/HANDOFF.md"
RECIPE="deploy/REBUILD_RECIPE.tsv"

lines=io.open(P,encoding="utf-8").read().splitlines()
n=0
for i,l in enumerate(lines):
    f=l.split("\t")
    if len(f)>=11 and f[1]=="P533":
        f[6]="1"; f[7]="DONE"
        f[8]+=" **W1047 已装机**：D1–D6 全 PASS 后冷启动；config `9e2df560fdb88f684a3f2fb7b15d9ad5`，容器内 env 实证 `STRATA_HC_DOWN_DP4A=1`、`STRATA_HC_DOWN_DP4A_MAX_T=6`，disk=build=running，health ok。**重启 7 次 / 停机 1810 s / 装机 1 / 回滚 0**（三个 clean/数值/n3 窗口 + 两次 harness 误失败恢复 + 最终换件）。"
        lines[i]="\t".join(f); n+=1
assert n==1
io.open(P,"w",encoding="utf-8",newline="\n").write("\n".join(lines)+"\n")

tot=done=0
for l in lines:
    f=l.split("\t")
    if len(f)>=10 and f[0]!="block" and not l.startswith("#"):
        try: tot+=int(f[5]); done+=int(f[6])
        except ValueError: pass
pct=100.0*done/tot
print("TOTALS",tot,done,round(pct,1))

s=io.open(PLAN,encoding="utf-8").read()
s=re.sub(r"\| 进度分母 \| \*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1047；",
         "| 进度分母 | **%d 条 / 已结 %d / %.1f%%**（W1047；"%(tot,done,pct),s,count=1)
s=s.replace("| **唯一队列** | **P533（W1047：B3 `hc4b` D1–D5 已过，待 D6 后装机）** →",
            "| **唯一队列** | ~~**P533/W1047 B3 `hc4b` 已装机（D1–D6 全过，冷启动验证）**~~ →",1)
title="### 回写 · W1047 装机补记（2026-11-07 22:3x）hc4b 落生产"
block=title+"""

- **D1–D6 全 PASS 后换件**：`strata-0.1.57-attn` → `strata-0.1.57-hc4b`，config `3dde8801…` → `9e2df560…`（仅 exe + `STRATA_HC_DOWN_DP4A=1` + `STRATA_HC_DOWN_DP4A_MAX_T=6`）。冷启动 41 s 后 health ok；容器内 `/proc/<engine>/environ` 实证两个 env；disk=build=running。
- **本轮停机口径**：**重启 7 次 / 停机 1810 s / 装机 1 / 回滚 0**。两次早期 needle 失败是 harness（health 匹配、忘发布端口），不是模型；已修复后复测。
- **回滚**：`tmp/w1047/cfg_preinstall_w1047.bak`（=`3dde8801…`）+ `strata-0.1.57-attn`；失败路径会恢复 config **并重启容器**。
"""
assert title not in s
s=s.rstrip("\n")+"\n\n"+block+"\n"
io.open(PLAN,"w",encoding="utf-8",newline="\n").write(s)

h=io.open(HAND,encoding="utf-8").read()
h=re.sub(r"> SNAPSHOT:.*","> SNAPSHOT: round=W1047 date=2026-11-07 prod_exe=strata-0.1.57-hc4b prod_md5=0533074826258d5f96c4b65bc0ad33df config_md5=9e2df560fdb88f684a3f2fb7b15d9ad5",h,count=1)
io.open(HAND,"w",encoding="utf-8",newline="\n").write(h)

r=io.open(RECIPE,encoding="utf-8-sig").read().splitlines()
if not any(l.startswith("strata-0.1.57-hc4b\t") for l in r):
    r.append("\t".join([
        "strata-0.1.57-hc4b","0533074826258d5f96c4b65bc0ad33df","43679864",
        "gfx906/hc-dp4a @ 03509d1b","b12180 / bcb0152876e8f0b684ba70d3defcab6cdf35adb5",
        "4c1004c49221b07c3b8108977e3d1991fc9f45cc",
        "build-masterp（/src=pr/k10, /llama.cpp=tmp/w1037/llama-master）",
        "W1047/R109 B3 装机：HC down DP4A + MAX_T=6；D1-D6 全 PASS，见 P527/P528/P533"
    ]))
io.open(RECIPE,"w",encoding="utf-8",newline="\n").write("\n".join(r)+"\n")

m=io.open(MEM,encoding="utf-8").read().rstrip("\n")
add="""
- **装机完成**：`hc4b` / config `9e2df560…`，env 12；D1–D6 全 PASS；冷启动 41 s；重启 7 / 停机 1810 s / 装机 1 / 回滚 0。SNAPSHOT 已更新。
"""
io.open(MEM,"w",encoding="utf-8",newline="\n").write(m+add+"\n")
print("postinstall landed")
