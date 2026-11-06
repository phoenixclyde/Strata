#!/usr/bin/env python3
"""One round's closing gate: report + artifacts + push status.

W1002 (machine-owner's three questions): "did you actually port it / where are
the four reports / where is your CI-CD".  The failure mode was never a missing
tool -- report_lint.py, gate.py and the workflows all existed -- it was that
nothing *called* them at the end of a round.  This script is the caller.

  python3 ci/round_gate.py --ci                 # GitHub runner: no GPU, no git needed
  python3 ci/round_gate.py --report <md>       # four-section report lint
  python3 ci/round_gate.py --status            # 166: pushed? tree clean? artifacts? port status?
"""
import argparse
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
PY = sys.executable

# A minimal but complete four-section report: the lint must accept it.
GOOD = """## 一、生产容器（8 字段）
| 1 | 容器 / 镜像 | 4f387a12e84b / strata-gfx906:0.2.10-101 image 5267df6dbdeb |
| 2 | 运行中引擎 | eea5ea3749ad54b124330386605a18bc, 44,908,992 B, strata 0.1.56 |
| 3 | config | md5 eea5ea3749ad54b124330386605a18bc exe=/data/bin/strata-0.1.56-090 args 37 env 9 |
| 4 | 健康 | /health ok, restarts=0, StartedAt 2026-11-05T11:58:52Z |
| 5 | 资源隔离 | ulimit -l unlimited, VmLck: 0 kB |
| 6 | 显存布局 | expert cache 7463 slots / 21.79 GiB, borrows 2606 (7.62 GiB), 882 MiB of VRAM free |
| 7 | 回滚件 | strata-0.1.56-080; cp /data/x.json.bak /data/x.json |
| 8 | 本轮改动 | 零；disk = build = running 三方一致 |
| 9 | ROCm 版本 | 打包 .info/version 10.1.0；HIP 7.16.26323-0000000 |
| 10 | llama.cpp 版本 | b11062 = 3cf03257f219afbe7334045ff7c6a06ac68c627d |
## 二、主线
branch @ 304bd3be · mi50-0.2.10-r32 · 落后 0 / 领先 16 · 上游 ffa80d73 · 工作树脏 0 行
## 三、本次落生产
改动 0；重启 0 次；停机 0；回滚件同上
## 四、进度 + 队列
196 条 / 已结 120 / 61.2%；主线 168 / 120；死块池 0/28
队列：R97 → R96 → R86 → R91 → R95 → R94 → R89 → R46
"""
BAD = "conclusion only, no four sections"


def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def lint_text(payload, expect_pass):
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write(payload)
        p = f.name
    r = run([PY, str(HERE / "report_lint.py"), p])
    ok = (r.returncode == 0) if expect_pass else (r.returncode != 0)
    pathlib.Path(p).unlink(missing_ok=True)
    return ok, (r.stdout + r.stderr).strip().splitlines()[-1] if r.stdout or r.stderr else ""


def ci():
    fails = []
    v = run([PY, str(HERE / "repack_ab" / "verify.py")])
    if v.returncode != 0:
        fails.append("verify.py: " + (v.stdout + v.stderr).strip().replace("\n", " | "))
    else:
        print("  " + v.stdout.strip())
    ph = run([PY, str(HERE / "prefill_phases" / "phases.py"), "--check",
              str(HERE / "prefill_phases" / "PREFILL_PHASES.tsv")])
    if ph.returncode != 0:
        fails.append("phases.py: " + (ph.stdout + ph.stderr).strip().replace("\n", " | "))
    else:
        print("  " + ph.stdout.strip().splitlines()[-1])
    # W1013: the bundle budget (the 5% gate, applied to a sum instead of to single items) and the
    # cfg_apply verdict arithmetic (it crashed once after installing a candidate; see the test's docstring).
    bu = run([PY, str(HERE / "bundle_budget" / "bundle.py")])
    if bu.returncode != 0:
        fails.append("bundle.py: " + (bu.stdout + bu.stderr).strip().replace("\n", " | "))
    else:
        print("  " + bu.stdout.strip().splitlines()[-1])
    tv = run([PY, str(HERE / "test_cfg_verdict.py")])
    if tv.returncode != 0:
        fails.append("test_cfg_verdict.py: " + (tv.stdout + tv.stderr).strip().replace("\n", " | "))
    else:
        print("  " + tv.stdout.strip().splitlines()[-1])
    # W1022: release_check's fifth pointer (llama.cpp pin) -- the negative cases prove it can fail.
    # Skips itself when there is no docker daemon (GitHub runners), loudly.
    sp = run([PY, str(HERE / "selftest_pin.py")])
    if sp.returncode != 0:
        fails.append("selftest_pin.py: " + (sp.stdout + sp.stderr).strip().replace("\n", " | "))
    else:
        print("  " + sp.stdout.strip().splitlines()[-1])
    for payload, expect, label in ((GOOD, True, "positive"), (BAD, False, "negative")):
        ok, last = lint_text(payload, expect)
        if not ok:
            fails.append("report_lint %s self-test did not behave as expected (%s)" % (label, last))
        else:
            print("  report_lint %-8s self-test ok" % label)
    return fails


def status():
    fails = ci()
    # A gate that exists but is never called is the exact bug this file fixes.
    # Only checked on the 166 host: GitHub runners do not have our hooks installed.
    for hook_name in ("pre-commit", "pre-push"):
        hook = ROOT / ".git" / "hooks" / hook_name
        if not hook.is_file():
            fails.append("%s hook is not installed (run ci/install-hooks.sh)" % hook_name)
        elif "round_gate" not in hook.read_text(encoding="utf-8", errors="replace"):
            fails.append("%s hook is installed but does not call round_gate" % hook_name)
    checks = [
        (["git", "status", "--porcelain"], "working tree is dirty"),
        (["git", "rev-list", "--left-right", "--count", "@{u}...HEAD"], None),
    ]
    tree = run(checks[0][0], cwd=ROOT)
    if tree.stdout.strip():
        fails.append("working tree has %d uncommitted path(s)" % len(tree.stdout.strip().splitlines()))
    lr = run(checks[1][0], cwd=ROOT)
    parts = lr.stdout.split()
    if len(parts) == 2 and parts[1] != "0":
        fails.append("%s commit(s) ahead of origin -- CI has never seen them" % parts[1])
    if len(parts) == 2 and parts[0] != "0":
        fails.append("%s commit(s) behind origin" % parts[0])
    remote = run(["git", "ls-remote", "origin", "HEAD"], cwd=ROOT)
    head = run(["git", "rev-parse", "HEAD"], cwd=ROOT)
    if remote.returncode == 0 and remote.stdout.strip() and head.stdout.strip():
        same = remote.stdout.split()[0] == head.stdout.strip()
        print("  remote HEAD == local HEAD: %s" % same)
        if not same:
            fails.append("origin tip differs from local HEAD (not pushed / different default branch)")
    ps = HERE / "repack_ab" / "PORT_STATUS.md"
    if ps.is_file():
        line = [l for l in ps.read_text(encoding="utf-8").splitlines()
                if "PRODUCTION_PORT" in l]
        print("  " + (line[0].strip() if line else "PORT_STATUS: no PRODUCTION_PORT line"))
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--report")
    a = ap.parse_args()
    if a.report:
        r = run([PY, str(HERE / "report_lint.py"), a.report])
        print(r.stdout.strip() or r.stderr.strip())
        return r.returncode
    fails = status() if a.status else ci()
    if fails:
        print("ROUND_GATE: FAIL (%d)" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("ROUND_GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
