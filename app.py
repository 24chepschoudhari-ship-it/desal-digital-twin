import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# 1. PAGE SETUP & STYLING
st.set_page_config(page_title="Desalination Digital Twin", layout="wide")

st.title("🖥️ Industrial Desalination Digital Twin")
st.markdown("### Advanced Multi-Year Operational Lifecycle & Safety Analytics Suite")
st.write("---")

# Initialize persistent session state tracking for chemistry parameters
if "na_val" not in st.session_state: st.session_state.na_val = 650.0
if "cl_val" not in st.session_state: st.session_state.cl_val = 950.0
if "target_ph" not in st.session_state: st.session_state.target_ph = 7.8
if "as_dosage" not in st.session_state: st.session_state.as_dosage = 3.0

# 2. SIDEBAR PANEL FOR INTERACTIVE SETTINGS
st.sidebar.header("⚙️ Plant Operating Framework")

# Process Configuration
st.sidebar.subheader("📐 Process Configuration")
tech_view_mode = st.sidebar.selectbox(
    "Select Display Mode",
    ["Compare All Schemes", "Single Scheme Focus"]
)

if tech_view_mode == "Single Scheme Focus":
    target_tech = st.sidebar.selectbox("Select Target Technology", ["PFRO", "CCRO", "FRRO", "Conventional"])
else:
    target_tech = None

# Custom Array Geometry Configurator
st.sidebar.subheader("🎛️ Array Element Geometry")
col_stages, col_elems = st.sidebar.columns(2)
with col_stages:
    custom_stages = st.number_input("No. of Stages", min_value=1, max_value=3, value=1, step=1)
with col_elems:
    custom_elements = st.number_input("Elements / Vessel", min_value=2, max_value=8, value=6, step=1)

# Dual Input Sync Logic for Hydraulics
st.sidebar.subheader("🌊 Hydraulic & Thermodynamic Bounds")

# Sync Feed Flow
if "flow_val" not in st.session_state: st.session_state.flow_val = 346.4
col_f1, col_f2 = st.sidebar.columns([2, 1])
with col_f1:
    f_slide = st.slider("Feed Flow Rate (Q₀, m³/h)", 50.0, 600.0, float(st.session_state.flow_val), step=10.0, key="fs")
with col_f2:
    f_num = st.number_input("Value", 50.0, 600.0, float(st.session_state.flow_val), step=0.1, key="fn", label_visibility="collapsed")
st.session_state.flow_val = f_num if f_num != st.session_state.flow_val else f_slide

# Recovery bounds
if "rec_val" not in st.session_state: st.session_state.rec_val = 75.0
col_r1, col_r2 = st.sidebar.columns([2, 1])
with col_r1:
    r_slide = st.slider("Target Recovery Goal (Y, %)", 40.0, 96.0, float(st.session_state.rec_val), step=0.5, key="rs")
with col_r2:
    r_num = st.number_input("Value", 40.0, 96.0, float(st.session_state.rec_val), step=0.1, key="rn", label_visibility="collapsed")
st.session_state.rec_val = r_num if r_num != st.session_state.rec_val else r_slide

# Sync Temperature
if "temp_val" not in st.session_state: st.session_state.temp_val = 25.0
col_t1, col_t2 = st.sidebar.columns([2, 1])
with col_t1:
    t_slide = st.slider("Operating Temp (°C)", 5.0, 45.0, float(st.session_state.temp_val), step=1.0, key="ts")
with col_t2:
    t_num = st.number_input("Value", 5.0, 45.0, float(st.session_state.temp_val), step=0.5, key="tn", label_visibility="collapsed")
st.session_state.temp_val = t_num if t_num != st.session_state.temp_val else t_slide

# Extract active variables
Q_feed_total = st.session_state.flow_val
Y_user_target = st.session_state.rec_val
T_operating = st.session_state.temp_val

# Membrane Specs
st.sidebar.subheader("🧬 Membrane Specifications")
mem_choice = st.sidebar.selectbox(
    "Select Membrane Element Model",
    ["Standard Brackish (BW30)", "Low Energy (LE)", "High-Rejection (SW30)"]
)
horizon_years = st.sidebar.slider("Lifecycle Evaluation Window (Years)", 1, 7, 5)

# Chemical Pre-Treatment Panel
st.sidebar.subheader("🧪 Chemical Pre-Treatment & Dosing")
acid_choice = st.sidebar.selectbox("Acid Treatment Strategy", ["None", "Sulfuric Acid (H2SO4)", "Hydrochloric Acid (HCl)"])

if acid_choice != "None":
    st.session_state.target_ph = st.sidebar.slider("Target Dosed pH", 5.0, 7.8, float(st.session_state.target_ph), step=0.1)
else:
    st.session_state.target_ph = 7.8

st.session_state.as_dosage = st.sidebar.slider("Anti-Scalant Target (mg/L)", 0.0, 12.0, float(st.session_state.as_dosage), step=0.5)

# --- INTERCEPTOR: AUTO-MITIGATION TRIGGERS ---
if st.session_state.get("apply_lsi_fix"):
    st.session_state.target_ph = 6.2
    st.session_state.apply_lsi_fix = False

if st.session_state.get("apply_gypsum_fix"):
    st.session_state.as_dosage = 8.5
    st.session_state.apply_gypsum_fix = False

# 3. WATER CHEMISTRY INTERFACE
st.subheader("💧 Raw Water Influent Chemistry")
col_na, col_cl, col_ca, col_so4, col_alk = st.columns(5)

ca_fixed = 180.0
so4_fixed = 520.0
alk_fixed = 220.0

with col_na: na_input = st.number_input("Sodium (Na⁺, mg/L)", min_value=0.0, max_value=50000.0, value=float(st.session_state.na_val), step=10.0)
with col_cl: cl_input = st.number_input("Chloride (Cl⁻, mg/L)", min_value=0.0, max_value=50000.0, value=float(st.session_state.cl_val), step=10.0)
with col_ca: ca_input = st.number_input("Calcium (Ca²⁺, mg/L)", value=ca_fixed)
with col_so4: so4_input = st.number_input("Sulfate (SO₄²⁻, mg/L)", value=so4_fixed)
with col_alk: allk_input = st.number_input("Alkalinity (HCO₃⁻, mg/L)", value=alk_fixed)

st.session_state.na_val = na_input
st.session_state.cl_val = cl_input

ph_delta = max(0.0, 7.8 - st.session_state.target_ph)
dosed_alk = alk_fixed * max(0.10, 1.0 - (ph_delta * 0.45))
dosed_so4 = so4_fixed + (ph_delta * 55.0) if acid_choice == "Sulfuric Acid (H2SO4)" else so4_fixed
dosed_cl = cl_input + (ph_delta * 40.0) if acid_choice == "Hydrochloric Acid (HCl)" else cl_input
treated_chemistry = {'Na': na_input, 'Cl': dosed_cl, 'Ca': ca_fixed, 'SO4': dosed_so4, 'HCO3': dosed_alk}

cations_meq = (na_input * 1 / 22.99) + (ca_fixed * 2 / 40.08)
anions_meq = (dosed_cl * 1 / 35.45) + (dosed_so4 * 2 / 96.06) + (dosed_alk * 1 / 61.02)
total_charge = cations_meq + anions_meq
ion_balance_error = ((cations_meq - anions_meq) / total_charge) * 100 if total_charge > 0 else 0.0

col_bal_badge, col_bal_metrics, col_bal_btn = st.columns([1.2, 3.8, 1.5])
with col_bal_badge:
    if abs(ion_balance_error) <= 5.0: st.success("✅ Ion Balance OK")
    else: st.error("❌ Charge Imbalance")
with col_bal_metrics:
    st.markdown(f"**Cations:** `{cations_meq:.2f} meq/L` | **Anions:** `{anions_meq:.2f} meq/L` | **Electro-Neutrality Error:** `{ion_balance_error:.2f}%` (Target: < ±5%)")
with col_bal_btn:
    if abs(ion_balance_error) > 0.01:
        if st.button("⚖️ Auto-Balance Ions", type="primary"):
            delta_meq = cations_meq - anions_meq
            if delta_meq > 0: st.session_state.cl_val = cl_input + (delta_meq * 35.45)
            else: st.session_state.na_val = na_input + (abs(delta_meq) * 22.99)
            st.rerun()

# 4. SIMULATION ENGINE KINETICS
mem_registry = {
    'Low Energy (LE)': {'aw_mod': 1.35, 'rejection': 0.993, 'compaction': 0.095, 'leak_grow': 0.22},
    'Standard Brackish (BW30)': {'aw_mod': 1.00, 'rejection': 0.997, 'compaction': 0.065, 'leak_grow': 0.15},
    'High-Rejection (SW30)': {'aw_mod': 0.65, 'rejection': 0.9985, 'compaction': 0.035, 'leak_grow': 0.08}
}
selected_mem = mem_registry[mem_choice]

def calculate_lsi(tds, temp_c, calcium, alkalinity, current_ph):
    log10_tds = np.log10(max(10.0, tds))
    A = (log10_tds - 1.0) / 10.0
    B = -13.12 * np.log10(temp_c + 273.15) + 34.55
    C = np.log10(max(1.0, calcium * 2.497)) - 0.40
    D = np.log10(max(1.0, alkalinity * 0.82))
    return current_ph - ((9.3 + A + B) - (C + D))

full_tech_registry = {
    'PFRO': {'stages': custom_stages, 'elements': custom_elements, 'Aw': 2.45, 'color': '#2ecc71', 'scale_factor': 0.090, 'target_flux': 24.5},
    'FRRO': {'stages': custom_stages, 'elements': custom_elements, 'Aw': 1.45, 'color': '#e67e22', 'scale_factor': 0.050, 'target_flux': 19.0},
    'CCRO': {'stages': custom_stages, 'elements': custom_elements, 'Aw': 1.85, 'color': '#3498db', 'scale_factor': 0.120, 'target_flux': 21.0},
    'Conventional': {'stages': custom_stages, 'elements': custom_elements, 'Aw': 1.25, 'color': '#95a5a6', 'scale_factor': 0.180, 'target_flux': 17.5}
}

tech_registry = {target_tech: full_tech_registry[target_tech]} if tech_view_mode == "Single Scheme Focus" and target_tech else full_tech_registry
primary_tech = list(tech_registry.keys())[0]

t_kelvin_base, t_kelvin_actual = 298.15, 273.15 + T_operating
TCF = np.exp(2640.0 * (1.0 / t_kelvin_base - 1.0 / t_kelvin_actual))
vfd_eff = 0.98 if abs(T_operating - 25.0) < 5 else 0.95
local_inlet_tds = sum(treated_chemistry.values())

years_axis = np.arange(0, horizon_years + 1)
lifecycle_results, spatial_results = {}, {}
max_brine_lsi, max_caso4_saturation = -99.0, 0.0

for tech, cfg in tech_registry.items():
    pressures, secs, perm_tds = [], [], []
    res_factor = 0.7 if tech in ['PFRO', 'CCRO'] else 1.2
    gypsum_ceiling = 100.0 if st.session_state.as_dosage == 0 else min(600.0, 100.0 + (25.5 * (st.session_state.as_dosage ** 1.15) * np.exp(-0.15 * res_factor)))
    
    for yr in years_axis:
        Aw_corrected = cfg['Aw'] * selected_mem['aw_mod'] * TCF * (1.0 - selected_mem['compaction'] * np.log1p(yr))
        current_rejection = min(0.9995, selected_mem['rejection'] / (1.0 + selected_mem['leak_grow'] * yr))
        conc_mult = 1.0 / max(0.01, 1.0 - (Y_user_target / 100.0))
        tail_ca, tail_so4, tail_tds = treated_chemistry['Ca'] * conc_mult, treated_chemistry['SO4'] * conc_mult, local_inlet_tds * conc_mult
        
        caso4_sat = (((tail_ca / 40078) * (tail_so4 / 96060)) / 2.4e-5) * 100.0
        tail_lsi = calculate_lsi(tail_tds, T_operating, tail_ca, treated_chemistry['HCO3'] * conc_mult, st.session_state.target_ph)
        
        if tail_lsi > max_brine_lsi: max_brine_lsi = tail_lsi
        if caso4_sat > max_caso4_saturation: max_caso4_saturation = caso4_sat
        
        supersat = max(0.0, tail_lsi - 1.0) + (max(0.0, caso4_sat - gypsum_ceiling) * 0.025)
        scale_res = supersat * cfg['scale_factor'] * (1.4 if tech == 'Conventional' else 0.35 if tech == 'CCRO' else 0.15 if tech == 'PFRO' else 0.4)
        avg_ndp = (cfg['target_flux'] / (1.0 + scale_res)) / Aw_corrected
        
        friction = (cfg['stages'] * cfg['elements']) * (0.55 if tech in ['Conventional', 'FRRO'] else 0.35)
        pump_p = max(12.0, min(140.0, avg_ndp + (0.0072 * ((local_inlet_tds + tail_tds) / 2) * 0.45) + friction))
        net_kw = max(5.0, (((Q_feed_total * pump_p) / 36.0) / (0.85 * vfd_eff)) - (((Q_feed_total * (1.0 - Y_user_target/100.0)) * pump_p * 0.95) / 36.0))
        
        pressures.append(pump_p)
        secs.append(net_kw / (Q_feed_total * (Y_user_target / 100.0)))
        perm_tds.append(local_inlet_tds * (1.0 - current_rejection))
        
    lifecycle_results[tech] = {'p': pressures, 'sec': secs, 'tds': perm_tds}

    # SPATIAL VECTOR PROFILING ENGINE
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
q_permeate = Q_feed_total * (Y_user_target / 100.0)
q_brine = Q_feed_total - q_permeate

# --- 5. INTERACTIVE PROCESS FLOW DIAGRAM (PFD) ---
st.subheader("🏭 Live Process Flow Diagram (PFD)")
with st.container(border=True):
    pfd_col1, pfd_col2, pfd_col3, pfd_col4, pfd_col5 = st.columns([1, 1, 1.3, 1, 1])
    
    with pfd_col1:
        st.markdown("### 🚰 Stream 1\n**Raw Influent Feed**")
        st.metric(label="Flow Rate", value=f"{Q_feed_total:.1f} m³/h")
        st.caption(f"TDS: {local_inlet_tds:,.0f} mg/L")
        st.markdown("<div style='text-align: center; font-size: 24px; color: #3498db;'>➔ ➔ ➔</div>", unsafe_allow_html=True)

    with pfd_col2:
        st.markdown("### 🧬 Stream 2\n**Chemical Dosing**")
        st.metric(label="Target pH", value=f"{st.session_state.target_ph:.2f}")
        st.caption(f"Anti-scalant: {st.session_state.as_dosage:.1f} mg/L")
        st.markdown("<div style='text-align: center; font-size: 24px; color: #9b59b6;'>➔ ➔ ➔</div>", unsafe_allow_html=True)

    with pfd_col3:
        st.markdown(f"### ⚡ Pump & Core\n**{primary_tech} Array**")
        st.metric(label="HPP Discharge Pressure", value=f"{p_end:.1f} bar")
        st.caption(f"Configuration: {custom_stages} Stage / {custom_elements} Elements")
        pump_arrow_color = "#e74c3c" if (max_brine_lsi > 2.2 or max_caso4_saturation > 250.0) else "#2ecc71"
        st.markdown(f"<div style='text-align: center; font-size: 24px; color: {pump_arrow_color};'>➔ Split ➔</div>", unsafe_allow_html=True)

    with pfd_col4:
        st.markdown("### 💧 Stream 3\n**Permeate Yield**")
        st.metric(label="Product Flow", value=f"{q_permeate:.1f} m³/h")
        st.caption(f"Quality: {lifecycle_results[primary_tech]['tds'][-1]:.1f} mg/L")
        st.markdown("<div style='text-align: center; font-size: 24px; color: #2ecc71;'>➔ Product</div>", unsafe_allow_html=True)

    with pfd_col5:
        st.markdown("### 🌶️ Stream 4\n**Concentrate Brine**")
        st.metric(label="Reject Flow", value=f"{q_brine:.1f} m³/h")
        st.caption(f"Brine LSI: {max_brine_lsi:.2f}")
        st.markdown("<div style='text-align: center; font-size: 24px; color: #e67e22;'>➔ Discharge</div>", unsafe_allow_html=True)

# 6. RENDER LIVE KPI METRIC CARDS
st.subheader("📊 Live System Key Performance Indicators (KPIs)")
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
p_start, sec_start = lifecycle_results[primary_tech]['p'][0], lifecycle_results[primary_tech]['sec'][0]

with kpi_col1: st.metric(label=f"Pump Pressure (Yr 0 ➔ Yr {horizon_years})", value=f"{p_end:.1f} bar", delta=f"+{p_end - p_start:.1f} bar tax", delta_color="inverse")
with kpi_col2: st.metric(label="Specific Energy Cost (SEC)", value=f"{sec_end:.3f} kWh/m³", delta=f"+{((sec_end - sec_start)/sec_start)*100:.1f}% Degradation", delta_color="inverse")
with kpi_col3: st.metric(label="Total Plant Water Yield", value=f"{daily_volume:,.0f} m³/day", delta=f"Based on {Y_user_target}% Recovery")
with kpi_col4:
    status_text = "Highly Stable" if max_brine_lsi < 1.5 else "Scaling Susceptible"
    st.metric(label="Vessel Structural Health State", value=status_text, delta=f"Max Brine LSI: {max_brine_lsi:.2f}", delta_color="normal" if max_brine_lsi < 1.5 else "inverse")

# 7. DIAGNOSTIC & AUTOMATED MITIGATION MONITORS
st.subheader("🚨 Real-Time Safety & Fouling Guardrails")
guardrail_healthy = True

if max_brine_lsi > 2.2:
    st.error(f"⚠️ **CRITICAL SCALING WARNING:** Calculated Tail Node Brine LSI is dangerously high ({max_brine_lsi:.2f}). Severe Calcium Carbonate ($CaCO_3$) crystallization is predicted to choke the spacers.")
    st.markdown("**What's wrong:** High alkaline concentration at high recovery elevates the pH saturation threshold, forcing immediate mineral scale dropout.")
    if st.button("🔧 Auto-Dose Acid (Fix Carbonate Scaling)", key="btn_lsi"):
        st.session_state.apply_lsi_fix = True
        st.rerun()
    guardrail_healthy = False
elif max_brine_lsi > 1.5:
    st.warning(f"⚡ **OPERATIONAL NOTICE:** Brine LSI is elevated ({max_brine_lsi:.2f}). High threat of crystal incubation. Ensure anti-scalant pumps are fully operational.")
    guardrail_healthy = False

if max_caso4_saturation > 250.0:
    st.error(f"💥 **CRITICAL GYPSUM WARNING:** Gypsum ($CaSO_4$) saturation levels have exceeded safe boundary ceilings ({max_caso4_saturation:.1f}%). Permanent flux decline will occur within minutes of operations.")
    st.markdown("**What's wrong:** Total concentration factor has pushed Calcium and Sulfate ions far past their thermodynamic solubility product limits.")
    if st.button("🚀 Optimize Anti-Scalant Dosing (Fix Gypsum Scaling)", key="btn_gyp"):
        st.session_state.apply_gypsum_fix = True
        st.rerun()
    guardrail_healthy = False

if guardrail_healthy:
    st.success("✅ **HYDRAULIC ENVELOPE SECURE:** All chemical saturation kinetics fall within safe anti-fouling parameters for the chosen layout profile. Membranes are running in optimal thermodynamic health.")

# 8. TAB INTERFACE WITH UNPACKED LINE MATPLOTLIB PROPERTIES
st.write("---")
tab_lifecycle, tab_spatial = st.tabs(["⏳ Long-Term Lifecycle Metrics", "📐 Internal Vessel Spatial Profiling"])

with tab_lifecycle:
    st.subheader(f"Metrics Projected Over {horizon_years} Operational Years")
    fig1, ax1 = plt.subplots(1, 3, figsize=(15, 4.5))
    for tech, data in lifecycle_results.items():
        color = full_tech_registry[tech]['color']
        ax1[0].plot(years_axis, data['p'], 'o-', color=color, linewidth=2, label=tech)
        ax1[1].plot(years_axis, data['sec'], 's-', color=color, linewidth=2, label=tech)
        ax1[2].plot(years_axis, data['tds'], 'D-', color=color, linewidth=2, label=tech)
        
    ax1[0].set_title("Required Pump Pressure (bar)")
    ax1[0].set_xlabel("Years")
    ax1[0].grid(True, linestyle=":")
    ax1[0].legend()
    
    ax1[1].set_title("Specific Energy Cost (kWh/m³)")
    ax1[1].set_xlabel("Years")
    ax1[1].grid(True, linestyle=":")
    
    ax1[2].set_title("Permeate Product Water TDS (mg/L)")
    ax1[2].set_xlabel("Years")
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
