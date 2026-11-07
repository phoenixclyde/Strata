import subprocess, base64
def sh(s, t=180):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p4 -c '
for v in STRATA_GDN_HEAD STRATA_GDN_PP STRATA_GDN_CONVL2 STRATA_GDN_NOY STRATA_CVEC_FUSE STRATA_PF_PAD STRATA_PF_GEMM STRATA_ATTN_DAILY STRATA_ATTN_MERGE_V2 STRATA_SELECT_WMMA STRATA_QSA_WARP; do
  n=$(strings /src/build-906/strata 2>/dev/null | grep -c "^$v$")
  echo "$v : $n"
done
' 2>&1 | tail -14
'''))
