# SOFY 扩大 PPO：预先固定的实验计划

2026-10-26，在新分支训练和评估前记录。沿用 stage1 完整现有动作/牌种，规则没有简化。
目标是扩大真实 on-policy 经验并测量棋力，不把并行作业数或 PPO loss 当成强度证据。

## 硬件与采样

`ssh air4` 的登录环境提供 SOFY；显式目标为 `bifrost-2026101312015311-zhousc6`。
发现时此集群 64 张 PPU-ZW810E 中有 48 张调度空闲，分布于 3 个 worker；每卡 96 GiB。
每节点 184 线程，cgroup CPU 配额 184 核；PyTorch 2.9.0，CUDA 12.9 兼容层。
master 上已有其他 16 卡任务，不干预。真实资源随时变化，以提交时调度为准。

先提交 1 卡/64 CPU 基准，每配置真实训练 3×2,048 局，独立进程池；记录首批冷启动与后续采样/更新时间。
脚本 `scripts/sofy_ppo_probe.py`，任务 59336。现有 Linux x86-64 原生 FFI 来自已验证 desk 部署，
bundle 保存源码与逐文件 SHA-256；不另写 PPU 规则引擎。

实际基准成功：8/16/32/48 进程热身后采样中位数分别为 413.7/806.1/1,388.2/1,795.4 局/秒，
每配置只有三次更新，首批冷启动另列，原始记录在 `benchmarks/sofy-ppo-probe.json`。
选择 32 进程以留出父进程传输和评估余量；48 进程吞吐更高但每核收益下降。

## 四条独立训练分支

共同初始权重为已验收 PPO40，SHA-256
`1f865a82f1d0ff30266ec9ae0857993bb600700727de3799987b2f86b390dc62`。
每分支 1 卡、64 CPU 申请，32 个采样进程、每进程 32 局推理批次。
每分支 128×4,096 = 524,288 局，四分支合计 **2,097,152 局**。
这四条是独立 PPO 学习器，不是四卡 DDP，也不宣称已经实现历史对手池自博弈。

| 分支 | 学习率 | teacher BC 系数 | 训练种子起点 |
| --- | --- | --- | --- |
| b0 | 3e-5 | 0.1 | 21,000,000 |
| b1 | 3e-5 | 0.5 | 23,000,000 |
| b2 | 1e-4 | 0.1 | 25,000,000 |
| b3 | 1e-4 | 0.5 | 27,000,000 |

训练时无 discard guard，固定 qualified-tenpai 对手和 scaffold，正式净分/64 奖励，无额外塑形。
PPO 4 epochs、minibatch 2,048，其余沿用脚本默认。每 32 次更新保存 checkpoint。
每个任务 1 小时超时上限，非有限损失或权重直接失败；历史模型不覆盖。

## 模型选择与最终验收

开发集：种子 30,000,000..30,003,199，每 seed 以 offset%4 轮换模型座位，对手 qualified-tenpai。
评估四分支 u32/u64/u96/u128，分别 raw/teacher-optimal，共 32 配置；原候选、closed 和 qualified 作为冻结参照。
按开发集平均正式净分选择一个配置；若没有超过原候选，网页继续保留原候选。

仅在开发集选定且超过原候选后，冻结 checkpoint hash 和 guard，再使用新的
31,000,000..31,006,399 holdout。相同种子席位配对比较：相对原候选与 qualified 的
95% 区间下界都需 > -1；只有相对原候选下界 > 0 才宣称已证实提升。
没有通过则不替换网页。旧 holdout 6,600,000 段已经使用，不再次当作独立验收。

运行命令见 `scripts/sofy_ppo_train.py --branch 0..3`，在包含 `initial.bin`、`native/mahjong_ffi.so`
和训练源码的 SOFY bundle 内通过 `/usr/local/bin/python` 执行；产物位于 bundle 的 `large-ppo-bN/`。

## 实际任务与复现

四个训练 task 为 59337/59338/59339/59340，对应 b0..b3。
本次训练 bundle 根目录：
`/dataset-cpfs5/vtm-foundation-pretrain/temp/zhousc6/sofy/sofy-20261013-040152-0f100ab2/bundles/6a3a5aed44d98587`。

```sh
# 本地打包；Linux FFI 必须来自相同源码，不能上传 macOS 动态库。
python scripts/package_sofy.py --library /path/to/linux/mahjong_ffi.so \
  --checkpoint training/checkpoints/ppo-qualified-fast30k-v1-u0040.pt \
  --output /tmp/mahjong-sofy-new-run
# 将目录复制到 air4 后，在 air4 的登录 shell 内运行，每分支一次：
sofy submit --job-name bifrost-2026101312015311-zhousc6 \
  --name mahjong-ppo-b0 --nodes 1 --gpus-per-node 1 --cpus-per-node 64 \
  --description 'Train the predeclared Mahjong PPO branch on real stage1 games and evaluate against frozen opponents.' \
  --bundle /tmp/mahjong-sofy-new-run \
  --cmd 'env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 /usr/local/bin/python -u scripts/sofy_ppo_train.py --branch 0'
```

`scripts/sofy_ppo_evaluate.py --training-root <本次训练bundle目录> --branch N`
评估各不可变快照，并写入 `large-ppo-bN/development/`。不要覆盖已有 run 目录重新运行。
服务端拒绝 CPU-only 任务（HTTP 400），本次评估因此申请 1 GPU 调度槽/32 CPU，实际评估用 CPU，
并在结束后释放。没有改动其他人的作业或启动新的付费集群。

## 训练与开发集实测

四分支均完成 128 更新，2,097,152 局；评估任务 59341..59344 完成全部 32 个配置和三个参照。
开发集选择 `b2/u0032 + teacher-optimal`，均分 1.295，旧候选 1.0946875。
后续更新没有超过该快照，不能把更多训练步数当作更强的证据。
完整选择记录为 `benchmarks/sofy-ppo-development.json`。

`scripts/sofy_ppo_accept.py` 在 task 59345 中先落盘选择结果及 checkpoint SHA，再运行新 holdout；
若没有开发集提升则不会访问 holdout。`scripts/sofy_collect.py` 在 air4 复用已认证的 SOFY
HTTP 客户端，以 128 KiB 分块读取本项目 checkpoint 和原始评估记录，避开诊断输出的 256 KiB 截断。
仅 4 路并发，传输结果校验 SHA-256；不导出登录凭据。此适配使用本次 SOFY 0.7 客户端的内部接口，
升级 SOFY 后需复核接口兼容性。此前 Fuyao SSH 下载未能解析可用目标，因此不作为复现依赖。

```sh
# 在 air4 的 SOFY Python 环境执行，输出必须是新文件。
python scripts/sofy_collect.py --job-name bifrost-2026101312015311-zhousc6 \
  --remote-root <上述训练bundle根目录> --output /tmp/mahjong-sofy-results.tar.gz
```

## 一次性 holdout 结果

task 59345 成功完成 6,400×3 局配对评估。新候选均分 **0.57890625**，旧候选 **0.4753125**，
qualified 教师 **0.74953125**。

- 相对旧候选：+0.10359375，95% CI **[-0.31456364, 0.52175114]**。
- 相对 qualified：-0.170625，95% CI **[-0.62927813, 0.28802813]**。

通过预先设定的非劣门槛，但**没有证明比旧候选或 qualified 更强**。因此网页继续保留原人测候选；
这次结果不能包装成“大规模训练已显著提升棋力”。31,000,000..31,006,399 已使用，今后不能再当作新 holdout。
selected checkpoint SHA-256：`ceb031e49c0d57631e081d71393995290c88e19ff104c9edb955df72e5ed06e2`。

追加的同墙四座 184,000 盘棋力评估见 `docs/arena-evaluation.md`，同样未证明新旧部署策略有显著差异。
本轮 task 59336..59347 均已结束。现有算力足以继续实验，下一步应先处理原始网络对保护的依赖、
对手分布和训练目标；增加 GPU 数量本身没有带来已验证的棋力提升。

87 个训练快照及评估文件已取回本地 `training/runs/sofy-20261026/`（忽略目录，不提交大文件）。
归档 53,438,361 字节，SHA-256 `f0eb4a73a886c4847f7783e02419cb37ad1ef734a16d770a39725c59c3341abf`；
归档和选定 checkpoint 均已核对校验值。原始远端产物仍保留。
