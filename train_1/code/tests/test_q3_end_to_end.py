import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd


CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from run_q3_modeling import run_q3  # noqa: E402


class Q3EndToEndTests(unittest.TestCase):
    def test_formal_run_writes_required_outputs_and_uses_scip(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "paper_output"
            summary = run_q3(
                CODE_DIR.parent / "data" / "附件1.xlsx",
                output,
                solver="SCIP",
                time_limit=120,
                build_figures=False,
            )
            required = [
                "tables/q3_fulltime_employee_schedule.csv",
                "tables/q3_parttime_employee_schedule.csv",
                "tables/q3_hourly_coverage.csv",
                "tables/q3_cross_group_summary.csv",
                "tables/q3_group_transition_matrix.csv",
                "tables/q3_scenario_comparison.csv",
                "results/q3_model_results.json",
                "results/q3_verification.json",
            ]
            self.assertTrue(all((output / relative).is_file() for relative in required))
            scenarios = pd.read_csv(output / "tables" / "q3_scenario_comparison.csv")
            verification = json.loads((output / "results" / "q3_verification.json").read_text(encoding="utf-8"))

        self.assertEqual(scenarios["scenario"].tolist(), [f"S{i}" for i in range(8)])
        self.assertEqual(scenarios.loc[0, "status"], "INFEASIBLE")
        self.assertEqual(scenarios.loc[1, "status"], "INFEASIBLE")
        self.assertEqual(set(scenarios["solver_name"]), {"PySCIPOpt/SCIP"})
        feasible = scenarios.loc[scenarios["status"] == "OPTIMAL"]
        self.assertEqual(feasible["deficit_count"].astype(int).tolist(), [0] * 6)
        self.assertTrue((feasible["minimum_slack"] >= 0).all())
        self.assertFalse(summary["environment"]["solver_fallback_used"])
        self.assertEqual(summary["selected_scenario"], "S4")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["deficit_count"], 0)
        self.assertEqual(verification["cpsat_status"], "PASS")
        self.assertLess(
            int(scenarios.loc[scenarios["scenario"] == "S2", "total_staff"].iloc[0]),
            int(scenarios.loc[scenarios["scenario"] == "S3", "total_staff"].iloc[0]),
        )
        self.assertLess(
            int(scenarios.loc[scenarios["scenario"] == "S4", "total_staff"].iloc[0]),
            int(scenarios.loc[scenarios["scenario"] == "S6", "total_staff"].iloc[0]),
        )


if __name__ == "__main__":
    unittest.main()
