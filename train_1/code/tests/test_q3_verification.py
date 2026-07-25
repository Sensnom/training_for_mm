from pathlib import Path
import sys
import unittest

import numpy as np


CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from q3_models import Q3ScenarioResult, Q3ScenarioSpec  # noqa: E402
from q3_patterns import (  # noqa: E402
    build_fulltime_coverage,
    build_parttime_coverage,
    generate_fulltime_patterns,
    generate_parttime_patterns,
)
from q3_roster import build_q3_rosters  # noqa: E402
from q3_verification import verify_q3_rosters  # noqa: E402


class Q3VerificationTests(unittest.TestCase):
    def make_case(self):
        full_patterns = generate_fulltime_patterns(2)
        part_patterns = generate_parttime_patterns()
        z = np.zeros((10, len(full_patterns), 10, 10), dtype=np.int64)
        z[:8, 0, 0, 1] = 2
        p = np.zeros((10, len(part_patterns), 10), dtype=np.int64)
        p[:, 0, 0] = 1
        result = Q3ScenarioResult(
            spec=Q3ScenarioSpec("T", "test", 2, True, True, "headcount"),
            status="OPTIMAL",
            solver_name="PySCIPOpt/SCIP",
            solver_version="10.0.2",
            runtime_seconds=0.0,
            fulltime_staff=2,
            parttime_staff=1,
            total_staff=3,
            total_parttime_shifts=10,
            total_paid_hours=168,
            cross_group_employee_days=16,
            fulltime_workdays=16,
            z=z,
            p=p,
            fulltime_patterns=full_patterns,
            parttime_patterns=part_patterns,
        )
        part_cov = build_parttime_coverage(part_patterns)
        demand = np.zeros((10, 11, 10), dtype=np.int64)
        for day in range(10):
            for shift, pattern in enumerate(full_patterns):
                for g in range(10):
                    for k in range(10):
                        count = z[day, shift, g, k]
                        demand[day, pattern.first_start - 8:pattern.first_end - 8, g] += count
                        demand[day, pattern.second_start - 8:pattern.second_end - 8, k] += count
            for shift in range(len(part_patterns)):
                for group in range(10):
                    demand[day, :, group] += part_cov[:, shift] * p[day, shift, group]
        return result, build_q3_rosters(result), demand

    def test_verification_reconstructs_coverage_and_cross_group_statistics(self):
        result, roster, demand = self.make_case()
        verified = verify_q3_rosters(result, roster, demand, run_cpsat=True)

        self.assertEqual(verified.summary["status"], "PASS")
        self.assertEqual(verified.summary["deficit_count"], 0)
        self.assertEqual(verified.summary["cross_group_employee_days"], 16)
        self.assertEqual(len(verified.hourly_coverage), 1100)
        self.assertEqual(len(verified.transition_rows), 10)
        self.assertEqual(
            sum(
                row[f"to_group_{group}"]
                for row in verified.transition_rows
                for group in range(1, 11)
            ),
            16,
        )
        self.assertEqual(verified.summary["cpsat_status"], "PASS")

    def test_verification_rejects_a_coverage_deficit(self):
        result, roster, demand = self.make_case()
        demand[9, 0, 9] = 1

        with self.assertRaisesRegex(AssertionError, "覆盖缺口"):
            verify_q3_rosters(result, roster, demand, run_cpsat=False)


if __name__ == "__main__":
    unittest.main()
