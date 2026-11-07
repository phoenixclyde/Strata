import io

p = "ci/cfg_apply.py"
s = io.open(p, encoding="utf-8").read()

# 1) new flag
if "--restart-baseline" not in s:
    s = s.replace(
        '    ap.add_argument("--record-only", action="store_true", help="measure the live config, change nothing")',
        '    ap.add_argument("--record-only", action="store_true", help="measure the live config, change nothing")\n'
        '    ap.add_argument("--restart-baseline", action="store_true",\n'
        '                    help="with --record-only: restart first, so the baseline sits in the same state as an applied arm")',
        1)

# 2) restart before measuring in the record-only path
old = '''        print("== record-only: measuring the live config, nothing is written to it")'''
new = '''        print("== record-only: measuring the live config, nothing is written to it")
        if a.restart_baseline:
            up, dt = restart()
            print("   restarted before measuring: %s in %.0fs" % ("ok" if up else "FAILED", dt))
            if not up:
                return 2'''
assert old in s
s = s.replace(old, new, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("patched --restart-baseline")
