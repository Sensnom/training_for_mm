from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings

from matplotlib import colors as mcolors
from matplotlib import pyplot as plt
import pandas as pd


CODE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))

import build_q1_q2_figures as figures  # noqa: E402
from build_q1_q2_figures import (  # noqa: E402
    BLUE,
    FIGURE_STEMS,
    ORANGE,
    build_all_figures,
    load_q1_group_results,
    load_q2_daily_results,
    load_summary_results,
)


class FigureDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp.name) / "train_1"
        self.output_dir = self.project_dir / "paper_output"
        for section in ("tables", "results"):
            source = PROJECT_DIR / "paper_output" / section
            target = self.output_dir / section
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)

    def tearDown(self):
        self.temp.cleanup()

    def test_loaders_accept_verified_results(self):
        q1_table, q1_summary = load_q1_group_results(self.output_dir)
        q2_table, q2_summary = load_q2_daily_results(self.output_dir)
        q1_json, q2_json = load_summary_results(self.output_dir)

        self.assertEqual(len(q1_table), 10)
        self.assertEqual(int(q1_table["optimal_staff"].sum()), q1_summary["total_staff"])
        self.assertEqual(len(q2_table), 10)
        self.assertEqual(int(q2_table["actual_workers"].sum()), q2_summary["actual_workdays"])
        self.assertEqual(q1_json, q1_summary)
        self.assertEqual(q2_json, q2_summary)

    def test_q1_loader_rejects_group_total_mismatch(self):
        path = self.output_dir / "tables" / "q1_group_results.csv"
        table = pd.read_csv(path)
        table.loc[0, "optimal_staff"] += 1
        table.to_csv(path, index=False)
        summary_path = self.output_dir / "results" / "q1_model_results.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["group_staff"][0] += 1
        summary_path.write_text(json.dumps(summary), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "总和"):
            load_q1_group_results(self.output_dir)

    def test_q2_loader_rejects_more_than_one_difference_day(self):
        path = self.output_dir / "tables" / "q2_daily_actual.csv"
        table = pd.read_csv(path)
        table.loc[0, "actual_workers"] += 1
        table.loc[0, "redundant_workers"] += 1
        table.to_csv(path, index=False)
        summary_path = self.output_dir / "results" / "q2_model_results.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["actual_daily_workers"][0] += 1
        summary["actual_workdays"] += 1
        summary_path.write_text(json.dumps(summary), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "仅允许"):
            load_q2_daily_results(self.output_dir)

    def test_build_all_figures_writes_three_formats_to_both_directories(self):
        with warnings.catch_warnings(record=True):
            generated = build_all_figures(self.project_dir, self.output_dir)

        self.assertEqual(len(generated), len(FIGURE_STEMS) * 3 * 2)
        self.assertTrue(all(path.is_file() and path.stat().st_size > 0 for path in generated))
        expected_names = {
            f"{stem}.{suffix}"
            for stem in FIGURE_STEMS
            for suffix in ("png", "pdf", "svg")
        }
        self.assertEqual(
            {path.name for path in self.output_dir.joinpath("figures", "q1_q2").iterdir()},
            expected_names,
        )
        self.assertEqual(
            {path.name for path in self.project_dir.joinpath("figures").iterdir()},
            expected_names,
        )

    def test_comparison_percentage_is_derived_from_json(self):
        q1_path = self.output_dir / "results" / "q1_model_results.json"
        q2_path = self.output_dir / "results" / "q2_model_results.json"
        q1 = json.loads(q1_path.read_text(encoding="utf-8"))
        q2 = json.loads(q2_path.read_text(encoding="utf-8"))
        q1["total_staff"] = 500
        q1["employee_count"] = 500
        q1["group_staff"][-1] += 83
        q2["total_staff"] = 450
        q2["employee_count"] = 450
        q2["actual_workdays"] = 3600
        q2["work_record_count"] = 3600
        q1_path.write_text(json.dumps(q1), encoding="utf-8")
        q2_path.write_text(json.dumps(q2), encoding="utf-8")
        q1_table_path = self.output_dir / "tables" / "q1_group_results.csv"
        q1_table = pd.read_csv(q1_table_path)
        q1_table.loc[9, "optimal_staff"] += 83
        q1_table.to_csv(q1_table_path, index=False)
        q2_actual_path = self.output_dir / "tables" / "q2_daily_actual.csv"
        q2_actual = pd.read_csv(q2_actual_path)
        q2_actual["actual_workers"] = [360] * 10
        q2_actual["minimum_workers"] = [360] * 10
        q2_actual["redundant_workers"] = 0
        q2_actual.loc[6, "minimum_workers"] = 359
        q2_actual.loc[6, "redundant_workers"] = 1
        q2_actual.to_csv(q2_actual_path, index=False)
        q2_lower_path = self.output_dir / "tables" / "q2_daily_lower_bound.csv"
        q2_lower = pd.read_csv(q2_lower_path)
        q2_lower["minimum_workers"] = q2_actual["minimum_workers"]
        q2_lower["cumulative_minimum"] = q2_lower["minimum_workers"].cumsum()
        q2_lower.to_csv(q2_lower_path, index=False)
        q2["daily_lower_bound"] = q2_actual["minimum_workers"].tolist()
        q2["actual_daily_workers"] = q2_actual["actual_workers"].tolist()
        q2["daily_lower_bound_total"] = 3599
        q2_path.write_text(json.dumps(q2), encoding="utf-8")

        q1_summary, q2_summary = load_summary_results(self.output_dir)
        difference = q1_summary["total_staff"] - q2_summary["total_staff"]
        ratio = difference / q1_summary["total_staff"]
        self.assertEqual(difference, 50)
        self.assertAlmostEqual(ratio, 0.10)

    def test_repeated_figure_builds_are_byte_identical(self):
        with warnings.catch_warnings(record=True):
            build_all_figures(self.project_dir, self.output_dir)
        figure_dir = self.output_dir / "figures" / "q1_q2"
        first = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in sorted(figure_dir.iterdir())
        }

        with warnings.catch_warnings(record=True):
            build_all_figures(self.project_dir, self.output_dir)
        second = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in sorted(figure_dir.iterdir())
        }
        self.assertEqual(first, second)

    def test_main_figures_have_no_internal_titles(self):
        q1_table, q1_summary = load_q1_group_results(self.output_dir)
        q2_table, q2_summary = load_q2_daily_results(self.output_dir)
        captured = []

        def capture_figure(fig, destination, stem):
            captured.append(fig)
            return []

        try:
            with patch.object(figures, "_save_figure", side_effect=capture_figure):
                figures.plot_q1_group_staff(
                    q1_table, q1_summary, self.output_dir
                )
                figures.plot_q2_daily_lower_actual(
                    q2_table, q2_summary, self.output_dir
                )
                figures.plot_q1_q2_staff_comparison(
                    q1_summary, q2_summary, self.output_dir
                )

            self.assertEqual(len(captured), 3)
            self.assertEqual(
                [figure.axes[0].get_title() for figure in captured],
                ["", "", ""],
            )
        finally:
            for figure in captured:
                plt.close(figure)

    def test_q1_uses_orange_only_for_maximum_and_blue_for_all_other_bars(self):
        q1_table, q1_summary = load_q1_group_results(self.output_dir)
        captured = []

        def capture_figure(fig, destination, stem):
            captured.append(fig)
            return []

        try:
            with patch.object(figures, "_save_figure", side_effect=capture_figure):
                figures.plot_q1_group_staff(
                    q1_table, q1_summary, self.output_dir
                )

            values = q1_table["optimal_staff"].tolist()
            expected = [
                mcolors.to_rgba(ORANGE if value == max(values) else BLUE)
                for value in values
            ]
            actual = [
                patch.get_facecolor()
                for patch in captured[0].axes[0].patches[: len(values)]
            ]
            self.assertEqual(actual, expected)
        finally:
            for figure in captured:
                plt.close(figure)


if __name__ == "__main__":
    unittest.main()
