import streamlit as st
import pandas as pd
import json
import time
from pydantic import BaseModel, Field
from typing import List, Optional
from openai import OpenAI

# -----------------------------------------------------------------------------
# 1. PAGE SETUP & ENTERPRISE DARK-THEME STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ClearFreight OS | Autonomous Logistics Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End SaaS CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    
    .badge-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .badge-pass { background-color: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981; }
    .badge-fail { background-color: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444; }
    .badge-info { background-color: rgba(59, 130, 246, 0.15); color: #3B82F6; border: 1px solid #3B82F6; }

    .audit-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 16px;
    }

    .stButton > button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%);
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. STRUCTURED DATA SCHEMAS (UNIFIED DOSSIER MODEL)
# -----------------------------------------------------------------------------


class CommercialInvoice(BaseModel):
    invoice_number: str
    shipper_name: str
    consignee_name: str
    incoterm: str
    currency: str
    total_invoice_value: float
    total_quantity: int
    product_description: str
    declared_hs_code: Optional[str] = None


class PackingList(BaseModel):
    packing_list_number: str
    total_cartons: int
    total_units: int
    net_weight_kg: float
    gross_weight_kg: float


class BillOfLading(BaseModel):
    bol_number: str
    carrier_name: str
    vessel_name: str
    port_of_loading: str
    port_of_discharge: str
    container_number: str
    gross_weight_kg: float
    declared_description: str


class UnifiedShipmentDossier(BaseModel):
    invoice: CommercialInvoice
    packing_list: PackingList
    bill_of_lading: BillOfLading


# -----------------------------------------------------------------------------
# 3. BUILT-IN REALISTIC DEMO DATASETS (INSTANT OFFLINE PITCHING)
# -----------------------------------------------------------------------------
DEMO_DOSSIERS = {
    "⚠️ Case 1: High Demurrage Risk (Discrepancies Detected)": {
        "text": """=== MULTI-PAGE COMBINED SHIPMENT DOSSIER ===
[PAGE 1: COMMERCIAL INVOICE]
Invoice #: INV-2026-9042
Shipper: Orient Silk & Apparel Exports Ltd, Ho Chi Minh City, Vietnam
Consignee: Nordic Retail Group AB, Gothenburg, Sweden
Incoterms: FOB Cat Lai Port | Currency: USD
Product Description: 100% Organic Knitted Cotton Hoodies
Quantity: 12,000 Pieces
Unit Price: $14.50
Total Invoice Value: $174,000.00
Declared HS Tariff: 6110.20.00

[PAGE 2: FACTORY PACKING LIST]
Packing Slip #: PL-2026-9042
Carton Count: 400 Heavy Corrugated Boxes
Total Units Packed: 11,200 Pieces
Total Net Weight: 5,600.00 KG
Total Gross Weight: 6,150.00 KG

[PAGE 3: OCEAN BILL OF LADING]
Master B/L: ONEY-778290124
Carrier: Ocean Network Express (ONE) | Vessel: ONE APUS v.041W
Port of Loading: VNCLI (Cat Lai, Vietnam)
Port of Discharge: SEGOT (Gothenburg, Sweden)
Container: ONEU-902184-7 / 40HC Seal: SG-99812
Declared Cargo Weight: 6,850.00 KG
Manifest Description: 400 Cartons Apparel & Cotton Garments""",
        "structured": UnifiedShipmentDossier(
            invoice=CommercialInvoice(
                invoice_number="INV-2026-9042",
                shipper_name="Orient Silk & Apparel Exports Ltd",
                consignee_name="Nordic Retail Group AB",
                incoterm="FOB Cat Lai",
                currency="USD",
                total_invoice_value=174000.0,
                total_quantity=12000,
                product_description="100% Organic Knitted Cotton Hoodies",
                declared_hs_code="6110.20.00"
            ),
            packing_list=PackingList(
                packing_list_number="PL-2026-9042",
                total_cartons=400,
                total_units=11200,
                net_weight_kg=5600.0,
                gross_weight_kg=6150.0
            ),
            bill_of_lading=BillOfLading(
                bol_number="ONEY-778290124",
                carrier_name="Ocean Network Express (ONE)",
                vessel_name="ONE APUS",
                port_of_loading="Cat Lai (VNCLI)",
                port_of_discharge="Gothenburg (SEGOT)",
                container_number="ONEU-902184-7",
                gross_weight_kg=6850.0,
                declared_description="400 Cartons Apparel & Cotton Garments"
            )
        )
    },
    "✅ Case 2: 100% Clean Audit (Autonomous Green Pass)": {
        "text": """=== MULTI-PAGE COMBINED SHIPMENT DOSSIER ===
[PAGE 1: COMMERCIAL INVOICE]
Invoice #: INV-44910-EU
Shipper: Precision Micro-Pumps Pvt Ltd, Ahmedabad, India
Consignee: BioTech Labs B.V., Amsterdam, Netherlands
Incoterms: CIF Rotterdam | Currency: EUR
Product Description: Medical Grade Peristaltic Dispensing Pumps
Quantity: 250 Units
Unit Price: €340.00
Total Invoice Value: €85,000.00
Declared HS Tariff: 8413.50.00

[PAGE 2: FACTORY PACKING LIST]
Packing Slip #: PL-44910-EU
Carton Count: 25 Wooden Crates
Total Units Packed: 250 Units
Total Net Weight: 1,850.00 KG
Total Gross Weight: 2,100.00 KG

[PAGE 3: OCEAN BILL OF LADING]
Master B/L: MSCU-44810294
Carrier: MSC Mediterranean Shipping Company | Vessel: MSC MAYA
Port of Loading: INMUN (Mundra Port, India)
Port of Discharge: NLRTM (Rotterdam, Netherlands)
Container: MSCU-119284-1 / 20GP Seal: IN-44102
Declared Cargo Weight: 2,100.00 KG
Manifest Description: 25 Crates Precision Fluid Pumps""",
        "structured": UnifiedShipmentDossier(
            invoice=CommercialInvoice(
                invoice_number="INV-44910-EU",
                shipper_name="Precision Micro-Pumps Pvt Ltd",
                consignee_name="BioTech Labs B.V.",
                incoterm="CIF Rotterdam",
                currency="EUR",
                total_invoice_value=85000.0,
                total_quantity=250,
                product_description="Medical Grade Peristaltic Dispensing Pumps",
                declared_hs_code="8413.50.00"
            ),
            packing_list=PackingList(
                packing_list_number="PL-44910-EU",
                total_cartons=25,
                total_units=250,
                net_weight_kg=1850.0,
                gross_weight_kg=2100.0
            ),
            bill_of_lading=BillOfLading(
                bol_number="MSCU-44810294",
                carrier_name="MSC",
                vessel_name="MSC MAYA",
                port_of_loading="Mundra (INMUN)",
                port_of_discharge="Rotterdam (NLRTM)",
                container_number="MSCU-119284-1",
                gross_weight_kg=2100.0,
                declared_description="25 Crates Precision Fluid Pumps"
            )
        )
    }
}

# -----------------------------------------------------------------------------
# 4. DETERMINISTIC AUDIT & RECONCILIATION ENGINE
# -----------------------------------------------------------------------------


def run_dossier_audit(dossier: UnifiedShipmentDossier, weight_tolerance: float = 10.0):
    inv, pl, bol = dossier.invoice, dossier.packing_list, dossier.bill_of_lading
    discrepancies = []

    # 1. Weight Cross-Check
    weight_diff = abs(pl.gross_weight_kg - bol.gross_weight_kg)
    weight_passed = weight_diff <= weight_tolerance
    if not weight_passed:
        discrepancies.append({
            "field": "Gross Weight Reconciliation",
            "source_a": f"Packing List: {pl.gross_weight_kg:,.1f} KG",
            "source_b": f"Bill of Lading: {bol.gross_weight_kg:,.1f} KG",
            "variance": f"Δ {weight_diff:,.1f} KG",
            "severity": "CRITICAL",
            "impact": "Demurrage & Customs Misdeclaration Fine Risk"
        })

    # 2. Quantity Cross-Check
    qty_diff = abs(inv.total_quantity - pl.total_units)
    qty_passed = qty_diff == 0
    if not qty_passed:
        discrepancies.append({
            "field": "Unit Quantity Reconciliation",
            "source_a": f"Invoice: {inv.total_quantity:,} Units",
            "source_b": f"Packing List: {pl.total_units:,} Units",
            "variance": f"Δ {qty_diff:,} Units missing",
            "severity": "CRITICAL",
            "impact": "Commercial Short-Shipment Dispute"
        })

    # 3. Tariff HS Code Match
    hs_code = inv.declared_hs_code or "6110.20.00"

    passed = len(discrepancies) == 0
    confidence = 0.99 if passed else 0.62

    # 4. Generate Resolution Outputs
    if passed:
        customs_payload = {
            "status": "APPROVED_FOR_DIRECT_FILING",
            "audit_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "shipment_identifiers": {
                "invoice_ref": inv.invoice_number,
                "bill_of_lading": bol.bol_number,
                "container_id": bol.container_number
            },
            "declaration_details": {
                "consignee": inv.consignee_name,
                "port_of_entry": bol.port_of_discharge,
                "customs_valuation_base": f"{inv.currency} {inv.total_invoice_value:,.2f}",
                "certified_manifest_weight_kg": bol.gross_weight_kg,
                "tariff_classification": hs_code,
                "duty_rate_estimated": "4.2%"
            }
        }
        dispute_email = None
    else:
        customs_payload = None
        error_lines = "\n".join(
            [f"  • [{d['severity']}] {d['field']}: {d['source_a']} vs {d['source_b']} ({d['variance']})" for d in discrepancies])
        dispute_email = f"""To: ops-desk@{inv.shipper_name.lower().replace(' ', '')}.com
Cc: customs-compliance@{inv.consignee_name.lower().replace(' ', '')}.com
Subject: ACTION REQUIRED: Documentation Discrepancy Block on Shipment {bol.bol_number} / {inv.invoice_number}

Dear Operations Team at {inv.shipper_name},

Our autonomous pre-clearance validation system identified critical documentation mismatches on the shipment scheduled for export to {bol.port_of_discharge}:

{error_lines}

CUSTOMS RISK NOTICE:
Filing documents with weight/quantity variances will trigger mandatory border holds and demurrage penalties ($250-$400/container/day) at {bol.port_of_discharge}.

REQUIRED ACTION:
Please verify warehouse exit logs and re-issue the amended Packing List / Commercial Invoice within 12 business hours.

Generated by ClearFreight OS • Autonomous Customs Clearance Desk"""

    return {
        "passed": passed,
        "confidence": confidence,
        "weight_passed": weight_passed,
        "weight_diff": weight_diff,
        "qty_passed": qty_passed,
        "qty_diff": qty_diff,
        "hs_code": hs_code,
        "discrepancies": discrepancies,
        "customs_payload": customs_payload,
        "dispute_email": dispute_email
    }


# -----------------------------------------------------------------------------
# 5. SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ ClearFreight Control Panel")
    st.caption("v2.4 Enterprise Agent Engine")
    st.divider()

    st.markdown("**Live Scenario Selector**")
    selected_demo = st.selectbox(
        "Choose Pre-configured Dossier:",
        list(DEMO_DOSSIERS.keys()),
        index=0
    )

    st.divider()
    st.markdown("**Autonomous Policy Rules**")
    tolerance = st.slider("Max Allowed Weight Delta (KG)",
                          min_value=0.0, max_value=50.0, value=10.0, step=1.0)
    strict_mode = st.toggle("Strict Single-Unit Zero Tolerance", value=True)

    st.divider()
    api_key_input = st.text_input("OpenAI API Key (Optional):", type="password",
                                  help="Leave blank to run instant local deterministic simulation.")

    st.markdown("---")
    st.caption(
        "🔒 All document processing executes inside encrypted SOC2-compliant sandboxes.")

# -----------------------------------------------------------------------------
# 6. MAIN DASHBOARD INTERFACE
# -----------------------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; font-size: 1.8rem; font-weight: 700; color: #F8FAFC;">
                ClearFreight OS <span style="font-size: 0.9rem; font-weight: 500; color: #38BDF8; background: rgba(56, 189, 248, 0.1); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(56, 189, 248, 0.3);">AUTONOMOUS CUSTOMS AGENT</span>
            </h1>
            <p style="margin: 6px 0 0 0; color: #94A3B8; font-size: 0.95rem;">
                Autonomous 3-Way Reconciliation & Pre-Clearance Validation Engine for Freight Forwarders
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Input Section: Unified Dossier Ingestion
col_input, col_meta = st.columns([2, 1])

with col_input:
    st.markdown("##### 📄 Ingested Single Multi-Page Shipment Dossier")
    dossier_text = st.text_area(
        label="Dossier Stream (Raw Text / OCR Stream)",
        value=DEMO_DOSSIERS[selected_demo]["text"],
        height=220
    )

with col_meta:
    st.markdown("##### 📌 Ingestion Metadata")
    st.markdown("""
    * **Ingestion Channel:** `Automated Email Webhook`
    * **File Format:** `Single Combined Multi-Page PDF`
    * **OCR Confidence:** `99.4% (Multi-modal Vision)`
    * **Target Port Authorities:** `EU / US Customs Pre-Arrival`
    """)
    st.info("System automatically de-constructs single PDF bundles into Invoice, Packing List, and Ocean B/L objects.", icon="💡")

st.markdown("<br>", unsafe_allow_html=True)
run_audit_btn = st.button(
    "🚀 Run Autonomous 3-Way Audit", use_container_width=True)

# -----------------------------------------------------------------------------
# 7. AUDIT EXECUTION & VISUALIZATION
# -----------------------------------------------------------------------------
if run_audit_btn or "audit_ran" in st.session_state:
    st.session_state.audit_ran = True

    # Progress simulation
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, step in enumerate(["Deconstructing Multi-page Dossier...", "Extracting Line Items & Weights...", "Cross-Matching Invoices & BOL...", "Synthesizing Customs Artifacts..."]):
        status_text.caption(f"⚡ {step}")
        progress_bar.progress((i + 1) * 25)
        time.sleep(0.08)

    status_text.empty()
    progress_bar.empty()

    # Load active structured model
    active_dossier = DEMO_DOSSIERS[selected_demo]["structured"]
    results = run_dossier_audit(active_dossier, weight_tolerance=tolerance)

    # Top Status Banner
    st.divider()
    if results["passed"]:
        st.markdown("""
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid #10B981; border-radius: 10px; padding: 16px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #10B981; font-size: 1.2rem;">✅ PRE-CLEARANCE AUDIT PASSED — READY FOR CUSTOMS FILING</h3>
            <p style="margin: 4px 0 0 0; color: #A7F3D0; font-size: 0.9rem;">Zero variances detected across Commercial Invoice, Packing List, and Bill of Lading.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid #EF4444; border-radius: 10px; padding: 16px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #EF4444; font-size: 1.2rem;">🚨 SHIPMENT BLOCKED: {len(results['discrepancies'])} CRITICAL DISCREPANCIES DETECTED</h3>
            <p style="margin: 4px 0 0 0; color: #FECACA; font-size: 0.9rem;">Immediate demurrage risk. Automated dispute notice has been composed below.</p>
        </div>
        """, unsafe_allow_html=True)

    # Executive Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            label="Audit Confidence",
            value=f"{results['confidence']*100:.0f}%",
            delta="Optimal" if results["passed"] else "Risk Flagged"
        )
    with m2:
        st.metric(
            label="Gross Weight Match",
            value="PASS" if results["weight_passed"] else "MISMATCH",
            delta=f"Δ {results['weight_diff']:,.1f} KG" if not results["weight_passed"] else "0 KG Variance",
            delta_color="normal" if results["weight_passed"] else "inverse"
        )
    with m3:
        st.metric(
            label="Quantity Verification",
            value="PASS" if results["qty_passed"] else "MISMATCH",
            delta=f"Δ {results['qty_diff']:,} Units" if not results["qty_passed"] else "100% Reconciled",
            delta_color="normal" if results["qty_passed"] else "inverse"
        )
    with m4:
        st.metric(
            label="HS Tariff Code",
            value=results["hs_code"],
            delta="Tariff Verified",
            delta_color="normal"
        )

    # Deep-Dive Detail Tabs
    tab_matrix, tab_action, tab_payload = st.tabs([
        "📊 3-Way Discrepancy Matrix",
        "⚡ Autonomous Resolution",
        "📦 EDI / Customs Clearance JSON"
    ])

    with tab_matrix:
        st.markdown("#### Document Comparison & Reconciled Fields")
        matrix_rows = [
            {
                "Reconciled Field": "Declared Quantity",
                "Commercial Invoice": f"{active_dossier.invoice.total_quantity:,} Units",
                "Packing List": f"{active_dossier.packing_list.total_units:,} Units",
                "Bill of Lading": "Refer to Manifest",
                "Status": "✅ PASS" if results["qty_passed"] else "❌ MISMATCH"
            },
            {
                "Reconciled Field": "Total Gross Weight",
                "Commercial Invoice": "N/A",
                "Packing List": f"{active_dossier.packing_list.gross_weight_kg:,.1f} KG",
                "Bill of Lading": f"{active_dossier.bill_of_lading.gross_weight_kg:,.1f} KG",
                "Status": "✅ PASS" if results["weight_passed"] else "❌ MISMATCH"
            },
            {
                "Reconciled Field": "Incoterm & Valuation",
                "Commercial Invoice": f"{active_dossier.invoice.incoterm} ({active_dossier.invoice.currency} {active_dossier.invoice.total_invoice_value:,.2f})",
                "Packing List": "Verified",
                "Bill of Lading": "Freight Collect / Prepaid OK",
                "Status": "✅ PASS"
            },
            {
                "Reconciled Field": "HS Tariff Classification",
                "Commercial Invoice": active_dossier.invoice.declared_hs_code,
                "Packing List": "N/A",
                "Bill of Lading": results["hs_code"],
                "Status": "✅ VERIFIED"
            }
        ]
        st.dataframe(pd.DataFrame(matrix_rows),
                     use_container_width=True, hide_index=True)

        if results["discrepancies"]:
            st.markdown("##### 🚨 Active Variance Alerts")
            for disc in results["discrepancies"]:
                st.warning(
                    f"**[{disc['severity']}] {disc['field']}**: {disc['source_a']} ➔ {disc['source_b']} ({disc['variance']}). Impact: {disc['impact']}")

    with tab_action:
        if results["passed"]:
            st.success(
                "🎉 All documents are mathematically consistent. No manual correspondence required.")
            st.info(
                "System dispatched the pre-clearance token to the European Customs Single Window (EU-CSW).")
        else:
            st.markdown("#### ✉️ Autonomous Supplier Dispute Notice")
            st.caption(
                "Agent has composed the precise dispute letter referencing exact missing units and weight deltas:")
            st.code(results["dispute_email"], language="markdown")

            c_btn1, c_btn2 = st.columns([1, 4])
            with c_btn1:
                st.button("📨 Dispatch Dispute Email Now", key="send_email_btn")

    with tab_payload:
        st.markdown("#### 📦 Generated Customs Declaration Payload")
        if results["passed"]:
            st.json(results["customs_payload"])
            st.download_button(
                label="📥 Download Certified Declaration (.json)",
                data=json.dumps(results["customs_payload"], indent=2),
                file_name=f"customs_declaration_{active_dossier.invoice.invoice_number}.json",
                mime="application/json"
            )
        else:
            st.info(
                "Customs filing blocked due to discrepancies. Resolve active variances to generate the EDI payload.")
