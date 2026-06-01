import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# 1. PAGE SETUP & STYLING
st.set_page_config(page_title="Desalination Digital Twin", layout="wide")

st.title("🖥️ Industrial Desalination Digital Twin")
st.markdown("### Multi-Year Operational Lifecycle & Membrane Degradation Suite")
st.write("---")

# 2. SIDEBAR PANEL FOR INTERACTIVE SETTINGS
st.sidebar.header("⚙️ Plant Operating Framework")

# Flow and Targets
Q_feed_total = st.sidebar.slider("Feed Flow Rate (Q₀, m³/h)", 50.0, 600.0, 346.4, step=10.0)
Y_user_target = st.sidebar.slider("Target Recovery Goal (Y, %)", 70.0, 96.0, 92.0, step=0.5)
T_operating = st.sidebar.slider("Operating Temperature (°C)", 5.0, 45.0, 25.0, step=1.0)

# Membrane Specs
st.sidebar.subheader("🧬 Membrane Specifications")
mem_choice = st.sidebar.selectbox(
    "Select Membrane Element Model",
    ["Standard Brackish (BW30)", "Low Energy (LE)", "High-Rejection (SW30)"]
)
horizon_years = st.sidebar.slider("Lifecycle Evaluation Window (Years)", 1, 7, 5)

# Chemical Pre-Treatment
st.sidebar.subheader("🧪 Chemical Pre-Treatment & Dosing")
acid_choice = st.sidebar.selectbox("Acid Treatment Strategy", ["None", "Sulfuric Acid (H2SO4)", "Hydrochloric Acid (HCl)"])
target_ph = st.sidebar.slider("Target Dosed pH", 5.0, 7.8, 7.8, step=0.1) if acid_choice != "None" else 7.8
as_dosage = st.sidebar.slider("Anti-Scalant Target (mg/L)", 0.0, 12.0, 3.0, step=0.5)

# 3. MAIN INTERFACE: INFLUENT WATER CHEMISTRY ENTRY
st.subheader("💧 Raw Water Influent Chemistry")
col_na, col_cl, col_ca, col_so4, col_alk = st.columns(5)

with col_na: na_input = st.number_input("Sodium (Na⁺, mg/L)", value=650.0)
with col_cl: cl_input = st.number_input("Chloride (Cl⁻, mg/L)", value=950.0)
with col_ca: ca_input = st.number_input("Calcium (Ca²⁺, mg/L)", value=180.0)
with col_so4: so4_input = st.number_input("Sulfate (SO₄²⁻, mg/L)", value=520.0)
with col_alk: alk_input = st.number_input("Alkalinity (HCO₃⁻, mg/L)", value=220.0)

# 4. KINETICS & ENGINE CALCULATIONS
mem_registry = {
    'Low Energy (LE)': {'aw_mod': 1.35, 'rejection': 0.993, 'compaction': 0.095, 'leak_grow': 0.22},
    'Standard Brackish (BW30)': {'aw_mod': 1.00, 'rejection': 0.997, 'compaction': 0.065, 'leak_grow': 0.15},
    'High-Rejection (SW30)': {'aw_mod': 0.65, 'rejection': 0.9985, 'compaction': 0.035, 'leak_grow': 0.08}
}
selected_mem = mem_registry[mem_choice]

# Chemical transformations
ph_delta = max(0.0, 7.8 - target_ph)
dosed_alk = alk_input * max(0.10, 1.0 - (ph_delta * 0.45))
dosed_so4 = so4_input + (ph_delta * 55.0) if acid_choice == "Sulfuric Acid (H2SO4)" else so4_input
dosed_cl = cl_input + (ph_delta * 40.0) if acid_choice == "Hydrochloric Acid (HCl)" else cl_input
treated_chemistry = {'Na': na_input, 'Cl': dosed_cl, 'Ca': ca_input, 'SO4': dosed_so4, 'HCO3': dosed_alk}

def calculate_lsi(tds, temp_c, calcium, alkalinity, current_ph):
    log10_tds = np.log10(max(10.0, tds))
    A = (log10_tds - 1.0) / 10.0
    B = -13.12 * np.log10(temp_c + 273.15) + 34.55
    C = np.log10(max(1.0, calcium * 2.497)) - 0.40
    D = np.log10(max(1.0, alkalinity * 0.82))
    return current_ph - ((9.3 + A + B) - (C + D))

# Technology performance properties
tech_registry = {
    'PFRO': {'stages': 1, 'elements': 6, 'Aw': 2.45, 'color': '#2ecc71', 'scale_factor': 0.090, 'target_flux': 24.5},
    'FRRO': {'stages': 2, 'elements': 6, 'Aw': 1.45, 'color': '#e67e22', 'scale_factor': 0.050, 'target_flux': 19.0},
    'CCRO': {'stages': 1, 'elements': 7, 'Aw': 1.85, 'color': '#3498db', 'scale_factor': 0.120, 'target_flux': 21.0},
    'Conventional': {'stages': 2, 'elements': 7, 'Aw': 1.25, 'color': '#95a5a6', 'scale_factor': 0.180, 'target_flux': 17.5}
}

t_kelvin_base = 298.15
t_kelvin_actual = 273.15 + T_operating
TCF = np.exp(2640.0 * (1.0 / t_kelvin_base - 1.0 / t_kelvin_actual))
vfd_eff = 0.98 if abs(T_operating - 25.0) < 5 else 0.95
local_inlet_tds = sum(treated_chemistry.values())

years_axis = np.arange(0, horizon_years + 1)
lifecycle_results = {}

for tech, cfg in tech_registry.items():
    pressures, secs, perm_tds = [], [], []
    res_factor = 0.7 if tech in ['PFRO', 'CCRO'] else 1.2
    gypsum_ceiling = 100.0 if as_dosage == 0 else min(600.0, 100.0 + (25.5 * (as_dosage ** 1.15) * np.exp(-0.15 * res_factor)))
    
    for yr in years_axis:
        Aw_corrected = cfg['Aw'] * selected_mem['aw_mod'] * TCF * (1.0 - selected_mem['compaction'] * np.log1p(yr))
        current_rejection = min(0.9995, selected_mem['rejection'] / (1.0 + selected_mem['leak_grow'] * yr))
        
        conc_mult = 1.0 / max(0.01, 1.0 - (Y_user_target / 100.0))
        tail_ca, tail_so4, tail_tds = treated_chemistry['Ca'] * conc_mult, treated_chemistry['SO4'] * conc_mult, local_inlet_tds * conc_mult
        
        caso4_sat = (((tail_ca / 40078) * (tail_so4 / 96060)) / 2.4e-5) * 100.0
        tail_lsi = calculate_lsi(tail_tds, T_operating, tail_ca, treated_chemistry['HCO3'] * conc_mult, target_ph)
        
        supersat = max(0.0, tail_lsi - 1.0) + (max(0.0, caso4_sat - gypsum_ceiling) * 0.025)
        
        scale_res = supersat * cfg['scale_factor'] * (1.4 if tech == 'Conventional' else 0.35 if tech == 'CCRO' else 0.15 if tech == 'PFRO' else 0.4)
        avg_ndp = (cfg['target_flux'] / (1.0 + scale_res)) / Aw_corrected
        
        pump_p = max(12.0, min(140.0, avg_ndp + (0.0072 * ((local_inlet_tds + tail_tds) / 2) * 0.45) + (cfg['stages'] * cfg['elements'] * (0.55 if tech in ['Conventional', 'FRRO'] else 0.35))))
        net_kw = max(5.0, (((Q_feed_total * pump_p) / 36.0) / (0.85 * vfd_eff)) - (((Q_feed_total * (1.0 - Y_user_target/100.0)) * pump_p * 0.95) / 36.0))
        
        pressures.append(pump_p)
        secs.append(net_kw / (Q_feed_total * (Y_user_target / 100.0)))
        perm_tds.append(local_inlet_tds * (1.0 - current_rejection))
        
    lifecycle_results[tech] = {'p': pressures, 'sec': secs, 'tds': perm_tds}

# 5. RENDER SYSTEM PLOTS
st.subheader(f"📊 Plant Performance Projections over {horizon_years} Years ({mem_choice} Membranes)")

fig, ax = plt.subplots(1, 3, figsize=(15, 5))
for tech, data in lifecycle_results.items():
    color = tech_registry[tech]['color']
    ax[0].plot(years_axis, data['p'], 'o-', color=color, linewidth=2, label=tech)
    ax[1].plot(years_axis, data['sec'], 's-', color=color, linewidth=2)
    ax[2].plot(years_axis, data['tds'], 'D-', color=color, linewidth=2)

ax[0].set_title("Required Pump Pressure (bar)", fontweight='bold')
ax[0].set_xlabel("Years")
ax[0].grid(True, linestyle=":")
ax[0].legend()

ax[1].set_title("Specific Energy Cost (kWh/m³)", fontweight='bold')
ax[1].set_xlabel("Years")
ax[1].grid(True, linestyle=":")

ax[2].set_title("Permeate Product Water TDS (mg/L)", fontweight='bold')
ax[2].set_xlabel("Years")
ax[2].axhline(500.0, color='red', linestyle='--', alpha=0.7, label='WHO Cap')
ax[2].grid(True, linestyle=":")
ax[2].legend()

st.pyplot(fig)
