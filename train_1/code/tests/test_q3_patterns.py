from pathlib import Path
import sys
import unittest

import numpy as np


CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from data_loader import load_demand  # noqa: E402
from q3_patterns import (  # noqa: E402
    blind_zone_proof,
    build_fulltime_coverage,
    build_parttime_coverage,
    generate_fulltime_patterns,
    generate_parttime_patterns,
)


class Q3PatternTests(unittest.TestCase):
    def test_fulltime_pattern_counts_and_coverage(self):
        strict = generate_fulltime_patterns(2)
        gap_one = generate_fulltime_patterns(1)

        self.assertEqual(len(strict), 3)
        self.assertEqual(len(gap_one), 6)
        self.assertTrue(np.all(build_fulltime_coverage(strict).sum(axis=0) == 8))
        self.assertTrue(np.all(build_fulltime_coverage(gap_one).sum(axis=0) == 8))

    def test_strict_patterns_have_common_blind_hour(self):
        project = CODE_DIR.parent
        demand = load_demand(project / "data" / "附件1.xlsx").demand
        strict = generate_fulltime_patterns(2)
        proof = blind_zone_proof(demand, strict)

        self.assertEqual(proof["blind_hour_start"], "13:00")
        self.assertEqual(proof["blind_hour_end"], "14:00")
        self.assertEqual(proof["all_patterns_zero_at_blind_hour"], True)
        self.assertEqual(proof["daily_blind_hour_demand"], [85, 98, 146, 149, 152, 159, 188, 206, 150, 167])
        self.assertEqual(proof["total_blind_hour_demand"], 1500)

    def test_parttime_patterns_all_cover_blind_hour(self):
        patterns = generate_parttime_patterns()
        coverage = build_parttime_coverage(patterns)

        self.assertEqual(len(patterns), 4)
        self.assertTrue(np.all(coverage.sum(axis=0) == 4))
        self.assertTrue(np.all(coverage[5, :] == 1))


if __name__ == "__main__":
    unittest.main()
