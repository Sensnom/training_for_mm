from collections import Counter
from pathlib import Path
import sys
import unittest

import numpy as np


CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from q3_models import Q3ScenarioResult, Q3ScenarioSpec  # noqa: E402
from q3_patterns import generate_fulltime_patterns, generate_parttime_patterns  # noqa: E402
from q3_roster import build_q3_rosters  # noqa: E402


class Q3RosterTests(unittest.TestCase):
    def make_result(self):
        full_patterns = generate_fulltime_patterns(2)
        part_patterns = generate_parttime_patterns()
        z = np.zeros((10, len(full_patterns), 10, 10), dtype=np.int64)
        z[:8, 0, 0, 1] = 2
        p = np.zeros((10, len(part_patterns), 10), dtype=np.int64)
        p[0, 0, 0] = 3
        p[1, 1, 2] = 2
        return Q3ScenarioResult(
            spec=Q3ScenarioSpec("T", "test", 2, True, True, "headcount"),
            status="OPTIMAL",
            solver_name="PySCIPOpt/SCIP",
            solver_version="10.0.2",
            runtime_seconds=0.0,
            fulltime_staff=2,
            parttime_staff=3,
            total_staff=5,
            total_parttime_shifts=5,
            total_paid_hours=148,
            cross_group_employee_days=16,
            fulltime_workdays=16,
            z=z,
            p=p,
            fulltime_patterns=full_patterns,
            parttime_patterns=part_patterns,
        )

    def test_fulltime_roster_has_eight_workdays_and_matches_macro_slots(self):
        result = self.make_result()
        roster = build_q3_rosters(result)

        statuses = {}
        for row in roster.fulltime_schedule:
            statuses.setdefault(row["employee_id"], Counter())[row["status"]] += 1
        self.assertEqual(len(statuses), 2)
        self.assertTrue(all(counts == Counter({"WORK": 8, "REST": 2}) for counts in statuses.values()))
        self.assertTrue(all(row["cross_group"] for row in roster.fulltime_schedule if row["status"] == "WORK"))
        self.assertTrue(np.array_equal(roster.reconstructed_z, result.z))

    def test_parttime_roster_uses_pool_and_at_most_one_shift_per_day(self):
        result = self.make_result()
        roster = build_q3_rosters(result)

        employee_days = [(row["employee_id"], row["day"]) for row in roster.parttime_schedule]
        self.assertEqual(len(employee_days), len(set(employee_days)))
        self.assertEqual(len({row["employee_id"] for row in roster.parttime_schedule}), 3)
        self.assertTrue(np.array_equal(roster.reconstructed_p, result.p))


if __name__ == "__main__":
    unittest.main()
