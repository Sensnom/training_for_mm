# 第4题第一至三问修订源码

## 内容

- `03-q1.tex`: 第一问几何复核模型
- `04-q2.tex`: 第二问候选正文（尚未验收）
- `writer/q2_critique.tex`: 对教师第二问方案的客观取舍
- `writer/05-q3.tex`: 第三问物理先验鲁棒多目标模型
- `q1_geometry.py`, `q2_closed_loop.py`, `q3_model.py`: 可重复计算脚本
- `q1_results.csv`, `writer/q2_results.csv`, `writer/q3_results.csv`: 计算结果
- `writer/figure/`: 论文图和优化图

## 运行

使用 Python 运行 `q1_geometry.py`、`q2_closed_loop.py`、`q3_model.py`。问题二采用单腔开放系统零维循环模型：端口流动、Wiebe 放热、壁面传热、泄漏与FMEP均进入1080度偏心轴循环积分。其16个AIE 225CS扭矩点是手工数字化候选点，仅用于相似机型条件下的参数标定；它们并非题设发动机台架实测数据，拟合误差仅为样本内诊断。为避免16点扭矩数据对8个参数的不可辨识，端口面积、换热、燃烧持续期和进气恢复等6个量固定为提交的工程先验，只对燃烧效率和FMEP尺度做固定三起点、1度RK4拟合。为兼顾确定性与计算量，程序先进行7×7个精确ODE节点的参数筛查，拟合二次响应代理后做有界多起点最小二乘，并将每个候选重新代回精确ODE，以精确ODE成本选择结果；每个起点的状态、成本与参数移动均写入 `q2_run_metadata.json`。当前选择的FMEP尺度达到其人为上界1.80，说明手工数字化源曲线不能独立识别该损失参数，故不能把该拟合解释为唯一物理标定。所有Q2工况统一以收敛1080度循环起点的fresh charge推得 `mfuel_per_cycle`，并在该循环的RK4阶段内固定；因此 `eta_b=P/(mfuel_per_cycle*LHV*n/60)`，BSFC也使用同一 `mfuel_per_cycle`。基准、31点扫描与0.5度细化均由同一 `simulate` 返回字段计算，metadata中含程序化一致性检查。问题三仍须独立审查。

Q1 的实际脚本路径为 `q1_geometry.py`（不在 `writer/` 下）。从本目录的父目录执行：`python 第4题第一二三问修订源码/q1_geometry.py`。该命令会创建/覆盖 `q1_results.csv`、`figure/q1_corrected_volume_cr.png` 与 `q1_run_metadata.json`。

## 关键结果

- Q1（仅限已批准圆弧理想几何）: `Vmin=40.6603 cm^3`, `Vs=409.1970 cm^3`, `CR=11.0638`；实体接触边界为 `d=150 mm`，`159.872613647263 mm` 仅为非物理代数延拓中的 `Vmin=0` 根。
- Q2（generated，待独立验收）: 在6000 r/min、128度重叠角条件下运行 `q2_closed_loop.py`；输出会更新 `q2_closed_loop_results.csv`、`q2_overlap_response.csv`、`q2_cycle_trace.csv`、`q2_three_chamber_torque.csv`、`q2_run_metadata.json`与三幅Q2图。该功率是跨机型假设下的条件模型预测，不能称为题设发动机实测最大功率；20度扫描端点不是实际最优重叠角结论。
- Q3: 鲁棒推荐 `d=149.28 mm`, `alpha_ov=20.36 deg`, `theta_ign=18.74 deg BTDC`, `theta_EOI=600.60 deg`, `lambda=1.006`；先验预测 `P=45.84 kW`, `eta_b=31.21%`, `BSFC=265.2 g/(kW h)`。
