set +e
D=/home/albus/strata166/gfx029
echo "===== [1] 运行配置的真实 pack（与文件名对照） ====="
python3 -c "
import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
a=d['args']
print('cfg file   : strata-huihui-ud-iq4_xs.json')
print('exe        :', d['exe'])
print('pack arg   :', a[a.index('--pack')+1] if '--pack' in a else '?')
print('native     :', (a[a.index('--native')+1].split('/')[-1] if '--native' in a else '?'))
print('vram-rsv   :', a[a.index('--vram-reserve-mib')+1] if '--vram-reserve-mib' in a else '?')
print('args n=',len(a),' env n=',len(d.get('env') or {}))
"
echo
echo "===== [2] 旧 0.2.8 分支与上游现在有没有共同祖先（unshallow 后） ====="
cd "$D"
echo -n "merge-base(0.2.8分支, upstream/main) = "; git merge-base gfx906/0.2.8-mi50 upstream/main 2>/dev/null | cut -c1-10 || echo "(空)"
echo -n "0.2.8 分支提交数 = "; git rev-list --count gfx906/0.2.8-mi50
echo
echo "===== [3] rebase 助手是否就位 ====="
ls -l /home/albus/strata166/tmp/rebase_gfx906.sh 2>/dev/null | sed 's/^/  /'
echo "===== [4] 新分支相对上游的净差异 ====="
git diff --stat upstream/main..HEAD | tail -14
echo "===== [5] 分支顶端三次确认 ====="
echo "  branch = $(git rev-parse --abbrev-ref HEAD)  HEAD = $(git rev-parse --short HEAD)"
echo "  ahead of upstream/main = $(git rev-list --count upstream/main..HEAD)  commit(s)"
echo "  working tree = $(git status --porcelain | wc -l) dirty file(s)"
echo "  remote = $(git rev-parse --short origin/gfx906/0.2.9-mi50 2>/dev/null)"
