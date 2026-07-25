from hashlib import sha256
from pathlib import Path
import sys
import tempfile
import unittest


CODE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))

from run_modeling import run_all  # noqa: E402


CORE_CSVS = (
    "tables/q1_employee_schedule.csv",
    "tables/q1_hourly_coverage.csv",
    "tables/q2_employee_schedule.csv",
    "tables/q2_hourly_coverage.csv",
)


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output1 = Path(cls.temp.name) / "run1"
        cls.output2 = Path(cls.temp.name) / "run2"
        data = PROJECT_DIR / "data" / "附件1.xlsx"
        cls.summary1 = run_all(data, cls.output1, requested_solver="HiGHS")
        cls.summary2 = run_all(data, cls.output2, requested_solver="HiGHS")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_expected_output_files_exist(self):
        expected = [
            "results/data_validation.json",
            "results/q1_model_results.json",
            "results/q2_model_results.json",
            "results/q2_verification.json",
            "results/q2_redundancy_summary.json",
            "results/full_milp_verification.json",
            "results/cpsat_roster_verification.json",
            "tables/shift_patterns_q1_q2.csv",
            "tables/shift_coverage_matrix.csv",
            "tables/daily_minimum_by_group.csv",
            "tables/q1_group_results.csv",
            "tables/q1_daily_shift_plan.csv",
            "tables/q1_maxflow_summary.csv",
            "tables/q1_employee_day_status.csv",
            "tables/q1_employee_schedule.csv",
            "tables/q1_hourly_coverage.csv",
            "tables/q2_daily_lower_bound.csv",
            "tables/q2_daily_actual.csv",
            "tables/q2_daily_shift_plan.csv",
            "tables/q2_maxflow_summary.csv",
            "tables/q2_employee_day_status.csv",
            "tables/q2_employee_schedule.csv",
            "tables/q2_hourly_coverage.csv",
            "figures/q1_q2/fig_q1_group_staff.png",
            "figures/q1_q2/fig_q1_group_staff.pdf",
            "figures/q1_q2/fig_q1_group_staff.svg",
            "figures/q1_q2/fig_q2_daily_lower_actual.png",
            "figures/q1_q2/fig_q2_daily_lower_actual.pdf",
            "figures/q1_q2/fig_q2_daily_lower_actual.svg",
            "figures/q1_q2/fig_q1_q2_staff_comparison.png",
            "figures/q1_q2/fig_q1_q2_staff_comparison.pdf",
            "figures/q1_q2/fig_q1_q2_staff_comparison.svg",
            "logs/run_modeling.log",
            "logs/full_milp_verification.log",
        ]
        missing = [name for name in expected if not (self.output1 / name).is_file()]
        self.assertEqual(missing, [])

    def test_full_milp_matches_analytic_results(self):
        full = self.summary1["full_milp"]
        self.assertEqual(self.summary1["q1"]["status"], "OPTIMAL")
        self.assertEqual(self.summary1["q1"]["verification_status"], "PASS")
        self.assertEqual(self.summary1["q2"]["status"], "OPTIMAL")
        self.assertEqual(self.summary1["q2"]["verification_status"], "PASS")
        self.assertEqual(full["q1"]["status"], "OPTIMAL")
        self.assertEqual(full["q1"]["objective_value"], 417)
        self.assertEqual(full["q2"]["status"], "OPTIMAL")
        self.assertEqual(full["q2"]["objective_value"], 406)

    def test_repeated_runs_are_identical(self):
        first = {name: file_hash(self.output1 / name) for name in CORE_CSVS}
        second = {name: file_hash(self.output2 / name) for name in CORE_CSVS}
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
