import os,sys,urllib.request
def get(repo,ref,path,dest):
    u='https://gh-proxy.com/https://raw.githubusercontent.com/%s/%s/%s'%(repo,ref,path)
    try:
        b=urllib.request.urlopen(u,timeout=90).read()
    except Exception as e:
        print('FAIL',path,e); return False
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    open(dest,'wb').write(b); print('ok %-70s %d'%(path,len(b))); return True
