import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io

# ==========================================
# PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="HKMA GS-2 Corporate Transition Risk & Underwriting Dashboard",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .card {
        padding: 1.2rem;
        border-radius: 0.5rem;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE INITIALIZATION FOR FEEDBACK
# ==========================================
if "feedback_list" not in st.session_state:
    st.session_state.feedback_list = []

# ==========================================
# PRE-LOADED DATA (HKEX COMPANIES)
# ==========================================
COMPANY_DATA = {
    "Custom Input Mode": {
        "revenue": 10000.0,
        "ebitda": 2000.0,
        "total_debt": 5000.0,
        "loan_amount": 1000.0,
        "emissions": 850000.0,
        "sbti_target": 15.0,
        "green_capex": 20.0,
        "carbon_tax": 50.0
    },
    "Geely Auto (0175.HK)": {
        "revenue": 179200.0,
        "ebitda": 14500.0,
        "total_debt": 42000.0,
        "loan_amount": 5000.0,
        "emissions": 1250000.0,
        "sbti_target": 25.0,
        "green_capex": 35.0,
        "carbon_tax": 75.0
    },
    "Cathay Pacific (0293.HK)": {
        "revenue": 94800.0,
        "ebitda": 15100.0,
        "total_debt": 68000.0,
        "loan_amount": 8000.0,
        "emissions": 14200000.0,
        "sbti_target": 12.0,
        "green_capex": 10.0,
        "carbon_tax": 100.0
    },
    "CR Building Materials (1313.HK)": {
        "revenue": 31500.0,
        "ebitda": 4800.0,
        "total_debt": 15000.0,
        "loan_amount": 3000.0,
        "emissions": 28500000.0,
        "sbti_target": 18.0,
        "green_capex": 15.0,
        "carbon_tax": 80.0
    }
}

# ==========================================
# SIDEBAR - CASE SELECTOR & INPUTS
# ==========================================
st.sidebar.markdown("## ⚙️ Control Panel")
selected_company = st.sidebar.selectbox("Select Company Case", list(COMPANY_DATA.keys()))
defaults = COMPANY_DATA[selected_company]

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Financial Inputs (HKD M)")
rev_input = st.sidebar.number_input("Revenue", value=defaults["revenue"], step=100.0)
ebitda_input = st.sidebar.number_input("EBITDA", value=defaults["ebitda"], step=50.0)
total_debt_input = st.sidebar.number_input("Total Debt", value=defaults["total_debt"], step=100.0)
loan_amount_input = st.sidebar.number_input("Subject Loan Amount", value=defaults["loan_amount"], step=50.0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🌍 Climate & Transition Inputs")
emissions_input = st.sidebar.number_input("Scope 1 & 2 Emissions (tCO2e)", value=defaults["emissions"], step=10000.0)
sbti_input = st.sidebar.slider("SBTi 5-Year Reduction Target (%)", 0.0, 60.0, defaults["sbti_target"], 1.0)
green_capex_input = st.sidebar.slider("Green CapEx Ratio (%)", 0.0, 100.0, defaults["green_capex"], 1.0)
carbon_tax_input = st.sidebar.slider("Carbon Tax Shock Scenario (USD/ton)", 0.0, 200.0, defaults["carbon_tax"], 5.0)
USD_HKD = 7.8

# ==========================================
# CALCULATIONS FOR EXPORT & APP
# ==========================================
is_capex_aligned = green_capex_input >= 30.0
is_sbti_aligned = sbti_input >= 20.0
is_fully_aligned = is_capex_aligned and is_sbti_aligned

annual_reduction_rate = (sbti_input / 100.0) / 5.0 if is_fully_aligned else 0.01
base_interest_rate = 0.06
interest_expense = total_debt_input * base_interest_rate
principal_repayment = loan_amount_input * 0.10
debt_service = interest_expense + principal_repayment

sim_data = []
current_emissions = emissions_input
dscr_list = []
icr_list = []

for i in range(1, 6):
    if i > 1:
        current_emissions *= (1.0 - annual_reduction_rate)
    
    carbon_cost_hkd = (current_emissions * carbon_tax_input * USD_HKD) / 1e6
    stressed_ebitda = max(ebitda_input - carbon_cost_hkd, 10.0)
    
    dscr = stressed_ebitda / debt_service
    icr = stressed_ebitda / interest_expense
    
    dscr_list.append(dscr)
    icr_list.append(icr)
    
    sim_data.append({
        "Year": f"Year {i}",
        "Emissions (tCO2e)": round(current_emissions, 0),
        "Carbon Cost (HKD M)": round(carbon_cost_hkd, 2),
        "Stressed EBITDA (HKD M)": round(stressed_ebitda, 2),
        "DSCR (x)": round(dscr, 2),
        "ICR (x)": round(icr, 2)
    })

df_sim = pd.DataFrame(sim_data)
min_dscr = min(dscr_list)
sicr_triggered = (min_dscr < 1.25) or (not is_fully_aligned)

base_margin_bps = 250.0
if is_fully_aligned and sbti_input >= 25.0:
    pricing_adjustment = -15.0
elif not is_fully_aligned or min_dscr < 1.25:
    pricing_adjustment = 20.0
else:
    pricing_adjustment = 0.0

final_margin_bps = base_margin_bps + pricing_adjustment
annual_interest_impact = (loan_amount_input * 1e6 * (pricing_adjustment / 10000.0))

# ==========================================
# EXCEL EXPORT FUNCTION (CREDIT MEMO)
# ==========================================
def generate_credit_memo_excel():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        summary_df = pd.DataFrame([{
            "Company Case": selected_company,
            "Revenue (HKD M)": rev_input,
            "EBITDA (HKD M)": ebitda_input,
            "Total Debt (HKD M)": total_debt_input,
            "Subject Loan (HKD M)": loan_amount_input,
            "Emissions (tCO2e)": emissions_input,
            "SBTi Target (%)": sbti_input,
            "Green CapEx (%)": green_capex_input,
            "Carbon Tax (USD/ton)": carbon_tax_input,
            "Taxonomy Aligned": is_fully_aligned,
            "Min Projected DSCR": round(min_dscr, 2),
            "IFRS 9 Staging": "Stage 2 (SICR)" if sicr_triggered else "Stage 1"
        }])
        summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
        df_sim.to_excel(writer, sheet_name='5-Year Stress Testing', index=False)
        
        sll_df = pd.DataFrame([{
            "Base Margin (bps)": base_margin_bps,
            "Pricing Adjustment (bps)": pricing_adjustment,
            "Final Loan Margin (bps)": final_margin_bps,
            "Annual Interest Impact (HKD)": annual_interest_impact
        }])
        sll_df.to_excel(writer, sheet_name='SLL Pricing & Subsidies', index=False)
    output.seek(0)
    return output

st.sidebar.markdown("---")
st.sidebar.markdown("### 📥 Credit Memo Export")
excel_file = generate_credit_memo_excel()
st.sidebar.download_button(
    label="📄 一鍵匯出信用審查備忘錄 (Excel)",
    data=excel_file,
    file_name=f"Credit_Memo_{selected_company.replace(' ', '_').replace('(', '').replace(')', '')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ==========================================
# MAIN TITLE & OVERVIEW
# ==========================================
st.markdown('<p class="main-header">🏦 Credit Risk Assessment & Underwriting Design</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Corporate Transition Framework under HKMA SPM GS-2 Guidelines & IFRS 9 Staging</p>', unsafe_allow_html=True)

# ==========================================
# TABS SETUP
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📈 Risk Assessment & Stress Testing", 
    "💡 Underwriting Structuring & Subsidies", 
    "📝 Practitioner Feedback Survey"
])

# ==========================================
# TAB 1: RISK ASSESSMENT & STRESS TESTING
# ==========================================
with tab1:
    st.markdown("### 1. Phase 2A Taxonomy Alignment Check")
    
    with st.expander("📖 點此查看 HKMA SPM GS-2 計算邏輯與公式說明 (Taxonomy Alignment)"):
        st.markdown("""
        - **Phase 2A 判定標準**：依據香港金融管理局（HKMA）《氣候風險管理》（SPM GS-2）及綠色分類目錄，企業必須同時滿足 **綠色資本支出佔比 $\ge 30\%$** 且 **SBTi 5年減碳目標 $\ge 20\%$**，方可被判定為「Taxonomy Aligned (Green)」。
        - **不符之影響**：若未達標則列為轉型中/棕色資產（Transition/Brown），可能觸發 IFRS 9 階段二信用風險評估。
        """)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Green CapEx Benchmark", f"{green_capex_input}%", "Target: ≥ 30%", delta_color="normal" if is_capex_aligned else "inverse")
    with col2:
        st.metric("SBTi Target Benchmark", f"{sbti_input}%", "Target: ≥ 20%", delta_color="normal" if is_sbti_aligned else "inverse")
    with col3:
        alignment_status = "🟢 Taxonomy Aligned (Green)" if is_fully_aligned else "🔴 Non-Aligned (Transition/Brown)"
        st.metric("Taxonomy Status", alignment_status)
    
    st.markdown("---")
    st.markdown("### 2. Forward-Looking 5-Year Stress Testing (Carbon Tax Shock)")
    
    with st.expander("📖 點此查看 HKMA SPM GS-2 計算邏輯與公式說明 (Stress Testing & IFRS 9)"):
        st.markdown("""
        - **碳成本計算公式**：$$\\text{Carbon Cost (HKD)} = \\text{Emissions} \\times \\text{Carbon Tax (USD/ton)} \\times \\text{USD/HKD}$$
        - **DSCR 公式**：$$\\text{DSCR} = \\frac{\\text{Stressed EBITDA}}{\\text{Interest Expense} + \\text{Principal Repayment}}$$
        - **IFRS 9 Staging**：當預測期最低 DSCR $< 1.25\\text{x}$ 或轉型計畫未對齊時，依會計準則需自 Stage 1（12個月預期信用損失）上調至 Stage 2（存續期預期信用損失，SICR）。
        """)

    st.dataframe(df_sim, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 3. IFRS 9 Staging & SICR Trigger Assessment")
    if sicr_triggered:
        st.error(
            f"🚨 **IFRS 9 SICR TRIGGER WARNING: MIGRATION TO STAGE 2 (Lifetime ECL) REQUIRED**\n\n"
            f"Reason: {'Minimum projected DSCR (' + str(round(min_dscr, 2)) + 'x) is below the 1.25x prudential threshold' if min_dscr < 1.25 else ''}"
            f"{' and/or ' if (min_dscr < 1.25 and not is_fully_aligned) else ''}"
            f"{'Corporate Transition Plan is Non-Aligned with HKMA Phase 2A Taxonomy.' if not is_fully_aligned else ''}"
        )
    else:
        st.success(
            "✅ **Credit Risk Standing: STAGE 1 (12-Month ECL)**\n\n"
            "The corporate borrower maintains robust forward-looking debt service coverage (DSCR ≥ 1.25x) and satisfies HKMA Phase 2A Taxonomy alignment criteria."
        )

    st.markdown("---")
    st.markdown("### 4. 5-Year DSCR Trend Visualization")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[f"Year {i}" for i in range(1, 6)], y=dscr_list, mode='lines+markers+text',
        name='Projected DSCR', text=[f"{val:.2f}x" for val in dscr_list],
        textposition="top center", line=dict(color='#0284c7', width=3), marker=dict(size=8)
    ))
    fig.add_hline(
        y=1.25, line_dash="dash", line_color="#dc2626",
        annotation_text="Prudential Threshold (1.25x)", annotation_position="bottom right"
    )
    fig.update_layout(
        xaxis_title="Projection Horizon",
        yaxis_title="Debt Service Coverage Ratio (DSCR)",
        yaxis=dict(range=[0, max(max(dscr_list) + 0.5, 2.0)]),
        margin=dict(l=20, r=20, t=30, b=20),
        height=380
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### 5. 敏感度分析矩陣 (Sensitivity Heatmap)")
    st.markdown("本互動式矩陣模擬不同「碳稅衝擊情境 (USD/ton)」與「綠色資本支出佔比 (%)」組合下的 5 年最低 DSCR 表現。")

    tax_range = [25, 50, 75, 100, 125, 150, 175, 200]
    capex_range = [10, 20, 30, 40, 50, 60]
    heatmap_matrix = []

    for c in capex_range:
        row = []
        for t in tax_range:
            aligned = (c >= 30.0 and sbti_input >= 20.0)
            red_rate = (sbti_input / 100.0) / 5.0 if aligned else 0.01
            curr_e = emissions_input
            min_d = 999.0
            for yr_idx in range(5):
                if yr_idx > 0:
                    curr_e *= (1.0 - red_rate)
                c_cost = (curr_e * t * USD_HKD) / 1e6
                s_ebitda = max(ebitda_input - c_cost, 10.0)
                d = s_ebitda / debt_service
                if d < min_d:
                    min_d = d
            row.append(round(min_d, 2))
        heatmap_matrix.append(row)

    fig_heat = px.imshow(
        heatmap_matrix,
        labels=dict(x="Carbon Tax (USD/ton)", y="Green CapEx (%)", color="Min DSCR (x)"),
        x=[str(t) for t in tax_range],
        y=[str(c) + "%" for c in capex_range],
        color_continuous_scale="RdYlGn",
        range_color=[1.0, 3.0],
        text_auto=True
    )
    fig_heat.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_heat, use_container_width=True)

# ==========================================
# TAB 2: UNDERWRITING STRUCTURING & SUBSIDIES
# ==========================================
with tab2:
    st.markdown("### 1. Sustainability-Linked Loan (SLL) Dynamic Pricing Engine")
    
    with st.expander("📖 點此查看 HKMA SPM GS-2 計算邏輯與公式說明 (SLL Pricing & GSF Grant)"):
        st.markdown("""
        - **SLL 動態定價**：若企業符合氣候轉型 KPI（綠色 CapEx 與減碳達標），貸款利率可享 15 bps 獎勵折扣；反之若未達標或觸發 SICR，則加收 20 bps 轉型風險溢價。
        - **GSF Grant Track II**：合資格的外部審查費用可獲 75% 資助，上限為港幣 80 萬元。
        """)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="card">
            <h4>Pricing Structure Summary</h4>
            <p><b>Base Margin:</b> {base_margin_bps:.0f} bps ({base_margin_bps/100:.2f}%)</p>
            <p><b>Adjustment:</b> {pricing_adjustment:+.0f} bps</p>
            <p><b>Final Loan Margin:</b> <b>{final_margin_bps:.0f} bps ({final_margin_bps/100:.2f}%)</b></p>
            <p style="color: #334155; margin-top: 0.5rem;"><b>Status:</b> {pricing_status if 'pricing_status' in locals() else ''}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card">
            <h4>Annual Financial Impact on Borrower</h4>
            <p><b>Subject Loan Amount:</b> HKD {loan_amount_input:,.1f} M</p>
            <p><b>Annual Interest Savings / (Cost Penalty):</b></p>
            <h3 style="color: {'#16a34a' if annual_interest_impact <= 0 else '#dc2626'};">
                HKD {abs(annual_interest_impact):,.2f} {('Savings per year' if annual_interest_impact < 0 else 'Additional Cost per year' if annual_interest_impact > 0 else '')}
            </h3>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 2. HKMA Green and Sustainable Finance (GSF) Grant Scheme Track II Subsidy Calculator")
    st.markdown("Under HKMA GSF Grant Scheme Track II, eligible bond issuers and loan borrowers can apply for subsidies covering external review expenses.")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        external_review_cost_hkd = st.number_input("Estimated External Review / Second-Party Opinion Fee (HKD)", value=500000.0, step=50000.0)
    with col_g2:
        is_eligible_gsf = st.checkbox("Meets HKMA GSF Grant Scheme Eligibility Criteria", value=True)
        
    grant_reimbursement_rate = 0.75
    max_grant_cap = 800000.0
    
    calculated_grant = min(external_review_cost_hkd * grant_reimbursement_rate, max_grant_cap) if is_eligible_gsf else 0.0
    net_review_cost = external_review_cost_hkd - calculated_grant
    
    st.markdown(f"""
    <div class="card" style="background-color: #f0fdf4; border-color: #bbf7d0;">
        <h4 style="color: #166534;">HKMA GSF Grant Subsidy Breakdown</h4>
        <p><b>Total External Review Cost:</b> HKD {external_review_cost_hkd:,.2f}</p>
        <p><b>Eligible Grant Reimbursement (75% up to HKD 800K cap):</b> <b>HKD {calculated_grant:,.2f}</b></p>
        <p><b>Net Out-of-Pocket Review Expense for Borrower:</b> <b>HKD {net_review_cost:,.2f}</b></p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# TAB 3: PRACTITIONER FEEDBACK SURVEY & DASHBOARD
# ==========================================
with tab3:
    st.markdown("### 📝 Practitioner Feedback Survey & Evaluation")
    st.markdown("Please evaluate the usability, risk efficacy, and commercial feasibility of this HKMA SPM GS-2 automated underwriting dashboard for institutional banking deployment.")
    
    with st.form("feedback_form"):
        st.markdown("#### Rate the following core dimensions (1 = Poor, 5 = Excellent):")
        
        clarity_rating = st.slider(
            "1. Clarity of HKMA SPM GS-2 Guidelines & Phase 2A Taxonomy Integration",
            min_value=1, max_value=5, value=4
        )
        efficacy_rating = st.slider(
            "2. Risk Efficacy & Stress Testing Accuracy (Carbon Tax Shock & IFRS 9 Staging)",
            min_value=1, max_value=5, value=5
        )
        feasibility_rating = st.slider(
            "3. Commercial Feasibility for Corporate Underwriting & SLL Pricing",
            min_value=1, max_value=5, value=4
        )
        
        practitioner_role = st.selectbox(
            "Select Your Professional Role",
            ["Senior Credit Risk Manager", "ESG Sustainable Finance Specialist", "Corporate Relationship Manager", "RegTech / Risk Modeler", "Academic / Researcher"]
        )
        
        comments = st.text_area(
            "Qualitative Comments, Suggestions, or Custom Policy Adjustments",
            placeholder="Enter feedback regarding carbon price sensitivities, transition scenario parameters, or grant scheme integration..."
        )
        
        submitted = st.form_submit_button("Submit Practitioner Feedback")
        
        if submitted:
            new_feedback = {
                "Role": practitioner_role,
                "Clarity Rating": clarity_rating,
                "Risk Efficacy Rating": efficacy_rating,
                "Commercial Feasibility Rating": feasibility_rating,
                "Comments": comments,
                "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state.feedback_list.append(new_feedback)
            st.success("🎉 Thank you! Your practitioner evaluation has been successfully recorded for capstone analysis and validation.")
            st.balloons()

    st.markdown("---")
    st.markdown("### 📊 評審意見統計儀表板 (Feedback Dashboard)")
    if len(st.session_state.feedback_list) > 0:
        fb_df = pd.DataFrame(st.session_state.feedback_list)
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            st.metric("Total Submissions", len(fb_df))
        with col_f2:
            st.metric("Avg Clarity", f"{fb_df['Clarity Rating'].mean():.2f} / 5")
        with col_f3:
            st.metric("Avg Risk Efficacy", f"{fb_df['Risk Efficacy Rating'].mean():.2f} / 5")
        with col_f4:
            st.metric("Avg Feasibility", f"{fb_df['Commercial Feasibility Rating'].mean():.2f} / 5")
        
        st.markdown("#### 📝 歷史質化評語與明細")
        st.dataframe(fb_df, use_container_width=True)
    else:
        st.info("目前尚無提交的評審意見。請填寫上方問卷後即時解鎖統計儀表板。")
