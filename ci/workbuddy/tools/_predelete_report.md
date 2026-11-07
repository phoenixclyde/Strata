# 删除前置校验报告  2026-10-08 20:44:35

## D:\strata166 -> D:\workbuddy_space\strata_ws\deploy
- 源文件数=4207  源字节=157569536
- 逐字节相同=4207  目标侧缺失=0  字节数不符=0  md5不符=0  白名单内差异=1
    [白名单] configs/workbuddy-strata166.md :: 本波(W712)按 0.1.40.4 升级更新了头部/§6/§9，并清了存量禁用码位；源件为 0.1.40.2 时代的 7324 B 版本，删除前快照留档
- 判定: **PASS**

## D:\workbuddy\_z_rk81 -> D:\workbuddy_space\strata_ws\waves
- 源文件数=165  源字节=582840
- 逐字节相同=164  目标侧缺失=0  字节数不符=0  md5不符=0  白名单内差异=1
    [白名单] _gh.py :: 迁移时**有意**改一处：TOKF 由旧 _z_rk81 路径改指新工作区（+14 B），见 MAP_OLD_TO_NEW.md；源件为改前的 3042 B 版本，删除前快照留档
- 判定: **PASS**

## 原件快照（删除前留档）
- _gh.py  ->  D:\workbuddy_space\strata_ws\tools\snapshots_premigrate\_z_rk81\_gh.py  (3042 B, md5 84e9897ec4e515c31b13b53ecd0a064f)

## 总判定
- **ALL PASS -> 可删**
- 待删文件合计=4372
- 模式: DELETE（--go）
