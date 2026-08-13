import csv
import json
import os
import platform
from math import asin, atan2, cos, pi, sin, sqrt
from pathlib import Path

# The sandbox may not permit a user config directory; keep Matplotlib's cache
# outside the project so the formal command remains warning-free and portable.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/q1-matplotlib")

import matplotlib.pyplot as plt
import numpy as np

R = 105.0  # rotor circumradius, mm (210 mm outer diameter)
e = 15.0   # eccentricity, mm
B = 50.0   # rotor width, mm
PHASE_DEG = 69.0
CONTACT_DIAMETER_MM = 2.0 * (R - 2.0 * e)
ANGLE_SAMPLES = 10_001
NUMERICAL_TOLERANCE_CM3 = 1.0e-10
ANALYTIC_GAP_TOLERANCE_MM = 1.0e-12


def rotor_area(d_inner):
    r = d_inner / 2.0
    chord_offset = R / 2.0
    sagitta = r - chord_offset
    half_chord = sqrt(3.0) * R / 2.0
    if sagitta <= 0:
        raise ValueError("The circular flank must lie outside the straight chord.")
    rho = (half_chord**2 + sagitta**2) / (2.0 * sagitta)
    gamma = 2.0 * asin(half_chord / rho)
    segment = 0.5 * rho**2 * (gamma - sin(gamma))
    triangle = 3.0 * sqrt(3.0) * R**2 / 4.0
    return triangle + 3.0 * segment, rho, gamma


def metrics(d_inner):
    a_rotor, rho, gamma = rotor_area(d_inner)
    a_housing = pi * (R**2 + 3.0 * e**2)
    v_free = (a_housing - a_rotor) * B / 1000.0
    v_s = 3.0 * sqrt(3.0) * R * e * B / 1000.0
    v_min = (v_free - 1.5 * v_s) / 3.0
    v_max = v_min + v_s
    cr = v_max / v_min if abs(v_min) > NUMERICAL_TOLERANCE_CM3 else np.inf
    return {
        "d": d_inner, "rho": rho, "gamma_deg": gamma * 180 / pi,
        "A_housing": a_housing, "A_rotor": a_rotor,
        "V_free": v_free, "Vmin": v_min, "Vs": v_s,
        "Vmax": v_max, "CR": cr,
        "Vd_attachment": 3.0 * v_max,
        "three_face_swept_sum": 3.0 * v_s,
    }


def volume(theta_deg, d_inner=147.0, phase_deg=PHASE_DEG):
    m = metrics(d_inner)
    arg = np.deg2rad(2.0 * (np.asarray(theta_deg) - phase_deg) / 3.0)
    return m["Vmin"] + 0.5 * m["Vs"] * (1.0 - np.cos(arg))


def bisect_zero_clearance(low=150.0, high=161.7, iterations=80):
    """Deterministic root of the scalar extension Vmin(d)=0."""
    if metrics(low)["Vmin"] <= 0 or metrics(high)["Vmin"] >= 0:
        raise ValueError("The root bracket does not straddle Vmin(d)=0.")
    for _ in range(iterations):
        middle = (low + high) / 2.0
        if metrics(middle)["Vmin"] > 0:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def analytic_gap_mm(d_inner):
    """Formal approved-geometry criterion: g(d)=R-2e-d/2."""
    return R - 2.0 * e - d_inner / 2.0


def geometry_status(d_inner):
    gap = analytic_gap_mm(d_inner)
    if gap > ANALYTIC_GAP_TOLERANCE_MM:
        return "noninterfering_ideal_geometry", "Conditional non-interfering ideal geometry (d < 150 mm)."
    if abs(gap) <= ANALYTIC_GAP_TOLERANCE_MM:
        return "contact_boundary", "Conditional contact boundary of the approved ideal geometry (d = 150 mm)."
    return "entity_overlap", "Nonphysical algebraic continuation: ideal-geometry entity overlap (d > 150 mm)."


def thermal_phase_deg(theta_deg):
    """State coordinate for the 1080-degree thermodynamic event cycle."""
    return np.mod(np.asarray(theta_deg) - PHASE_DEG, 1080.0)


def cyclic_difference(a, b, period):
    return np.abs(np.mod(np.asarray(a) - np.asarray(b) + period / 2.0, period) - period / 2.0)


def numerical_checks(d_inner=147.0):
    """Check the 540-degree geometry period and three-chamber conservation."""
    theta = np.linspace(0.0, 1080.0, ANGLE_SAMPLES)
    va, vb, vc = volume(theta, d_inner), volume(theta - 360.0, d_inner), volume(theta - 720.0, d_inner)
    m = metrics(d_inner)
    return {
        "angle_samples": ANGLE_SAMPLES,
        "geometric_volume_min_period_deg": 540.0,
        "geometric_period_max_abs_error_cm3": float(np.max(np.abs(va - volume(theta + 540.0, d_inner)))),
        "three_chamber_conservation_max_abs_error_cm3": float(np.max(np.abs(va + vb + vc - m["V_free"]))),
        "thermodynamic_state_cycle_deg": 1080.0,
        "thermal_state_1080_cycle_max_error_deg": float(np.max(cyclic_difference(thermal_phase_deg(theta), thermal_phase_deg(theta + 1080.0), 1080.0))),
        "thermal_state_540_cycle_difference_deg": float(np.max(cyclic_difference(thermal_phase_deg(theta), thermal_phase_deg(theta + 540.0), 1080.0))),
    }


def _rotor_profile_points(d_inner, points_per_arc=81):
    """Minor-arc rotor boundary for the optional polygonal cross-check only."""
    half_chord = sqrt(3.0) * R / 2.0
    sagitta = (d_inner - R) / 2.0
    rho = (half_chord**2 + sagitta**2) / (2.0 * sagitta)
    alpha = atan2(half_chord, rho - sagitta)
    points = []
    for side in range(3):
        normal = 2.0 * pi * side / 3.0
        centre = np.array([(d_inner / 2.0 - rho) * cos(normal), (d_inner / 2.0 - rho) * sin(normal)])
        for arc_angle in np.linspace(-alpha, alpha, points_per_arc, endpoint=(side == 2)):
            local_x, local_y = rho * cos(arc_angle), rho * sin(arc_angle)
            points.append(centre + np.array([cos(normal) * local_x - sin(normal) * local_y, sin(normal) * local_x + cos(normal) * local_y]))
    return np.asarray(points)


def optional_shapely_check():
    """Shapely is optional; the analytic criterion remains the formal evidence."""
    try:
        import shapely
        from shapely.geometry import Polygon
    except ImportError:
        return {"available": False, "status": "skipped", "reason": "Shapely is not installed."}
    t = np.linspace(0.0, 6.0 * pi, 6001)
    housing = Polygon(np.column_stack((e * np.cos(t) + R * np.cos(t / 3.0), e * np.sin(t) + R * np.sin(t / 3.0))))
    poses = np.linspace(0.0, 1080.0, 121)
    cases = {}
    for d_inner in (147.0, CONTACT_DIAMETER_MM, 150.01):
        base, max_exterior_area = _rotor_profile_points(d_inner), 0.0
        for theta_deg in poses:
            theta_rad = np.deg2rad(theta_deg)
            orientation = theta_rad / 3.0 + pi
            rotation = np.array([[cos(orientation), -sin(orientation)], [sin(orientation), cos(orientation)]])
            rotor = Polygon(base @ rotation.T + np.array([e * cos(theta_rad), e * sin(theta_rad)]))
            max_exterior_area = max(max_exterior_area, rotor.difference(housing).area)
        cases[f"{d_inner:.2f}"] = {"max_exterior_area_mm2": max_exterior_area, "within_polygon_tolerance": max_exterior_area <= 1.0e-3}
    return {
        "available": True, "status": "completed", "shapely_version": shapely.__version__,
        "pose_samples": len(poses), "housing_samples": len(t), "rotor_points_per_arc": 81,
        "exterior_area_tolerance_mm2": 1.0e-3, "cases": cases,
        "interpretation": "Cross-check only; analytic g(d)=R-2e-d/2 is the formal contact evidence.",
    }


EVENTS = (
    (69.0, "compression_TDC_combustion_start", "minimum"),
    (339.0, "exhaust_opening", "maximum"),
    (609.0, "intake_opening", "minimum"),
    (879.0, "intake_closing_compression_start", "maximum"),
    (1149.0, "next_compression_TDC", "minimum"),
)
CSV_FIELDS = (
    "record_type", "d_inner_mm", "input_precision_note", "root_kind", "event_angle_deg", "event_name",
    "A_volume_cm3", "B_volume_cm3", "C_volume_cm3", "A_min_max_state", "Vmin_cm3", "Vs_single_cm3",
    "Vmax_cm3", "CR", "attachment_3Vmax_cm3", "three_face_swept_sum_cm3", "analytic_gap_mm",
    "geometry_status", "physical_interpretation",
)


def _number(value):
    if value is None:
        return ""
    if np.isinf(value):
        return "infinite"
    return f"{float(value):.12f}"


def _base_row(d_inner, root_kind="not_a_root"):
    m = metrics(d_inner)
    status, interpretation = geometry_status(d_inner)
    return {
        "d_inner_mm": _number(d_inner),
        "input_precision_note": "full double-precision input recorded; root row is not rounded before evaluation",
        "root_kind": root_kind,
        "Vmin_cm3": _number(m["Vmin"]), "Vs_single_cm3": _number(m["Vs"]), "Vmax_cm3": _number(m["Vmax"]), "CR": _number(m["CR"]),
        "attachment_3Vmax_cm3": _number(m["Vd_attachment"]), "three_face_swept_sum_cm3": _number(m["three_face_swept_sum"]),
        "analytic_gap_mm": _number(analytic_gap_mm(d_inner)), "geometry_status": status, "physical_interpretation": interpretation,
    }


def write_csv(output_path, d_zero):
    rows = []
    for d_inner in (132.3, 147.0, 150.0, 150.01, d_zero, 161.7):
        row = _base_row(d_inner, "algebraic_zero_clearance_root" if d_inner == d_zero else "not_a_root")
        row.update({"record_type": "diameter_summary", "event_angle_deg": "", "event_name": "", "A_volume_cm3": "", "B_volume_cm3": "", "C_volume_cm3": "", "A_min_max_state": ""})
        rows.append(row)
    for angle, name, state in EVENTS:
        row = _base_row(147.0)
        row.update({"record_type": "event_angle", "event_angle_deg": _number(angle), "event_name": name,
                    "A_volume_cm3": _number(volume(angle, 147.0)), "B_volume_cm3": _number(volume(angle - 360.0, 147.0)),
                    "C_volume_cm3": _number(volume(angle - 720.0, 147.0)), "A_min_max_state": state})
        rows.append(row)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def plot_outputs(output_path, d_zero):
    theta = np.linspace(0.0, 1080.0, 2001)
    va, vb, vc = volume(theta), volume(theta - 360.0), volume(theta - 720.0)
    physical_ds = np.linspace(132.3, CONTACT_DIAMETER_MM, 400, endpoint=False)
    algebraic_ds = np.linspace(CONTACT_DIAMETER_MM + 0.001, d_zero - 0.001, 400)
    plt.rcParams.update({"font.size": 9.5, "axes.unicode_minus": False})
    fig, axes = plt.subplots(1, 2, figsize=(11.7, 4.25), constrained_layout=True)
    ax = axes[0]
    ax.plot(theta, va, lw=2.0, label="Chamber A")
    ax.plot(theta, vb, lw=1.4, label="Chamber B")
    ax.plot(theta, vc, lw=1.4, label="Chamber C")
    for x, label in ((69, "TDC"), (339, "EO"), (609, "IO"), (879, "IC")):
        ax.axvline(x, color="0.60", lw=0.8, ls="--")
        ax.text(x + 5, 445, label, rotation=90, va="top", color="0.35")
    ax.text(535, 24, "1149 deg: next-cycle TDC (outside viewport)", ha="center", color="0.35", fontsize=8)
    ax.set(xlabel="Eccentric-shaft angle (deg)", ylabel="Chamber volume (cm$^3$)", xlim=(0, 1080), title="Geometry: 540 deg period; thermal states: 1080 deg cycle")
    ax.grid(alpha=0.22); ax.legend(frameon=False, ncol=3, loc="upper center")
    ax = axes[1]
    ax.plot(physical_ds, [metrics(float(d))["CR"] for d in physical_ds], color="#c43c35", lw=2.2, label="physical curve: d < 150 mm")
    ax.plot(algebraic_ds, [metrics(float(d))["CR"] for d in algebraic_ds], color="#8d8d8d", lw=1.5, ls="--", label="nonphysical algebraic extension (entity overlap)")
    baseline = metrics(147.0)
    ax.scatter([147.0], [baseline["CR"]], color="#c43c35", zorder=3)
    ax.annotate("baseline 147 mm", (147.0, baseline["CR"]), xytext=(4, 7), textcoords="offset points", fontsize=8)
    ax.axvline(CONTACT_DIAMETER_MM, color="#333333", lw=1.0, ls="--")
    ax.annotate("150 mm contact boundary", (150.15, 18), rotation=90, va="bottom", color="#333333", fontsize=8)
    ax.axvspan(CONTACT_DIAMETER_MM, 161.7, color="#707070", alpha=0.10)
    ax.text(155.8, 42, "d > 150 mm:\nideal-geometry entity overlap", ha="center", va="top", color="#4d4d4d", fontsize=8)
    ax.set(xlabel="Rotor inner-circle diameter (mm)", ylabel="Compression ratio", xlim=(132.3, 161.7), ylim=(0, 50))
    ax.grid(alpha=0.22); ax.legend(frameon=False, loc="upper left", fontsize=7.5)
    fig.savefig(output_path, dpi=220, metadata={"Software": "q1_geometry.py", "Creation Time": None})
    plt.close(fig)


def write_metadata(output_path, d_zero, checks, shapely_check, csv_rows):
    baseline = metrics(147.0)
    payload = {
        "schema_version": 1, "command": "python 第4题第一二三问修订源码/q1_geometry.py", "script": "第4题第一二三问修订源码/q1_geometry.py",
        "model_scope": "Approved symmetric minor circular-arc flanks only; not a manufacturing, thermal-expansion, or sealing model.",
        "python": platform.python_version(), "dependencies": {"numpy": np.__version__, "matplotlib": plt.matplotlib.__version__},
        "parameters_mm": {"R": R, "e": e, "B": B, "phase_deg": PHASE_DEG},
        "scan": {"angle_samples": ANGLE_SAMPLES, "angle_range_deg": [0.0, 1080.0], "analytic_gap_tolerance_mm": ANALYTIC_GAP_TOLERANCE_MM, "numerical_volume_tolerance_cm3": NUMERICAL_TOLERANCE_CM3},
        "formal_contact_criterion": {"formula": "g(d)=R-2e-d/2", "d_contact_mm": CONTACT_DIAMETER_MM, "meaning": "d<150 noninterfering; d=150 contact; d>150 entity overlap, conditional on the approved ideal geometry."},
        "algebraic_root": {"root_kind": "Vmin(d)=0 only", "d_zero_mm": d_zero, "root_residual_cm3": metrics(d_zero)["Vmin"], "meaning": "Not a mechanical contact or interference boundary."},
        "baseline_d_147": {"Vmin_cm3": baseline["Vmin"], "Vs_single_cm3": baseline["Vs"], "Vmax_cm3": baseline["Vmax"], "CR": baseline["CR"], "attachment_3Vmax_cm3": baseline["Vd_attachment"], "three_face_swept_sum_cm3": baseline["three_face_swept_sum"]},
        "period_and_conservation_checks": checks, "optional_shapely_polygon_cross_check": shapely_check,
        "outputs": {"csv": "q1_results.csv", "figure": "figure/q1_corrected_volume_cr.png", "metadata": "q1_run_metadata.json", "csv_rows": csv_rows},
        "determinism": "No timestamps are written; CSV/JSON serialization and PNG metadata are fixed for repeatable output in a fixed environment.",
    }
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def main():
    output_dir = Path(__file__).resolve().parent
    figure_dir = output_dir / "figure"
    figure_dir.mkdir(parents=True, exist_ok=True)
    d_zero = bisect_zero_clearance()
    checks, shapely_check = numerical_checks(), optional_shapely_check()
    csv_rows = write_csv(output_dir / "q1_results.csv", d_zero)
    plot_outputs(figure_dir / "q1_corrected_volume_cr.png", d_zero)
    write_metadata(output_dir / "q1_run_metadata.json", d_zero, checks, shapely_check, csv_rows)
    baseline = metrics(147.0)
    print(f"d_contact_mm={CONTACT_DIAMETER_MM:.12f}")
    print(f"d_zero_mm={d_zero:.15f} (algebraic Vmin=0 root only)")
    print(f"baseline_d=147: Vmin={baseline['Vmin']:.12f}, Vs={baseline['Vs']:.12f}, Vmax={baseline['Vmax']:.12f}, CR={baseline['CR']:.12f}")
    print(f"period_error_cm3={checks['geometric_period_max_abs_error_cm3']:.3e}; conservation_error_cm3={checks['three_chamber_conservation_max_abs_error_cm3']:.3e}; angle_samples={ANGLE_SAMPLES}")
    print(f"shapely_check={shapely_check['status']}; csv_rows={csv_rows}")
    print(output_dir / "q1_results.csv")
    print(figure_dir / "q1_corrected_volume_cr.png")
    print(output_dir / "q1_run_metadata.json")


if __name__ == "__main__":
    main()
