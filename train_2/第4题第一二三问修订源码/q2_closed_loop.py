"""Question 2: calibrated open-system, zero-dimensional rotary-engine model.

This candidate model uses the verified Question 1 single-chamber swept-volume
convention ``Vs = 409.197003288147 cm^3``.  It does *not* treat the public
AIE 225CS curve as a target-engine measurement: the 16 reference points below
are manual digitisation candidates used only to calibrate transferable model
parameters.  Consequently every output for the requested engine is a
conditioned, cross-engine model prediction.

The state is integrated over a 1080 degree eccentric-shaft thermodynamic
cycle.  In addition to mass, fresh charge and internal energy, work and wall
heat are integrated as RK4 states.  This avoids mixing a post-step state with
the preceding angle when computing cycle work, peak pressure or heat loss.

Run from this directory, or from the project root:
    python 第4题第一二三问修订源码/q2_closed_loop.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.optimize import least_squares


ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figure"
PAPER_FIG = ROOT.parent / "figures"
FIG.mkdir(exist_ok=True)
PAPER_FIG.mkdir(exist_ok=True)

# Public AIE 225CS curve: manually digitised candidate points, not raw bench
# data and not measurements of the requested engine.  lb ft -> N m.
RPM_DATA = np.array(
    [5000, 5167, 5333, 5500, 5667, 5833, 6000, 6167,
     6333, 6500, 6667, 6833, 7000, 7167, 7333, 7500], dtype=float
)
TQ_DATA = np.array(
    [22.5, 24.2, 26.6, 28.1, 27.6, 28.7, 29.0, 29.1,
     29.3, 29.6, 29.8, 30.0, 30.5, 30.4, 30.7, 30.9], dtype=float
) * 1.3558179483

R_GAS = 287.0
CV = 718.0
CP = 1005.0
GAMMA = 1.40
LHV = 43.5e6
AFR = 14.5
P_IN = 1.01325e5
P_EX = 1.055e5
T_IN = 298.15
T_EX = 720.0
T_WALL = 573.15
CD_IN, CD_EX = 0.92, 0.95
A_LEAK = 0.03e-6
VS_TARGET_M3 = 409.197003288147e-6
CR_TARGET = 11.063792444592519
CYCLE_START_DEG = -30.0
CYCLE_END_DEG = 1050.0
CYCLE_DEG = CYCLE_END_DEG - CYCLE_START_DEG
FUEL_MASS_DEFINITION = (
    "mfuel_per_cycle is the fuel implied by the fresh charge at the start of "
    "the converged 1080-degree cycle, held fixed during that cycle"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def volume(theta_deg: float, vs_m3: float, compression_ratio: float) -> tuple[float, float]:
    """One-chamber volume [m3] and dV/dtheta [m3/degree]."""
    vmin = vs_m3 / (compression_ratio - 1.0)
    phase = math.radians(2.0 * theta_deg / 3.0)
    volume_m3 = vmin + 0.5 * vs_m3 * (1.0 - math.cos(phase))
    dvol_ddeg = 0.5 * vs_m3 * math.sin(phase) * math.pi / 270.0
    return volume_m3, dvol_ddeg


def port_area(theta_deg: float, opening_deg: float, closing_deg: float, area_m2: float) -> float:
    if theta_deg < opening_deg or theta_deg > closing_deg:
        return 0.0
    return area_m2 * math.sin(math.pi * (theta_deg - opening_deg) / (closing_deg - opening_deg))


def nozzle_mass_flow(p_up: float, t_up: float, p_down: float, cd: float, area_m2: float) -> float:
    """Quasi-steady compressible nozzle flow [kg/s], positive from up to down."""
    if area_m2 <= 0.0 or p_up <= p_down:
        return 0.0
    pressure_ratio = p_down / p_up
    critical_ratio = (2.0 / (GAMMA + 1.0)) ** (GAMMA / (GAMMA - 1.0))
    if pressure_ratio <= critical_ratio:
        phi = (2.0 / (GAMMA + 1.0)) ** ((GAMMA + 1.0) / (2.0 * (GAMMA - 1.0)))
    else:
        phi = math.sqrt(max(0.0, 2.0 / (GAMMA - 1.0) * (
            pressure_ratio ** (2.0 / GAMMA)
            - pressure_ratio ** ((GAMMA + 1.0) / GAMMA)
        )))
    return cd * area_m2 * p_up * math.sqrt(GAMMA / (R_GAS * max(t_up, 180.0))) * phi


def fuel_mass_from_fresh_charge(fresh_mass_kg: float, lambda_air: float, eoi_deg: float) -> float:
    """Fuel delivered for one chamber cycle from its fixed-point fresh charge."""
    delivery = max(0.94, 1.0 - 0.00006 * (eoi_deg - 597.0) ** 2)
    return max(fresh_mass_kg, 1e-9) / (AFR * lambda_air) * delivery


def model_rhs(theta_deg: float, state: np.ndarray, rpm: float, vs_m3: float,
              compression_ratio: float, pars: np.ndarray, overlap_deg: float,
              lambda_air: float, ignition_btdc_deg: float, eoi_deg: float,
              mfuel_per_cycle_kg: float) -> tuple[np.ndarray, dict[str, float]]:
    """Cycle ODE per eccentric-shaft degree; W and Qwall are accumulated states."""
    area_in_mm2, area_ex_mm2, heat_scale, burn_duration_deg, eta_comb, friction_scale, k_linear, k_quad = pars
    del friction_scale  # Used after the indicated work calculation, not in the thermodynamic RHS.
    scale = (vs_m3 / 225e-6) ** (2.0 / 3.0)
    area_in_m2 = area_in_mm2 * 1e-6 * scale
    area_ex_m2 = area_ex_mm2 * 1e-6 * scale
    speed_offset = (rpm - 6000.0) / 1000.0
    p_in_effective = P_IN * math.exp(k_linear * speed_offset + k_quad * speed_offset * speed_offset)
    sec_per_degree = 1.0 / (6.0 * rpm)

    # Keep exhaust opening and intake closure fixed; overlap changes the two
    # neighbouring port boundaries about their 533 degree centre.
    exhaust_open, exhaust_close = 150.0, 533.0 + overlap_deg / 2.0
    intake_open, intake_close = 533.0 - overlap_deg / 2.0, 850.0

    mass, fresh_mass, internal_energy, _, _ = state
    mass = max(mass, 1e-10)
    temperature = max(180.0, internal_energy / (mass * CV))
    chamber_volume, dvol_ddeg = volume(theta_deg, vs_m3, compression_ratio)
    pressure = max(2e4, mass * R_GAS * temperature / chamber_volume)

    a_in = port_area(theta_deg, intake_open, intake_close, area_in_m2)
    a_ex = port_area(theta_deg, exhaust_open, exhaust_close, area_ex_m2)
    m_in_intake = nozzle_mass_flow(p_in_effective, T_IN, pressure, CD_IN, a_in)
    m_out_intake = nozzle_mass_flow(pressure, temperature, p_in_effective, CD_IN, a_in)
    m_out_exhaust = nozzle_mass_flow(pressure, temperature, P_EX, CD_EX, a_ex)
    m_in_exhaust = nozzle_mass_flow(P_EX, T_EX, pressure, CD_EX, a_ex)
    m_out_leak = nozzle_mass_flow(pressure, temperature, P_IN, 0.75, A_LEAK)
    m_in_leak = nozzle_mass_flow(P_IN, T_IN, pressure, 0.75, A_LEAK)

    # Each successive cycle takes its own fresh charge at cycle start.  That
    # quantity stays fixed inside the RK4 stages, so the heat-release energy
    # and the reported brake-thermal-efficiency denominator have one meaning.
    del lambda_air, eoi_deg
    burn_progress = (theta_deg + ignition_btdc_deg) / burn_duration_deg
    dxb_ddeg = 0.0 if burn_progress <= 0.0 or burn_progress >= 1.0 else (
        15.0 / burn_duration_deg * burn_progress ** 2 * math.exp(-5.0 * burn_progress ** 3)
    )
    heat_release_ddeg = eta_comb * mfuel_per_cycle_kg * LHV * dxb_ddeg

    htc = 95.0 * heat_scale * (pressure / 1e5) ** 0.8 * (max(temperature, 250.0) / 300.0) ** -0.53 * (rpm / 6000.0) ** 0.8
    reference_area = 0.014 * scale
    wall_area = reference_area * (chamber_volume / (vs_m3 + vs_m3 / (compression_ratio - 1.0))) ** 0.30
    wall_heat_ddeg = htc * wall_area * (temperature - T_WALL) * sec_per_degree

    dm_ddeg = (m_in_intake + m_in_exhaust + m_in_leak - m_out_intake - m_out_exhaust - m_out_leak) * sec_per_degree
    fresh_fraction = max(0.0, min(1.0, fresh_mass / mass))
    dfresh_ddeg = (
        m_in_intake + m_in_leak
        - (m_out_intake + m_out_exhaust + m_out_leak) * fresh_fraction
    ) * sec_per_degree
    denergy_ddeg = (
        heat_release_ddeg - pressure * dvol_ddeg - wall_heat_ddeg
        + (m_in_intake * CP * T_IN + m_in_exhaust * CP * T_EX + m_in_leak * CP * T_IN
           - (m_out_intake + m_out_exhaust + m_out_leak) * CP * temperature) * sec_per_degree
    )

    derivatives = np.array([dm_ddeg, dfresh_ddeg, denergy_ddeg, pressure * dvol_ddeg, wall_heat_ddeg], dtype=float)
    diagnostics = {
        "pressure_Pa": pressure,
        "temperature_K": temperature,
        "volume_m3": chamber_volume,
        "dV_ddeg_m3": dvol_ddeg,
        "mfuel_per_cycle_kg": mfuel_per_cycle_kg,
        "p_in_effective_Pa": p_in_effective,
    }
    return derivatives, diagnostics


def rk4_step(theta_deg: float, state: np.ndarray, step_deg: float, *args: Any) -> np.ndarray:
    k1, _ = model_rhs(theta_deg, state, *args)
    k2, _ = model_rhs(theta_deg + 0.5 * step_deg, state + 0.5 * step_deg * k1, *args)
    k3, _ = model_rhs(theta_deg + 0.5 * step_deg, state + 0.5 * step_deg * k2, *args)
    k4, _ = model_rhs(theta_deg + step_deg, state + step_deg * k3, *args)
    next_state = state + step_deg * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
    next_state[0] = max(next_state[0], 1e-9)
    next_state[1] = min(max(next_state[1], 0.0), next_state[0])
    next_state[2] = max(next_state[2], next_state[0] * CV * 180.0)
    return next_state


def fmep_bar(rpm: float, vs_m3: float, friction_scale: float) -> float:
    source_fmep_pa = (0.23 + (rpm - 4600.0) * (0.385 - 0.23) / (7500.0 - 4600.0)) * 1e5 * friction_scale
    size_ratio = (vs_m3 / 225e-6) ** (1.0 / 3.0)
    return source_fmep_pa * (0.70 + 0.30 * size_ratio ** 2 * (rpm / 6000.0) ** 2) / 1e5


def simulate_source_batch(rpms: np.ndarray, vs_m3: float, compression_ratio: float,
                          pars: np.ndarray, step_deg: float = 1.0,
                          max_cycles: int = 20, cycle_tolerance: float = 2e-5,
                          free_by_case: np.ndarray | None = None) -> dict[str, np.ndarray | int]:
    """Vectorised 1-degree source-curve simulation used only for calibration.

    All sixteen source speeds share the same geometric angle grid but retain
    independent thermodynamic states.  This is algebraically the same RK4
    update as :func:`simulate`, while making deterministic multi-start fitting
    computationally feasible.
    """
    speeds = np.asarray(rpms, dtype=float)
    ncase = speeds.size
    area_in_mm2, area_ex_mm2, heat_scale, burn_duration_deg, eta_comb, friction_scale, k_linear, k_quad = pars
    scale = (vs_m3 / 225e-6) ** (2.0 / 3.0)
    area_in_m2, area_ex_m2 = area_in_mm2 * 1e-6 * scale, area_ex_mm2 * 1e-6 * scale
    speed_offset = (speeds - 6000.0) / 1000.0
    p_in_effective = P_IN * np.exp(k_linear * speed_offset + k_quad * speed_offset ** 2)
    sec_per_degree = 1.0 / (6.0 * speeds)
    if free_by_case is None:
        eta_case = np.full(ncase, eta_comb)
        friction_case = np.full(ncase, friction_scale)
    else:
        free_case = np.asarray(free_by_case, dtype=float)
        if free_case.shape != (ncase, 2):
            raise ValueError("free_by_case must have one [eta_comb, friction_scale] pair per speed")
        eta_case, friction_case = free_case[:, 0], free_case[:, 1]
    grid = np.arange(CYCLE_START_DEG, CYCLE_END_DEG + 0.5 * step_deg, step_deg)
    if not np.isclose(grid[-1], CYCLE_END_DEG):
        raise ValueError("step_deg must divide the 1080 degree thermodynamic cycle")
    v0, _ = volume(CYCLE_START_DEG, vs_m3, compression_ratio)
    m0 = P_IN * v0 / (R_GAS * T_IN)
    thermo = np.column_stack((np.full(ncase, m0), np.full(ncase, m0), np.full(ncase, m0 * CV * T_IN)))
    previous: np.ndarray | None = None
    residuals = np.full(ncase, np.inf)

    def batch_nozzle(p_up: np.ndarray, t_up: np.ndarray | float, p_down: np.ndarray | float, cd: float, area: float) -> np.ndarray:
        up = np.asarray(p_up, dtype=float)
        down = np.asarray(p_down, dtype=float)
        active = (area > 0.0) & (up > down)
        ratio = np.divide(down, up, out=np.ones_like(up), where=up > 0.0)
        critical = (2.0 / (GAMMA + 1.0)) ** (GAMMA / (GAMMA - 1.0))
        phi_choked = (2.0 / (GAMMA + 1.0)) ** ((GAMMA + 1.0) / (2.0 * (GAMMA - 1.0)))
        phi_sub = np.sqrt(np.maximum(0.0, 2.0 / (GAMMA - 1.0) * (ratio ** (2.0 / GAMMA) - ratio ** ((GAMMA + 1.0) / GAMMA))))
        phi = np.where(ratio <= critical, phi_choked, phi_sub)
        return np.where(active, cd * area * up * np.sqrt(GAMMA / (R_GAS * np.maximum(t_up, 180.0))) * phi, 0.0)

    def rhs(theta_deg: float, state: np.ndarray, mfuel_per_cycle: np.ndarray) -> np.ndarray:
        mass = np.maximum(state[:, 0], 1e-10)
        fresh = state[:, 1]
        temperature = np.maximum(180.0, state[:, 2] / (mass * CV))
        chamber_volume, dvol_ddeg = volume(theta_deg, vs_m3, compression_ratio)
        pressure = np.maximum(2e4, mass * R_GAS * temperature / chamber_volume)
        exhaust_open, exhaust_close = 150.0, 533.0 + 128.0 / 2.0
        intake_open, intake_close = 533.0 - 128.0 / 2.0, 850.0
        a_in = port_area(theta_deg, intake_open, intake_close, area_in_m2)
        a_ex = port_area(theta_deg, exhaust_open, exhaust_close, area_ex_m2)
        mi_in = batch_nozzle(p_in_effective, T_IN, pressure, CD_IN, a_in)
        mi_out = batch_nozzle(pressure, temperature, p_in_effective, CD_IN, a_in)
        me_out = batch_nozzle(pressure, temperature, P_EX, CD_EX, a_ex)
        me_in = batch_nozzle(np.full(ncase, P_EX), T_EX, pressure, CD_EX, a_ex)
        ml_out = batch_nozzle(pressure, temperature, P_IN, 0.75, A_LEAK)
        ml_in = batch_nozzle(np.full(ncase, P_IN), T_IN, pressure, 0.75, A_LEAK)
        burn_progress = (theta_deg + 18.0) / burn_duration_deg
        dxb_ddeg = 0.0 if burn_progress <= 0.0 or burn_progress >= 1.0 else 15.0 / burn_duration_deg * burn_progress ** 2 * math.exp(-5.0 * burn_progress ** 3)
        heat_release = eta_case * mfuel_per_cycle * LHV * dxb_ddeg
        htc = 95.0 * heat_scale * (pressure / 1e5) ** 0.8 * (np.maximum(temperature, 250.0) / 300.0) ** -0.53 * (speeds / 6000.0) ** 0.8
        wall_area = 0.014 * scale * (chamber_volume / (vs_m3 + vs_m3 / (compression_ratio - 1.0))) ** 0.30
        wall_heat = htc * wall_area * (temperature - T_WALL) * sec_per_degree
        dm = (mi_in + me_in + ml_in - mi_out - me_out - ml_out) * sec_per_degree
        fresh_fraction = np.clip(fresh / mass, 0.0, 1.0)
        dfresh = (mi_in + ml_in - (mi_out + me_out + ml_out) * fresh_fraction) * sec_per_degree
        denergy = heat_release - pressure * dvol_ddeg - wall_heat + (
            mi_in * CP * T_IN + me_in * CP * T_EX + ml_in * CP * T_IN
            - (mi_out + me_out + ml_out) * CP * temperature
        ) * sec_per_degree
        return np.column_stack((dm, dfresh, denergy, pressure * dvol_ddeg, wall_heat))

    final_state = None
    for cycle_index in range(1, max_cycles + 1):
        state = np.column_stack((thermo, np.zeros(ncase), np.zeros(ncase)))
        # The batch path uses the same fixed-within-cycle fuel definition as
        # the scalar target/scan solver (lambda=1 and eoi=597 here).
        mfuel_per_cycle = np.maximum(thermo[:, 1], 1e-9) / AFR
        for theta in grid[:-1]:
            k1 = rhs(theta, state, mfuel_per_cycle)
            k2 = rhs(theta + 0.5 * step_deg, state + 0.5 * step_deg * k1, mfuel_per_cycle)
            k3 = rhs(theta + 0.5 * step_deg, state + 0.5 * step_deg * k2, mfuel_per_cycle)
            k4 = rhs(theta + step_deg, state + step_deg * k3, mfuel_per_cycle)
            state += step_deg * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
            state[:, 0] = np.maximum(state[:, 0], 1e-9)
            state[:, 1] = np.clip(state[:, 1], 0.0, state[:, 0])
            state[:, 2] = np.maximum(state[:, 2], state[:, 0] * CV * 180.0)
        thermo = state[:, :3].copy()
        final_state = state
        if previous is not None:
            residuals = np.max(np.abs((thermo - previous) / (np.abs(previous) + 1e-12)), axis=1)
            if bool(np.all(residuals < cycle_tolerance)):
                break
        previous = thermo.copy()
    assert final_state is not None
    imep = final_state[:, 3] / vs_m3 / 1e5
    friction = np.asarray(fmep_bar(speeds, vs_m3, friction_case), dtype=float)
    bmep = np.maximum(0.0, imep - friction)
    torque = bmep * 1e5 * vs_m3 / (2.0 * math.pi)
    return {"torque_Nm": torque, "IMEP_bar": imep, "BMEP_bar": bmep, "FMEP_bar": friction,
            "converged": residuals < cycle_tolerance, "state_relative_residual": residuals,
            "cycles_completed": cycle_index}


def simulate(rpm: float, vs_m3: float, compression_ratio: float, pars: np.ndarray,
             overlap_deg: float = 128.0, lambda_air: float = 1.0,
             ignition_btdc_deg: float = 18.0, eoi_deg: float = 597.0,
             step_deg: float = 3.0, max_cycles: int = 50,
             cycle_tolerance: float = 2e-5, return_trace: bool = False,
             collect_extrema: bool = True) -> dict[str, Any]:
    """Run successive 1080 degree cycles until mass/energy state convergence."""
    grid = np.arange(CYCLE_START_DEG, CYCLE_END_DEG + 0.5 * step_deg, step_deg)
    if not np.isclose(grid[-1], CYCLE_END_DEG):
        raise ValueError("step_deg must divide the 1080 degree thermodynamic cycle")
    v0, _ = volume(CYCLE_START_DEG, vs_m3, compression_ratio)
    thermo_state = np.array([P_IN * v0 / (R_GAS * T_IN), P_IN * v0 / (R_GAS * T_IN), P_IN * v0 * CV / R_GAS], dtype=float)
    previous_end: np.ndarray | None = None
    end_residual = math.inf
    converged = False
    final_cycle_state: np.ndarray | None = None
    final_trace: list[dict[str, float]] = []

    for cycle_index in range(1, max_cycles + 1):
        state = np.r_[thermo_state, 0.0, 0.0]
        cycle_trace: list[dict[str, float]] = []
        pmax_pa = 0.0
        tmax_k = 0.0
        mfuel_per_cycle_kg = fuel_mass_from_fresh_charge(float(state[1]), lambda_air, eoi_deg)
        fresh_charge_start_kg = float(state[1])
        cycle_rhs_args = (rpm, vs_m3, compression_ratio, pars, overlap_deg, lambda_air,
                          ignition_btdc_deg, eoi_deg, mfuel_per_cycle_kg)
        if collect_extrema or return_trace:
            _, d0 = model_rhs(grid[0], state, *cycle_rhs_args)
            pmax_pa = max(pmax_pa, d0["pressure_Pa"])
            tmax_k = max(tmax_k, d0["temperature_K"])
        else:
            d0 = {}
        if return_trace:
            cycle_trace.append({"theta_deg": grid[0], "mass_kg": state[0], "fresh_mass_kg": state[1],
                                "internal_energy_J": state[2], "work_J": state[3], "wall_heat_J": state[4], **d0})
        for theta in grid[:-1]:
            state = rk4_step(theta, state, step_deg, *cycle_rhs_args)
            if collect_extrema or return_trace:
                _, diag = model_rhs(theta + step_deg, state, *cycle_rhs_args)
                pmax_pa = max(pmax_pa, diag["pressure_Pa"])
                tmax_k = max(tmax_k, diag["temperature_K"])
            if return_trace:
                cycle_trace.append({"theta_deg": theta + step_deg, "mass_kg": state[0], "fresh_mass_kg": state[1],
                                    "internal_energy_J": state[2], "work_J": state[3], "wall_heat_J": state[4], **diag})
        thermo_state = state[:3].copy()
        if previous_end is not None:
            end_residual = float(np.max(np.abs((thermo_state - previous_end) / (np.abs(previous_end) + 1e-12))))
            if end_residual < cycle_tolerance:
                converged = True
                final_cycle_state = state.copy()
                final_trace = cycle_trace
                break
        previous_end = thermo_state.copy()
        final_cycle_state = state.copy()
        final_trace = cycle_trace

    assert final_cycle_state is not None
    work_j = float(final_cycle_state[3])
    qwall_j = float(final_cycle_state[4])
    imep_bar = work_j / vs_m3 / 1e5
    friction_bar = fmep_bar(rpm, vs_m3, float(pars[5]))
    bmep_bar = max(0.0, imep_bar - friction_bar)
    torque_nm = bmep_bar * 1e5 * vs_m3 / (2.0 * math.pi)
    power_kw = torque_nm * 2.0 * math.pi * rpm / 60.0 / 1000.0
    pmax_mpa = pmax_pa / 1e6 if collect_extrema or return_trace else float("nan")
    tmax_k = tmax_k if collect_extrema or return_trace else float("nan")
    mfuel_per_cycle_mg = mfuel_per_cycle_kg * 1e6
    fresh_charge_start_mg = fresh_charge_start_kg * 1e6
    fresh_charge_end_mg = float(final_cycle_state[1]) * 1e6
    fuel_power_w = mfuel_per_cycle_kg * LHV * rpm / 60.0
    brake_thermal_efficiency = power_kw * 1000.0 / fuel_power_w if fuel_power_w > 0.0 else float("nan")
    bsfc_g_kwh = mfuel_per_cycle_kg * rpm * 60000.0 / power_kw if power_kw > 0.0 else float("nan")
    return {
        "converged": converged,
        "cycles_completed": cycle_index,
        "state_relative_residual": end_residual,
        "step_deg": step_deg,
        "work_J": work_j,
        "qwall_J": qwall_j,
        "torque_Nm": torque_nm,
        "power_kW": power_kw,
        "IMEP_bar": imep_bar,
        "BMEP_bar": bmep_bar,
        "FMEP_bar": friction_bar,
        "eta_m": bmep_bar / imep_bar if imep_bar > 0.0 else 0.0,
        "eta_b": brake_thermal_efficiency,
        "BSFC_g_kWh": bsfc_g_kwh,
        "fuel_mass_definition": FUEL_MASS_DEFINITION,
        "mfuel_per_cycle_kg": mfuel_per_cycle_kg,
        "mfuel_per_cycle_mg": mfuel_per_cycle_mg,
        "fresh_charge_start_mg": fresh_charge_start_mg,
        "fresh_charge_end_mg": fresh_charge_end_mg,
        "pmax_MPa": pmax_mpa,
        "Tmax_K": tmax_k,
        "trace": final_trace,
    }


FIXED_COEFFICIENTS = np.array([
    361.91521693994156, 606.159284370356, 0.9694097189196712,
    111.2396719111877, 0.7200431789874384, 1.0503262156424105,
    0.07790785923613822, -0.01829931843876515,
], dtype=float)


def expand_free_coefficients(free: np.ndarray) -> np.ndarray:
    """Fit only combustion efficiency and FMEP scale; keep six priors fixed."""
    pars = FIXED_COEFFICIENTS.copy()
    pars[4], pars[5] = free
    return pars


def calibration_residual(free: np.ndarray) -> np.ndarray:
    """All 16 manual candidate points, with the formal one-degree RK4 grid."""
    source = simulate_source_batch(RPM_DATA, 225e-6, 10.0, expand_free_coefficients(free), step_deg=1.0, max_cycles=20)
    torque = np.asarray(source["torque_Nm"], dtype=float)
    if not bool(np.all(source["converged"])):
        return torque - TQ_DATA + 50.0
    return torque - TQ_DATA


def build_one_degree_ode_surrogate() -> dict[str, Any]:
    """Fit a quadratic response surrogate to a deterministic 7x7 ODE screen.

    Each of the 49 nodes is an exact 1-degree RK4 simulation of all 16 manual
    reference speeds.  The inexpensive differentiable surrogate permits a
    reproducible three-start bounded least-squares refinement while retaining
    an explicit exact-ODE screening record.
    """
    eta_nodes = np.linspace(0.72, 1.00, 7)
    friction_nodes = np.linspace(0.55, 1.80, 7)
    free_nodes = np.array([(eta, friction) for eta in eta_nodes for friction in friction_nodes], dtype=float)
    source = simulate_source_batch(
        np.tile(RPM_DATA, len(free_nodes)), 225e-6, 10.0, FIXED_COEFFICIENTS,
        step_deg=1.0, max_cycles=20,
        free_by_case=np.repeat(free_nodes, len(RPM_DATA), axis=0),
    )
    if not bool(np.all(source["converged"])):
        raise RuntimeError("one-degree ODE calibration screen did not converge")
    torque_nodes = np.asarray(source["torque_Nm"], dtype=float).reshape(len(free_nodes), len(RPM_DATA))

    def features(free: np.ndarray) -> np.ndarray:
        values = np.atleast_2d(np.asarray(free, dtype=float))
        eta_scaled = (values[:, 0] - 0.86) / 0.14
        friction_scaled = (values[:, 1] - 1.175) / 0.625
        return np.column_stack((np.ones(len(values)), eta_scaled, friction_scaled,
                                eta_scaled ** 2, eta_scaled * friction_scaled,
                                friction_scaled ** 2))

    design = features(free_nodes)
    coefficients, _, _, _ = np.linalg.lstsq(design, torque_nodes, rcond=None)

    def surrogate_residual(free: np.ndarray) -> np.ndarray:
        return (features(free) @ coefficients).ravel() - TQ_DATA

    screen_sse = np.sum((torque_nodes - TQ_DATA) ** 2, axis=1)
    return {
        "free_nodes": free_nodes,
        "torque_nodes": torque_nodes,
        "screen_sse": screen_sse,
        "screen_minimum": free_nodes[int(np.argmin(screen_sse))],
        "surrogate_residual": surrogate_residual,
        "screen_cycles_completed": int(source["cycles_completed"]),
        "screen_max_state_residual": float(np.max(source["state_relative_residual"])),
    }


def trace_to_array(trace: list[dict[str, float]]) -> np.ndarray:
    return np.asarray([[row[key] for key in ("theta_deg", "pressure_Pa", "temperature_K", "volume_m3", "dV_ddeg_m3", "mass_kg", "fresh_mass_kg", "work_J", "wall_heat_J")] for row in trace], dtype=float)


def chamber_torque_trace(trace: list[dict[str, float]], friction_torque_nm: float) -> list[dict[str, float]]:
    """Construct three 360-degree phase-shifted gas-torque channels.

    theta is the eccentric-shaft angle.  ``p*dV/dtheta_rad`` is gas torque;
    the mean FMEP torque is then subtracted once from the three-chamber sum.
    """
    array = trace_to_array(trace)
    theta = array[:, 0]
    period = CYCLE_DEG
    theta_ext = np.r_[theta, theta[1:] + period]
    p_ext = np.r_[array[:, 1], array[1:, 1]]
    dv_ext = np.r_[array[:, 4], array[1:, 4]]

    def channel(phase_deg: float) -> np.ndarray:
        sample = ((theta + phase_deg - CYCLE_START_DEG) % period) + CYCLE_START_DEG
        pressure = np.interp(sample, theta_ext, p_ext)
        dvol_ddeg = np.interp(sample, theta_ext, dv_ext)
        return pressure * dvol_ddeg * 180.0 / math.pi

    tau_a = channel(0.0)
    tau_b = channel(360.0)
    tau_c = channel(720.0)
    rows: list[dict[str, float]] = []
    for angle, a, b, c in zip(theta, tau_a, tau_b, tau_c):
        total = a + b + c
        rows.append({
            "eccentric_shaft_angle_deg": float(angle),
            "gas_torque_chamber_A_Nm": float(a),
            "gas_torque_chamber_B_Nm": float(b),
            "gas_torque_chamber_C_Nm": float(c),
            "gas_torque_total_Nm": float(total),
            "mean_mechanical_loss_torque_Nm": float(friction_torque_nm),
            "conditional_shaft_torque_Nm": float(total - friction_torque_nm),
        })
    return rows


def write_dict_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_figures(pred_torque: np.ndarray, fitted_mape: float, overlap_rows: list[dict[str, Any]],
                 trace: list[dict[str, float]], torque_rows: list[dict[str, float]]) -> list[Path]:
    outputs: list[Path] = []
    plt.rcParams.update({"font.size": 10, "axes.unicode_minus": False})

    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.0), constrained_layout=True)
    axes[0].plot(RPM_DATA, TQ_DATA, "o", label="manual-digitisation candidates")
    axes[0].plot(RPM_DATA, pred_torque, "-", label="source-engine ODE candidate")
    axes[0].set(xlabel="Speed (r/min)", ylabel="Torque (N m)")
    axes[0].grid(alpha=0.25)
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].text(0.03, 0.05, f"In-sample MAPE = {fitted_mape:.2f}%", transform=axes[0].transAxes, fontsize=8)
    axes[1].plot([row["overlap_deg"] for row in overlap_rows], [row["power_kW"] for row in overlap_rows], "-o", ms=3)
    axes[1].set(xlabel="Overlap angle (degree)", ylabel="Conditioned model power (kW)")
    axes[1].grid(alpha=0.25)
    efficiency_line = axes[2].plot([row["overlap_deg"] for row in overlap_rows], [100.0 * row["eta_b"] for row in overlap_rows], "-o", ms=3, color="tab:green", label="Brake thermal efficiency")[0]
    axes[2].set(xlabel="Overlap angle (degree)", ylabel="Brake thermal efficiency (%)")
    axes[2].grid(alpha=0.25)
    axes_bsfc = axes[2].twinx()
    bsfc_line = axes_bsfc.plot([row["overlap_deg"] for row in overlap_rows], [row["BSFC_g_kWh"] for row in overlap_rows], "-s", ms=3, color="tab:red", label="BSFC")[0]
    axes_bsfc.set_ylabel("BSFC (g kW$^{-1}$ h$^{-1}$)")
    axes[2].legend(handles=[efficiency_line, bsfc_line], frameon=False, fontsize=8, loc="best")
    overlap_fig = FIG / "q2_overlap_response.png"
    fig.savefig(overlap_fig, dpi=220)
    plt.close(fig)
    outputs.append(overlap_fig)

    tr = trace_to_array(trace)
    fig, axes = plt.subplots(2, 1, figsize=(8, 5.6), sharex=True, constrained_layout=True)
    axes[0].plot(tr[:, 0], tr[:, 1] / 1e6)
    axes[0].set(ylabel="Model pressure (MPa)")
    axes[0].grid(alpha=0.25)
    axes[1].plot(tr[:, 0], tr[:, 2])
    axes[1].set(xlabel="Eccentric-shaft angle (degree)", ylabel="Model temperature (K)")
    axes[1].grid(alpha=0.25)
    cycle_fig = FIG / "q2_pressure_temperature_trace.png"
    fig.savefig(cycle_fig, dpi=220)
    plt.close(fig)
    outputs.append(cycle_fig)

    fig, axes = plt.subplots(2, 1, figsize=(9, 5.8), sharex=True, constrained_layout=True)
    angle = [row["eccentric_shaft_angle_deg"] for row in torque_rows]
    axes[0].plot(angle, [row["gas_torque_chamber_A_Nm"] for row in torque_rows], label="Chamber A")
    axes[0].plot(angle, [row["gas_torque_chamber_B_Nm"] for row in torque_rows], label="Chamber B")
    axes[0].plot(angle, [row["gas_torque_chamber_C_Nm"] for row in torque_rows], label="Chamber C")
    axes[0].set(ylabel="Gas torque (N m)")
    axes[0].grid(alpha=0.25)
    axes[0].legend(frameon=False, ncol=3, fontsize=8)
    axes[1].plot(angle, [row["gas_torque_total_Nm"] for row in torque_rows], label="Three-chamber gas torque")
    axes[1].plot(angle, [row["conditional_shaft_torque_Nm"] for row in torque_rows], label="Minus mean mechanical loss")
    axes[1].set(xlabel="Eccentric-shaft angle (degree)", ylabel="Torque (N m)")
    axes[1].grid(alpha=0.25)
    axes[1].legend(frameon=False, fontsize=8)
    torque_fig = FIG / "q2_three_chamber_torque.png"
    fig.savefig(torque_fig, dpi=220)
    plt.close(fig)
    outputs.append(torque_fig)
    return outputs


def main() -> None:
    # Six coefficients are held at submitted engineering priors because the
    # 16 hand-digitised torque values cannot identify all eight independently.
    # The two torque-identifiable coefficients are fit with three deterministic,
    # physically bounded starts on exactly the one-degree formal grid.
    ode_surrogate = build_one_degree_ode_surrogate()
    starts = np.array([[0.74, 0.90], [0.86, 1.10], [0.98, 1.30]], dtype=float)
    fit_records: list[dict[str, Any]] = []
    fitted_free: list[np.ndarray] = []
    for index, start in enumerate(starts, start=1):
        fit = least_squares(ode_surrogate["surrogate_residual"], start, bounds=([0.72, 0.55], [1.00, 1.80]),
                            x_scale=[0.08, 0.15], max_nfev=30, ftol=1e-10, xtol=1e-10,
                            gtol=1e-10, diff_step=0.01, verbose=0)
        moved = float(np.max(np.abs(fit.x - start)))
        fitted_free.append(fit.x.copy())
        fit_records.append({
            "start_index": index, "start_eta_comb": float(start[0]), "start_friction_scale": float(start[1]),
            "eta_comb": float(fit.x[0]), "friction_scale": float(fit.x[1]), "cost": float(fit.cost),
            "status": int(fit.status), "success": bool(fit.success), "message": str(fit.message),
            "nfev": int(fit.nfev), "optimality": float(fit.optimality), "max_parameter_move": moved,
        })
    # Evaluate every selected surrogate candidate back in the exact 1-degree
    # ODE, so final selection never relies only on a response approximation.
    exact = simulate_source_batch(
        np.tile(RPM_DATA, len(fitted_free)), 225e-6, 10.0, FIXED_COEFFICIENTS,
        step_deg=1.0, max_cycles=20,
        free_by_case=np.repeat(np.asarray(fitted_free), len(RPM_DATA), axis=0),
    )
    exact_torque = np.asarray(exact["torque_Nm"], dtype=float).reshape(len(fitted_free), len(RPM_DATA))
    for index, record in enumerate(fit_records):
        residuals_exact = exact_torque[index] - TQ_DATA
        record["exact_ode_cost"] = float(0.5 * np.sum(residuals_exact ** 2))
        record["exact_ode_mape_pct_in_sample"] = float(np.mean(np.abs(residuals_exact) / TQ_DATA) * 100.0)
        record["exact_ode_converged"] = bool(np.all(np.asarray(exact["converged"])[index * len(RPM_DATA):(index + 1) * len(RPM_DATA)]))
        target_candidate = simulate(6000.0, VS_TARGET_M3, CR_TARGET, expand_free_coefficients(fitted_free[index]),
                                    overlap_deg=128.0, step_deg=1.0, max_cycles=60, collect_extrema=False)
        record["target_power_kW"] = float(target_candidate["power_kW"])
        record["target_torque_Nm"] = float(target_candidate["torque_Nm"])
    successful = [record for record in fit_records if record["success"] and record["max_parameter_move"] > 1e-6]
    if not successful:
        raise RuntimeError("no deterministic multi-start calibration reached a converged, moved solution")
    selected = min(successful, key=lambda record: (record["exact_ode_cost"], record["start_index"]))
    free_selected = np.array([selected["eta_comb"], selected["friction_scale"]], dtype=float)
    pars = expand_free_coefficients(free_selected)
    multistart_diagnostics = {
        "eta_comb_range": [float(min(record["eta_comb"] for record in fit_records)), float(max(record["eta_comb"] for record in fit_records))],
        "friction_scale_range": [float(min(record["friction_scale"] for record in fit_records)), float(max(record["friction_scale"] for record in fit_records))],
        "target_power_kW_range": [float(min(record["target_power_kW"] for record in fit_records)), float(max(record["target_power_kW"] for record in fit_records))],
        "exact_ode_cost_range": [float(min(record["exact_ode_cost"] for record in fit_records)), float(max(record["exact_ode_cost"] for record in fit_records))],
        "active_bound_warning": "friction_scale reaches its imposed upper bound 1.80; the source candidate curve does not independently identify this loss scale",
        "selected_friction_scale_at_upper_bound": bool(abs(float(selected["friction_scale"]) - 1.80) < 1e-8),
    }

    source_batch = simulate_source_batch(RPM_DATA, 225e-6, 10.0, pars, step_deg=1.0, max_cycles=20)
    if not bool(np.all(source_batch["converged"])):
        raise RuntimeError("source-model calibration results did not reach cyclic convergence")
    pred_torque = np.asarray(source_batch["torque_Nm"], dtype=float)
    mape = float(np.mean(np.abs(pred_torque - TQ_DATA) / TQ_DATA) * 100.0)
    rmse = float(np.sqrt(np.mean((pred_torque - TQ_DATA) ** 2)))

    target = simulate(6000.0, VS_TARGET_M3, CR_TARGET, pars, overlap_deg=128.0,
                      step_deg=1.0, max_cycles=60, return_trace=True)
    if not target["converged"]:
        raise RuntimeError("target reference-overlap cycle did not reach cyclic convergence")
    target_refined = simulate(6000.0, VS_TARGET_M3, CR_TARGET, pars, overlap_deg=128.0,
                              step_deg=0.5, max_cycles=60, return_trace=False, collect_extrema=False)
    if not target_refined["converged"]:
        raise RuntimeError("0.5 degree reference-cycle refinement did not reach cyclic convergence")
    refinement = {key: {
        "one_degree": target[key], "half_degree": target_refined[key],
        "relative_difference": abs(target_refined[key] - target[key]) / max(abs(target_refined[key]), 1e-12),
    } for key in ("work_J", "torque_Nm", "power_kW", "IMEP_bar", "BMEP_bar", "eta_b", "BSFC_g_kWh")}

    overlap_rows: list[dict[str, Any]] = []
    reference_power = target["power_kW"]
    for overlap in np.arange(20.0, 170.0 + 1e-9, 5.0):
        result = simulate(6000.0, VS_TARGET_M3, CR_TARGET, pars, overlap_deg=float(overlap), step_deg=1.0, max_cycles=60, collect_extrema=False)
        if not result["converged"]:
            raise RuntimeError(f"overlap={overlap:g} degree did not reach cyclic convergence")
        overlap_rows.append({
            "overlap_deg": float(overlap),
            "power_kW": result["power_kW"],
            "power_change_from_128deg_pct": (result["power_kW"] / reference_power - 1.0) * 100.0,
            "BMEP_bar": result["BMEP_bar"],
            "IMEP_bar": result["IMEP_bar"],
            "FMEP_bar": result["FMEP_bar"],
            "eta_m": result["eta_m"],
            "eta_b": result["eta_b"],
            "BSFC_g_kWh": result["BSFC_g_kWh"],
            "fuel_mass_definition": result["fuel_mass_definition"],
            "mfuel_per_cycle_kg": result["mfuel_per_cycle_kg"],
            "mfuel_per_cycle_mg": result["mfuel_per_cycle_mg"],
            "fresh_charge_start_mg": result["fresh_charge_start_mg"],
            "fresh_charge_end_mg": result["fresh_charge_end_mg"],
            "qwall_J": result["qwall_J"],
            "torque_Nm": result["torque_Nm"],
            "cycles_completed": result["cycles_completed"],
            "state_relative_residual": result["state_relative_residual"],
            "converged": result["converged"],
            "interpretation": "conditional model response; 20 degree is scan lower boundary, not a proven physical optimum",
        })

    friction_torque = target["FMEP_bar"] * 1e5 * VS_TARGET_M3 / (2.0 * math.pi)
    torque_rows = chamber_torque_trace(target["trace"], friction_torque)

    # Guard the thermal metrics against a recurrence of mixed fuel-mass
    # denominators.  Every solver route returns the same named cycle quantity.
    thermal_cases = [target, target_refined, *(row for row in overlap_rows)]
    eta_errors = []
    bsfc_errors = []
    definitions = []
    for case in thermal_cases:
        mfuel = float(case["mfuel_per_cycle_kg"])
        power = float(case["power_kW"])
        eta_expected = power * 1000.0 / (mfuel * LHV * 6000.0 / 60.0)
        bsfc_expected = mfuel * 6000.0 * 60000.0 / power
        eta_errors.append(abs(float(case["eta_b"]) - eta_expected))
        bsfc_errors.append(abs(float(case["BSFC_g_kWh"]) - bsfc_expected))
        definitions.append(str(case["fuel_mass_definition"]))
    fuel_mass_consistency = {
        "definition": FUEL_MASS_DEFINITION,
        "all_cases_use_same_definition": bool(all(item == FUEL_MASS_DEFINITION for item in definitions)),
        "checked_cases": len(thermal_cases),
        "maximum_abs_eta_b_formula_error": float(max(eta_errors)),
        "maximum_abs_BSFC_g_kWh_formula_error": float(max(bsfc_errors)),
        "baseline_mfuel_per_cycle_kg": float(target["mfuel_per_cycle_kg"]),
        "refined_mfuel_per_cycle_kg": float(target_refined["mfuel_per_cycle_kg"]),
        "overlap_mfuel_per_cycle_kg_range": [
            float(min(row["mfuel_per_cycle_kg"] for row in overlap_rows)),
            float(max(row["mfuel_per_cycle_kg"] for row in overlap_rows)),
        ],
    }
    if (not fuel_mass_consistency["all_cases_use_same_definition"]
            or fuel_mass_consistency["maximum_abs_eta_b_formula_error"] > 1e-12
            or fuel_mass_consistency["maximum_abs_BSFC_g_kWh_formula_error"] > 1e-9):
        raise RuntimeError("inconsistent Q2 fuel-mass definition in thermal metrics")

    results_path = ROOT / "q2_closed_loop_results.csv"
    with results_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["metric", "value", "unit_or_scope"])
        writer.writerow(["evidence_status", "generated", "requires independent verification before formal-paper use"])
        writer.writerow(["reference_curve_status", "manual digitisation candidate", "16 AIE 225CS source-engine points; not target-engine measurements"])
        writer.writerow(["fit_MAPE_pct", mape, "in-sample diagnostic using the same 16 manual-digitisation candidates; not validation error"])
        writer.writerow(["fit_RMSE_Nm", rmse, "in-sample diagnostic using the same 16 manual-digitisation candidates; not validation error"])
        writer.writerow(["selected_start_index", selected["start_index"], "minimum exact one-degree ODE cost among converged and moved deterministic starts"])
        writer.writerow(["selected_least_squares_success", selected["success"], "selected deterministic two-parameter surrogate fit, re-evaluated in exact ODE"])
        writer.writerow(["selected_least_squares_status", selected["status"], "SciPy least_squares status code"])
        writer.writerow(["selected_least_squares_nfev", selected["nfev"], "bounded quadratic surrogate of a 7x7 exact one-degree ODE screen"])
        writer.writerow(["selected_least_squares_optimality", selected["optimality"], "selected deterministic two-parameter surrogate fit"])
        writer.writerow(["selected_friction_scale_at_upper_bound", multistart_diagnostics["selected_friction_scale_at_upper_bound"], multistart_diagnostics["active_bound_warning"]])
        for name, value in zip(("Ain_max_mm2", "Aex_max_mm2", "heat_scale", "combustion_duration_deg", "combustion_efficiency", "friction_scale", "intake_pressure_linear", "intake_pressure_quadratic"), pars):
            coefficient_scope = "multi-start fitted coefficient" if name in {"combustion_efficiency", "friction_scale"} else "fixed submitted engineering prior; not independently identifiable from 16 torque candidates"
            writer.writerow([name, value, coefficient_scope])
        writer.writerow(["fuel_mass_definition", FUEL_MASS_DEFINITION, "used consistently for baseline, scan and numerical refinement"])
        writer.writerow(["eta_b_formula", "P/(mfuel_per_cycle*LHV*n/60)", "P in W, mfuel_per_cycle in kg/cycle, n in r/min"])
        writer.writerow(["BSFC_formula", "mfuel_per_cycle*n*60000/P", "g/kWh; same mfuel_per_cycle definition as eta_b"])
        for key, value in fuel_mass_consistency.items():
            writer.writerow([f"fuel_mass_consistency_{key}", value, "programmatic check of baseline, 0.5 degree refinement and 31 overlap conditions"])
        for key in ("converged", "cycles_completed", "state_relative_residual", "work_J", "qwall_J", "torque_Nm", "power_kW", "IMEP_bar", "BMEP_bar", "FMEP_bar", "eta_m", "eta_b", "BSFC_g_kWh", "mfuel_per_cycle_kg", "mfuel_per_cycle_mg", "fresh_charge_start_mg", "fresh_charge_end_mg", "pmax_MPa", "Tmax_K"):
            writer.writerow([f"target_{key}", target[key], "6000 r/min, 128 degree overlap; conditioned cross-engine model prediction"])
        for key, record in refinement.items():
            writer.writerow([f"refinement_half_degree_relative_difference_{key}", record["relative_difference"], "one-degree formal result versus 0.5-degree RK4 refinement"])
        writer.writerow(["swept_volume_single_chamber_cm3", VS_TARGET_M3 * 1e6, "Question 1 verified single-chamber convention"])
        writer.writerow(["overlap_scan_deg", "20--170 by 5", "20 degree is scan lower boundary; no true optimum claim"])

    overlap_path = ROOT / "q2_overlap_response.csv"
    write_dict_csv(overlap_path, overlap_rows, list(overlap_rows[0]))
    cycle_path = ROOT / "q2_cycle_trace.csv"
    write_dict_csv(cycle_path, target["trace"], list(target["trace"][0]))
    torque_path = ROOT / "q2_three_chamber_torque.csv"
    write_dict_csv(torque_path, torque_rows, list(torque_rows[0]))
    figure_paths = make_figures(pred_torque, mape, overlap_rows, target["trace"], torque_rows)
    copied_figures: list[Path] = []
    for source in figure_paths:
        destination = PAPER_FIG / source.name.replace("_", "-")
        shutil.copyfile(source, destination)
        copied_figures.append(destination)

    output_paths = [results_path, overlap_path, cycle_path, torque_path, *figure_paths, *copied_figures]
    metadata = {
        "model_status": "generated_candidate_pending_independent_verification",
        "model_route": "open-system zero-dimensional ODE with port flow, Wiebe heat release, wall heat transfer, leakage and FMEP",
        "interpretation_limits": [
            "AIE 225CS points are manual digitisation candidates, not raw target-engine bench measurements",
            "MAPE and RMSE are in-sample fit diagnostics, not out-of-sample validation",
            "Six of eight submitted coefficients are fixed engineering priors because 16 torque candidates cannot identify all eight independently",
            "Only combustion efficiency and FMEP scale are fitted; even deterministic multi-start convergence does not establish physical uniqueness",
            "42.8 kW-scale outputs are conditioned cross-engine model predictions, not measured maximum power",
            "20 degree is the lower boundary of the specified scan and is not asserted to be a physical optimum",
            "Brake thermal efficiency and BSFC use the fixed-point cycle-start fresh-charge fuel mass consistently; they remain conditional-model responses",
        ],
        "single_chamber_swept_volume_cm3": VS_TARGET_M3 * 1e6,
        "compression_ratio": CR_TARGET,
        "reference_condition": {"rpm": 6000.0, "overlap_deg": 128.0, "step_deg": 1.0, "cycle_tolerance": 2e-5, "max_cycles": 60},
        "fuel_mass_basis": {"definition": FUEL_MASS_DEFINITION, "eta_b_formula": "P/(mfuel_per_cycle*LHV*n/60)", "bsfc_formula": "mfuel_per_cycle*n*60000/P"},
        "reference_result": {key: target[key] for key in ("converged", "cycles_completed", "state_relative_residual", "work_J", "qwall_J", "torque_Nm", "power_kW", "IMEP_bar", "BMEP_bar", "FMEP_bar", "eta_m", "eta_b", "BSFC_g_kWh", "mfuel_per_cycle_kg", "mfuel_per_cycle_mg", "fresh_charge_start_mg", "fresh_charge_end_mg", "pmax_MPa", "Tmax_K")},
        "numerical_refinement": {"formal_step_deg": 1.0, "refined_step_deg": 0.5, "reference_condition": "6000 r/min, 128 degree overlap", "metrics": refinement},
        "fuel_mass_consistency_check": fuel_mass_consistency,
        "calibration": {
            "reference_curve_status": "16 manual digitisation candidates from a public AIE 225CS curve; not target-engine measurements",
            "formal_grid_step_deg": 1.0,
            "optimizer_route": "least_squares on quadratic response surrogate fitted to a 7x7 exact one-degree ODE screen; every multi-start candidate is re-evaluated in exact ODE before selection",
            "ode_screen": {"nodes": 49, "screen_minimum_free_coefficients": [float(value) for value in ode_surrogate["screen_minimum"]], "cycles_completed": ode_surrogate["screen_cycles_completed"], "max_state_relative_residual": ode_surrogate["screen_max_state_residual"]},
            "fixed_prior_coefficients": {name: float(value) for name, value in zip(("Ain_max_mm2", "Aex_max_mm2", "heat_scale", "combustion_duration_deg", "combustion_efficiency_submitted", "friction_scale_submitted", "intake_pressure_linear", "intake_pressure_quadratic"), FIXED_COEFFICIENTS)},
            "free_coefficients": ["combustion_efficiency", "friction_scale"],
            "starts": fit_records,
            "multistart_diagnostics": multistart_diagnostics,
            "selection_rule": "minimum exact one-degree ODE cost among starts with success=true and a nonzero parameter move; ties use lower start_index",
            "selected": selected,
            "mape_pct_in_sample": mape,
            "rmse_Nm_in_sample": rmse,
        },
        "versions": {"python": sys.version.split()[0], "platform": platform.platform(), "numpy": np.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__},
        "script_sha256": sha256_file(Path(__file__)),
        "parameters": {name: float(value) for name, value in zip(("Ain_max_mm2", "Aex_max_mm2", "heat_scale", "combustion_duration_deg", "combustion_efficiency", "friction_scale", "intake_pressure_linear", "intake_pressure_quadratic"), pars)},
        "outputs": [{"path": str(path.relative_to(ROOT.parent)), "sha256": sha256_file(path)} for path in output_paths],
        "metadata_hash_note": "The JSON file's own byte hash is reported externally because embedding it would be self-referential.",
    }
    metadata_path = ROOT / "q2_run_metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"power_kW": target["power_kW"], "torque_Nm": target["torque_Nm"], "eta_b": target["eta_b"], "BSFC_g_kWh": target["BSFC_g_kWh"], "converged": target["converged"], "cycles": target["cycles_completed"], "residual": target["state_relative_residual"], "fit_mape_in_sample_pct": mape, "fit_rmse_in_sample_Nm": rmse, "selected_start": selected["start_index"], "optimizer_nfev": selected["nfev"], "optimizer_success": selected["success"]}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
