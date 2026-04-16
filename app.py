import os
import pandas as pd
import altair as alt
import streamlit as st

from logic import (
    analyze_system,
    convert_length_to_m,
    convert_force_to_N,
    convert_moment_to_Nm,
    convert_stress_to_Pa,
    convert_density_to_kg_m3,
    stress_from_Pa,
    length_from_m,
)

st.set_page_config(page_title="JMU Scissor Member Stress App", layout="wide")

# ---------- Theme / Font ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Faculty+Glyphic&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(to bottom, #f8f6f2 0%, #fffaf0 100%);
}

/* Headers */
h1, h2, h3 {
    color: #450084;
    font-family: 'Inter', sans-serif !important;
}

/* General text */
p, div, span, label {
    font-family: 'Inter', sans-serif !important;
    color: #222222;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(to bottom, #450084 0%, #5c1a9c 100%);
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

/* Sidebar selectboxes */
section[data-testid="stSidebar"] div[data-baseweb="select"] * {
    color: black !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: #fffaf0 !important;
    border: 2px solid #c99700 !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}

/* Remove cursor artifacts from selectboxes */
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

/* Dropdown menu */
ul[role="listbox"] li,
div[role="option"] {
    color: black !important;
    background-color: white !important;
}

/* Metric cards */
[data-testid="metric-container"] {
    border: 2px solid #c99700;
    padding: 12px;
    border-radius: 12px;
    background: linear-gradient(to bottom right, white, #fff8dc);
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}

/* Number inputs */
input {
    border: 2px solid #c99700 !important;
    border-radius: 8px !important;
}

/* Labels */
label {
    color: #450084 !important;
    font-weight: 700;
}

/* Tables */
.stDataFrame {
    background-color: white;
    border: 2px solid #c99700;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar Logos ----------
logo1 = "logo.png"
logo2 = "logo2.png"

if os.path.exists(logo1):
    st.sidebar.image(logo1, use_container_width=True)

if os.path.exists(logo2):
    left, center, right = st.sidebar.columns([1, 3, 1])
    with center:
        st.image(logo2, width=180)

# ---------- Header ----------
st.title("JMU Engineering Theater Capstone Stress Analysis App")
st.caption("Purple and gold engineering analysis tool")

# ---------- Cross-member reference image just below title/description ----------
crossmember_img = "crossmember.png"
if os.path.exists(crossmember_img):
    st.image(crossmember_img, use_container_width=True)

# ---------- Sidebar Units ----------
st.sidebar.header("Unit settings")

length_unit = st.sidebar.selectbox("Length unit", ["in", "mm", "cm", "m"], index=0)
force_unit = st.sidebar.selectbox("Force unit", ["lbf", "N", "kN", "kip"], index=0)
moment_unit = st.sidebar.selectbox("Moment unit", ["ft-lb", "Nm", "kNm", "kip-ft"], index=0)
stress_unit = st.sidebar.selectbox("Stress unit", ["ksi", "MPa", "psi", "Pa"], index=0)
density_unit = st.sidebar.selectbox("Density unit", ["kg/m3", "g/cm3", "lb/ft3"], index=2)

# ---------- Inputs ----------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Geometry")
    b_val = st.number_input("Width b", value=3.0, min_value=0.0001, format="%.4f")
    h_val = st.number_input("Thickness h", value=0.25, min_value=0.0001, format="%.4f")
    L_val = st.number_input("Member span L", value=20.0, min_value=0.0001, format="%.4f")
    d_val = st.number_input("Pin-hole diameter d", value=1.0, min_value=0.0, format="%.4f")
    edge_offset_val = st.number_input("Distance from left edge to left hole", value=0.75, min_value=0.0, format="%.4f")

    st.subheader("Material")
    rho_val = st.number_input("Material density", value=490.0, min_value=0.0001, format="%.4f")
    Sy_val = st.number_input("Yield strength", value=36.0, min_value=0.0001, format="%.4f")
    Kt_P = st.number_input("Kt_P", value=2.0, min_value=0.0, format="%.3f")

with col2:
    st.subheader("Configuration")
    theta_deg = st.slider("Scissor angle θ", 1, 89, 15)
    n = st.slider("Stages n", 1, 10, 1)

    sit = st.selectbox(
        "Loading situation",
        options=[1, 2, 6, 7],
        format_func=lambda x: {
            1: "1 - Centered vertical payload P",
            2: "2 - Overturning moment about Z (Mz)",
            6: "6 - Overturning moment about X (Mx)",
            7: "7 - Overturning moment about Y (My)",
        }[x],
    )

    P_val = Mz_val = Mx_val = My_val = dep_val = 0.0

    if sit == 1:
        P_val = st.number_input("Payload P", value=225.0, min_value=0.0, format="%.4f")
    elif sit == 2:
        Mz_val = st.number_input("Moment Mz", value=100.0, min_value=0.0, format="%.4f")
    elif sit == 6:
        Mx_val = st.number_input("Moment Mx", value=100.0, min_value=0.0, format="%.4f")
        dep_val = st.number_input("Spacing dep", value=6.0, min_value=0.0001, format="%.4f")
    elif sit == 7:
        My_val = st.number_input("Moment My", value=100.0, min_value=0.0, format="%.4f")
        dep_val = st.number_input("Spacing dep", value=6.0, min_value=0.0001, format="%.4f")

    st.subheader("Cross Bracing")
    use_cb = st.checkbox("Include cross bracing", value=False)

    cb_outer_val = cb_len_val = cb_t_val = None

    if use_cb:
        cb_outer_val = st.number_input("Cross-brace outer width/height", value=1.0, min_value=0.0001, format="%.4f")
        cb_len_val = st.number_input("Cross-brace length", value=18.0, min_value=0.0001, format="%.4f")
        cb_t_val = st.number_input("Cross-brace wall thickness", value=0.065, min_value=0.0001, format="%.4f")

# ---------- Sweep ----------
st.subheader("Tube Sweep")

c1, c2, c3, c4 = st.columns(4)

with c1:
    tube_t_min_val = st.number_input("Min t", value=0.065, min_value=0.0001, format="%.4f")
with c2:
    tube_t_max_val = st.number_input("Max t", value=0.250, min_value=0.0001, format="%.4f")
with c3:
    tube_t_step_val = st.number_input("Step t", value=0.020, min_value=0.0001, format="%.4f")
with c4:
    SF_target = st.number_input("Target SF", value=1.20, min_value=0.0001, format="%.3f")

# ---------- Run ----------
try:
    b_m = convert_length_to_m(b_val, length_unit)
    h_m = convert_length_to_m(h_val, length_unit)
    L_m = convert_length_to_m(L_val, length_unit)
    d_m = convert_length_to_m(d_val, length_unit)
    edge_offset_m = convert_length_to_m(edge_offset_val, length_unit)

    rho_kg_m3 = convert_density_to_kg_m3(rho_val, density_unit)
    Sy_Pa = convert_stress_to_Pa(Sy_val, stress_unit)

    P_N_user = convert_force_to_N(P_val, force_unit) if sit == 1 else 0.0
    Mz_Nm = convert_moment_to_Nm(Mz_val, moment_unit) if sit == 2 else 0.0
    Mx_Nm = convert_moment_to_Nm(Mx_val, moment_unit) if sit == 6 else 0.0
    My_Nm = convert_moment_to_Nm(My_val, moment_unit) if sit == 7 else 0.0
    dep_m = convert_length_to_m(dep_val, length_unit) if sit in [6, 7] else 0.0

    cb_outer_m = convert_length_to_m(cb_outer_val, length_unit) if use_cb else None
    cb_len_m = convert_length_to_m(cb_len_val, length_unit) if use_cb else None
    cb_t_m = convert_length_to_m(cb_t_val, length_unit) if use_cb else None

    tube_t_min_m = convert_length_to_m(tube_t_min_val, length_unit)
    tube_t_max_m = convert_length_to_m(tube_t_max_val, length_unit)
    tube_t_step_m = convert_length_to_m(tube_t_step_val, length_unit)

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
        tube_t_min_m=tube_t_min_m,
        tube_t_max_m=tube_t_max_m,
        tube_t_step_m=tube_t_step_m,
        SF_target=SF_target,
    )

    st.subheader("Results")

    a, b, c = st.columns(3)
    a.metric("Von Mises", f"{stress_from_Pa(results['solid_sigma_vm'], stress_unit):.3f} {stress_unit}")
    b.metric("Safety Factor", f"{results['solid_SF']:.3f}")
    c.metric("Status", "YIELDS" if results["solid_yields"] else "OK")

    st.caption("Using original-script defaults: Kt_M = 2.0 and Kt_tau = 2.0")

    rows = []
    for r in results["tube_rows"]:
        rows.append({
            f"t ({length_unit})": round(length_from_m(r["t_m"], length_unit), 4),
            "mass (kg)": round(r["mass_kg"], 4),
            f"σ_vm ({stress_unit})": round(stress_from_Pa(r["sigma_vm"], stress_unit), 4),
            "SF": round(r["SF"], 4),
        })

    if rows:
        df = pd.DataFrame(rows)

        st.subheader("Tube Candidates")
        st.dataframe(df, use_container_width=True, hide_index=True)

        x_col = f"t ({length_unit})"

        chart = (
            alt.Chart(df)
            .mark_line(point=alt.OverlayMarkDef(size=100, filled=True))
            .encode(
                x=alt.X(x_col, title=x_col),
                y=alt.Y("SF", title="Safety Factor"),
                tooltip=[x_col, "mass (kg)", f"σ_vm ({stress_unit})", "SF"]
            )
            .properties(height=400)
        )

        st.altair_chart(chart, use_container_width=True)

    viable_rows = []
    for r in results["tube_viable"]:
        viable_rows.append({
            f"t ({length_unit})": round(length_from_m(r["t_m"], length_unit), 4),
            "mass (kg)": round(r["mass_kg"], 4),
            "SF": round(r["SF"], 4),
        })

    st.subheader("Viable Options")
    if viable_rows:
        st.dataframe(pd.DataFrame(viable_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No options meet target safety factor.")

except Exception as e:
    st.error(f"Error: {e}")

