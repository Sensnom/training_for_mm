from pathlib import Path
import sys
import unittest

import numpy as np


CODE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))

from data_loader import load_demand  # noqa: E402
from shift_patterns import build_coverage, generate_shift_patterns  # noqa: E402


class InputAndPatternTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_demand(PROJECT_DIR / "data" / "附件1.xlsx")
        cls.patterns = generate_shift_patterns()
        cls.coverage = build_coverage(cls.patterns)

    def test_data_shape_and_integrity(self):
        self.assertEqual(self.data.demand.shape, (10, 11, 10))
        self.assertEqual(self.data.demand.size, 1100)
        self.assertTrue(np.issubdtype(self.data.demand.dtype, np.integer))
        self.assertTrue(np.all(self.data.demand > 0))
        self.assertEqual(self.data.days, tuple(range(1, 11)))
        self.assertEqual(len(self.data.hour_labels), 11)

    def test_shift_count_is_10(self):
        self.assertEqual(len(self.patterns), 10)
        self.assertEqual(
            [(p.first_start, p.second_start) for p in self.patterns],
            [
                (8, 12), (8, 13), (8, 14), (8, 15),
                (9, 13), (9, 14), (9, 15),
                (10, 14), (10, 15), (11, 15),
            ],
        )

    def test_each_shift_covers_8_hours(self):
        self.assertEqual(self.coverage.shape, (11, 10))
        np.testing.assert_array_equal(
            self.coverage.sum(axis=0), np.full(10, 8, dtype=int)
        )


if __name__ == "__main__":
    unittest.main()
