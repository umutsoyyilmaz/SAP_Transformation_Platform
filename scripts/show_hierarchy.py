"""Show the full entity hierarchy."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from app.models.scope import Process, ScopeItem, Analysis
from app.models.scenario import Scenario
from app.models.requirement import Requirement

app = create_app('development')
with app.app_context():
    for sc in Scenario.query.order_by(Scenario.id).all():
        roots = Process.query.filter_by(scenario_id=sc.id, parent_id=None).all()
        print(f"\nScenario [{sc.id}] {sc.name} (module={sc.sap_module})")
        for l1 in roots:
            print(f"  L1 [{l1.id}] {l1.name}")
            for l2 in Process.query.filter_by(parent_id=l1.id).order_by(Process.order).all():
                si_count = ScopeItem.query.filter_by(process_id=l2.id).count()
                print(f"    L2 [{l2.id}] {l2.name} -- {si_count} scope items")
                for si in ScopeItem.query.filter_by(process_id=l2.id).all():
                    an_count = si.analyses.count()
                    req_info = f"-> REQ#{si.requirement_id}" if si.requirement_id else "(unlinked)"
                    print(f"      SI [{si.id}] {si.code} {si.name} [{si.status}] {req_info} -- {an_count} analyses")
                for l3 in Process.query.filter_by(parent_id=l2.id).order_by(Process.order).all():
                    si3_count = ScopeItem.query.filter_by(process_id=l3.id).count()
                    print(f"      L3 [{l3.id}] {l3.name} -- {si3_count} scope items")
                    for si3 in ScopeItem.query.filter_by(process_id=l3.id).all():
                        an3 = si3.analyses.count()
                        req3 = f"-> REQ#{si3.requirement_id}" if si3.requirement_id else "(unlinked)"
                        print(f"        SI [{si3.id}] {si3.code} {si3.name} [{si3.status}] {req3} -- {an3} analyses")

    print(f"\n--- Totals ---")
    print(f"Scenarios: {Scenario.query.count()}")
    print(f"Processes: {Process.query.count()} (L1={Process.query.filter_by(level='L1').count()}, L2={Process.query.filter_by(level='L2').count()}, L3={Process.query.filter_by(level='L3').count()})")
    print(f"ScopeItems: {ScopeItem.query.count()} (linked to req={ScopeItem.query.filter(ScopeItem.requirement_id.isnot(None)).count()})")
    print(f"Analyses: {Analysis.query.count()}")
    print(f"Requirements: {Requirement.query.count()}")
