from pathlib import Path
import sys
import unittest


CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from data_loader import load_demand  # noqa: E402
from q3_models import build_default_scenarios, solve_q3_scenario  # noqa: E402


class Q3ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demand = load_demand(CODE_DIR.parent / "data" / "附件1.xlsx").demand

    def test_default_scenarios_have_required_ids_and_objectives(self):
        scenarios = build_default_scenarios()

        self.assertEqual([scenario.scenario_id for scenario in scenarios], [f"S{i}" for i in range(8)])
        self.assertEqual([scenario.minimum_break_hours for scenario in scenarios], [2, 2, 1, 1, 2, 2, 2, 2])
        self.assertEqual([scenario.allow_cross_group for scenario in scenarios], [True, False, True, False, True, False, True, False])
        self.assertEqual([scenario.objective_policy for scenario in scenarios], ["staff", "staff", "staff", "staff", "headcount", "headcount", "parttime_first", "parttime_first"])

    def test_strict_scenarios_are_milp_infeasible(self):
        for scenario in build_default_scenarios()[:2]:
            result = solve_q3_scenario(scenario, self.demand, time_limit=30)
            self.assertEqual(result.status, "INFEASIBLE")
            self.assertEqual(result.solver_name, "PySCIPOpt/SCIP")
            self.assertEqual(result.lexicographic_stages, [])


if __name__ == "__main__":
    unittest.main()
