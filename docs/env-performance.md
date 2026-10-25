# 环境性能审计（2026-10-26）

## 第三轮：合并调用、复用计算和批量推理

本地 Apple M5、单进程、原生构建、CPU 单线程推理；固定 BC checkpoint，240 局，
种子 12000000 起，3 次重复的墙钟中位数。`benchmark_sampling.py` 将指纹计算排除在计时外；
不包含进程启动、压缩、GPU 更新。原始 JSON 位于 `benchmarks/sampling-*.json`。

| 路径 | 本轮优化前 | 优化后 | 吞吐倍数 |
| --- | ---: | ---: | ---: |
| PPO（旧采样顺序） | 4.466 s | 2.757 s | 1.62× |
| PPO（16 局合批） | 4.466 s | 1.955 s | 2.28× |
| 教师数据（不含压缩） | 5.599 s | 2.913 s | 1.92× |

这些是相对上一轮分块 DP 版本的增益。20 局完整观察/特征/动作/结算基准为 0.373 秒，
摘要仍为 `7502ee94d480a670c2859e8e9545e1eab1b249676f804f0998f6dabcaea3ecab`。
远端 Ryzen 3900X 同机前后基准为 **2.386×** 吞吐（`remote-before-ppo.json` / `remote-batch-ppo.json`）。

- `teacher_chunk` 每次最多生成 64 个教师决策，复用同一份弃牌候选给观察提示和教师选择。
- `advance_batch` 在同一个 OCaml 状态机内执行对手和 scaffold 动作，停在模型弃牌点或终局。
  批次校验失败会回滚全部牌局；非法动作仍然报错，不自动换动作。
- 可见牌计数由 34 次遍历改为一次；结构 frontier 的合并结果有界缓存；候选弃牌和摸牌
  增量更新对应花色及特殊形统计。旧参考算法保留，30,000 手随机比较以及增减牌对照通过。
- PPO 每进程同时推进至多 16 局，再一次前向。240 局的边界调用从 65,333 次降为 809 次，
  推理从 3,557 次降为 314 次，实际平均 batch 约 11.1。每盘各自结算和 GAE，行为权重固定。
- **合批会改变随机数消费顺序。**同采样模式可复现；旧模式保留为 batch-size=1。
  单路新旧路径的 features/mask/action/log-prob/value/reward/GAE 逐项一致，
  多路验证 log-prob 与冻结策略一致、动作合法、回报无跨盘混接、精确恢复一致。
- 原生与 JSON-lines 后备接口均通过新批量契约测试。仍使用 JSON 传递模型决策观察，
  没有宣称已实现全二进制特征 ABI，也没有更改规则或教师策略。
- 已同步到独立目录 `/home/zsc/play_mahjong_releases/batch-20261026`，历史部署不覆盖。
  远端按锁文件补齐 pytest 9.1.1；原生测试 22 项和批量/恢复测试 10 项通过后启动新训练分支。
- 新分支已完成 40×480 = 19,200 局、274,099 个模型决策，累计采样 56.250 秒、
  参数更新 10.041 秒；单批采样中位数 1.330 秒。详情 `benchmarks/ppo-batch-v2-training.json`。
  训练耗时不等于棋力：该分支未超过开发集原候选，最终独立验收采用原 PPO40 + 保护。
  目前仍无升级 GPU 的必要，采样耗时高于参数更新且没有显存不足。

```sh
uv run python training/benchmark_sampling.py --mode ppo --batch-size 16 --output /tmp/ppo-batch.json
uv run python training/benchmark_sampling.py --mode teacher --chunk-size 64 --output /tmp/teacher-chunk.json
uv run python training/train_ppo.py --init training/checkpoints/bc-qualified-fast30k-v1.pt \
  --output training/checkpoints/new-run.pt --workers 8 --rollout-batch-size 16 \
  --games-per-update 480 --updates 40 --scaffold-variant qualified-tenpai --opponent-variant qualified-tenpai
```

## 第二轮优化与远端落地

用户要求继续加速并训练人测候选后，增加了按花色/字牌分解的动态规划。
每个块保留 `(面子数, 是否有雀头)` 对应的最大搭子数；三门数牌共享 `5^9` 懒计算表，
字牌使用独立 `5^7` 表，全局合并保留面子/雀头约束。十个状态以 30 位整数打包，
不把各花色的一个最优标量直接相加。普通向听、七对/十三幺的原有启发式语义不变。
原递归实现继续作为参考，30,000 组普通/密集单花色计数、0–4 个副露做逐项对照。
表由代码在运行时计算，没有提交预生成二进制或改变规则版本。

- 本机相同 20 局：原始版本 15.107 秒 → 第一轮缓存 7.013 秒 → 分块版本 0.914 秒。
  JSON-lines 版本 0.952 秒，完整轨迹摘要仍相同。
- 远端独立目录 `/home/zsc/play_mahjong_releases/frontier-20261026-0710` 构建测试通过，
  同种子 20 局 1.822 秒，与本机轨迹摘要相同。此时旧 24 个生成任务仍在运行。
- 新数据种子 `13000000..13029999`，8 worker、24 个 1250 局分片，
  **30,000 局实际生成及压缩写盘 444.302 秒（约 7.4 分钟，67.52 局/秒）**。
  2,371,105 条决策全部通过数据契约/合法标签/种子去重/回报结算校验。
- 没有终止旧任务或覆盖历史实验。Linux FFI 构建改为原子替换共享库文件，
  避免截断运行中进程 mmap 的 inode。
- BC 新增 `--vectorized-batches`：整批取数、设备端批量花色增强，
  六种排列 × 全部 122 个动作与逐条参考增强完全一致；数据哈希每次训练只算一次。
- PPO 复用采样 Pool，新增 `--resume` 恢复 optimizer、更新计数、配置与 RNG。
  同 CPU 上“两次连续更新”和“第一次快照恢复再更新”的模型/optimizer 逐 bit 一致。
  旧 checkpoint 缺少恢复状态时明确拒绝 resume，可显式 `--init` warm start。

原始证据见 `benchmarks/env-block-frontier-*.json`、`qualified-fast30k-generation.json`、
`qualified-fast30k-validation.json` 和 `ppo-exact-resume.json`。
本轮数据/训练/人测判据见 `docs/human-test-plan.md`。下方保留第一轮测量及当时状态，
其中“只在本地”和“尚无精确 resume”已被本节更新。

## 第一轮审计记录

目前先不升级 GPU。当前数据生成受 CPU 上的向听/进张计算限制；已有 RTX 2080 SUPER
在本次检查时空闲。性能优化不能替代完整规则验收：当前仍是 `mcr-wmo2006-stage1`。

## 现场与测量边界

- 本机：Apple M5、10 个逻辑 CPU、32 GiB RAM、macOS arm64；OCaml 5.5.2，
  Dune 3.24.2，Python 3.12.15。使用 `dune build @all @ffi` 默认 profile，未额外启用 release。
- 远端 `desk`：Ryzen 9 3900X、12 核/24 线程、约 62 GiB 可用总内存、RTX 2080 SUPER 8 GiB。
  PyTorch 2.14.1+cu126。24 个 teacher 数据生成进程各占约一个逻辑 CPU，load average 约 24。
  GPU 利用率 0%，占用 16 MiB；系统内存已用约 6.4 GiB，swap 未使用。
- 远端已有任务持续运行。本次没有终止、重启或覆盖它们；性能改动只在本地构建，未同步到远端。
- 当前应用进程直接 SSH 返回 `No route to host`，通过已有 tmux server 新建独立短时会话可连接。
  这不表示远端关机。采集脚本见 `benchmarks/audit_remote.sh`。

## 本地 teacher 数据路径

单进程、batch=1，`qualified-tenpai`，种子 `12000000..12000019`，20 局、1,584 次决策。
测量包含 JSON 传输、实际观察编码、合法性检查和轨迹摘要，不包含 NPZ 压缩写盘。

| 阶段 | 原实现秒数 | 缓存后秒数 |
| --- | ---: | ---: |
| observe（包含弃牌 hints） | 7.345 | 5.908 |
| teacher | 7.613 | 0.582 |
| Python 特征编码 | 0.081 | 0.072 |
| step（包含校验、规则和结算） | 0.021 | 0.017 |
| 总墙钟时间 | 15.107 | 7.013 |
| 决策/秒 | 104.85 | 225.85 |

原实现 observe + teacher 占总时间约 99%。C ABI 目前仍携带 JSON，但本次最显著的成本
是 hints 与 teacher 重复求结构向听/进张，不能将全部耗时归因于 Python 或 FFI。

已给 `Shanten.of_counts` 增加最多 32,768 项的进程内缓存，键包含副露数量和复制后的
34 种牌计数；只缓存纯结构计算，不缓存牌墙、对手暗手、算番上下文或可变数组。
满容量清空后重新填充，内存有界；多进程各自持有缓存。
保留 `of_counts_uncached` 递归参考实现，1,500 组随机计数/副露数量做等价验证及可变输入回归。
没有修改动作、番种、计分或教师排序，因而没有升级规则/特征/动作版本。

第一次前后对照为 **2.15 倍**；第二次缓存版为 6.372 秒。JSON-lines 后备传输为 6.637 秒。
这几次测试的完整观察、特征、动作、step 返回和终局摘要均为：

`7502ee94d480a670c2859e8e9545e1eab1b249676f804f0998f6dabcaea3ecab`

样本较小且运行时间有波动，不据此宣称 JSON-lines 比原生更快，也不将 2.15 倍直接外推到远端、
所有教师、完整 MCR 或 PPO。改后两种本地传输一致不等于 WASM 一致性已经通过。
原始结果保存在 `benchmarks/env-*.json`；`env-after-provenance.json` 另外记录源码和后端文件 SHA256。

## 远端 PPO 小样本

使用现有 `ppo-discard-closed-v6-38k.pt`，模型 295,035 个参数、隐藏层 256。
取种子 `12100000..12100003`，对手和 scaffold 都为 `qualified-tenpai`。
CPU 单 worker、PyTorch 单线程采样，在原有 24 个生成进程运行期间测量：

- 4 局产生 65 条学习决策：7.716 秒。
- 同批数据，预热后 4 epochs、minibatch 配置 512（实际只有 65 条）：CPU 更新 0.0222 秒；
  CUDA 更新 0.0239 秒；CUDA 峰值张量分配 25.59 MiB，不包含全部驱动/context 占用。
- CPU/CUDA 各自重载同一 checkpoint 后做预热和更新，结果仅作为吞吐测试，未保存模型。

这一小批次约 99.7% 的“采样+CUDA 更新”耗时在采样端。它不能代表正式 480 局批次，
也不能据此认为大批次 CPU 训练一定更快。原始输出见 `benchmarks/remote-ppo-20261026.txt`。

PPO 已新增 `rollout_seconds`、`update_seconds`、每秒局数和每秒学习样本数。
CUDA 计时边界显式同步；rollout 包含进程启动/结果传输，update 包含张量构造/传输，
两项都不包含 checkpoint 写盘。另去掉了每个学习决策的第二次 Python 特征编码。

本地实跑两进程、2 updates × 4 局、每次 1 PPO epoch：损失和权重有限，权重确实变化。
采样分别为 0.934 / 1.212 秒，更新为 0.0229 / 0.0019 秒。
证据在 `benchmarks/ppo-local-smoke-20261026.json`，临时 checkpoint 在 `/tmp`，不是发布模型。

## 下一步优先级与其他问题

1. **完整规则优先于扩大训练。**完整番种组合/排斥、16 手整场和 WASM 一致性仍未验收。
   `State.draw_source` 只有单个枚举，花补会覆盖前一来源，尚未保存 AGENTS 要求的完整补牌来源链。
2. **断点恢复尚不完整。**PPO 保存 optimizer，但 `--init` 只载入模型，新建 optimizer，
   从 update=1 开始；未保存完整 RNG 状态/配置。这是 warm start，不是精确 resume。
3. **继续优化 CPU hints。**缓存后观察仍占主要时间。可用带必要面子/雀头状态的花色查表替代
   重复递归，必须逐项对照参考算法；不能删除输入 hints 或合法动作来冒充加速。
4. **批量环境与持久 worker。**目前没有真正的 `stepBatch/encodeBatch`；PPO 每次更新重建
   spawn Pool，单局单观察推理，返回大量 Python dict。正式批次应继续计时，随后实现持久 worker、
   批量数组传输和批量推理，保证每批冻结行为权重及 RNG/玩家边界。
5. **24 workers 不等于最优。**3900X 是 12 个物理核；应在现有任务结束后做 8/12/16/24 worker
   同种子吞吐测试，当前没有用干净的扩展测试证明 24 最优。
6. **BC 另需测数据管道。**按样本做花色增强与每批 `.cpu()` 指标同步可能限制 GPU 供给，
   当前尚未测量完整 BC epoch，不能对其 GPU 占比作结论。

已有 30,000 局生成任务在审计时仍未结束：抽查 shard 0/7/8/23 分别到 620/600/380/360，
各目标 1,250 局，最终 NPZ/meta 均为 0 个。必须等 24 对文件完成并做数据契约验证后才进入 BC。
本次没有采用 `qualified-best` 或运行其正式消融；构建通过不代表它强于现有教师。

现阶段不需要买 GPU。只有在 CPU 采样/数据供给改善后，正式批次的 update 明显主导墙钟时间，
或实际发生显存不足，再按测量结果选择升级；如果采样继续主导，优先考虑 CPU 实现和物理核吞吐。

## 复现与验证

```sh
eval "$(opam env --switch=mahjong --set-switch)"
dune build --root ocaml @all @ffi
dune runtest --root ocaml --force
uv run python training/profile_env.py --games 20 --output /tmp/env-native-new.json
MAHJONG_FFI_SERVER="$PWD/ocaml/_build/default/mahjong_ffi/server/mahjong_ffi_server.exe" \
  uv run python training/profile_env.py --games 20 --output /tmp/env-server-new.json
uv run ruff check training
uv run pytest -q training/tests
```

profile 工具拒绝覆盖已有报告。若 uv 默认缓存目录不可写，可设置 `UV_CACHE_DIR=/tmp/mahjong-uv-cache`。
本次 OCaml 21 项、Python 110 项及 ruff 均通过；Python 有 4 条已有 ONNX exporter 弃用警告。
多进程 smoke 首次被沙箱的 `torch_shm_manager` 限制阻止，获执行环境授权后重跑通过。
未执行完整 MCR 验收、远端优化版吞吐、正式批量 BC/PPO、新 holdout 或网页测试。
