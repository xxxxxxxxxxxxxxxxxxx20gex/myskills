# 模型结构核对

只核查任务相关的模型与展开层级。以下是审图规则，不是用来覆盖当前实现的固定架构模板。

## 绘图前的结构契约

记录模型版本／代码入口、训练或推理场景、总图粒度、关键张量符号和有意省略的细节。节点表至少能说明每个模块的输入来自哪里、输出流向哪里。没有证据的关系标为待核实，不以配色或布局补全架构。

| 操作 | 必须确认 |
|---|---|
| Add／残差 | 两个输入的形状兼容，残差来自正确的子层输入；若需要投影或缩放，不能省略 |
| Concat | 拼接轴及输出尺寸，不用加号代替拼接 |
| Attention | Q、K、V 来源及序列长度，mask 类型，输出沿 Query 长度排列 |
| 重复层 | 重复范围包含完整子层；层间传递关系明确；参数共享与独立参数区分 |
| 多消费者 | 从同一表示明确分叉；复制显示时使用同名端口并注明复用 |
| 训练分支 | loss 的预测输入与监督来源、冻结模块和 stop-gradient 按实际实现标注；冻结不自动等于截断梯度 |

维度只标在跨模块接口和改变形状的位置；批维可统一省略并说明。不要在每根短箭头上重复尺寸。

## Transformer

先确定 Encoder–Decoder、encoder-only 或 decoder-only，以及 Pre-LN／Post-LN。不要把一种变体的图称为所有 Transformer 的通用实现。

以原始 Encoder–Decoder Post-LN 为参考（Vaswani et al., 2017，论文第 3.1–3.3 节与 Figure 1）：
<https://arxiv.org/abs/1706.03762>

- Encoder 每层含 self-attention 与 FFN，各自都有残差和 LayerNorm；Decoder 每层含 masked self-attention、cross-attention 与 FFN，各自也都有残差和 LayerNorm。
- Post-LN 子层关系为 `z = LayerNorm(x + Dropout(Sublayer(x)))`。若用圈加号表达相加，后续框写 `LayerNorm`；若用合并框 `Add & Norm`，让两个输入直接接该框。不能重复表达相加。
- Pre-LN 则先对输入归一化再送子层，残差绕过子层；是否有栈末归一化以实现为准，不能只交换标签就当作完成转换。
- Self-attention 的 Q/K/V 来自同一序列 X，但分别投影：`Q=XW_Q, K=XW_K, V=XW_V`。不要写成投影后的 `Q=K=V`。
- Cross-attention 的 Q 来自 Decoder 前一子层，K/V 来自 Encoder 最后一层输出；同一 Encoder Memory 被各 Decoder 层读取。
- 源长度 n、目标长度 m，单头注意力权重形状为 `m × n`，输出为 `m × d_v`；self-attention 时对应长度相同。多头 concat 后还有输出投影。
- Causal mask 防止当前位置访问未来目标位置；padding mask 作用不同，按展示粒度说明。右移训练目标与逐 Token 推理区分，不将训练输入画成已知未来答案。
- `N×` 包含完整层及其残差／归一化；原始层间参数独立。Encoder 最终输出应由层末归一化引出，Decoder 最终表示再接词表投影和 Softmax。
- 总图可将注意力整体封装；如展开内部，保持 `QKᵀ / √d_k → Mask（适用时）→ Softmax → 与 V 相乘 → 多头拼接及输出投影` 的顺序。嵌入缩放、Dropout 等未展开的细节在图注列明。

## 其他常见结构

- 多模态：独立模态分别接编码器；确认参数共享、特征复用和对齐层级。双输入相似度不能画成两个表示依次转换。
- 多尺度／U-Net：skip connection 核对源层和目标层分辨率，标明 Add 或 Concat；采样和通道投影按实现放置。
- 辅助分支／融合：确认读取的是 Token、池化特征还是 logits，在哪里回接；分别表示特征相加、logits 融合、概率加权和 loss 加权。

## 沿边追踪验收

1. 从输入逐边追踪到输出，每条线的源点、终点、箭头方向与节点表一致。
2. 在每个残差／融合节点暂停，逐个数清语义输入；确认每条分支能追溯到有效节点或明确的复用端口。
3. 检查重复框内部是否漏掉末尾算子，输出是否接在框内最后一个操作之后。
4. 查公式与说明是否一致，再看形状是否支持该操作。未核实项必须在交付中说明。

回归示例：一个“原始 Transformer Post-LN”图若在 FFN 后只有加号、没有 LayerNorm，应判结构不合格；若框外留白或连线很好看，也不能抵消该缺陷。此示例用于审图，不要求所有模型必须采用 Post-LN。
