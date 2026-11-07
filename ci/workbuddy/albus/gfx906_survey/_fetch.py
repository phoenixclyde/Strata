import os,sys,urllib.request
TOK=open(r'D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
def raw(repo,sha,path,dest):
    u='https://raw.githubusercontent.com/%s/%s/%s'%(repo,sha,path)
    r=urllib.request.Request(u,headers={'Authorization':'Bearer '+TOK,'User-Agent':'albus'})
    try:
        b=urllib.request.urlopen(r,timeout=60).read()
    except Exception as e:
        print('FAIL',path,e); return False
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    open(dest,'wb').write(b); print('ok',path,len(b)); return True
