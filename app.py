import os
import math
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import streamlit as st

from logic import (
    analyze_system,
    convert_length_to_m,
    convert_force_to_N,
    convert_moment_to_Nm,
    convert_stress_to_Pa,
    stress_from_Pa,
    length_from_m,
)

st.set_page_config(
    page_title="Engineering Theater Capstone Stress Analysis App",
    layout="wide"
)

# ---------- Display formatting helpers ----------
def fmt_sig(value, sig=3):
    """
    Format values to ~3 significant figures with commas and no scientific notation.
    """
    if value is None:
        return "-"
    if isinstance(value, str):
        return value
    if value == 0:
        return "0"

    a = abs(value)

    digits_before = int(math.floor(math.log10(a))) + 1 if a >= 1 else 0
    decimals = max(sig - digits_before, 0)

    if a < 1:
        decimals = max(sig + int(abs(math.floor(math.log10(a)))) - 1, sig)

    return f"{value:,.{decimals}f}"

def latex_num(value, sig=3):
    """
    Same formatting as fmt_sig, but escapes commas for LaTeX.
    """
    s = fmt_sig(value, sig)
    return s.replace(",", "{,}")

def convert_density_local(value, unit):
    if unit == "kg/m3":
        return value
    elif unit == "g/cm3":
        return value * 1000.0
    elif unit == "lb/ft3":
        return value * 16.0184634
    elif unit == "lb/in3":
        return value * 27679.9047
    else:
        raise ValueError("Unsupported density unit")

# ---------- Theme / Fonts ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cherry+Cream+Soda&family=Roboto:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Roboto', sans-serif;
}

.stApp {
    background: linear-gradient(to bottom, #f8f6f2 0%, #fffaf0 100%);
}

h1, h2, h3 {
    color: #450084;
    font-family: 'Roboto', sans-serif !important;
    font-weight: 700 !important;
}

/* Avoid overriding every span globally, or Streamlit icon fonts break */
p, label {
    font-family: 'Roboto', sans-serif !important;
    color: #222222;
}

div {
    color: #222222;
}

/* Keep expander/material icon fonts intact */
span.material-symbols-rounded,
i.material-icons,
i.material-symbols-rounded {
    font-family: "Material Symbols Rounded" !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(to bottom, #450084 0%, #5c1a9c 100%);
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] * {
    color: black !important;
    font-family: 'Roboto', sans-serif !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: #fffaf0 !important;
    border: 2px solid #c99700 !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}

div[data-baseweb="select"] input {
    caret-color: transparent !important;
    color: transparent !important;
    text-shadow: none !important;
    pointer-events: none !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

div[data-baseweb="select"] input:focus,
div[data-baseweb="select"] *:focus {
    outline: none !important;
    box-shadow: none !important;
}

ul[role="listbox"] li,
div[role="option"] {
    color: black !important;
    background-color: white !important;
    font-family: 'Roboto', sans-serif !important;
}

[data-testid="metric-container"] {
    border: 2px solid #c99700;
    padding: 12px;
    border-radius: 12px;
    background: linear-gradient(to bottom right, white, #fff8dc);
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}

input {
    border: 2px solid #c99700 !important;
    border-radius: 8px !important;
    font-family: 'Roboto', sans-serif !important;
}

label {
    color: #450084 !important;
    font-weight: 700;
    font-family: 'Roboto', sans-serif !important;
}

.stDataFrame {
    background-color: white;
    border: 2px solid #c99700;
    border-radius: 10px;
}

.block-container {
    padding-top: 2rem;
}

/* Slider colors */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background-color: #a56de2 !important;
    border-color: #a56de2 !important;
    box-shadow: none !important;
}

.stSlider [data-baseweb="slider"] > div > div > div {
    background: #b68cf0 !important;
}

.stSlider [data-baseweb="slider"] > div > div > div > div {
    background: #b68cf0 !important;
}

/* Expander / math spacing */
div[data-testid="stExpander"] details {
    overflow: visible !important;
}

div[data-testid="stExpander"] details summary {
    overflow: visible !important;
    white-space: normal !important;
}

div[data-testid="stExpander"] .katex-display {
    padding-top: 0.35rem !important;
    padding-bottom: 0.35rem !important;
    overflow-x: auto !important;
    overflow-y: visible !important;
}

div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] {
    overflow: visible !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- Helper: axial stress concentration factor ----------
def axial_kt_from_ratio(x: float) -> float:
    return 2.95 - 2.855 * x + 3.410 * x**2 - 1.678 * x**3

# ---------- Helper: live scissor visualization ----------
def draw_scissor_lift_vertical(n_stages: int, theta_deg: float):
    theta_deg = max(1, min(89, theta_deg))
    theta = math.radians(theta_deg)

    member_length = 1.0
    dx = member_length * math.cos(theta)
    dy = member_length * math.sin(theta)

    width = 2 * dx
    total_height = 2 * n_stages * dy

    purple = "#5E2CA5"
    purple_dark = "#450084"
    gold = "#C99700"

    fig, ax = plt.subplots(figsize=(3.6, 3.9), dpi=200)

    ax.plot([0, width], [0, 0], color=purple_dark, linewidth=1.8)

    for i in range(n_stages):
        y0 = 2 * i * dy
        y1 = y0 + 2 * dy

        ax.plot([0, width], [y0, y1], color=purple, linewidth=1.8)
        ax.plot([0, width], [y1, y0], color=purple, linewidth=1.8)
        ax.plot([dx], [y0 + dy], marker="o", markersize=3.5, color=gold)

    pad = 0.12 * width
    ax.plot(
        [-pad, width + pad],
        [total_height, total_height],
        color=purple_dark,
        linewidth=2.2
    )

    ax.set_xlim(-0.2, width + 0.2)
    ax.set_ylim(-0.1, total_height + 0.25)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        f"{n_stages} stage(s), θ = {theta_deg}°",
        fontsize=10,
        color=purple_dark,
        pad=6,
        loc="center"
    )

    fig.tight_layout(pad=0.3)
    return fig

# ---------- Helper: equation display ----------
def show_step(title: str, general_eq: str, substituted_eq: str, result_eq: str):
    st.markdown(f"#### {title}")
    st.latex(general_eq)
    st.latex(substituted_eq)
    st.latex(result_eq)

# ---------- Sidebar Logos ----------
logo1 = "logo.png"
logo2 = "logo2.png"

if os.path.exists(logo1):
    st.sidebar.image(logo1, use_container_width=True)

if os.path.exists(logo2):
    left, center, right = st.sidebar.columns([1, 3, 1])
    with center:
        st.image(logo2, width=180)

# ---------- Centered Header ----------
col_left, col_center, col_right = st.columns([1, 6, 1])

with col_center:
    st.markdown("""
        <h1 style='
            text-align:center;
            margin-bottom:0.2rem;
            color:#450084;
            font-family:"Cherry Cream Soda", system-ui;
            font-weight:400;'>
        Engineering Theater Capstone Stress Analysis App
        </h1>
    """, unsafe_allow_html=True)

    st.markdown("""
        <p style='
            text-align:center;
            font-size:1.05rem;
            color:#666;
            margin-top:0;
            margin-bottom:1rem;
            font-family:"Cherry Cream Soda", system-ui;'>
        A transparent analysis tool for evaluating solid-member stresses and exploring lighter tube alternatives.
        </p>
    """, unsafe_allow_html=True)

# ---------- Sidebar Units ----------
st.sidebar.header("Reporting units")
st.sidebar.caption("These selections control how inputs are entered and how final results are displayed throughout the report.")

length_unit = st.sidebar.selectbox("Length units used throughout the report", ["in", "mm", "cm", "m"], index=0)
force_unit = st.sidebar.selectbox("Force units for applied loading", ["lbf", "N", "kN", "kip"], index=0)
moment_unit = st.sidebar.selectbox("Moment units for overturning cases", ["ft-lb", "Nm", "kNm", "kip-ft"], index=0)
stress_unit = st.sidebar.selectbox("Stress units for displayed results", ["ksi", "MPa", "psi", "Pa"], index=0)
density_unit = st.sidebar.selectbox("Material density units", ["kg/m3", "g/cm3", "lb/ft3", "lb/in3"], index=2)

st.markdown("---")

# ---------- Section 1: Geometry ----------
st.subheader("Member Geometry Definition")
st.caption(
    "This section defines the baseline cross-member geometry used in the stress analysis. "
    "These dimensions control both the solid-member check and the tube weight-reduction sweep."
)

geo_left, geo_right = st.columns([1, 1])

with geo_left:
    b_val = st.number_input("Overall member width, b", value=3.0, min_value=0.0001, format="%.4f")
    h_val = st.number_input("Member thickness, h", value=0.25, min_value=0.0001, format="%.4f")
    L_val = st.number_input("Pin-to-pin member span, L", value=20.0, min_value=0.0001, format="%.4f")
    d_val = st.number_input("Pin-hole diameter, d", value=1.0, min_value=0.0, format="%.4f")
    edge_offset_val = st.number_input("Distance from left edge to the first hole center", value=0.75, min_value=0.0, format="%.4f")

with geo_right:
    if os.path.exists("crossmember.png"):
        img_left, img_center, img_right = st.columns([0.15, 9.7, 0.15])
        with img_center:
            st.image("crossmember.png", use_container_width=True)

st.markdown("---")

# ---------- Section 2: Material ----------
st.subheader("Material Properties")
st.caption(
    "These properties define the baseline material behavior used in the analysis. "
    "Density influences member weight, while yield strength is used to compute the factor of safety."
)

mat1, mat2 = st.columns(2)

with mat1:
    rho_val = st.number_input("Material density", value=490.0, min_value=0.0001, format="%.4f")
with mat2:
    Sy_val = st.number_input("Material yield strength", value=36.0, min_value=0.0001, format="%.4f")

st.markdown("---")

# ---------- Section 3: Configuration ----------
st.subheader("Loading and Lift Configuration")
st.caption(
    "This section describes the operating geometry and the loading case being evaluated. "
    "The selected angle, number of stages, and applied loading determine the internal forces used in the stress calculations."
)

config_left, config_right = st.columns([1, 1])

with config_left:
    theta_deg = st.slider("Scissor angle, θ", 1, 89, 15)
    n = st.slider("Number of scissor stages, n", 1, 6, 1)

    sit = st.selectbox(
        "Loading case to be evaluated",
        options=[1, 2, 6, 7],
        format_func=lambda x: {
            1: "1 - Centered vertical payload, P",
            2: "2 - Overturning moment about the z-axis, Mz",
            6: "6 - Overturning moment about the x-axis, Mx",
            7: "7 - Overturning moment about the y-axis, My",
        }[x]
    )

    P_val = 0.0
    Mz_val = 0.0
    Mx_val = 0.0
    My_val = 0.0
    dep_val = 0.0

    if sit == 1:
        P_val = st.number_input("Applied centered payload, P", value=225.0, min_value=0.0, format="%.4f")
    elif sit == 2:
        Mz_val = st.number_input("Applied overturning moment, Mz", value=100.0, min_value=0.0, format="%.4f")
    elif sit == 6:
        Mx_val = st.number_input("Applied overturning moment, Mx", value=100.0, min_value=0.0, format="%.4f")
        dep_val = st.number_input("Member spacing used for this loading case, dep", value=6.0, min_value=0.0001, format="%.4f")
    elif sit == 7:
        My_val = st.number_input("Applied overturning moment, My", value=100.0, min_value=0.0, format="%.4f")
        dep_val = st.number_input("Member spacing used for this loading case, dep", value=6.0, min_value=0.0001, format="%.4f")

    st.markdown("#### Cross-bracing assumption")
    use_cb = st.checkbox("Include the self-weight of cross bracing in the load model", value=False)

    cb_outer_val = None
    cb_len_val = None
    cb_t_val = None

    if use_cb:
        cb_outer_val = st.number_input("Cross-brace outer width/height", value=1.0, min_value=0.0001, format="%.4f")
        cb_len_val = st.number_input("Cross-brace member length", value=18.0, min_value=0.0001, format="%.4f")
        cb_t_val = st.number_input("Cross-brace wall thickness", value=0.065, min_value=0.0001, format="%.4f")

with config_right:
    left_pad, center_block, right_pad = st.columns([1.2, 1.6, 1.2])

    with center_block:
        st.markdown(
            """
            <h4 style="
                text-align:center;
                margin:0 0 0.6rem 0;
                color:#111111;">
                Live Scissor Lift Geometry Preview
            </h4>
            """,
            unsafe_allow_html=True
        )

        st.caption(
            "This preview shows the current lift geometry based on the selected number of stages "
            "and scissor angle. It is intended as a quick visual reference for the configuration being analyzed."
        )

        viz_fig = draw_scissor_lift_vertical(n_stages=n, theta_deg=theta_deg)
        st.pyplot(viz_fig, use_container_width=True)
        plt.close(viz_fig)

st.markdown("---")

try:
    # ---------- Convert inputs ----------
    b_m = convert_length_to_m(b_val, length_unit)
    h_m = convert_length_to_m(h_val, length_unit)
    L_m = convert_length_to_m(L_val, length_unit)
    d_m = convert_length_to_m(d_val, length_unit)
    edge_offset_m = convert_length_to_m(edge_offset_val, length_unit)

    rho_kg_m3 = convert_density_local(rho_val, density_unit)
    Sy_Pa = convert_stress_to_Pa(Sy_val, stress_unit)

    P_N_user = convert_force_to_N(P_val, force_unit) if sit == 1 else 0.0
    Mz_Nm = convert_moment_to_Nm(Mz_val, moment_unit) if sit == 2 else 0.0
    Mx_Nm = convert_moment_to_Nm(Mx_val, moment_unit) if sit == 6 else 0.0
    My_Nm = convert_moment_to_Nm(My_val, moment_unit) if sit == 7 else 0.0
    dep_m = convert_length_to_m(dep_val, length_unit) if sit in [6, 7] else 0.0

    cb_outer_m = convert_length_to_m(cb_outer_val, length_unit) if use_cb else None
    cb_len_m = convert_length_to_m(cb_len_val, length_unit) if use_cb else None
    cb_t_m = convert_length_to_m(cb_t_val, length_unit) if use_cb else None

    if b_val <= 0:
        raise ValueError("Width b must be greater than zero.")

    x_ratio = d_val / b_val

    if x_ratio <= 0:
        raise ValueError("The ratio d/b must be greater than zero.")
    if x_ratio > 0.6:
        st.error(
            f"d/b = {fmt_sig(x_ratio)} which is outside the polynomial validity range used here (0 < d/b ≤ 0.6). "
            "Please reduce the hole diameter or increase the beam width."
        )
        st.stop()

    Kt_P = axial_kt_from_ratio(x_ratio)

    # ---------- Run once for solid results ----------
    default_tube_t_min_val = 0.065
    default_tube_t_max_val = 0.250
    default_tube_t_step_val = 0.020
    default_SF_target = 1.20

    default_tube_t_min_m = convert_length_to_m(default_tube_t_min_val, length_unit)
    default_tube_t_max_m = convert_length_to_m(default_tube_t_max_val, length_unit)
    default_tube_t_step_m = convert_length_to_m(default_tube_t_step_val, length_unit)

    results = analyze_system(
        b_m=b_m,
        h_m=h_m,
        L_m=L_m,
        d_m=d_m,
        edge_offset_m=edge_offset_m,
        rho_kg_m3=rho_kg_m3,
        Kt_P=Kt_P,
        Kt_M=2.0,
        Kt_tau=2.0,
        theta_deg=theta_deg,
        n=n,
        sit=sit,
        Sy_Pa=Sy_Pa,
        P_N_user=P_N_user,
        Mz_Nm=Mz_Nm,
        Mx_Nm=Mx_Nm,
        My_Nm=My_Nm,
        dep_m=dep_m,
        cb_outer_m=cb_outer_m,
        cb_len_m=cb_len_m,
        cb_t_m=cb_t_m,
        tube_t_min_m=default_tube_t_min_m,
        tube_t_max_m=default_tube_t_max_m,
        tube_t_step_m=default_tube_t_step_m,
        SF_target=default_SF_target,
    )

    solid = results["solid"]

    # ---------- Solid results ----------
    st.subheader("Baseline Solid Member Assessment")
    st.caption(
        "These results summarize the stress state of the baseline solid member under the selected loading case. "
        "This section serves as the reference design before exploring lighter tube alternatives."
    )

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Von Mises stress for the solid member",
        f"{fmt_sig(stress_from_Pa(results['solid_sigma_vm'], stress_unit))} {stress_unit}"
    )
    m2.metric(
        "Factor of safety for the solid member",
        fmt_sig(results["solid_SF"])
    )
    m3.metric("Baseline solid-member status", "YIELDS" if results["solid_yields"] else "OK")

    st.markdown("---")

    # ---------- Tube evaluation and sweep ----------
    st.subheader("Tube Evaluation and Weight-Reduction Sweep")
    st.caption(
        "This section investigates whether the solid member can be replaced by a lighter tube section while still meeting the desired safety target. "
        "By sweeping across candidate wall thicknesses, the tool helps identify designs that reduce mass without sacrificing acceptable structural performance."
    )

    st.markdown(
        """
        **Design intent:**  
        The goal of this sweep is to explore how much weight can be saved by switching from a solid member to a tube geometry.  
        A lighter member can reduce overall system mass and may also reduce internal loading from self-weight, provided the resulting tube still satisfies the required factor of safety.
        """
    )

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        tube_t_min_val = st.number_input("Minimum candidate tube wall thickness", value=0.065, min_value=0.0001, format="%.4f")
    with s2:
        tube_t_max_val = st.number_input("Maximum candidate tube wall thickness", value=0.250, min_value=0.0001, format="%.4f")
    with s3:
        tube_t_step_val = st.number_input("Tube wall thickness increment for the sweep", value=0.020, min_value=0.0001, format="%.4f")
    with s4:
        SF_target = st.number_input("Required minimum factor of safety", value=1.20, min_value=0.0001, format="%.3f")

    tube_t_min_m = convert_length_to_m(tube_t_min_val, length_unit)
    tube_t_max_m = convert_length_to_m(tube_t_max_val, length_unit)
    tube_t_step_m = convert_length_to_m(tube_t_step_val, length_unit)

    tube_results = analyze_system(
        b_m=b_m,
        h_m=h_m,
        L_m=L_m,
        d_m=d_m,
        edge_offset_m=edge_offset_m,
        rho_kg_m3=rho_kg_m3,
        Kt_P=Kt_P,
        Kt_M=2.0,
        Kt_tau=2.0,
        theta_deg=theta_deg,
        n=n,
        sit=sit,
        Sy_Pa=Sy_Pa,
        P_N_user=P_N_user,
        Mz_Nm=Mz_Nm,
        Mx_Nm=Mx_Nm,
        My_Nm=My_Nm,
        dep_m=dep_m,
        cb_outer_m=cb_outer_m,
        cb_len_m=cb_len_m,
        cb_t_m=cb_t_m,
        tube_t_min_m=tube_t_min_m,
        tube_t_max_m=tube_t_max_m,
        tube_t_step_m=tube_t_step_m,
        SF_target=SF_target,
    )

    st.markdown("#### Tube candidate summary")
    st.caption(
        "Each row below represents a candidate tube wall thickness from the sweep. "
        "The table reports resulting member mass, von Mises stress, and factor of safety so that lighter acceptable designs can be compared directly."
    )

    rows = []
    for r in tube_results["tube_rows"]:
        rows.append({
            f"Tube wall thickness, t ({length_unit})": fmt_sig(length_from_m(r["t_m"], length_unit)),
            "Resulting member mass (kg)": fmt_sig(r["mass_kg"]),
            f"Von Mises stress ({stress_unit})": fmt_sig(stress_from_Pa(r["sigma_vm"], stress_unit)),
            "Factor of safety": fmt_sig(r["SF"]),
        })

    if rows:
        display_df = pd.DataFrame(rows)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        chart_rows = []
        for r in tube_results["tube_rows"]:
            chart_rows.append({
                f"Tube wall thickness, t ({length_unit})": length_from_m(r["t_m"], length_unit),
                "Resulting member mass (kg)": r["mass_kg"],
                f"Von Mises stress ({stress_unit})": stress_from_Pa(r["sigma_vm"], stress_unit),
                "Factor of safety": r["SF"],
            })

        chart_df = pd.DataFrame(chart_rows)
        x_col = f"Tube wall thickness, t ({length_unit})"
        chart = (
            alt.Chart(chart_df)
            .mark_line(point=alt.OverlayMarkDef(size=100, filled=True))
            .encode(
                x=alt.X(x_col, title=x_col),
                y=alt.Y("Factor of safety", title="Factor of Safety"),
                tooltip=[
                    alt.Tooltip(x_col, format=",.3f"),
                    alt.Tooltip("Resulting member mass (kg)", format=",.3f"),
                    alt.Tooltip(f"Von Mises stress ({stress_unit})", format=",.3f"),
                    alt.Tooltip("Factor of safety", format=",.3f"),
                ]
            )
            .properties(height=400)
        )
        st.altair_chart(chart, use_container_width=True)

    st.markdown("#### Tube designs that satisfy the safety requirement")
    st.caption(
        "This filtered table isolates only the tube options that meet or exceed the required factor of safety. "
        "These are the candidate designs most useful for reducing weight while maintaining the specified performance threshold."
    )

    viable_rows = []
    for r in tube_results["tube_viable"]:
        viable_rows.append({
            f"Tube wall thickness, t ({length_unit})": fmt_sig(length_from_m(r["t_m"], length_unit)),
            "Resulting member mass (kg)": fmt_sig(r["mass_kg"]),
            "Factor of safety": fmt_sig(r["SF"]),
        })

    if viable_rows:
        st.dataframe(pd.DataFrame(viable_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No tube options in the current sweep satisfy the required factor of safety.")

    st.markdown("---")

    # ---------- Detailed calculations at bottom ----------
    with st.expander("Detailed calculations and derivation trail", expanded=False):
        st.markdown(
            "### Step-by-step solid member calculations\n"
            "This appendix-style section shows the mathematical path used to produce the baseline solid-member results. "
            "Each step is shown in symbolic form, then with substituted values, and finally with the computed result."
        )

        st.markdown("#### Input summary")
        input_df = pd.DataFrame([
            {"Quantity": "Width b", "Value": fmt_sig(b_val), "Unit": length_unit},
            {"Quantity": "Thickness h", "Value": fmt_sig(h_val), "Unit": length_unit},
            {"Quantity": "Member span L", "Value": fmt_sig(L_val), "Unit": length_unit},
            {"Quantity": "Hole diameter d", "Value": fmt_sig(d_val), "Unit": length_unit},
            {"Quantity": "Left hole offset", "Value": fmt_sig(edge_offset_val), "Unit": length_unit},
            {"Quantity": "Density", "Value": fmt_sig(rho_val), "Unit": density_unit},
            {"Quantity": "Yield strength", "Value": fmt_sig(Sy_val), "Unit": stress_unit},
            {"Quantity": "Scissor angle θ", "Value": fmt_sig(theta_deg), "Unit": "deg"},
            {"Quantity": "Stages n", "Value": fmt_sig(n), "Unit": "-"},
        ])
        st.dataframe(input_df, use_container_width=True, hide_index=True)

        show_step(
            "1. Hole-to-width ratio",
            r"x=\frac{d}{b}",
            rf"x=\frac{{{latex_num(d_val)}}}{{{latex_num(b_val)}}}",
            rf"x={latex_num(x_ratio)}"
        )

        show_step(
            "2. Axial stress concentration factor",
            r"K_t=2.95-2.855x+3.410x^2-1.678x^3",
            rf"K_t=2.95-2.855({latex_num(x_ratio)})+3.410({latex_num(x_ratio)})^2-1.678({latex_num(x_ratio)})^3",
            rf"K_t={latex_num(Kt_P)}"
        )

        st.markdown("#### 3. Converted SI values")
        si_df = pd.DataFrame([
            {"Quantity": "b", "Value": fmt_sig(b_m), "Unit": "m"},
            {"Quantity": "h", "Value": fmt_sig(h_m), "Unit": "m"},
            {"Quantity": "L", "Value": fmt_sig(L_m), "Unit": "m"},
            {"Quantity": "d", "Value": fmt_sig(d_m), "Unit": "m"},
            {"Quantity": "Edge offset", "Value": fmt_sig(edge_offset_m), "Unit": "m"},
            {"Quantity": "Density", "Value": fmt_sig(rho_kg_m3), "Unit": "kg/m^3"},
            {"Quantity": "Yield strength", "Value": fmt_sig(Sy_Pa), "Unit": "Pa"},
            {"Quantity": "P", "Value": fmt_sig(P_N_user), "Unit": "N"},
            {"Quantity": "Mz", "Value": fmt_sig(Mz_Nm), "Unit": "N·m"},
            {"Quantity": "Mx", "Value": fmt_sig(Mx_Nm), "Unit": "N·m"},
            {"Quantity": "My", "Value": fmt_sig(My_Nm), "Unit": "N·m"},
            {"Quantity": "dep", "Value": fmt_sig(dep_m), "Unit": "m"},
        ])
        st.dataframe(si_df, use_container_width=True, hide_index=True)

        st.markdown("#### 4. Statics results used by the solid member calculation")
        forces = solid["forces"]
        statics_df = pd.DataFrame([
            {"Quantity": "Xt", "Value": fmt_sig(forces["Xt"]), "Unit": "lbf"},
            {"Quantity": "Yt", "Value": fmt_sig(forces["Yt"]), "Unit": "lbf"},
            {"Quantity": "Xm", "Value": fmt_sig(forces["Xm"]), "Unit": "lbf"},
            {"Quantity": "Ym", "Value": fmt_sig(forces["Ym"]), "Unit": "lbf"},
            {"Quantity": "Xb", "Value": fmt_sig(forces["Xb"]), "Unit": "lbf"},
            {"Quantity": "Yb", "Value": fmt_sig(forces["Yb"]), "Unit": "lbf"},
            {"Quantity": "Max |V|", "Value": fmt_sig(solid["V_abs_max_lbf"]), "Unit": "lbf"},
            {"Quantity": "Max |M|", "Value": fmt_sig(solid["M_abs_max_lbf_in"]), "Unit": "lbf·in"},
            {"Quantity": "Member mass", "Value": fmt_sig(solid["mass_kg"]), "Unit": "kg"},
            {"Quantity": "Pin span used", "Value": fmt_sig(solid["L_pin_in"]), "Unit": "in"},
        ])
        st.dataframe(statics_df, use_container_width=True, hide_index=True)

        show_step(
            "5. Net area used for axial stress",
            r"A_{net}=(b-d)h",
            rf"A_{{net}}=({latex_num(b_m)}-{latex_num(d_m)})({latex_num(h_m)})",
            rf"A_{{net}}={latex_num(solid['A_net_report'])}\ \text{{m}}^2"
        )

        if d_m > 0:
            s_calc = ((b_m**3 - d_m**3) * h_m) / (6.0 * d_m)
            show_step(
                "6. Section modulus used for bending",
                r"S=\frac{(b^3-d\,^3)h}{6d}",
                rf"S=\frac{{({latex_num(b_m)}^3-{latex_num(d_m)}\,^3)({latex_num(h_m)})}}{{6({latex_num(d_m)})}}",
                rf"S={latex_num(s_calc)}\ \text{{m}}^3"
            )

        axial_force_N = solid["sigma_nom_P"] * solid["A_net_report"]
        show_step(
            "7. Nominal axial stress",
            r"\sigma_{nom,P}=\frac{P}{A_{net}}",
            rf"\sigma_{{nom,P}}=\frac{{{latex_num(axial_force_N)}}}{{{latex_num(solid['A_net_report'])}}}",
            rf"\sigma_{{nom,P}}={latex_num(solid['sigma_nom_P'])}\ \text{{Pa}}"
        )

        show_step(
            "8. Maximum axial stress",
            r"\sigma_{max,P}=K_t\,\sigma_{nom,P}",
            rf"\sigma_{{max,P}}=({latex_num(Kt_P)})({latex_num(solid['sigma_nom_P'])})",
            rf"\sigma_{{max,P}}={latex_num(solid['sigma_max_P'])}\ \text{{Pa}}"
        )

        max_moment_Nm = solid["M_abs_max_lbf_in"] * 4.44822 * 0.0254
        show_step(
            "9. Nominal bending stress",
            r"\sigma_{nom,M}=\frac{M}{S}",
            rf"\sigma_{{nom,M}}=\frac{{{latex_num(max_moment_Nm)}}}{{{latex_num(solid['S_report'])}}}",
            rf"\sigma_{{nom,M}}={latex_num(solid['sigma_nom_M'])}\ \text{{Pa}}"
        )

        show_step(
            "10. Maximum bending stress",
            r"\sigma_{max,M}=K_{t,M}\,\sigma_{nom,M}",
            rf"\sigma_{{max,M}}=(2.00)({latex_num(solid['sigma_nom_M'])})",
            rf"\sigma_{{max,M}}={latex_num(solid['sigma_max_M'])}\ \text{{Pa}}"
        )

        show_step(
            "11. Combined normal stress",
            r"\sigma=\sigma_{max,P}+\sigma_{max,M}",
            rf"\sigma=({latex_num(solid['sigma_max_P'])})+({latex_num(solid['sigma_max_M'])})",
            rf"\sigma={latex_num(solid['sigma_comb'])}\ \text{{Pa}}"
        )

        max_shear_N = solid["V_abs_max_lbf"] * 4.44822
        show_step(
            "12. Maximum shear stress",
            r"\tau=K_{t,\tau}\left(\frac{V}{A_{shear}}\right)",
            rf"\tau=(2.00)\left(\frac{{{latex_num(max_shear_N)}}}{{{latex_num(solid['A_shear_m2'])}}}\right)",
            rf"\tau={latex_num(solid['tau_max'])}\ \text{{Pa}}"
        )

        show_step(
            "13. Von Mises stress",
            r"\sigma_{vm}=\sqrt{\sigma^2+3\tau^2}",
            rf"\sigma_{{vm}}=\sqrt{{({latex_num(solid['sigma_comb'])})^2+3({latex_num(solid['tau_max'])})^2}}",
            rf"\sigma_{{vm}}={latex_num(results['solid_sigma_vm'])}\ \text{{Pa}}"
        )

        show_step(
            "14. Safety factor",
            r"SF=\frac{S_y}{\sigma_{vm}}",
            rf"SF=\frac{{{latex_num(Sy_Pa)}}}{{{latex_num(results['solid_sigma_vm'])}}}",
            rf"SF={latex_num(results['solid_SF'])}"
        )

        st.markdown("#### 15. Final solid member values")
        final_df = pd.DataFrame([
            {"Quantity": "Von Mises stress", "Value": fmt_sig(stress_from_Pa(results["solid_sigma_vm"], stress_unit)), "Unit": stress_unit},
            {"Quantity": "Safety factor", "Value": fmt_sig(results["solid_SF"]), "Unit": "-"},
            {"Quantity": "Status", "Value": "YIELDS" if results["solid_yields"] else "OK", "Unit": ""},
        ])
        st.dataframe(final_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")