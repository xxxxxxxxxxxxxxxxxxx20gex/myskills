# BDC-CLIP 案例：来源、图形对象与已知风险

这是本 skill 的风格来源，不是所有项目的结构模板。以下为 2026-09-23 整理时的实现线索；再次作图时检查当前文件。

## 案例资源

相对本 skill 文件夹：

- 参考图：`../assets/bdc_original_figure2_reference.png`
- 矢量示例：`../assets/bdc_three_paths_editable.svg`
- 预览／PDF：同名 `.png`、`.pdf`
- 确定性绘图源：`../assets/render_bdc_three_paths_editable.py`
- 当前模型：`../trainers/bdc_clip.py`
- 原论文文本：`../bdc.md`

原论文图注说明，为简化图面省略了视觉分类器。不能由主图只画两部分，就认定 BDC-CLIP 原模型只有两路 logits。

## 当前代码对应关系

| 部分 | 核对入口 | 图上表达 |
|---|---|---|
| 双编码器 | `image_encoder`、`text_encoder` | 两个独立编码器，各自输出被分支复用 |
| cosine 路径 | `logits_cos_vl` | 时间平均的 CLS 与 EOS 对齐 |
| GLTBA | `token_late_interaction()` | patch／word 匹配、聚合、残差增强 cosine logits |
| BDC-VL | `video_bdc_adapter()`、`text_bdc_adapter()` | 视频和文本表示分别进入归一化与点积 |
| 当前文本投影 | `text_bdc_projection(eos_token)` | EOS → Text Projection；不是原论文完整 Text BDC Adapter |
| 原视觉分类 | `vision_bdc_head` 及 downstream 版本 | 同一 Video BDC 向量接分类器 |
| SMCD | `MomentProbingHead` | CLS 语义分类 + patch 跨组统计分类，帧内融合后时间平均，残差加入 BDC 分类 logits |

SMCD 的矩探测借鉴 Moment Probing；GLTBA 的历史记录涉及 Video-ColBERT 风格 late interaction。新增到项目的适配与原论文机制应区分，不能通过改名暗示核心算子均为原创。

默认图曾使用“GLTBA 仅预训练、SMCD 预训练与下游均使用”的阶段说明。这是特定方案的条件；代码支持其他开关，不能原样套用到所有实验。

## 应继承的优点

- 原有计算路径保留，新增模块用珊瑚色大框包围；读者可以同时看出接入位置和模块内部变化。
- 外层中文、内部算法英文，图例解释 Token、矩阵和来源端口。
- 用矩阵与条带说明“局部特征 → 统计／相似度表示 → logits”。
- 两个残差加号与最终 Softmax 融合分开，避免把不同层次的融合混为一体。

## 不应继承的瑕疵

这些是本次迭代暴露的问题，不应把旧预览当成无需核查的正确模板：

- 生成图曾把独立编码器合成 `Shared CLIP encoders`，并把文本走线接向视觉分类路径。
- 曾将 Video BDC 与文本表示串联，而正确关系是并行输入相似度。
- 对位图直接覆盖乱码曾擦断 SMCD 框边；位图修补不适合作为长期编辑源。
- 翻译和改符号可能只改到部分位置：旧脚本曾保留左侧端口 `E`，而分支使用 `T`；帧维度写 `T`，图例却改为 `F`。复用时统一定义与所有引用。
- 标签从短词扩展到 `Patch Token` 后，箭头可能仍从旧位置出发而穿过文字。必须同步改箭头起点或标签位置。
- 跨组协方差不应强制画成对称矩阵，也不能把协方差图标直接等同于最终分类分数。

本 skill 记录制作方法；既有图形是否需要进一步修正，应按用户当次的制图任务处理。
