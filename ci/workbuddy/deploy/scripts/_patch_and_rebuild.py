# -*- coding: utf-8 -*-
"""写 gfx906 hip_compat 补丁 + 更新 Dockerfile，推到 166 重建。
补丁依据（源码对拍）：
  A) include/strata/platform/hip_compat/strata_hip.h 把 cudaFuncSetAttribute 定义成函数式宏，
     遇 `kernel<1, 6, true>` 这类实参会被预处理器按逗号拆成 5 个参数 -> 宏失效 -> 编译报错。
     全仓共 16 处这样的调用（fused_gr.cu 8 / qsa_prompt_attn.cu 2 / moe_fused.cu 2 / moe_fused_iq.cu 1 …）。
     同仓库 wave32 那套（include/strata/hip_compat/cuda_runtime.h）用的是
     `template <typename Kernel> inline hipError_t cudaFuncSetAttribute(...)`，没有这个问题 —— 照搬之。
  B) 该头还缺 `cudaFuncAttributePreferredSharedMemoryCarveout` 映射（wave32 那套有），补上。
"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
CTX = '/home/albus/strata166/build-ctx'
LOG = '/home/albus/strata166/logs/build-image.log'

PATCH = r'''# -*- coding: utf-8 -*-
"""gfx906 hip_compat 最小补丁：函数式宏 -> 模板内联函数；补一个缺失的属性映射。"""
import sys

P = '/src/include/strata/platform/hip_compat/strata_hip.h'
s = open(P, encoding='utf-8').read()

OLD = ('#define cudaFuncSetAttribute(fn, attr, val) '
       'hipFuncSetAttribute(reinterpret_cast<const void*>(fn), attr, val)')
NEW = """template <typename Kernel>
inline hipError_t cudaFuncSetAttribute(Kernel kernel, hipFuncAttribute attribute, int value) {
    return hipFuncSetAttribute(reinterpret_cast<const void*>(kernel), attribute, value);
}"""

if OLD in s:
    s = s.replace(OLD, NEW)
    print('patched: cudaFuncSetAttribute 宏 -> 模板内联函数')
elif 'template <typename Kernel>\ninline hipError_t cudaFuncSetAttribute' in s:
    print('already patched: cudaFuncSetAttribute')
else:
    sys.exit('ANCHOR NOT FOUND: cudaFuncSetAttribute 定义既不是预期宏也不是已打补丁的形态')

ANC = '#define cudaFuncAttributeMaxDynamicSharedMemorySize hipFuncAttributeMaxDynamicSharedMemorySize'
if 'cudaFuncAttributePreferredSharedMemoryCarveout' not in s:
    if ANC not in s:
        sys.exit('ANCHOR NOT FOUND: cudaFuncAttributeMaxDynamicSharedMemorySize')
    s = s.replace(ANC, ANC + '\n#define cudaFuncAttributePreferredSharedMemoryCarveout '
                             'hipFuncAttributePreferredSharedMemoryCarveout')
    print('patched: + cudaFuncAttributePreferredSharedMemoryCarveout')
else:
    print('already present: cudaFuncAttributePreferredSharedMemoryCarveout')

open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('hip_compat patch done ->', P)
'''

DF = open(r'D:\strata166\docker\Dockerfile', encoding='utf-8').read()
if 'patch_hipcompat.py' not in DF:
    anchor = '''    ls -d /src/third_party/llama.cpp/ggml/CMakeLists.txt /src/third_party/llama.cpp/gguf-py
'''
    assert anchor in DF, 'Dockerfile 锚点找不到'
    add = anchor + '''
# ---- gfx906 hip_compat 最小补丁（详见 patch_hipcompat.py 头部说明）----
#   gfx906 专用的 include/strata/platform/hip_compat/strata_hip.h 把 cudaFuncSetAttribute 写成函数式宏，
#   而全仓有 16 处调用把模板实参（`kernel<1, 6, true>`）传进去 —— 预处理器的逗号拆分会让宏失效。
COPY patch_hipcompat.py /tmp/
RUN set -eux; python3 /tmp/patch_hipcompat.py; \
    grep -n -A3 "cudaFuncSetAttribute" /src/include/strata/platform/hip_compat/strata_hip.h | head -12
'''
    DF = DF.replace(anchor, add)
    open(r'D:\strata166\docker\Dockerfile', 'w', encoding='utf-8', newline='\n').write(DF)
    print('Dockerfile 已加入补丁步骤，%d 字节' % len(DF.encode('utf-8')))
else:
    print('Dockerfile 已含补丁步骤')

IGNORE = "**\n!Dockerfile\n!patch_hipcompat.py\n!transfer/\n!transfer/**\n"

script = '''set +e
CTX=%s
echo '%s' | base64 -d > $CTX/Dockerfile
echo '%s' | base64 -d > $CTX/patch_hipcompat.py
printf '%s' > $CTX/.dockerignore
echo "=== dockerignore ==="; cat $CTX/.dockerignore
echo "=== Dockerfile 关键段 ==="; grep -n "patch_hipcompat\\|SMMQ_KQUANTS\\|STRATA_HIP_GFX906" $CTX/Dockerfile
echo "=== 本地先跑一遍补丁逻辑（对着解压后的源码？没有——只做语法检查）==="
python3 -c "import ast,sys; ast.parse(open('$CTX/patch_hipcompat.py').read()); print('patch 脚本语法 OK')"
echo
echo "=== 重建 ==="
cd /home/albus/strata166
setsid nohup docker build --progress=plain -t strata-gfx906:0.1.39 -f $CTX/Dockerfile $CTX \\
  > %s 2>&1 < /dev/null &
echo "launched pid=$!"
sleep 30
tail -12 %s
''' % (CTX,
       base64.b64encode(DF.encode('utf-8')).decode('ascii'),
       base64.b64encode(PATCH.encode('utf-8')).decode('ascii'),
       base64.b64encode(IGNORE.encode('utf-8')).decode('ascii'),
       LOG, LOG)

open(r'D:\strata166\docker\patch_hipcompat.py', 'w', encoding='utf-8', newline='\n').write(PATCH)

b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=900)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:600])
