import json, os, time, urllib.request

TOK = open('D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
OUT = 'D:/workbuddy_space/strata_ws/albus/w828/'
H = {'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus', 'Accept': 'application/vnd.github+json'}


def get(url, hdr=None, timeout=90):
    req = urllib.request.Request(url, headers=hdr or H)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), dict(r.headers)


def main():
    # 1) compare v0.2.7.1 ... v0.2.8
    body, _ = get('https://api.github.com/repos/Niko1221/Strata/compare/v0.2.7.1...v0.2.8')
    c = json.loads(body)
    print('compare status=%s ahead=%s files=%d total_commits=%d truncated=%s' % (
        c.get('status'), c.get('ahead_by'), len(c.get('files', [])), c.get('total_commits'), c.get('files') is None))
    files = c.get('files', [])
    with open(OUT + 'compare_0271_028.json', 'w', encoding='utf-8') as f:
        json.dump(files, f, ensure_ascii=False, indent=1)
    st = {}
    for x in files:
        st[x['status']] = st.get(x['status'], 0) + 1
    print('status counts', st)
    print('sum additions/deletions', sum(x['additions'] for x in files), sum(x['deletions'] for x in files))
    # engine-side
    eng = [x['filename'] for x in files if x['filename'].startswith(('src/', 'include/')) or x['filename'] == 'CMakeLists.txt']
    print('engine files', len(eng))

    # 2) raw speed test
    t0 = time.time()
    b, hd = get('https://raw.githubusercontent.com/Niko1221/Strata/v0.2.8/include/strata/kernels/window_limits.hpp',
                hdr={'User-Agent': 'albus'})
    dt = time.time() - t0
    open(OUT + 'window_limits_028.hpp', 'wb').write(b)
    print('raw %.0f B in %.2fs -> %.1f KB/s' % (len(b), dt, len(b) / 1024 / max(dt, 1e-6)))


main()
