# 展销会排班问题一、二、三计算代码

本目录提供论文问题一、二、三的完整可复现求解链。

问题一、二采用：

> 严格读取附件 → 自动生成合法班型 → 日内整数覆盖 → 解析确定招聘规模 → 最大流安排休息日 → 员工—班次确定性映射 → 员工级反算校验 → 完整 MILP 独立复核。

问题三采用：

> 规则分解与公共盲区证明 → 八场景 SCIP 字典序优化 → 同日跨组 A/B 实验 → 全职/兼职人员池 → 最大流安排全职休息日 → 稳定槽位映射 → 员工级反算与 CP-SAT 复核。

`solve_q3_test.py`、`solve_repair_43.py`、`solve_q2.py` 和
`build_verified_results.py` 是旧版实验脚本，标记为 legacy，不会被任何正式
入口调用，其中的绝对路径和 OR-Tools 线性求解器写法不代表当前主链。

## 环境

建议 Python 3.11 或更高版本：

```bash
python -m pip install -r train_1/requirements.txt
```

正式结果使用 PySCIPOpt 调用 SCIP 求解全部整数规划；SciPy/HiGHS 保留为可选后端。整数最大流由项目内的确定性 Dinic 算法计算。OR-Tools 仅用于额外的 CP-SAT 独立复核；未安装 OR-Tools 时，问题一、二主流程与完整 MILP 仍可运行，此时 CP-SAT 复核会在 JSON 中明确记录为 `SKIPPED`。

问题三正式入口必须同时安装 PySCIPOpt 与 OR-Tools。SCIP 负责宏观整数规划，
CP-SAT 负责固定人员规模后的独立员工池可行性复核；任一依赖缺失都会直接
报错，不会回退或把 `SKIPPED` 记为通过。

## 数据

原始需求文件默认位于：

```text
train_1/data/附件1.xlsx
```

程序不修改附件，也不在源码中抄写需求。输入必须具有 10 个日期、每天 11 个小时段和 10 个小组，共 1100 个正整数需求单元。

## 一键运行

从仓库根目录运行：

```bash
python train_1/code/run_modeling.py \
  --data train_1/data/附件1.xlsx \
  --output train_1/paper_output \
  --solver SCIP
```

如需用 HiGHS 复算：

```bash
python train_1/code/run_modeling.py \
  --data train_1/data/附件1.xlsx \
  --output train_1/paper_output \
  --solver HiGHS
```

程序不会静默回退求解器。请求 SCIP 但未安装 PySCIPOpt 时会直接报错并返回非零退出码；结果中的 `requested_solver`、`actual_solver`、`actual_solver_version` 和 `solver_fallback_used` 可用于核验实际后端。

问题三单独运行：

```bash
python train_1/code/run_q3_modeling.py \
  --data train_1/data/附件1.xlsx \
  --output train_1/paper_output \
  --solver SCIP
```

该入口固定运行 S0--S7。S0、S1 必须由 SCIP 返回不可行；S2--S7 的每一层
字典序目标都必须达到 `OPTIMAL` 且相对间隙为 0。

## 测试

安装 pytest 后：

```bash
pytest train_1/code/tests -q
```

仅使用 Python 标准库测试运行器也可以执行同一测试集：

```bash
python -m unittest discover -s train_1/code/tests -p 'test_*.py' -v
```

端到端测试会运行两次完整主链，并比较以下核心 CSV 的 SHA-256：

- `q1_employee_schedule.csv`
- `q1_hourly_coverage.csv`
- `q2_employee_schedule.csv`
- `q2_hourly_coverage.csv`

论文图测试还会连续生成两次 PNG、PDF、SVG，并逐文件比较 SHA-256，
以保证同一环境下重复运行结果完全一致。

## 代码结构

| 文件 | 职责 |
|---|---|
| `data_loader.py` | 严格读取和验证 Excel |
| `shift_patterns.py` | 自动生成 10 种合法班型及覆盖矩阵 |
| `milp_utils.py` | PySCIPOpt/SCIP 与 SciPy/HiGHS 双后端整数规划封装 |
| `daily_cover.py` | 100 个日内覆盖模型及解析人数下界 |
| `roster_flow.py` | 确定性 Dinic 最大流和休息日分配 |
| `schedule_mapping.py` | 员工与匿名班次槽位的稳定映射 |
| `verification.py` | 员工级、班型级、逐小时覆盖反算 |
| `solve_core_and_roster.py` | 问题一、二主构造 |
| `verify_full_milp.py` | 完整聚合 MILP 独立复核 |
| `verify_with_cpsat.py` | 可选 CP-SAT 独立复核 |
| `build_q1_q2_figures.py` | 从 CSV/JSON 校验并生成问题一、二的三幅论文主图 |
| `run_modeling.py` | 统一命令行入口和结果写出 |
| `build_two_stage_visualization.py` | 读取新员工表生成两阶段示意图 |
| `q3_patterns.py` | 枚举严格/一小时休息全职班型与午间兼职班型，生成盲区证明 |
| `q3_models.py` | 用 PySCIPOpt/SCIP 求解 S0--S7 及全部字典序目标 |
| `q3_roster.py` | 最大流分配全职休息日并稳定映射全职/兼职槽位 |
| `q3_verification.py` | 从员工表反算覆盖、跨组统计和 CP-SAT 复核 |
| `q3_figures.py` | 从正式结果生成问题三三幅论文图 |
| `run_q3_modeling.py` | 问题三正式统一入口和结果写出 |

## 输出

输出根目录为 `paper_output/`：

- `tables/`：班型、日内最优、问题一/二聚合方案、最大流、员工排班和逐小时覆盖 CSV；
- `results/`：数据验证、问题一/二总结果、冗余说明、完整 MILP 与 CP-SAT JSON；
- `logs/`：数据、主运行、完整 MILP 和测试日志；
- `figures/q1_q2/`：问题一、二三幅主图的 PNG、PDF、SVG；
- `figures/q3/`：问题三公共盲区、跨组 A/B 和混合人员构成图；
- 项目根目录 `figures/`：上述论文图的同名副本，可直接由 LaTeX 引用。

问题三核心输出为：

- `q3_scenario_comparison.csv`：S0--S7 状态、人员规模、首层目标最优界和间隙；
- `q3_fulltime_employee_schedule.csv`、`q3_parttime_employee_schedule.csv`：所选总人数最优方案的员工级排班；
- `q3_hourly_coverage.csv`：1100 个需求单元反算结果；
- `q3_cross_group_summary.csv`、`q3_group_transition_matrix.csv`：最低跨组频率及方向；
- `q3_model_results.json`、`q3_verification.json`：确定性模型结论与验收；
- `q3_solver_run_metadata.json`：每个场景与最大流的实测运行时间。

`q3_model_results.json` 明确区分总人数最优方案与兼职班次最少优先方案。前者
直接回答最少总招聘人数，后者体现将兼职班次控制在公共盲区理论下界的管理
政策，二者不得混写。

只重新生成论文图而不重复求解时，从 `train_1/` 运行：

```bash
python code/build_q1_q2_figures.py
```

脚本优先使用 Source Han Sans SC、Noto Sans CJK SC、Microsoft YaHei 或
SimHei。若系统缺少这些字体，会明确警告并使用
`assets/fonts/NotoSansHans-Regular.otf`，因此交付图仍能正常显示中文。

`run_modeling.py` 遇到 Excel 结构错误、求解失败、最大流不足或覆盖缺口时会返回非零退出码，并打印明确错误；不会静默跳过异常。
