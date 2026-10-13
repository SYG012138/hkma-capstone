from io import BytesIO

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ==========================================
# PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="stephenclimatecreditunderwritingsystem",
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


def simulate_stress_test(
    emissions: float,
    ebitda: float,
    sbti_target: float,
    green_capex: float,
    carbon_tax: float,
    debt_service: float,
    interest_expense: float,
) -> list[dict[str, float | str]]:
    is_aligned = green_capex >= 30.0 and sbti_target >= 20.0
    annual_reduction_rate = (sbti_target / 100.0) / 5.0 if is_aligned else 0.01
    results: list[dict[str, float | str]] = []
    projected_emissions = emissions

    for year in range(5):
        if year > 0:
            projected_emissions *= 1.0 - annual_reduction_rate

        carbon_cost = projected_emissions * carbon_tax * USD_HKD / 1e6
        stressed_ebitda = max(ebitda - carbon_cost, 10.0)
        dscr = stressed_ebitda / debt_service if debt_service > 0 else np.nan
        icr = stressed_ebitda / interest_expense if interest_expense > 0 else np.nan
        results.append({
            "Year": f"Year {year + 1}",
            "Emissions (tCO2e)": round(projected_emissions, 0),
            "Carbon Cost (HKD M)": round(carbon_cost, 2),
            "Stressed EBITDA (HKD M)": round(stressed_ebitda, 2),
            "DSCR (x)": dscr,
            "ICR (x)": icr,
        })
    return results


def build_credit_memo_pdf(
    company: str,
    risk_summary: pd.DataFrame,
    stress_test: pd.DataFrame,
    pricing_summary: pd.DataFrame,
    grant_summary: pd.DataFrame,
) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Credit Review Memorandum", styles["Title"]),
        Paragraph(f"Company: {company}", styles["Heading2"]),
        Paragraph(
            "Illustrative decision-support output. Validate assumptions and "
            "apply the institution's approved credit and IFRS 9 policies.",
            styles["BodyText"],
        ),
        Spacer(1, 8 * mm),
    ]

    for title, frame in (
        ("Risk Assessment", risk_summary),
        ("5-Year Stress Test", stress_test),
        ("SLL Pricing", pricing_summary),
        ("GSF Grant Estimate", grant_summary),
    ):
        story.append(Paragraph(title, styles["Heading2"]))
        values = [
            [Paragraph(str(value), styles["BodyText"]) for value in frame.columns],
            *[
                [Paragraph(str(value), styles["BodyText"]) for value in row]
                for row in frame.fillna("N/A").astype(str).values.tolist()
            ],
        ]
        available_width = A4[0] - 36 * mm
        table = Table(
            values,
            colWidths=[available_width / len(frame.columns)] * len(frame.columns),
            repeatRows=1,
            hAlign="LEFT",
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f4c81")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([table, Spacer(1, 6 * mm)])

    document.build(story)
    return buffer.getvalue()


def build_credit_memo_excel(
    risk_summary: pd.DataFrame,
    stress_test: pd.DataFrame,
    pricing_summary: pd.DataFrame,
    grant_summary: pd.DataFrame,
) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        risk_summary.to_excel(writer, sheet_name="Risk Summary", index=False)
        stress_test.to_excel(writer, sheet_name="5-Year Stress Test", index=False)
        pricing_summary.to_excel(writer, sheet_name="SLL Pricing", index=False)
        grant_summary.to_excel(writer, sheet_name="GSF Grant", index=False)
    return buffer.getvalue()


# ==========================================
# SIDEBAR - CASE SELECTOR & INPUTS
# ==========================================
st.sidebar.markdown("## ⚙️ Control Panel")
selected_company = st.sidebar.selectbox("Select Company Case", list(COMPANY_DATA.keys()))

defaults = COMPANY_DATA[selected_company]

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Financial Inputs (HKD M)")
rev_input = st.sidebar.number_input("Revenue", min_value=0.0, value=defaults["revenue"], step=100.0)
ebitda_input = st.sidebar.number_input("EBITDA", min_value=0.0, value=defaults["ebitda"], step=50.0)
total_debt_input = st.sidebar.number_input("Total Debt", min_value=0.0, value=defaults["total_debt"], step=100.0)
loan_amount_input = st.sidebar.number_input("Subject Loan Amount", min_value=0.0, value=defaults["loan_amount"], step=50.0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🌍 Climate & Transition Inputs")
emissions_input = st.sidebar.number_input("Scope 1 & 2 Emissions (tCO2e)", min_value=0.0, value=defaults["emissions"], step=10000.0)
sbti_input = st.sidebar.slider("SBTi 5-Year Reduction Target (%)", 0.0, 60.0, defaults["sbti_target"], 1.0)
green_capex_input = st.sidebar.slider("Green CapEx Ratio (%)", 0.0, 100.0, defaults["green_capex"], 1.0)
carbon_tax_input = st.sidebar.slider("Carbon Tax Shock Scenario (USD/ton)", 0.0, 200.0, defaults["carbon_tax"], 5.0)

USD_HKD = 7.8

# ==========================================
# MAIN TITLE & OVERVIEW
# ==========================================
st.markdown('<p class="main-header">🏦 Stephen Climate Credit Underwriting System</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Corporate Transition Framework under HKMA SPM GS-2 Guidelines & IFRS 9 Staging</p>', unsafe_allow_html=True)

# ==========================================
# TABS SETUP
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📈 Risk Assessment & Stress Testing", 
    "💡 Underwriting Structuring & Subsidies", 
    "📝 Practitioner Feedback Survey"
])
st.session_state.setdefault("practitioner_feedback", [])

# ==========================================
# TAB 1: RISK ASSESSMENT & STRESS TESTING
# ==========================================
with tab1:
    st.markdown("### 1. Phase 2A Taxonomy Alignment Check")
    with st.expander("📖 View HKMA SPM GS-2 calculation methodology and formulas"):
        st.markdown(
            "This page uses green capital expenditure of at least 30% and a five-year SBTi "
            "reduction target of at least 20% as **illustrative alignment thresholds**. "
            "HKMA SPM GS-2 requires banks to assess climate risks through their governance, "
            "risk management, and scenario analysis arrangements. These dashboard thresholds "
            "are not official HKMA classifications or regulatory determinations."
        )
    
    is_capex_aligned = green_capex_input >= 30.0
    is_sbti_aligned = sbti_input >= 20.0
    is_fully_aligned = is_capex_aligned and is_sbti_aligned
    
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
    with st.expander("📖 View HKMA SPM GS-2 calculation methodology and formulas"):
        st.markdown(
            "Carbon cost (HKD million) = emissions (tCO₂e) × carbon price (USD/t) × 7.8 "
            "÷ 1,000,000. Illustrative EBITDA = max(baseline EBITDA − carbon cost, HKD 10M). "
            "When the alignment thresholds above are met, the reduction target is assumed to "
            "be spread evenly over five years; otherwise, annual emissions reduction is assumed "
            "to be 1%."
        )

    base_interest_rate = 0.06
    interest_expense = total_debt_input * base_interest_rate
    principal_repayment = loan_amount_input * 0.10
    debt_service = interest_expense + principal_repayment
    sim_data = simulate_stress_test(
        emissions_input,
        ebitda_input,
        sbti_input,
        green_capex_input,
        carbon_tax_input,
        debt_service,
        interest_expense,
    )
    df_sim = pd.DataFrame(sim_data)
    dscr_list = [value for value in df_sim["DSCR (x)"] if np.isfinite(value)]
    df_sim_display = df_sim.copy()
    df_sim_display[["DSCR (x)", "ICR (x)"]] = df_sim_display[["DSCR (x)", "ICR (x)"]].round(2)
    st.dataframe(df_sim_display, use_container_width=True)
    
    min_dscr = min(dscr_list) if dscr_list else np.nan
    sicr_triggered = (np.isfinite(min_dscr) and min_dscr < 1.25) or (not is_fully_aligned)
    staging_result = (
        "Stage 2" if sicr_triggered else
        "Stage 1" if np.isfinite(min_dscr) else
        "Indeterminate"
    )
    
    st.markdown("---")
    st.markdown("### 3. IFRS 9 Staging & SICR Trigger Assessment")
    if sicr_triggered:
        st.error(
            f"🚨 **IFRS 9 SICR TRIGGER WARNING: MIGRATION TO STAGE 2 (Lifetime ECL) REQUIRED**\n\n"
            f"Reason: {'Minimum projected DSCR (' + str(round(min_dscr, 2)) + 'x) is below the 1.25x prudential threshold' if np.isfinite(min_dscr) and min_dscr < 1.25 else ''}"
            f"{' and/or ' if (np.isfinite(min_dscr) and min_dscr < 1.25 and not is_fully_aligned) else ''}"
            f"{'Corporate Transition Plan is Non-Aligned with HKMA Phase 2A Taxonomy.' if not is_fully_aligned else ''}"
        )
    elif np.isfinite(min_dscr):
        st.success(
            "✅ **Credit Risk Standing: STAGE 1 (12-Month ECL)**\n\n"
            "The corporate borrower maintains robust forward-looking debt service coverage (DSCR ≥ 1.25x) and satisfies HKMA Phase 2A Taxonomy alignment criteria."
        )
    if not np.isfinite(min_dscr):
        st.warning("DSCR is unavailable because projected debt service is zero; interpret staging results with caution.")

    with st.expander("📖 View HKMA SPM GS-2 calculation methodology and formulas"):
        st.markdown(
            "DSCR = stressed EBITDA ÷ (total debt × 6% + subject loan amount × 10%). "
            "This prototype flags a significant increase in credit risk (SICR) when the "
            "five-year minimum DSCR is below 1.25x or the illustrative transition-alignment "
            "thresholds are not met. This is not an automated IFRS 9 staging determination; "
            "actual Stage 2 assessments must follow the bank's approved policies and use "
            "forward-looking information."
        )

    st.markdown("---")
    st.markdown("### 4. 5-Year DSCR Trend Visualization")
    if dscr_list:
        valid_dscr = df_sim.loc[np.isfinite(df_sim["DSCR (x)"])]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=valid_dscr["Year"],
            y=valid_dscr["DSCR (x)"],
            mode="lines+markers+text",
            name="Projected DSCR",
            text=[f"{val:.2f}x" for val in valid_dscr["DSCR (x)"]],
            textposition="top center",
            line=dict(color="#0284c7", width=3),
            marker=dict(size=8),
        ))
        fig.add_hline(
            y=1.25,
            line_dash="dash",
            line_color="#dc2626",
            annotation_text="Prudential Threshold (1.25x)",
            annotation_position="bottom right",
        )
        fig.update_layout(
            xaxis_title="Projection Horizon",
            yaxis_title="Debt Service Coverage Ratio (DSCR)",
            yaxis=dict(range=[0, max(max(dscr_list) + 0.5, 2.0)]),
            margin=dict(l=20, r=20, t=30, b=20),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("DSCR trend cannot be plotted because projected debt service is zero.")

    st.markdown("---")
    st.markdown("### 5. Sensitivity Analysis Matrix")
    st.caption(
        "Each cell shows the five-year minimum DSCR and the stage estimated using this "
        "page's illustrative rules; color represents DSCR."
    )
    carbon_scenarios = [0, 50, 100, 150, 200]
    capex_scenarios = [0, 20, 40, 60, 80, 100]
    heatmap_dscr = []
    heatmap_labels = []
    heatmap_stages = []
    for capex_scenario in capex_scenarios:
        row_dscr = []
        row_labels = []
        row_stages = []
        for tax_scenario in carbon_scenarios:
            scenario_results = simulate_stress_test(
                emissions_input,
                ebitda_input,
                sbti_input,
                capex_scenario,
                tax_scenario,
                debt_service,
                interest_expense,
            )
            scenario_dscrs = [
                row["DSCR (x)"] for row in scenario_results
                if np.isfinite(row["DSCR (x)"])
            ]
            scenario_min_dscr = min(scenario_dscrs) if scenario_dscrs else np.nan
            scenario_aligned = capex_scenario >= 30.0 and sbti_input >= 20.0
            scenario_stage = (
                "Stage 2" if not scenario_aligned or (
                    np.isfinite(scenario_min_dscr) and scenario_min_dscr < 1.25
                ) else "Stage 1" if np.isfinite(scenario_min_dscr) else "Indeterminate"
            )
            row_dscr.append(scenario_min_dscr)
            row_labels.append(
                f"{scenario_min_dscr:.2f}x<br>{scenario_stage}"
                if np.isfinite(scenario_min_dscr)
                else f"N/A<br>{scenario_stage}"
            )
            row_stages.append(scenario_stage)
        heatmap_dscr.append(row_dscr)
        heatmap_labels.append(row_labels)
        heatmap_stages.append(row_stages)

    heatmap = go.Figure(go.Heatmap(
        x=carbon_scenarios,
        y=capex_scenarios,
        z=heatmap_dscr,
        text=heatmap_labels,
        customdata=heatmap_stages,
        texttemplate="%{text}",
        colorscale="RdYlGn",
        zmin=0,
        zmax=2.0,
        colorbar=dict(title="Min DSCR (x)"),
        hovertemplate=(
            "Carbon tax: %{x} USD/ton<br>"
            "Green CapEx: %{y}%<br>"
            "5-year minimum DSCR: %{z:.2f}x<br>"
            "IFRS 9 staging: %{customdata}<extra></extra>"
        ),
    ))
    heatmap.update_layout(
        xaxis_title="Carbon Tax Shock Scenario (USD/ton)",
        yaxis_title="Green CapEx Ratio (%)",
        height=430,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(heatmap, use_container_width=True)
    with st.expander("📖 View HKMA SPM GS-2 calculation methodology and formulas"):
        st.markdown(
            "The sensitivity matrix recalculates the same five-year emissions, EBITDA, and "
            "DSCR model for each carbon price on the horizontal axis and green capital "
            "expenditure ratio on the vertical axis. A green capital expenditure ratio below "
            "30% or an SBTi target below 20% triggers an illustrative Stage 2 warning. "
            "Scenario results are for analysis only and are not regulatory classifications."
        )

# ==========================================
# TAB 2: UNDERWRITING STRUCTURING & SUBSIDIES
# ==========================================
with tab2:
    st.markdown("### 1. Sustainability-Linked Loan (SLL) Dynamic Pricing Engine")
    with st.expander("📖 View HKMA SPM GS-2 calculation methodology and formulas"):
        st.markdown(
            "This prototype starts with a 250 bps base margin: it applies a 15 bps discount "
            "when the alignment thresholds are met and the SBTi target is at least 25%; it "
            "applies a 20 bps premium when alignment thresholds are not met or the minimum "
            "DSCR is below 1.25x; otherwise, the base margin is unchanged. This illustrative "
            "pricing rule is not an HKMA requirement or recommended pricing formula."
        )
    
    base_margin_bps = 250.0
    
    if is_fully_aligned and sbti_input >= 25.0:
        pricing_adjustment = -15.0
        pricing_status = "🟢 Transition Incentive Discount Applied (-15 bps)"
    elif not is_fully_aligned or (np.isfinite(min_dscr) and min_dscr < 1.25):
        pricing_adjustment = 20.0
        pricing_status = "🔴 Transition Risk Premium Applied (+20 bps)"
    else:
        pricing_adjustment = 0.0
        pricing_status = "⚪ Standard Pricing (Neutral)"
        
    final_margin_bps = base_margin_bps + pricing_adjustment
    annual_interest_impact = (loan_amount_input * 1e6 * (pricing_adjustment / 10000.0))
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="card">
            <h4>Pricing Structure Summary</h4>
            <p><b>Base Margin:</b> {base_margin_bps:.0f} bps ({base_margin_bps/100:.2f}%)</p>
            <p><b>Adjustment:</b> {pricing_adjustment:+.0f} bps</p>
            <p><b>Final Loan Margin:</b> <b>{final_margin_bps:.0f} bps ({final_margin_bps/100:.2f}%)</b></p>
            <p style="color: #334155; margin-top: 0.5rem;"><b>Status:</b> {pricing_status}</p>
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
    with st.expander("📖 View HKMA SPM GS-2 calculation methodology and formulas"):
        st.markdown(
            "Illustrative grant = min(external review cost × 75%, HKD 800,000), subject to "
            "the user-selected eligibility status. Grant scheme terms, caps, and eligibility "
            "may change; confirm against the latest HKMA announcements and actual application "
            "decisions."
        )
    st.markdown("Under HKMA GSF Grant Scheme Track II, eligible bond issuers and loan borrowers can apply for subsidies covering external review expenses.")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        external_review_cost_hkd = st.number_input("Estimated External Review / Second-Party Opinion Fee (HKD)", min_value=0.0, value=500000.0, step=50000.0)
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
# TAB 3: PRACTITIONER FEEDBACK SURVEY
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
            st.session_state["practitioner_feedback"].append({
                "Role": practitioner_role,
                "Clarity Rating": clarity_rating,
                "Risk Efficacy Rating": efficacy_rating,
                "Commercial Feasibility Rating": feasibility_rating,
                "Comments": comments.strip(),
            })
            st.success("🎉 Thank you! Your practitioner evaluation has been successfully recorded for capstone analysis and validation.")
            st.balloons()
    with st.expander("📖 View HKMA SPM GS-2 calculation methodology and formulas"):
        st.markdown(
            "This survey collects feedback for the prototype. Responses are stored temporarily "
            "in the current Streamlit session's memory; they are not guaranteed to persist "
            "after the session ends and are not written to a persistent database. Do not submit "
            "personal or confidential information."
        )


if st.session_state["practitioner_feedback"]:
    feedback = pd.DataFrame(st.session_state["practitioner_feedback"])
    st.markdown("---")
    st.markdown("## 📊 Practitioner Feedback Dashboard")
    rating_columns = ["Clarity Rating", "Risk Efficacy Rating", "Commercial Feasibility Rating"]
    summary_columns = st.columns(len(rating_columns) + 1)
    summary_columns[0].metric("Responses", len(feedback))
    for column, rating in zip(summary_columns[1:], rating_columns):
        column.metric(rating, f"{feedback[rating].mean():.2f} / 5")
    comments_only = feedback.loc[feedback["Comments"].str.len() > 0, ["Role", "Comments"]]
    st.markdown("### Qualitative Comments")
    if comments_only.empty:
        st.caption("There are no written comments yet.")
    else:
        st.dataframe(comments_only, use_container_width=True, hide_index=True)


risk_summary = pd.DataFrame([{
    "Company": selected_company,
    "Revenue (HKD M)": rev_input,
    "EBITDA (HKD M)": ebitda_input,
    "Total Debt (HKD M)": total_debt_input,
    "Subject Loan Amount (HKD M)": loan_amount_input,
    "Scope 1 & 2 Emissions (tCO2e)": emissions_input,
    "Green CapEx Ratio (%)": green_capex_input,
    "SBTi 5-Year Reduction Target (%)": sbti_input,
    "Carbon Tax Scenario (USD/ton)": carbon_tax_input,
    "Minimum 5-Year DSCR (x)": min_dscr,
    "IFRS 9 Staging (Illustrative)": staging_result,
    "Taxonomy Alignment (Illustrative)": "Aligned" if is_fully_aligned else "Non-Aligned",
}])
pricing_summary = pd.DataFrame([{
    "Base Margin (bps)": base_margin_bps,
    "Pricing Adjustment (bps)": pricing_adjustment,
    "Final Margin (bps)": final_margin_bps,
    "Annual Interest Impact (HKD)": annual_interest_impact,
    "Pricing Status": pricing_status.replace("🟢 ", "").replace("🔴 ", "").replace("⚪ ", ""),
}])
grant_summary = pd.DataFrame([{
    "External Review Cost (HKD)": external_review_cost_hkd,
    "Eligibility Selected": is_eligible_gsf,
    "Grant Estimate (HKD)": calculated_grant,
    "Net Review Cost (HKD)": net_review_cost,
}])

st.sidebar.markdown("---")
st.sidebar.markdown("### 📄 Credit Memo Export")
st.sidebar.download_button(
    "Download Credit Memo (PDF)",
    data=build_credit_memo_pdf(
    selected_company, risk_summary, df_sim.round(2), pricing_summary, grant_summary
    ),
    file_name="credit_memo.pdf",
    mime="application/pdf",
    use_container_width=True,
)
st.sidebar.download_button(
    "Download Credit Memo (Excel)",
    data=build_credit_memo_excel(risk_summary, df_sim, pricing_summary, grant_summary),
    file_name="credit_memo.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
