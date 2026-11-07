"""Run a local .sh file on 166: python rsh_run.py <local.sh> [timeout_s]"""
import sys

sys.path.insert(0, 'D:/workbuddy_space/strata_ws/albus/w828')
import rsh  # noqa: E402

path = sys.argv[1]
to = int(sys.argv[2]) if len(sys.argv) > 2 else 600
script = open(path, encoding='utf-8').read()
rc, out, err = rsh.run(script, timeout=to)
sys.stdout.write(out)
if err.strip():
    sys.stderr.write('\n--- STDERR ---\n' + err)
print('\n[rc=%d]' % rc)
