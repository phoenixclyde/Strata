"""GitHub API 小工具：带重试，供本机直连（不走 166）。

用法: gh.py <path> [--raw]
"""
import json
import sys
import time
import urllib.error
import urllib.request

TOK = open("deploy/tmp/_tok.txt", encoding="utf-8").read().strip()


def api(path, tries=5, timeout=60):
    last = None
    for i in range(tries):
        req = urllib.request.Request(
            "https://api.github.com" + path,
            headers={
                "Authorization": "Bearer " + TOK,
                "Accept": "application/vnd.github+json",
                "User-Agent": "albus",
            },
        )
        try:
            raw = urllib.request.urlopen(req, timeout=timeout).read()
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode("utf-8", "replace")
            last = "HTTP %s %s" % (e.code, body)
            if e.code in (403, 429):
                time.sleep(5 * (i + 1))
                continue
            raise SystemExit(last)
        except Exception as e:  # timeout / conn reset
            last = "%s: %s" % (type(e).__name__, e)
            time.sleep(3 * (i + 1))
    raise SystemExit("FAILED after %d tries: %s" % (tries, last))


if __name__ == "__main__":
    d = api(sys.argv[1])
    print(json.dumps(d, ensure_ascii=False))
