#!/usr/bin/env python3
"""Quick verification of seeded data."""
import sys
sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.program import Program
from app.models.scenario import Scenario
from app.models.scope import Process
from app.models.requirement import Requirement
from app.models.backlog import BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec, Sprint
from app.models.testing import TestPlan, TestCycle, TestCase, TestExecution, Defect
from app.models.raid import Risk, Action, Issue, Decision

app = create_app()
with app.app_context():
    print("=== VERI DOGRULAMA ===")
    p = Program.query.first()
    print(f"Program: {p.name}")
    print(f"Scenarios: {Scenario.query.count()}")
    l2 = Process.query.filter_by(level="L2").count()
    l3 = Process.query.filter_by(level="L3").count()
    l4 = Process.query.filter_by(level="L4").count()
    print(f"Processes: {Process.query.count()} (L2={l2}, L3={l3}, L4={l4})")
    print(f"Requirements: {Requirement.query.count()}")
    print(f"Sprints: {Sprint.query.count()}")
    print(f"Backlog Items: {BacklogItem.query.count()}")
    print(f"Config Items: {ConfigItem.query.count()}")
    print(f"Func Specs: {FunctionalSpec.query.count()}, Tech Specs: {TechnicalSpec.query.count()}")
    print(f"Test Plans: {TestPlan.query.count()}, Cycles: {TestCycle.query.count()}, Cases: {TestCase.query.count()}")
    print(f"Executions: {TestExecution.query.count()}, Defects: {Defect.query.count()}")
    print(f"RAID: R={Risk.query.count()} A={Action.query.count()} I={Issue.query.count()} D={Decision.query.count()}")
    total = (1 + Scenario.query.count() + Process.query.count() + Requirement.query.count()
             + Sprint.query.count() + BacklogItem.query.count() + ConfigItem.query.count()
             + FunctionalSpec.query.count() + TechnicalSpec.query.count()
             + TestPlan.query.count() + TestCycle.query.count() + TestCase.query.count()
             + TestExecution.query.count() + Defect.query.count()
             + Risk.query.count() + Action.query.count() + Issue.query.count() + Decision.query.count())
    print(f"\nToplam (ana tablolar): {total}")
