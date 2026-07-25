from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd


CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from milp_utils import solve_integer_program  # noqa: E402
from run_modeling import run_all  # noqa: E402


class SolverBackendTests(unittest.TestCase):
    def test_scip_backend_reports_real_scip_result(self):
        result = solve_integer_program(
            objective=np.array([1.0]),
            matrix=np.array([[1.0]]),
            lower=np.array([3.0]),
            upper=np.array([np.inf]),
            solver="SCIP",
        )

        self.assertEqual(result.status, "OPTIMAL")
        self.assertEqual(result.objective_value, 3.0)
        self.assertEqual(result.best_bound, 3.0)
        self.assertEqual(result.relative_gap, 0.0)
        self.assertEqual(result.solver_name, "PySCIPOpt/SCIP")
        self.assertRegex(result.solver_version, r"^\d+\.\d+\.\d+$")

    def test_scip_request_runs_every_reported_milp_without_fallback(self):
        project_dir = CODE_DIR.parent
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "scip"
            summary = run_all(
                project_dir / "data" / "附件1.xlsx",
                output,
                requested_solver="SCIP",
            )
            daily = pd.read_csv(output / "tables" / "daily_minimum_by_group.csv")

        self.assertEqual(summary["environment"]["requested_solver"], "SCIP")
        self.assertEqual(
            summary["environment"]["actual_solver"], "PySCIPOpt/SCIP"
        )
        self.assertFalse(summary["environment"]["solver_fallback_used"])
        self.assertEqual(set(daily["solver_name"]), {"PySCIPOpt/SCIP"})
        self.assertEqual(
            summary["full_milp"]["q1"]["solver_name"], "PySCIPOpt/SCIP"
        )
        self.assertEqual(
            summary["full_milp"]["q2"]["solver_name"], "PySCIPOpt/SCIP"
        )


if __name__ == "__main__":
    unittest.main()
