import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# 1. PAGE SETUP & STYLING
st.set_page_config(page_title="Desalination Digital Twin", layout="wide")

st.title("🖥️ EPC Industrial Desalination Plant & Process Simulator")
st.markdown("### Process Engineering Sizing Suite: Fluid Hydrodynamics, Aqueous Chemistry Balancing & SCADA Telemetry")
st.write("---")

# Water Source Template Database
WATER_TEMPLATES = {
    "Custom / Manual Input": None,
    "Arabian Gulf Seawater (High TDS)": {
        "na": 11500.0, "cl": 21000.0, "ca": 450.0, "so4": 3000.0, "alk": 150.0
    },
    "Arizona Brackish Groundwater (High Hardness)": {
        "na": 450.0, "cl": 680.0, "ca": 220.0, "so4": 410.0, "alk": 280.0
    },
    "Industrial Wastewater Effluent (High Alkalinity)": {
        "na": 950.0, "cl": 1100.0, "ca": 90.0, "so4": 550.0, "alk": 650.0
    }
}

# Branded Membrane Specification Database with Geometric Constants
MEMBRANE_MANUFACTURERS = {
    "DuPont™ FilmTec™ BW30-400 (Standard Brackish)": {
        "aw_mod": 1.00, "rejection": 0.9970, "compaction": 0.065, "leak_grow": 0.15, "area": 37.2, "spacer_mil": 34
    },
    "DuPont™ FilmTec™ Eco PRO-400 (Low Energy)": {
        "aw_mod": 1.35, "rejection": 0.9940, "compaction": 0.085, "leak_grow": 0.18, "area": 37.2, "spacer_mil": 28
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
st.sidebar.header("⚙️ Plant Sizing & Operational Framework")

st.sidebar.subheader("👁️ Visualization Architecture Scope")
view_scope = st.sidebar.selectbox(
    "Select Simulation View Scope",
    options=["All Comparison Matrices Simultaneously", "Conventional Only", "CCRO Only", "PFRO Only"]
)

st.sidebar.subheader("📐 Mechanical Sizing Parameters")
design_flux_lmh = st.sidebar.slider("Target Average Design Flux (LMH)", min_value=10.0, max_value=30.0, value=17.5, step=0.5)
custom_elements = st.sidebar.slider("Elements per Pressure Vessel (NV)", min_value=4, max_value=8, value=6, step=1)
vessels_parallel = st.sidebar.slider("Parallel Vessel Train Count (PV)", min_value=2, max_value=60, value=16, step=1)

st.sidebar.subheader("🌊 Hydraulic Bounds")
if "flow_val" not in st.session_state: st.session_state.flow_val = 346.4
Q_feed_total = st.sidebar.slider("Feed Inflow Capacity ($Q_0$, $m^3/h$)", 50.0, 600.0, float(st.session_state.flow_val), step=10.0)
Y_user_target = st.sidebar.slider("Recovery Configuration ($Y$, %)", 40.0, 96.0, 75.0, step=0.5)
T_operating = st.sidebar.slider("Operating Process Temperature (°C)", 5.0, 45.0, 25.0, step=1.0)

st.sidebar.subheader("🧬 Membrane Selection")
mem_choice = st.sidebar.selectbox("Select Model Matrix", options=list(MEMBRANE_MANUFACTURERS.keys()))
selected_mem = MEMBRANE_MANUFACTURERS[mem_choice]

st.sidebar.subheader("🧼 Maintenance Sweeps")
cip_frequency_months = st.sidebar.slider("CIP Flush Interventions", min_value=2, max_value=12, value=6)
has_erd = st.sidebar.toggle("Deploy Isobaric Energy Recovery (ERD)", value=True)

st.sidebar.subheader("🧪 Chemical Adjustments")
acid_choice = st.sidebar.selectbox("Acid Treatment Strategy", ["None", "Sulfuric Acid (H2SO4)"])
st.session_state.target_ph = st.sidebar.slider("Target Dosed pH", 5.0, 7.8, float(st.session_state.target_ph), step=0.1) if acid_choice != "None" else 7.8
st.session_state.as_dosage = st.sidebar.slider("Anti-Scalant Target ($mg/L$)", 0.0, 12.0, float(st.session_state.as_dosage), step=0.5)


# 3. INTERACTIVE CRISIS STRESS TESTER
st.subheader("🚨 Interactive Plant Failure Mode Simulator")
col_fail1, col_fail2, col_fail3 = st.columns(3)
with col_fail1: fail_valve_jam = st.toggle("💥 Feed Valve Jam (40% Flow Drop)", value=False)
with col_fail2: fail_sbs_pump = st.toggle("☣️ SBS Chemical Pump Failure", value=False)
with col_fail3: fail_algae_bloom = st.toggle("🌿 Red Tide Algae Bloom Event", value=False)

modified_feed_flow = Q_feed_total * 0.60 if fail_valve_jam else Q_feed_total
base_leak_growth_modifier = 4.5 if fail_sbs_pump else 1.0
base_fouling_multiplier = 5.0 if fail_algae_bloom else 1.0


# 4. WATER CHEMISTRY INTERFACE & EQUILIBRIUM DOSING ENGINE
st.write("---")
st.subheader("💧 Raw Water Influent Chemistry & Aqueous Equilibrium Calculations")
selected_template = st.selectbox("📂 Select Feed Source Template Preset", options=list(WATER_TEMPLATES.keys()), index=list(WATER_TEMPLATES.keys()).index(st.session_state.prev_template))

if selected_template != st.session_state.prev_template and WATER_TEMPLATES[selected_template] is not None:
    preset = WATER_TEMPLATES[selected_template]
    st.session_state.na_val, st.session_state.cl_val, st.session_state.ca_val, st.session_state.so4_val, st.session_state.alk_val = preset["na"], preset["cl"], preset["ca"], preset["so4"], preset["alk"]
    st.session_state.prev_template = selected_template
    st.rerun()

col_na, col_cl, col_ca, col_so4, col_alk = st.columns(5)
with col_na: na_input = st.number_input("Sodium ($Na^+$, $mg/L$)", 0.0, 100000.0, float(st.session_state.na_val), 10.0)
with col_cl: cl_input = st.number_input("Chloride ($Cl^-$, $mg/L$)", 0.0, 100000.0, float(st.session_state.cl_val), 10.0)
with col_ca: ca_input = st.number_input("Calcium ($Ca^{2+}$, $mg/L$)", 0.0, 50000.0, float(st.session_state.ca_val), 5.0)
with col_so4: so4_input = st.number_input("Sulfate ($SO_4^{2-}$, $mg/L$)", 0.0, 50000.0, float(st.session_state.so4_val), 10.0)
with col_alk: alk_input = st.number_input("Alkalinity ($HCO_3^-$, $mg/L$)", 0.0, 50000.0, float(st.session_state.alk_val), 5.0)

ph_delta = max(0.0, 7.8 - st.session_state.target_ph)
dosed_alk = alk_input * max(0.10, 1.0 - (ph_delta * 0.45))
dosed_so4 = so4_input + (ph_delta * 55.0) if acid_choice == "Sulfuric Acid (H2SO4)" else so4_input
treated_chemistry = {'Na': na_input, 'Cl': cl_input, 'Ca': ca_input, 'SO4': dosed_so4, 'HCO3': dosed_alk}

local_inlet_tds = sum(treated_chemistry.values())

# INTERACTIVE ION BALANCE CALCULATOR CORE
if st.button("📊 Run Ion Balance & Activity Coefficient Check", type="primary"):
    meq_na = na_input / 22.99
    meq_ca = (ca_input * 2) / 40.08
    meq_cl = cl_input / 35.45
    meq_so4 = (dosed_so4 * 2) / 96.06
    meq_hco3 = dosed_alk / 61.02
    
    sum_cations = meq_na + meq_ca
    sum_anions = meq_cl + meq_so4 + meq_hco3
    total_ions = sum_cations + sum_anions
    balance_error = ((sum_cations - sum_anions) / total_ions * 100.0) if total_ions > 0 else 0.0
    
    m_na = (na_input / 1000.0) / 22.99
    m_ca = (ca_input / 1000.0) / 40.08
    m_cl = (cl_input / 1000.0) / 35.45
    m_so4 = (dosed_so4 / 1000.0) / 96.06
    m_hco3 = (dosed_alk / 1000.0) / 61.02
    
    ionic_strength = 0.5 * (m_na*(1**2) + m_ca*(2**2) + m_cl*(1**2) + m_so4*(2**2) + m_hco3*(1**2))
    ionic_strength = max(1e-5, ionic_strength)
    
    A_param = 0.51 * np.sqrt(ionic_strength) / (1.0 + 1.0 * np.sqrt(ionic_strength))
    log_gamma_z1 = -A_param * (1**2) + 0.15 * ionic_strength
    log_gamma_z2 = -A_param * (2**2) + 0.15 * ionic_strength
    
    gamma_1 = 10**log_gamma_z1
    gamma_2 = 10**log_gamma_z2

    st.markdown("### 🧬 Aqueous Equilibrium Assessment Summary")
    bal_col1, bal_col2, bal_col3 = st.columns(3)
    with bal_col1:
        st.metric(label="Total Cation Load", value=f"{sum_cations:.3f} meq/L")
        st.metric(label="Total Anion Load", value=f"{sum_anions:.3f} meq/L")
        if abs(balance_error) <= 5.0: st.success(f"Electro-neutrality Balance: {balance_error:.2f}%")
        else: st.error(f"Electro-neutrality Balance: {balance_error:.2f}% (Deviation > 5%)")
    with bal_col2:
        st.metric(label="Calculated Ionic Strength ($I$)", value=f"{ionic_strength:.4f} M")
        st.metric(label="Total Blended Inlet TDS", value=f"{local_inlet_tds:,.1f} mg/L")
    with bal_col3:
        st.metric(label="Monovalent Activity Coeff ($\\gamma_1$)", value=f"{gamma_1:.3f}")
        st.metric(label="Divalent Activity Coeff ($\\gamma_2$)", value=f"{gamma_2:.3f}")


# --- 5. LIVE INSIDE-THE-VESSEL MEMBRANE PROFILER ---
st.write("---")
st.subheader("🔍 Live Inside-the-Vessel Membrane Profiler")
st.markdown("This section maps the localized hydraulics step-by-step from **Element 1 (Feed Inlet)** to **Element NV (Concentrate Exit)** across a single continuous housing array.")

element_steps = np.arange(1, custom_elements + 1)
vessel_flow_tracking = []
vessel_tds_tracking = []
vessel_cp_tracking = []
vessel_flux_tracking = []

current_feed_flow_m3 = modified_feed_flow / vessels_parallel
current_salt_mass = current_feed_flow_m3 * local_inlet_tds

for elem_idx in element_steps:
    local_recovery = (Y_user_target / 100.0) / custom_elements
    elem_permeate = current_feed_flow_m3 * local_recovery
    
    elem_feed_tds = current_salt_mass / current_feed_flow_m3
    elem_flux = (elem_permeate * 1000.0) / selected_mem["area"]
    elem_cp = np.exp(elem_flux / (3600.0 * 0.00022))
    
    vessel_flow_tracking.append(current_feed_flow_m3)
    vessel_tds_tracking.append(elem_feed_tds)
    vessel_cp_tracking.append(elem_cp)
    vessel_flux_tracking.append(elem_flux)
    
    current_feed_flow_m3 -= elem_permeate
    current_salt_mass -= (elem_permeate * elem_feed_tds * (1.0 - selected_mem["rejection"]))

fig_live, ax_live = plt.subplots(1, 3, figsize=(16, 3.8))
ax_live[0].bar(element_steps, vessel_tds_tracking, color='#e67e22', alpha=0.85, edgecolor='black')
ax_live[0].set_title("Bulk Stream Salt Concentration Build-Up", fontsize=9, fontweight='bold')
ax_live[0].set_xlabel("Pressure Vessel Element Position")
ax_live[0].set_ylabel("Local Stream TDS ($mg/L$)")
ax_live[0].grid(True, linestyle=":", alpha=0.6)

ax_live[1].plot(element_steps, vessel_cp_tracking, marker='o', color='#9b59b6', linewidth=2.5)
ax_live[1].set_title("Concentration Polarization (CP) Boundary Layer", fontsize=9, fontweight='bold')
ax_live[1].set_xlabel("Pressure Vessel Element Position")
ax_live[1].set_ylabel("CP Factor ($C_m / C_b$)")
ax_live[1].grid(True, linestyle=":", alpha=0.6)

ax_live[2].plot(element_steps, vessel_flux_tracking, marker='s', color='#1abc9c', linewidth=2.5)
ax_live[2].set_title("Local Flux Compression & Drop-off", fontsize=9, fontweight='bold')
ax_live[2].set_xlabel("Pressure Vessel Element Position")
ax_live[2].set_ylabel("Local Flux Performance (LMH)")
ax_live[2].grid(True, linestyle=":", alpha=0.6)
plt.tight_layout()
st.pyplot(fig_live)


# --- FEATURE 4: AUTOMATED PID CONTROL LOOP FOR VFD PUMP VECTORS ---
st.write("---")
st.subheader("⏱️ Real-Time Automated SCADA PLC / PID Variable Frequency Drive Controller")
st.markdown("Simulates the transient digital feedback control loop adjusting high-pressure pump motor speed to counteract hydraulic upsets and maintain constant permeate flow rate setpoint.")

target_permeate_q = (modified_feed_flow * (Y_user_target / 100.0))
pid_kp, pid_ki, pid_kd = 0.45, 0.22, 0.08
sim_ticks = np.arange(0, 31)

pid_pressure_history = []
pid_flow_history = []
current_vfd_pressure = 12.0  # Initial startup guess boundary
integrated_error = 0.0
last_error = 0.0

for tick in sim_ticks:
    # Sudden pressure drop/spike profile based on active failure modes
    upset_modifier = 4.5 if (fail_valve_jam and tick > 10) else 0.0
    fouling_backpressure = (base_fouling_multiplier * 0.35) if tick > 15 else 0.0
    
    # Calculate current system response
    simulated_permeate_flow = max(0.0, (current_vfd_pressure - 7.5 - upset_modifier - fouling_backpressure) * (target_permeate_q / 10.0))
    
    # Run loop calculation
    flow_error = target_permeate_q - simulated_permeate_flow
    integrated_error += flow_error * 0.1
    derivative_error = (flow_error - last_error) / 0.1
    
    vfd_adjustment = (pid_kp * flow_error) + (pid_ki * integrated_error) + (pid_kd * derivative_error)
    current_vfd_pressure += vfd_adjustment
    current_vfd_pressure = max(5.0, min(65.0, current_vfd_pressure))
    last_error = flow_error
    
    pid_pressure_history.append(current_vfd_pressure)
    pid_flow_history.append(simulated_permeate_flow)

fig_pid, ax_pid = plt.subplots(1, 2, figsize=(16, 3.8))
ax_pid[0].plot(sim_ticks, pid_flow_history, color='#2980b9', linewidth=2.5, label='Actual Flow Rate')
ax_pid[0].axhline(target_permeate_q, color='red', linestyle='--', alpha=0.7, label='Target Setpoint')
ax_pid[0].set_title("Permeate Stream Velocity Stabilization Curve", fontsize=9, fontweight='bold')
ax_pid[0].set_xlabel("Control Loop Iterations (Ticks)")
ax_pid[0].set_ylabel("Permeate Production ($m^3/h$)")
ax_pid[0].legend()
ax_pid[0].grid(True, linestyle=":")

ax_pid[1].plot(sim_ticks, pid_pressure_history, color='#e74c3c', linewidth=2.5, label='VFD Output Head')
ax_pid[1].set_title("VFD Motor Frequency & Discharge Pressure Tuning Modulations", fontsize=9, fontweight='bold')
ax_pid[1].set_xlabel("Control Loop Iterations (Ticks)")
ax_pid[1].set_ylabel("Pump Discharge Pressure (bar)")
ax_pid[1].grid(True, linestyle=":")
plt.tight_layout()
st.pyplot(fig_pid)


# --- FEATURE 5: ELEMENT-BY-ELEMENT AUTOPSY & LIFECYCLE AGEING MATRIX ---
st.write("---")
st.subheader("🩺 Membrane Structural Core Autopsy & Remaining Life Asset Matrix")
st.markdown("Tracks and diagnoses localized structural degradation patterns at Year 4 (Month 48) inside the high-pressure housing vessel array.")

autopsy_dataset = []
for idx in element_steps:
    local_compaction_rate = selected_mem['compaction'] * np.log1p(48 / 12.0) * (1.1 if idx <= 2 else 0.9) * 100.0
    local_scaling_crust = (vessel_tds_tracking[idx-1] / local_inlet_tds) * (1.4 if idx >= 4 else 0.4) * base_fouling_multiplier * 8.5
    chemical_oxidation_wear = 0.55 * base_leak_growth_modifier * 12.0
    
    cumulative_degradation = local_compaction_rate + local_scaling_crust + chemical_oxidation_wear
    remaining_lifetime_pct = max(0.0, 100.0 - cumulative_degradation)
    
    if remaining_lifetime_pct > 75.0: status = "🟢 Optimal / Active"
    elif remaining_lifetime_pct > 45.0: status = "🟡 Fouled / Monitor"
    else: status = "🔴 Critical Scale Crust / Extract Element"
    
    autopsy_dataset.append({
        "Element Position": f"Position {idx}",
        "Local Flux Compression (LMH)": f"{vessel_flux_tracking[idx-1]:.2f} LMH",
        "Compaction Rate": f"{local_compaction_rate:.2f}%",
        "Crystalline Mineral Scale": f"{local_scaling_crust:.1f} mg/cm²",
        "Membrane Health Rating": f"{remaining_lifetime_pct:.1f}%",
        "Action Status Mapping": status
    })

st.table(pd.DataFrame(autopsy_dataset))


# --- 6. MECHANICAL PROCESS SIZING CALCULATOR ENGINE ---
total_installed_elements = vessels_parallel * custom_elements
total_active_surface_area_m2 = total_installed_elements * selected_mem["area"]

actual_q_permeate = modified_feed_flow * (Y_user_target / 100.0)
realized_flux_lmh = (actual_q_permeate * 1000.0) / total_active_surface_area_m2

spacer_thickness_meters = (selected_mem["spacer_mil"] * 2.54e-5)
vessel_inner_diameter_meters = 0.20  
cross_sectional_flow_area = (np.pi * (vessel_inner_diameter_meters / 2)**2) * 0.55  
feed_flow_per_vessel_m3_s = (modified_feed_flow / vessels_parallel) / 3600.0
inlet_crossflow_velocity_m_s = feed_flow_per_vessel_m3_s / cross_sectional_flow_area
fluid_density_kg_m3 = 1000.0 + (0.75 * (local_inlet_tds / 1000.0))


# --- 7. HIGH-FIDELITY CHEMICAL TRANSLATION & TRANSPORT PIPELINE ---
def calculate_osmotic_pressure(chem_dict, concentration_factor, temp_c):
    mol_weights = {'Na': 22.99, 'Cl': 35.45, 'Ca': 40.08, 'SO4': 96.06, 'HCO3': 61.02}
    total_molarity = 0.0
    for ion, mg_l in chem_dict.items():
        molarity = (mg_l * concentration_factor) / (mol_weights[ion] * 1000.0)
        total_molarity += molarity
    return total_molarity * 0.083145 * (temp_c + 273.15)

def calculate_lsi(tds, temp_c, calcium, alkalinity, current_ph):
    log10_tds = np.log10(max(10.0, tds))
    A = (log10_tds - 1.0) / 10.0
    B = -13.12 * np.log10(temp_c + 273.15) + 34.55
    C = np.log10(max(1.0, calcium * 2.497)) - 0.40
    D = np.log10(max(1.0, alkalinity * 0.82))
    return current_ph - ((9.3 + A + B) - (C + D))

def calculate_davies_caso4_saturation(chem_dict, conc_factor, temp_c):
    mw = {'Ca': 40.08, 'SO4': 96.06, 'Na': 22.99, 'Cl': 35.45, 'HCO3': 61.02}
    c_ca = (chem_dict['Ca'] * conc_factor) / 1000.0 / mw['Ca']
    c_so4 = (chem_dict['SO4'] * conc_factor) / 1000.0 / mw['SO4']
    c_na = (chem_dict['Na'] * conc_factor) / 1000.0 / mw['Na']
    c_cl = (chem_dict['Cl'] * conc_factor) / 1000.0 / mw['Cl']
    c_hco3 = (chem_dict['HCO3'] * conc_factor) / 1000.0 / mw['HCO3']
    
    I = 0.5 * ((c_na * 1**2) + (c_cl * 1**2) + (c_hco3 * 1**2) + (c_ca * 2**2) + (c_so4 * 2**2))
    I = max(1e-5, I)
    
    A = 0.51 * np.sqrt(I) / (1.0 + 1.0 * np.sqrt(I))
    log_gamma_divalent = -A * (2**2) + 0.15 * I
    gamma_2 = 10**log_gamma_divalent
    
    iap = (c_ca * gamma_2) * (c_so4 * gamma_2)
    tk = temp_c + 273.15
    log_ksp = -68.2401 + (3241.25 / tk) + (24.3219 * np.log(tk)) - (0.05586 * tk)
    ksp_gypsum = 10**log_ksp
    return (iap / ksp_gypsum) * 100.0

full_tech_registry = {
    'Conventional': {'stages': 2, 'elements': custom_elements, 'Aw': 1.25, 'color': '#95a5a6', 'scale_factor': 0.180},
    'CCRO': {'stages': 1, 'elements': custom_elements, 'Aw': 1.85, 'color': '#3498db', 'scale_factor': 0.120},
    'PFRO': {'stages': 2, 'elements': custom_elements, 'Aw': 2.45, 'color': '#2ecc71', 'scale_factor': 0.090}
}

viscosity_25 = 0.890  
viscosity_T = 1.002 * np.exp(1.1709 * (20 - T_operating) / (T_operating + 96))
TCF = viscosity_25 / viscosity_T

months_axis = np.arange(0, 49)
technology_performance_matrix = {}
lifecycle_curves_by_scheme = {}
scada_log_data_stream = []

for tech, cfg in full_tech_registry.items():
    pressures, secs, perm_tds = [], [], []
    fluxes, lsis, sats, bhps = [], [], [], []
    accumulated_fouling_resistance = 0.0
    
    for m in months_axis:
        is_cip_month = False
        if m > 0 and m % cip_frequency_months == 0:
            accumulated_fouling_resistance *= (1.0 - 0.95)
            is_cip_month = True
            
        yr_equivalent = m / 12.0
        Aw_actual = cfg['Aw'] * selected_mem['aw_mod'] * TCF * (1.0 - selected_mem['compaction'] * np.log1p(yr_equivalent))
        current_rejection = min(0.9995, selected_mem['rejection'] / (1.0 + (selected_mem['leak_grow'] * base_leak_growth_modifier) * yr_equivalent))
        
        rec_frac = Y_user_target / 100.0
        conc_factor_avg = 1.0 if tech == 'CCRO' else (1.0 + (1.0 / (1.0 - rec_frac))) / 2.0
        conc_factor_tail = 1.0 / max(0.01, 1.0 - rec_frac)
        
        concentration_polarization_factor = np.exp(realized_flux_lmh / (3600 * 0.00025))
        osmotic_feed = calculate_osmotic_pressure(treated_chemistry, 1.0, T_operating)
        osmotic_avg = calculate_osmotic_pressure(treated_chemistry, conc_factor_avg, T_operating) * concentration_polarization_factor
        delta_osmotic = osmotic_avg - (osmotic_feed * (1.0 - current_rejection))
        
        tail_ca = treated_chemistry['Ca'] * conc_factor_tail
        tail_tds = local_inlet_tds * conc_factor_tail
        
        caso4_sat = calculate_davies_caso4_saturation(treated_chemistry, conc_factor_tail, T_operating)
        tail_lsi = calculate_lsi(tail_tds, T_operating, tail_ca, treated_chemistry['HCO3'] * conc_factor_tail, st.session_state.target_ph)
        
        supersat = max(0.0, tail_lsi - 1.0) + (max(0.0, caso4_sat - 120.0) * 0.025)
        accumulated_fouling_resistance += (supersat * cfg['scale_factor'] * base_fouling_multiplier) * (0.05 if tech == 'CCRO' else 0.12)
        
        current_realized_flux = realized_flux_lmh / (1.0 + (accumulated_fouling_resistance * 0.15))
        avg_ndp = (realized_flux_lmh / (1.0 + accumulated_fouling_resistance)) / Aw_actual
        spacer_friction_drop = (cfg['stages'] * cfg['elements']) * 0.35
        
        pump_p = max(5.0, avg_ndp + delta_osmotic + (spacer_friction_drop / 2.0))
        calculated_bhp = ((modified_feed_flow * (pump_p * 100000)) / (3600 * 0.84)) / 1000.0
        
        pump_efficiency, motor_efficiency = 0.84, 0.95
        total_wire_to_water_eff = pump_efficiency * motor_efficiency
        
        if has_erd:
            brine_flow = modified_feed_flow * (1.0 - rec_frac)
            recovered_power_kw = ((brine_flow * (pump_p - spacer_friction_drop) * 0.92) / 36.0)
            raw_pump_power_kw = ((modified_feed_flow * pump_p) / 36.0) / total_wire_to_water_eff
            net_kw = max(2.0, raw_pump_power_kw - recovered_power_kw)
        else:
            net_kw = max(2.0, (((modified_feed_flow * pump_p) / 36.0) / total_wire_to_water_eff))
            
        pressures.append(pump_p)
        secs.append(net_kw / (modified_feed_flow * rec_frac))
        perm_tds.append(local_inlet_tds * (1.0 - current_rejection))
        fluxes.append(current_realized_flux)
        lsis.append(tail_lsi)
        sats.append(caso4_sat)
        bhps.append(calculated_bhp)
        
        if (view_scope == "All Comparison Matrices Simultaneously" and tech == 'Conventional') or \
           (view_scope == "Conventional Only" and tech == 'Conventional') or \
           (view_scope == "CCRO Only" and tech == 'CCRO') or \
           (view_scope == "PFRO Only" and tech == 'PFRO'):
            scada_log_data_stream.append({
                'month': m, 'p': pump_p, 'tds': local_inlet_tds * (1.0 - current_rejection),
                'lsi': tail_lsi, 'sat': caso4_sat, 'cip': is_cip_month, 'tech': tech
            })
            
    lifecycle_curves_by_scheme[tech] = {
        'p': pressures, 'sec': secs, 'tds': perm_tds, 
        'flux': fluxes, 'lsi': lsis, 'sat': sats, 'bhp': bhps
    }
    technology_performance_matrix[tech] = {
        'p_last': pressures[-1], 'sec_last': secs[-1], 'tds_last': perm_tds[-1]
    }

display_tech = 'Conventional'
if view_scope == "CCRO Only": display_tech = 'CCRO'
if view_scope == "PFRO Only": display_tech = 'PFRO'

active_p = technology_performance_matrix[display_tech]['p_last']
active_sec = technology_performance_matrix[display_tech]['sec_last']
active_tds = technology_performance_matrix[display_tech]['tds_last']


# --- 8. AUTOMATED DIAGNOSTICS & MECHANICAL SAFETIES ---
st.write("---")
st.subheader(f"🛡️ Digital Twin Sizing & Process Diagnostics ({display_tech} Active Monitor)")

has_errors = False
if realized_flux_lmh > 25.0:
    st.error(f"🚨 **FLUX EXCURSION LIMIT:** Sized array yields operating flux of **{realized_flux_lmh:.1f} LMH**. High risk of rapid cake fouling. Increase parallel vessel count (PV).")
    has_errors = True
elif realized_flux_lmh < 11.0:
    st.warning(f"⚠️ **OVER-SIZED FOOTPRINT DETECTED:** Operating flux fell to **{realized_flux_lmh:.1f} LMH**. Capital expenditure underutilized.")

if inlet_crossflow_velocity_m_s < 0.08:
    st.warning(f"⚠️ **LOW CONCENTRATE CROSS-FLOW:** Linear velocity fell to **{inlet_crossflow_velocity_m_s:.3f} m/s**. Concentration polarization layer will destabilize.")
elif inlet_crossflow_velocity_m_s > 0.45:
    st.error(f"🚨 **EROSION VELOCITY BREACH:** Input crossflow velocity hit **{inlet_crossflow_velocity_m_s:.3f} m/s**. Physical spacer destruction imminent.")

if active_p > 68.0:
    st.error(f"🚨 **CRITICAL OVERPRESSURE:** Required net feed pressure crested to **{active_p:.1f} bar**, exceeding physical element crush boundaries.")
    has_errors = True

if not has_errors:
    st.success(f"✅ **MECHANICAL SIZING STABLE ({display_tech}):** Fluid velocities and flux boundaries configured within safe parameters.")


# --- 9. PLANT SIZING AND PROCESS STREAM METRICS ---
st.write("---")
st.subheader(f"📐 Plant Structural Sizing and Process Stream Metrics — {display_tech} Active")
sz_col1, sz_col2, sz_col3, sz_col4 = st.columns(4)

with sz_col1:
    st.metric(label="Total Active Surface Area", value=f"{total_active_surface_area_m2:,.1f} m²", delta=f"{total_installed_elements} Elements Sized")
with sz_col2:
    st.metric(label="Operating Saturated Flux", value=f"{realized_flux_lmh:.1f} LMH", delta=f"Target: {design_flux_lmh} LMH", delta_color="off")
with sz_col3:
    st.metric(label="Inlet Crossflow Linear Velocity", value=f"{inlet_crossflow_velocity_m_s:.3f} m/s", help="Minimum target threshold: > 0.08 m/s")
with sz_col4:
    st.metric(label="High Pressure Pump Shaft Power", value=f"{((modified_feed_flow * (active_p * 100000)) / (3600 * 0.84)) / 1000:.1f} kW_m")


# --- 10. SCADA CONSOLE LOGGER ---
st.write("---")
st.subheader("📟 SCADA Distributed Control System (DCS) Live Sizing Operational Shift Log")
log_box_content = ""
current_timestamp = datetime.now().strftime("%H:%M:%S")

for frame in scada_log_data_stream:
    m = frame['month']
    t_name = frame['tech']
    time_prefix = f"[{current_timestamp} | Month {m:02d} | {t_name}]"
    if m == 0: log_box_content += f"🟢 {time_prefix} INITIALIZATION: Geometric constraints mapped. Sized Area = {total_active_surface_area_m2:.1f} m².\n"
    if m == 1:
        if realized_flux_lmh > 24: log_box_content += f"⚠️ {time_prefix} HIGH FLUX WARNING: Membrane elements entering severe concentration polarization regimes.\n"
        if inlet_crossflow_velocity_m_s < 0.08: log_box_content += f"🔴 {time_prefix} VELOCITY LOW: Flow bypass detected. Channel fouling acceleration forecast.\n"
    if frame['cip']: log_box_content += f"🧼 {time_prefix} MAINTENANCE: Core element Clean-In-Place sweep restored nominal element flux profiles.\n"

st.text_area("Terminal Console Log Summary", value=log_box_content, height=120, label_visibility="collapsed")


# --- 11. PERFORMANCE GRAPHICAL ENGINE ---
st.write("---")
st.subheader(f"⏳ Long-Term 48-Month Multi-Variable Analytical Graphs ({view_scope})")

if view_scope == "All Comparison Matrices Simultaneously":
    fig1, ax1 = plt.subplots(2, 3, figsize=(16, 8.5))
    
    ax1[0, 0].plot(months_axis, lifecycle_curves_by_scheme['Conventional']['p'], label='Conventional', color='#95a5a6', linewidth=2)
    ax1[0, 0].plot(months_axis, lifecycle_curves_by_scheme['CCRO']['p'], label='CCRO Loop', color='#3498db', linewidth=2)
    ax1[0, 0].plot(months_axis, lifecycle_curves_by_scheme['PFRO']['p'], label='PFRO Optimize', color='#2ecc71', linewidth=2)
    ax1[0, 0].set_title("Required System Operational Pressure (bar)", fontsize=10, fontweight='bold')
    ax1[0, 0].grid(True, linestyle=":")
    ax1[0, 0].legend()

    ax1[0, 1].plot(months_axis, lifecycle_curves_by_scheme['Conventional']['sec'], label='Conventional', color='#95a5a6', linewidth=2)
    ax1[0, 1].plot(months_axis, lifecycle_curves_by_scheme['CCRO']['sec'], label='CCRO Loop', color='#3498db', linewidth=2)
    ax1[0, 1].plot(months_axis, lifecycle_curves_by_scheme['PFRO']['sec'], label='PFRO Optimize', color='#2ecc71', linewidth=2)
    ax1[0, 1].set_title("Dynamic Specific Energy Cost ($kWh/m^3$)", fontsize=10, fontweight='bold')
    ax1[0, 1].grid(True, linestyle=":")

    ax1[0, 2].plot(months_axis, lifecycle_curves_by_scheme['Conventional']['tds'], label='Conventional', color='#95a5a6', linewidth=2)
    ax1[0, 2].plot(months_axis, lifecycle_curves_by_scheme['CCRO']['tds'], label='CCRO Loop', color='#3498db', linewidth=2)
    ax1[0, 2].plot(months_axis, lifecycle_curves_by_scheme['PFRO']['tds'], label='PFRO Optimize', color='#2ecc71', linewidth=2)
    ax1[0, 2].set_title("Solute Leakage Permeate TDS ($mg/L$)", fontsize=10, fontweight='bold')
    ax1[0, 2].grid(True, linestyle=":")

    ax1[1, 0].plot(months_axis, lifecycle_curves_by_scheme['Conventional']['flux'], label='Conventional', color='#95a5a6', linestyle='--')
    ax1[1, 0].plot(months_axis, lifecycle_curves_by_scheme['CCRO']['flux'], label='CCRO Loop', color='#3498db', linewidth=2)
    ax1[1, 0].plot(months_axis, lifecycle_curves_by_scheme['PFRO']['flux'], label='PFRO Optimize', color='#2ecc71', linewidth=2)
    ax1[1, 0].set_title("Membrane Transport Flux Decay Profile (LMH)", fontsize=10, fontweight='bold')
    ax1[1, 0].set_xlabel("Operating Months")
    ax1[1, 0].grid(True, linestyle=":")

    ax1[1, 1].plot(months_axis, lifecycle_curves_by_scheme['Conventional']['sat'], label='Conv CaSO4%', color='#95a5a6', alpha=0.5)
    ax1[1, 1].plot(months_axis, lifecycle_curves_by_scheme['CCRO']['sat'], label='CCRO CaSO4%', color='#3498db', linewidth=2)
    ax1[1, 1].plot(months_axis, lifecycle_curves_by_scheme['PFRO']['sat'], label='PFRO CaSO4%', color='#2ecc71', linewidth=2)
    ax1[1, 1].set_title("Tail-Element Scaling Concentration Saturation (%)", fontsize=10, fontweight='bold')
    ax1[1, 1].set_xlabel("Operating Months")
    ax1[1, 1].grid(True, linestyle=":")
    ax1[1, 1].legend(fontsize=8)

    ax1[1, 2].plot(months_axis, lifecycle_curves_by_scheme['Conventional']['bhp'], label='Conventional', color='#95a5a6')
    ax1[1, 2].plot(months_axis, lifecycle_curves_by_scheme['CCRO']['bhp'], label='CCRO Loop', color='#3498db', linewidth=2)
    ax1[1, 2].plot(months_axis, lifecycle_curves_by_scheme['PFRO']['bhp'], label='PFRO Optimize', color='#2ecc71', linewidth=2)
    ax1[1, 2].set_title("High-Pressure Pump Driver Power (BHP, kW)", fontsize=10, fontweight='bold')
    ax1[1, 2].set_xlabel("Operating Months")
    ax1[1, 2].grid(True, linestyle=":")
    plt.tight_layout()
    st.pyplot(fig1)

else:
    fig1, ax1 = plt.subplots(1, 3, figsize=(16, 4.2))
    tech_color = full_tech_registry[display_tech]['color']
    curves = lifecycle_curves_by_scheme[display_tech]
    
    ax1[0].plot(months_axis, curves['p'], color=tech_color, linewidth=2.5, label='Feed Press.')
    ax1[0].set_ylabel('Required Feed Pressure (bar)', color=tech_color)
    ax1[0].set_xlabel("Operating Months")
    ax2 = ax1[0].twinx()
    ax2.plot(months_axis, curves['bhp'], color='#e74c3c', linestyle=':', linewidth=2, label='Shaft BHP')
    ax2.set_ylabel('Gross Pump Shaft Power (kW)', color='#e74c3c')
    ax1[0].set_title(f"{display_tech}: Hydraulic Vector Sizing Symmetrical Dynamics", fontsize=10, fontweight='bold')
    ax1[0].grid(True, linestyle=":")

    ax1[1].plot(months_axis, curves['sec'], color=tech_color, linewidth=2.5)
    ax1[1].set_ylabel('Specific Energy Cost ($kWh/m^3$)', color=tech_color)
    ax1[1].set_xlabel("Operating Months")
    ax3 = ax1[1].twinx()
    ax3.plot(months_axis, curves['flux'], color='#f39c12', linestyle='--', linewidth=1.8)
    ax3.set_ylabel('Active Realized Flux (LMH)', color='#f39c12')
    ax1[1].set_title(f"{display_tech}: Energy Index vs Boundary Flux Droop", fontsize=10, fontweight='bold')
    ax1[1].grid(True, linestyle=":")

    ax1[2].plot(months_axis, curves['lsi'], color=tech_color, linewidth=2.5)
    ax1[2].set_ylabel('Tail Element LSI Index', color=tech_color)
    ax1[2].set_xlabel("Operating Months")
    ax4 = ax1[2].twinx()
    ax4.plot(months_axis, curves['sat'], color='#9b59b6', linestyle='-.', linewidth=1.8)
    ax4.set_ylabel('$CaSO_4$ Saturation Balance (%)', color='#9b59b6')
    ax1[2].set_title(f"{display_tech}: Mass Transport Solute Scaling Intersections", fontsize=10, fontweight='bold')
    ax1[2].grid(True, linestyle=":")
    plt.tight_layout()
    st.pyplot(fig1)
