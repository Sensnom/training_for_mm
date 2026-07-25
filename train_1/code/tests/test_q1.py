from pathlib import Path
import sys
import unittest

import numpy as np


CODE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))

from daily_cover import solve_daily_minima  # noqa: E402
from data_loader import load_demand  # noqa: E402
from shift_patterns import build_coverage, generate_shift_patterns  # noqa: E402
from solve_core_and_roster import solve_q1  # noqa: E402


class QuestionOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_demand(PROJECT_DIR / "data" / "附件1.xlsx")
        cls.patterns = generate_shift_patterns()
        cls.coverage = build_coverage(cls.patterns)
        cls.daily = solve_daily_minima(cls.data.demand, cls.coverage)
        cls.q1 = solve_q1(
            cls.data.demand, cls.coverage, cls.patterns, cls.daily
        )

    def test_q1_each_group_full_flow(self):
        self.assertEqual(
            [r["computed_max_flow"] for r in self.q1.maxflow_summary],
            [78, 78, 86, 82, 88, 78, 84, 84, 86, 90],
        )
        self.assertTrue(all(r["is_full_flow"] for r in self.q1.maxflow_summary))

    def test_q1_employee_counts(self):
        self.assertEqual(len(self.q1.employee_schedule), 4170)
        statuses = [r["status"] for r in self.q1.employee_schedule]
        self.assertEqual(statuses.count("WORK"), 3336)
        self.assertEqual(statuses.count("REST"), 834)
        by_employee = {}
        for row in self.q1.employee_schedule:
            by_employee.setdefault(row["employee"], []).append(row)
        self.assertEqual(len(by_employee), 417)
        for rows in by_employee.values():
            self.assertEqual(len(rows), 10)
            self.assertEqual(sum(r["status"] == "WORK" for r in rows), 8)
            self.assertEqual(sum(r["status"] == "REST" for r in rows), 2)

    def test_q1_fixed_group(self):
        by_employee = {}
        for row in self.q1.employee_schedule:
            by_employee.setdefault(row["employee"], set()).add(row["fixed_group"])
        self.assertTrue(all(len(groups) == 1 for groups in by_employee.values()))

    def test_q1_hourly_no_deficit(self):
        self.assertEqual(self.q1.verification["deficit_count"], 0)
        self.assertGreaterEqual(self.q1.verification["minimum_slack"], 0)
        self.assertEqual(len(self.q1.hourly_coverage), 1100)
        self.assertTrue(np.all(self.q1.shift_counts.sum(axis=2) <= self.q1.staff))
        np.testing.assert_array_equal(
            self.q1.shift_counts.sum(axis=(0, 2)), 8 * self.q1.staff
        )


if __name__ == "__main__":
    unittest.main()
