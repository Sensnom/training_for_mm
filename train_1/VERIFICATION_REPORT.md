# 问题一、二本地计算与验证报告

生成日期：2026-07-24

## 实际运行命令

```bash
python code/run_modeling.py \
  --data data/附件1.xlsx \
  --output paper_output \
  --solver SCIP
```

全部日内整数覆盖模型、问题一与问题二的精确人数模型，以及完整聚合 MILP 均通过 PySCIPOpt 调用 SCIP 求解。运行记录为 `requested_solver=SCIP`、`actual_solver=PySCIPOpt/SCIP`、`solver_fallback_used=false`。OR-Tools 仅用于额外的 CP-SAT 独立可行性复核。

全量测试：

```bash
python -m unittest discover -s code/tests -p 'test_*.py' -v
```

结果：19 项测试全部通过，0 failures，0 errors。测试包括 SCIP 后端最小整数规划，以及统一入口调用 SCIP 且不发生求解器回退的回归检查。完整输出见 `paper_output/logs/pytest.log`。测试文件与 pytest 兼容，本地使用 Python 标准库 `unittest` 执行同一测试集。

语法检查：

```bash
python -m compileall -q code
```

结果：退出码 0。

## 数据与环境

- 数据：`data/附件1.xlsx`
- SHA-256：`1eae47338d7b1e586e902aec7591d01c1218cd52f1781a27f071c1cfe92e1acf`
- 张量：`(10, 11, 10)`，共 1100 个正整数需求单元
- Python：3.12.13
- NumPy：2.5.1
- Pandas：2.2.3
- OpenPyXL：3.1.5
- PySCIPOpt：6.2.1
- SCIP：10.0.2
- SciPy/HiGHS：1.17.0（可选复算后端，本次正式结果未使用）
- 主最大流：项目内确定性 Dinic 整数最大流
- OR-Tools：9.15.6755

## 问题一

- 各组最优编制：`39, 39, 43, 41, 44, 39, 42, 42, 43, 45`
- 总招聘人数：417
- 十组最大流：`78, 78, 86, 82, 88, 78, 84, 84, 86, 90`
- 十组最大流均达到 `2 × 组内员工数`
- 员工级记录：4170
- WORK：3336
- REST：834
- 每名员工：8 WORK + 2 REST，十天固定小组
- 逐小时覆盖：1100 个需求单元，缺口 0，最小松弛 0
- 完整聚合 MILP 独立目标：417，最优间隙 0

## 问题二

- 逐日最低工作人数：`214, 349, 314, 333, 349, 331, 363, 350, 325, 319`
- 逐日下界总和：3247
- 总招聘人数：406
- 实际逐日工作人数：`214, 349, 314, 333, 349, 331, 364, 350, 325, 319`
- 实际工作人日：3248
- 冗余工作人日：1，位于第 7 天
- 最大流：812，达到 `2 × 406`
- 员工级记录：4060
- WORK：3248
- REST：812
- 每名员工：8 WORK + 2 REST；每个工作日恰属一个小组
- 逐小时覆盖：1100 个需求单元，缺口 0，最小松弛 0
- 完整聚合 MILP 独立目标：406，最优间隙 0

## 确定性复核

端到端测试独立运行主链两次，下列核心 CSV 的两次 SHA-256 完全一致。最终交付文件的哈希为：

| 文件 | SHA-256 |
|---|---|
| `q1_employee_schedule.csv` | `4e634435708459f7b9680fae52ddbf52ac6da7fded29970c02954510df4492f7` |
| `q1_hourly_coverage.csv` | `3b9017f5989649ed18bc8208234de535039852654886c5ee2fd60eb3a92e150d` |
| `q2_employee_schedule.csv` | `028f258ab397f4ee14db97f2b3dd2cb0fe0da8a2d050866c6ac2f4b95eddf218` |
| `q2_hourly_coverage.csv` | `8ce91331611d197a45db1b3c6650997dfa9fcb32ea5397a06a0ea35e096718d1` |

## 可选复核与已知环境限制

- CP-SAT 独立复核已实际执行并通过：问题一十组均可行，问题二可行且逐日人数与主构造完全一致。结果见 `paper_output/results/cpsat_roster_verification.json`。
- 本报告开头的 19 项 SCIP 测试是正式求解交付时的完整运行记录。当前容器再次单独运行 PySCIPOpt 后端测试会触发底层 `Bus error (135)`；本次绘图增量验收未覆盖正式 SCIP 结果文件，也未将临时 HiGHS 端到端结果写入 `paper_output`。

## 问题一、二论文图增量验收

增量验收日期：2026-07-25。

新增脚本 `code/build_q1_q2_figures.py` 从 CSV/JSON 读取并校验数据，生成三幅论文主图：

| 图 | 数据来源 | 核心校验 |
|---|---|---|
| `fig_q1_group_staff` | `q1_group_results.csv`、`q1_model_results.json` | 10 组编制逐项一致，总和等于 417 |
| `fig_q2_daily_lower_actual` | `q2_daily_lower_bound.csv`、`q2_daily_actual.csv`、`q2_model_results.json` | 下界总和 3247，实际 3248，仅第 7 天增加 1 |
| `fig_q1_q2_staff_comparison` | 两问结果 JSON | 动态计算减少 11 人、降幅 2.64% |

每幅图均已生成 PNG、PDF、SVG，输出到
`paper_output/figures/q1_q2/`，并复制到 `figures/`。PNG 实测分辨率为
300 dpi；PDF 内嵌 Noto Sans Hans 中文字体；SVG 将文字转为路径，避免目标
机器缺少字体时出现乱码。

系统未安装任务书指定的四种首选中文字体，因此脚本按要求产生 warning，并
使用项目内 `assets/fonts/NotoSansHans-Regular.otf`。三幅 PNG 和 PDF
渲染结果均已人工检查，中文、数值、图例和注释正常，无明显遮挡。

绘图增量回归命令运行 25 项测试，结果为 `25 tests, 0 failures,
0 errors`。其中新增 8 项测试覆盖：

- CSV/JSON 正常加载与逐项一致性；
- 问题一总和不一致时拒绝输出；
- 问题二多于一个差异日时拒绝输出；
- 三图三格式写出与论文目录复制；
- 比较差值和百分比从 JSON 动态计算；
- 连续两次生成的 9 个图文件 SHA-256 完全一致；
- 三幅主图不设置图内标题，由论文 LaTeX 图注统一承担标题；
- 问题一柱状图仅最高值使用橙色，其余 9 个柱统一使用蓝色。

此外已完成：

- `python -m compileall -q code`，退出码 0；
- PNG/PDF/SVG 文件类型检查；
- PDF 字体嵌入检查；
- PDF 页面渲染检查；
- 使用 XeLaTeX 对三幅 PDF 执行最小 `\includegraphics` 编译，退出码 0。
