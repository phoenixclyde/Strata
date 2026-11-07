## 2026-10-31 晚（W831）UI 宽度溯源 + WEB-UI 补丁真假

- **monitor 宽度窄不是我们改的**：三棵树 `serve/web/app.css` md5 全等 `cf027c74…`（src0271/src027/src028），容器与 HTTP 下发同 md5。
  上游逐 tag：**v0.2.2~v0.2.6 = 1240px，v0.2.7.1/v0.2.8 = `min(100%,1920px)`** ⇒ 上游改的，跟着带进来了。
- **判定视口的土办法（可复用）**：拿页面里已知 CSS 尺寸反算缩放倍数。本例用卡片 `gap:14px`→5.9px、`ctx-gauge:150px`、
  容器 1968px→829px 三点互校，得 0.4219 ⇒ 截图 1080×452 = **2560×1073** 等比缩放，1920 的盖子才第一次咬到。
- **处置**：`app.css` 末尾追加 `.monitor { max-width: none }`（标记 `ALBUS-W831`，作用域仅 monitor，about/chat 保留上游 1100）。
  无头 Chrome `--window-size=2560,1080` + `/#monitor`（前端支持 hash 直链）实图验证：8 卡一行、面板通栏；1280 宽回落 4 卡一行、无横向滚动
  （全局 `box-sizing:border-box`，`width:100%` 不吃 padding）。镜像 **0.2.8p2**。
- **WEB-UI 补丁其实只剩 4 行**：部署的 `app.js` 与上游 v0.2.8 **字节相同**（md5 `9fed14d1…`，92101 B）。
  用 patched−base orig 算真实增量 78 行，逐行比对上游：**74 行上游已原生具备**（images 页/saveApiKey/prefill 速率/采样默认值/火花线顶值），
  只有 PCIe 卡的 `· peak NN MB/s` 后缀是我们的。已按 `ALBUS-W831` 补回（92101→92306），实测 `to GPU 0.0 MB/s · peak 162 MB/s`，
  空载 `pciePk<1` 不显示。
- **门禁假绿（重要教训）**：`WEB-UI` 那条用的标记 `saveApiKey`，**上游自己就有** ⇒ 补丁没了也绿。标记已换成 `pciePk`。
  ⇒ **新铁律：门禁标记禁止用功能词，一律 `ALBUS-<批次>` 前缀；且必须同时校验 tree + image + served 三处。**
- **一致性**：`app.css`/`app.js` 四处 md5 相同（tree = image = container = 实际下发）。为免二次停服（引擎加载 ~240 s），
  `app.js` 用 `docker cp` 热更新 + 同时重建镜像；镜像内容与容器逐字节相同，重启/重建都得同一份，不产生漂移。
- 门禁扩到 **13 项，13/13 PASS**。回滚件：镜像 `0.2.8p1`/`0.2.8`、`app.css.bak-w831`、`app.js.bak-w831b`。
- 登记：**P203（ADOPTED）/ P204（CORRECTED）**；文档 `deploy/W828_UPSTREAM_028_PORT.md` §6.17。

