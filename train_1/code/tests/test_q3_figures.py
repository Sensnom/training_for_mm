import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd


CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from q3_figures import build_q3_figures  # noqa: E402


class Q3FigureTests(unittest.TestCase):
    def test_builds_three_formats_in_output_and_paper_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "train_1"
            output = project / "paper_output"
            (output / "tables").mkdir(parents=True)
            (output / "results").mkdir(parents=True)
            rows = []
            totals = [None, None, 20, 25, 18, 22, 24, 29]
            full = [None, None, 20, 25, 12, 16, 18, 23]
            part = [None, None, 0, 0, 6, 6, 6, 6]
            for index in range(8):
                rows.append({
                    "scenario": f"S{index}",
                    "status": "INFEASIBLE" if index < 2 else "OPTIMAL",
                    "fulltime_staff": full[index],
                    "parttime_staff": part[index],
                    "total_staff": totals[index],
                    "allow_cross_group": index % 2 == 0,
                })
            pd.DataFrame(rows).to_csv(output / "tables" / "q3_scenario_comparison.csv", index=False)
            payload = {
                "analytic_strict_infeasibility": {
                    "blind_hour_start": "13:00",
                    "daily_blind_hour_demand": [1] * 10,
                    "total_blind_hour_demand": 10,
                }
            }
            (output / "results" / "q3_model_results.json").write_text(json.dumps(payload), encoding="utf-8")

            generated = build_q3_figures(output)

            self.assertEqual(len(generated), 18)
            self.assertTrue(all(path.is_file() and path.stat().st_size > 0 for path in generated))


if __name__ == "__main__":
    unittest.main()
