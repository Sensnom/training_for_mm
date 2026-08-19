# File Library 中的项目文件（当前运行时未挂载，未伪造复制）

以下文件在本项目历史中存在，但当前容器只提供 File Library 引用而非原始字节，因此本压缩包不伪造同名二进制。它们的状态和用途已记录在 `.modeling/evidence.yaml`。

- `第7题_第1-7部分_P0修订报告.pdf` — Q1-Q3 修订报告 PDF。
- `第7题_第1-7部分_P0修订报告.docx` — Q1-Q3 修订报告 Word 源。
- `q7_strict_boundary_repair.py` — Q1 附件法证 + Q2/Q3 解析概率脚本；不是完整 3D geometry kernel。
- `strict_geometry_reference.py` — 独立严格边界参考几何内核。
- `strict_connectivity_reference.py` — 参考连通图层。
- `q2_q3_independent_check.py` — Q2/Q3 独立随机数交叉检查。
- `q2_q3_independent_derivation.md` — Q2/Q3 独立解析推导。
- `controller_handoff.md` — 独立 verification gate handoff；Q4 PASS、Q1 仍 pending。
- `v0_code_coverage.md` — 对 `q7_strict_boundary_repair.py` 覆盖范围的审计。

如果后续在一个完整工程副本中继续写论文，建议将这些原始文件从 File Library 导出后放入本包对应目录，再更新 SHA256 清单。
