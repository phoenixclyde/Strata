"""每轮汇报生成器（三节：生产情况 / 落产情况 / 方案进度）

用法： python tools/round_report.py [--write]
  --write  写到 deploy/STATUS_<今天>.md；否则打到 stdout

口径（不要改，改就改这些文件本身）：
  生产情况 = 166 上现取的 state_q（--no-probe）+ docker inspect + md5 + 门禁
  落产情况 = 与 deploy/PROD_BASELINE.tsv 逐项比对（exe md5 / cfg md5 / image id / 启动时间）
  方案进度 = deploy/PROGRESS.tsv 的计数（tools/progress.py 同一套算法）
"""
import re
import subprocess
import sys
import datetime
import io
import os

ROOT = "D:/workbuddy_space/strata_ws"
RSH = ROOT + "/albus/w828/rsh_run.py"
PROBE = ROOT + "/albus/common/round_probe.sh"
BASE = ROOT + "/deploy/PROD_BASELINE.tsv"

REMOTE = r"""
set +e
python3 /home/albus/strata166/tmp/state_q.py 2>&1
echo "@@@"
docker inspect strata166-407 --format 'started={{.State.StartedAt}} restarts={{.RestartCount}} image={{.Config.Image}} imgid={{.Image}}'
CFGJ=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
EXEC=$(python3 -c "import json;print(json.load(open('$CFGJ'))['exe'])")
EXEH=$(printf '%s' "$EXEC" | sed 's#^/data/#/home/albus/strata166/data/#')
echo "exe=$EXEC"
md5sum "$EXEH" | awk '{print "binmd5="$1}'
md5sum "$CFGJ" | awk '{print "cfgmd5="$1}'
echo "@@@"
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -3
"""


def read_tsv(p):
    d = {}
    for ln in io.open(p, encoding="utf-8-sig").read().splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        k, _, v = ln.partition("\t")
        d[k.strip()] = v.strip()
    return d


def run_probe():
    os.makedirs(ROOT + "/albus/common", exist_ok=True)
    io.open(PROBE, "w", encoding="utf-8", newline="\n").write(REMOTE)
    p = subprocess.run([sys.executable, RSH, PROBE, "300"], capture_output=True, text=True)
    return p.stdout + ("\nERR:" + p.stderr if p.stderr.strip() else "")


def parse(txt):
    v = {}
    for pat, key in [
        (r"\[容器\]\s+(.+)", "up"),
        (r"\[镜像\]\s+(\S+)", "image"),
        (r"\[引擎\]\s+(\S+)\s+args:\s+(\d+)\s+env:\s+(\d+)", "exe"),
        (r"\[显存\]\s+([\d.]+ / +[\d.]+ GB).*?([\d.]+%)", "vram"),
        (r"\[专家缓存\]\s+(\d+) slots, ([\d.]+ GiB)", "cache"),
        (r"\[提示借用\]\s+(\d+) slots \(([\d.]+ GiB)\)", "borrow"),
        (r"\[自适应\]\s+(.+)", "adapt"),
        (r"\[预热\]\s+(\d+/\d+ slots in [\d.]+ s \([\d.]+ MB/s\))", "warm"),
        (r"\[探针\]\s+decode 128 tok: ([\d.]+) s → ([\d.]+) tok/s\s+TTFT\(新prompt\): (\d+) ms", "probe"),
        (r"\[健康\]|\[health\]\s+(.+)", "health"),
        (r"started=(\S+) restarts=(\d+) image=(\S+) imgid=(\S+)", "cont"),
        (r"^exe=(\S+)", "exepath"),
        (r"binmd5=(\w+)", "binmd5"),
        (r"cfgmd5=(\w+)", "cfgmd5"),
        (r"(GATE (?:PASS|FAIL))", "gate"),
    ]:
        m = re.search(pat, txt)
        if m:
            v[key] = m.groups() if len(m.groups()) > 1 else m.group(1)
    return v


def progress():
    p = subprocess.run([sys.executable, ROOT + "/tools/progress.py", "--md"], capture_output=True, text=True)
    a = subprocess.run([sys.executable, ROOT + "/tools/ledger_audit.py"], capture_output=True, text=True)
    first = (a.stdout.strip().splitlines() or ["（台账审计无输出）"])[0]
    return p.stdout.strip() + "\n\n台账对账：%s（exit=%d）" % (first, a.returncode)


def main():
    txt = run_probe()
    v = parse(txt)
    base = read_tsv(BASE) if os.path.exists(BASE) else {}
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    cont = v.get("cont") or ("", "", "", "")
    started, restarts, image, imgid = cont if isinstance(cont, tuple) else ("", "", "", "")
    binmd5, cfgmd5 = v.get("binmd5", "?"), v.get("cfgmd5", "?")
    exe = v.get("exe", ("?", "?", "?"))
    vram, cache, borrow = v.get("vram", ("?", "?")), v.get("cache", ("?", "?")), v.get("borrow", ("?", "?"))

    diffs = []
    for k, cur in (("exe_md5", binmd5), ("cfg_md5", cfgmd5), ("image_id", imgid), ("started", started)):
        old = base.get(k, "")
        if old and old != cur:
            diffs.append("%s: %s → %s" % (k, old[:16], cur[:16]))

    L = []
    L.append("# 本轮汇报 · %s" % today)
    L.append("")
    L.append("> 由 `tools/round_report.py` 生成；三节口径固定：生产=现取，落产=与 `deploy/PROD_BASELINE.tsv` 比对，进度=`deploy/PROGRESS.tsv`。")
    L.append("")
    L.append("## 1 生产情况（166 实取）")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append("| 容器 | %s |" % (v.get("up", "?")))
    L.append("| 镜像 | %s（id %s） |" % (image or v.get("image", "?"), (imgid or "?")[:14]))
    L.append("| 引擎 | %s · args %s · env %s |" % (v.get("exepath", exe[0] if isinstance(exe, tuple) else exe),
                                                exe[1] if isinstance(exe, tuple) else "?", exe[2] if isinstance(exe, tuple) else "?"))
    L.append("| 显存 | %s (%s) |" % (vram[0] if isinstance(vram, tuple) else "?", vram[1] if isinstance(vram, tuple) else ""))
    L.append("| 专家缓存 / 提示借用 | %s 槽 %s ／ %s 槽 %s |" % (
        cache[0] if isinstance(cache, tuple) else "?", cache[1] if isinstance(cache, tuple) else "",
        borrow[0] if isinstance(borrow, tuple) else "?", borrow[1] if isinstance(borrow, tuple) else ""))
    L.append("| 自适应 tier（累计均值，探针会扰动） | %s |" % v.get("adapt", "?"))
    L.append("| 预热 | %s |" % v.get("warm", "?"))
    L.append("| decode 单点 / TTFT | %s |" % (("%s tok/s / %s ms（128 tok 整请求，含 TTFT）" % (v["probe"][1], v["probe"][2])) if isinstance(v.get("probe"), tuple) else "?"))
    L.append("| /health | %s |" % (v.get("health", "?")))
    L.append("| 门禁 | %s |" % v.get("gate", "?"))
    L.append("")
    L.append("## 2 落产情况")
    L.append("")
    if not base:
        L.append("首次建立基线（`deploy/PROD_BASELINE.tsv`）。")
    elif not diffs:
        L.append("**本轮 0 落产**：exe md5 `%s`、cfg md5 `%s`、镜像 id `%s`、启动时间 `%s`、restarts=%s 全部未变。"
                 % (binmd5[:16], cfgmd5[:16], imgid[:14], started, restarts))
    else:
        L.append("**本轮有落产**，逐项差：")
        for d in diffs:
            L.append("- " + d)
    L.append("")
    L.append("## 3 方案进度")
    L.append("")
    for ln in progress().splitlines():
        if ln.startswith("  "):
            L.append("> " + ln.strip())
        else:
            L.append(ln)
    L.append("")
    out = "\n".join(L)
    if "--write" in sys.argv:
        p = ROOT + "/deploy/STATUS_%s.md" % datetime.datetime.now().strftime("%Y-%m-%d")
        io.open(p, "w", encoding="utf-8", newline="\n").write(out + "\n")
        print("written: " + p)
    else:
        print(out)


if __name__ == "__main__":
    main()
