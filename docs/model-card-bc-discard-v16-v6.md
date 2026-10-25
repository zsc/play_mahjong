# 模型卡：bc-discard-v16-v6

## 身份与范围

- 本地 checkpoint：`training/checkpoints/bc-discard-v16-v6.pt`，3,553,727 bytes。
- SHA-256：`35a9443b472d1279de2fdf7faebb1d496dbe274c839c17bfe3806bc8aafd13a4`。
- 算法：行为克隆（BC），只学习 34 种标准弃牌；和牌、响应、吃碰杠与花牌仍由 OCaml 启发式处理。
- 该 checkpoint 未发布到网页；`training/checkpoints/` 是本地忽略目录。

## 契约

| 项目 | 值 |
| --- | --- |
| `ruleset_id` | `mcr-wmo2006-stage1` |
| `observation_version` | 1 |
| `feature_encoding_version` | 6 |
| `feature_size` | 771 |
| `action_catalog_version` | 1 |
| `action_count` | 122 |
| 网络 | 共享 MLP，hidden 256，policy/value 双头 |
| 推理选择 | 合法 mask 后的 argmax；value 不是胜率 |

特征为数量/统计通道，不是把打包整数当连续值。对手暗手、牌墙顺序和未公开暗杠牌种不进入输入。加载器会拒绝不同 observation、feature、action 契约的 checkpoint。

## 训练数据

- 数据：`training/data/v6-corrected-shards/`，8 个 NPZ 分片及 `.meta.json` 侧车。
- 种子：`1700000..1700999`，共 1000 局、78,314 个决策。
- 教师：当前 OCaml 结构向听/进张启发式，feature v6 语义。
- 训练：40 epoch，最佳验证损失 `0.758363`（第 32 epoch），训练 seed `20261102`。
- 增强：标准花色置换；验证集按完整对局种子分隔。
- 数据 SHA 汇总：`1d3c1ef3bdfe81871a3d20bca26a7bb88d1d9d170f66c38d619669f4385076a3`。

## 评估

评估使用 1600 局、种子从 `3000000` 起、座位 0/1/2/3 轮换、CPU 推理，训练/评估种子分离。对照为同版本 v6 启发式教师。

| 策略 | 平均净得分 ± 标准误 | 和牌率 | 放炮率 | 流局率 |
| --- | ---: | ---: | ---: | ---: |
| v6 教师 | -0.4525 ± 0.6851 | 22.44% | 18.31% | 8.44% |
| BC + teacher-optimal 护栏 | +0.1631 ± 0.6761 | 23.19% | 17.25% | 8.88% |
| BC，无护栏 | -4.2638 ± 0.5862 | 15.56% | 17.25% | 11.63% |

“teacher-optimal 护栏”表示只在教师同样认定为最优的等价弃牌之间让网络选择，因此这是复合策略。相对教师的配对差为 `+0.6156 ± 0.5972`，95% CI `[-0.5549, 1.7862]`，跨 0；当前不能宣称模型已统计显著地强于教师。

## 已知限制

- 规则实现仍不是完整 MCR；16 手整场、完整番种排斥和规范歧义认证尚未完成。
- 没有 WASM/ONNX 导出，也没有浏览器部署。
- 只控制一个座位并只学习弃牌；不能把本结果解释为四家统一 AI。
- 无护栏的纯网络评估明显退化，说明当前 BC 仍依赖教师动作约束。
- 训练数据与 checkpoint 默认不进入版本库，复现需重新生成数据。
