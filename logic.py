import math
from dataclasses import dataclass
from typing import List, Tuple, Optional

# ---------- Unit conversions ----------
PA_TO_PSI = 1.0 / 6894.757
PA_TO_KSI = PA_TO_PSI / 1e3

IN2M = 0.0254
FT2M = 0.3048
MM2M = 0.001
CM2M = 0.01

LBF2N = 4.44822
KIP2N = 1000.0 * LBF2N

LBFIN2NM = LBF2N * IN2M
LBFFT2NM = LBF2N * FT2M

G_ACCEL = 9.80665  # m/s^2


# ---------- Conversion helpers ----------
def convert_length_to_m(value: float, unit: str) -> float:
    factors = {
        "mm": MM2M,
        "cm": CM2M,
        "m": 1.0,
        "in": IN2M,
        "ft": FT2M,
    }
    return value * factors[unit]


def convert_force_to_N(value: float, unit: str) -> float:
    factors = {
        "N": 1.0,
        "kN": 1e3,
        "lbf": LBF2N,
        "kip": KIP2N,
    }
    return value * factors[unit]


def convert_moment_to_Nm(value: float, unit: str) -> float:
    factors = {
        "Nm": 1.0,
        "kNm": 1e3,
        "ft-lb": LBFFT2NM,
        "lbft": LBFFT2NM,
        "kip-ft": KIP2N * FT2M,
    }
    return value * factors[unit]


def convert_stress_to_Pa(value: float, unit: str) -> float:
    factors = {
        "Pa": 1.0,
        "kPa": 1e3,
        "MPa": 1e6,
        "GPa": 1e9,
        "psi": 1.0 / PA_TO_PSI,
        "ksi": 1.0 / PA_TO_KSI,
    }
    return value * factors[unit]


def convert_density_to_kg_m3(value: float, unit: str) -> float:
    factors = {
        "kg/m3": 1.0,
        "g/cm3": 1000.0,
        "lb/ft3": 16.018463,
        "lb/in3": 27679.904710191,
    }
    return value * factors[unit]


def stress_from_Pa(value_pa: float, unit: str) -> float:
    factors = {
        "Pa": 1.0,
        "kPa": 1e3,
        "MPa": 1e6,
        "GPa": 1e9,
        "psi": 1.0 / PA_TO_PSI,
        "ksi": 1.0 / PA_TO_KSI,
    }
    return value_pa / factors[unit]


def force_from_N(value_N: float, unit: str) -> float:
    factors = {
        "N": 1.0,
        "kN": 1e3,
        "lbf": LBF2N,
        "kip": KIP2N,
    }
    return value_N / factors[unit]


def length_from_m(value_m: float, unit: str) -> float:
    factors = {
        "mm": MM2M,
        "cm": CM2M,
        "m": 1.0,
        "in": IN2M,
        "ft": FT2M,
    }
    return value_m / factors[unit]


# ---------- Scissor member statics ----------
def cosd(a):
    return math.cos(math.radians(a))


def sind(a):
    return math.sin(math.radians(a))


def tand(a):
    return math.tan(math.radians(a))


def shear_moment(
    L_in: float,
    Xt: float, Yt: float,
    Xm: float, Ym: float,
    Xb: float, Yb: float,
    theta_deg: float,
    w_total_lbf: float = 0.0,
    dx_in: float = 0.1
) -> Tuple[List[float], List[float], List[float]]:
    nsteps = int(round(L_in / dx_in)) + 1
    xs = [k * dx_in for k in range(nsteps)]
    w = (w_total_lbf / L_in) * cosd(theta_deg)
    V = []
    M = []
    for x in xs:
        if x <= L_in / 2.0:
            V_i = -Xt * sind(theta_deg) - Yt * cosd(theta_deg) - w * x
            M_i = (-Xt * sind(theta_deg) - Yt * cosd(theta_deg)) * x - 0.5 * w * (x ** 2)
        else:
            V_i = -Xt * sind(theta_deg) - Yt * cosd(theta_deg) + Xm * sind(theta_deg) + Ym * cosd(theta_deg) - w * x
            M_i = (
                (-Xt * sind(theta_deg) - Yt * cosd(theta_deg) + Xm * sind(theta_deg) + Ym * cosd(theta_deg))
                * (x - L_in)
                - 0.5 * w * (x ** 2 - L_in ** 2)
            )
        V.append(V_i)
        M.append(M_i)
    return xs, V, M


def situation_1_forces(n: int, P_lbf: float, theta_deg: float) -> Tuple[float, float, float, float, float, float]:
    Yt = 0.25 * P_lbf
    Ym = 0.0
    Yb = 0.25 * P_lbf
    Xt = 0.5 * P_lbf * (n - 1) / tand(theta_deg)
    Xm = 0.25 * (2 * n - 1) * P_lbf / tand(theta_deg)
    Xb = 0.5 * P_lbf * n / tand(theta_deg)
    return Xt, Yt, Xm, Ym, Xb, Yb


def situation_2_forces(Mz_lbf_in: float, L_in: float, theta_deg: float) -> Tuple[float, float, float, float, float, float]:
    Ym = Mz_lbf_in / (L_in * cosd(theta_deg))
    Yt = Mz_lbf_in / (2 * L_in * cosd(theta_deg))
    Yb = Mz_lbf_in / (2 * L_in * cosd(theta_deg))
    Xt = Xm = Xb = 0.0
    return Xt, Yt, Xm, Ym, Xb, Yb


def situation_6_forces(Mx_lbf_in: float, dep_in: float) -> Tuple[float, float, float, float, float, float]:
    if dep_in <= 0:
        raise ValueError("dep must be > 0.")
    Y_end = Mx_lbf_in / (2.0 * dep_in)
    Xt = Xm = Xb = 0.0
    Yt = Y_end
    Yb = Y_end
    Ym = 0.0
    return Xt, Yt, Xm, Ym, Xb, Yb


def situation_7_forces(My_lbf_in: float, L_in: float, dep_in: float, theta_deg: float) -> Tuple[float, float, float, float, float, float]:
    denom = (L_in ** 2 * (cosd(theta_deg) ** 2) + dep_in ** 2)
    if denom <= 0:
        raise ValueError("Invalid geometry for situation 7 mapping.")
    X = (My_lbf_in * dep_in) / (2.0 * denom)
    Xt = X
    Xb = X
    Xm = 0.0
    Yt = Ym = Yb = 0.0
    return Xt, Yt, Xm, Ym, Xb, Yb


# ---------- Tube section calculations ----------
def tube_area(b: float, h: float, t: float) -> float:
    if t <= 0 or t >= 0.5 * min(b, h):
        raise ValueError("Wall thickness t must be > 0 and < min(b,h)/2.")
    return b * h - (b - 2 * t) * (h - 2 * t)


def tube_Ix(b: float, h: float, t: float) -> float:
    return (h * b ** 3 - (h - 2 * t) * (b - 2 * t) ** 3) / 12.0


# ---------- Core stress calculation ----------
@dataclass
class BeamInputs:
    b_m: float
    d_m: float
    h_m: float
    P_N: float
    M_Nm: float
    Kt_P: float
    Kt_M: float = 2.0
    section_type: str = "solid"
    t_wall_m: Optional[float] = None


@dataclass
class BeamResults:
    sigma_nom_P_Pa: float
    sigma_max_P_Pa: float
    sigma_nom_M_Pa: float
    sigma_max_M_Pa: float
    sigma_comb_Pa: float


def compute_beam_stress(inp: BeamInputs) -> BeamResults:
    b = inp.b_m
    d = inp.d_m
    h = inp.h_m
    P = inp.P_N
    M = inp.M_Nm
    Kt_P = inp.Kt_P
    Kt_M = inp.Kt_M

    if d >= b:
        raise ValueError("Hole diameter d must be less than beam width b.")

    section = (inp.section_type or "solid").strip().lower()

    if section == "solid":
        A_net = (b - d) * h
        if A_net <= 0.0:
            raise ValueError("Non-positive net area; check b, d, h.")
        sigma_nom_P = P / A_net

        denom = (b ** 3 - d ** 3) * h
        if denom == 0.0:
            raise ZeroDivisionError("Invalid geometry → zero bending denominator.")
        sigma_nom_M = (6.0 * M * d) / denom

    elif section == "tube":
        t = inp.t_wall_m
        if t is None:
            raise ValueError("Wall thickness t is required for tube section.")
        if t <= 0 or t >= 0.5 * min(b, h):
            raise ValueError("Wall thickness t must be > 0 and < min(b,h)/2.")
        A_tube = tube_area(b, h, t)
        A_net = A_tube - 2.0 * d * t
        if A_net <= 0.0:
            raise ValueError("Non-positive net area for tube; increase b/h/t or reduce d.")
        sigma_nom_P = P / A_net

        I = tube_Ix(b, h, t)
        c = 0.5 * h
        S = I / c
        if S <= 0.0:
            raise ZeroDivisionError("Invalid tube section modulus.")
        sigma_nom_M = M / S

    else:
        raise ValueError("Unknown section_type. Use 'solid' or 'tube'.")

    sigma_max_P = Kt_P * sigma_nom_P
    sigma_max_M = Kt_M * sigma_nom_M
    sigma_comb = sigma_max_P + sigma_max_M
    return BeamResults(sigma_nom_P, sigma_max_P, sigma_nom_M, sigma_max_M, sigma_comb)


def parse_thickness_range_values(t_min: float, t_max: float, t_step: float) -> List[float]:
    if t_step <= 0:
        raise ValueError("Step must be > 0.")
    vals = []
    x = t_min
    while x <= t_max + 1e-12:
        vals.append(x)
        x += t_step
    return vals


def run_full_case(
    section_type_local: str,
    t_local_m: Optional[float],
    *,
    b_m: float,
    h_m: float,
    L_m: float,
    d_m: float,
    edge_offset_m: float,
    rho_kg_m3: float,
    Kt_P: float,
    Kt_M: float,
    Kt_tau: float,
    theta_deg: float,
    n: int,
    sit: int,
    P_N_user: float = 0.0,
    Mz_Nm: float = 0.0,
    Mx_Nm: float = 0.0,
    My_Nm: float = 0.0,
    dep_m: float = 0.0,
    cb_outer_m: Optional[float] = None,
    cb_len_m: Optional[float] = None,
    cb_t_m: Optional[float] = None,
):
    edge_offset_in = edge_offset_m / IN2M
    L_in = L_m / IN2M
    if edge_offset_in < 0:
        raise ValueError("Left-edge hole offset must be >= 0.")
    if 2.0 * edge_offset_in >= L_in:
        raise ValueError("Left-edge hole offset too large: 2*offset must be < span.")

    x_left_pin = edge_offset_in
    x_right_pin = L_in - edge_offset_in
    x_mid_pin = 0.5 * (x_left_pin + x_right_pin)
    L_pin = L_in - 2.0 * edge_offset_in

    hole_count = 3 if d_m > 0 else 0

    cb_W_member_lbf = 0.0
    if cb_outer_m is not None and cb_len_m is not None and cb_t_m is not None:
        if cb_t_m <= 0 or cb_outer_m <= 0 or cb_len_m <= 0:
            raise ValueError("Cross-brace dimensions must be > 0.")
        if 2.0 * cb_t_m >= cb_outer_m:
            raise ValueError("Cross-brace wall thickness is too large (2t must be < outer width).")

        cb_area_m2 = tube_area(cb_outer_m, cb_outer_m, cb_t_m)
        cb_vol_one_m3 = cb_area_m2 * cb_len_m
        cb_mass_one_kg = rho_kg_m3 * cb_vol_one_m3
        cb_W_one_lbf = (cb_mass_one_kg * G_ACCEL) / LBF2N
        cb_count_total = 2 * n
        cb_W_total_lbf = cb_count_total * cb_W_one_lbf
        cb_W_member_lbf = cb_W_total_lbf

    if section_type_local == "solid":
        A_section_m2 = b_m * h_m
        V_gross_m3 = A_section_m2 * L_m
        V_hole_one_m3 = (math.pi * (0.5 * d_m) ** 2) * h_m
        A_net_report = (b_m - d_m) * h_m
        S_report = ((b_m ** 3 - d_m ** 3) * h_m) / (6.0 * d_m) if d_m > 0 else float("nan")
        I_report = S_report * (0.5 * h_m) if not math.isnan(S_report) else float("nan")
    else:
        if t_local_m is None:
            raise ValueError("Tube thickness is required.")
        A_section_m2 = tube_area(b_m, h_m, t_local_m)
        V_gross_m3 = A_section_m2 * L_m
        V_hole_one_m3 = 2.0 * (math.pi * (0.5 * d_m) ** 2) * t_local_m
        A_tube = A_section_m2
        A_net_report = A_tube - 2.0 * d_m * t_local_m
        I_report = tube_Ix(b_m, h_m, t_local_m)
        S_report = I_report / (0.5 * h_m)

    V_holes_m3 = hole_count * V_hole_one_m3
    V_net_m3 = max(V_gross_m3 - V_holes_m3, 0.0)
    mass_kg = rho_kg_m3 * V_net_m3
    W_N = mass_kg * G_ACCEL
    W_lbf = W_N / LBF2N

    if sit == 1:
        P_eff_lbf = (P_N_user / LBF2N) + cb_W_member_lbf
        Xt, Yt, Xm, Ym, Xb, Yb = situation_1_forces(n, P_eff_lbf, theta_deg)
        w_for_diagram = W_lbf
    elif sit == 2:
        Xt, Yt, Xm, Ym, Xb, Yb = situation_2_forces(Mz_Nm / LBFIN2NM, L_pin, theta_deg)
        w_for_diagram = 0.0
    elif sit == 6:
        Xt, Yt, Xm, Ym, Xb, Yb = situation_6_forces(Mx_Nm / LBFIN2NM, dep_m / IN2M)
        w_for_diagram = 0.0
    elif sit == 7:
        Xt, Yt, Xm, Ym, Xb, Yb = situation_7_forces(My_Nm / LBFIN2NM, L_pin, dep_m / IN2M, theta_deg)
        w_for_diagram = 0.0
    else:
        raise ValueError("Unsupported situation.")

    xs_in, V_lbf, M_lbf_in = shear_moment(
        L_pin, Xt, Yt, Xm, Ym, Xb, Yb, theta_deg, w_total_lbf=w_for_diagram, dx_in=0.1
    )

    theta_rad = math.radians(theta_deg)
    Fx_total = Xt + Xm + Xb
    Fy_total = Yt + Ym + Yb
    Tension_lbf = Fx_total * math.cos(theta_rad) + Fy_total * math.sin(theta_rad)

    M_abs_max_val_lbf_in = max(abs(v) for v in M_lbf_in) if M_lbf_in else 0.0
    V_abs_max_lbf = max(abs(v) for v in V_lbf) if V_lbf else 0.0

    P_SI = Tension_lbf * LBF2N
    M_SI_for_bending = M_abs_max_val_lbf_in * LBFIN2NM

    res = compute_beam_stress(
        BeamInputs(
            b_m=b_m,
            d_m=d_m,
            h_m=h_m,
            P_N=P_SI,
            M_Nm=M_SI_for_bending,
            Kt_P=Kt_P,
            Kt_M=Kt_M,
            section_type=section_type_local,
            t_wall_m=t_local_m,
        )
    )

    V_abs_max_N = V_abs_max_lbf * LBF2N
    A_shear_m2 = (b_m * h_m) if section_type_local == "solid" else tube_area(b_m, h_m, t_local_m)
    tau_max_Pa = Kt_tau * (V_abs_max_N / A_shear_m2)

    return {
        "mass_kg": mass_kg,
        "W_lbf": W_lbf,
        "W_crossbrace_member_lbf": cb_W_member_lbf,
        "M_abs_max_lbf_in": M_abs_max_val_lbf_in,
        "V_abs_max_lbf": V_abs_max_lbf,
        "sigma_nom_P": res.sigma_nom_P_Pa,
        "sigma_max_P": res.sigma_max_P_Pa,
        "sigma_nom_M": res.sigma_nom_M_Pa,
        "sigma_max_M": res.sigma_max_M_Pa,
        "sigma_comb": res.sigma_comb_Pa,
        "tau_max": tau_max_Pa,
        "A_shear_m2": A_shear_m2,
        "A_net_report": A_net_report,
        "I_report": I_report,
        "S_report": S_report,
        "forces": {
            "Xt": Xt, "Yt": Yt,
            "Xm": Xm, "Ym": Ym,
            "Xb": Xb, "Yb": Yb,
        },
        "x_mid_pin_in": x_mid_pin,
        "L_pin_in": L_pin,
        "xs_in": xs_in,
        "V_lbf": V_lbf,
        "M_lbf_in": M_lbf_in,
    }


def analyze_system(
    *,
    b_m: float,
    h_m: float,
    L_m: float,
    d_m: float,
    edge_offset_m: float,
    rho_kg_m3: float,
    Kt_P: float,
    Kt_M: float,
    Kt_tau: float,
    theta_deg: float,
    n: int,
    sit: int,
    Sy_Pa: float,
    P_N_user: float = 0.0,
    Mz_Nm: float = 0.0,
    Mx_Nm: float = 0.0,
    My_Nm: float = 0.0,
    dep_m: float = 0.0,
    cb_outer_m: Optional[float] = None,
    cb_len_m: Optional[float] = None,
    cb_t_m: Optional[float] = None,
    tube_t_min_m: float = 0.065 * IN2M,
    tube_t_max_m: float = 0.250 * IN2M,
    tube_t_step_m: float = 0.020 * IN2M,
    SF_target: float = 1.20,
):
    solid = run_full_case(
        "solid", None,
        b_m=b_m,
        h_m=h_m,
        L_m=L_m,
        d_m=d_m,
        edge_offset_m=edge_offset_m,
        rho_kg_m3=rho_kg_m3,
        Kt_P=Kt_P,
        Kt_M=Kt_M,
        Kt_tau=Kt_tau,
        theta_deg=theta_deg,
        n=n,
        sit=sit,
        P_N_user=P_N_user,
        Mz_Nm=Mz_Nm,
        Mx_Nm=Mx_Nm,
        My_Nm=My_Nm,
        dep_m=dep_m,
        cb_outer_m=cb_outer_m,
        cb_len_m=cb_len_m,
        cb_t_m=cb_t_m,
    )

    sigma_vm_solid = math.sqrt(solid["sigma_comb"] ** 2 + 3.0 * (solid["tau_max"] ** 2))
    SF_solid = (Sy_Pa / sigma_vm_solid) if sigma_vm_solid > 0 else float("inf")
    will_yield_solid = sigma_vm_solid >= Sy_Pa

    t_list = parse_thickness_range_values(tube_t_min_m, tube_t_max_m, tube_t_step_m)

    all_rows = []
    viable = []

    for t in t_list:
        if t >= 0.5 * min(b_m, h_m):
            continue
        try:
            tube = run_full_case(
                "tube", t,
                b_m=b_m,
                h_m=h_m,
                L_m=L_m,
                d_m=d_m,
                edge_offset_m=edge_offset_m,
                rho_kg_m3=rho_kg_m3,
                Kt_P=Kt_P,
                Kt_M=Kt_M,
                Kt_tau=Kt_tau,
                theta_deg=theta_deg,
                n=n,
                sit=sit,
                P_N_user=P_N_user,
                Mz_Nm=Mz_Nm,
                Mx_Nm=Mx_Nm,
                My_Nm=My_Nm,
                dep_m=dep_m,
                cb_outer_m=cb_outer_m,
                cb_len_m=cb_len_m,
                cb_t_m=cb_t_m,
            )
        except Exception:
            continue

        sigma_vm = math.sqrt(tube["sigma_comb"] ** 2 + 3.0 * (tube["tau_max"] ** 2))
        SF = (Sy_Pa / sigma_vm) if sigma_vm > 0 else float("inf")

        row = {
            "t_m": t,
            "mass_kg": tube["mass_kg"],
            "W_lbf": tube["W_lbf"],
            "sigma_vm": sigma_vm,
            "SF": SF,
            "details": tube,
        }
        all_rows.append(row)
        if SF >= SF_target:
            viable.append(row)

    viable.sort(key=lambda r: (r["mass_kg"], -r["SF"]))
    all_rows.sort(key=lambda r: (r["mass_kg"], -r["SF"]))

    return {
        "solid": solid,
        "solid_sigma_vm": sigma_vm_solid,
        "solid_SF": SF_solid,
        "solid_yields": will_yield_solid,
        "tube_rows": all_rows,
        "tube_viable": viable,
    }