"""Remote shell helper for 166. Always: base64 -> `base64 -d | bash` on the far side
(immune to the local shim eating leading chars / CRLF)."""
import base64
import subprocess
import sys

HOST = 'albus@192.168.50.166'
PROLOG = 'export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; '


def run(script, timeout=600, quiet=False):
    b64 = base64.b64encode((PROLOG + script).encode('utf-8')).decode('ascii')
    p = subprocess.run(
        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', HOST,
         'base64 -d | bash'],
        input=b64.encode('ascii'), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=timeout)
    out = p.stdout.decode('utf-8', 'replace')
    err = p.stderr.decode('utf-8', 'replace')
    if not quiet or p.returncode != 0:
        pass
    return p.returncode, out, err


if __name__ == '__main__':
    rc, out, err = run(sys.stdin.read())
    sys.stdout.write(out)
    sys.stderr.write(err)
    sys.exit(rc)
