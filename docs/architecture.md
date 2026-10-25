# 架构与数据契约

## 当前链路

1. `ocaml/mahjong_core` 是唯一规则实现，负责状态机、合法动作、和牌、算番、结算、观察和确定性历史。
2. `ocaml/mahjong_ffi` 把核心编译进原生对象，并通过 C ABI 或 JSON-lines 子进程调用同一个 OCaml dispatcher。
3. `training/mahjong_ai/engine.py` 用 `ctypes` 加载共享库，或在设置 `MAHJONG_FFI_SERVER` 时驱动 JSON-lines 子进程；Python 只负责训练、数据与评估，不复制规则。
4. `training` 使用 PyTorch 做 BC 和后续 masked PPO，输出 checkpoint、指标和后续 ONNX 模型。

## 版本契约

- `ruleset_id`: `mcr-wmo2006-stage1`
- 原始 `observation_version`: 1
- `feature_encoding_version`: 6（包含公开副露牌种、逐弃牌向听/进张，以及满足 8 番门槛的有效听张与期望支付提示；修正和牌张重复计数与弃牌后未见数重复扣减）
- `action_catalog_version`: 1
- 动作数量：122
- 当前特征数量：771

动作 ID 中，非法动作由状态、座位和当前窗口共同决定；模型只能通过 mask 选择。模型输出编号本身不保证跨规则版本稳定，加载时必须比对 manifest/checkpoint 中的版本。

## C ABI

共享库只暴露以下入口：

```c
char *mahjong_ffi_call(const char *json_request);
void mahjong_ffi_free(char *response);
int mahjong_ffi_abi_version(void);
```

请求和响应均为 JSON。错误通过 `{"ok":false,"error":"..."}` 返回，不允许静默改写成其他动作。OCaml 5 运行时使用 pooled embedding；当前一个 Python 进程内由 Python 锁串行调用，并行训练应使用多个进程。

## JSON-lines 传输

`mahjong_ffi_server` 从标准输入逐行读取同样的 JSON 请求，并把 dispatcher 返回的一行 JSON 写回标准输出。它用于无法安全加载共享库的环境、后备运行以及跨传输一致性检查；当前 Linux x86-64 原生库也已可用。每个 Python 工作进程持有自己的 server 子进程；server 退出或返回空响应会转为明确错误，不会静默重建状态。该传输与 C ABI 共用规则、动作目录、观察和结算实现。

## 启发式与 scaffold 口径

- `--heuristic-variant` 是候选席使用的教师策略。
- `--opponent-variant` 是另外三席使用的固定对手策略，默认 `default`，不得被候选变体隐式改写。
- `--scaffold-variant` 只控制学习模型在非学习决策上的兜底策略；评估报告会记录该值。仅学习弃牌时，胡牌和鸣牌仍由 scaffold 产生。
- 当前候选教师消融统一采用“候选席 vs 默认三席”；同策略四席自博弈的均值不能用于证明某个候选更强。

## 信息边界

`Observation.create state seat` 只包含该座位可见的信息：本人手牌与摸牌、场上明牌、副露公开信息、牌河、花牌计数、牌墙剩余数和合法动作。其他玩家暗手、未公开暗杠牌种、牌墙顺序和待公开响应选择不进入观察。coordinator 可以知道下一位需要决策的座位，但该调度信息不能并入策略特征。
