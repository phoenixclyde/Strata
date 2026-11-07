# -*- coding: utf-8 -*-
"""收尾：① 记关机前状态到日志 ② 优雅停 strata166 ③ sync ④ 发 poweroff"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

# ---------- ① 先落盘"关机前状态" ----------
p = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
TXT = """

## [W-Strata-18] 会话收尾（2026-10-06 02:3x~02:5x）：**166 关闭**

### 一、关机时 166 的现场（已取证）
- 容器 `strata166`（`strata-gfx906:0.1.39`）**只停这一个**（它是我们的，占 32GB VRAM）
- **5 个常驻容器（open-webui / portainer / comfyui-cu130 / netdata / searxng）刻意不停** ——
  按技能「重启 166 的完整规程」的更正：`docker stop` 会给它们打「用户手动停止」标记，
  而 `unless-stopped` 的语义正是「除非被手动停过」，该标记跨重启仍有效 ⇒ 下次开机会少 3 个。
  **不停它们 = 保留开机自恢复**（代价只是 systemd 关机多等约 30 s）。
- 关机命令用规程里已验证的写法：`sudo -n systemctl poweroff --no-block`
  （**禁** `/sbin/systemctl`（Ubuntu 22.04 上不存在）；**禁** `sleep`/`nohup &`；
  **回执「连接被远端关闭 / RC=255」是成功的正常长相，不得据此重发**）
- 166 **无远程唤醒**（无线网卡、无 BMC/IPMI）⇒ 下次要用**必须现场按电源键**

### 二、磁盘与代码的最终状态
| 项 | 位置 |
|---|---|
| 专用工作区（本机） | `D:\\strata166\\{scripts,logs,docker,configs,transfer,weights}` |
| 专用工作区（166） | `/home/albus/strata166/{docker,src,build,weights,data,logs,transfer,build-ctx}` |
| 权重 | 166 `/home/albus/strata166/weights/` 4 片 UD-Q4_K_XL，sha256 全过 |
| MTP draft | 166 `/home/albus/strata166/data/mtp/rt/`（experts.bin 707.8MB / dense.bin 116MB / dense.txt / draft_vocab.bin） |
| pack | 166 `/home/albus/strata166/data/packs/ud-q4_k_xl/` |
| 镜像 | 166 `strata-gfx906:0.1.39`（6.52 GB） |
| 构建上下文 | `D:\\strata166\\transfer\\`（strata-src zip + llama.cpp tar.gz，共 47.67 MB） |
| 补丁 | `D:\\strata166\\docker\\patch_hipcompat.py`（hip_compat 函数式宏 → 模板内联函数） |

### 三、本会话所有原始证据文件（本机）
`D:\\strata166\\logs\\` 下：
`_ab_mmq.txt`(MMQ/KQ256) · `_ab_pleio.txt`(PLE IO 三档) · `_ab_round4.txt`(含失败 arm) ·
`_ab_round5.txt`(5 arm 全绿) · `_final_bench.txt`(解码基准+初版盘刻画) ·
`_evidence_166.txt`(审计整改后重取的构建物证 + 盘 QD 重跑) · `_ready131k.txt` · `_166_probe*.txt` 等

### 四、本次审计（`routeb-audit` 规程）最终账
- 10 条发现：**5 条 P1**（含 2 条核心结论降级）· 3 条 P2 · 2 条已确认干净
- 两条核心降级：**「轮内顺序效应」→ 单轮现象（机制未明）**；**「PLE 随机读是瓶颈」→ 未证实候选假说（有直接反例）**
- 连带得到一条更重要的方法学结论：**本数据集里 <5% 的档间差异不可分辨**
- 全部裁决与更正已写入 `[W-Strata-17]`，技能 `flashnext-engine-selection` 的 §7.6/§7.8/§7.9 已同步修正，
  并新增 §7.10（干净解码基准）
"""
old = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(old.rstrip() + '\n' + TXT)
print('[1] memory logged, size', os.path.getsize(p), 'B')

# ---------- ② 关机前预检 ----------
PRE = r'''
echo "=== 关机前预检（只读）==="
echo "--- 我们的进程 ---"
docker exec strata166 bash -lc 'ps -eo pid,etimes,args | grep -E "serve/[s]erver.py|build-906/[s]trata" | head -4 || true'
echo "--- 全机容器 ---"
docker ps --format "{{.Names}}|{{.Status}}|{{.Image}}"
echo "--- 显存 ---"
rocm-smi --showmeminfo vram 2>/dev/null | grep -E "Total"
echo "--- uptime / boot ---"
uptime -s; cat /proc/sys/kernel/random/boot_id
'''
b = base64.b64encode(PRE.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=180)
pre_out = r.stdout.decode('utf-8', 'replace')
print('[2] 预检:\n' + pre_out)
with open(r'D:\strata166\logs\_shutdown_precheck.txt', 'w', encoding='utf-8') as f:
    f.write(pre_out)

# ---------- ③ 停我们的容器 + sync + 关机 ----------
GO = r'''
set +e
echo "=== 停我们的容器（只停 strata166；5 个常驻刻意不停）==="
docker stop -t 30 strata166; echo "stop_rc=$?"
sleep 2
echo "--- 停后：容器清单 ---"
docker ps --format "{{.Names}}|{{.Status}}"
echo "--- 停后：显存 ---"
rocm-smi --showmeminfo vram 2>/dev/null | grep -E "Total"
echo "=== sync ==="
sync; echo "sync_rc=$?"
echo "=== 发关机 ==="
sudo -n systemctl poweroff --no-block
echo "poweroff_sent_rc=$?"
'''
b = base64.b64encode(GO.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=600)
out = r.stdout.decode('utf-8', 'replace')
err = r.stderr.decode('utf-8', 'replace')
print('[3] 关机命令回执（RC=%s；RC!=0 且"连接被远端关闭"= 成功的正常长相）:' % r.returncode)
print(out)
if err.strip():
    print('  stderr:', err.strip()[:300])
with open(r'D:\strata166\logs\_shutdown_send.txt', 'w', encoding='utf-8') as f:
    f.write('returncode=%s\n--- stdout ---\n%s\n--- stderr ---\n%s' % (r.returncode, out, err))
print('saved -> _shutdown_send.txt')
