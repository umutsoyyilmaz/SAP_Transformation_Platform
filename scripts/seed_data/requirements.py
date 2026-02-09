"""
Aşama 4 — Requirements, Traces, Process Mappings, Open Items
Şirket: Anadolu Gıda ve İçecek A.Ş.

25 Requirement (business, functional, technical, integration, non_functional)
14 Traces (requirement → phase / workstream / scenario)
8  Requirement–Process Mappings (requirement → L3 process)
6  Open Items (question, decision, dependency)
"""

REQUIREMENTS = [
    # ── Business Requirements ────────────────────────────────────────────
    {"code": "REQ-BIZ-001", "title": "TFRS/VUK paralel muhasebe raporlaması",
     "req_type": "business", "priority": "must_have", "status": "approved", "module": "FI",
     "description": "TFRS ve VUK'a uygun paralel mali tablo üretimi. Konsolide bilanço, gelir tablosu.",
     "source": "CFO"},
    {"code": "REQ-BIZ-002", "title": "8 tesiste gerçek zamanlı stok görünürlüğü",
     "req_type": "business", "priority": "must_have", "status": "approved", "module": "MM",
     "description": "Tüm depo ve tesislerde anlık stok seviyesi. Minimum stok ve raf ömrü uyarıları.",
     "source": "Lojistik Direktörü"},
    {"code": "REQ-BIZ-003", "title": "Sipariş-nakit sürecinin uçtan uca otomasyonu",
     "req_type": "business", "priority": "must_have", "status": "approved", "module": "SD",
     "description": "Müşteri siparişinden tahsilata kadar kesintisiz süreç. Ortalama O2C süresi < 5 gün.",
     "source": "Ticari Direktör"},
    {"code": "REQ-BIZ-004", "title": "Üretim planlama ve MRP optimizasyonu (gıda sektörü)",
     "req_type": "business", "priority": "must_have", "status": "in_progress", "module": "PP",
     "description": "Raf ömrü bazlı MRP, HACCP kontrol entegrasyonu. MRP çalıştırma < 1 saat.",
     "source": "Üretim Direktörü"},
    {"code": "REQ-BIZ-005", "title": "HACCP ve gıda güvenliği kalite yönetimi",
     "req_type": "business", "priority": "must_have", "status": "approved", "module": "QM",
     "description": "Kritik kontrol noktalarının SAP QM'de izlenmesi. Sertifika yönetimi.",
     "source": "Kalite Direktörü"},

    # ── Functional Requirements ──────────────────────────────────────────
    {"code": "REQ-FI-001", "title": "KDV vergi kodu yapılandırması (%1, %10, %20)",
     "req_type": "functional", "priority": "must_have", "status": "approved", "module": "FI",
     "description": "Türkiye KDV oranları, ÖTV, ÖİV tanımları. Gıda sektörü muafiyetleri."},
    {"code": "REQ-FI-002", "title": "Banka entegrasyonu (XML ISO 20022 + EFT)",
     "req_type": "functional", "priority": "should_have", "status": "approved", "module": "FI",
     "description": "8 bankayla otomatik ödeme, hesap özeti (MT940/camt.053 ), mutabakat."},
    {"code": "REQ-MM-001", "title": "Satınalma onay iş akışı (4 kademe)",
     "req_type": "functional", "priority": "must_have", "status": "approved", "module": "MM",
     "description": "Tutar bazlı 4 kademeli onay: <₺25K, <₺100K, <₺500K, ≥₺500K."},
    {"code": "REQ-MM-002", "title": "MRP → otomatik satınalma siparişi",
     "req_type": "functional", "priority": "should_have", "status": "in_progress", "module": "MM",
     "description": "MRP önerilerinden tedarikçi bazlı otomatik PO oluşturma."},
    {"code": "REQ-SD-001", "title": "Fiyatlandırma şeması (15+ koşul tipi)",
     "req_type": "functional", "priority": "must_have", "status": "approved", "module": "SD",
     "description": "Bayi, market, ihracat kanallarına göre farklı iskonto/prim şemaları."},
    {"code": "REQ-SD-002", "title": "Kredi limit yönetimi ve otomatik blokaj",
     "req_type": "functional", "priority": "should_have", "status": "draft", "module": "SD",
     "description": "Müşteri bazlı kredi limiti, vadesi geçmiş bakiye kontrolü, otomatik blokaj."},
    {"code": "REQ-PP-001", "title": "Reçete (BOM) ve rota yönetimi — gıda üretimi",
     "req_type": "functional", "priority": "must_have", "status": "in_progress", "module": "PP",
     "description": "Formülasyon bazlı BOM, co-product/by-product, lot izlenebilirlik."},

    # ── Technical Requirements ───────────────────────────────────────────
    {"code": "REQ-TEC-001", "title": "SAP BTP CPI — 18 arayüz geliştirme",
     "req_type": "technical", "priority": "must_have", "status": "approved", "module": "BTP",
     "description": "ERP ↔ MES, WMS, TMS, banka, e-Belge, EDI 18 arayüz. BTP CPI iFlow."},
    {"code": "REQ-TEC-002", "title": "Veri göçü — 10 ana nesne (~15M kayıt)",
     "req_type": "technical", "priority": "must_have", "status": "in_progress", "module": "Migration",
     "description": "Müşteri, tedarikçi, malzeme, BOM, açık kalem, stok bakiye, sabit kıymet göçü."},
    {"code": "REQ-TEC-003", "title": "Yetkilendirme matrisi (80 rol, SOD kontrol)",
     "req_type": "technical", "priority": "must_have", "status": "draft", "module": "Basis",
     "description": "80 SAP rolü, görev ayrımı (SOD) kontrolleri. Fiori app bazlı yetkilendirme."},

    # ── Integration Requirements ─────────────────────────────────────────
    {"code": "REQ-INT-001", "title": "e-Fatura / e-İrsaliye / e-Arşiv GİB entegrasyonu",
     "req_type": "integration", "priority": "must_have", "status": "approved", "module": "SD",
     "description": "GİB e-Belge entegrasyonu. UBL-TR 1.2 formatı. Giden ve gelen."},
    {"code": "REQ-INT-002", "title": "MES ↔ SAP PP üretim entegrasyonu",
     "req_type": "integration", "priority": "should_have", "status": "in_progress", "module": "PP",
     "description": "MES sisteminden üretim onayları, hurda/fire, OEE verileri. OData + CPI."},
    {"code": "REQ-INT-003", "title": "WMS ↔ EWM stok senkronizasyonu",
     "req_type": "integration", "priority": "should_have", "status": "draft", "module": "EWM",
     "description": "Harici WMS ile depo transferi, mal giriş/çıkış senkronizasyonu."},
    {"code": "REQ-INT-004", "title": "EDI — Perakende zincir sipariş entegrasyonu",
     "req_type": "integration", "priority": "should_have", "status": "draft", "module": "SD",
     "description": "Büyük market zincirleriyle EDIFACT sipariş/sevkiyat/fatura alışverişi."},

    # ── Non-Functional Requirements ──────────────────────────────────────
    {"code": "REQ-NFR-001", "title": "Sistem yanıt süresi < 2 saniye (P95)",
     "req_type": "non_functional", "priority": "must_have", "status": "approved", "module": "Basis",
     "description": "Online işlemler P95 < 2sn. Toplu işlemler performans hedefleri tanımlı."},
    {"code": "REQ-NFR-002", "title": "Sistem kullanılabilirliği >= %99.5 (uptime SLA)",
     "req_type": "non_functional", "priority": "must_have", "status": "approved", "module": "Basis",
     "description": "Yıllık planlı bakım hariç %99.5 sürekli çalışma garantisi."},
]

# ── Traces: Requirement → Phase / Workstream / Scenario ──────────────────
TRACES = [
    # Business → Explore phase
    {"req_code": "REQ-BIZ-001", "target_type": "phase", "target_name": "Explore", "trace_type": "derived_from"},
    {"req_code": "REQ-BIZ-002", "target_type": "phase", "target_name": "Explore", "trace_type": "derived_from"},
    {"req_code": "REQ-BIZ-003", "target_type": "phase", "target_name": "Explore", "trace_type": "derived_from"},
    {"req_code": "REQ-BIZ-004", "target_type": "phase", "target_name": "Realize", "trace_type": "implements"},
    # Functional → Workstreams
    {"req_code": "REQ-FI-001", "target_type": "workstream", "target_name": "Finance (FI/CO)", "trace_type": "implements"},
    {"req_code": "REQ-FI-002", "target_type": "workstream", "target_name": "Finance (FI/CO)", "trace_type": "implements"},
    {"req_code": "REQ-MM-001", "target_type": "workstream", "target_name": "Materials Management (MM)", "trace_type": "implements"},
    {"req_code": "REQ-SD-001", "target_type": "workstream", "target_name": "Sales & Distribution (SD)", "trace_type": "implements"},
    {"req_code": "REQ-PP-001", "target_type": "workstream", "target_name": "Production Planning (PP/QM)", "trace_type": "implements"},
    # Technical → Scenarios
    {"req_code": "REQ-TEC-001", "target_type": "scenario", "target_name": "Bilgi Teknolojileri ve Altyapı", "trace_type": "related_to"},
    {"req_code": "REQ-TEC-002", "target_type": "scenario", "target_name": "Bilgi Teknolojileri ve Altyapı", "trace_type": "related_to"},
    # Integration → BTP workstream
    {"req_code": "REQ-INT-001", "target_type": "workstream", "target_name": "Integration (BTP)", "trace_type": "implements"},
    {"req_code": "REQ-INT-002", "target_type": "workstream", "target_name": "Integration (BTP)", "trace_type": "implements"},
    {"req_code": "REQ-INT-003", "target_type": "workstream", "target_name": "Integration (BTP)", "trace_type": "implements"},
]

# ── Requirement ↔ L3 Process Code Mappings ───────────────────────────────
RPM_DATA = [
    {"req_code": "REQ-SD-001", "l3_code": "1OC", "coverage_type": "full", "notes": "Fiyatlandırma VA01 içinde"},
    {"req_code": "REQ-SD-001", "l3_code": "4OC", "coverage_type": "partial", "notes": "Fatura fiyatlandırma"},
    {"req_code": "REQ-FI-001", "l3_code": "1RR", "coverage_type": "full", "notes": "Vergi kodları GL kayıtta"},
    {"req_code": "REQ-FI-002", "l3_code": "1RR", "coverage_type": "partial", "notes": "Banka mutabakatı"},
    {"req_code": "REQ-MM-001", "l3_code": "1PP", "coverage_type": "full", "notes": "PO onay iş akışı"},
    {"req_code": "REQ-MM-002", "l3_code": "1PP", "coverage_type": "full", "notes": "MRP → otomatik PO"},
    {"req_code": "REQ-PP-001", "l3_code": "1PM", "coverage_type": "partial", "notes": "MRP BOM entegrasyonu"},
    {"req_code": "REQ-BIZ-005", "l3_code": "3PM", "coverage_type": "full", "notes": "QM HACCP süreci"},
]

# ── Open Items ───────────────────────────────────────────────────────────
OI_DATA = [
    {"req_code": "REQ-FI-002", "title": "Banka formatı henüz belirlenmedi",
     "item_type": "question", "owner": "Finans Ekibi", "priority": "high", "blocker": True, "status": "open",
     "description": "8 bankadan hangileri MT940, hangileri camt.053 kullanacak? Format teyidi bekleniyor."},
    {"req_code": "REQ-SD-002", "title": "Kredi limiti onay seviyesi kararı",
     "item_type": "decision", "owner": "Ticari Direktör", "priority": "high", "blocker": True, "status": "open",
     "description": "Kredi limiti aşıldığında hangi yönetici seviyesi onaylayacak?"},
    {"req_code": "REQ-TEC-002", "title": "Legacy veri temizlik kuralları",
     "item_type": "dependency", "owner": "Hakan Güneş", "priority": "critical", "blocker": True, "status": "open",
     "description": "ECC'den gelecek master data cleansing kuralları hâlâ bekleniyor."},
    {"req_code": "REQ-INT-001", "title": "GİB e-Fatura test ortamı sertifikası",
     "item_type": "dependency", "owner": "Murat Çelik", "priority": "high", "blocker": False, "status": "in_progress",
     "description": "GİB test portalı için dijital sertifika başvurusu yapıldı, onay bekleniyor."},
    {"req_code": "REQ-BIZ-004", "title": "MRP raf ömrü parametreleri",
     "item_type": "question", "owner": "Deniz Aydın", "priority": "medium", "blocker": False, "status": "in_progress",
     "description": "Gıda ürünleri için minimum kalan raf ömrü eşik değerleri ne olmalı?"},
    {"req_code": "REQ-BIZ-001", "title": "TFRS 16 kiralama muhasebesi kapsam kararı",
     "item_type": "decision", "owner": "CFO", "priority": "medium", "blocker": False, "status": "resolved",
     "resolution": "Phase 2'ye ertelendi. Mevcut kapsam dışında."},
]
