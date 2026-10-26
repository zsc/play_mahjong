# 四人 MCR 麻将 AI 训练与演示

本项目使用 OCaml 实现单一规则核心，Python/PyTorch 负责训练，通过 C ABI/ctypes、JSON-lines 子进程与 WASM 服务本地训练和浏览器。目标规则是 WMO 2006 Mahjong Competition Rules（MCR）。

> 当前仍是阶段一，不是完整 MCR。已有通过独立 6,400 局门槛的“PPO 模型 + 启发式保护”人测候选、ONNX 导出及浏览器人测网页；未证明强于 qualified 教师。完整番种排斥、补牌来源链和 16 手整场尚未完成。

本机可直接运行 `./scripts/play_candidate.sh` 开始中文终端对战，输入动作 ID，`q` 退出。
实际成绩、权重来源和限制见 [人测候选模型卡](docs/model-card-human-candidate-20261026.md)。

浏览器人测：`cd web && npm ci && npm run prepare:assets && npm run dev`，然后打开
`http://127.0.0.1:5173/`。提供人机对局、AI 观战、回放和真实训练记录，规则与推理均在本机 Worker 中执行。
完整启动、静态子路径构建和验证说明见 [浏览器人测](docs/browser-human-test.md)。

## 目录

- `ocaml/mahjong_core/`: 无 UI 的规则核心与测试
- `ocaml/mahjong_ffi/`: C ABI、JSON-lines 子进程与 WASM 导出
- `training/`: teacher 数据、网络、BC、评估和后续 PPO
- `web/`: 浏览器人机牌桌、AI 观战、回放、真实训练记录与 WASM Worker
- `docs/`: 规则基线、架构和真实进度

## 环境

本机已验证：

- macOS arm64，OCaml 5.5.2（opam switch `mahjong`），Dune 3.24.2
- `wasm_of_ocaml-compiler` 6.5.0
- Python 3.12（由 `uv` 管理），PyTorch 2.14.1
- Node.js 26.12.1、npm 11.20.0

新机器可执行：

```sh
brew install opam
opam init
opam switch create mahjong 5.5.2
eval "$(opam env --switch=mahjong --set-switch)"
opam install dune alcotest qcheck ctypes yojson zarith utop ocamlformat ocaml-lsp-server wasm_of_ocaml-compiler
```

## 规则测试与原生接口

```sh
eval "$(opam env --switch=mahjong --set-switch)"
cd ocaml
dune runtest
cd ..
./scripts/build_ffi.sh
```

共享库输出为 `ocaml/_build/default/mahjong_ffi/mahjong_ffi.so`。Python 进程内串行调用；并行采样使用多个进程。

Linux 上 `scripts/build_ffi.sh` 会使用 `-output-obj` 和 `libasmrun_pic.a` 构建可加载共享库；当前 Linux x86-64 环境已通过原生 ctypes 冒烟调用。若其他平台无法加载，可设置 `MAHJONG_FFI_SERVER` 使用下面的 JSON-lines 后备传输。

无法直接加载共享库的平台可改用同一 dispatcher 的 JSON-lines 子进程：

```sh
eval "$(opam env --switch=mahjong --set-switch)"
cd ocaml
dune build mahjong_ffi/server/mahjong_ffi_server.exe
cd ..
MAHJONG_FFI_SERVER="$PWD/ocaml/_build/default/mahjong_ffi/server/mahjong_ffi_server.exe" \
  uv run python training/evaluate.py --policy heuristic --games 40
```

两种传输都调用 `mahjong_ffi_dispatch`，规则、动作和结算不另写。

## Python 训练

```sh
uv sync
uv run pytest -q
uv run python training/generate_bc.py \
  --games 125 --seed-start 1700000 \
  --output training/data/teacher-v6-smoke.npz
uv run python training/train_bc.py \
  --data training/data/teacher-v6-smoke.npz \
  --discard-only --suit-augment \
  --output training/checkpoints/bc-discard-smoke-v6.pt \
  --epochs 10
uv run python training/evaluate.py \
  --policy model --model-scope discard --discard-guard teacher-optimal \
  --checkpoint training/checkpoints/bc-discard-smoke-v6.pt \
  --device cpu \
  --games 400 \
  --seed-start 3000000 \
  --output training/runs/bc-discard-smoke-v6-eval.json
uv run python training/export_onnx.py \
  --checkpoint training/checkpoints/bc-discard-smoke-v6.pt \
  --output training/exports/bc-discard-smoke-v6.onnx
```

训练数据必须与 `.meta.json` 侧车一起使用；`train_bc.py` 会拒绝 feature 契约不匹配的数据。`training/data`、`training/runs` 和 `training/checkpoints` 是大产物目录，默认不提交。发布模型时必须附带模型、规则、观察、动作和数据版本，以及真实评估记录。

正式长评估可按不相交种子分片，再用合并工具去重并重算指标：

```sh
uv run python training/merge_runs.py \
  --input training/runs/shard-0.json training/runs/shard-1.json \
  --output training/runs/merged-eval.json
uv run python training/compare_runs.py \
  --candidate training/runs/merged-eval.json \
  --baseline training/runs/teacher-eval.json
```

## 运行边界

- 规则和结算只在 OCaml 核心中实现；Python 不另写规则。
- teacher 是结构向听/进张启发式；BC 模型是否优于 teacher 必须由固定种子、轮换座位的正式结算评估决定。
- 当前全新 seed 段证据显示闭门教师明显强于默认鸣牌教师；仍须在最终 holdout 和模型训练中复核，不能把教师强弱直接当作 AI 能力。
- 训练数据生成和评估不读取隐藏手牌或牌墙顺序。
- 当前发牌数字流程不实现骰子开墙与物理“一三”流程，已记录为未完成项。

## 当前缺口

- 81 番完整金标准、全部组合/排斥关系和规范歧义认证
- 16 手整场与庄家/圈风轮转
- v6 语义下的 DAgger/PPO 增益、对手池、自博弈和冻结对手评估曲线
- ONNX 的 WASM/WebGPU 数值验证、可运行 WASM、浏览器对局、Worker 推理和 GitHub Pages 部署

完整规则来源与边界见 `docs/rules.md`，技术契约见 `docs/architecture.md`。

## 环境性能

2026-10-26 实测及算力建议见 [环境性能审计](docs/env-performance.md)。结构向听使用有界缓存；
PPO 日志区分采样与参数更新耗时。用真实对局复测（输出路径必须不存在）：

```sh
uv run python training/profile_env.py --games 20 --output /tmp/mahjong-env-profile.json
```

本轮已实现分块/增量向听、合并 JSON 调用、教师候选复用及 PPO 多局批量推理。
相对上一轮分块版本，远端同机采样基准为 2.386 倍吞吐。`--rollout-batch-size 1` 保留逐局采样，
默认 16 局合批；合批改变随机数消费顺序，checkpoint 会记录采样配置。

```sh
uv run python training/benchmark_sampling.py --mode ppo --batch-size 16 --output /tmp/batch-benchmark.json
uv run python training/generate_parallel.py --help
uv run python training/validate_dataset.py --help
uv run python training/train_bc.py --help  # --vectorized-batches --suit-augment
uv run python training/train_ppo.py --resume training/checkpoints/your-run.pt \
  --output training/checkpoints/your-run-resumed.pt --updates 80
```

`--resume` 恢复优化器、随机状态及保存的训练/采样配置，`--updates` 为累计目标；
`--init` 是新分支 warm start。大数据、所有历史 checkpoint 和完整日志保留在训练产物目录。
