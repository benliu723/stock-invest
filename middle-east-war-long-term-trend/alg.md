# Actor / Factor / Weight 算法公式定义

## 总结
当前版本采用 `actor + actor_weight + factor + factor_weight + direction` 作为核心输入，并以统一的索引变量与函数记号定义长期方向判断算法。该算法的目标是：先为每个 factor 指定唯一方向，再通过 actor 权重与 factor 权重计算各方向总分，最终由最高总分确定长期主趋势。

该算法当前是一个方向加权汇总模型，而不是完整的博弈论均衡模型；其价值在于建立统一、严谨、可扩展的数学表达，为未来迭代提供稳定基础。

## 定义
设 actor 集合为：
\[
\mathcal{A}=\{\text{美国},\text{以色列},\text{伊朗}\}
\]

对任意 actor：
\[
a\in\mathcal{A}
\]

设 actor \(a\) 的 factor 集合为：
\[
\mathcal{F}_a
\]

对任意 factor：
\[
f\in\mathcal{F}_a
\]

设方向集合为：
\[
\mathcal{D}=\{\text{缓和},\text{僵持},\text{升级}\}
\]

定义权重变量：
\[
AW_a\in[0,1]
\]
表示 actor \(a\) 的权重；

\[
FW_{a,f}\in[0,1]
\]
表示 actor \(a\) 下 factor \(f\) 的权重。

定义方向标签：
\[
D_{a,f}\in\mathcal{D}
\]

表示 factor \((a,f)\) 的唯一主方向。

## 约束与函数
对任意固定的 \(a\in\mathcal{A}\)、\(f\in\mathcal{F}_a\)，定义方向选择函数：
\[
I_{a,f}:\mathcal{D}\to\{0,1\}
\]

其定义为：
\[
I_{a,f}(d)=
\begin{cases}
1, & D_{a,f}=d \\
0, & D_{a,f}\neq d
\end{cases}
\qquad d\in\mathcal{D}
\]

由于每个 factor 在 v1 中只允许一个主方向，因此有：
\[
\sum_{d\in\mathcal{D}} I_{a,f}(d)=1
\]

定义 factor \((a,f)\) 的贡献值为：
\[
C_{a,f}=AW_a\cdot FW_{a,f}
\]

## 总分与结论
定义方向总分函数：
\[
S:\mathcal{D}\to\mathbb{R}
\]

对任意 \(d\in\mathcal{D}\)，定义：
\[
S(d)=\sum_{a\in\mathcal{A}}\sum_{f\in\mathcal{F}_a} AW_a\cdot FW_{a,f}\cdot I_{a,f}(d)
\]

即：
- 所有 actor 的所有 factor 都参与累加
- 只有方向属于 \(d\) 的 factor 才对 \(S(d)\) 产生贡献
- \(AW_a\) 表示 actor 的全局影响力
- \(FW_{a,f}\) 表示 factor 在该 actor 内部的重要性

最终长期主趋势定义为：
\[
T=\arg\max_{d\in\mathcal{D}} S(d)
\]

即：
- 若 \(S(\text{缓和})\) 最大，则 \(T=\text{缓和}\)
- 若 \(S(\text{僵持})\) 最大，则 \(T=\text{僵持}\)
- 若 \(S(\text{升级})\) 最大，则 \(T=\text{升级}\)

## 输出映射与验证
长期形态映射固定为：
- `缓和 -> 低冲突缓和均衡`
- `僵持 -> 高压持久战`
- `升级 -> 失稳上行态势`

验证该算法时，至少覆盖以下情况：
- 当多数高权重 factor 的方向为 `僵持` 时，\(S(\text{僵持})\) 应最高
- 当高影响 actor 的高权重 factor 主要指向 `升级` 时，\(S(\text{升级})\) 应明显上升
- 当多个 actor 的高权重 factor 同时指向 `缓和` 时，\(S(\text{缓和})\) 应最高
- 当仅调整某个关键 \(AW_a\) 或 \(FW_{a,f}\) 时，结论应发生可解释变化

## 假设与边界
- v1 中每个 factor 只允许一个主方向
- v1 暂不处理 factor 之间的相互作用、冲突关系和反馈机制
- v1 当前是方向加权汇总模型，不是完整的博弈论均衡模型
- 该定义的主要价值是建立统一符号体系和可解释算法，为未来扩展关系层、策略层和收益层保留演进空间
