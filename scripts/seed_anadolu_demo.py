#!/usr/bin/env python3
"""
SAP Transformation Platform — Anadolu Holding Demo Seed.

Gerçekçi Türk SAP dönüşüm projesi: Anadolu Holding S/4HANA.
Brownfield yaklaşım, SD/MM/FI/CO modülleri, ~97 kayıt.

Kaynak: SEED_DATA_MANUAL_ENTRY.md

Usage:
    python scripts/seed_anadolu_demo.py              # Mevcut DB'ye ekle
    python scripts/seed_anadolu_demo.py --reset      # DB sıfırlayıp yükle
"""

import argparse
import sys
import uuid
from datetime import date, datetime, time, timezone

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.program import Program, Phase, Workstream, TeamMember
from app.models.scenario import Scenario
from app.models.scope import Process, Analysis
from app.models.explore import (
    ProcessLevel,
    ExploreWorkshop,
    WorkshopAttendee,
    WorkshopAgendaItem,
    ProcessStep,
    ExploreDecision,
    ExploreOpenItem,
    ExploreRequirement,
)
from app.models.backlog import BacklogItem, ConfigItem
from app.models.testing import TestPlan, TestCycle, TestCase, TestExecution
from app.models.raid import Risk, Action

_now = datetime.now(timezone.utc)
_uid = lambda: str(uuid.uuid4())

# ═══════════════════════════════════════════════════════════════════════════
# 1. PROGRAM & INFRA
# ═══════════════════════════════════════════════════════════════════════════

def seed_program():
    """Anadolu Holding S/4HANA Transformation program."""
    p = Program(
        name="Anadolu Holding S/4HANA Transformation",
        description=(
            "Anadolu Holding'in mevcut ECC 6.0 sisteminden S/4HANA'ya dönüşüm projesi. "
            "4 ana modül kapsam dahilinde, 12 ay süre planlanmıştır. "
            "Brownfield yaklaşımla mevcut özelleştirmeler korunarak modern platforma geçiş hedeflenmektedir."
        ),
        project_type="brownfield",
        methodology="sap_activate",
        status="active",
        priority="critical",
        sap_product="S/4HANA 2023 FPS02",
        deployment_option="on_premise",
        start_date=date(2026, 3, 1),
        end_date=date(2027, 3, 1),
        go_live_date=date(2027, 1, 15),
    )
    db.session.add(p)
    db.session.flush()

    # Phases
    phases = []
    for idx, (name, status, pct, sd, ed) in enumerate([
        ("Discover", "completed", 100, date(2026, 3, 1), date(2026, 3, 14)),
        ("Prepare", "completed", 100, date(2026, 3, 15), date(2026, 3, 31)),
        ("Explore", "in_progress", 35, date(2026, 4, 1), date(2026, 6, 30)),
        ("Realize", "planned", 0, date(2026, 7, 1), date(2026, 10, 31)),
        ("Deploy", "planned", 0, date(2026, 11, 1), date(2026, 12, 31)),
        ("Run", "planned", 0, date(2027, 1, 1), date(2027, 3, 1)),
    ]):
        ph = Phase(
            program_id=p.id, name=name, status=status,
            completion_pct=pct, planned_start=sd, planned_end=ed,
            order=idx,
        )
        db.session.add(ph)
        phases.append(ph)
    db.session.flush()

    # Workstreams
    ws_data = [
        ("SD — Sales & Distribution", "SD"),
        ("MM — Materials Management", "MM"),
        ("FI — Financial Accounting", "FI"),
        ("CO — Controlling", "CO"),
    ]
    workstreams = {}
    for ws_name, mod in ws_data:
        ws = Workstream(program_id=p.id, name=ws_name, ws_type="functional", status="active")
        db.session.add(ws)
        workstreams[mod] = ws
    db.session.flush()

    # Team Members
    members = [
        ("Ayşe Demir", "project_lead", "ayse.demir@consulting.com"),
        ("Burak Kaya", "consultant", "burak.kaya@consulting.com"),
        ("Canan Öztürk", "stream_lead", "canan.ozturk@consulting.com"),
        ("Deniz Aksoy", "developer", "deniz.aksoy@consulting.com"),
        ("Mehmet Yılmaz", "team_member", "mehmet.yilmaz@anadoluholding.com.tr"),
    ]
    for mname, mrole, memail in members:
        tm = TeamMember(program_id=p.id, name=mname, role=mrole, email=memail)
        db.session.add(tm)
    db.session.flush()

    print(f"  ✅ Program: {p.name} (id={p.id})")
    print(f"  ✅ {len(phases)} phases, {len(workstreams)} workstreams, {len(members)} team members")
    return p, phases, workstreams


# ═══════════════════════════════════════════════════════════════════════════
# 2. SCENARIOS (5)
# ═══════════════════════════════════════════════════════════════════════════

def seed_scenarios(program):
    scenarios = {}
    data = [
        ("S-001", "Order to Cash", "SD", "order_to_cash", "in_analysis",
         "Müşteri siparişinden tahsilata kadar tüm satış sürecini kapsar. Standart sipariş, iade, kredi/borç dekontu, ATP kontrolü ve faturalama dahil. SAP Best Practice scope item 1YG, BD9 referanslı."),
        ("S-002", "Procure to Pay", "MM", "procure_to_pay", "in_analysis",
         "Satın alma talebinden tedarikçi ödemesine kadar tüm tedarik sürecini kapsar. Satın alma talebi, sipariş, mal girişi, fatura doğrulama ve ödeme. Scope item J58, 2NM referanslı."),
        ("S-003", "Record to Report", "FI", "record_to_report", "draft",
         "Muhasebe kayıtlarından finansal raporlamaya kadar süreç. Genel muhasebe, alacak/borç yönetimi, varlık muhasebesi, dönem sonu kapanış ve raporlama. Scope item J77, BEV referanslı."),
        ("S-004", "Plan to Produce", "CO", "plan_to_produce", "draft",
         "Üretim planlama ve maliyet kontrolü senaryosu. Maliyet merkezi muhasebesi, dahili siparişler, ürün maliyetlendirme ve kar/maliyet analizi. CO modülü odaklı."),
        ("S-005", "O2C + R2R Integration Test", "SD", "order_to_cash", "draft",
         "Satış faturasının FI'a otomatik muhasebe kaydı oluşturması, alacak hesabına yansıması ve raporlamaya düşmesi. Cross-module entegrasyon testi."),
    ]
    for code, name, mod, pa, status, desc in data:
        s = Scenario(
            program_id=program.id, name=name, description=desc,
            sap_module=mod, process_area=pa, status=status,
            priority="high" if status == "in_analysis" else "medium",
        )
        db.session.add(s)
        db.session.flush()
        scenarios[code] = s

    print(f"  ✅ {len(scenarios)} scenarios")
    return scenarios


# ═══════════════════════════════════════════════════════════════════════════
# 3. PROCESS HIERARCHY (L2/L3) & ANALYSES
# ═══════════════════════════════════════════════════════════════════════════

def seed_processes_and_analyses(program, scenarios):
    """Create L2/L3 process nodes + Analysis records."""
    processes = {}

    # L2 Process Areas
    l2_data = [
        ("S-001", "Sales & Distribution", "SD", "O2C"),
        ("S-002", "Procurement", "MM", "P2P"),
        ("S-003", "Financial Accounting", "FI", "R2R"),
        ("S-004", "Controlling", "CO", "P2Pr"),
    ]
    for sc_code, name, mod, proc_code in l2_data:
        p2 = Process(
            scenario_id=scenarios[sc_code].id,
            name=name, level="L2", module=mod,
            process_id_code=proc_code,
        )
        db.session.add(p2)
        db.session.flush()
        processes[f"{sc_code}_L2"] = p2

    # L3 Processes (for analysis targets)
    l3_data = [
        ("S-001", "Standard Sales Order Processing", "SD", "O2C-001", "S-001_L2"),
        ("S-001", "Billing & Credit Management", "SD", "O2C-002", "S-001_L2"),
        ("S-002", "Procurement & Goods Receipt", "MM", "P2P-001", "S-002_L2"),
        ("S-002", "Invoice Verification & Payment", "MM", "P2P-002", "S-002_L2"),
        ("S-003", "General Ledger & Closing", "FI", "R2R-001", "S-003_L2"),
    ]
    for sc_code, name, mod, proc_code, parent_key in l3_data:
        p3 = Process(
            scenario_id=scenarios[sc_code].id,
            parent_id=processes[parent_key].id,
            name=name, level="L3", module=mod,
            process_id_code=proc_code,
        )
        db.session.add(p3)
        db.session.flush()
        processes[proc_code] = p3

    # Analyses (4)
    analyses = {}
    anl_data = [
        ("ANL-001", "O2C Fit-to-Standard Workshop", "O2C-001", "workshop", "completed",
         "Order to Cash sürecinin SAP Best Practice ile karşılaştırma atölyesi. SD modülü ana süreçleri incelendi. Katılımcılar: SD danışmanları, satış müdürü, depo sorumlusu.",
         date(2026, 3, 15)),
        ("ANL-002", "O2C Gap Detail Analysis", "O2C-001", "fit_gap", "in_progress",
         "Workshop'ta tespit edilen Gap'lerin detaylı analizi. Her gap için çözüm alternatifi ve effort tahmini yapılıyor.",
         date(2026, 3, 22)),
        ("ANL-003", "P2P Fit-to-Standard Workshop", "P2P-001", "workshop", "completed",
         "Procure to Pay sürecinin SAP Best Practice ile karşılaştırma atölyesi. MM modülü tedarik süreçleri incelendi.",
         date(2026, 3, 18)),
        ("ANL-004", "R2R Fit-to-Standard Workshop", "R2R-001", "workshop", "planned",
         "Record to Report sürecinin SAP Best Practice ile karşılaştırma atölyesi. FI modülü muhasebe süreçleri planlanıyor.",
         date(2026, 4, 5)),
    ]
    for code, name, proc_code, atype, status, desc, adate in anl_data:
        a = Analysis(
            process_id=processes[proc_code].id,
            name=name, description=desc,
            analysis_type=atype, status=status, date=adate,
        )
        db.session.add(a)
        db.session.flush()
        analyses[code] = a

    print(f"  ✅ {len(processes)} processes (L2+L3), {len(analyses)} analyses")
    return processes, analyses


# ═══════════════════════════════════════════════════════════════════════════
# 4. EXPLORE WORKSHOPS (Sessions) + ProcessLevels
# ═══════════════════════════════════════════════════════════════════════════

def seed_workshops(program):
    """Create ExploreWorkshop sessions and ProcessLevel hierarchy."""

    # Process Levels (L1→L4)
    levels = {}
    level_map = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
    pl_data = [
        ("SD — Sales & Distribution", 1, "SD", "VC-SD", None),
        ("Sales Order Processing", 2, "SD", "PA-SD01", "VC-SD"),
        ("Standard Sales Order & Delivery", 3, "SD", "SD-001", "PA-SD01"),
        ("ATP Check", 4, "SD", "SD-001.01", "SD-001"),
        ("Delivery Split Logic", 4, "SD", "SD-001.02", "SD-001"),
        ("Pricing Procedure", 4, "SD", "SD-001.03", "SD-001"),
        ("Billing & Credit Management", 3, "SD", "SD-002", "PA-SD01"),
        ("Intercompany Billing", 4, "SD", "SD-002.01", "SD-002"),
        ("Credit Management", 4, "SD", "SD-002.02", "SD-002"),
        ("MM — Materials Management", 1, "MM", "VC-MM", None),
        ("Procurement", 2, "MM", "PA-MM01", "VC-MM"),
        ("Purchase Requisition & PO", 3, "MM", "MM-001", "PA-MM01"),
        ("PR Approval (Release Strategy)", 4, "MM", "MM-001.01", "MM-001"),
        ("Auto PO Creation", 4, "MM", "MM-001.02", "MM-001"),
        ("Goods Receipt & Inventory", 3, "MM", "MM-002", "PA-MM01"),
        ("GR Tolerance Check", 4, "MM", "MM-002.01", "MM-002"),
        ("Vendor Scoring", 4, "MM", "MM-002.02", "MM-002"),
        ("Consignment Reporting", 4, "MM", "MM-002.03", "MM-002"),
        ("FI — Financial Accounting", 1, "FI", "VC-FI", None),
        ("CO — Controlling", 1, "CO", "VC-CO", None),
    ]
    for pl_name, pl_level, mod, pl_code, parent_code in pl_data:
        parent_id = levels[parent_code].id if parent_code else None
        pl = ProcessLevel(
            id=_uid(), project_id=program.id,
            name=pl_name, level=pl_level,
            code=pl_code,
            process_area_code=mod,
            parent_id=parent_id,
        )
        db.session.add(pl)
        db.session.flush()
        levels[pl_code] = pl

    # Workshops (Sessions)
    workshops = {}
    ws_data = [
        ("SES-001", "O2C Workshop Day 1: Sales Order & Delivery", "SD",
         "fit_to_standard", "completed", date(2026, 3, 15), time(9, 0), time(13, 0),
         "Canan Öztürk"),
        ("SES-002", "O2C Workshop Day 2: Billing & Credit Management", "SD",
         "fit_to_standard", "completed", date(2026, 3, 16), time(9, 0), time(13, 0),
         "Canan Öztürk"),
        ("SES-003", "P2P Workshop Day 1: Procurement & Goods Receipt", "MM",
         "fit_to_standard", "completed", date(2026, 3, 18), time(9, 0), time(13, 0),
         "Fatih Korkmaz"),
        ("SES-004", "P2P Workshop Day 2: Invoice Verification & Payment", "MM",
         "fit_to_standard", "completed", date(2026, 3, 19), time(10, 0), time(13, 0),
         "Fatih Korkmaz"),
    ]
    for code, name, mod, wtype, status, wdate, st, et, fac in ws_data:
        w = ExploreWorkshop(
            id=_uid(), project_id=program.id,
            code=code, name=name, type=wtype, status=status,
            date=wdate, start_time=st, end_time=et,
            process_area=mod,
        )
        db.session.add(w)
        db.session.flush()
        workshops[code] = w

    print(f"  ✅ {len(levels)} process levels, {len(workshops)} workshops (sessions)")
    return workshops, levels


# ═══════════════════════════════════════════════════════════════════════════
# 5. ATTENDEES (9)
# ═══════════════════════════════════════════════════════════════════════════

def seed_attendees(workshops):
    att_data = {
        "SES-001": [
            ("Canan Öztürk", "Facilitator / SD Consultant", "consultant"),
            ("Mehmet Yılmaz", "Business Owner", "customer"),
            ("Elif Kara", "Key User - Sales", "customer"),
            ("Hasan Demir", "Key User - Logistics", "customer"),
            ("Burak Kaya", "Solution Architect", "consultant"),
        ],
        "SES-003": [
            ("Fatih Korkmaz", "Facilitator / MM Consultant", "consultant"),
            ("Aylin Şahin", "Key User - Purchasing", "customer"),
            ("Serkan Yıldız", "Key User - Warehouse", "customer"),
            ("Zehra Aydın", "Finance Representative", "customer"),
        ],
    }
    count = 0
    for ws_code, people in att_data.items():
        for name, role, org in people:
            a = WorkshopAttendee(
                id=_uid(), workshop_id=workshops[ws_code].id,
                name=name, role=role, organization=org,
                attendance_status="present",
            )
            db.session.add(a)
            count += 1
    db.session.flush()
    print(f"  ✅ {count} attendees")


# ═══════════════════════════════════════════════════════════════════════════
# 6. AGENDA ITEMS (13)
# ═══════════════════════════════════════════════════════════════════════════

def seed_agenda(workshops):
    agenda_data = {
        "SES-001": [
            (time(9, 0), "Proje kapsamı ve workshop amacı", 15, "session"),
            (time(9, 15), "SAP Best Practice: Standard Sales Order (1YG)", 45, "demo"),
            (time(10, 0), "Mevcut süreç vs. SAP Standard karşılaştırma", 60, "discussion"),
            (time(11, 0), "ATP Check ve Availability süreçleri", 30, "session"),
            (time(11, 30), "Delivery & Shipping Point yapılandırması", 30, "session"),
            (time(12, 0), "Gap'lerin tespiti ve önceliklendirme", 30, "discussion"),
            (time(12, 30), "Sonraki adımlar ve aksiyonlar", 10, "wrap_up"),
        ],
        "SES-003": [
            (time(9, 0), "P2P süreç genel bakış", 15, "session"),
            (time(9, 15), "SAP Best Practice: Basic Procurement (J58)", 45, "demo"),
            (time(10, 0), "Satın alma talep ve onay süreci inceleme", 45, "discussion"),
            (time(10, 45), "Mal girişi ve depo süreçleri", 30, "session"),
            (time(11, 15), "Gap tespiti ve tartışma", 30, "discussion"),
            (time(11, 45), "Aksiyonlar", 15, "wrap_up"),
        ],
    }
    count = 0
    for ws_code, items in agenda_data.items():
        for idx, (t, title, dur, atype) in enumerate(items):
            ai = WorkshopAgendaItem(
                id=_uid(), workshop_id=workshops[ws_code].id,
                time=t, title=title, duration_minutes=dur,
                type=atype, sort_order=idx + 1,
            )
            db.session.add(ai)
            count += 1
    db.session.flush()
    print(f"  ✅ {count} agenda items")


# ═══════════════════════════════════════════════════════════════════════════
# 7. PROCESS STEPS + FIT-GAP (11)
# ═══════════════════════════════════════════════════════════════════════════

def seed_fitgap(workshops, levels):
    """ProcessStep = FitGap items tied to workshops and L4 process levels."""
    steps = {}
    # Map gap items to L4 level codes (unique workshop+level per step)
    gap_data = [
        # SES-001 FitGap — each must have unique (workshop_id, process_level_id)
        ("GAP-001", "SES-001", "SD-001.03", "fit",
         "SAP standard sipariş süreci (VA01-VA02-VA03) mevcut süreci karşılıyor. Pricing procedure karşılanıyor."),
        ("GAP-003", "SES-001", "SD-001.01", "partial_fit",
         "Plant seviyesi ATP standard'da mevcut. Storage location bazlı ATP için enhancement gerekiyor."),
        ("GAP-004", "SES-001", "SD-002.01", "gap",
         "Mevcut intercompany faturalama tamamen manuel. SAP standard BD9 var ama transfer pricing kuralları custom development gerektiriyor."),
        ("GAP-005", "SES-001", "SD-001.02", "partial_fit",
         "Standart delivery split mevcut. Müşterinin özel split kuralları enhancement gerektirir."),
        ("GAP-006", "SES-001", "SD-002.02", "fit",
         "SAP Credit Management (1E1) online kredi kontrolü sağlıyor. Configuration ile taşınabilir."),
        # SES-003 FitGap
        ("GAP-007", "SES-003", "MM-001.01", "fit",
         "SAP standard PR süreci mevcut süreci tam olarak karşılıyor. Onay süreci Release Strategy ile çözülecek."),
        ("GAP-008", "SES-003", "MM-001.02", "fit",
         "MRP çalışması sonrası otomatik PO oluşturma SAP standard'da mevcut (ME59N)."),
        ("GAP-009", "SES-003", "MM-002.02", "gap",
         "Mevcut Excel-tabanlı tedarikçi puanlama sistemi 15 özel kriter içeriyor. SAP standard evaluation sadece 5 kriter. Custom report gerekli."),
        ("GAP-010", "SES-003", "MM-002.03", "partial_fit",
         "Konsinyasyon stok takibi standard'da mevcut. 3 özel rapor gerekli: aging, turnover, value."),
        ("GAP-011", "SES-003", "MM-002.01", "fit",
         "Goods receipt tolerance kontrolü SAP standard'da mevcut. OMBR/OMBW config transaction'ları ile ayarlanabilir."),
    ]
    for code, ws_code, level_code, decision, notes in gap_data:
        ps = ProcessStep(
            id=_uid(),
            workshop_id=workshops[ws_code].id,
            process_level_id=levels[level_code].id,
            fit_decision=decision,
            notes=notes,
            sort_order=len(steps) + 1,
            demo_shown=True,
            bpmn_reviewed=True,
        )
        db.session.add(ps)
        db.session.flush()
        steps[code] = ps

    print(f"  ✅ {len(steps)} fit-gap items (process steps)")
    return steps


# ═══════════════════════════════════════════════════════════════════════════
# 8. QUESTIONS / OPEN ITEMS (8)
# ═══════════════════════════════════════════════════════════════════════════

def seed_questions(program, workshops):
    q_data = [
        ("Q-001", "SES-001", "Mevcut sistemde kaç farklı sipariş tipi kullanılıyor?",
         "12 farklı sipariş tipi mevcut. SAP standard'da 7'si karşılanıyor, 5'i özel geliştirme olarak devam edecek.",
         "closed", "Elif Kara", "clarification"),
        ("Q-002", "SES-001", "ATP kontrolü hangi seviyede yapılıyor? Plant mı, storage location mı?",
         "Şu an plant seviyesinde. SAP standard ATP storage location seviyesini de destekliyor, configuration ile çözülebilir.",
         "closed", "Hasan Demir", "technical"),
        ("Q-003", "SES-001", "Intercompany satışlarda faturalama nasıl çalışıyor?",
         "Mevcut sistemde manuel. S/4HANA'da scope item BD9 ile otomatik intercompany billing mümkün.",
         "closed", "Mehmet Yılmaz", "process"),
        ("Q-004", "SES-001", "Kredi limit kontrolü online mı batch mı yapılıyor?",
         "", "open", "Elif Kara", "technical"),
        ("Q-005", "SES-001", "Third-party satışlarda süreç nasıl işleyecek?",
         "", "open", "Mehmet Yılmaz", "scope"),
        ("Q-006", "SES-003", "Tedarikçi değerlendirme sistemi SAP'de mevcut mu?",
         "SAP standard'da Supplier Evaluation (ME61-ME65) mevcut. Özel kriterlerin taşınması için custom development gerekebilir.",
         "closed", "Aylin Şahin", "technical"),
        ("Q-007", "SES-003", "Satın alma onay limitleri nasıl tanımlanacak?",
         "SAP'de Release Strategy ile tanımlanacak. Mevcut 4 kademeli onay süreci birebir karşılanabiliyor.",
         "closed", "Aylin Şahin", "process"),
        ("Q-008", "SES-003", "Konsinyasyon alım süreci mevcut mu?",
         "Evet, scope item 2NM kapsamında mevcut. Ancak özel konsinyasyon raporları SAP standard'da yok.",
         "closed", "Serkan Yıldız", "process"),
    ]
    count = 0
    creator_id = _uid()  # dummy user ID
    for code, ws_code, title, resolution, status, asked_by, category in q_data:
        q = ExploreOpenItem(
            id=_uid(), project_id=program.id,
            workshop_id=workshops[ws_code].id,
            code=code, title=title,
            description=f"Soru: {title}",
            status=status,
            priority="P2" if status == "open" else "P3",
            category=category,
            assignee_name=asked_by,
            resolution=resolution if resolution else None,
            created_by_id=creator_id,
            process_area=workshops[ws_code].process_area,
        )
        db.session.add(q)
        count += 1
    db.session.flush()
    print(f"  ✅ {count} questions (open items)")


# ═══════════════════════════════════════════════════════════════════════════
# 9. DECISIONS (5)
# ═══════════════════════════════════════════════════════════════════════════

def seed_decisions(program, steps):
    dec_data = [
        ("DEC-001", "GAP-001", "Sipariş tipi konsolidasyonu",
         "12 mevcut sipariş tipinden 7'si SAP standard tiplere map edilecek. 5 özel tip devam edecek.",
         "Mehmet Yılmaz, Canan Öztürk", "process", "active"),
        ("DEC-002", "GAP-003", "ATP seviyesi karar",
         "ATP kontrolü plant seviyesinde kalacak, storage location seviyesi Phase 2'ye bırakılacak.",
         "Hasan Demir, Burak Kaya", "technical", "active"),
        ("DEC-003", "GAP-004", "Intercompany yaklaşım",
         "SAP standard BD9 scope item kullanılacak. Transfer pricing kuralları için ABAP enhancement geliştirilecek.",
         "Mehmet Yılmaz", "scope", "active"),
        ("DEC-004", "GAP-007", "Release Strategy yapısı",
         "4 kademeli onay süreci SAP Release Strategy ile birebir uygulanacak.",
         "Aylin Şahin", "process", "active"),
        ("DEC-005", "GAP-009", "Vendor Evaluation yaklaşımı",
         "SAP standard evaluation + custom Z-report kombinasyonu.",
         "Aylin Şahin, Fatih Korkmaz", "technical", "active"),
    ]
    count = 0
    for code, step_code, text, rationale, decided_by, category, status in dec_data:
        d = ExploreDecision(
            id=_uid(), project_id=program.id,
            process_step_id=steps[step_code].id,
            code=code, text=text, rationale=rationale,
            decided_by=decided_by, category=category, status=status,
        )
        db.session.add(d)
        count += 1
    db.session.flush()
    print(f"  ✅ {count} decisions")


# ═══════════════════════════════════════════════════════════════════════════
# 10. RISKS (5)
# ═══════════════════════════════════════════════════════════════════════════

def seed_risks(program):
    risk_data = [
        ("RSK-001", "Data Migration karmaşıklığı",
         "12 sipariş tipinin 7'ye konsolidasyonu sırasında açık sipariş ve tarihsel veri dönüşümü karmaşık olabilir. 50K+ açık sipariş mevcut.",
         "high", 4, 5, "Deniz Aksoy",
         "Migration pilot çalışması yapılacak. İlk 1000 kayıt ile test, sonra tam migration. Fallback planı hazırlanacak."),
        ("RSK-002", "Intercompany geliştirme süresi",
         "Transfer pricing ABAP geliştirmesi Go-live tarihini tehdit edebilir. Complexity yüksek.",
         "high", 3, 4, "Burak Kaya",
         "Erken prototip (Sprint 2'de başlangıç). Gerekirse Go-live scope'undan çıkarılıp Phase 2'ye alınır."),
        ("RSK-003", "Key User müsaitliği",
         "Elif Kara (SD Key User) Nisan ayında 2 hafta izinli olacak. Workshop planlamasını etkiler.",
         "medium", 3, 3, "Ayşe Demir",
         "Backup key user (Gamze Yıldız) atanacak. Nisan öncesi kritik workshoplar tamamlanacak."),
        ("RSK-004", "Custom report performansı",
         "Vendor scoring custom report'u büyük veri setlerinde (100K+ tedarikçi kaydı) yavaş çalışabilir.",
         "low", 2, 3, "Deniz Aksoy",
         "HANA optimizasyonu + CDS view kullanımı ile performans sağlanacak."),
        ("RSK-005", "Kullanıcı eğitimi yetersizliği",
         "200+ son kullanıcı eğitimi yeterli sürede tamamlanamayabilir.",
         "medium", 3, 3, "Ayşe Demir",
         "Train-the-trainer yaklaşımı. 15 süper kullanıcı yetiştirilecek."),
    ]
    count = 0
    for code, title, desc, priority, prob, impact, owner, mitigation in risk_data:
        r = Risk(
            program_id=program.id,
            code=code, title=title, description=desc,
            status="open", owner=owner, priority=priority,
            probability=prob, impact=impact,
            mitigation_plan=mitigation,
        )
        r.recalculate_score()
        db.session.add(r)
        count += 1
    db.session.flush()
    print(f"  ✅ {count} risks")


# ═══════════════════════════════════════════════════════════════════════════
# 11. ACTIONS (8)
# ═══════════════════════════════════════════════════════════════════════════

def seed_actions(program):
    act_data = [
        ("ACT-001", "Sipariş tipi mapping dokümanı hazırla", "Canan Öztürk",
         date(2026, 3, 25), "high", "in_progress", "follow_up"),
        ("ACT-002", "ATP enhancement scope dokümanı yaz", "Canan Öztürk",
         date(2026, 3, 28), "high", "open", "follow_up"),
        ("ACT-003", "Intercompany transfer pricing kurallarını dokümante et", "Mehmet Yılmaz",
         date(2026, 4, 1), "critical", "open", "preventive"),
        ("ACT-004", "Backup key user (Gamze Yıldız) onayını al", "Ayşe Demir",
         date(2026, 3, 20), "medium", "completed", "corrective"),
        ("ACT-005", "Data migration pilot planı hazırla", "Deniz Aksoy",
         date(2026, 4, 5), "high", "open", "preventive"),
        ("ACT-006", "Release Strategy detay tasarımı", "Fatih Korkmaz",
         date(2026, 3, 28), "medium", "in_progress", "follow_up"),
        ("ACT-007", "Vendor scoring kriterleri listesi (15 kriter detaylı)", "Aylin Şahin",
         date(2026, 3, 30), "high", "open", "follow_up"),
        ("ACT-008", "Konsinyasyon rapor gereksinimleri yaz", "Serkan Yıldız",
         date(2026, 4, 2), "medium", "open", "follow_up"),
    ]
    count = 0
    for code, title, owner, due, priority, status, atype in act_data:
        a = Action(
            program_id=program.id,
            code=code, title=title, owner=owner,
            due_date=due, priority=priority, status=status,
            action_type=atype,
        )
        db.session.add(a)
        count += 1
    db.session.flush()
    print(f"  ✅ {count} actions")


# ═══════════════════════════════════════════════════════════════════════════
# 12. REQUIREMENTS (12)
# ═══════════════════════════════════════════════════════════════════════════

def seed_requirements(program, workshops, steps, levels):
    """Create ExploreRequirements — Fit, Partial Fit, Gap."""
    reqs = {}
    creator_id = _uid()

    req_data = [
        # Fit requirements
        ("REQ-001", "Standard Sales Order Configuration", "Fit", "SD", "P1", "approved",
         "configuration", "SES-001", "GAP-001",
         "Standart sipariş tipi (OR) konfigürasyonu. Order type, item category determination, schedule line category, copy control ayarları. Scope item 1YG kapsamında.", 0),
        ("REQ-002", "SD Pricing Procedure Setup", "Fit", "SD", "P1", "approved",
         "configuration", "SES-001", "GAP-001",
         "Fiyatlandırma prosedürü konfigürasyonu. 8 condition type ve access sequence tanımları.", 0),
        ("REQ-003", "Credit Management Configuration", "Fit", "SD", "P2", "approved",
         "configuration", "SES-001", "GAP-006",
         "SAP Credit Management (FIN-FSCM-CR) konfigürasyonu. Kredi segmenti, risk kategorisi, otomatik kredi karar kuralları.", 0),
        ("REQ-004", "Purchase Requisition Approval (Release Strategy)", "Fit", "MM", "P1", "approved",
         "configuration", "SES-003", "GAP-007",
         "Satın alma talebi onay stratejisi konfigürasyonu. 4 kademe onay.", 0),
        ("REQ-005", "GR Tolerance Configuration", "Fit", "MM", "P3", "approved",
         "configuration", "SES-003", "GAP-011",
         "Mal girişi tolerans kontrolü ayarları. Quantity tolerance %5, price tolerance %3.", 0),
        # Partial Fit requirements
        ("REQ-006", "ATP Check Enhancement", "Partial Fit", "SD", "P1", "under_review",
         "enhancement", "SES-001", "GAP-003",
         "Storage location bazlı ATP logic ve alternatif plant check için BADI implementation gerekiyor.", 12),
        ("REQ-007", "Delivery Split Custom Logic", "Partial Fit", "SD", "P2", "under_review",
         "enhancement", "SES-001", "GAP-005",
         "Same-day delivery priority logic ve müşteriye özel partial shipment restriction kuralları. User exit USEREXIT_MOVE_FIELD_TO_VBLK.", 8),
        ("REQ-008", "Consignment Stock Reporting", "Partial Fit", "MM", "P2", "draft",
         "enhancement", "SES-003", "GAP-010",
         "3 özel rapor gerekli: aging report, turnover analysis, value report. CDS view + Fiori app yaklaşımı.", 15),
        # Gap requirements
        ("REQ-009", "Intercompany Billing Automation", "Gap", "SD", "P1", "approved",
         "development", "SES-001", "GAP-004",
         "SAP standard BD9 üzerine transfer pricing custom logic. ABAP enhancement + custom pricing procedure. Tahmini: 40 adam/gün.", 40),
        ("REQ-010", "Vendor Scoring Custom Report", "Gap", "MM", "P1", "approved",
         "development", "SES-003", "GAP-009",
         "15 kriterli tedarikçi puanlama raporu. Z-report + ALV + Fiori dashboard. Tahmini: 20 adam/gün.", 20),
        ("REQ-011", "Custom IDoc for Intercompany Orders", "Gap", "SD", "P1", "draft",
         "integration", "SES-001", "GAP-004",
         "Intercompany sipariş oluşturma için özel IDoc message type. ORDERS05 base IDoc üzerine Z-segment. Tahmini: 15 adam/gün.", 15),
        ("REQ-012", "Automated Dunning Workflow", "Gap", "FI", "P2", "draft",
         "development", None, None,
         "Otomatik tahsilat hatırlatma workflow'u. SAP standard dunning (F150) üzerine custom workflow. BRFplus karar tablosu. Tahmini: 25 adam/gün.", 25),
    ]

    fit_map = {"Fit": "fit", "Partial Fit": "partial_fit", "Gap": "gap"}

    for code, title, fit, mod, priority, status, rtype, ws_code, step_code, desc, effort in req_data:
        ws_id = workshops[ws_code].id if ws_code else None
        ps_id = steps[step_code].id if step_code else None
        r = ExploreRequirement(
            id=_uid(), project_id=program.id,
            workshop_id=ws_id,
            process_step_id=ps_id,
            code=code, title=title, description=desc,
            priority=priority, type=rtype,
            fit_status=fit_map[fit], status=status,
            sap_module=mod,
            effort_hours=effort * 8 if effort else None,
            complexity="high" if effort >= 20 else "medium" if effort >= 8 else "low",
            created_by_id=creator_id,
            created_by_name="Seed Script",
        )
        db.session.add(r)
        db.session.flush()
        reqs[code] = r

    print(f"  ✅ {len(reqs)} requirements")
    return reqs


# ═══════════════════════════════════════════════════════════════════════════
# 13. WRICEF ITEMS (6)
# ═══════════════════════════════════════════════════════════════════════════

def seed_wricef(program, reqs):
    items = {}
    w_data = [
        ("W-001", "ATP Check Enhancement (BADI)", "enhancement", "SD",
         "High", "new", "REQ-006",
         "BADI implementation: BAPI_MATERIAL_AVAILABILITY. Storage location bazlı ATP logic. Tahmini: 12 adam/gün.", 12),
        ("W-002", "Delivery Split Custom Logic", "enhancement", "SD",
         "Medium", "new", "REQ-007",
         "User exit USEREXIT_MOVE_FIELD_TO_VBLK enhancement. Same-day delivery priority. Tahmini: 8 adam/gün.", 8),
        ("W-003", "Intercompany Billing Enhancement", "enhancement", "SD",
         "Critical", "design", "REQ-009",
         "ABAP enhancement: transfer pricing logic, custom pricing procedure ZINTER. Tahmini: 40 adam/gün.", 40),
        ("R-001", "Vendor Scoring Dashboard", "report", "MM",
         "High", "new", "REQ-010",
         "ALV interactive report + Fiori app. 15 kriter, weighted scoring. CDS view: ZI_VENDOR_SCORE. Tahmini: 20 adam/gün.", 20),
        ("I-001", "Intercompany Order IDoc", "interface", "SD",
         "High", "new", "REQ-011",
         "Custom IDoc message type ZORDERS_IC. Base: ORDERS05. Z-segment: Z1ICDATA. Tahmini: 15 adam/gün.", 15),
        ("W-004", "Dunning Workflow Automation", "workflow", "FI",
         "Medium", "new", "REQ-012",
         "SAP Workflow + BRFplus. Dunning trigger → mail → eskalasyon → portal notification. Tahmini: 25 adam/gün.", 25),
    ]
    priority_map = {"Critical": "critical", "High": "high", "Medium": "medium", "Low": "low"}

    for code, title, wtype, mod, priority, status, req_code, desc, effort in w_data:
        bi = BacklogItem(
            program_id=program.id,
            explore_requirement_id=reqs[req_code].id,
            code=code, title=title, description=desc,
            wricef_type=wtype, module=mod,
            status=status,
            priority=priority_map.get(priority, "medium"),
            estimated_hours=effort * 8,
            story_points=effort // 2,
            complexity="high" if effort >= 20 else "medium",
        )
        db.session.add(bi)
        db.session.flush()
        items[code] = bi

    print(f"  ✅ {len(items)} WRICEF items")
    return items


# ═══════════════════════════════════════════════════════════════════════════
# 14. CONFIG ITEMS (5)
# ═══════════════════════════════════════════════════════════════════════════

def seed_config_items(program, reqs):
    configs = {}
    cfg_data = [
        ("CFG-001", "Sales Order Type Configuration", "SD", "in_progress", "REQ-001",
         "VOV8, VOV7, OVLP",
         "Order type OR konfigürasyonu: item category determination (TAN, TAX), schedule line (CP, CN), copy control, partner determination."),
        ("CFG-002", "SD Pricing Procedure Config", "SD", "in_progress", "REQ-002",
         "V/08, VK11-VK13",
         "Pricing procedure RVAA01 üzerinden condition type tanımları. Access sequence, condition tables, condition records."),
        ("CFG-003", "Credit Management Setup", "SD", "planned", "REQ-003",
         "UKM_ADMIN, FDK43",
         "Credit segment ZSTD tanımlama, risk category A/B/C, credit control area 1000, automatic credit decision kuralları."),
        ("CFG-004", "MM Release Strategy", "MM", "in_progress", "REQ-004",
         "SPRO, CL02, ME28",
         "Release group Z1, release code (Z1-Z4), release strategy tanımları. Classification: purchasing group + net value range."),
        ("CFG-005", "GR Tolerance Setup", "MM", "planned", "REQ-005",
         "OMBR, OMBW",
         "Tolerance key PE: qty tolerance 5%, price tolerance 3%. Plant bazlı tanımlama. Movement type 101 ve 102 için aktif."),
    ]
    for code, title, mod, status, req_code, tcode, desc in cfg_data:
        ci = ConfigItem(
            program_id=program.id,
            explore_requirement_id=reqs[req_code].id,
            code=code, title=title, description=desc,
            module=mod, status=status,
            transaction_code=tcode,
            priority="high",
        )
        db.session.add(ci)
        db.session.flush()
        configs[code] = ci

    print(f"  ✅ {len(configs)} config items")
    return configs


# ═══════════════════════════════════════════════════════════════════════════
# 15. TEST CASES (8)
# ═══════════════════════════════════════════════════════════════════════════

def seed_test_cases(program, wricef, configs):
    cases = {}
    tc_data = [
        # Unit tests
        ("UT-001", "Unit Test: SD Pricing Procedure", "unit", "SD", "ready",
         "CFG-002", None,
         "VA01 ile sipariş yarat → 8 condition type doğru geldiğini kontrol et → Net value hesaplamasını doğrula",
         "VA01 → sipariş oluştur", "Condition type PR00, K004, K005, K007, MWST, HA00, HB00, ZK01 mevcut. Net value doğru."),
        ("UT-002", "Unit Test: ATP Check Enhancement", "unit", "SD", "draft",
         None, "W-001",
         "VA01 → storage location bazlı ATP → sonuç doğrula → alternatif plant check → sıralama doğrula",
         "VA01 → ATP check tetikle", "Storage location bazlı ATP sonucu doğru. Alternatif plant sıralaması beklenen."),
        ("UT-003", "Unit Test: Release Strategy", "unit", "MM", "ready",
         "CFG-004", None,
         "ME51N ile PR oluştur → her seviye test: <5K otomatik, 5K-25K dept müdürü, 25K-100K direktör, >100K CEO",
         "ME51N → PR oluştur", "Her kademe doğru release code tetikleniyor."),
        ("UT-004", "Unit Test: Vendor Scoring Report", "unit", "MM", "draft",
         None, "R-001",
         "Z-report çalıştır → 15 kriter doğru hesaplanıyor mu → weighted score kontrol → drill-down çalışıyor mu",
         "Z-report execute", "15 kriter weighted score ile gösterildi. Drill-down OK."),
        # SIT tests
        ("SIT-001", "SIT: O2C End-to-End Flow", "sit", "SD", "draft",
         None, None,
         "VA01 sipariş → VL01N teslimat → VL02N PGI → VF01 fatura → FI muhasebe kaydı → alacak hesabı doğrulaması",
         "VA01 → VL01N → VF01 → FI posting", "Tüm zincir sorunsuz. FI kaydı oluştu."),
        ("SIT-002", "SIT: P2P End-to-End Flow", "sit", "MM", "draft",
         None, None,
         "ME51N talep → ME21N sipariş → MIGO mal girişi → MIRO fatura doğrulama → FI muhasebe kaydı → ödeme planı",
         "ME51N → ME21N → MIGO → MIRO", "P2P zinciri tamamlandı. FI kaydı OK."),
        # UAT tests
        ("UAT-001", "UAT: Sales Order Processing", "uat", "SD", "draft",
         None, None,
         "Son kullanıcı senaryosu: müşteriden sipariş al → stok kontrol → teslimat planla → fatura kes → tahsilat takibi",
         "Sipariş al → teslimat → fatura", "Son kullanıcı senaryosu başarılı."),
        ("UAT-002", "UAT: Procurement Cycle", "uat", "MM", "draft",
         None, None,
         "Son kullanıcı senaryosu: malzeme ihtiyacı tespit → PR oluştur → onay al → PO gönder → mal kabul → fatura eşleştir",
         "PR → PO → GR → IR", "Procurement döngüsü OK."),
    ]
    for code, title, layer, mod, status, cfg_code, wricef_code, desc, steps, expected in tc_data:
        cfg_id = configs[cfg_code].id if cfg_code else None
        wricef_id = wricef[wricef_code].id if wricef_code else None
        tc = TestCase(
            program_id=program.id,
            config_item_id=cfg_id,
            backlog_item_id=wricef_id,
            code=code, title=title, description=desc,
            test_layer=layer, module=mod, status=status,
            test_steps=steps, expected_result=expected,
            priority="high" if layer == "unit" else "medium",
        )
        db.session.add(tc)
        db.session.flush()
        cases[code] = tc

    print(f"  ✅ {len(cases)} test cases")
    return cases


# ═══════════════════════════════════════════════════════════════════════════
# 16. TEST CYCLES (3) + TEST PLAN
# ═══════════════════════════════════════════════════════════════════════════

def seed_test_cycles(program, cases):
    # Test Plan (required parent)
    tp = TestPlan(
        program_id=program.id,
        name="Anadolu Holding — Master Test Plan",
        description="SD/MM/FI/CO modülleri için unit, SIT ve UAT test planı.",
        status="active",
    )
    db.session.add(tp)
    db.session.flush()

    cycles = {}
    cycle_data = [
        ("TC-001", "Sprint 1 Unit Test Cycle", "unit", "planning",
         date(2026, 5, 1), date(2026, 5, 15),
         "İlk sprint unit testleri. SD pricing, ATP enhancement, MM release strategy testleri."),
        ("TC-002", "SIT Cycle 1 — Core Processes", "sit", "planning",
         date(2026, 6, 1), date(2026, 6, 30),
         "O2C ve P2P end-to-end entegrasyon testleri. Cross-module bağlantılar doğrulanacak."),
        ("TC-003", "UAT Cycle 1 — Business Validation", "uat", "planning",
         date(2026, 8, 1), date(2026, 8, 31),
         "Son kullanıcı kabul testleri. Key user'lar tarafından gerçek iş senaryoları test edilecek."),
    ]
    for idx, (code, name, layer, status, sd, ed, desc) in enumerate(cycle_data):
        tc = TestCycle(
            plan_id=tp.id, name=name, description=desc,
            test_layer=layer, status=status,
            start_date=sd, end_date=ed,
            order=idx + 1,
        )
        db.session.add(tc)
        db.session.flush()
        cycles[code] = tc

    print(f"  ✅ 1 test plan, {len(cycles)} test cycles")
    return cycles


# ═══════════════════════════════════════════════════════════════════════════
# 17. TEST EXECUTIONS (2)
# ═══════════════════════════════════════════════════════════════════════════

def seed_test_executions(cycles, cases):
    exec_data = [
        ("TC-001", "UT-001", "pass", "Canan Öztürk", 45,
         "8/8 condition type doğru geldi. Net value hesaplaması OK."),
        ("TC-001", "UT-003", "fail", "Fatih Korkmaz", 60,
         ">100K seviyesinde release code Z4 tetiklenmiyor. Config eksik — classification object güncellenecek."),
    ]
    count = 0
    for cycle_code, case_code, result, executor, dur, notes in exec_data:
        te = TestExecution(
            cycle_id=cycles[cycle_code].id,
            test_case_id=cases[case_code].id,
            result=result, executed_by=executor,
            duration_minutes=dur, notes=notes,
            executed_at=_now,
        )
        db.session.add(te)
        count += 1
    db.session.flush()
    print(f"  ✅ {count} test executions")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Seed Anadolu Holding demo data")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.reset:
            print("\n⚠️  DB sıfırlanıyor (drop_all + create_all)...")
            db.drop_all()
            db.create_all()
            print("   ✅ DB yeniden oluşturuldu\n")

        print("=" * 60)
        print("🏢 Anadolu Holding S/4HANA Demo Verileri Yükleniyor...")
        print("=" * 60)
        print()

        # 1. Program
        program, phases, workstreams = seed_program()

        # 2. Scenarios
        scenarios = seed_scenarios(program)

        # 3. Process hierarchy + Analyses
        processes, analyses = seed_processes_and_analyses(program, scenarios)

        # 4. Explore Workshops + Process Levels
        workshops, levels = seed_workshops(program)

        # 5. Attendees
        seed_attendees(workshops)

        # 6. Agenda
        seed_agenda(workshops)

        # 7. Fit-Gap (ProcessSteps)
        steps = seed_fitgap(workshops, levels)

        # 8. Questions (Open Items)
        seed_questions(program, workshops)

        # 9. Decisions
        seed_decisions(program, steps)

        # 10. Risks
        seed_risks(program)

        # 11. Actions
        seed_actions(program)

        # 12. Requirements
        reqs = seed_requirements(program, workshops, steps, levels)

        # 13. WRICEF Items
        wricef = seed_wricef(program, reqs)

        # 14. Config Items
        configs = seed_config_items(program, reqs)

        # 15. Test Cases
        cases = seed_test_cases(program, wricef, configs)

        # 16. Test Cycles
        cycles = seed_test_cycles(program, cases)

        # 17. Test Executions
        seed_test_executions(cycles, cases)

        db.session.commit()

        print()
        print("=" * 60)
        print("🎉 ANADOLU HOLDİNG DEMO VERİ YÜKLEME TAMAMLANDI")
        print("=" * 60)
        print()
        print("   📊 Özet:")
        print("   ├── 1 Program (Anadolu Holding S/4HANA)")
        print("   ├── 5 Scenarios (O2C, P2P, R2R, P2Pr, Composite)")
        print("   ├── 4 Analyses")
        print("   ├── 4 Workshops (Sessions)")
        print("   ├── 9 Attendees")
        print("   ├── 13 Agenda Items")
        print("   ├── 10 Fit-Gap Items")
        print("   ├── 8 Questions (Open Items)")
        print("   ├── 5 Decisions")
        print("   ├── 5 Risks")
        print("   ├── 8 Actions")
        print("   ├── 12 Requirements")
        print("   ├── 6 WRICEF Items")
        print("   ├── 5 Config Items")
        print("   ├── 8 Test Cases")
        print("   ├── 3 Test Cycles")
        print("   └── 2 Test Executions")
        print()
        print("   🔗 http://localhost:5001")
        print()


if __name__ == "__main__":
    main()
