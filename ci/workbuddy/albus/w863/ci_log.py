# -*- coding: utf-8 -*-
"""Download one GitHub Actions job log.

The /actions/jobs/{id}/logs endpoint answers 302 to Azure blob storage. Sending our
Authorization header along to that redirect makes Azure reject it (403), so the redirect
is followed by hand without credentials.
"""
import io
import sys
import urllib.request
import zipfile

TOK = open(r"D:\workbuddy_space\strata_ws\deploy\tmp\_tok.txt").read().strip()
REPO = "phoenixclyde/Strata"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(NoRedirect)
url = "https://api.github.com/repos/%s/actions/jobs/%s/logs" % (REPO, sys.argv[1])
req = urllib.request.Request(url, headers={"Authorization": "token " + TOK,
                                           "Accept": "application/vnd.github+json",
                                           "User-Agent": "albus-w863"})
try:
    resp = opener.open(req, timeout=60)
    blob = resp.read()
except urllib.error.HTTPError as e:
    if e.code not in (301, 302, 303, 307, 308):
        raise
    loc = e.headers["Location"]
    blob = urllib.request.urlopen(
        urllib.request.Request(loc, headers={"User-Agent": "albus-w863"}), timeout=120).read()

if blob[:2] == b"PK":
    zf = zipfile.ZipFile(io.BytesIO(blob))
    txt = "\n".join(zf.read(n).decode("utf-8", "replace") for n in zf.namelist())
else:
    txt = blob.decode("utf-8", "replace")

lines = txt.splitlines()
print("total log lines: %d" % len(lines))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 160
for l in lines[-n:]:
    print(l[:260])
