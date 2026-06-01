import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 1. PAGE SETUP & STYLING
st.set_page_config(page_title="Desalination Digital Twin", layout="wide")

st.title("🖥️ Industrial Desalination Digital Twin")
st.markdown("### Ultimate Engineering Suite: Sizing, Crisis Loops, SCADA Logs & ROI Payback Engine")
st.write("---")

# Water Source Template Database
WATER_TEMPLATES = {
    "Custom / Manual Input": None,
    "Arabian Gulf Seawater (High TDS)": {
        "na": 11500.0, "cl": 21000.0, "ca": 450.0, "so4": 3000.0, "alk": 150.0
    },
    "Arizona Brackish Groundwater (High Hardness)": {
        "na": 450.0, "cl": 680.0, "ca": 220.0, "so4": 410.0, "alk": 280.0
    }
}

# Branded Membrane Specification Database
MEMBRANE_MANUFACTURERS = {
    "DuPont™ FilmTec™ BW30-400 (Standard Brackish)": {
        "aw_mod": 1.00, "rejection": 0.9970, "compaction": 0.065, "leak_grow": 0.15, "cost": 480.0, "area": 37.2
    }
}

# Initialize persistent session state tracking
if "na_val" not in st.session_state: st.session_state.na_val = 650.0
if "cl_val" not in st.session_state: st.session_state.cl_val = 950.0
if "ca_val" not in st.session_state: st.session_state.ca_val = 180.0
if "so4_val" not in st.session_state: st.session_state.so4_val = 520.0
if "alk_val" not in st.session_state: st.session_state.alk_val = 220.0

if "target_ph" not in st.session_state: st.session_state.target_ph = 7.8
if "as_dosage" not in st.session_state: st.session_state.as_dosage = 3.0
if "prev_template" not in st.session_state: st.session_state.prev_template = "Custom / Manual Input"

# 2. SIDEBAR PANEL FOR INTERACTIVE SETTINGS
st.sidebar.header("⚙️ Plant Operating Framework")

st.sidebar.subheader("📐 Sizing Slices")
design_flux_lmh = st.sidebar.slider("Target Average Flux (LMH)", min_value=10.0, max_value=30.0, value=18.0)
custom_elements = st.sidebar.slider("Elements Loaded / Pressure Vessel", min_value=4, max_value=8, value=6, step=1)

st.sidebar.subheader("🌊 Hydraulic & Thermodynamic Bounds")
if "flow_val" not in st.session_state: st.session_state.flow_val = 346.4
Q_feed_total = st.sidebar.slider("Feed Flow Rate (Q₀, m³/h)", 50.0, 600.0, float(st.session_state.flow_val), step=10.0)
Y_user_target = st.sidebar.slider("Target Recovery Goal (Y, %)", 40.0, 96.0, 75.0, step=0.5)
T_operating = st.sidebar.slider("Operating Temp (°C)", 5.0, 45.0, 25.0, step=1.0)

selected_mem = MEMBRANE_MANUFACTURERS["DuPont™ FilmTec™ BW30-400 (Standard Brackish)"]
cip_frequency_months = st.sidebar.slider("CIP Flush Interventions", min_value=2, max_value=12, value=6)
has_erd = st.sidebar.toggle("Deploy Isobaric Energy Recovery (ERD)", value=True)

st.sidebar.subheader("🎛️ Utility Tariff Adjustments")
elec_rate = st.sidebar.number_input("Electricity Tariff ($/kWh)", 0.01, 0.50, 0.12, 0.01)
as_chem_rate = st.sidebar.number_input("Anti-Scalant Bulk Cost ($/kg)", 1.0, 15.0, 4.50, 0.50)

acid_choice = st.sidebar.selectbox("Acid Treatment Strategy", ["None", "Sulfuric Acid (H2SO4)"])
st.session_state.target_ph = st.sidebar.slider("Target Dosed pH", 5.0, 7.8, float(st.session_state.target_ph), step=0.1) if acid_choice != "None" else 7.8
st.session_state.as_dosage = st.sidebar.slider("Anti-Scalant Target (mg/L)", 0.0, 12.0, float(st.session_state.as_dosage), step=0.5)


# 3. INTERACTIVE CRISIS STRESS TESTER (Maintained context across layers)
st.subheader("🚨 Interactive Plant Failure Mode Simulator")
col_fail1, col_fail2, col_fail3 = st.columns(3)
with col_fail1: fail_valve_jam = st.toggle("💥 Feed Valve Jam (40% Flow Drop)", value=False)
with col_fail2: fail_sbs_pump = st.toggle("☣️ SBS Chemical Pump Failure", value=False)
with col_fail3: fail_algae_bloom = st.toggle("🌿 Red Tide Algae Bloom Event", value=False)

modified_feed_flow = Q_feed_total * 0.60 if fail_valve_jam else Q_feed_total
base_leak_growth_modifier = 4.5 if fail_sbs_pump else 1.0
base_fouling_multiplier = 5.0 if fail_algae_bloom else 1.0


# 4. WATER CHEMISTRY INTERFACE
st.write("---")
st.subheader("💧 Raw Water Influent Chemistry")
selected_template = st.selectbox("📂 Select Feed Source Template Preset", options=list(WATER_TEMPLATES.keys()), index=list(WATER_TEMPLATES.keys()).index(st.session_state.prev_template))

if selected_template != st.session_state.prev_template and WATER_TEMPLATES[selected_template] is not None:
    preset = WATER_TEMPLATES[selected_template]
    st.session_state.na_val, st.session_state.cl_val, st.session_state.ca_val, st.session_state.so4_val, st.session_state.alk_val = preset["na"], preset["cl"], preset["ca"], preset["so4"], preset["alk"]
    st.session_state.prev_template = selected_template
    st.rerun()

col_na, col_cl, col_ca, col_so4, col_alk = st.columns(5)
with col_na: na_input = st.number_input("Sodium (Na⁺, mg/L)", 0.0, 100000.0, float(st.session_state.na_val), 10.0)
with col_cl: cl_input = st.number_input("Chloride (Cl⁻, mg/L)", 0.0, 100000.0, float(st.session_state.cl_val), 10.0)
with col_ca: ca_input = st.number_input("Calcium (Ca²⁺, mg/L)", 0.0, 50000.0, float(st.session_state.ca_val), 5.0)
with col_so4: so4_input = st.number_input("Sulfate (SO₄²⁻, mg/L)", 0.0, 50000.0, float(st.session_state.so4_val), 10.0)
with col_alk: alk_input = st.number_input("Alkalinity (HCO₃⁻, mg/L)", 0.0, 50000.0, float(st.session_state.alk_val), 5.0)

ph_delta = max(0.0, 7.8 - st.session_state.target_ph)
dosed_alk = st.session_state.alk_val * max(0.10, 1.0 - (ph_delta * 0.45))
dosed_so4 = st.session_state.so4_val + (ph_delta * 55.0) if acid_choice == "Sulfuric Acid (H2SO4)" else st.session_state.so4_val
treated_chemistry = {'Na': st.session_state.na_val, 'Cl': cl_input, 'Ca': st.session_state.ca_val, 'SO4': dosed_so4, 'HCO3': dosed_alk}

local_inlet_tds = sum(treated_chemistry.values())


# 5. HIGH-FIDELITY SIMULATION COMPUTE BLOCK (Simulates all 3 modes for financial mapping)
q_permeate_calc = modified_feed_flow * (Y_user_target / 100.0)
required_surface_area_m2 = (q_permeate_calc * 1000.0) / design_flux_lmh
calculated_total_elements = int(np.ceil(required_surface_area_m2 / selected_mem["area"]))
vessel_count = int(np.ceil(calculated_total_elements / custom_elements))

def calculate_lsi(tds, temp_c, calcium, alkalinity, current_ph):
    log10_tds = np.log10(max(10.0, tds))
    A, B = (log10_tds - 1.0) / 10.0, -13.12 * np.log10(temp_c + 273.15) + 34.55
    C, D = np.log10(max(1.0, calcium * 2.497)) - 0.40, np.log10(max(1.0, alkalinity * 0.82))
    return current_ph - ((9.3 + A + B) - (C + D))

full_tech_registry = {
    'Conventional': {'stages': 2, 'elements': custom_elements, 'Aw': 1.25, 'color': '#95a5a6', 'scale_factor': 0.180, 'target_flux': design_flux_lmh, 'premium_capex_mult': 1.0},
    'CCRO': {'stages': 1, 'elements': custom_elements, 'Aw': 1.85, 'color': '#3498db', 'scale_factor': 0.120, 'target_flux': design_flux_lmh + 2.0, 'premium_capex_mult': 1.28},
    'PFRO': {'stages': 2, 'elements': custom_elements, 'Aw': 2.45, 'color': '#2ecc71', 'scale_factor': 0.090, 'target_flux': design_flux_lmh + 4.5, 'premium_capex_mult': 1.15}
}

t_kelvin_base, t_kelvin_actual = 298.15, 273.15 + T_operating
TCF = np.exp(2640.0 * (1.0 / t_kelvin_base - 1.0 / t_kelvin_actual))
months_axis = np.arange(0, 49)

technology_financial_matrix = {}

for tech, cfg in full_tech_registry.items():
    pressures, secs = [], []
    accumulated_fouling_resistance = 0.0
    
    for m in months_axis:
        if m > 0 and m % cip_frequency_months == 0:
            accumulated_fouling_resistance *= (1.0 - 0.95)
            
        yr_equivalent = m / 12.0
        Aw_base_degrade = cfg['Aw'] * selected_mem['aw_mod'] * TCF * (1.0 - selected_mem['compaction'] * np.log1p(yr_equivalent))
        
        conc_mult = 1.0 / max(0.01, 1.0 - (Y_user_target / 100.0))
        tail_ca = treated_chemistry['Ca'] * conc_mult
        tail_tds = local_inlet_tds * conc_mult
        
        caso4_sat = (((tail_ca / 40078) * (treated_chemistry['SO4'] * conc_mult / 96060)) / 2.4e-5) * 100.0
        tail_lsi = calculate_lsi(tail_tds, T_operating, tail_ca, treated_chemistry['HCO3'] * conc_mult, st.session_state.target_ph)
        
        supersat = max(0.0, tail_lsi - 1.0) + (max(0.0, caso4_sat - 120.0) * 0.025)
        accumulated_fouling_resistance += (supersat * cfg['scale_factor'] * base_fouling_multiplier) * (0.05 if tech == 'CCRO' else 0.12)
        
        avg_ndp = (cfg['target_flux'] / (1.0 + accumulated_fouling_resistance)) / Aw_base_degrade
        friction = (cfg['stages'] * cfg['elements']) * 0.45
        pump_p = max(12.0, min(140.0, avg_ndp + (0.0072 * ((local_inlet_tds + tail_tds) / 2) * 0.45) + friction))
        
        if has_erd:
            net_kw = max(5.0, (((modified_feed_flow * pump_p) / 36.0) / 0.86) - (((modified_feed_flow * ((100.0 - Y_user_target)/100.0)) * pump_p * 0.94) / 36.0))
        else:
            net_kw = max(5.0, (((modified_feed_flow * pump_p) / 36.0) / 0.86))
            
        pressures.append(pump_p)
        secs.append(net_kw / (modified_feed_flow * (Y_user_target / 100.0)))
        
    # Asset Ledger Sizing Calculations
    annual_water_yield_m3 = (modified_feed_flow * (Y_user_target / 100.0) * 24.0) * 365.0
    avg_sec = np.mean(secs)
    
    # Financial Sizing Models
    base_hardware_capex = (vessel_count * 12500.0) + (calculated_total_elements * selected_mem['cost'])
    total_capex = base_hardware_capex * cfg['premium_capex_mult']
    
    annual_power_opex = (avg_sec * annual_water_yield_m3) * elec_rate
    annual_chemical_opex = (((st.session_state.as_dosage / 1e6) * (modified_feed_flow * 24 * 1000)) * 365.0 * as_chem_rate) + ((12/cip_frequency_months) * vessel_count * 200.0)
    total_opex = annual_power_opex + annual_chemical_opex
    
    technology_financial_matrix[tech] = {
        'capex': total_capex, 'opex': total_opex, 'sec': avg_sec, 'water': annual_water_yield_m3
    }


# --- 6. NEW FEATURE MODULE: ROI & PAYBACK ENGINE MATRIX ---
st.write("---")
st.subheader("💰 Technology Financial Pro Forma & Capital Payback Asset Matrix")

conv_f = technology_financial_matrix['Conventional']
ccro_f = technology_financial_matrix['CCRO']
pfro_f = technology_financial_matrix['PFRO']

# Payback period logic (Delta CAPEX / Delta OPEX savings)
ccro_opex_savings = conv_f['opex'] - ccro_f['opex']
ccro_capex_premium = ccro_f['capex'] - conv_f['capex']
ccro_payback = ccro_capex_premium / ccro_opex_savings if ccro_opex_savings > 0 else float('inf')

pfro_opex_savings = conv_f['opex'] - pfro_f['opex']
pfro_capex_premium = pfro_f['capex'] - conv_f['capex']
pfro_payback = pfro_capex_premium / pfro_opex_savings if pfro_opex_savings > 0 else float('inf')

# Render side-by-side ROI metrics
roi_col1, roi_col2, roi_col3 = st.columns(3)
with roi_col1:
    st.metric(label="Conventional Base Asset Footprint", value=f"${conv_f['capex']:,.0f} CAPEX", caption=f"Baseline OPEX: ${conv_f['opex']:,.0f}/yr")
with roi_col2:
    if ccro_payback != float('inf') and ccro_payback > 0:
        st.metric(label="CCRO System Return On Investment", value=f"{ccro_payback:.2f} Years Payback", delta=f"${ccro_opex_savings:,.0f}/yr Saved", delta_color="normal")
    else:
        st.metric(label="CCRO System Return On Investment", value="No Payback", caption="Fouling profile limits savings vs Conventional base")
with roi_col3:
    if pfro_payback != float('inf') and pfro_payback > 0:
        st.metric(label="PFRO System Return On Investment", value=f"{pfro_payback:.2f} Years Payback", delta=f"${pfro_opex_savings:,.0f}/yr Saved", delta_color="normal")
    else:
        st.metric(label="PFRO System Return On Investment", value="No Payback", caption="Fouling profile limits savings vs Conventional base")

# Dataframe Breakdown Matrix
pro_forma_data = {
    "Financial Metric": ["Total Asset Initial CAPEX", "Annualized Operations OPEX", "Mean Specific Energy (SEC)"],
    "Conventional Setup": [f"${conv_f['capex']:,.2f}", f"${conv_f['opex']:,.2f}", f"{conv_f['sec']:.3f} kWh/m³"],
    "CCRO Architecture": [f"${ccro_f['capex']:,.2f}", f"${ccro_f['opex']:,.2f}", f"{ccro_f['sec']:.3f} kWh/m³"],
    "PFRO Framework": [f"${pfro_f['capex']:,.2f}", f"${pfro_f['opex']:,.2f}", f"{pfro_f['sec']:.3f} kWh/m³"]
}
st.table(pd.DataFrame(pro_forma_data).set_index("Financial Metric"))


# 7. COMPARATIVE METRIC PLOTS
st.write("---")
st.subheader("📊 Lifecycle Financial Asset Comparison Chart")

fig, ax = plt.subplots(1, 2, figsize=(15, 4.0))

labels = ['Conventional', 'CCRO', 'PFRO']
capexs = [conv_f['capex'], ccro_f['capex'], pfro_f['capex']]
opexs = [conv_f['opex'], ccro_f['opex'], pfro_f['opex']]
colors = [full_tech_registry['Conventional']['color'], full_tech_registry['CCRO']['color'], full_tech_registry['PFRO']['color']]

ax[0].bar(labels, capexs, color=colors, alpha=0.85, edgecolor='black')
ax[0].set_title("Total Capital Procurement Expense (CAPEX, $)")
ax[0].grid(True, linestyle=":", alpha=0.6)

ax[1].bar(labels, opexs, color=colors, alpha=0.85, edgecolor='black')
ax[1].set_title("Annual Operational Expenditure (OPEX, $/yr)")
ax[1].grid(True, linestyle=":", alpha=0.6)

st.pyplot(fig)
