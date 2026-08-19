# 第7题证据状态总表

| 对象 | 状态 | 当前可写结论 |
|---|---|---|
| 题面边界语义 | verified | X/Y/Z 真实越界片段回迁；同一 physical ID 保持；未越界独立介质不额外做全局 minimum-image 接触 |
| Q1 严格回迁组件重构 | verified | 仅接受 X 对侧端点精确一致、方向完全共线、合计轴长 5000 nm 的组件；三组分别有 2/5/63 个，三组均导通 |
| Q2 | verified under Assumption A | 中心 iid 均匀、A 方向 iid 各向同性、介质独立时，四个给定填充量均在六位小数下报告 1.000000 |
| Q3 | verified under Assumption A | N_A*=8，精确体积分数约 0.0113097336%，题面两位报告 0.01% |
| Q4 全局最优性 | verified under Assumption A | (N_A,N_B)=(0,57)，C_min=0.0955044167 元，Phi_B=0.1910088333% |
| Q4 Stage 5 B-only 全图 MC | verified | 三个 M=10^6 新随机种子均将 57B 与 56B 分隔在 0.90 阈值两侧 |
| 旧 528 / 0.7464% / (528,0) | rejected | 旧 X 裁剪 + Y/Z 全局最小镜像结果不得复用为正式结论 |

## 敏感性增强验收

| 对象 | 状态 | 当前可写结论 |
|---|---|---|
| $\delta\in[0,9]$ nm | verified analytic | 其他口径固定时，7A必要事件上界始终<0.90，8A直接下界>0.90；七个更便宜Q4成本前沿中(0,56)始终最强且上界<0.90，57B直接下界>0.90 |
| A方向分布 | verified sensitivity / high-impact | 完全沿X时严格平端圆柱 $p_A^D=0.5$，4A即可使直接下界>0.90；完全横向 $p_A^D=0.006$。方向改变后需重新全局搜索 |
| 边界语义对照 | verified scope-limited | 只比较自短路分量；不将不同语义下的完整网络概率混为一谈 |
| Pareto展示 | verified visualization | 纵轴为直接自短路解析下界；不可替代Q4整数全局最优证明 |
