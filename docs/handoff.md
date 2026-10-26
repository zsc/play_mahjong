# 麻将 AI 项目交接

更新时间：2026-10-26（Asia/Singapore；本节覆盖下方历史记录）

## 最新进度

- **当前优先发布网页，用户要求不再连接 air4。**目标 origin 为 `https://github.com/zsc/play_mahjong.git`。
  静态产物已整理到 `docs/`，Pages 使用 main → /docs；结果和发布步骤见 `docs/release-20261026.md`。
  新的全动作模型尚未通过独立棋力验收，网页继续使用旧 PPO40 复合策略。
- 全动作 `decision_batch`、tile-shared-v1、每玩家轨迹、冻结对手池和 distill/PPO 路线已实现。
  本地 MPS 蒸馏完成 64×1024=65,536 盘，5,325,390 个样本；
  `training/runs/league-local-warm-20261026/u0064.pt` 已落盘，SHA 与训练摘要在
  `benchmarks/league-local-warm-summary.json`。教师一致率不是独立棋力，未导出到网页。
  远端只完成 61039 探针，59350 已取消，后续 warm 提交因 SSH 超时未启动；本轮没有重连。
  新开发种子段 60000000 起尚未评估，最终 holdout 62000000..62015999 未使用。
  训练恢复/导出/arena 针对性 9 项通过，MPS 恢复 RNG 已保存但未验证逐 bit 恢复。

- SOFY 四分支 PPO 已完成 2,097,152 盘（59337..59340），开发集选定 b2-u32；
  新 6,400 局 holdout 对旧候选 +0.104，CI [-0.315, 0.522]，未证明提升，不替换网页模型。
  18.4 万盘棋力测试（59346、59347）进一步确认：主测试每策略 32,000 盘、8,000 同墙四座组，
  新旧带保护模型配对差 +0.0528，CI [-0.1403, 0.2459]。
  旧候选对三个 qualified 平均 +0.240，CI [0.052, 0.428]；无弃牌保护旧网络 -0.507。
  这是该冻结对手配置下的复合策略收益，不是完整 MCR 或纯网络强度。详见 `docs/arena-evaluation.md`。
  SOFY 59336..59347 本轮任务均已结束，未取消其他任务。当前无需升级 GPU；优先研究训练目标、
  对手多样性及保护依赖。资源、快照、原始记录位置见 `docs/sofy-ppo-plan.md`。
  87 个快照/评估文件已校验并取回 `training/runs/sofy-20261026/`，18.4 万盘统计已本地重算核对。
  开发种子 30000000..30003199、holdout 31000000..31006399、arena 40000000..40007999
  及 41000000..41000999 均已使用。

- 浏览器人测已接入已验收 PPO40 + teacher-optimal：`web/` 提供人机对局、全合法动作、AI 观战、
  模型建议、终局回放导入/导出、真实训练记录。OCaml CPS WASM 和 ORT 单线程 WASM 均在 Worker 中运行。
  `cd web && npm ci && npm run prepare:assets && npm run dev`；精选 ONNX 随源码保留。
  4 盘 291 次原生/WASM 转移、207 次模型决策一致，特征误差 0，另通过回放/非法动作/加载失败测试。
  纯静态 `/mahjong/` 子路径已加载验证。详见 `docs/browser-human-test.md`。

- 优化已部署到 `/home/zsc/play_mahjong_releases/batch-20261026`，之前的 frontier 部署和
  `/home/zsc/play_mahjong` 未覆盖。直接 SSH 在应用进程不可达，仍通过独立 tmux 会话执行 SSH。
  tmux 读取 Downloads 可能被 macOS 拒绝，上传/下载经 `/tmp` 中转。
- 向听分块 DP、增量候选计算、合并缓存、单遍可见牌计数、teacher_chunk、advance_batch、
  每进程 16 局批量推理已实现。相对上轮分块版本，本地 PPO 2.28×、教师数据 1.92×；
  远端相同 240 局三次中位数 10.725→4.495 秒（2.386×）。轨迹摘要保持一致。
- 30,000 局 qualified 教师数据已在 frontier 部署的 `training/data/qualified-fast30k/` 生成并校验；
  种子 13000000..13029999，2,371,105 样本，444.302 秒含压缩。
- BC 已完成 40 epochs；随后 PPO v1 已完成 40×480 局（种子 14000000 起）。
- 新批量采样 PPO v2 从 v1-u0040 warm start，再完成 40×480 局（种子 15000000 起）；
  8 个常驻进程、16 局/进程、CUDA 更新，快照已取回本地 `training/checkpoints/ppo-batch-v2-u*.pt`。
- PPO 支持保存优化器、RNG、配置并精确 `--resume`；改变 sampler 使用明确的 `--init` 新分支。
- 最新核心 22 项、Python 123 项通过；批量接口 JSON-lines 对照 9 项、远端批量/恢复 10 项通过。
  规则仍是 stage1，完整番种排斥、补牌来源链、整场尚未完成；网页静态构建已可用，公网 Pages 尚未发布。
- 人测选择及独立验收见 `docs/human-test-plan.md`；完整证据见 `docs/env-performance.md`。
  下方旧模型失败记录仅为历史，不能用来替代新模型的独立验收结果。
- **人测门槛已通过**：选定 v1-u0040 + teacher-optimal。6,400 局相对 closed 的配对差
  +1.3930，CI [0.8855, 1.9004]；相对 qualified +0.1578，CI [-0.2848, 0.6005]。
  v2 没有在开发集超过旧候选。这份早期 holdout 未证明强于 qualified；最新同墙四座结果见上方。
- `./scripts/play_candidate.sh` 可开始本地终端人测；ONNX 100 局 1,460 决策数值/动作对照通过。
  详见 `docs/model-card-human-candidate-20261026.md`。holdout 6600000..6606399 已使用，不能再调参后复用作最终验收。

## 以下是历史交接记录

## 接手补充：环境效率审计

- 详见 `docs/env-performance.md` 及 `benchmarks/` 原始证据。当前不需要升级 GPU：
  远端数据生成占满 CPU，GPU 空闲；4 局 PPO 小样本同样主要耗时在采样。
- 本地增加结构向听有界缓存，20 局同轨迹从 15.107 秒降至 7.013 秒；
  native/JSON-lines 观察、特征、动作和终局摘要一致。没有修改规则或教师排序。
- PPO 增加采样/更新阶段计时，去掉重复编码；两进程、8 局真实 smoke 完成，权重有限且变化。
- 最新本地验证为 OCaml 21/21、Python 110 passed、ruff 通过，包含 `qualified-best` 构建。
  `qualified-best` 的正式消融仍未执行，不能采用为更强教师。
- 改动尚未同步远端，没有重启原有 24 个生成任务。最近抽查 shard 0/7/8/23 为
  620/600/380/360（各 1250），尚无最终 NPZ/meta。不能启动依赖它的 BC。
- 发现 PPO `--init` 是 warm start，尚非精确断点恢复；补牌来源链、完整规则与整场仍待完成。
- 直接 SSH 在当前应用进程失败，使用独立 tmux 会话已成功读取远端并跑小样本基准。
- 用户要求 `git commit`，本次初始化本地 Git 并提交现有源码、性能改动与小型基准证据；
  大数据、日志、模型权重和构建产物被忽略，没有推送或发布。

以下为此前训练交接记录；其中“未验证”的构建/回归状态已由本节更新。

## 一句话状态

项目已经完成 OCaml 规则核心、C ABI、Python 训练与版本化评估链路；当前规则仍是
`mcr-wmo2006-stage1`，不是完整 MCR。已验证的**最强策略是 `qualified-tenpai` 启发式**，
不是神经网络。现有 PPO 在干净 holdout 上没有超过闭门教师，不能宣称“训练模型更强”。

当前有一个远端后台任务正在生成 30,000 局 `qualified-tenpai` 教师数据；完成前不要启动
对应的 BC 训练。此前交接时没有 Git 元数据；本次 Git 状态见上方接手补充。

## 用户最新要求与约定

- `AGENTS.md` 的技术基线已从 Rust/PyO3/maturin/wasm-bindgen 改为
  OCaml/C ABI/ctypes/`wasm_of_ocaml-compiler`。当前文件中已无 Rust、PyO3、maturin 或
  wasm-bindgen 架构残留。
- 本机 OCaml 环境已就绪：opam 2.6.1，switch `mahjong`，OCaml 5.5.2，Dune 3.24.2。
  已安装 Alcotest、QCheck、ctypes、ctypes-foreign、Yojson、Zarith、utop、ocamlformat、
  ocaml-lsp-server 和 wasm_of_ocaml-compiler。
- 默认中文沟通；代码标识符用英文；编辑使用 `apply_patch`。
- 训练结果、随机权重、启发式和回放必须明确区分，不伪造棋力。
- 当前目标仍是继续提高麻将 AI 水平；远端 GPU 为 RTX 2080 SUPER，入口是 `ssh desk`。

## 当前代码与验证状态

### 已验证

- 在最新 `qualified-best` 改动之前，OCaml `dune build @all @ffi` 成功，
  `dune runtest --force` 为 **20/20**。
- OCaml 原生 `.so` 可在本机 macOS arm64 加载；远端 Linux 原生 FFI 和 JSON-lines
  后备传输都已完成过冒烟与一致性检查。
- `training/train_ppo.py` 新增的 `--snapshot-every` / `--snapshot-dir` 已在远端真实
  PPO 训练中实际生成第 10/20/30/40 次更新快照。
- 最新完整 Python 回归（本次新增代码之前）为 **109 passed**，`ruff check training` 通过。

### 未验证或进行中

- 本地新增了 OCaml 教师变体 `qualified-best`：
  - `ocaml/mahjong_core/lib/heuristic.ml`
  - `training/mahjong_ai/teachers.py`

  它计划在多个“合格听”鸣牌之间按番值、听张、进张排序，而不是取第一个。改动后
  `dune build @all @ffi && dune runtest --force` 被中断，**尚未完成构建和测试**；也没有同步到远端。
  在验证前不要用它生成训练数据或做正式评估。
- 最新 `training/train_ppo.py` 和 `qualified-best` 改动尚未重跑完整 Python 回归与 ruff。
- 当前规则核心只覆盖阶段一，不是完整 MCR；WASM 网页、GitHub Pages、完整 81 番排斥、
  16 手整场和正式整场流程仍未完成。

## 真实训练结果

### 1. 当前 PPO 的干净 holdout：未超过闭门教师

种子 `6400000..6406399`，6400 局，候选席轮换，候选对三名默认教师。

| 策略 | 平均净得分 ± SE | 和牌率 | 放炮率 | 流局率 |
| --- | ---: | ---: | ---: | ---: |
| `ppo-discard-closed-v6-38k.pt` | +2.519 ± 0.373 | 25.02% | 13.77% | 10.41% |
| 闭门教师 | +3.349 ± 0.378 | 26.39% | 13.95% | 9.38% |
| `bc-discard-closed-v6-38k.pt` | +2.437 ± 0.371 | 24.75% | 13.53% | 10.50% |

按 `(seed, seat)` 配对：

- PPO 相对闭门教师：`-0.830 ± 0.409`，95% CI `[-1.633, -0.027]`，显著更差。
- PPO 相对 BC：`+0.082 ± 0.392`，95% CI `[-0.686, 0.850]`，没有证明提升。
- BC 相对闭门教师：`-0.912 ± 0.419`，95% CI `[-1.733, -0.091]`。

此前的 6.0m 1600 局结果中 PPO 点估计略高于教师，但 6.2m 和 6.4m 的更大样本都给出负差值；
不得再把旧结果表述为“PPO 已超过教师”。

### 2. 对三名闭门教师对手的开发集

种子 `6500000..6501599`，1600 局，候选席轮换，对手为三名闭门教师。

| 策略 | 平均净得分 ± SE | 和牌率 | 放炮率 | 流局率 |
| --- | ---: | ---: | ---: | ---: |
| 原 PPO | +0.895 ± 0.739 | 23.25% | 13.75% | 10.69% |
| 闭门教师 | +1.434 ± 0.786 | 23.75% | 13.31% | 10.56% |
| 闭门 BC | +1.164 ± 0.754 | 23.69% | 12.81% | 10.94% |

配对差：PPO 相对闭门教师 `-0.539 ± 0.751`，95% CI 跨 0；相对 BC `-0.269 ± 0.677`，
也没有证明提升。

### 3. 对闭门对手继续训练 PPO

从 `ppo-discard-closed-v6-38k.pt` 继续训练 40 次更新，每次 480 局、24 workers，
对手改为闭门教师，其他条件为 4 PPO epochs、学习率 `5e-5`、teacher BC 系数 0.5。

开发集仍为种子 `6500000..6501599`、1600 局：

| 快照 | 平均净得分 ± SE | 相对闭门教师的配对差 | 95% CI |
| --- | ---: | ---: | ---: |
| update 10 | +1.842 ± 0.775 | +0.408 ± 0.707 | `[-0.978, 1.793]` |
| update 20 | +0.824 ± 0.746 | -0.610 ± 0.752 | `[-2.084, 0.864]` |
| update 30 | +1.301 ± 0.744 | -0.133 ± 0.712 | `[-1.529, 1.263]` |
| update 40 | +0.936 ± 0.738 | -0.498 ± 0.734 | `[-1.937, 0.941]` |

第 10 次快照点估计最好，但置信区间跨 0；后续更新反而退化。这个 checkpoint 可保留作实验，
不能作为“已提升”的发布模型。

### 4. 教师消融：发现明确更强的启发式

种子 `6500000..6501599`，1600 局，候选对三名默认教师：

| 教师变体 | 平均净得分 ± SE | 和牌率 | 放炮率 | 流局率 |
| --- | ---: | ---: | ---: | ---: |
| `qualified-tenpai` | **+2.644 ± 0.724** | 26.8% | 14.2% | 8.7% |
| `closed-kong` | +1.531 ± 0.704 | 24.9% | 14.6% | 9.1% |
| `closed` | +1.456 ± 0.705 | 24.9% | 14.6% | 8.9% |
| `tenpai-only` | +0.668 ± 0.689 | 23.4% | 15.9% | 9.4% |
| `default` | -0.832 ± 0.655 | 21.5% | 15.9% | 9.1% |

`qualified-tenpai` 相对 `closed` 的配对差为 `+1.1888 ± 0.2594`，95% CI
`[+0.6804, +1.6971]`，结果明确。

在三名闭门教师作为对手、同样 1600 局的开发集上：

- `qualified-tenpai`：`+2.626 ± 0.795`。
- `closed`：`+1.434 ± 0.786`。
- 配对差：`+1.1919 ± 0.2741`，95% CI `[+0.6547, +1.7291]`，仍然明确。

因此当前最可靠的方向不是继续微调旧闭门 BC，而是：

1. 用 `qualified-tenpai` 生成新数据。
2. 训练同口径 BC。
3. 以 `qualified-tenpai` 为至少一种冻结对手做 PPO。
4. 用全新 holdout 比较 BC、PPO 与 `qualified-tenpai` 本身。

## 当前后台任务

远端正在生成 `training/data/qualified-tenpai-v1-30k/`：

- 24 个分片，每片 1,250 局，共 30,000 局。
- 种子 `9000000..9029999`，与已有训练和评估种子不重叠。
- 命令口径：`--teacher-variant qualified-tenpai`。
- 进程在 `ssh desk` 远端持续运行；最后一次观察时 shard 0 为 `340/1250`，shard 8 为
  `120/1250`，尚无 `.npz`/`.meta.json` 最终文件落盘。
- 生成结束后必须检查 24 个 `.npz` 和 24 个 `.meta.json` 都存在，再统一验证。

查看状态：

```sh
ssh desk 'cd /home/zsc/play_mahjong && ps -eo pid,etime,pcpu,args | rg "generate_bc.py" | rg -v rg; \
  for i in 0 7 8 23; do echo "shard $i"; tail -1 training/logs/generate-qualified-30k-$i.log; done'
```

不要重启仍在运行的生成进程，否则会覆盖或重复消耗 seed 段。

## 已落盘资产

### 闭门教师数据

- 本机 8,000 局：`training/data/closed-v6-local8k/`。
- 远端 30,000 局：`/home/zsc/play_mahjong/training/data/closed-v6-30k/`。
- 合并规模：38,000 局、3,123,098 个决策，其中弃牌 2,232,169。
- 用于训练既有 `bc-*-closed-v6-38k.pt`。

### 模型

- `training/checkpoints/bc-discard-closed-v6-38k.pt`
- `training/checkpoints/bc-all-closed-v6-38k.pt`
- `training/checkpoints/ppo-discard-closed-v6-38k.pt`
- `training/checkpoints/ppo-closedopp-v1.pt`
- `training/checkpoints/ppo-closedopp-v1-snapshots/ppo-closedopp-v1-u0010.pt` 到 `u0040.pt`
- 上述 PPO checkpoint 和快照已同步回本机。

### 报告与证据

关键报告均已在 `training/runs/`：

- `holdout64-ppo.json`
- `holdout64-teacher.json`
- `holdout64-bc.json`
- `compare-holdout64-ppo-vs-teacher.json`
- `compare-holdout64-ppo-vs-bc.json`
- `dev65-ppo-closedopp.json`
- `dev65-teacher-closedopp.json`
- `dev65-bc-closedopp.json`
- `compare-dev65-ppo-vs-teacher-closedopp.json`
- `compare-dev65-ppo-vs-bc-closedopp.json`
- `dev65-qualified-closedopp.json`
- `compare-dev65-qualified-vs-closed-closedopp.json`
- `dev65-closedopp-u10.json`、`u20`、`u30`、`u40` 及对应 compare 报告
- 五种教师变体的 `dev65-*-defaultopp.json` 和 `compare-dev65-*-vs-closed.json`

报告中的 `mean_net_score` 是单盘正式结算分差均值；`mean_difference` 才是同 seed/seat
配对差。不要把两者混用。

## 下一步建议顺序

1. **等待并验证 qualified 数据**
   - 确认 24 个分片完成。
   - 检查每片元数据为 `teacher_variant=qualified-tenpai`，规则/特征/动作版本一致。
   - 检查 seed 无重复、无跨片重叠，mask 非空，标签在 mask 内，features 有限。
   - 汇总动作分布并写入 `validation.json`。

2. **完成 `qualified-best` 的构建和消融**
   - 运行 `dune build @all @ffi && dune runtest --force`。
   - 在开发种子 `6500000..6501599` 上分别对默认教师和闭门教师各跑 1600 局。
   - 只有配对 CI 明确为正才采用；否则保留 `qualified-tenpai`，不要为了“新代码”强行切换。

3. **训练 qualified 教师 BC**
   - 使用 30k 数据，按完整对局分 train/validation。
   - 先跑隐藏层 256、30-40 epochs 的可比模型；如果验证损失仍下降，再试 512。
   - 学习范围先保持标准弃牌；其他动作由 `qualified-tenpai` scaffold 处理，并在文档中明确。
   - 不建议再把 smoke 或验证损失当成棋力。

4. **PPO 用 qualified 对手而不是旧 default/closed**
   - 从 qualified BC 初始化，训练对手至少包含 `qualified-tenpai`。
   - 每 10 次更新保存快照，在固定开发集选择，而不是只保留最后一次更新。
   - 可比较 `teacher_bc_coefficient` 0.2/0.5 和学习率 `5e-5`/`1e-4`，每轮只改一个变量。

5. **全新 holdout 复核**
   - 建议使用未参与调参的 `6600000..6606399` 或新的独立段。
   - 同 seed/seat 配对比较 BC、PPO、`qualified-tenpai` 和闭门教师。
   - 至少报告 6400 局、平均净得分 ± SE、和牌/放炮/流局率与 95% CI。

6. **只有通过后才导出和更新发布材料**
   - 重新导出 ONNX，manifest 写入真实评估路径和 SHA256。
   - 更新 `docs/progress.md`、模型卡和 `README.md`。
   - 运行 `uv run ruff check training`、`uv run pytest -q training/tests`、OCaml 全量测试。

## 常用命令

```sh
# 本机 OCaml 环境
eval "$(opam env --switch=mahjong --set-switch)"
cd ocaml
dune build @all @ffi
dune runtest --force

# Python 回归
cd ..
uv run ruff check training
uv run pytest -q training/tests

# 远端检查
ssh desk 'cd /home/zsc/play_mahjong && ps -eo pid,etime,pcpu,args | rg "generate_bc.py|train_ppo.py|evaluate.py" | rg -v rg'

# 远端 Python
PYTHONPATH=training /home/zsc/mahjong-venv/bin/python training/...
```

并行跑多个小模型评估时，优先使用 `--device cpu`，并设置
`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TORCH_NUM_THREADS=1`。
否则每个 Python 进程会争用同一块 GPU 或大量 CPU 线程，整批评估会明显变慢。

## 不可宣称的事项

- 不可宣称完整 MCR 已实现。
- 不可宣称当前 PPO/BC 已统计证明强于教师。
- 不可把 `qualified-tenpai` 启发式称为“训练出的强 AI”。
- 不可把训练局数、smoke checkpoint、训练 loss 或验证准确率当成正式棋力。
- 不可把当前评分与缺少完整番种、整场流程的版本混为完整 MCR 结果。
