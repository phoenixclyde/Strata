import sys,json,os
sys.path.insert(0,'D:/workbuddy_space/strata_ws/albus/gfx906_survey')
from _gh import gh
nums=[int(x) for x in sys.argv[1:]]
os.makedirs('pr',exist_ok=True)
for n in nums:
    f=gh('/repos/ggml-org/llama.cpp/pulls/%d/files'%n,per_page=40)
    with open('pr/%d.txt'%n,'w',encoding='utf8') as fh:
        for x in f:
            fh.write('### %s  +%d -%d\n'%(x['filename'],x['additions'],x['deletions']))
            fh.write(x.get('patch','(no patch)')+'\n\n')
    print('saved',n,sum(1 for _ in f))
