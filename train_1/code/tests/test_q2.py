from pathlib import Path
import sys
import unittest


CODE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))

from daily_cover import solve_daily_minima  # noqa: E402
from data_loader import load_demand  # noqa: E402
from shift_patterns import build_coverage, generate_shift_patterns  # noqa: E402
from solve_core_and_roster import solve_q2  # noqa: E402


class QuestionTwoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_demand(PROJECT_DIR / "data" / "附件1.xlsx")
        cls.patterns = generate_shift_patterns()
        cls.coverage = build_coverage(cls.patterns)
        cls.daily = solve_daily_minima(cls.data.demand, cls.coverage)
        cls.q2 = solve_q2(
            cls.data.demand, cls.coverage, cls.patterns, cls.daily
        )

    def test_q2_staff_and_redundancy(self):
        self.assertEqual(cls_staff := self.q2.staff, 406)
        self.assertEqual(int(self.q2.daily_lower_bound.sum()), 3247)
        self.assertEqual(int(self.q2.actual_daily_workers.sum()), 3248)
        self.assertEqual(self.q2.redundant_workdays, 1)
        self.assertEqual(self.q2.redundancy_day, 7, msg=f"staff={cls_staff}")
        self.assertEqual(
            self.q2.actual_daily_workers.tolist(),
            [214, 349, 314, 333, 349, 331, 364, 350, 325, 319],
        )

    def test_q2_full_flow(self):
        self.assertEqual(self.q2.maxflow_summary["required_flow"], 812)
        self.assertEqual(self.q2.maxflow_summary["computed_max_flow"], 812)
        self.assertTrue(self.q2.maxflow_summary["is_full_flow"])

    def test_q2_employee_counts_and_one_group_per_day(self):
        self.assertEqual(len(self.q2.employee_schedule), 4060)
        self.assertEqual(
            sum(r["status"] == "WORK" for r in self.q2.employee_schedule), 3248
        )
        self.assertEqual(
            sum(r["status"] == "REST" for r in self.q2.employee_schedule), 812
        )
        keys = [
            (r["employee"], r["day"])
            for r in self.q2.employee_schedule
            if r["status"] == "WORK"
        ]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(self.q2.verification["one_group_per_workday"])

    def test_q2_hourly_no_deficit(self):
        self.assertEqual(len(self.q2.hourly_coverage), 1100)
        self.assertEqual(self.q2.verification["deficit_count"], 0)
        self.assertGreaterEqual(self.q2.verification["minimum_slack"], 0)


if __name__ == "__main__":
    unittest.main()
