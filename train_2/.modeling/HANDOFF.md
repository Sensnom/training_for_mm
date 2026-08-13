# Project Controller 交接摘要

> 更新时间：2026-08-14  
> 项目目录：`/home/Sparkle/programming/tex_profiles/train/train_2`  
> 当前阶段：问题一主体与检验已完成；问题二条件模型主体及数值检验已写入，但跨机型物理预测仍未验收；问题三尚未开始正式写作。

## 0C. 2026-08-14 问题三条件设计返修、验收与写入

用户确认没有遗漏的目标机台架材料，并批准按条件设计路线返修。旧Q3的44.93 kW、正负15%统一缩放、159.873 mm几何上界和未经ODE支撑的峰压代理均已废弃。新程序`q3_conditional_design.py`直接调用最新版Q2开放系统ODE：400个七维拉丁超立方点全部循环收敛，以极端随机树只作50000候选筛选，随后对前40候选的5种真实输入扰动情景执行200次ODE复排，并以1度步长回代推荐点。

条件推荐为`d=149.601853 mm`、`overlap=23.261230 deg`、`ignition=29.745066 deg BTDC`、`EOI=591.681525 deg`、`lambda=0.968920`；1度ODE给出`52.763364 kW`、`eta_b=0.372483`、`BSFC=222.180812 g/kWh`、`pmax=6.977358 MPa`和`Tmax=2922.083 K`。0.5度功率相对差约`1.84e-4`。数值链、几何边界、情景传播、输出哈希和步长细化已由`model-verification-writer [问题三]`验收。

限制必须保留：目标机台架仍缺失；Q2摩擦尺度命中上界；代理峰压留出集R2仅0.7824；推荐的直径、点火角和重叠角贴近边界，不同种子/权重下重叠角约在25.35--70.86度变化。因此Q3数值只可称指定候选池、情景与权重下经ODE复排的条件试验起点，不得称目标机实测、全局最优、法规排放或寿命预测。问题三主体和verification区域均已按此边界写入。

## 0B. 2026-08-14 问题二数值检验写入

`model-verification-writer [问题二]` 已仅在 `problem-2:verification` 受保护区域写入六类检验：重复运行与SHA-256谱系、开放系统ODE量纲及RK4同步积分、1080度循环固定点、1度对0.5度步长细化、三腔错相与单腔 `Vs` 功率口径、统一循环起点燃料定义，以及多起点两参数受限拟合和31点扫描完整性。检验逐项给出输入、方法、判据、指标、结果及对正文结论的影响。

数值检验支持程序实现和条件响应的可复算性，但不改变证据边界：42.82 kW、20度边界的46.36 kW、效率曲线和模型峰值状态仍是当前先验与受限参数下的 `generated` 条件输出。`friction_scale=1.8` 命中施加上界，ISSUE-014保持open major；`project_state.yaml` 中问题二总体 `verification_status` 因缺少目标机台架验收继续保持 `pending`。

## 0A. 2026-08-14 问题二条件模型主体写入

`problem-modeling-writer [问题二]` 已在 `problem-2-analysis` 和 `problem-2` 非verification区域写入“相似机型约束的开放系统热力--转矩耦合模型”。正文采用开放系统零维质量--能量ODE、准稳态端口孔口流、Wiebe放热、简化壁面换热、等效泄漏、FMEP、循环收敛RK4积分和三腔错相瞬时转矩路线，旧的等BMEP直接缩放不再作为正式模型路线。

正文仅按条件模型报告6000 r/min、128度参考情景的42.82 kW、68.15 N m、29.326 mg/cycle、eta_b=0.3357和BSFC=246.55 g/(kW h)，并将20度的46.36 kW明确标为扫描下边界结果；75度仅称当前固定先验、受限拟合及20--170度、5度网格内的条件效率最大点。Peden等AIE 225CS的16个点明确为手工数字化候选点，不是题设目标机实测；样本内MAPE/RMSE也未称为验证误差。`friction_scale=1.8`命中上界及物理不可辨识性已在正文保留，ISSUE-014继续open。

正文引用三幅已验收谱系的稳定图名，图题均标明模型预测或条件响应。`problem-2:verification`现已由`model-verification-writer [问题二]`独立完成。

## 0. 2026-08-14 问题二效率口径最小返修正式验证增量

`model-verification-writer [问题二]` 已对最新版 `q2_closed_loop.py` 的ISSUE-013最小返修完成针对性验收。批量标定、基准simulate、31点扫描和0.5度细化均由收敛1080度循环起点fresh charge计算一次燃料量，并在该循环全部RK4子步中固定；`return_trace/collect_extrema` 不再改变燃料定义。独立重算基准、细化和31点扫描共33例，定义完全一致，燃料量与循环起点公式最大差6.8e-21 kg，`eta_b`与BSFC公式误差均为0。ISSUE-013已resolved，旧混合口径命题保留为历史rejected。

最新版仍采用1度网格，固定6项工程先验，仅拟合燃烧效率与FMEP尺度；三起点均收敛到`eta_comb=0.7392333966`、`friction_scale=1.8`并经精确ODE回代。独立批量精确ODE重算的成本为19.6973291460，MAPE为3.756606833%，RMSE为1.569129103 N m。旧的 `success=false,nfev=3` 阻塞保持resolved；但摩擦尺度仍命中1.8上界，故ISSUE-014保持open major，跨机型参数不具物理唯一性。

在指定先验与受限参数下，参考工况6000 r/min、128度的条件输出为42.820137 kW、68.150365 N m、燃料29.326057 mg/cycle、`eta_b=0.33566428`、BSFC=246.551764 g/kWh、峰压4.28697 MPa、峰温2739.90 K。0.5度功率差0.0352%，效率与BSFC差约0.00963%。31点扫描中功率从20度下边界的46.362162 kW降至170度的40.157262 kW；条件`eta_b`在75度达到网格最大0.336260，BSFC同时达到网格最小246.114724 g/kWh。

`problem-modeling-writer [问题二]` 已按上述边界完成条件模型主体写入。最强效率措辞仍为“在当前固定先验、受限拟合和指定20--170度、5度网格下，模型的制动热效率在75度达到网格最大值0.3363，BSFC降至246.1 g/kWh”；这不是目标机台架验证或实际最优角。功率、效率、峰压和峰温的物理预测仍保持generated，ISSUE-014及跨机型限制不变。

## 1. 用户协作偏好

1. 用户本地 Agent 额度有限。凡是不依赖本地文件操作或命令执行的任务，包括写作、只读审查、文献检索和方案论证，优先整理为完整任务包交给用户在网页 Claude 执行，用户会把结果发回。
2. 每个委派任务必须明确要求调用本项目的数学建模 Skill，例如：
   - `problem-modeling-writer [问题编号]`
   - `model-verification-writer [问题编号]`
   - `front-matter-writer`
   - `synthesis-evaluation-writer`
   - `abstract-writer`
   - `finalization-controller`
3. 用户所说的“Skill”是上述数学建模 Skill，不是 Nature 系列 Skill。不要再要求 `nature-*`。
4. 用户允许并行委派多个 Agent，但必须遵守项目规则：
   - 可以并行进行彼此独立的只读审查、材料检索、文献核验；
   - 文件修改始终串行；
   - `project-controller` 不得并行启动多个写作任务修改同一项目；
   - 每个问题的主体审查与 verification 审查可以并行收集意见，但必须分别限定区域，且在未获批准时都只输出清单/报告，不编辑。
5. 用户要求需要上网搜索时直接告诉他们，并提供可在网页执行的完整任务包。

持久偏好另见：
- `[[delegate-web-agent-tasks]]`
- `[[require-modeling-skills-for-delegation]]`

## 2. 项目身份与正式来源

- 竞赛：2026年武汉理工大学数学建模训练
- 题目：第4题《转子发动机容积建模与动力学优化设计》
- 问题数：3
- 正式题面：`2026年武汉理工大学数学建模训练题目4-6.docx`
- 正式附件：`第4题附件/附件.docx`
- 建模手/编程手候选材料：`第4题第一二三问修订源码/`
- 主文档：`main.tex`
- 参考文献：`references.bib`
- 图片正式目录：`figures/`
- 编译命令：`latexmk -xelatex main.tex`

题面和附件已登记为 `verified`。候选源码、CSV、图和候选正文不是正式附件，默认仅为 `generated/submitted`。

## 3. 已完成初始化

已创建并验证：

- `main.tex`：单文件正文；问题一主体与检验、问题二条件模型主体已写入，其余区域仍按所有权逐步完成。
- `references.bib`：已加入经核验的 Peden et al. 2018 SAE Technical Paper 条目，供问题二相似机型来源引用。
- `cumcmthesis.cls`：从既有模板复制，之后永久禁止修改。
- `figures/`、`data/`、`code/`
- `.modeling/project_state.yaml`
- `.modeling/section_ownership.yaml`
- `.modeling/evidence.yaml`
- `.modeling/issues.md`
- `.modeling/tasks/programming/reproduce-and-verify-q123.md`
- `.modeling/tasks/figures/select-and-trace-q123-figures.md`
- `.modeling/tasks/literature/turner-aie225cs-source-verification.md`
- `.modeling/tasks/literature/target-engine-bench-data-recovery.md`

完整性检查结果：

- Python 虚拟环境：`/home/Sparkle/.conda/envs/daily_use/bin/python`
- Python 3.13.5，PyYAML 6.0.2
- 三个 YAML 均成功解析
- `project_state.yaml` 已包含3个问题
- `section_ownership.yaml` 共20个区域，标记唯一、顺序正确、无非法重叠
- `main.tex` 未发现 `\input` 或 `\include`
- 当前容器再次执行 `latexmk -xelatex main.tex` 时因缺少 `ctexart.cls` 停止；这是环境依赖阻塞，不是本次问题二区域的已定位LaTeX语法错误。
- `git diff --check` 最近一次成功
- 最近一次 `latexmk` 显示所有目标已是最新

本次交接前尝试刷新 Git/编译状态时，Bash 因安全分类模型临时超时而未运行；以上为此前同一会话中最近一次成功检查结果。下一位控制器开始工作时应重新执行 `git status --short`、`git diff`、`git diff --check` 和必要的编译。

## 4. Git 状态与用户已有工作

仓库根目录：`/home/Sparkle/programming/tex_profiles/train`

最近一次成功的 Git 状态：

```text
 M ../train_1/main.tex
?? ../.claude/
?? ../train_1/figures/q3_flow.png
?? ./
```

含义：

- `train_1/main.tex` 有用户已有未提交修改，不得触碰或覆盖；
- `train_1/figures/q3_flow.png` 为用户已有未跟踪文件；
- `train_2/` 整体尚未跟踪；
- `.claude/` 尚未跟踪；
- 当前分支为 `master`；
- 禁止自行 commit/push；
- 禁止任何覆盖性 Git 命令。

## 5. 区域所有权

完整定义见 `.modeling/section_ownership.yaml`。关键区域：

- `problem_1_analysis`、`problem_1`：`problem-modeling-writer [问题一]`
- `problem_1_verification`：`model-verification-writer [问题一]`
- `problem_2_analysis`、`problem_2`：`problem-modeling-writer [问题二]`
- `problem_2_verification`：`model-verification-writer [问题二]`
- `problem_3_analysis`、`problem_3`：`problem-modeling-writer [问题三]`
- `problem_3_verification`：`model-verification-writer [问题三]`

受保护路径：

- `cumcmthesis.cls`
- `code/**`
- `第4题第一二三问修订源码/**`

任何候选程序都只能读取和运行，论文 Skill 不得直接修改。

## 6. 已确认几何事实

来自正式附件：

- 转子顶点长度：210 mm
- 转子内圆直径：147 mm
- 转子厚度：50 mm
- 固定外齿圈内圆直径：60 mm
- 滚动内齿圈外圆直径：90 mm
- 内外齿圈齿数比：3:2
- 曲轴与转子角速度比：3:1
- 曲轴0°位于压缩上止点前69°
- 附件排量定义：单缸进气结束点容积乘以3
- 附件压缩比定义：单腔最大容积除以单腔最小余隙容积

## 7. 问题一当前状态

候选文件：

- `第4题第一二三问修订源码/03-q1.tex`
- `第4题第一二三问修订源码/q1_geometry.py`
- `第4题第一二三问修订源码/q1_results.csv`

以下基准结果已在用户批准的圆弧理想化范围内由 `model-verification-writer [问题一]` 本地独立验收为 `verified`：

- `Vmin = 40.6603 cm³`
- 单腔扫气容积 `Vs = 409.1970 cm³`
- `Vmax = 449.8573 cm³`
- `CR = 11.0638`
- 附件口径排量 `3Vmax = 1349.5720 cm³`
- 三个工作面的 swept-volume 数值和 `3Vs = 1227.5910 cm³`（不能在相同 `n/60` 下直接用于当前 BMEP 公式）
- 条件性实体接触边界 `d_contact = 150.000 mm`
- 代数零余隙根 `d_zero = 159.872613647263 mm`（不是机械接触边界）

脚本、CSV、元数据、图片、基准数值、540°/1080°周期区分、三腔守恒、接触边界和BMEP口径均已分项verified。`project_state.yaml` 的问题一 `verification_status` 已更新为verified；`official_results` 仍为空，因为本 Skill 只验收证据，不自行确立或写入主体正式结果。

现已收到两份网页只读审查报告（主体审查与独立验证），均已在 `evidence.yaml` 登记为 `generated` 的 submitted evidence，**不是**本地 `verified` 结论。用户已批准 Q1 的局部理想化：三条转子侧边连接相邻顶点、关于边中线对称，并在边中点与直径 `d` 的内切圆相切，取劣圆弧；该假设只适用于 Q1 理想几何/容积/灵敏度，不是正式附件对实际转子形状的事实断言。

两份网页报告本身继续保持 `generated/submitted`，不因本地验收而整体升级。原报告指出的程序问题已经修复并闭合 lineage；历史“脚本仍写入错误路径”的旧命题在 `evidence.yaml` 保持rejected。候选正文 `03-q1.tex` 保持只读，不作为正式正文来源。

### 问题一正式写入状态

2026-08-13，`problem-modeling-writer [问题一]` 已在获批区域写入问题分析、圆弧转子--Green面积容积模型、基准结果与内圆直径灵敏度分析，并引用稳定图名 `figures/q1-volume-cr.png`。正文已明确：540°为几何容积最小周期，1080°为同一腔热力状态循环；150 mm为获批理想几何的条件性接触边界；`3Vmax`为题面排量，单腔`Vs`为问题二BMEP接口。ISSUE-008和ISSUE-009已解决；ISSUE-010的Q1部分已解决。问题一verification子区域随后已独立写入。

问题二验收已确认：若409.1970 cm³确为单腔扫气容积，则用于单转子Wankel公式 `P = BMEP * Vs * n / 60` 的口径自洽；但数值本身仍依赖问题一验证。

2026-08-13，用户已批准并完成问题一 verification 子区域写入。该小节以80位独立重算与Green离散积分、20003点周期/守恒检查、五个事件角核对及721姿态、24001壳体点的接触复核，支撑基准几何结论和$[132.3,150)$ mm的理想几何非干涉区间；其结论不外推至制造公差、热变形或密封。

## 8. 问题二外部证据验收结果

用户已在网页完成两步：

1. `problem-modeling-writer [问题二]` 外部检索；
2. `model-verification-writer [问题二]` 独立证据验收。

结果已登记到 `.modeling/evidence.yaml` 与 `.modeling/issues.md`。

### 已分项 `verified`

- Peden et al. 2018 书目信息，DOI `10.4271/2018-01-1452`
- Peden Fig.17 是扭矩曲线，覆盖16个5000--7500 r/min转速点
- AIE 225CS 是225 cc/chamber single-rotor
- 29 lb·ft 到39.3187 N·m的单位换算
- 外部参数的真实来源语义：
  - 0.92/0.95 是 Tartakovsky 对其他Wankel的virtual-blowing计算值，被Peden作为先验，不是225CS或题设机实测
  - 0.03 mm² 是Peden敏感性扫描后采用的代表性等效泄漏参数，不是实测几何泄漏面积
  - 2.5% 是Peden模型对实验扭矩的average discrepancy，不是已定义MAPE、测量误差或跨机型误差
  - 96.7%--97% 是经验FMEP关系推算的机械效率代理，不是motoring实测

### 仍为 `generated`

- 6000 r/min精确读值29.0 lb·ft：原图支持约29，但缺PDF原页、坐标标定、像素记录和数字化CSV
- 10.98 bar：数学推导正确，但依赖未完整验收的精确读值
- 44.9 kW：保持相同BMEP的跨机型条件估计，不是目标机实测最大功率
- 38.19--51.67 kW：只是假设BMEP正负15%的敏感性场景，不是正式不确定区间
- `xi0=0.20` 和重叠效率变化表：完全混合公式数学自洽，但参数和映射未由目标机标定
- AIE 225CS到题设发动机的整体迁移结论

### 允许的最强功率措辞

只能类似：

> 以Peden et al.公开的AIE 225CS台架扭矩曲线为相似机型先验，在假设题设发动机于6000 r/min下具有相同制动平均有效压力时，利用问题一的单腔扫气容积得到约44.9 kW的条件制动功率估计；该值并非题设发动机台架实测最大功率。

不能写“该发动机最大输出功率为44.93 kW”。

## 9. 当前问题清单

完整内容见 `.modeling/issues.md`。当前关键项：

- ISSUE-001 blocking：题目称附件有台架标定结果，但现有附件未发现目标机台架数表
- ISSUE-002 major：AIE来源已分项验收，但Fig.17数字化链和跨机型推导仍未正式化
- ISSUE-003 major：Q1已独立验收，Q2第二轮程序已复现但条件物理解释仍受限，Q3尚未完成同等级审查
- ISSUE-004 major：Q3代理指标和设计边界缺少目标机标定
- ISSUE-005 blocking：问题二不能把44.9 kW条件估计写成目标机最大功率
- ISSUE-006 blocking：问题二缺端口面积、压差、基准重叠角和喷油方式，重叠角到效率映射不可辨识
- ISSUE-013 resolved：基准、扫描、细化与批量标定已统一循环起点燃料定义，允许写条件效率响应
- ISSUE-014 major：两参数受限拟合数值收敛，但摩擦尺度命中1.8上界且六项先验固定，不具物理唯一辨识性

## 10. 参考文献规范结论

验收建议：

- Peden 2018、Tartakovsky 2012、Chen 2020、Vorraro Part II/III 是 SAE Technical Paper，项目中优先统一为 `@techreport`，也可有理由采用 `@inproceedings`，不建议使用 `@article`
- Vorraro Part IV 是正式期刊论文，使用 `@article`，年份2023、卷5、期3、页1243--1255；`2022-01-1001` 是SAE paper/product code，不是期号
- 正式简称应为 Peden et al. 2018，而不是笼统写Turner et al.
- `references.bib` 已加入经核验的 Peden et al. 2018 SAE Technical Paper 条目，DOI为`10.4271/2018-01-1452`

## 11. 下一步编排建议

问题一已完成。问题二条件主体和数值检验均已写入；问题二总体证据状态仍为`pending`，不得把条件输出升级为目标机实测。下一步由控制器核对本次区域修改、编译与状态文件，再决定是否进入问题三审查。

## 12. 永久禁止事项

- 不得修改 `cumcmthesis.cls`
- 不得自行 `git commit` 或 `git push`
- 不得使用覆盖性Git命令清除工作
- 不得直接修改 `code/` 或 `第4题第一二三问修订源码/` 中程序
- 不得把猜测标为confirmed/verified
- 不得把AIE 225CS或其他相似机型数据写成题设目标机实测数据
- 不得自动开始摘要、综合评价或后续问题写作
- 不得并行修改同一项目文件

## 13. 下一位控制器启动检查

开始工作时必须：

1. 调用 `project-controller`；
2. 读取共享指南；
3. 读取完整 `main.tex`、`.modeling/project_state.yaml`、`section_ownership.yaml`、`evidence.yaml`、`issues.md` 和本文件；
4. 执行 `git status --short` 与 `git diff`；
5. 确认无 `\input`/`\include`；
6. 检查用户是否已带回问题一并行审查结果；
7. 若尚未执行，则向用户提供两个独立、完整、明确要求数学建模Skill的问题一网页任务包；
8. 不直接开始写正文。
