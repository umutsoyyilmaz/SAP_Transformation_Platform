"""Seed extra Analysis Hub demo data — processes, scope items, analyses."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from app.models.scope import Process, ScopeItem, Analysis
from app.models.scenario import Scenario, Workshop
from datetime import date, datetime, timezone

app = create_app("development")

with app.app_context():
    scenarios = Scenario.query.all()
    print(f"Existing scenarios: {len(scenarios)}")

    # Grab first 3 scenarios to enrich
    if len(scenarios) < 2:
        print("Not enough scenarios. Run seed_demo_data.py first.")
        sys.exit(1)

    s1, s2, s3 = scenarios[0], scenarios[1], scenarios[2] if len(scenarios) > 2 else scenarios[1]

    # Get existing workshop IDs for linking
    ws1 = Workshop.query.filter_by(scenario_id=s1.id).first()
    ws2 = Workshop.query.filter_by(scenario_id=s2.id).first()

    # ── Additional Processes for Scenario 1 (O2C) ──────────────────────
    existing_procs = Process.query.filter_by(scenario_id=s1.id).count()
    new_items_count = 0
    new_analyses_count = 0

    if existing_procs >= 5:
        print(f"  Scenario 1 already has {existing_procs} procs — skipping process creation")
    else:
        # L1: Order to Cash
        l1_o2c = Process(scenario_id=s1.id, name="Order to Cash", level="L1",
                         process_id_code="O2C", module="SD", order=1)
        db.session.add(l1_o2c)
        db.session.flush()

        # L2 under O2C
        l2_sales = Process(scenario_id=s1.id, parent_id=l1_o2c.id,
                           name="Standard Sales Order", level="L2",
                           process_id_code="O2C-010", module="SD", order=1)
        l2_returns = Process(scenario_id=s1.id, parent_id=l1_o2c.id,
                             name="Returns Processing", level="L2",
                             process_id_code="O2C-020", module="SD", order=2)
        l2_billing = Process(scenario_id=s1.id, parent_id=l1_o2c.id,
                             name="Billing & Invoicing", level="L2",
                             process_id_code="O2C-030", module="SD", order=3)
        db.session.add_all([l2_sales, l2_returns, l2_billing])
        db.session.flush()

        # L3 under Standard Sales Order
        l3_credit = Process(scenario_id=s1.id, parent_id=l2_sales.id,
                            name="Credit Check", level="L3",
                            process_id_code="O2C-010-01", module="SD", order=1)
        l3_pricing = Process(scenario_id=s1.id, parent_id=l2_sales.id,
                             name="Pricing Determination", level="L3",
                             process_id_code="O2C-010-02", module="SD", order=2)
        l3_atp = Process(scenario_id=s1.id, parent_id=l2_sales.id,
                         name="Availability Check (ATP)", level="L3",
                         process_id_code="O2C-010-03", module="SD", order=3)
        db.session.add_all([l3_credit, l3_pricing, l3_atp])
        db.session.flush()

        # Scope Items under L2 Standard Sales Order
        si_list = [
            ScopeItem(process_id=l2_sales.id, code="1YG", name="Domestic Sales",
                      sap_reference="BP-SD-001", status="in_scope", priority="high", module="SD"),
            ScopeItem(process_id=l2_sales.id, code="2OC", name="Cross-Company Sales",
                      sap_reference="BP-SD-002", status="in_scope", priority="high", module="SD"),
            ScopeItem(process_id=l2_sales.id, code="BD9", name="Intercompany Billing",
                      sap_reference="BP-SD-003", status="in_scope", priority="medium", module="SD"),
            ScopeItem(process_id=l2_returns.id, code="1NS", name="Customer Returns",
                      sap_reference="BP-SD-010", status="in_scope", priority="high", module="SD"),
            ScopeItem(process_id=l2_returns.id, code="2RR", name="Return Refund Processing",
                      sap_reference="BP-SD-011", status="deferred", priority="low", module="SD"),
            ScopeItem(process_id=l2_billing.id, code="J56", name="Milestone Billing",
                      sap_reference="BP-SD-020", status="in_scope", priority="medium", module="SD"),
            ScopeItem(process_id=l2_billing.id, code="J57", name="Periodic Billing",
                      sap_reference="BP-SD-021", status="in_scope", priority="medium", module="SD"),
        ]
        db.session.add_all(si_list)
        db.session.flush()
        new_items_count += len(si_list)

        # Analyses for scope items
        an_list = [
            Analysis(scope_item_id=si_list[0].id, name="SD Fit-Gap Workshop #1",
                     analysis_type="fit_gap", status="completed", fit_gap_result="fit",
                     decision="Standard SAP functionality sufficient",
                     attendees="Ahmet Yilmaz, Mehmet Kaya", date=date(2026, 1, 15),
                     workshop_id=ws1.id if ws1 else None),
            Analysis(scope_item_id=si_list[1].id, name="Cross-Company Analysis",
                     analysis_type="fit_gap", status="completed", fit_gap_result="partial_fit",
                     decision="Config required for cross-company pricing rules",
                     attendees="Ahmet Yilmaz, Ayse Demir", date=date(2026, 1, 18),
                     workshop_id=ws1.id if ws1 else None),
            Analysis(scope_item_id=si_list[2].id, name="Intercompany Billing Review",
                     analysis_type="fit_gap", status="completed", fit_gap_result="gap",
                     decision="Custom development needed for Turkish tax integration",
                     attendees="Ahmet Yilmaz, Finance Team", date=date(2026, 1, 20),
                     workshop_id=ws1.id if ws1 else None),
            Analysis(scope_item_id=si_list[3].id, name="Returns Fit-Gap",
                     analysis_type="fit_gap", status="completed", fit_gap_result="fit",
                     decision="Standard returns processing OK",
                     attendees="Mehmet Kaya", date=date(2026, 1, 22)),
            Analysis(scope_item_id=si_list[5].id, name="Milestone Billing Analysis",
                     analysis_type="workshop", status="in_progress",
                     attendees="Billing Team", date=date(2026, 2, 5)),
            Analysis(scope_item_id=si_list[6].id, name="Periodic Billing Review",
                     analysis_type="review", status="planned",
                     date=date(2026, 2, 15)),
        ]
        db.session.add_all(an_list)
        new_analyses_count += len(an_list)

        print(f"  ✅ Scenario 1 enriched: +7 processes, +{len(si_list)} scope items, +{len(an_list)} analyses")

    # ── Additional Processes for Scenario 2 (P2P / MM) ────────────────────
    existing_procs2 = Process.query.filter_by(scenario_id=s2.id).count()
    existing_si2 = db.session.query(ScopeItem).join(Process).filter(Process.scenario_id == s2.id).count()
    if existing_procs2 >= 4 or existing_si2 >= 4:
        print(f"  Scenario 2 already has {existing_procs2} procs — skipping")
    else:
        l1_p2p = Process(scenario_id=s2.id, name="Procure to Pay", level="L1",
                         process_id_code="P2P", module="MM", order=1)
        db.session.add(l1_p2p)
        db.session.flush()

        l2_pr = Process(scenario_id=s2.id, parent_id=l1_p2p.id,
                        name="Purchase Requisition", level="L2",
                        process_id_code="P2P-010", module="MM", order=1)
        l2_po = Process(scenario_id=s2.id, parent_id=l1_p2p.id,
                        name="Purchase Order Processing", level="L2",
                        process_id_code="P2P-020", module="MM", order=2)
        l2_gr = Process(scenario_id=s2.id, parent_id=l1_p2p.id,
                        name="Goods Receipt & Invoice", level="L2",
                        process_id_code="P2P-030", module="MM", order=3)
        db.session.add_all([l2_pr, l2_po, l2_gr])
        db.session.flush()

        si_mm = [
            ScopeItem(process_id=l2_pr.id, code="1NN", name="Direct Procurement",
                      sap_reference="BP-MM-001", status="in_scope", priority="high", module="MM"),
            ScopeItem(process_id=l2_pr.id, code="2LD", name="Subcontracting",
                      sap_reference="BP-MM-002", status="in_scope", priority="medium", module="MM"),
            ScopeItem(process_id=l2_po.id, code="3MM", name="Framework Orders",
                      sap_reference="BP-MM-010", status="in_scope", priority="medium", module="MM"),
            ScopeItem(process_id=l2_po.id, code="4PO", name="Service Procurement",
                      sap_reference="BP-MM-011", status="in_scope", priority="high", module="MM"),
            ScopeItem(process_id=l2_gr.id, code="5GR", name="3-Way Matching",
                      sap_reference="BP-MM-020", status="in_scope", priority="high", module="MM"),
            ScopeItem(process_id=l2_gr.id, code="6IV", name="Evaluated Receipt Settlement",
                      sap_reference="BP-MM-021", status="deferred", priority="low", module="MM"),
        ]
        db.session.add_all(si_mm)
        db.session.flush()
        new_items_count += len(si_mm)

        an_mm = [
            Analysis(scope_item_id=si_mm[0].id, name="Direct Procurement Fit-Gap",
                     analysis_type="fit_gap", status="completed", fit_gap_result="fit",
                     decision="Standard functionality sufficient",
                     attendees="MM Team", date=date(2026, 1, 25),
                     workshop_id=ws2.id if ws2 else None),
            Analysis(scope_item_id=si_mm[1].id, name="Subcontracting Analysis",
                     analysis_type="fit_gap", status="completed", fit_gap_result="partial_fit",
                     decision="Additional config for subcontracting stock management",
                     attendees="MM Team, Production", date=date(2026, 1, 28),
                     workshop_id=ws2.id if ws2 else None),
            Analysis(scope_item_id=si_mm[2].id, name="Framework Orders Review",
                     analysis_type="review", status="planned",
                     date=date(2026, 2, 10)),
            Analysis(scope_item_id=si_mm[4].id, name="3-Way Matching Demo",
                     analysis_type="demo", status="completed", fit_gap_result="fit",
                     decision="Standard 3-way matching meets requirement",
                     attendees="Finance, MM Team", date=date(2026, 2, 1)),
        ]
        db.session.add_all(an_mm)
        new_analyses_count += len(an_mm)

        print(f"  ✅ Scenario 2 enriched: +4 processes, +{len(si_mm)} scope items, +{len(an_mm)} analyses")

    # ── Additional Processes for Scenario 3 (R2R / FI) ────────────────────
    existing_procs3 = Process.query.filter_by(scenario_id=s3.id).count()
    if existing_procs3 >= 3:
        print(f"  Scenario 3 already has {existing_procs3} procs — skipping")
    else:
        l1_r2r = Process(scenario_id=s3.id, name="Record to Report", level="L1",
                         process_id_code="R2R", module="FI", order=1)
        db.session.add(l1_r2r)
        db.session.flush()

        l2_gl = Process(scenario_id=s3.id, parent_id=l1_r2r.id,
                        name="General Ledger Accounting", level="L2",
                        process_id_code="R2R-010", module="FI", order=1)
        l2_ap = Process(scenario_id=s3.id, parent_id=l1_r2r.id,
                        name="Accounts Payable", level="L2",
                        process_id_code="R2R-020", module="FI", order=2)
        l2_ar = Process(scenario_id=s3.id, parent_id=l1_r2r.id,
                        name="Accounts Receivable", level="L2",
                        process_id_code="R2R-030", module="FI", order=3)
        db.session.add_all([l2_gl, l2_ap, l2_ar])
        db.session.flush()

        si_fi = [
            ScopeItem(process_id=l2_gl.id, code="J78", name="Parallel Accounting",
                      sap_reference="BP-FI-001", status="in_scope", priority="high", module="FI"),
            ScopeItem(process_id=l2_gl.id, code="J79", name="Intercompany Accounting",
                      sap_reference="BP-FI-002", status="in_scope", priority="high", module="FI"),
            ScopeItem(process_id=l2_ap.id, code="K01", name="Vendor Invoice Processing",
                      sap_reference="BP-FI-010", status="in_scope", priority="high", module="FI"),
            ScopeItem(process_id=l2_ar.id, code="K10", name="Customer Payment Processing",
                      sap_reference="BP-FI-020", status="in_scope", priority="medium", module="FI"),
            ScopeItem(process_id=l2_ar.id, code="K11", name="Dunning",
                      sap_reference="BP-FI-021", status="in_scope", priority="low", module="FI"),
        ]
        db.session.add_all(si_fi)
        db.session.flush()
        new_items_count += len(si_fi)

        an_fi = [
            Analysis(scope_item_id=si_fi[0].id, name="Parallel Accounting Fit-Gap",
                     analysis_type="fit_gap", status="completed", fit_gap_result="partial_fit",
                     decision="IFRS 16 parallel ledger config needed",
                     attendees="Finance Team, Consultants", date=date(2026, 2, 3)),
            Analysis(scope_item_id=si_fi[2].id, name="Vendor Invoice Demo",
                     analysis_type="demo", status="completed", fit_gap_result="fit",
                     attendees="AP Team", date=date(2026, 2, 5)),
        ]
        db.session.add_all(an_fi)
        new_analyses_count += len(an_fi)

        print(f"  ✅ Scenario 3 enriched: +4 processes, +{len(si_fi)} scope items, +{len(an_fi)} analyses")

    db.session.commit()
    print(f"\n🎉 Analysis Hub seed complete: +{new_items_count} scope items, +{new_analyses_count} analyses")

    # Final counts
    total_procs = Process.query.count()
    total_si = ScopeItem.query.count()
    total_an = Analysis.query.count()
    total_ws = Workshop.query.count()
    print(f"   Total processes: {total_procs}")
    print(f"   Total scope items: {total_si}")
    print(f"   Total analyses: {total_an}")
    print(f"   Total workshops: {total_ws}")
