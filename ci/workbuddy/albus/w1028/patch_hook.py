import io
p = "/home/albus/strata166/pr/strata-fork/ci/hooks/pre-push"
s = io.open(p, encoding="utf-8").read()
old = 'case "$url" in\n  *phoenixclyde/Strata*|*phoenixclyde/strata*) ;;\n'
new = ('case "$url" in\n'
       '  *phoenixclyde/Strata*|*phoenixclyde/strata*) ;;\n'
       '  # W1028: the local gate repo is the enforcement point -- its pre-receive hook runs\n'
       '  # ci/round_gate.py on the tree that actually arrives.  It is a path on this box, not a\n'
       '  # forge, so nothing leaves the machine; allowing it does not widen the fork-only policy.\n'
       '  */gate/strata-gate.git|*/gate/strata-gate.git/) ;;\n')
assert old in s, "anchor"
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("patched ci/hooks/pre-push")
