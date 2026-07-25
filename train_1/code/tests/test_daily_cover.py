from pathlib import Path
import sys
import unittest

import numpy as np


CODE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))

from daily_cover import analytic_q1_staff, analytic_q2_staff, solve_daily_minima  # noqa: E402
from data_loader import load_demand  # noqa: E402
from shift_patterns import build_coverage, generate_shift_patterns  # noqa: E402


class DailyCoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demand = load_demand(PROJECT_DIR / "data" / "附件1.xlsx").demand
        cls.coverage = build_coverage(generate_shift_patterns())
        cls.result = solve_daily_minima(cls.demand, cls.coverage)

    def test_daily_models_all_optimal(self):
        self.assertEqual(cls_shape := self.result.minimum_workers.shape, (10, 10))
        self.assertEqual(self.result.shift_counts.shape, (10, 10, 10))
        self.assertEqual(len(self.result.metadata), 100)
        self.assertTrue(all(row["solver_status"] == "OPTIMAL" for row in self.result.metadata))
        np.testing.assert_array_equal(
            self.result.shift_counts.sum(axis=2), self.result.minimum_workers
        )
        actual = np.einsum("hs,dgs->dhg", self.coverage, self.result.shift_counts)
        self.assertTrue(np.all(actual >= self.demand), msg=f"shape={cls_shape}")

    def test_q1_group_staff_and_total(self):
        q1 = analytic_q1_staff(self.result.minimum_workers)
        np.testing.assert_array_equal(
            q1.staff, np.array([39, 39, 43, 41, 44, 39, 42, 42, 43, 45])
        )
        self.assertEqual(int(q1.staff.sum()), 417)

    def test_q2_daily_lower_bound_total(self):
        q2 = analytic_q2_staff(self.result.minimum_workers)
        np.testing.assert_array_equal(
            q2.daily_lower_bound,
            np.array([214, 349, 314, 333, 349, 331, 363, 350, 325, 319]),
        )
        self.assertEqual(int(q2.daily_lower_bound.sum()), 3247)
        self.assertEqual(q2.staff, 406)
        self.assertEqual(q2.redundant_workdays, 1)
        self.assertEqual(q2.redundancy_day, 7)


if __name__ == "__main__":
    unittest.main()
