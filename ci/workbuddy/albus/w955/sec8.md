## 8 顺手修掉的账本不一致（`AUDIT24` 遗留 P1）

`ci/config.sh` 一直指着 **gfx029-build / 0.2.9-101**，而生产早已是 **build-r28 / 0.2.10-101**（`W938` 改了流程没改它）。
⇒ 任何人跑 `ci/strata-ci build` 都会拿错 ninja 树与镜像。本轮已改并落库：

- 改动：`BUILD=/home/albus/strata166/build-r28`、`IMG=strata-gfx906:0.2.10-101`
- 提交 **`03381d82`**，tag **`mi50-0.2.10-r29`**（末条 tag == HEAD，满足 `R80` 的 provenance）
- 主线状态随之变成 **落后 0 / 领先 38**（原 37）
