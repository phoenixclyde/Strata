# -*- coding: utf-8 -*-
"""验证 166 已下线：多端口 TCP 全 TIMEOUT + ARP 无条目 + ping 文本解析（关闭前等待窗口 ~75s）"""
import socket, subprocess, time, os, json

TARGET = '192.168.50.166'
PORTS = [22, 3000, 4096, 8188, 9090, 19999, 8090]

time.sleep(75)          # socat/systemd 关机窗口；166 热重启历史 60~171 s

print('=== ① 多端口 TCP 探测（期望全部非 0）===')
alive = []
for p in PORTS:
    s = socket.socket(); s.settimeout(3)
    rc = s.connect_ex((TARGET, p))
    s.close()
    print('  %-6d -> %s' % (p, 'OPEN' if rc == 0 else 'DOWN(rc=%d)' % rc))
    if rc == 0:
        alive.append(p)

print('\n=== ② ARP 表里有没有该目标 ===')
arp = subprocess.run(['arp', '-a'], capture_output=True)
atxt = arp.stdout.decode('gbk', 'replace')
hit = [l.strip() for l in atxt.splitlines() if TARGET in l]
print('  arp 条目:', hit if hit else '（无 —— 目标不在网上）')
for l in atxt.splitlines()[:12]:
    print('   ', l.strip())

print('\n=== ③ ping（必须解析文本：只有"来自 <目标IP> 的回复"才算 UP）===')
pr = subprocess.run(['ping.exe', '-n', '2', '-w', '1000', TARGET], capture_output=True)
ptxt = pr.stdout.decode('gbk', 'replace')      # 中文 Windows ping 输出是 GBK，禁 text=True
up = ('来自 %s 的回复' % TARGET) in ptxt
print('  returncode=%s（不可信）' % pr.returncode)
for l in ptxt.splitlines():
    if l.strip():
        print('   ', l.strip())
print('  判读: 回复者==目标IP? %s' % up)

print('\n=== 结论 ===')
verdict = (not alive) and (not hit) and (not up)
print('  tcp_all_down=%s  arp_no_entry=%s  icmp_not_from_target=%s' % (not alive, not hit, not up))
print('  SHUTDOWN_CONFIRMED = %s' % ('YES' if verdict else 'NO'))

out = {'tcp_open_ports': alive, 'arp_hits': hit, 'icmp_from_target': up, 'confirmed': verdict}
with open(r'D:\strata166\logs\_shutdown_verify.txt', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('  saved -> D:\\strata166\\logs\\_shutdown_verify.txt')
