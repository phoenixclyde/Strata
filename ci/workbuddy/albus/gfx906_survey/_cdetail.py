import sys
sys.path.insert(0,'D:/workbuddy_space/strata_ws/albus/gfx906_survey')
from _gh import gh
for spec in sys.argv[1:]:
    repo,sha=spec.split('@')
    print('='*25,repo,sha)
    try:
        c=gh('/repos/%s/commits/%s'%(repo,sha))
    except Exception as e:
        print(' ERR',e); continue
    print('MSG:',c['commit']['message'][:300].replace('\n',' | '))
    for f in c.get('files',[]):
        print('  --',f['filename'],'+%d -%d'%(f['additions'],f['deletions']))
