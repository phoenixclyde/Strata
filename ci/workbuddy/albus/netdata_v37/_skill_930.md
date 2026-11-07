### 9.30 【严重】部署链路的静默失败：镜像层数无上限（2026-11-05 02:37）
**现象**：机主让改「磁盘容量占用加括号」，我改完、部署、截图——线上没变。查容器内文件：
```
/usr/share/netdata/web/custom/gpu.html  161991 B  Nov 4 18:34   ← 旧版本
宿主 assets/gpu.html                    161750 B                ← 新版本
docker images | grep rk-netdata         最新 tag 仍是上一轮
```
构建日志真因：
```
#9 [5/7] COPY assets/gpu.html ...
ERROR: failed to prepare 13t55... as u6gr8...: max depth exceeded
FATAL: build 失败
```
**根因**：`build_image.sh` 里 `BASE=$(docker inspect netdata -f '{{.Image}}')` —— FROM 取的是**运行中容器的镜像**，
而那是上一轮的派生镜像。于是每次构建 = 上一轮派生 + N 层，层数无界增长；当天部署二十多次后到 125 层触发上限。
更糟的是脚本在 build 之前就 echo 了 `TAG=...`，我用 `grep TAG=` 取输出 => 看不到 FATAL => 误判为"已部署"。
**判据（已写进脚本）**：
1. `FROM` 必须用**固定 base**：`$OPS/BASE_IMAGE` 一行（默认 `rk-netdata-base:6ac52ba4145c` = netdata v2.11.0-151-nightly）。
   升级底座时改这个文件，不要改"取运行镜像"的逻辑。
2. 构建后必须校验：产物 ID 非空 + `len .RootFS.Layers` ≤ 40，否则 FATAL 退出。现在稳定 12 层。
3. 部署后必须比对**容器内 /usr/share/netdata/web/custom/gpu.html 的 md5 == 本地 md5**，
   不能只看 verify PASS（verify 比的是"线上==容器内"，两者都旧时照样 PASS）。
**教训**：`grep TAG=` 这种"只挑好消息"的取输出方式会掩盖失败；**判定部署成功要用文件指纹，不是用日志关键字**。
