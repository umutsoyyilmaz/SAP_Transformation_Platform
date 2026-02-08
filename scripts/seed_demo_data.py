#!/usr/bin/env python3
"""
SAP Transformation Platform — Full Demo Data Seed Script.

Creates a realistic, fully-connected dataset for offline testing:

    1 Program  (SAP S/4HANA Greenfield — Türk Otomotiv A.Ş.)
    ├── 6 Phases  (SAP Activate: Discover→Prepare→Explore→Realize→Deploy→Run)
    │   └── 8 Gates
    ├── 12 Workstreams  (FI/CO, MM, SD, PP, Basis, Integration, …)
    ├── 10 Team Members
    ├── 4 Committees   (SteerCo, PMO, CAB, ARB)
    ├── 5 Scenarios    (Greenfield vs Brownfield, Cloud vs OnPrem, …)
    │   └── 15 Parameters
    ├── 20 Requirements (business, functional, technical — MoSCoW + fit/gap)
    │   └── 12 Traces  (to phases, workstreams, scenarios)
    ├── 3 Sprints      (Sprint 1-3 with capacity + velocity)
    ├── 25 Backlog Items (WRICEF: 4W, 5R, 5I, 4C, 4E, 3F — various statuses)
    ├── 10 Config Items  (IMG activities, customizing)
    ├── 8 Functional Specs  (linked to backlog + config items)
    │   └── 5 Technical Specs
    └── Traceability chain fully connected

Usage:
    python scripts/seed_demo_data.py              # Fresh seed (drops & recreates data)
    python scripts/seed_demo_data.py --append     # Append without clearing
    python scripts/seed_demo_data.py --verbose     # Show detailed output
"""

import argparse
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.program import (
    Committee, Gate, Phase, Program, TeamMember, Workstream,
)
from app.models.scenario import Scenario, Workshop
from app.models.requirement import Requirement, RequirementTrace
from app.models.backlog import (
    BacklogItem, ConfigItem, FunctionalSpec, Sprint, TechnicalSpec,
)
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
)
from app.models.scope import Process, ScopeItem, Analysis
from app.models.raid import (
    Risk, Action, Issue, Decision,
    next_risk_code, next_action_code, next_issue_code, next_decision_code,
    calculate_risk_score, risk_rag_status,
)
from app.models.notification import Notification


# ═════════════════════════════════════════════════════════════════════════════
# DATA DEFINITIONS
# ═════════════════════════════════════════════════════════════════════════════

PROGRAM_DATA = {
    "name": "Türk Otomotiv A.Ş. — S/4HANA Greenfield Dönüşüm",
    "description": (
        "Türk Otomotiv A.Ş. için SAP ECC 6.0'dan S/4HANA Cloud'a greenfield "
        "dönüşüm projesi. 15 lokasyon, 2,500+ kullanıcı, 12 SAP modülü. "
        "SAP Activate metodolojisi ile Discover-to-Run yaklaşımı uygulanacaktır. "
        "Proje süresi: 18 ay, bütçe: ₺45M."
    ),
    "project_type": "greenfield",
    "methodology": "sap_activate",
    "status": "in_progress",
    "priority": "critical",
    "sap_product": "S/4HANA Cloud",
    "deployment_option": "cloud",
}

PHASES = [
    {
        "name": "Discover",
        "order": 1,
        "status": "completed",
        "description": "İş stratejisi analizi, kapsam belirleme, iş vakası onayı.",
        "gates": [
            {"name": "Discover Quality Gate", "gate_type": "quality_gate", "status": "passed",
             "criteria": "✅ İş vakası onaylandı\n✅ Üst düzey kapsam imzalandı\n✅ Bütçe ve zaman çizelgesi onaylandı"},
        ],
    },
    {
        "name": "Prepare",
        "order": 2,
        "status": "completed",
        "description": "Proje yönetişimi, ekip oluşturma, sistem altyapısı kurulumu.",
        "gates": [
            {"name": "Prepare Quality Gate", "gate_type": "quality_gate", "status": "passed",
             "criteria": "✅ Proje tüzüğü imzalandı\n✅ Ekip onboarding tamamlandı\n✅ DEV ortamı hazır"},
        ],
    },
    {
        "name": "Explore",
        "order": 3,
        "status": "completed",
        "description": "Fit-to-Standard atölyeleri, Fit/Gap analizi, backlog oluşturma.",
        "gates": [
            {"name": "Explore Quality Gate", "gate_type": "quality_gate", "status": "passed",
             "criteria": "✅ Fit-to-Standard atölyeleri tamamlandı\n✅ Fit/Gap analizi belgelendi\n✅ Backlog önceliklendirildi"},
        ],
    },
    {
        "name": "Realize",
        "order": 4,
        "status": "in_progress",
        "description": "Konfigürasyon, WRICEF geliştirme, SIT/UAT testleri.",
        "gates": [
            {"name": "SIT Quality Gate", "gate_type": "quality_gate", "status": "not_started",
             "criteria": "✅ Tüm konfigürasyon tamamlandı\n✅ WRICEF geliştirme bitti\n✅ SIT geçti"},
            {"name": "UAT Quality Gate", "gate_type": "quality_gate", "status": "not_started",
             "criteria": "✅ UAT planı onaylandı\n✅ UAT yürütüldü\n✅ Eğitim materyalleri hazır"},
        ],
    },
    {
        "name": "Deploy",
        "order": 5,
        "status": "not_started",
        "description": "Cutover, son veri göçü, go-live.",
        "gates": [
            {"name": "Go/No-Go Decision Gate", "gate_type": "decision_point", "status": "not_started",
             "criteria": "✅ Cutover provası başarılı\n✅ Veri göçü doğrulandı\n✅ SteerCo onayı alındı"},
        ],
    },
    {
        "name": "Run",
        "order": 6,
        "status": "not_started",
        "description": "Hypercare destek, stabilizasyon, AMS devir teslim.",
        "gates": [
            {"name": "Hypercare Exit Gate", "gate_type": "milestone", "status": "not_started",
             "criteria": "✅ Hypercare süresi tamamlandı\n✅ Kritik biletler çözüldü\n✅ AMS ekibi hazır"},
        ],
    },
]

WORKSTREAMS = [
    {"name": "Finance (FI/CO)", "ws_type": "functional", "description": "Genel muhasebe, AP/AR, maliyet merkezi, kârlılık analizi", "status": "active"},
    {"name": "Materials Management (MM)", "ws_type": "functional", "description": "Satınalma, stok yönetimi, depo operasyonları", "status": "active"},
    {"name": "Sales & Distribution (SD)", "ws_type": "functional", "description": "Sipariş-to-nakit, fiyatlandırma, sevkiyat, faturalama", "status": "active"},
    {"name": "Production Planning (PP)", "ws_type": "functional", "description": "MRP, üretim emirleri, atölye kontrolü", "status": "active"},
    {"name": "Quality Management (QM)", "ws_type": "functional", "description": "Kalite planlama, muayene, bildirimler", "status": "active"},
    {"name": "Plant Maintenance (PM)", "ws_type": "functional", "description": "Önleyici/düzeltici bakım, iş emirleri", "status": "active"},
    {"name": "Human Capital (HCM)", "ws_type": "functional", "description": "Organizasyon yönetimi, personel, bordro", "status": "active"},
    {"name": "Basis / Technology", "ws_type": "technical", "description": "Sistem yönetimi, yetkilendirme, güvenlik", "status": "active"},
    {"name": "Integration (BTP)", "ws_type": "technical", "description": "SAP BTP Integration Suite, API'ler, middleware", "status": "active"},
    {"name": "Data Migration", "ws_type": "technical", "description": "Veri çıkarma, dönüştürme, doğrulama, yükleme", "status": "active"},
    {"name": "Testing", "ws_type": "cross_cutting", "description": "Test stratejisi, SIT, UAT, performans, regresyon", "status": "active"},
    {"name": "Change Management", "ws_type": "cross_cutting", "description": "Paydaş yönetimi, eğitim, iletişim", "status": "active"},
]

TEAM_MEMBERS = [
    {"name": "Mehmet Yılmaz", "role": "Program Manager", "email": "mehmet.yilmaz@turkotomotiv.com", "is_active": True},
    {"name": "Ayşe Kaya", "role": "Solution Architect", "email": "ayse.kaya@turkotomotiv.com", "is_active": True},
    {"name": "Ahmet Demir", "role": "FI/CO Consultant", "email": "ahmet.demir@consultant.com", "is_active": True},
    {"name": "Fatma Çelik", "role": "MM/SD Consultant", "email": "fatma.celik@consultant.com", "is_active": True},
    {"name": "Ali Öztürk", "role": "PP/QM Consultant", "email": "ali.ozturk@consultant.com", "is_active": True},
    {"name": "Zeynep Arslan", "role": "Basis Admin", "email": "zeynep.arslan@turkotomotiv.com", "is_active": True},
    {"name": "Emre Koç", "role": "ABAP Developer", "email": "emre.koc@consultant.com", "is_active": True},
    {"name": "Selin Doğan", "role": "BTP Integration Specialist", "email": "selin.dogan@consultant.com", "is_active": True},
    {"name": "Can Yıldırım", "role": "Data Migration Lead", "email": "can.yildirim@consultant.com", "is_active": True},
    {"name": "Elif Şahin", "role": "Test Manager", "email": "elif.sahin@turkotomotiv.com", "is_active": True},
]

COMMITTEES = [
    {"name": "Yönlendirme Komitesi (SteerCo)", "committee_type": "steering", "meeting_frequency": "monthly",
     "description": "Üst düzey yönetişim. Bütçe, kapsam değişiklikleri ve stratejik kararlar."},
    {"name": "Proje Yönetim Ofisi (PMO)", "committee_type": "working_group", "meeting_frequency": "weekly",
     "description": "Operasyonel proje yönetimi. İlerleme, risk ve sorun takibi."},
    {"name": "Değişiklik Danışma Kurulu (CAB)", "committee_type": "advisory", "meeting_frequency": "biweekly",
     "description": "Değişiklik taleplerini inceler ve onaylar."},
    {"name": "Mimari İnceleme Kurulu (ARB)", "committee_type": "review", "meeting_frequency": "biweekly",
     "description": "Teknik mimari kararlar, entegrasyon desenleri, güvenlik."},
]

SCENARIOS = [
    {
        "name": "Sevkiyat Süreci (Shipping Process)",
        "description": "Satış siparişinden sevkiyata kadar uçtan uca sevkiyat süreci. Teslimat oluşturma, toplama, paketleme, yükleme ve mal çıkışı.",
        "sap_module": "SD", "process_area": "order_to_cash",
        "status": "in_analysis", "priority": "critical",
        "owner": "Ayşe Yılmaz", "workstream": "Lojistik",
        "workshops": [
            {"title": "SD Sevkiyat Fit-Gap Workshop #1", "session_type": "fit_gap_workshop", "status": "completed",
             "facilitator": "Mehmet Kaya", "attendees": "Ayşe Yılmaz, Emre Koç, Fatma Çelik",
             "location": "İstanbul Merkez Ofis — Toplantı Odası A",
             "duration_minutes": 240, "fit_count": 8, "gap_count": 3, "partial_fit_count": 2,
             "notes": "Standart teslimat türleri SAP standard ile karşılanıyor. Özel paketleme gereksinimi gap.",
             "decisions": "Özel paketleme için WRICEF geliştirme açılacak."},
            {"title": "SD Sevkiyat Requirement Gathering", "session_type": "requirement_gathering", "status": "completed",
             "facilitator": "Mehmet Kaya", "attendees": "Ayşe Yılmaz, Lojistik Ekibi",
             "duration_minutes": 180, "requirements_identified": 6},
        ],
    },
    {
        "name": "Satın Alma Süreci (Procurement)",
        "description": "Satınalma talebi, teklif toplama, sipariş oluşturma, mal girişi ve fatura doğrulama süreci.",
        "sap_module": "MM", "process_area": "procure_to_pay",
        "status": "in_analysis", "priority": "critical",
        "owner": "Emre Koç", "workstream": "Tedarik Zinciri",
        "workshops": [
            {"title": "MM Satınalma Fit-Gap Workshop", "session_type": "fit_gap_workshop", "status": "completed",
             "facilitator": "Selin Doğan", "attendees": "Emre Koç, Ahmet Demir, Satınalma Ekibi",
             "duration_minutes": 300, "fit_count": 12, "gap_count": 5, "partial_fit_count": 3,
             "notes": "4 kademeli onay iş akışı SAP standard + workflow ile mümkün. Tedarikçi portalı gap."},
            {"title": "MM Satınalma Design Workshop", "session_type": "design_workshop", "status": "planned",
             "facilitator": "Selin Doğan", "duration_minutes": 240},
        ],
    },
    {
        "name": "Fiyatlandırma Süreci (Pricing)",
        "description": "Satış fiyat belirleme, iskonto yönetimi, kampanya fiyatları ve transfer fiyatlandırma.",
        "sap_module": "SD", "process_area": "order_to_cash",
        "status": "draft", "priority": "high",
        "owner": "Fatma Çelik", "workstream": "Satış",
        "workshops": [
            {"title": "SD Pricing Process Mapping", "session_type": "process_mapping", "status": "planned",
             "facilitator": "Mehmet Kaya", "duration_minutes": 180},
        ],
    },
    {
        "name": "Finansal Kapanış Süreci (Financial Close)",
        "description": "Aylık/yıllık kapanış süreci. Dönem sonu işlemler, mutabakat, raporlama.",
        "sap_module": "FI", "process_area": "record_to_report",
        "status": "analyzed", "priority": "critical",
        "owner": "Ahmet Demir", "workstream": "Finans",
        "workshops": [
            {"title": "FI Kapanış Fit-Gap Workshop", "session_type": "fit_gap_workshop", "status": "completed",
             "facilitator": "Ahmet Demir", "attendees": "Finans Ekibi, Denetim",
             "duration_minutes": 360, "fit_count": 15, "gap_count": 2, "partial_fit_count": 4,
             "decisions": "IFRS/TFRS paralel muhasebe SAP standard ile destekleniyor."},
            {"title": "FI Kapanış Sign-Off", "session_type": "sign_off", "status": "planned",
             "facilitator": "Ahmet Demir", "duration_minutes": 120},
        ],
    },
    {
        "name": "Üretim Planlama Süreci (Production Planning)",
        "description": "MRP çalıştırma, üretim emirleri, kapasite planlama, iş emirleri ve üretim onayları.",
        "sap_module": "PP", "process_area": "plan_to_produce",
        "status": "draft", "priority": "high",
        "owner": "Can Öztürk", "workstream": "Üretim",
        "workshops": [],
    },
]

REQUIREMENTS = [
    # Business requirements (must_have)
    {"code": "REQ-BIZ-001", "title": "Konsolide finansal raporlama (IFRS + TFRS)", "req_type": "business", "priority": "must_have", "status": "approved", "module": "FI", "fit_gap": "partial_fit", "description": "Tüm şirketler için konsolide mali tablolar. IFRS ve TFRS paralel muhasebe desteği.", "source": "CFO ofisi"},
    {"code": "REQ-BIZ-002", "title": "Gerçek zamanlı stok görünürlüğü (15 lokasyon)", "req_type": "business", "priority": "must_have", "status": "approved", "module": "MM", "fit_gap": "fit", "description": "Tüm depolarda gerçek zamanlı stok seviyesi takibi. Minimum stok uyarıları.", "source": "Lojistik müdürü"},
    {"code": "REQ-BIZ-003", "title": "Sipariş-to-nakit sürecinin otomasyonu", "req_type": "business", "priority": "must_have", "status": "approved", "module": "SD", "fit_gap": "fit", "description": "Sipariş girişinden tahsilata kadar uçtan uca otomatik süreç.", "source": "Satış direktörü"},
    {"code": "REQ-BIZ-004", "title": "Üretim planlama ve MRP optimizasyonu", "req_type": "business", "priority": "must_have", "status": "in_progress", "module": "PP", "fit_gap": "partial_fit", "description": "MRP çalıştırma süresi < 2 saat. Kapasite planlama entegrasyonu.", "source": "Üretim müdürü"},
    # Functional requirements
    {"code": "REQ-FI-001", "title": "Vergi kodu yapılandırması (KDV %1, %10, %20)", "req_type": "functional", "priority": "must_have", "status": "approved", "module": "FI", "fit_gap": "fit", "description": "Türkiye KDV oranları ve muafiyet kodları tanımlanacak."},
    {"code": "REQ-FI-002", "title": "Banka entegrasyonu (XML ISO 20022)", "req_type": "functional", "priority": "should_have", "status": "approved", "module": "FI", "fit_gap": "gap", "description": "6 bankayla otomatik ödeme ve hesap dövizi mutabakatı."},
    {"code": "REQ-MM-001", "title": "Satınalma onay iş akışı (4 seviye)", "req_type": "functional", "priority": "must_have", "status": "approved", "module": "MM", "fit_gap": "partial_fit", "description": "Tutar bazlı 4 kademeli onay: <₺10K, <₺100K, <₺500K, ≥₺500K."},
    {"code": "REQ-MM-002", "title": "Otomatik sipariş oluşturma (MRP → PO)", "req_type": "functional", "priority": "should_have", "status": "in_progress", "module": "MM", "fit_gap": "fit", "description": "MRP önerilerinden otomatik satınalma siparişi oluşturma."},
    {"code": "REQ-SD-001", "title": "Fiyat belirleme şeması (10+ koşul)", "req_type": "functional", "priority": "must_have", "status": "approved", "module": "SD", "fit_gap": "partial_fit", "description": "İskonto, prim, nakliye, vergi koşullarını içeren fiyat şeması."},
    {"code": "REQ-SD-002", "title": "Kredi yönetimi ve risk kontrolü", "req_type": "functional", "priority": "should_have", "status": "draft", "module": "SD", "fit_gap": "gap", "description": "Müşteri bazlı kredi limiti, otomatik blokaj, ülke riski değerlendirmesi."},
    {"code": "REQ-PP-001", "title": "Seri üretim planlama (Repetitive MFG)", "req_type": "functional", "priority": "must_have", "status": "in_progress", "module": "PP", "fit_gap": "fit", "description": "Otomotiv parça üretimi için seri üretim planlama senaryosu."},
    # Technical requirements
    {"code": "REQ-TEC-001", "title": "SAP BTP Integration Suite — 15 arayüz", "req_type": "technical", "priority": "must_have", "status": "approved", "module": "BTP", "fit_gap": "gap", "description": "ERP ↔ MES, WMS, TMS, CRM, e-Fatura 15 arayüz bağlantısı."},
    {"code": "REQ-TEC-002", "title": "Veri göçü — 8 ana nesne (müşteri, malzeme, BOM, …)", "req_type": "technical", "priority": "must_have", "status": "in_progress", "module": "Migration", "fit_gap": "gap", "description": "8 ana veri nesnesi + 5 hareket nesnesi göçü. Toplam ~12M kayıt."},
    {"code": "REQ-TEC-003", "title": "Yetkilendirme matrisi (60 rol)", "req_type": "technical", "priority": "must_have", "status": "draft", "module": "Basis", "fit_gap": "gap", "description": "60 SAP rolü, SOD (Görev Ayrımı) kontrolleri ile. Fiori app bazlı yetkilendirme."},
    # Non-functional
    {"code": "REQ-NFR-001", "title": "Sistem yanıt süresi < 2 saniye (P95)", "req_type": "non_functional", "priority": "must_have", "status": "approved", "module": "Basis", "fit_gap": "fit", "description": "Tüm online işlemler için P95 yanıt süresi < 2 saniye."},
    {"code": "REQ-NFR-002", "title": "Sistem kullanılabilirliği >= %99.5", "req_type": "non_functional", "priority": "must_have", "status": "approved", "module": "Basis", "fit_gap": "fit", "description": "Yıllık planlı bakım hariç %99.5 uptime SLA."},
    # Integration
    {"code": "REQ-INT-001", "title": "e-Fatura / e-İrsaliye GIB entegrasyonu", "req_type": "integration", "priority": "must_have", "status": "approved", "module": "SD", "fit_gap": "gap", "description": "GİB e-Fatura, e-İrsaliye, e-Arşiv entegrasyonu. UBL-TR formatı."},
    {"code": "REQ-INT-002", "title": "MES entegrasyonu (üretim verileri)", "req_type": "integration", "priority": "should_have", "status": "in_progress", "module": "PP", "fit_gap": "gap", "description": "MES ↔ SAP PP entegrasyonu. Üretim onayları, hurda bildirimi, OEE verileri."},
    {"code": "REQ-INT-003", "title": "WMS entegrasyonu (depo yönetimi)", "req_type": "integration", "priority": "should_have", "status": "draft", "module": "MM", "fit_gap": "gap", "description": "WMS ↔ SAP EWM entegrasyonu. Mal giriş/çıkış, stok transferi."},
    {"code": "REQ-INT-004", "title": "Banka SWIFT/MT940 otomatik mutabakat", "req_type": "integration", "priority": "could_have", "status": "draft", "module": "FI", "fit_gap": "gap", "description": "Banka hesap özeti otomatik yükleme ve mutabakat. MT940/camt.053 formatı."},
]

SPRINTS = [
    {
        "name": "Sprint 1 — Temel Konfigürasyon",
        "goal": "FI/CO, MM, SD temel konfigürasyon. Şirket kodu, tesis, depo tanımları.",
        "status": "completed", "start_date": "2026-01-06", "end_date": "2026-01-17",
        "capacity_points": 40, "velocity": 38, "order": 1,
    },
    {
        "name": "Sprint 2 — WRICEF Geliştirme Başlangıç",
        "goal": "İlk 8 WRICEF nesnesi geliştirme. e-Fatura arayüzü, satınalma iş akışı.",
        "status": "completed", "start_date": "2026-01-20", "end_date": "2026-01-31",
        "capacity_points": 45, "velocity": 42, "order": 2,
    },
    {
        "name": "Sprint 3 — Entegrasyon Sprint",
        "goal": "BTP arayüzleri, veri göçü hazırlık, raporlama geliştirme.",
        "status": "active", "start_date": "2026-02-03", "end_date": "2026-02-14",
        "capacity_points": 50, "velocity": None, "order": 3,
    },
]

# Backlog items: 25 total — various WRICEF types, statuses, and sprints
BACKLOG_ITEMS = [
    # ── Workflows (W) ──
    {"code": "WF-MM-001", "title": "Satınalma siparişi onay iş akışı", "wricef_type": "workflow", "module": "MM",
     "status": "closed", "priority": "critical", "story_points": 8, "estimated_hours": 40, "actual_hours": 36,
     "complexity": "high", "assigned_to": "Emre Koç", "sprint_idx": 0,
     "description": "4 kademeli tutar bazlı onay: <₺10K otomatik, <₺100K bölüm müdürü, <₺500K direktör, ≥₺500K CEO.",
     "transaction_code": "ME21N", "package": "ZMM_WF", "acceptance_criteria": "4 seviye test edilmeli\nProxy onay çalışmalı"},
    {"code": "WF-FI-001", "title": "Fatura onay iş akışı", "wricef_type": "workflow", "module": "FI",
     "status": "deploy", "priority": "high", "story_points": 5, "estimated_hours": 24, "actual_hours": 20,
     "complexity": "medium", "assigned_to": "Emre Koç", "sprint_idx": 1,
     "description": "Gelen fatura 3 kademeli onay süreci. Tutar ve maliyet merkezi bazlı yönlendirme."},
    {"code": "WF-SD-001", "title": "Kredi limit aşımı onay iş akışı", "wricef_type": "workflow", "module": "SD",
     "status": "build", "priority": "medium", "story_points": 5, "estimated_hours": 24,
     "complexity": "medium", "assigned_to": "Emre Koç", "sprint_idx": 2},
    {"code": "WF-HR-001", "title": "İzin talep onay iş akışı", "wricef_type": "workflow", "module": "HCM",
     "status": "new", "priority": "low", "story_points": 3, "estimated_hours": 16,
     "complexity": "low", "assigned_to": ""},
    # ── Reports (R) ──
    {"code": "RPT-FI-001", "title": "Konsolide bilanço raporu (IFRS/TFRS)", "wricef_type": "report", "module": "FI",
     "status": "test", "priority": "critical", "story_points": 13, "estimated_hours": 64, "actual_hours": 58,
     "complexity": "very_high", "assigned_to": "Ahmet Demir", "sprint_idx": 1,
     "description": "Çoklu şirket kodu konsolide bilanço. IFRS ve TFRS paralel raporlama. Döviz çevrimi."},
    {"code": "RPT-FI-002", "title": "Yaşlandırma raporu (müşteri/tedarikçi)", "wricef_type": "report", "module": "FI",
     "status": "closed", "priority": "high", "story_points": 5, "estimated_hours": 24, "actual_hours": 22,
     "complexity": "medium", "assigned_to": "Ahmet Demir", "sprint_idx": 0},
    {"code": "RPT-MM-001", "title": "Stok devir hızı analiz raporu", "wricef_type": "report", "module": "MM",
     "status": "build", "priority": "medium", "story_points": 5, "estimated_hours": 24,
     "complexity": "medium", "assigned_to": "Fatma Çelik", "sprint_idx": 2},
    {"code": "RPT-SD-001", "title": "Satış performans dashboard (Fiori)", "wricef_type": "report", "module": "SD",
     "status": "design", "priority": "high", "story_points": 8, "estimated_hours": 40,
     "complexity": "high", "assigned_to": "Fatma Çelik"},
    {"code": "RPT-PP-001", "title": "Üretim verimliliği OEE raporu", "wricef_type": "report", "module": "PP",
     "status": "new", "priority": "medium", "story_points": 8, "estimated_hours": 40,
     "complexity": "high", "assigned_to": ""},
    # ── Interfaces (I) ──
    {"code": "INT-SD-001", "title": "e-Fatura / e-İrsaliye GIB arayüzü", "wricef_type": "interface", "module": "SD",
     "status": "test", "priority": "critical", "story_points": 13, "estimated_hours": 80, "actual_hours": 72,
     "complexity": "very_high", "assigned_to": "Selin Doğan", "sprint_idx": 1,
     "description": "GİB e-Fatura, e-İrsaliye, e-Arşiv giden/gelen. UBL-TR 1.2 formatı. BTP CPI iFlow.",
     "transaction_code": "VF01", "package": "ZSD_EINVOICE"},
    {"code": "INT-PP-001", "title": "MES → SAP PP üretim onay arayüzü", "wricef_type": "interface", "module": "PP",
     "status": "build", "priority": "high", "story_points": 8, "estimated_hours": 48,
     "complexity": "high", "assigned_to": "Selin Doğan", "sprint_idx": 2,
     "description": "MES sisteminden üretim onayları, hurda bildirimi. OData + BTP CPI."},
    {"code": "INT-MM-001", "title": "WMS ↔ EWM stok senkronizasyonu", "wricef_type": "interface", "module": "MM",
     "status": "design", "priority": "high", "story_points": 8, "estimated_hours": 48,
     "complexity": "high", "assigned_to": "Selin Doğan"},
    {"code": "INT-FI-001", "title": "Banka hesap özeti (MT940) arayüzü", "wricef_type": "interface", "module": "FI",
     "status": "new", "priority": "medium", "story_points": 5, "estimated_hours": 32,
     "complexity": "medium", "assigned_to": ""},
    {"code": "INT-FI-002", "title": "Ödeme dosyası gönderim (SWIFT)", "wricef_type": "interface", "module": "FI",
     "status": "new", "priority": "medium", "story_points": 5, "estimated_hours": 32,
     "complexity": "medium", "assigned_to": ""},
    # ── Conversions (C) ──
    {"code": "CNV-MD-001", "title": "Müşteri ana veri göçü (12,000 kayıt)", "wricef_type": "conversion", "module": "SD",
     "status": "test", "priority": "critical", "story_points": 8, "estimated_hours": 48, "actual_hours": 44,
     "complexity": "high", "assigned_to": "Can Yıldırım", "sprint_idx": 1,
     "description": "ECC BP_CUSTOMER → S/4 Business Partner göçü. 12K aktif müşteri + adres + iletişim."},
    {"code": "CNV-MD-002", "title": "Malzeme ana veri göçü (45,000 kayıt)", "wricef_type": "conversion", "module": "MM",
     "status": "build", "priority": "critical", "story_points": 13, "estimated_hours": 64,
     "complexity": "very_high", "assigned_to": "Can Yıldırım", "sprint_idx": 2,
     "description": "MARA/MARC/MARD → S/4 malzeme göçü. MRP görünümleri, depo verileri dahil."},
    {"code": "CNV-MD-003", "title": "Tedarikçi ana veri göçü (3,500 kayıt)", "wricef_type": "conversion", "module": "MM",
     "status": "design", "priority": "high", "story_points": 5, "estimated_hours": 32,
     "complexity": "medium", "assigned_to": "Can Yıldırım"},
    {"code": "CNV-FI-001", "title": "Açık kalem (AP/AR) göçü", "wricef_type": "conversion", "module": "FI",
     "status": "new", "priority": "high", "story_points": 8, "estimated_hours": 40,
     "complexity": "high", "assigned_to": ""},
    # ── Enhancements (E) ──
    {"code": "ENH-FI-001", "title": "Otomatik vergi hesaplama BAdI", "wricef_type": "enhancement", "module": "FI",
     "status": "closed", "priority": "critical", "story_points": 5, "estimated_hours": 24, "actual_hours": 20,
     "complexity": "medium", "assigned_to": "Emre Koç", "sprint_idx": 0,
     "description": "KDV + ÖTV + ÖİV otomatik hesaplama. Malzeme tipi + iş ortağı lokasyonu bazlı.",
     "transaction_code": "FB01", "package": "ZFI_TAX"},
    {"code": "ENH-SD-001", "title": "Özel fiyatlandırma koşul tipi", "wricef_type": "enhancement", "module": "SD",
     "status": "deploy", "priority": "high", "story_points": 5, "estimated_hours": 24, "actual_hours": 22,
     "complexity": "medium", "assigned_to": "Emre Koç", "sprint_idx": 1},
    {"code": "ENH-MM-001", "title": "Satınalma talep otomatik oluşturma", "wricef_type": "enhancement", "module": "MM",
     "status": "build", "priority": "medium", "story_points": 5, "estimated_hours": 24,
     "complexity": "medium", "assigned_to": "Emre Koç", "sprint_idx": 2},
    {"code": "ENH-PP-001", "title": "Üretim emri otomatik serbest bırakma", "wricef_type": "enhancement", "module": "PP",
     "status": "new", "priority": "medium", "story_points": 3, "estimated_hours": 16,
     "complexity": "low", "assigned_to": ""},
    # ── Forms (F) ──
    {"code": "FRM-SD-001", "title": "Teslimat irsaliyesi (Adobe Form)", "wricef_type": "form", "module": "SD",
     "status": "closed", "priority": "high", "story_points": 5, "estimated_hours": 24, "actual_hours": 20,
     "complexity": "medium", "assigned_to": "Emre Koç", "sprint_idx": 0,
     "description": "A4 teslimat irsaliyesi. Şirket logosu, barkod, imza alanı. Adobe Forms."},
    {"code": "FRM-MM-001", "title": "Satınalma siparişi formu (Adobe Form)", "wricef_type": "form", "module": "MM",
     "status": "test", "priority": "medium", "story_points": 3, "estimated_hours": 16, "actual_hours": 14,
     "complexity": "low", "assigned_to": "Emre Koç", "sprint_idx": 1},
    {"code": "FRM-FI-001", "title": "Banka ödeme dekontu (SmartForms)", "wricef_type": "form", "module": "FI",
     "status": "design", "priority": "low", "story_points": 3, "estimated_hours": 16,
     "complexity": "low", "assigned_to": ""},
]

CONFIG_ITEMS = [
    {"code": "CFG-FI-001", "title": "Şirket kodu tanımlama (1000, 2000, 3000)", "module": "FI",
     "config_key": "SPRO > Enterprise Structure > Definition > Financial Accounting > Define Company Code",
     "transaction_code": "OX02", "status": "closed", "priority": "critical", "complexity": "low",
     "estimated_hours": 4, "actual_hours": 3, "assigned_to": "Ahmet Demir"},
    {"code": "CFG-FI-002", "title": "Hesap planı tanımlama (CATA — Türkiye)", "module": "FI",
     "config_key": "SPRO > FI > General Ledger > G/L Accounts > Master Data > Define Chart of Accounts",
     "transaction_code": "OB13", "status": "closed", "priority": "critical", "complexity": "medium",
     "estimated_hours": 8, "actual_hours": 7, "assigned_to": "Ahmet Demir"},
    {"code": "CFG-FI-003", "title": "KDV vergi kodları (%1, %10, %20, muaf)", "module": "FI",
     "config_key": "SPRO > FI > Tax > Define Tax Codes for Sales and Purchases",
     "transaction_code": "FTXP", "status": "deploy", "priority": "critical", "complexity": "medium",
     "estimated_hours": 6, "actual_hours": 5, "assigned_to": "Ahmet Demir"},
    {"code": "CFG-MM-001", "title": "Satınalma organizasyonu tanımlama", "module": "MM",
     "config_key": "SPRO > Enterprise Structure > Definition > MM > Define Purchasing Organization",
     "transaction_code": "OX08", "status": "closed", "priority": "high", "complexity": "low",
     "estimated_hours": 2, "actual_hours": 2, "assigned_to": "Fatma Çelik"},
    {"code": "CFG-MM-002", "title": "Malzeme türü tanımlama (ZRAW, ZFRT, ZHLB)", "module": "MM",
     "config_key": "SPRO > Logistics > MM > Master Data > Material > Define Material Types",
     "transaction_code": "OMS2", "status": "test", "priority": "high", "complexity": "medium",
     "estimated_hours": 8, "actual_hours": 7, "assigned_to": "Fatma Çelik"},
    {"code": "CFG-SD-001", "title": "Satış organizasyonu ve dağıtım kanalı", "module": "SD",
     "config_key": "SPRO > Enterprise Structure > Definition > SD > Define Sales Organization",
     "transaction_code": "OVX5", "status": "closed", "priority": "high", "complexity": "low",
     "estimated_hours": 4, "actual_hours": 3, "assigned_to": "Fatma Çelik"},
    {"code": "CFG-SD-002", "title": "Fiyatlandırma prosedürü (ZPRC01)", "module": "SD",
     "config_key": "SPRO > SD > Basic Functions > Pricing > Pricing Control > Define Pricing Procedure",
     "transaction_code": "V/08", "status": "build", "priority": "critical", "complexity": "high",
     "estimated_hours": 16, "assigned_to": "Fatma Çelik"},
    {"code": "CFG-PP-001", "title": "Üretim emri tipi tanımlama (ZPP1, ZPP2)", "module": "PP",
     "config_key": "SPRO > Production > Shop Floor Control > Define Order Types",
     "transaction_code": "OPJH", "status": "build", "priority": "high", "complexity": "medium",
     "estimated_hours": 6, "assigned_to": "Ali Öztürk"},
    {"code": "CFG-PP-002", "title": "MRP kontrol parametreleri (tesis bazlı)", "module": "PP",
     "config_key": "SPRO > Production > MRP > Plant Parameters > Define MRP Control Parameters",
     "transaction_code": "OPPQ", "status": "design", "priority": "high", "complexity": "medium",
     "estimated_hours": 8, "assigned_to": "Ali Öztürk"},
    {"code": "CFG-BASIS-001", "title": "Yetkilendirme rol tanımlama (SAP_FIORI_*)", "module": "Basis",
     "config_key": "PFCG Role Maintenance — Fiori Catalog/Group based roles",
     "transaction_code": "PFCG", "status": "design", "priority": "critical", "complexity": "high",
     "estimated_hours": 40, "assigned_to": "Zeynep Arslan"},
]


# ═════════════════════════════════════════════════════════════════════════════
# SEED FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def _p(msg, verbose):
    if verbose:
        print(msg)


def seed_all(app, append=False, verbose=False):
    """Seed ALL tables with demo data."""
    with app.app_context():
        if not append:
            print("🗑️  Clearing existing data...")
            for model in [Notification, Decision, Issue, Action, Risk,
                          TestExecution, Defect, TestCase, TestCycle, TestPlan,
                          TechnicalSpec, FunctionalSpec, ConfigItem, BacklogItem,
                          Sprint, RequirementTrace, Requirement,
                          Analysis, ScopeItem, Process,
                          Workshop,
                          Scenario, Committee, TeamMember, Workstream, Gate, Phase, Program]:
                db.session.query(model).delete()
            db.session.commit()
            print("   Done.\n")

        # ── 1. Program ───────────────────────────────────────────────────
        print("📦 Creating program...")
        program = Program(**PROGRAM_DATA)
        db.session.add(program)
        db.session.flush()
        pid = program.id
        print(f"   ✅ Program: {program.name} (ID: {pid})")

        # ── 2. Phases + Gates ────────────────────────────────────────────
        print("\n📅 Creating phases & gates...")
        phase_ids = {}
        for p_data in PHASES:
            phase = Phase(
                program_id=pid,
                name=p_data["name"],
                description=p_data["description"],
                order=p_data["order"],
                status=p_data["status"],
            )
            db.session.add(phase)
            db.session.flush()
            phase_ids[p_data["name"]] = phase.id
            _p(f"   📅 Phase: {phase.name} ({phase.status})", verbose)
            for g_data in p_data.get("gates", []):
                gate = Gate(
                    phase_id=phase.id,
                    name=g_data["name"],
                    gate_type=g_data["gate_type"],
                    status=g_data.get("status", "not_started"),
                    criteria=g_data.get("criteria", ""),
                )
                db.session.add(gate)
                _p(f"      🚪 Gate: {gate.name}", verbose)
        print(f"   ✅ {len(PHASES)} phases, {sum(len(p.get('gates', [])) for p in PHASES)} gates")

        # ── 3. Workstreams ───────────────────────────────────────────────
        print("\n🔧 Creating workstreams...")
        ws_ids = {}
        for ws_data in WORKSTREAMS:
            ws = Workstream(program_id=pid, **ws_data)
            db.session.add(ws)
            db.session.flush()
            ws_ids[ws_data["name"]] = ws.id
            _p(f"   🔧 {ws.name} ({ws.ws_type})", verbose)
        print(f"   ✅ {len(WORKSTREAMS)} workstreams")

        # ── 4. Team Members ──────────────────────────────────────────────
        print("\n👥 Creating team members...")
        for tm_data in TEAM_MEMBERS:
            tm = TeamMember(program_id=pid, **tm_data)
            db.session.add(tm)
            _p(f"   👤 {tm.name} — {tm.role}", verbose)
        print(f"   ✅ {len(TEAM_MEMBERS)} team members")

        # ── 5. Committees ────────────────────────────────────────────────
        print("\n🏛️  Creating committees...")
        for c_data in COMMITTEES:
            comm = Committee(program_id=pid, **c_data)
            db.session.add(comm)
            _p(f"   🏛️  {comm.name}", verbose)
        print(f"   ✅ {len(COMMITTEES)} committees")

        # ── 6. Scenarios + Workshops ─────────────────────────────────────
        print("\n🔮 Creating scenarios & workshops...")
        scenario_ids = {}
        total_workshops = 0
        for s_data in SCENARIOS:
            ws_list = s_data.pop("workshops", [])
            scenario = Scenario(program_id=pid, **s_data)
            db.session.add(scenario)
            db.session.flush()
            scenario_ids[s_data["name"]] = scenario.id
            _p(f"   🔮 Scenario: {scenario.name} ({scenario.status})", verbose)
            for w_data in ws_list:
                workshop = Workshop(scenario_id=scenario.id, **w_data)
                db.session.add(workshop)
                total_workshops += 1
            scenario.total_workshops = len(ws_list)
            # Restore workshops for potential re-run
            s_data["workshops"] = ws_list
        print(f"   ✅ {len(SCENARIOS)} scenarios, {total_workshops} workshops")

        # ── 6b. Processes, Scope Items, Analyses ─────────────────────────
        print("\n🔍 Creating processes, scope items & analyses...")
        # Pick the first scenario for the process tree
        first_sid = list(scenario_ids.values())[0]

        PROCESS_SEED = [
            {"name": "Order to Cash (O2C)", "level": "L1", "module": "SD",
             "process_id_code": "O2C", "order": 1, "children": [
                 {"name": "Sales Order Processing", "level": "L2", "module": "SD", "order": 1,
                  "scope_items": [
                      {"code": "1OC", "name": "Standard Sales Order", "status": "in_scope",
                       "sap_reference": "BP-1OC", "priority": "high", "module": "SD",
                       "analyses": [
                           {"name": "Sales Order Fit-Gap Workshop", "analysis_type": "fit_gap",
                            "status": "completed", "fit_gap_result": "fit",
                            "decision": "Standard SAP config yeterli.",
                            "attendees": "A. Yılmaz, M. Kaya", "date": date(2025, 2, 10)},
                       ]},
                      {"code": "2OC", "name": "Third-Party Order", "status": "deferred",
                       "sap_reference": "BP-2OC", "priority": "low", "module": "SD"},
                  ]},
                 {"name": "Billing & Invoicing", "level": "L2", "module": "SD", "order": 2,
                  "scope_items": [
                      {"code": "3OC", "name": "Invoice Processing", "status": "in_scope",
                       "sap_reference": "BP-3OC", "priority": "high", "module": "SD",
                       "analyses": [
                           {"name": "Billing Fit-Gap", "analysis_type": "workshop",
                            "status": "completed", "fit_gap_result": "partial_fit",
                            "decision": "Fatura şablonları özelleştirilecek.",
                            "attendees": "A. Yılmaz, B. Demir", "date": date(2025, 2, 15)},
                       ]},
                  ]},
             ]},
            {"name": "Procure to Pay (P2P)", "level": "L1", "module": "MM",
             "process_id_code": "P2P", "order": 2, "children": [
                 {"name": "Purchase Order Processing", "level": "L2", "module": "MM", "order": 1,
                  "scope_items": [
                      {"code": "1PP", "name": "Standard Purchase Order", "status": "in_scope",
                       "sap_reference": "BP-1PP", "priority": "high", "module": "MM",
                       "analyses": [
                           {"name": "PO Workshop", "analysis_type": "workshop",
                            "status": "completed", "fit_gap_result": "fit",
                            "decision": "Standart SAP süreçleri kullanılacak.",
                            "attendees": "C. Öz, D. Ak", "date": date(2025, 2, 20)},
                       ]},
                  ]},
                 {"name": "Invoice Verification", "level": "L2", "module": "MM", "order": 2,
                  "scope_items": [
                      {"code": "2PP", "name": "Logistics Invoice Verification", "status": "in_scope",
                       "sap_reference": "BP-2PP", "priority": "medium", "module": "MM"},
                  ]},
             ]},
            {"name": "Record to Report (R2R)", "level": "L1", "module": "FI",
             "process_id_code": "R2R", "order": 3, "children": [
                 {"name": "General Ledger Accounting", "level": "L2", "module": "FI", "order": 1,
                  "scope_items": [
                      {"code": "1RR", "name": "GL Posting & Period Close", "status": "in_scope",
                       "sap_reference": "BP-1RR", "priority": "critical", "module": "FI",
                       "analyses": [
                           {"name": "FI Fit-Gap Workshop", "analysis_type": "fit_gap",
                            "status": "completed", "fit_gap_result": "gap",
                            "decision": "Türk VUK uyumu için ek geliştirme gerekli.",
                            "attendees": "E. Şahin, F. Güneş", "date": date(2025, 3, 1)},
                       ]},
                  ]},
                 {"name": "Asset Accounting", "level": "L2", "module": "FI", "order": 2,
                  "scope_items": [
                      {"code": "2RR", "name": "Fixed Asset Management", "status": "in_scope",
                       "sap_reference": "BP-2RR", "priority": "high", "module": "FI"},
                  ]},
             ]},
            {"name": "Plan to Produce (P2P-MFG)", "level": "L1", "module": "PP",
             "process_id_code": "P2P-MFG", "order": 4, "children": [
                 {"name": "Production Planning", "level": "L2", "module": "PP", "order": 1,
                  "scope_items": [
                      {"code": "1PM", "name": "MRP & Demand Planning", "status": "in_scope",
                       "sap_reference": "BP-1PM", "priority": "high", "module": "PP"},
                  ]},
             ]},
        ]

        proc_count = 0
        si_count = 0
        an_count = 0

        def _seed_process(parent_id, proc_data, sid):
            nonlocal proc_count, si_count, an_count
            children = proc_data.pop("children", [])
            scope_items = proc_data.pop("scope_items", [])
            p = Process(scenario_id=sid, parent_id=parent_id, **proc_data)
            db.session.add(p)
            db.session.flush()
            proc_count += 1
            _p(f"   🔍 Process [{p.level}]: {p.name}", verbose)
            for si_data in scope_items:
                analyses = si_data.pop("analyses", [])
                si = ScopeItem(process_id=p.id, **si_data)
                db.session.add(si)
                db.session.flush()
                si_count += 1
                for a_data in analyses:
                    a = Analysis(scope_item_id=si.id, **a_data)
                    db.session.add(a)
                    an_count += 1
                si_data["analyses"] = analyses  # restore
            # Recurse children
            for child in children:
                _seed_process(p.id, child, sid)
            proc_data["children"] = children
            proc_data["scope_items"] = scope_items

        for proc_data in PROCESS_SEED:
            _seed_process(None, proc_data, first_sid)
        db.session.flush()
        print(f"   ✅ {proc_count} processes, {si_count} scope items, {an_count} analyses")

        # ── 7. Requirements ──────────────────────────────────────────────
        print("\n📋 Creating requirements...")
        req_ids = {}
        for r_data in REQUIREMENTS:
            req = Requirement(program_id=pid, **r_data)
            db.session.add(req)
            db.session.flush()
            req_ids[r_data["code"]] = req.id
            _p(f"   📋 {req.code}: {req.title[:60]} ({req.status})", verbose)
        print(f"   ✅ {len(REQUIREMENTS)} requirements")

        # ── 8. Requirement Traces ────────────────────────────────────────
        print("\n🔗 Creating requirement traces...")
        traces = [
            # Business reqs → Explore phase
            {"req_code": "REQ-BIZ-001", "target_type": "phase", "target_name": "Explore", "trace_type": "derived_from"},
            {"req_code": "REQ-BIZ-002", "target_type": "phase", "target_name": "Explore", "trace_type": "derived_from"},
            {"req_code": "REQ-BIZ-003", "target_type": "phase", "target_name": "Explore", "trace_type": "derived_from"},
            {"req_code": "REQ-BIZ-004", "target_type": "phase", "target_name": "Realize", "trace_type": "implements"},
            # Functional reqs → Workstreams
            {"req_code": "REQ-FI-001", "target_type": "workstream", "target_name": "Finance (FI/CO)", "trace_type": "implements"},
            {"req_code": "REQ-FI-002", "target_type": "workstream", "target_name": "Finance (FI/CO)", "trace_type": "implements"},
            {"req_code": "REQ-MM-001", "target_type": "workstream", "target_name": "Materials Management (MM)", "trace_type": "implements"},
            {"req_code": "REQ-SD-001", "target_type": "workstream", "target_name": "Sales & Distribution (SD)", "trace_type": "implements"},
            # Technical reqs → Scenarios
            {"req_code": "REQ-TEC-001", "target_type": "scenario", "target_name": "Greenfield — S/4HANA Cloud (Seçilen)", "trace_type": "related_to"},
            {"req_code": "REQ-TEC-002", "target_type": "scenario", "target_name": "Greenfield — S/4HANA Cloud (Seçilen)", "trace_type": "related_to"},
            # Integration reqs → Integration workstream
            {"req_code": "REQ-INT-001", "target_type": "workstream", "target_name": "Integration (BTP)", "trace_type": "implements"},
            {"req_code": "REQ-INT-002", "target_type": "workstream", "target_name": "Integration (BTP)", "trace_type": "implements"},
        ]
        trace_count = 0
        for t in traces:
            req_id = req_ids.get(t["req_code"])
            if not req_id:
                continue
            if t["target_type"] == "phase":
                target_id = phase_ids.get(t["target_name"])
            elif t["target_type"] == "workstream":
                target_id = ws_ids.get(t["target_name"])
            elif t["target_type"] == "scenario":
                target_id = scenario_ids.get(t["target_name"])
            else:
                target_id = None
            if target_id:
                trace = RequirementTrace(
                    requirement_id=req_id,
                    target_type=t["target_type"],
                    target_id=target_id,
                    trace_type=t["trace_type"],
                )
                db.session.add(trace)
                trace_count += 1
                _p(f"   🔗 {t['req_code']} → {t['target_type']}:{t['target_name']}", verbose)
        print(f"   ✅ {trace_count} traces")

        # ── 9. Sprints ───────────────────────────────────────────────────
        print("\n🏃 Creating sprints...")
        sprint_objs = []
        for s_data in SPRINTS:
            sprint = Sprint(
                program_id=pid,
                name=s_data["name"],
                goal=s_data["goal"],
                status=s_data["status"],
                start_date=date.fromisoformat(s_data["start_date"]),
                end_date=date.fromisoformat(s_data["end_date"]),
                capacity_points=s_data["capacity_points"],
                velocity=s_data["velocity"],
                order=s_data["order"],
            )
            db.session.add(sprint)
            db.session.flush()
            sprint_objs.append(sprint)
            _p(f"   🏃 {sprint.name} ({sprint.status})", verbose)
        print(f"   ✅ {len(SPRINTS)} sprints")

        # ── 10. Backlog Items (WRICEF) ───────────────────────────────────
        print("\n📝 Creating backlog items (WRICEF)...")
        # Map requirement codes to backlog items for linking
        req_link_map = {
            "WF-MM-001": "REQ-MM-001",
            "WF-FI-001": "REQ-FI-002",
            "INT-SD-001": "REQ-INT-001",
            "INT-PP-001": "REQ-INT-002",
            "INT-MM-001": "REQ-INT-003",
            "INT-FI-001": "REQ-INT-004",
            "CNV-MD-001": "REQ-TEC-002",
            "CNV-MD-002": "REQ-TEC-002",
            "CNV-MD-003": "REQ-TEC-002",
            "ENH-FI-001": "REQ-FI-001",
            "RPT-FI-001": "REQ-BIZ-001",
            "RPT-FI-002": "REQ-BIZ-001",
            "FRM-SD-001": "REQ-SD-001",
        }
        backlog_objs = {}
        for bi_data in BACKLOG_ITEMS:
            sprint_idx = bi_data.pop("sprint_idx", None)
            sprint_id = sprint_objs[sprint_idx].id if sprint_idx is not None else None
            req_code = req_link_map.get(bi_data["code"])
            req_id = req_ids.get(req_code) if req_code else None
            bi = BacklogItem(
                program_id=pid,
                sprint_id=sprint_id,
                requirement_id=req_id,
                **bi_data,
            )
            db.session.add(bi)
            db.session.flush()
            backlog_objs[bi_data["code"]] = bi
            _p(f"   📝 [{bi.wricef_type.upper()[0]}] {bi.code}: {bi.title[:50]} ({bi.status})", verbose)
        print(f"   ✅ {len(BACKLOG_ITEMS)} backlog items")

        # ── 11. Config Items ─────────────────────────────────────────────
        print("\n⚙️  Creating config items...")
        # Link some config items to requirements
        cfg_req_map = {
            "CFG-FI-003": "REQ-FI-001",
            "CFG-MM-002": "REQ-MM-001",
            "CFG-SD-002": "REQ-SD-001",
            "CFG-BASIS-001": "REQ-TEC-003",
        }
        config_objs = {}
        for ci_data in CONFIG_ITEMS:
            req_code = cfg_req_map.get(ci_data["code"])
            req_id = req_ids.get(req_code) if req_code else None
            ci = ConfigItem(program_id=pid, requirement_id=req_id, **ci_data)
            db.session.add(ci)
            db.session.flush()
            config_objs[ci_data["code"]] = ci
            _p(f"   ⚙️  {ci.code}: {ci.title[:50]} ({ci.status})", verbose)
        print(f"   ✅ {len(CONFIG_ITEMS)} config items")

        # ── 12. Functional Specs ─────────────────────────────────────────
        print("\n📄 Creating functional specs...")
        fs_data_list = [
            # FS for backlog items
            {"backlog_code": "WF-MM-001", "title": "FS — Satınalma Siparişi Onay İş Akışı",
             "status": "approved", "author": "Fatma Çelik", "reviewer": "Ahmet Demir", "approved_by": "Mehmet Yılmaz",
             "content": "## 1. Amaç\nSatınalma siparişleri için tutar bazlı 4 kademeli onay iş akışı.\n\n## 2. Süreç Akışı\n- <₺10K: Otomatik onay\n- <₺100K: Bölüm müdürü\n- <₺500K: Direktör\n- ≥₺500K: CEO\n\n## 3. İş Kuralları\n- Proxy onay desteklenir\n- 48 saat içinde yanıt verilmezse escalation"},
            {"backlog_code": "INT-SD-001", "title": "FS — e-Fatura GIB Entegrasyonu",
             "status": "approved", "author": "Selin Doğan", "reviewer": "Ayşe Kaya", "approved_by": "Mehmet Yılmaz",
             "content": "## 1. Amaç\nGİB e-Fatura, e-İrsaliye, e-Arşiv entegrasyonu. UBL-TR 1.2 formatı.\n\n## 2. Arayüz Tasarımı\n- Giden fatura: SAP SD VF01 → BTP CPI → GİB\n- Gelen fatura: GİB → BTP CPI → SAP FI\n\n## 3. Hata Yönetimi\n- Retry: 3 deneme\n- Dead letter queue\n- Manuel işlem ekranı"},
            {"backlog_code": "RPT-FI-001", "title": "FS — Konsolide Bilanço Raporu",
             "status": "in_review", "author": "Ahmet Demir", "reviewer": "Mehmet Yılmaz",
             "content": "## 1. Amaç\nIFRS ve TFRS'ye uygun konsolide mali tablolar.\n\n## 2. Raporlama Yapısı\n- Bilanço, Gelir Tablosu, Nakit Akış\n- Şirket bazlı + konsolide\n- Döviz çevrimi (closing/average rate)"},
            {"backlog_code": "CNV-MD-001", "title": "FS — Müşteri Ana Veri Göçü",
             "status": "approved", "author": "Can Yıldırım", "reviewer": "Fatma Çelik", "approved_by": "Ayşe Kaya",
             "content": "## 1. Kapsam\n12,000 aktif müşteri kaydı göçü.\n\n## 2. Kaynak → Hedef Eşleme\n- KNA1 → BP General\n- KNVV → BP Sales\n- KNVK → Contact Person\n\n## 3. Doğrulama Kuralları\n- Vergi no zorunlu\n- Adres tam olmalı"},
            {"backlog_code": "ENH-FI-001", "title": "FS — Otomatik Vergi Hesaplama BAdI",
             "status": "approved", "author": "Ahmet Demir", "reviewer": "Emre Koç", "approved_by": "Ayşe Kaya",
             "content": "## 1. Amaç\nKDV, ÖTV, ÖİV otomatik hesaplama.\n\n## 2. BAdI Implementasyonu\n- BADI_TAX_CALC enhancement spot\n- Malzeme tipi + lokasyon bazlı kural\n\n## 3. Vergi Kodları\nV1: %20, V2: %10, V3: %1, V0: Muaf"},
            # FS for config items
            {"config_code": "CFG-SD-002", "title": "FS — Fiyatlandırma Prosedürü Konfigürasyonu",
             "status": "in_review", "author": "Fatma Çelik", "reviewer": "Ayşe Kaya",
             "content": "## 1. Amaç\nZPRC01 fiyatlandırma prosedürü.\n\n## 2. Koşul Tipleri\n- PR00: Temel fiyat\n- ZRA0: Müşteri iskontosu\n- ZRB0: Malzeme iskontosu\n- MWST: KDV\n\n## 3. Alt Toplam\n- Subtotal 1: Net fiyat\n- Subtotal 2: İskonto sonrası\n- Subtotal 3: Vergi dahil"},
            {"config_code": "CFG-BASIS-001", "title": "FS — Yetkilendirme Rol Tasarımı",
             "status": "draft", "author": "Zeynep Arslan",
             "content": "## 1. Kapsam\n60 SAP rolü tasarımı.\n\n## 2. Rol Kategorileri\n- SAP_FIORI_BC_*: Temel roller\n- Z_FI_*: Finans rolleri\n- Z_MM_*: MM rolleri\n\n## 3. SOD Kuralları\n- Ödeme oluşturma ≠ Ödeme onay\n- Satınalma talebi ≠ Sipariş onay"},
            {"config_code": "CFG-PP-002", "title": "FS — MRP Kontrol Parametreleri",
             "status": "draft", "author": "Ali Öztürk",
             "content": "## 1. Amaç\nTesis bazlı MRP kontrol parametreleri.\n\n## 2. Parametreler\n- Planlama ufku: 90 gün\n- Lot size: EX (exact)\n- Safety stock: otomatik hesaplama"},
        ]

        fs_objs = {}
        for fs_d in fs_data_list:
            backlog_code = fs_d.pop("backlog_code", None)
            config_code = fs_d.pop("config_code", None)
            fs = FunctionalSpec(
                backlog_item_id=backlog_objs[backlog_code].id if backlog_code else None,
                config_item_id=config_objs[config_code].id if config_code else None,
                **fs_d,
            )
            db.session.add(fs)
            db.session.flush()
            key = backlog_code or config_code
            fs_objs[key] = fs
            _p(f"   📄 FS: {fs.title[:60]} ({fs.status})", verbose)
        print(f"   ✅ {len(fs_data_list)} functional specs")

        # ── 13. Technical Specs ──────────────────────────────────────────
        print("\n📐 Creating technical specs...")
        ts_data_list = [
            {"fs_key": "WF-MM-001", "title": "TS — Satınalma Siparişi Onay WF Teknik Tasarım",
             "status": "approved", "author": "Emre Koç", "reviewer": "Ayşe Kaya", "approved_by": "Ayşe Kaya",
             "content": "## Teknik Detaylar\n- WF Template: WS90000001\n- Agent determination: Rule-based\n- Custom class: ZCL_WF_PO_APPROVAL\n- BAPI: BAPI_PO_APPROVE1",
             "objects_list": "ZCL_WF_PO_APPROVAL\nZIF_WF_PO_AGENT\nZFG_WF_PO (FM group)\nWS90000001 (WF template)",
             "unit_test_evidence": "UT-WF-001: 4 onay seviyesi test — PASS\nUT-WF-002: Proxy onay — PASS\nUT-WF-003: Escalation — PASS"},
            {"fs_key": "INT-SD-001", "title": "TS — e-Fatura GIIB Entegrasyonu Teknik Tasarım",
             "status": "approved", "author": "Selin Doğan", "reviewer": "Ayşe Kaya", "approved_by": "Ayşe Kaya",
             "content": "## Teknik Detaylar\n- iFlow: e-Invoice_Outbound_TR\n- Message mapping: SAP IDoc → UBL-TR 1.2\n- Credential: OAuth 2.0 (GİB portal)\n- Monitoring: BTP Alert Notification",
             "objects_list": "iFlow: e-Invoice_Outbound_TR\niFlow: e-Invoice_Inbound_TR\nValue mapping: Tax_Code_Map\nScript: UBL_TR_Converter.groovy",
             "unit_test_evidence": "UT-INT-001: Giden fatura — PASS\nUT-INT-002: Gelen fatura — PASS\nUT-INT-003: Hata senaryosu — PASS"},
            {"fs_key": "ENH-FI-001", "title": "TS — Otomatik Vergi Hesaplama BAdI Teknik Tasarım",
             "status": "approved", "author": "Emre Koç", "reviewer": "Ahmet Demir", "approved_by": "Ayşe Kaya",
             "content": "## Teknik Detaylar\n- Enhancement Spot: ES_TAX_CALC\n- BAdI: BADI_TAX_CALC\n- Implementation: ZCL_IM_TAX_CALC\n- Table: ZTAX_RULES (custom)",
             "objects_list": "ZCL_IM_TAX_CALC\nZTAX_RULES (config table)\nZFG_TAX_UTILS (FM group)\nZTAX_CALC_MONITOR (report)",
             "unit_test_evidence": "UT-ENH-001: KDV %20 — PASS\nUT-ENH-002: KDV %10 — PASS\nUT-ENH-003: ÖTV hesaplama — PASS"},
            {"fs_key": "CNV-MD-001", "title": "TS — Müşteri Göçü Teknik Tasarım",
             "status": "in_review", "author": "Can Yıldırım", "reviewer": "Ayşe Kaya",
             "content": "## Teknik Detaylar\n- Migration tool: SAP LTMC\n- Template: 2_Business_Partner\n- Source: CSV extract from ECC\n- Staging: BTP HANA DB",
             "objects_list": "LTMC Template: 2_BP_Customer\nStaging table: ZCUST_STAGING\nValidation report: ZCUST_VALIDATE\nCleanup program: ZCUST_CLEANUP"},
            {"fs_key": "CFG-SD-002", "title": "TS — Fiyatlandırma Prosedürü Teknik Detaylar",
             "status": "draft", "author": "Fatma Çelik",
             "content": "## Teknik Detaylar\n- Pricing procedure: ZPRC01\n- Access sequences: custom Z*\n- Condition types: PR00, ZRA0, ZRB0, MWST\n- Routine: 15 (net price calculation)",
             "objects_list": "Pricing procedure: ZPRC01\nAccess sequence: ZACS01\nCondition table: 506\nRequirement routine: 15"},
        ]

        for ts_d in ts_data_list:
            fs_key = ts_d.pop("fs_key")
            fs = fs_objs.get(fs_key)
            if not fs:
                print(f"   ⚠️  Skipping TS for {fs_key} — no FS found")
                continue
            ts = TechnicalSpec(functional_spec_id=fs.id, **ts_d)
            db.session.add(ts)
            _p(f"   📐 TS: {ts.title[:60]} ({ts.status})", verbose)
        print(f"   ✅ {len(ts_data_list)} technical specs")

        # ── 14. Test Plans ───────────────────────────────────────────────
        print("\n🧪 Creating test plans & cycles...")
        test_plan_data = [
            {"name": "SIT Ana Test Planı", "status": "active",
             "description": "Sistem Entegrasyon Testi ana planı — tüm modüller arası E2E testler.",
             "test_strategy": "Bottom-up entegrasyon: Modül SIT → Cross-module SIT → E2E SIT",
             "entry_criteria": "Tüm birim testleri tamamlanmış, QAS ortamı hazır",
             "exit_criteria": "P1/P2 defect sıfır, P3 <%5, geçiş oranı >%95",
             "start_date": "2025-04-01", "end_date": "2025-05-15",
             "cycles": [
                 {"name": "SIT Cycle 1 — Temel Akışlar", "test_layer": "sit", "status": "completed",
                  "start_date": "2025-04-01", "end_date": "2025-04-15"},
                 {"name": "SIT Cycle 2 — Hata Düzeltme Sonrası", "test_layer": "sit", "status": "in_progress",
                  "start_date": "2025-04-16", "end_date": "2025-04-30"},
             ]},
            {"name": "UAT Planı", "status": "draft",
             "description": "Kullanıcı Kabul Testi — İş birimi sahipleri tarafından yürütülecek.",
             "entry_criteria": "SIT tamamlanmış, P1/P2 sıfır, eğitim tamamlanmış",
             "exit_criteria": "Tüm iş senaryoları onaylanmış, Go/No-Go kararı",
             "start_date": "2025-05-16", "end_date": "2025-06-30",
             "cycles": [
                 {"name": "UAT Cycle 1 — İş Süreçleri", "test_layer": "uat", "status": "planning",
                  "start_date": "2025-05-16", "end_date": "2025-06-15"},
             ]},
            {"name": "Regresyon Test Planı", "status": "draft",
             "description": "Transport taşıma sonrası regresyon testi — kritik senaryolar.",
             "start_date": "2025-06-01", "end_date": "2025-07-31",
             "cycles": [
                 {"name": "Regression Cycle 1", "test_layer": "regression", "status": "planning",
                  "start_date": "2025-06-01", "end_date": "2025-06-15"},
             ]},
        ]

        plan_objs = []
        cycle_objs = []
        for tp_d in test_plan_data:
            cycles_d = tp_d.pop("cycles", [])
            plan = TestPlan(
                program_id=pid,
                name=tp_d["name"],
                description=tp_d.get("description", ""),
                status=tp_d.get("status", "draft"),
                test_strategy=tp_d.get("test_strategy", ""),
                entry_criteria=tp_d.get("entry_criteria", ""),
                exit_criteria=tp_d.get("exit_criteria", ""),
                start_date=date.fromisoformat(tp_d["start_date"]) if tp_d.get("start_date") else None,
                end_date=date.fromisoformat(tp_d["end_date"]) if tp_d.get("end_date") else None,
            )
            db.session.add(plan)
            db.session.flush()
            plan_objs.append(plan)
            _p(f"   🧪 Plan: {plan.name} ({plan.status})", verbose)

            for i, c_d in enumerate(cycles_d):
                cycle = TestCycle(
                    plan_id=plan.id,
                    name=c_d["name"],
                    test_layer=c_d.get("test_layer", "sit"),
                    status=c_d.get("status", "planning"),
                    start_date=date.fromisoformat(c_d["start_date"]) if c_d.get("start_date") else None,
                    end_date=date.fromisoformat(c_d["end_date"]) if c_d.get("end_date") else None,
                    order=i + 1,
                )
                db.session.add(cycle)
                db.session.flush()
                cycle_objs.append(cycle)
                _p(f"      🔄 Cycle: {cycle.name} ({cycle.status})", verbose)

            tp_d["cycles"] = cycles_d  # restore
        total_cycles = sum(len(tp.get("cycles", [])) for tp in test_plan_data)
        print(f"   ✅ {len(test_plan_data)} plans, {total_cycles} cycles")

        # ── 15. Test Cases (Catalog) ─────────────────────────────────────
        print("\n📋 Creating test cases...")
        test_case_data = [
            # FI test cases
            {"code": "TC-FI-0001", "title": "FI — Standart Fatura Kayıt ve Muhasebeleştirme",
             "module": "FI", "test_layer": "sit", "status": "approved", "priority": "high",
             "preconditions": "Şirket kodu, GL hesap planı konfigüre edilmiş",
             "test_steps": "1. FB60 ile tedarikçi faturası gir\n2. Belge numarasını kontrol et\n3. FBL1N ile tedarikçi bakiyesini doğrula",
             "expected_result": "Fatura muhasebeleşmiş, tedarikçi bakiyesi güncel",
             "req_code": "REQ-FI-001", "is_regression": True},
            {"code": "TC-FI-0002", "title": "FI — Otomatik Ödeme Programı (F110)",
             "module": "FI", "test_layer": "sit", "status": "approved", "priority": "high",
             "preconditions": "Açık kalemler mevcut, ödeme yöntemi tanımlı",
             "test_steps": "1. F110 çalıştır\n2. Teklif listesini kontrol et\n3. Ödeme çalıştır\n4. Banka çıkış belgesi kontrol",
             "expected_result": "Ödeme belgeleri oluşmuş, banka transferi tetiklenmiş",
             "req_code": "REQ-FI-002", "is_regression": True},
            {"code": "TC-FI-0003", "title": "FI — Dönem Sonu Kapanış (Aylık)",
             "module": "FI", "test_layer": "sit", "status": "approved", "priority": "medium",
             "test_steps": "1. Dönem sonu işlemleri çalıştır\n2. Kur farkı hesapla\n3. Yeniden değerleme\n4. Mali tablo çıkart",
             "expected_result": "Dönem kapanmış, mali tablolar doğru",
             "req_code": "REQ-BIZ-001"},
            # MM test cases
            {"code": "TC-MM-0001", "title": "MM — Satınalma Talebi → Sipariş → GİB Akışı",
             "module": "MM", "test_layer": "sit", "status": "approved", "priority": "critical",
             "preconditions": "Tedarikçi ve malzeme ana verileri mevcut",
             "test_steps": "1. ME51N ile ST oluştur\n2. ME21N ile sipariş oluştur\n3. Onay akışı tamamla\n4. MIGO ile mal girişi",
             "expected_result": "ST → PO → GR akışı tamamlanmış, stok güncel",
             "req_code": "REQ-MM-001", "is_regression": True},
            {"code": "TC-MM-0002", "title": "MM — Depo Transferi (Tesisler Arası)",
             "module": "MM", "test_layer": "sit", "status": "ready", "priority": "medium",
             "test_steps": "1. MB1B ile transfer emri oluştur\n2. Gönderen tesis stok düş\n3. Alan tesis stok artır",
             "expected_result": "Her iki tesiste stok doğru güncellendi"},
            # SD test cases
            {"code": "TC-SD-0001", "title": "SD — Standart Satış Siparişi → Teslimat → Faturalama",
             "module": "SD", "test_layer": "sit", "status": "approved", "priority": "critical",
             "preconditions": "Müşteri, malzeme, fiyat koşulları mevcut",
             "test_steps": "1. VA01 ile sipariş oluştur\n2. VL01N ile teslimat\n3. VF01 ile fatura\n4. FI belgesi kontrol",
             "expected_result": "O2C akışı tamamlanmış, FI entegrasyonu doğru",
             "req_code": "REQ-SD-001", "is_regression": True},
            {"code": "TC-SD-0002", "title": "SD — e-Fatura GİB Entegrasyonu",
             "module": "SD", "test_layer": "sit", "status": "approved", "priority": "high",
             "test_steps": "1. VF01 ile fatura oluştur\n2. e-Fatura trigger kontrol\n3. GİB yanıtı kontrol\n4. Durum güncelleme",
             "expected_result": "e-Fatura GİB'e iletilmiş, onay alınmış"},
            # PP test cases
            {"code": "TC-PP-0001", "title": "PP — MRP Çalıştırma ve Planlı Sipariş",
             "module": "PP", "test_layer": "sit", "status": "ready", "priority": "high",
             "test_steps": "1. MD01 ile MRP çalıştır\n2. Planlı siparişleri kontrol\n3. CO01 ile üretim emri dönüştür",
             "expected_result": "MRP önerileri oluşmuş, üretim emri oluşturulabilir"},
            # Integration test cases
            {"code": "TC-INT-0001", "title": "INT — P2P End-to-End (MM → FI)",
             "module": "INT", "test_layer": "sit", "status": "approved", "priority": "critical",
             "test_steps": "1. Satınalma talebi → sipariş → mal girişi → fatura doğrulama → ödeme\n2. Tüm FI belgelerini cross-check",
             "expected_result": "P2P E2E akış tamamlanmış, tüm FI kaydları doğru",
             "is_regression": True},
            {"code": "TC-INT-0002", "title": "INT — O2C End-to-End (SD → FI)",
             "module": "INT", "test_layer": "sit", "status": "approved", "priority": "critical",
             "test_steps": "1. Sipariş → teslimat → fatura → tahsilat\n2. Müşteri bakiyesi kontrol",
             "expected_result": "O2C E2E akış tamamlanmış, tahsilat kaydı doğru",
             "is_regression": True},
            # Performance test
            {"code": "TC-PERF-0001", "title": "PERF — MRP Toplu Çalıştırma Performans Testi",
             "module": "PP", "test_layer": "performance", "status": "ready", "priority": "high",
             "test_steps": "1. 10,000 malzeme ile MRP çalıştır\n2. Süreyi ölç\n3. Kaynak kullanımını kontrol",
             "expected_result": "MRP 30 dakika içinde tamamlanmalı"},
            {"code": "TC-PERF-0002", "title": "PERF — Yoğun Dönem Fatura Testi",
             "module": "SD", "test_layer": "performance", "status": "ready", "priority": "medium",
             "test_steps": "1. 500 eşzamanlı sipariş oluştur\n2. Toplu faturalama çalıştır\n3. Performans metriklerini kaydet",
             "expected_result": "500 fatura 15 dakika içinde işlenmeli"},
        ]

        tc_objs = {}
        for tc_d in test_case_data:
            req_code = tc_d.pop("req_code", None)
            req_id = req_ids.get(req_code) if req_code else None
            tc = TestCase(
                program_id=pid,
                requirement_id=req_id,
                code=tc_d["code"],
                title=tc_d["title"],
                module=tc_d.get("module", ""),
                test_layer=tc_d.get("test_layer", "sit"),
                status=tc_d.get("status", "draft"),
                priority=tc_d.get("priority", "medium"),
                preconditions=tc_d.get("preconditions", ""),
                test_steps=tc_d.get("test_steps", ""),
                expected_result=tc_d.get("expected_result", ""),
                is_regression=tc_d.get("is_regression", False),
            )
            db.session.add(tc)
            db.session.flush()
            tc_objs[tc_d["code"]] = tc
            _p(f"   📋 {tc.code}: {tc.title[:50]} ({tc.test_layer})", verbose)
        print(f"   ✅ {len(test_case_data)} test cases")

        # ── 16. Test Executions ──────────────────────────────────────────
        print("\n▶️  Creating test executions...")
        # SIT Cycle 1 executions (completed cycle — most cases executed)
        sit_cycle_1 = cycle_objs[0] if cycle_objs else None
        execution_data = [
            {"tc_code": "TC-FI-0001", "result": "pass", "executed_by": "Fatma Çelik", "duration_minutes": 25},
            {"tc_code": "TC-FI-0002", "result": "pass", "executed_by": "Ahmet Demir", "duration_minutes": 30},
            {"tc_code": "TC-FI-0003", "result": "fail", "executed_by": "Ahmet Demir", "duration_minutes": 45,
             "notes": "Kur farkı hesaplamada yuvarlama hatası tespit edildi"},
            {"tc_code": "TC-MM-0001", "result": "pass", "executed_by": "Selin Doğan", "duration_minutes": 40},
            {"tc_code": "TC-MM-0002", "result": "pass", "executed_by": "Selin Doğan", "duration_minutes": 20},
            {"tc_code": "TC-SD-0001", "result": "pass", "executed_by": "Zeynep Arslan", "duration_minutes": 35},
            {"tc_code": "TC-SD-0002", "result": "fail", "executed_by": "Zeynep Arslan", "duration_minutes": 30,
             "notes": "GİB bağlantı zaman aşımı — retry mekanizması devreye girmedi"},
            {"tc_code": "TC-PP-0001", "result": "blocked", "executed_by": "Ali Öztürk", "duration_minutes": 10,
             "notes": "MRP parametreleri eksik konfigürasyon nedeniyle çalıştırılamadı"},
            {"tc_code": "TC-INT-0001", "result": "pass", "executed_by": "Emre Koç", "duration_minutes": 60},
            {"tc_code": "TC-INT-0002", "result": "pass", "executed_by": "Can Yıldırım", "duration_minutes": 55},
        ]

        exec_count = 0
        if sit_cycle_1:
            for ex_d in execution_data:
                tc = tc_objs.get(ex_d["tc_code"])
                if not tc:
                    continue
                exe = TestExecution(
                    cycle_id=sit_cycle_1.id,
                    test_case_id=tc.id,
                    result=ex_d["result"],
                    executed_by=ex_d.get("executed_by", ""),
                    executed_at=datetime.now(timezone.utc) if ex_d["result"] != "not_run" else None,
                    duration_minutes=ex_d.get("duration_minutes"),
                    notes=ex_d.get("notes", ""),
                )
                db.session.add(exe)
                exec_count += 1
                _p(f"   ▶️  {ex_d['tc_code']}: {ex_d['result']}", verbose)
        print(f"   ✅ {exec_count} executions")

        # ── 17. Defects ──────────────────────────────────────────────────
        print("\n🐛 Creating defects...")
        defect_data = [
            {"code": "DEF-0001", "title": "FI — Kur farkı hesaplamada yuvarlama hatası",
             "severity": "P2", "status": "in_progress", "module": "FI",
             "description": "Dönem sonu kur farkı hesaplamasında 0.01 TRY yuvarlama farkı oluşuyor.",
             "steps_to_reproduce": "1. F.05 çalıştır\n2. Yabancı para bakiyeli hesapları kontrol et\n3. Kur farkı belgesi detaylarını incele",
             "reported_by": "Ahmet Demir", "assigned_to": "Emre Koç",
             "found_in_cycle": "SIT Cycle 1", "environment": "QAS",
             "tc_code": "TC-FI-0003"},
            {"code": "DEF-0002", "title": "SD — e-Fatura GİB entegrasyonunda timeout hatası",
             "severity": "P1", "status": "open", "module": "SD",
             "description": "GİB servisine bağlantıda 30sn timeout sonrası retry tetiklenmiyor.",
             "steps_to_reproduce": "1. VF01 ile fatura oluştur\n2. e-Fatura trigger'ını kontrol et\n3. GİB servisinin kapalı olduğu senaryoda test et",
             "reported_by": "Zeynep Arslan", "assigned_to": "Selin Doğan",
             "found_in_cycle": "SIT Cycle 1", "environment": "QAS",
             "tc_code": "TC-SD-0002"},
            {"code": "DEF-0003", "title": "PP — MRP kontrol parametreleri eksik",
             "severity": "P2", "status": "fixed", "module": "PP",
             "description": "MRP tesis parametreleri konfigüre edilmemiş — planlama çalışmıyor.",
             "reported_by": "Ali Öztürk", "assigned_to": "Ali Öztürk",
             "found_in_cycle": "SIT Cycle 1", "environment": "QAS",
             "resolution": "OMDU'da tesis parametreleri tanımlandı.",
             "tc_code": "TC-PP-0001"},
            {"code": "DEF-0004", "title": "MM — Onay iş akışında proxy atama hatası",
             "severity": "P3", "status": "new", "module": "MM",
             "description": "Proxy onayci atamasında organizasyon hiyerarşisi doğru çekilmiyor.",
             "reported_by": "Selin Doğan", "assigned_to": "Emre Koç",
             "found_in_cycle": "SIT Cycle 1", "environment": "QAS",
             "tc_code": "TC-MM-0001"},
            {"code": "DEF-0005", "title": "INT — P2P fatura doğrulamada tutar uyumsuzluğu",
             "severity": "P3", "status": "new", "module": "INT",
             "description": "3-way match'te sipariş tutarı ile fatura tutarı arasında tolerans kontrolü çalışmıyor.",
             "reported_by": "Can Yıldırım", "assigned_to": "Fatma Çelik",
             "found_in_cycle": "SIT Cycle 1", "environment": "QAS"},
            {"code": "DEF-0006", "title": "FI — Konsolide bilanço raporunda şirket kodu filtresi çalışmıyor",
             "severity": "P3", "status": "reopened", "module": "FI",
             "description": "Raporda şirket kodu filtresi seçildiğinde tüm veriler görünmeye devam ediyor.",
             "reported_by": "Ahmet Demir", "assigned_to": "Ahmet Demir",
             "found_in_cycle": "SIT Cycle 1", "environment": "QAS",
             "reopen_count": 1},
            {"code": "DEF-0007", "title": "SD — Fiyatlandırmada iskonto sıralaması hatalı",
             "severity": "P4", "status": "new", "module": "SD",
             "description": "Müşteri iskontosu malzeme iskontosundan sonra uygulanıyor, sıralama ters.",
             "reported_by": "Zeynep Arslan", "assigned_to": "Fatma Çelik",
             "found_in_cycle": "SIT Cycle 1", "environment": "QAS"},
            {"code": "DEF-0008", "title": "BASIS — Fiori launchpad'de F5 tile'ı görünmüyor",
             "severity": "P4", "status": "closed", "module": "BASIS",
             "description": "Fiori launchpad konfigürasyonunda catalog ataması eksik.",
             "reported_by": "Can Yıldırım", "assigned_to": "Zeynep Arslan",
             "found_in_cycle": "SIT Cycle 1", "environment": "QAS",
             "resolution": "Catalog ve group atamaları /UI2/FLPD_CUST üzerinden yapıldı.",
             "root_cause": "Taşıma sırasında target mapping eksik kalmış."},
        ]

        for d_d in defect_data:
            tc_code = d_d.pop("tc_code", None)
            tc = tc_objs.get(tc_code) if tc_code else None
            defect = Defect(
                program_id=pid,
                test_case_id=tc.id if tc else None,
                code=d_d["code"],
                title=d_d["title"],
                description=d_d.get("description", ""),
                steps_to_reproduce=d_d.get("steps_to_reproduce", ""),
                severity=d_d.get("severity", "P3"),
                status=d_d.get("status", "new"),
                module=d_d.get("module", ""),
                environment=d_d.get("environment", ""),
                reported_by=d_d.get("reported_by", ""),
                assigned_to=d_d.get("assigned_to", ""),
                found_in_cycle=d_d.get("found_in_cycle", ""),
                resolution=d_d.get("resolution", ""),
                root_cause=d_d.get("root_cause", ""),
                reopen_count=d_d.get("reopen_count", 0),
                resolved_at=datetime.now(timezone.utc) if d_d.get("status") in ("closed", "rejected") else None,
            )
            db.session.add(defect)
            _p(f"   🐛 [{d_d['severity']}] {d_d['code']}: {d_d['title'][:50]} ({d_d['status']})", verbose)
        print(f"   ✅ {len(defect_data)} defects")

        # ── RAID: Risks, Actions, Issues, Decisions ─────────────────────
        print("\n⚠️  Creating RAID items...")

        # -- Risks --
        risk_data = [
            {"title": "Data migration kalite riski", "description": "Legacy ECC verilerinin S/4HANA'ya migrasyon sırasında veri kalitesi sorunları oluşabilir.",
             "probability": 4, "impact": 5, "risk_category": "technical", "risk_response": "mitigate",
             "mitigation_plan": "Veri profiling ve cleansing araçları kullanılacak. Migration cockpit dry-run'lar yapılacak.",
             "contingency_plan": "Manuel veri düzeltme ekibi hazır tutulacak.", "owner": "Ayşe Yılmaz",
             "priority": "critical", "status": "mitigating", "trigger_event": "Migration test hatası %5'i aşarsa"},
            {"title": "Change management direnci", "description": "Kullanıcıların yeni sisteme adaptasyon süreci uzayabilir.",
             "probability": 3, "impact": 4, "risk_category": "organisational", "risk_response": "mitigate",
             "mitigation_plan": "Change Agent ağı kurulacak, düzenli iletişim planı uygulanacak.",
             "owner": "Mehmet Kaya", "priority": "high", "status": "analysed"},
            {"title": "3rd-party entegrasyon gecikmeleri", "description": "Harici sistemlerle (EDI, banka, lojistik) entegrasyonlar planlanan sürede tamamlanamayabilir.",
             "probability": 3, "impact": 3, "risk_category": "external", "risk_response": "transfer",
             "owner": "Can Yıldırım", "priority": "medium", "status": "identified"},
            {"title": "Performans sorunları (yüksek hacim)", "description": "Ay sonu kapanışlarında yüksek işlem hacmi performans sorunlarına yol açabilir.",
             "probability": 2, "impact": 4, "risk_category": "technical", "risk_response": "mitigate",
             "mitigation_plan": "Early sizing & capacity planning, stress testleri planlı.",
             "owner": "Fatma Demir", "priority": "medium", "status": "identified"},
            {"title": "Lisans bütçe aşımı", "description": "S/4HANA Cloud lisans maliyetleri öngörülen bütçeyi aşabilir.",
             "probability": 2, "impact": 3, "risk_category": "commercial", "risk_response": "accept",
             "owner": "Ali Şen", "priority": "low", "status": "accepted"},
        ]
        for rd in risk_data:
            p = int(rd.get("probability", 3))
            i = int(rd.get("impact", 3))
            score = calculate_risk_score(p, i)
            rag = risk_rag_status(score)
            risk = Risk(
                program_id=pid, code=next_risk_code(),
                title=rd["title"], description=rd.get("description", ""),
                status=rd.get("status", "identified"), owner=rd.get("owner", ""),
                priority=rd.get("priority", "medium"),
                probability=p, impact=i, risk_score=score, rag_status=rag,
                risk_category=rd.get("risk_category", "technical"),
                risk_response=rd.get("risk_response", "mitigate"),
                mitigation_plan=rd.get("mitigation_plan", ""),
                contingency_plan=rd.get("contingency_plan", ""),
                trigger_event=rd.get("trigger_event", ""),
            )
            db.session.add(risk)
            db.session.flush()
            _p(f"   🔴 Risk {risk.code}: {risk.title[:50]} (score={score}, {rag})", verbose)
        print(f"   ✅ {len(risk_data)} risks")

        # -- Actions --
        action_data = [
            {"title": "Migration dry-run #1 planla", "action_type": "preventive",
             "owner": "Ayşe Yılmaz", "priority": "high", "status": "in_progress",
             "due_date": date(2025, 4, 15), "linked_entity_type": "risk"},
            {"title": "Change Agent eğitim programı hazırla", "action_type": "preventive",
             "owner": "Mehmet Kaya", "priority": "high", "status": "open",
             "due_date": date(2025, 3, 30)},
            {"title": "EDI partner teknik toplantısı düzenle", "action_type": "corrective",
             "owner": "Can Yıldırım", "priority": "medium", "status": "completed",
             "due_date": date(2025, 3, 10), "completed_date": date(2025, 3, 8)},
            {"title": "Stress test senaryoları yaz", "action_type": "detective",
             "owner": "Fatma Demir", "priority": "medium", "status": "open",
             "due_date": date(2025, 5, 1)},
            {"title": "Lisans True-Up raporunu incele", "action_type": "follow_up",
             "owner": "Ali Şen", "priority": "low", "status": "open",
             "due_date": date(2025, 6, 1)},
        ]
        for ad in action_data:
            action = Action(
                program_id=pid, code=next_action_code(),
                title=ad["title"], description=ad.get("description", ""),
                status=ad.get("status", "open"), owner=ad.get("owner", ""),
                priority=ad.get("priority", "medium"),
                action_type=ad.get("action_type", "corrective"),
                due_date=ad.get("due_date"), completed_date=ad.get("completed_date"),
                linked_entity_type=ad.get("linked_entity_type", ""),
            )
            db.session.add(action)
            db.session.flush()
            _p(f"   📋 Action {action.code}: {action.title[:50]} ({action.status})", verbose)
        print(f"   ✅ {len(action_data)} actions")

        # -- Issues --
        issue_data = [
            {"title": "LTMC batch job timeout hatası", "description": "Legacy data load sırasında LTMC batch job'ları 30dk sonra timeout veriyor.",
             "severity": "major", "status": "investigating", "owner": "Zeynep Arslan",
             "priority": "high", "root_cause": "Memory allocation parametreleri düşük.",
             "escalation_path": "Basis Team → SAP Support"},
            {"title": "Fiori Launchpad role mapping eksik", "description": "3 rol grubu için Fiori tile assignment yapılmamış.",
             "severity": "moderate", "status": "resolved", "owner": "Ahmet Koç",
             "priority": "medium", "resolution": "Roller /UI2/FLPD_CUST üzerinden düzeltildi.",
             "resolution_date": date(2025, 3, 5)},
            {"title": "Banka entegrasyon format uyumsuzluğu", "description": "Garanti BBVA XML format değişikliği ile mevcut mapping çalışmıyor.",
             "severity": "critical", "status": "escalated", "owner": "Can Yıldırım",
             "priority": "critical", "escalation_path": "Integration Lead → Steering Committee"},
        ]
        for id_ in issue_data:
            issue = Issue(
                program_id=pid, code=next_issue_code(),
                title=id_["title"], description=id_.get("description", ""),
                status=id_.get("status", "open"), owner=id_.get("owner", ""),
                priority=id_.get("priority", "medium"),
                severity=id_.get("severity", "moderate"),
                escalation_path=id_.get("escalation_path", ""),
                root_cause=id_.get("root_cause", ""),
                resolution=id_.get("resolution", ""),
                resolution_date=id_.get("resolution_date"),
            )
            db.session.add(issue)
            db.session.flush()
            _p(f"   🔥 Issue {issue.code}: {issue.title[:50]} ({issue.severity})", verbose)
        print(f"   ✅ {len(issue_data)} issues")

        # -- Decisions --
        decision_data = [
            {"title": "S/4HANA Cloud tercih edildi (vs On-Premise)", "status": "approved",
             "decision_owner": "CIO — Hakan Öztürk", "owner": "Hakan Öztürk",
             "priority": "critical", "decision_date": date(2025, 1, 15),
             "alternatives": "Option A: S/4HANA Cloud (seçildi)\nOption B: S/4HANA On-Premise\nOption C: Hybrid",
             "rationale": "TCO analizi, 5 yılda %30 maliyet avantajı. Yıllık upgrade garantisi.",
             "impact_description": "Tüm customizing cloud-compatible olmalı.", "reversible": False},
            {"title": "Greenfield yaklaşım onaylandı", "status": "approved",
             "decision_owner": "Program Sponsor", "owner": "Mehmet Kaya",
             "priority": "high", "decision_date": date(2025, 1, 20),
             "rationale": "Legacy complexity temizlenecek, SAP Best Practice kullanılacak.",
             "reversible": False},
            {"title": "Cutover stratejisi: Big Bang (phased değil)", "status": "pending_approval",
             "decision_owner": "Steering Committee", "owner": "Ali Şen",
             "priority": "high",
             "alternatives": "Option A: Big Bang (önerilen)\nOption B: Phased (modül bazlı)",
             "rationale": "Entegrasyon karmaşıklığı phased yaklaşımla artıyor."},
        ]
        for dd in decision_data:
            decision = Decision(
                program_id=pid, code=next_decision_code(),
                title=dd["title"], description=dd.get("description", ""),
                status=dd.get("status", "proposed"), owner=dd.get("owner", ""),
                priority=dd.get("priority", "medium"),
                decision_date=dd.get("decision_date"),
                decision_owner=dd.get("decision_owner", ""),
                alternatives=dd.get("alternatives", ""),
                rationale=dd.get("rationale", ""),
                impact_description=dd.get("impact_description", ""),
                reversible=dd.get("reversible", True),
            )
            db.session.add(decision)
            db.session.flush()
            _p(f"   📝 Decision {decision.code}: {decision.title[:50]} ({decision.status})", verbose)
        print(f"   ✅ {len(decision_data)} decisions")

        raid_total = len(risk_data) + len(action_data) + len(issue_data) + len(decision_data)
        print(f"\n   ⚠️  RAID Total: {raid_total} items")

        # ── Commit ───────────────────────────────────────────────────────
        db.session.commit()

        # ── Summary ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("🎉 DEMO DATA SEED COMPLETE")
        print("=" * 60)
        print(f"""
    Program ID:         {pid}
    Phases:             {len(PHASES)}
    Gates:              {sum(len(p.get('gates', [])) for p in PHASES)}
    Workstreams:        {len(WORKSTREAMS)}
    Team Members:       {len(TEAM_MEMBERS)}
    Committees:         {len(COMMITTEES)}
    Scenarios:          {len(SCENARIOS)}
    Requirements:       {len(REQUIREMENTS)}
    Traces:             {trace_count}
    Sprints:            {len(SPRINTS)}
    Backlog Items:      {len(BACKLOG_ITEMS)}
    Config Items:       {len(CONFIG_ITEMS)}
    Functional Specs:   {len(fs_data_list)}
    Technical Specs:    {len(ts_data_list)}
    Test Plans:         {len(test_plan_data)}
    Test Cycles:        {total_cycles}
    Test Cases:         {len(test_case_data)}
    Test Executions:    {exec_count}
    Defects:            {len(defect_data)}
    Risks:              {len(risk_data)}
    Actions:            {len(action_data)}
    Issues:             {len(issue_data)}
    Decisions:          {len(decision_data)}
    ─────────────────────────────
    TOTAL RECORDS:      {1 + len(PHASES) + sum(len(p.get('gates', [])) for p in PHASES) + len(WORKSTREAMS) + len(TEAM_MEMBERS) + len(COMMITTEES) + len(SCENARIOS) + sum(len(s.get('parameters', [])) for s in SCENARIOS) + len(REQUIREMENTS) + trace_count + len(SPRINTS) + len(BACKLOG_ITEMS) + len(CONFIG_ITEMS) + len(fs_data_list) + len(ts_data_list) + len(test_plan_data) + total_cycles + len(test_case_data) + exec_count + len(defect_data) + raid_total}
""")


def main():
    parser = argparse.ArgumentParser(
        description="Seed the SAP Transformation Platform with realistic demo data"
    )
    parser.add_argument("--append", action="store_true",
                        help="Append data without clearing existing records")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed output for each record")
    args = parser.parse_args()

    app = create_app()
    print(f"🎯 Target DB: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print()

    # Ensure tables exist
    with app.app_context():
        db.create_all()

    seed_all(app, append=args.append, verbose=args.verbose)


if __name__ == "__main__":
    main()
