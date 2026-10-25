# 阶段一人测候选：PPO40 + 启发式保护

2026-10-26，已通过事先固定的人测门槛。该候选不是纯神经网络策略，也不是完整 MCR 成品。
规则仍为 `mcr-wmo2006-stage1`；完整番种排斥、补牌来源链、16 手整场、浏览器与 Pages 尚未完成。

## 直接试玩

在项目根目录运行（本机权重已就绪）：

```sh
./scripts/play_candidate.sh
# 其他座位/新牌局；输入动作 ID，q 退出
./scripts/play_candidate.sh --seat 1 --seed 16000002
# 自动观战并保存真实回放；输出文件必须不存在
./scripts/play_candidate.sh --watch --seed 16000003 --replay training/runs/my-watch.json
```

入口为本地中文终端，不是网页。真人可以选择引擎当时给出的全部合法动作，包括吃碰杠胡过和花牌操作；
教师保护只限制 AI 的标准弃牌候选，不限制真人动作。AI 非弃牌动作使用 `qualified-tenpai` 启发式。
输入错误会要求重新选择，未完成的牌局退出不记结算。尚未收集真人反馈；现有入口验证是代理操作冒烟。

## 模型与来源

- checkpoint：`training/checkpoints/ppo-qualified-fast30k-v1-u0040.pt`
- SHA-256：`1f865a82f1d0ff30266ec9ae0857993bb600700727de3799987b2f86b390dc62`
- 771 维 v6 特征、122 动作 v1、两层 256 MLP；网络学习标准弃牌，value 为缩放后的预期收益，不是胜率。
- 部署：确定性 argmax，`qualified-tenpai` scaffold，`teacher-optimal` 弃牌保护。
  保护保留教师在向听、合格听牌价值、听张、进张评分上并列最佳的弃牌，网络在其中选择。
  因此复合策略的成绩不能全部归因于网络。
- BC：30,000 局 qualified 教师，种子 13000000..13029999，2,371,105 条决策；
  40 epochs、batch 4096、花色增强、按对局划分验证集，最佳验证准确率约 81.6%。
- 随后 PPO：40×480 = 19,200 局，种子 14000000..14019199，三个冻结 qualified 对手，
  学习率 5e-5、teacher BC 系数 0.5。训练时没有 teacher-optimal 保护；保护是明确记录的推理配置。
- 优化采样后另完成 v2 的 19,200 局、274,099 次学习决策；该分支未超过原候选的开发集得分，
  所以没有把最新权重自动替换为最终候选。v2 历史、快照和失败比较均保留。

模型选择先在 1,600 局开发集（6700000..6701599）比较 BC 和两轮 PPO 的 8 个快照，
分别评估原始/受保护配置，共 18 种。按预定规则选开发集平均净得分最高者，
于 2026-10-26 07:40:36（Asia/Singapore）冻结权重校验值和配置，再运行最终 holdout。
选择记录见 `benchmarks/human-candidate-selection.json`，判据见 `docs/human-test-plan.md`。

## 独立评估

种子 6600000..6606399，共 6,400 局，每个 seed 使用一席候选，席位按 0/1/2/3 轮换，
其余三席均为冻结 qualified 教师。基线使用同一 seed/seat 配对；CI 为独立对局配对差的 95% 正态近似。

| 配置 | 平均净得分/盘 |
| --- | ---: |
| 人测候选（PPO40 + 保护） | +0.4622 |
| qualified 教师 | +0.3044 |
| closed 教师 | -0.9308 |

| 配对差 | 平均差 | 95% CI | 预定门槛 |
| --- | ---: | --- | --- |
| 候选 − closed | +1.3930 | [0.8855, 1.9004] | 下界 > 0：通过 |
| 候选 − qualified | +0.1578 | [-0.2848, 0.6005] | 下界 > -1：通过 |

候选和牌率 **23.97%**，放炮率 **14.52%**，流局率 **7.47%**。
相对 qualified 的区间跨过 0，不能宣称统计证明更强。以上是阶段一单盘结算，不能外推为完整 MCR 整场棋力。
完整原始报告在 `training/runs/human-holdout66-{candidate,closed,qualified}.json`；
可提交摘要及报告校验值在 `benchmarks/human-candidate-holdout.json`。

## 导出与验证

- ONNX：`training/exports/human-candidate-20261026.onnx`
- manifest：同目录 `human-candidate-20261026.manifest.json`，分别记录训练 guard 和部署 guard。
- ONNX SHA-256：`2d5b8d0c91032a940b0c1644f5201be38c591dc49965170150a22ec7336fa8ec`
- 100 局、1,460 个真实决策：PyTorch / ONNX CPU 所选动作全部一致；最大 logits 误差
  `2.1935e-5`，最大 value 误差 `2.9244e-6`。没有把 CPU 验证写成 WASM/WebGPU 已验证。
- 远端 Linux 再跑相同 100 局/1,460 决策也全部选牌一致；最大 logits/value 误差分别
  `2.4796e-5` / `2.3749e-6`，证据为 `benchmarks/human-candidate-onnx-remote.json`。
- 真人入口已检查非法输入拒绝、合法动作推进、返回下一决策、退出；观战 124 步完成并重放到同一结算。
- 大权重和完整运行数据不进入 Git；本机与远端保存真实文件，不含随机示例替身。
  远端候选、ONNX、完整 holdout 报告和本卡均在 `/home/zsc/play_mahjong_releases/batch-20261026`。

复核命令：

```sh
uv run python training/compare_runs.py --candidate training/runs/human-holdout66-candidate.json \
  --baseline training/runs/human-holdout66-closed.json
uv run python training/compare_runs.py --candidate training/runs/human-holdout66-candidate.json \
  --baseline training/runs/human-holdout66-qualified.json
uv run python training/verify_onnx.py --checkpoint training/checkpoints/ppo-qualified-fast30k-v1-u0040.pt \
  --onnx training/exports/human-candidate-20261026.onnx --discard-guard teacher-optimal \
  --games 100 --seed-start 12500000 --output /tmp/candidate-parity-new.json
```
