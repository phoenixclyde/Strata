import json, os, urllib.request

TOK = open('D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
OUT = 'D:/workbuddy_space/strata_ws/albus/w828'


def main():
    # main HEAD
    req = urllib.request.Request('https://api.github.com/repos/Niko1221/Strata/commits/main',
                                 headers={'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus'})
    with urllib.request.urlopen(req, timeout=60) as r:
        c = json.loads(r.read())
    print('main HEAD', c['sha'], c['commit']['author']['date'], c['commit']['message'].split('\n')[0])

    for tag in ('v0.2.8',):
        url = 'https://codeload.github.com/Niko1221/Strata/tar.gz/refs/tags/' + tag
        dst = OUT + '/strata-' + tag + '.tar.gz'
        if os.path.exists(dst) and os.path.getsize(dst) > 1000000:
            print('cached', dst, os.path.getsize(dst))
            continue
        req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus'})
        with urllib.request.urlopen(req, timeout=300) as r, open(dst, 'wb') as f:
            n = 0
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
                n += len(b)
        print('downloaded', dst, n)


main()
