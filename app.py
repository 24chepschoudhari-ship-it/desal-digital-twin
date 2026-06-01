import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# 1. PAGE SETUP & STYLING
st.set_page_config(page_title="Desalination Digital Twin", layout="wide")

st.title("🖥️ Industrial Desalination Digital Twin")
st.markdown("### Enterprise Operational Lifecycle, Automated Design Sizing & Engineering Suite")
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
    },
    "Standard Estuary Brackish Matrix": {
        "na": 1200.0, "cl": 1950.0, "ca": 80.0, "so4": 320.0, "alk": 180.0
    }
}

# Branded Membrane Specification Database
MEMBRANE_MANUFACTURERS = {
    "DuPont™ FilmTec™ BW30-400 (Standard Brackish)": {
        "aw_mod": 1.00, "rejection": 0.9970, "compaction": 0.065, "leak_grow": 0.15, "cost": 480.0, "area": 37.2,
        "desc": "Industry standard for high rejection brackish water treatment. 400 sq ft active area."
    },
    "DuPont™ FilmTec™ Eco PRO-400 (Low Energy)": {
        "aw_mod": 1.35, "rejection": 0.9940, "compaction": 0.085, "leak_grow": 0.18, "cost": 540.0, "area": 37.2,
        "desc": "High flow, low-energy brackish element engineered to slash pump power consumption."
    },
    "DuPont™ FilmTec™ SW30HRLE-400 (Seawater)": {
        "aw_mod": 0.65, "rejection": 0.9982, "compaction": 0.035, "leak_grow": 0.08, "cost": 750.0, "area": 37.2,
        "desc": "Premium seawater element offering high rejection at lowered feed pressures."
    },
    "Veolia (Suez) AG8040F (High Rejection Brackish)": {
        "aw_mod": 1.05, "rejection": 0.9965, "compaction": 0.070, "leak_grow": 0.14, "cost": 460.0, "area": 37.2,
        "desc": "Robust structural layout tailored for high-fouling industrial water loops."
    }
}

# Initialize persistent session state tracking for chemistry parameters
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

st.sidebar.subheader("📐 Process Configuration")
tech_view_mode = st.sidebar.selectbox("Select Display Mode", ["Compare All Schemes", "Single Scheme Focus"])
target_tech = st.sidebar.selectbox("Select Target Technology", ["PFRO", "CCRO", "FRRO", "Conventional"]) if tech_view_mode == "Single Scheme Focus" else None

# --- UPGRADED DESIGN SIZING CONSTRAINT INPUTS ---
st.sidebar.subheader("📐 Core Plant Sizing Flux Targets")
design_flux_lmh = st.sidebar.slider("Target Average Flux (LMH, L/m²/h)", min_value=10.0, max_value=30.0, value=18.0, help="Higher flux creates smaller footprint but accelerates scaling fouling taxes.")
custom_elements = st.sidebar.slider("Elements Loaded / Pressure Vessel", min_value=4, max_value=8, value=6, step=1)

st.sidebar.subheader("🌊 Hydraulic & Thermodynamic Bounds")
# Flow Sync
if "flow_val" not in st.session_state: st.session_state.flow_val = 346.4
col_f1, col_f2 = st.sidebar.columns([2, 1])
with col_f1: f_slide = st.slider("Feed Flow Rate (Q₀, m³/h)", 50.0, 600.0, float(st.session_state.flow_val), step=10.0, key="fs")
with col_f2: f_num = st.number_input("Value", 50.0, 600.0, float(st.session_state.flow_val), step=0.1, key="fn", label_visibility="collapsed")
st.session_state.flow_val = f_num if f_num != st.session_state.flow_val else f_slide

# Recovery Sync
if "rec_val" not in st.session_state: st.session_state.rec_val = 75.0
col_r1, col_r2 = st.sidebar.columns([2, 1])
with col_r1: r_slide = st.slider("Target Recovery Goal (Y, %)", 40.0, 96.0, float(st.session_state.rec_val), step=0.5, key="rs")
with col_r2: r_num = st.number_input("Value", 40.0, 96.0, float(st.session_state.rec_val), step=0.1, key="rn", label_visibility="collapsed")
st.session_state.rec_val = r_num if r_num != st.session_state.rec_val else r_slide

# Temp Sync
if "temp_val" not in st.session_state: st.session_state.temp_val = 25.0
col_t1, col_t2 = st.sidebar.columns([2, 1])
with col_t1: t_slide = st.slider("Operating Temp (°C)", 5.0, 45.0, float(st.session_state.temp_val), step=1.0, key="ts")
with col_t2: t_num = st.number_input("Value", 5.0, 45.0, float(st.session_state.temp_val), step=0.5, key="tn", label_visibility="collapsed")
st.session_state.temp_val = t_num if t_num != st.session_state.temp_val else t_slide

Q_feed_total, Y_user_target, T_operating = st.session_state.flow_val, st.session_state.rec_val, st.session_state.temp_val

st.sidebar.subheader("🧬 Commercial Membrane Element Selector")
mem_choice = st.sidebar.selectbox("Select Manufacturer Model", options=list(MEMBRANE_MANUFACTURERS.keys()))
selected_mem = MEMBRANE_MANUFACTURERS[mem_choice]

st.sidebar.subheader("🧼 Clean-In-Place (CIP) Schedules")
cip_frequency_months = st.sidebar.slider("CIP Flush Interventions", min_value=2, max_value=12, value=6)
cip_efficiency = st.sidebar.slider("Chemical Wash Recovery Efficiency (%)", 80.0, 100.0, 95.0, step=0.5) / 100.0

st.sidebar.subheader("🎛 ?? Utility Configurations")
has_erd = st.sidebar.toggle("Deploy Isobaric Energy Recovery (ERD)", value=True)
elec_rate = st.sidebar.number_input("Electricity Tariff ($/kWh)", 0.01, 0.50, 0.12, 0.01)
as_chem_rate = st.sidebar.number_input("Anti-Scalant Bulk Cost ($/kg)", 1.0, 15.0, 4.50, 0.50)

acid_choice = st.sidebar.selectbox("Acid Treatment Strategy", ["None", "Sulfuric Acid (H2SO4)", "Hydrochloric Acid (HCl)"])
st.session_state.target_ph = st.sidebar.slider("Target Dosed pH", 5.0, 7.8, float(st.session_state.target_ph), step=0.1) if acid_choice != "None" else 7.8
st.session_state.as_dosage = st.sidebar.slider("Anti-Scalant Target (mg/L)", 0.0, 12.0, float(st.session_state.as_dosage), step=0.5)

# --- INTERCEPTOR: AUTO-MITIGATION TRIGGERS ---
if st.session_state.get("apply_lsi_fix"):
    st.session_state.target_ph, st.session_state.apply_lsi_fix = 6.2, False
if st.session_state.get("apply_gypsum_fix"):
    st.session_state.as_dosage, st.session_state.apply_gypsum_fix = 8.5, False


# 3. WATER CHEMISTRY INTERFACE WITH TEMPLATE SELECTOR
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
dosed_cl = cl_input + (ph_delta * 40.0) if acid_choice == "Hydrochloric Acid (HCl)" else cl_input
treated_chemistry = {'Na': st.session_state.na_val, 'Cl': dosed_cl, 'Ca': st.session_state.ca_val, 'SO4': dosed_so4, 'HCO3': dosed_alk}

# Calculations for Chemistry Neutrals
cations_meq = (st.session_state.na_val * 1 / 22.99) + (st.session_state.ca_val * 2 / 40.08)
anions_meq = (dosed_cl * 1 / 35.45) + (dosed_so4 * 2 / 96.06) + (dosed_alk * 1 / 61.02)
total_charge = cations_meq + anions_meq
ion_balance_error = ((cations_meq - anions_meq) / total_charge) * 100 if total_charge > 0 else 0.0

col_bal_badge, col_bal_metrics, col_bal_btn = st.columns([1.2, 3.8, 1.5])
with col_bal_badge:
    if abs(ion_balance_error) <= 5.0: st.success("✅ Ion Balance OK")
    else: st.error("❌ Charge Imbalance")
with col_bal_metrics:
    st.markdown(f"**Cations:** `{cations_meq:.2f} meq/L` | **Anions:** `{anions_meq:.2f} meq/L` | **Error:** `{ion_balance_error:.2f}%`")
with col_bal_btn:
    if abs(ion_balance_error) > 0.01 and st.button("⚖️ Auto-Balance Ions", type="primary"):
        delta_meq = cations_meq - anions_meq
        if delta_meq > 0: st.session_state.cl_val += (delta_meq * 35.45)
        else: st.session_state.na_val += (abs(delta_meq) * 22.99)
        st.rerun()


# --- 4. ENGINE CORE WITH INTEGRATED GEOMETRY & SIZING SYNTHESIS ---
q_permeate_calc = Q_feed_total * (Y_user_target / 100.0)
required_surface_area_m2 = (q_permeate_calc * 1000.0) / design_flux_lmh
elements_per_vessel = custom_elements
single_element_area = selected_mem["area"]

# Synthesizing physical equipment geometry count
calculated_total_elements = int(np.ceil(required_surface_area_m2 / single_element_area))
vessel_count = int(np.ceil(calculated_total_elements / elements_per_vessel))

# Dynamic Staging Array Sizing Rules (Balances spatial hydrodynamics across array)
if vessel_count >= 3:
    stage1_vessels = int(np.ceil(vessel_count * 0.67))
    stage2_vessels = max(1, vessel_count - stage1_vessels)
    custom_stages = 2
else:
    stage1_vessels = vessel_count
    stage2_vessels = 0
    custom_stages = 1

def calculate_lsi(tds, temp_c, calcium, alkalinity, current_ph):
    log10_tds = np.log10(max(10.0, tds))
    A, B = (log10_tds - 1.0) / 10.0, -13.12 * np.log10(temp_c + 273.15) + 34.55
    C, D = np.log10(max(1.0, calcium * 2.497)) - 0.40, np.log10(max(1.0, alkalinity * 0.82))
    return current_ph - ((9.3 + A + B) - (C + D))

full_tech_registry = {
    'PFRO': {'stages': custom_stages, 'elements': custom_elements, 'Aw': 2.45, 'color': '#2ecc71', 'scale_factor': 0.090, 'target_flux': design_flux_lmh + 4.5},
    'FRRO': {'stages': custom_stages, 'elements': custom_elements, 'Aw': 1.45, 'color': '#e67e22', 'scale_factor': 0.050, 'target_flux': design_flux_lmh - 1.0},
    'CCRO': {'stages': custom_stages, 'elements': custom_elements, 'Aw': 1.85, 'color': '#3498db', 'scale_factor': 0.120, 'target_flux': design_flux_lmh + 2.0},
    'Conventional': {'stages': custom_stages, 'elements': custom_elements, 'Aw': 1.25, 'color': '#95a5a6', 'scale_factor': 0.180, 'target_flux': design_flux_lmh}
}

tech_registry = {target_tech: full_tech_registry[target_tech]} if tech_view_mode == "Single Scheme Focus" and target_tech else full_tech_registry
primary_tech = list(tech_registry.keys())[0]

t_kelvin_base, t_kelvin_actual = 298.15, 273.15 + T_operating
TCF = np.exp(2640.0 * (1.0 / t_kelvin_base - 1.0 / t_kelvin_actual))
vfd_eff, local_inlet_tds = (0.98 if abs(T_operating - 25.0) < 5 else 0.95), sum(treated_chemistry.values())

months_axis = np.arange(0, 49)
lifecycle_results, spatial_results = {}, {}
max_brine_lsi, max_caso4_saturation = -99.0, 0.0

for tech, cfg in tech_registry.items():
    pressures, secs, perm_tds = [], [], []
    res_factor = 0.7 if tech in ['PFRO', 'CCRO'] else 1.2
    gypsum_ceiling = 100.0 if st.session_state.as_dosage == 0 else min(600.0, 100.0 + (25.5 * (st.session_state.as_dosage ** 1.15) * np.exp(-0.15 * res_factor)))
    
    accumulated_fouling_resistance = 0.0
    
    for m in months_axis:
        if m > 0 and m % cip_frequency_months == 0:
            accumulated_fouling_resistance *= (1.0 - cip_efficiency)
            
        yr_equivalent = m / 12.0
        Aw_base_degrade = cfg['Aw'] * selected_mem['aw_mod'] * TCF * (1.0 - selected_mem['compaction'] * np.log1p(yr_equivalent))
        current_rejection = min(0.9995, selected_mem['rejection'] / (1.0 + selected_mem['leak_grow'] * yr_equivalent))
        
        conc_mult = 1.0 / max(0.01, 1.0 - (Y_user_target / 100.0))
        tail_ca, tail_so4, tail_tds = treated_chemistry['Ca'] * conc_mult, treated_chemistry['SO4'] * conc_mult, local_inlet_tds * conc_mult
        
        caso4_sat = (((tail_ca / 40078) * (tail_so4 / 96060)) / 2.4e-5) * 100.0
        tail_lsi = calculate_lsi(tail_tds, T_operating, tail_ca, treated_chemistry['HCO3'] * conc_mult, st.session_state.target_ph)
        
        if tail_lsi > max_brine_lsi: max_brine_lsi = tail_lsi
        if caso4_sat > max_caso4_saturation: max_caso4_saturation = caso4_sat
        
        supersat = max(0.0, tail_lsi - 1.0) + (max(0.0, caso4_sat - gypsum_ceiling) * 0.025)
        accumulated_fouling_resistance += supersat * cfg['scale_factor'] * (0.05 if tech == 'CCRO' else 0.02 if tech == 'PFRO' else 0.12)
        
        avg_ndp = (cfg['target_flux'] / (1.0 + accumulated_fouling_resistance)) / Aw_base_degrade
        friction = (cfg['stages'] * cfg['elements']) * (0.55 if tech in ['Conventional', 'FRRO'] else 0.35)
        pump_p = max(12.0, min(140.0, avg_ndp + (0.0072 * ((local_inlet_tds + tail_tds) / 2) * 0.45) + friction))
        
        if has_erd:
            net_kw = max(5.0, (((Q_feed_total * pump_p) / 36.0) / (0.85 * vfd_eff)) - (((Q_feed_total * ((100.0 - Y_user_target)/100.0)) * pump_p * 0.94) / 36.0))
        else:
            net_kw = max(5.0, (((Q_feed_total * pump_p) / 36.0) / (0.85 * vfd_eff)))
            
        pressures.append(pump_p)
        secs.append(net_kw / (Q_feed_total * (Y_user_target / 100.0)))
        perm_tds.append(local_inlet_tds * (1.0 - current_rejection))
        
    lifecycle_results[tech] = {'p': pressures, 'sec': secs, 'tds': perm_tds}

    # Spatial Mapping Vector
    elem_idx = np.arange(1, custom_elements + 1)
    flux_vector, tds_vector, lsi_vector = [], [], []
    current_tds, current_ca, current_alk = local_inlet_tds, treated_chemistry['Ca'], treated_chemistry['HCO3']
    rec_per_element = (Y_user_target / 100.0) / custom_elements
    for elem in elem_idx:
        flux_vector.append(cfg['target_flux'] * (1.15 - (0.05 * elem)))
        tds_vector.append(current_tds)
        lsi_vector.append(calculate_lsi(current_tds, T_operating, current_ca, current_alk, st.session_state.target_ph))
        multiplier = 1.0 / max(0.01, (1.0 - rec_per_element))
        current_tds *= multiplier; current_ca *= multiplier; current_alk *= multiplier
    spatial_results[tech] = {'elem': elem_idx, 'flux': flux_vector, 'tds': tds_vector, 'lsi': lsi_vector}

p_end, sec_end = lifecycle_results[primary_tech]['p'][-1], lifecycle_results[primary_tech]['sec'][-1]
daily_volume = Q_feed_total * (Y_user_target / 100.0) * 24
q_permeate, q_brine = Q_feed_total * (Y_user_target / 100.0), Q_feed_total - (Q_feed_total * (Y_user_target / 100.0))

# --- 5. AUTOMATED EQUIPMENT SIZING ENGINE MATRIX DISPLAY ---
st.subheader("📐 Automated Array Geometry Sizing Results")
size_col1, size_col2, size_col3, size_col4 = st.columns(4)

with size_col1:
    st.metric(label="Calculated Active Element Count", value=f"{calculated_total_elements} Units", caption=f"Total Surface Area: {required_surface_area_m2:.1f} m²")
with size_col2:
    st.metric(label="Total Sized Pressure Vessels", value=f"{vessel_count} Vessels", caption=f"Housing {elements_per_vessel} membranes each")
with size_col3:
    st.metric(label="Balanced Staging Array Blueprint", value=f"{stage1_vessels} ➔ {stage2_vessels if stage2_vessels > 0 else 'None'}", caption=f"Configured layout: Stage 1 ➔ Stage 2")
with size_col4:
    hydraulic_power_kw = (Q_feed_total * p_end) / 36.0
    pump_bhp_hp = (hydraulic_power_kw / 0.7457) / 0.88  # converting to horse power with mechanical shaft safety margins
    st.metric(label="HPP Motor Frame Size Sized", value=f"{pump_bhp_hp:.1f} HP", caption=f"Absorbed Shaft Power: {hydraulic_power_kw:.1f} kW")


# --- 6. PROCESS FLOW DIAGRAM ---
st.subheader("🏭 Live Process Flow Diagram (PFD)")
with st.container(border=True):
    pfd_col1, pfd_col2, pfd_col3, pfd_col4, pfd_col5 = st.columns([1, 1, 1.3, 1, 1])
    with pfd_col1:
        st.markdown("### 🚰 Stream 1\n**Raw Influent Feed**")
        st.metric(label="Flow Rate", value=f"{Q_feed_total:.1f} m³/h")
        st.caption(f"TDS: {local_inlet_tds:,.0f} mg/L")
    with pfd_col2:
        st.markdown("### 🧬 Stream 2\n**Chemical Dosing**")
        st.metric(label="Target pH", value=f"{st.session_state.target_ph:.2f}")
        st.caption(f"Anti-scalant: {st.session_state.as_dosage:.1f} mg/L")
    with pfd_col3:
        st.markdown(f"### ⚡ Pump & Core\n**HPP Array Layout**")
        st.metric(label="Discharge Pressure", value=f"{p_end:.1f} bar")
        st.caption(f"Staging Profile Split: {stage1_vessels}:{stage2_vessels}")
    with pfd_col4:
        st.markdown("### 💧 Stream 3\n**Permeate Yield**")
        st.metric(label="Product Flow", value=f"{q_permeate:.1f} m³/h")
        st.caption(f"Quality: {lifecycle_results[primary_tech]['tds'][-1]:.1f} mg/L")
    with pfd_col5:
        st.markdown("### 🌶️ Stream 4\n**Concentrate Brine**")
        st.metric(label="Reject Flow", value=f"{q_brine:.1f} m³/h")
        st.caption(f"Brine LSI: {max_brine_lsi:.2f}")

# 7. RENDER LIVE KPI METRIC CARDS
st.subheader("📊 Live System Key Performance Indicators (KPIs)")
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
p_start, sec_start = lifecycle_results[primary_tech]['p'][0], lifecycle_results[primary_tech]['sec'][0]
with kpi_col1: st.metric(label="Pump Overhaul Pressure", value=f"{p_end:.1f} bar", delta=f"+{p_end - p_start:.1f} bar drift", delta_color="inverse")
with kpi_col2: st.metric(label="Specific Energy Cost (SEC)", value=f"{sec_end:.3f} kWh/m³", delta=f"+{((sec_end - sec_start)/sec_start)*100:.1f}% Fouling Strain", delta_color="inverse")
with kpi_col3: st.metric(label="Total Plant Water Yield", value=f"{daily_volume:,.0f} m³/day", delta=f"Based on {Y_user_target}% Recovery")
with kpi_col4: st.metric(label="Vessel Structural Health State", value="Highly Stable" if max_brine_lsi < 1.5 else "Scaling Susceptible", delta=f"Max Brine LSI: {max_brine_lsi:.2f}", delta_color="normal" if max_brine_lsi < 1.5 else "inverse")

# 8. SAFETY MONITORS
st.subheader("🚨 Real-Time Safety & Fouling Guardrails")
guardrail_healthy = True
if max_brine_lsi > 2.2:
    st.error(f"⚠️ **CRITICAL SCALING WARNING:** Calculated Tail Node Brine LSI is dangerously high ({max_brine_lsi:.2f}).")
    if st.button("🔧 Auto-Dose Acid (Fix Carbonate Scaling)", key="btn_lsi"): st.session_state.apply_lsi_fix = True; st.rerun()
    guardrail_healthy = False
if max_caso4_saturation > 250.0:
    st.error(f"💥 **CRITICAL GYPSUM WARNING:** Gypsum ($CaSO_4$) saturation levels have exceeded safe boundary ceilings ({max_caso4_saturation:.1f}%).")
    if st.button("🚀 Optimize Anti-Scalant Dosing (Fix Gypsum Scaling)", key="btn_gyp"): st.session_state.apply_gypsum_fix = True; st.rerun()
    guardrail_healthy = False
if guardrail_healthy: st.success("✅ **HYDRAULIC ENVELOPE SECURE:** All parameters fall within safe margins.")


# --- 9. REAL-TIME FINANCIAL COST MATRIX ---
st.write("---")
st.subheader("💸 Real-Time Levelized Cost & Asset Valuation Engine")

annual_water_m3 = daily_volume * 365.0
pretreatment_sec = 0.35
total_system_sec = sec_end + pretreatment_sec
annual_power_kwh = total_system_sec * annual_water_m3
annual_power_cost = annual_power_kwh * elec_rate

annual_cip_washes = 12.0 / cip_frequency_months
annual_cip_cost = annual_cip_washes * vessel_count * 250.0

daily_feed_mass_kg = (Q_feed_total * 24.0) * 1000.0
daily_as_kg = (st.session_state.as_dosage / 1e6) * daily_feed_mass_kg
annual_as_cost = daily_as_kg * 365.0 * as_chem_rate
total_chem_cost = annual_as_cost + annual_cip_cost

total_elements_replaced = vessel_count * elements_per_vessel
total_membrane_capex = total_elements_replaced * selected_mem["cost"]
hpp_hardware_capex = 8500.0 * (hydraulic_power_kw ** 0.65) * (vessel_count / 4.0)
annual_machinery_amortization = (hpp_hardware_capex + total_membrane_capex) / 4.0

total_calculated_opex = annual_power_cost + total_chem_cost + annual_machinery_amortization
lcow_per_m3 = total_calculated_opex / annual_water_m3 if annual_water_m3 > 0 else 0.0

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1: st.metric(label="Total Co-Located Asset CAPEX", value=f"${hpp_hardware_capex + total_membrane_capex:,.2f}", caption="Pump Array + Membranes")
with m_col2: st.metric(label="Annual CIP Wash & Chemical OPEX", value=f"${total_chem_cost:,.2f}", caption=f"Includes {annual_cip_washes:.0f} clean cycles/yr")
with m_col3: st.metric(label="Annual Energy Bill (RO + Pre-Tx)", value=f"${annual_power_cost:,.2f}", caption=f"Total: {annual_power_kwh:,.0f} kWh/yr")
with m_col4: st.metric(label="Levelized Cost of Water (LCOW)", value=f"${lcow_per_m3:.3f} per m³", delta=f"OPEX Base: ${total_calculated_opex:,.0f}/yr")


# 10. TAB PLOTS INTERFACE
st.write("---")
tab_lifecycle, tab_spatial = st.tabs(["⏳ Long-Term Lifecycle Metrics", "📐 Internal Vessel Spatial Profiling"])

with tab_lifecycle:
    st.subheader("Performance Analytics Over 48-Month Maintenance Windows")
    fig1, ax1 = plt.subplots(1, 3, figsize=(15, 4.5))
    for tech, data in lifecycle_results.items():
        color = full_tech_registry[tech]['color']
        ax1[0].plot(months_axis, data['p'], '-', color=color, linewidth=2, label=tech)
        ax1[1].plot(months_axis, data['sec'], '-', color=color, linewidth=2, label=tech)
        ax1[2].plot(months_axis, data['tds'], '-', color=color, linewidth=2, label=tech)
        
    ax1[0].set_title("Required Feed Pressure (bar)")
    ax1[0].set_xlabel("Operating Months")
    ax1[0].grid(True, linestyle=":")
    ax1[0].legend()
    
    ax1[1].set_title("Specific Energy Cost (kWh/m³)")
    ax1[1].set_xlabel("Operating Months")
    ax1[1].grid(True, linestyle=":")
    
    ax1[2].set_title("Permeate Product Water TDS (mg/L)")
    ax1[2].set_xlabel("Operating Months")
    ax1[2].axhline(500.0, color='red', linestyle='--', alpha=0.7, label='WHO Cap')
    ax1[2].grid(True, linestyle=":")
    ax1[2].legend()
    
    st.pyplot(fig1)

with tab_spatial:
    st.subheader(f"Cross-Sectional Vector Profile Along the Pressure Vessel (Element #1 to #{custom_elements})")
    fig2, ax2 = plt.subplots(1, 3, figsize=(15, 4.5))
    for tech, data in spatial_results.items():
        color = full_tech_registry[tech]['color']
        ax2[0].plot(data['elem'], data['flux'], 'o-', color=color, linewidth=2, label=tech)
        ax2[1].plot(data['elem'], data['tds'], 's-', color=color, linewidth=2, label=tech)
        ax2[2].plot(data['elem'], data['lsi'], 'D-', color=color, linewidth=2, label=tech)
        
    ax2[0].set_title("Local Element Flux (LMH)")
    ax2[0].set_xlabel("Element Number")
    ax2[0].set_xticks(np.arange(1, custom_elements + 1))
    ax2[0].grid(True, linestyle=":")
    ax2[0].legend()
    
    ax2[1].set_title("Local Channel Stream TDS (mg/L)")
    ax2[1].set_xlabel("Element Number")
    ax2[1].set_xticks(np.arange(1, custom_elements + 1))
    ax2[1].grid(True, linestyle=":")
    
    ax2[2].set_title("Local Scaling Risk Index (LSI)")
    ax2[2].set_xlabel("Element Number")
    ax2[2].set_xticks(np.arange(1, custom_elements + 1))
    ax2[2].axhline(1.5, color='orange', linestyle='--', alpha=0.7, label='Caution Ceiling')
    ax2[2].grid(True, linestyle=":")
    ax2[2].legend()
    
    st.pyplot(fig2)
