# 浏览器人测

使用已经冻结并通过验收的 `ppo-qualified-fast30k-v1-u0040`，部署保护为
`teacher-optimal`，非标准弃牌由 `qualified-tenpai` 启发式处理。真人保留引擎给出的全部合法动作。
仍为 `mcr-wmo2006-stage1`，不代表完整 MCR 已验收。

## 启动

先按 README 安装 OCaml 工具链，然后从仓库根目录执行：

```sh
cd web
npm ci
npm run prepare:assets
npm run dev
```

访问 `http://127.0.0.1:5173/`，自动开始东家对局。选牌后确认打出；响应窗口提供实际合法的吃、碰、杠、胡、过或花牌操作。
可切换座位、设置确定性种子、查看本手建议，或选择 AI 观战再开始。
首次载入和「换牌开新局」都会生成新编号。需要复现时填写牌局编号并点击「按编号开局」；
相同编号、模型和四家 AI 配置会重现相同牌墙、动作及结局。编号写入回放，规则核心仍按显式种子确定性运行。

「保存回放」在终局后可用；JSON 包含完整动作和结算，导入后标记为历史回放。
「训练记录」显示 184,000 盘棋力测试、209 万盘训练的开发/验收结果、早期 6,400 局独立验收及真实后续训练记录；训练得分明确区别于固定对手评估。

## 静态构建

```sh
cd web
npm run prepare:assets
MAHJONG_BASE=/play_mahjong/ npm run build
npm run test:release
npm run stage:pages
npm run preview
```

`MAHJONG_BASE` 必须匹配部署子路径；省略时为相对路径 `./`。
将 `web/dist` 放到普通静态 HTTP 服务或 GitHub Pages 即可，不需要推理后端。
hash 导航不会依赖服务器路由。目标仓库为 `https://github.com/zsc/play_mahjong`。
`stage:pages` 将构建产物复制到 `docs/`，保留手写文档，生成 `.nojekyll`。提交并推送后，
在 Settings → Pages 中选择 **Deploy from a branch → main → /docs**。
目标网址为 `https://zsc.github.io/play_mahjong/`；启用并完成部署前不代表已经上线。
`.github/workflows/pages.yml` 在 main 推送和 PR 时重新构建并运行静态验收，不自动切换 Pages 发布源。
本地通过不等于 GitHub 工作流已经通过。

小型精选权重 `web/assets/candidate.onnx` 随源码保留，SHA-256 为
`2d5b8d0c91032a940b0c1644f5201be38c591dc49965170150a22ec7336fa8ec`。
构建时和浏览器加载时均校验；manifest 来自 `training/exports/human-candidate-20261026.manifest.json`。
大批 checkpoint 和训练数据仍在忽略目录。

## 浏览器运行边界

- 同一 OCaml dispatcher 经 `wasm_of_ocaml-compiler 6.5.0` 的 CPS 模式编译，Worker 中执行状态转移。
- 特征是训练端 v6 的 TypeScript 薄适配；ONNX Runtime Web 固定 `1.30.0`，单线程 WASM，无需 WebGPU、SharedArrayBuffer 或跨源隔离。
- 动作概率不是胜率；value 乘训练的 64 分缩放系数后显示为预期净得分。
- 页面只收到当前观察视角；他家摸牌、暗杠牌种和未裁定响应不展示。策略仍只使用 actor 的观察。
- 资源缺失、模型 SHA 或契约不匹配会明确失败，不会自动替换成启发式/随机权重。
- 需要支持 WebAssembly GC 的现代浏览器。未实现 WebGPU 加速、浏览器训练或 checkpoint 决策滑块。

## 已执行验证

```sh
# 需要原生 FFI 与原始候选 checkpoint；fixture 是实际对局，默认不提交。
.venv/bin/python web/scripts/native-fixtures.py
cd web
npm test   # 另一个终端先启动 npm run dev
```

Chromium 中 4 个真实完整单盘、291 次状态转移/观察/终局与原生逐项一致；207 次推理动作全部一致。
771 维特征最大差 0，WASM vs PyTorch logits 最大差 1.72e-5，value 最大差 2.67e-6。
证据：`benchmarks/browser-wasm-parity.json`。另通过非法/过期动作拒绝、对手摸牌过滤、整盘回放和结算一致、模型 404 与契约不匹配测试。
这验证的是现有阶段一核心的跨端一致性，不替代完整规则验收。

手工浏览器已验证选牌/确认出牌、模型建议、训练记录；纯静态 `/mahjong/` 子路径另作加载验证。
生产构建另通过 390×844 手机视窗无横向溢出、关闭 WebGPU 后真实 WASM 加载测试。
