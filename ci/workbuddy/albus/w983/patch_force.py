import io

p = "ci/cfg_apply.py"
s = io.open(p, encoding="utf-8").read()

if "--force-keep" not in s:
    s = s.replace('    ap.add_argument("--apply", action="store_true")',
                  '    ap.add_argument("--apply", action="store_true")\n'
                  '    ap.add_argument("--force-keep", action="store_true",\n'
                  '                    help="restoring a known-good value: keep it whatever the metrics say")', 1)
    s = s.replace('    verdict, why = "REVERT", "inconclusive: no change beyond 2x CV, so the live value stays"',
                  '    verdict, why = "REVERT", "inconclusive: no change beyond 2x CV, so the live value stays"\n'
                  '    if a.force_keep:\n'
                  '        verdict, why = "KEEP", "forced (restoring a known-good value)"', 1)

io.open(p, "w", encoding="utf-8").write(s)
print("patched --force-keep")
