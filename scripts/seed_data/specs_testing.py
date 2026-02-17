"""
Aşama 6 — Functional Specs, Technical Specs, Test Plans/Cycles/Cases,
           Test Suites, Test Steps, Test Executions, Defects
Şirket: Anadolu Gıda ve İçecek A.Ş.

10 Functional Specs  (WRICEF & Config items için)
 8 Technical Specs   (FS'e 1:1 bağlı)
 2 Test Plans        (SIT, UAT)
 4 Test Cycles       (SIT-C1, SIT-C2, UAT-C1, Regression)
 3 Test Suites       (SIT-Finance, UAT-Logistics, Regression-Core)
18 Test Cases        (modül bazlı, suite'e atanmış)
36 Test Steps        (her TC için 2 detaylı adım)
18 Test Executions   (SIT-C1 cycle için)
 8 Defects           (P1→P4)
"""

# ═════════════════════════════════════════════════════════════════════════════
# FUNCTIONAL SPECS — backlog_code veya config_code ile bağlanır
# ═════════════════════════════════════════════════════════════════════════════

FS_DATA = [
    # ── WRICEF Functional Specs ──
    {"backlog_code": "WF-MM-001", "config_code": None,
     "title": "FS — Satınalma Siparişi Onay İş Akışı",
     "description": "4-kademeli tutar bazlı onay WF. SAP Business Workflow + BRF+ kural motoru.",
     "content": "## 1. Genel Bakış\n4-kademeli satınalma siparişi onay...\n## 2. İş Kuralları\n- <₺25K: Otomatik\n- <₺100K: Bölüm Müdürü\n- <₺500K: Direktör\n- ≥₺500K: CEO",
     "version": "2.0", "status": "approved", "author": "Elif Kara",
     "reviewer": "Deniz Aydın", "approved_by": "Kemal Erdoğan"},
    {"backlog_code": "INT-SD-001", "config_code": None,
     "title": "FS — e-Fatura / e-İrsaliye GİB Arayüzü",
     "description": "UBL-TR 1.2 formatında GİB e-Belge arayüzü. BTP CPI iFlow tasarımı.",
     "content": "## 1. Arayüz Özeti\nGİB e-Fatura/e-İrsaliye giden/gelen...\n## 2. Mesaj Yapısı\nUBL-TR Invoice 2.1\n## 3. Hata Yönetimi\nGİB timeout → retry 3x",
     "version": "1.1", "status": "approved", "author": "Zeynep Koç",
     "reviewer": "Burak Şahin", "approved_by": "Kemal Erdoğan"},
    {"backlog_code": "ENH-FI-001", "config_code": None,
     "title": "FS — Otomatik Vergi Hesaplama BAdI",
     "description": "KDV + ÖTV + ÖİV hesaplama. Gıda ürünlerinde KDV %1/%10 ayrımı.",
     "content": "## 1. Vergi Kuralları\n- Temel gıda: KDV %1\n- İşlenmiş gıda: KDV %10\n- İçecek: KDV %20 + ÖİV\n## 2. BAdI: TAX_CALC_ENHANCE",
     "version": "1.0", "status": "approved", "author": "Ahmet Yıldız",
     "reviewer": "Elif Kara", "approved_by": "Kemal Erdoğan"},
    {"backlog_code": "RPT-FI-001", "config_code": None,
     "title": "FS — Konsolide Bilanço Raporu (TFRS/VUK)",
     "description": "Çoklu şirket kodu konsolidasyon. TFRS ve VUK paralel raporlama.",
     "content": "## 1. Raporlama Gereksinimleri\n3 şirket kodu konsolidasyon\n## 2. Parametre\nŞirket kodu, dönem, raporlama standardı",
     "version": "1.0", "status": "in_review", "author": "Ahmet Yıldız",
     "reviewer": "Kemal Erdoğan"},
    {"backlog_code": "CNV-MD-001", "config_code": None,
     "title": "FS — Müşteri Ana Veri Göçü",
     "description": "ECC KNA1/KNVV → S/4 Business Partner. 15.000 aktif müşteri.",
     "content": "## 1. Kaynak Sistem\nECC — KNA1, KNVV, KNB1, KNVK\n## 2. Hedef\nS/4 BP — BUT000, BUT020, BUT050\n## 3. Dönüşüm Kuralları\n- KUNNR → BP_NUMBER\n- Müşteri grubu → BP Role",
     "version": "1.0", "status": "approved", "author": "Hakan Güneş",
     "reviewer": "Burak Şahin", "approved_by": "Kemal Erdoğan"},
    {"backlog_code": "INT-PP-001", "config_code": None,
     "title": "FS — MES → SAP PP Üretim Onay Arayüzü",
     "description": "MES'ten üretim onayı ve hurda bildirimi. OData API + BTP CPI.",
     "content": "## 1. Arayüz Tipi\nMES → SAP (inbound)\n## 2. Protokol\nOData V4 API\n## 3. Veri\nÜretim emri no, operasyon, miktar, hurda, lot",
     "version": "1.0", "status": "draft", "author": "Zeynep Koç",
     "reviewer": "Deniz Aydın"},
    {"backlog_code": "ENH-MM-001", "config_code": None,
     "title": "FS — Raf Ömrü Kontrolü FIFO/FEFO",
     "description": "Gıda ürünlerinde otomatik FIFO/FEFO lot seçim kuralları.",
     "content": "## 1. Kural\nRaf ömrü < %25 kalan → bloke\n## 2. Lot Seçim\nFEFO: En yakın SKT önce\n## 3. Uyarı\nSKT < 30 gün → otomatik uyarı",
     "version": "1.0", "status": "in_review", "author": "Elif Kara",
     "reviewer": "Gökhan Demir"},

    # ── Config Functional Specs ──
    {"backlog_code": None, "config_code": "CFG-FI-003",
     "title": "FS — KDV Vergi Kodları Konfigürasyon",
     "description": "KDV %1, %10, %20, muaf vergi kodları IMG konfigürasyon dokümanı.",
     "content": "## 1. Vergi Kodları\n- V1: KDV %1 (temel gıda)\n- V2: KDV %10 (işlenmiş gıda)\n- V3: KDV %20\n- V0: KDV muaf",
     "version": "1.0", "status": "approved", "author": "Ahmet Yıldız",
     "reviewer": "Elif Kara", "approved_by": "Kemal Erdoğan"},
    {"backlog_code": None, "config_code": "CFG-SD-002",
     "title": "FS — Fiyatlandırma Prosedürü ZPRC01",
     "description": "Gıda sektörü fiyatlandırma prosedürü. Kanal bazlı koşul tipleri.",
     "content": "## 1. Prosedür\nZPRC01 — Anadolu Gıda Fiyatlandırma\n## 2. Koşul Tipleri\nZPR0: Taban fiyat\nZK01: Kanal iskontosu\nZM01: Miktar iskontosu\nMWST: KDV",
     "version": "1.0", "status": "draft", "author": "Burak Şahin",
     "reviewer": "Deniz Aydın"},
    {"backlog_code": None, "config_code": "CFG-BASIS-001",
     "title": "FS — Yetkilendirme Rol Tanımlama (Fiori + SOD)",
     "description": "Fiori Launchpad rolleri, SOD kontrol, katalog/grup yapısı.",
     "content": "## 1. Rol Yapısı\nSingle: Z_FI_*, Z_MM_*, Z_SD_*\nComposite: Z_COMP_*\n## 2. Fiori\nCatalog → Group → Space/Page\n## 3. SOD\nGRC risk analizi kuralları",
     "version": "1.0", "status": "draft", "author": "Murat Çelik",
     "reviewer": "Zeynep Koç"},
]

# ═════════════════════════════════════════════════════════════════════════════
# TECHNICAL SPECS — fs_key = backlog_code veya config_code (FS ile eşleşir)
# ═════════════════════════════════════════════════════════════════════════════

TS_DATA = [
    {"fs_key": "WF-MM-001",
     "title": "TS — Satınalma Onay WF Teknik Tasarım",
     "description": "Workflow template WS9900, BRF+ application ZMM_APPROVAL_RULES.",
     "content": "## Objeler\n- WF Template: WS99000001\n- BRF+ App: ZMM_APPROVAL_RULES\n- Task: TS99000001 (onay karar)\n## Unit Test\nSWEL izleme aktif, 4 seviye test senaryosu",
     "version": "1.0", "status": "approved", "author": "Elif Kara",
     "objects_list": "WS99000001, TS99000001, ZMM_APPROVAL_RULES, ZCL_MM_WF_HANDLER",
     "unit_test_evidence": "SWEL log — 12 test case pass"},
    {"fs_key": "INT-SD-001",
     "title": "TS — e-Fatura GİB Arayüzü Teknik Tasarım",
     "description": "BTP CPI iFlow, IDoc → UBL-TR dönüşüm, GİB API entegrasyonu.",
     "content": "## Objeler\n- iFlow: IF_EINVOICE_OUT, IF_EINVOICE_IN\n- Mapping: MM_IDOC2UBL, MM_UBL2IDOC\n## Güvenlik\nmTLS sertifika, GİB test ortamı",
     "version": "1.0", "status": "approved", "author": "Zeynep Koç",
     "objects_list": "IF_EINVOICE_OUT, IF_EINVOICE_IN, MM_IDOC2UBL, ZSD_EINVOICE_PROXY",
     "unit_test_evidence": "CPI monitoring — 50 test mesaj pass"},
    {"fs_key": "ENH-FI-001",
     "title": "TS — Vergi Hesaplama BAdI Teknik Tasarım",
     "description": "Enhancement implementation: ZCL_TAX_CALC, BAdI TAX_CALC_ENHANCE.",
     "content": "## Objeler\n- BAdI Impl: ZCL_TAX_CALC\n- Tax Procedure: ZTAXTR\n## Tablo\n- ZTAX_FOOD_MAP: Malzeme grubu → KDV oranı",
     "version": "1.0", "status": "approved", "author": "Ahmet Yıldız",
     "objects_list": "ZCL_TAX_CALC, ZTAXTR, ZTAX_FOOD_MAP, ZFM_TAX_DETERMINE",
     "unit_test_evidence": "ABAP Unit — 8 method, 24 assert pass"},
    {"fs_key": "RPT-FI-001",
     "title": "TS — Konsolide Bilanço Raporu Teknik Tasarım",
     "description": "CDS View + Fiori Elements analytical list page.",
     "content": "## Objeler\n- CDS: ZI_BALANCE_SHEET, ZC_BALANCE_CONS\n- OData: ZSB_BALANCESHEET\n- Fiori App: zfi_balance_cons",
     "version": "1.0", "status": "in_review", "author": "Ahmet Yıldız",
     "objects_list": "ZI_BALANCE_SHEET, ZC_BALANCE_CONS, ZSB_BALANCESHEET"},
    {"fs_key": "CNV-MD-001",
     "title": "TS — Müşteri Ana Veri Göçü Teknik Tasarım",
     "description": "LTMC template, migration cockpit, mapping programı.",
     "content": "## Objeler\n- LTMC Project: ZMIG_CUSTOMER\n- Template: S4_BP_CUSTOMER\n- Mapping: ZCL_MIG_CUST_MAP",
     "version": "1.0", "status": "approved", "author": "Hakan Güneş",
     "objects_list": "ZMIG_CUSTOMER, ZCL_MIG_CUST_MAP, ZTMP_CUSTOMER_STG",
     "unit_test_evidence": "100 kayıt dry-run — 98 başarılı, 2 hata düzeltildi"},
    {"fs_key": "INT-PP-001",
     "title": "TS — MES Üretim Onay Arayüzü Teknik Tasarım",
     "description": "Custom OData API + CPI iFlow. MES XML → SAP JSON dönüşüm.",
     "content": "## Objeler\n- OData: ZAPI_PRODCONFIRM\n- CPI iFlow: IF_MES_PRODCONF\n- BAPI: BAPI_PRODORDCONF_CREATE_TT",
     "version": "1.0", "status": "draft", "author": "Zeynep Koç",
     "objects_list": "ZAPI_PRODCONFIRM, IF_MES_PRODCONF"},
    {"fs_key": "CFG-FI-003",
     "title": "TS — KDV Vergi Kodları Teknik Konfigürasyon",
     "description": "Tax procedure ZTAXTR condition records detayları.",
     "content": "## Konfigürasyon Adımları\n- FTXP: V1, V2, V3, V0 kodları\n- Tax Procedure: ZTAXTR\n- Condition: MWST → V1/V2/V3/V0",
     "version": "1.0", "status": "approved", "author": "Ahmet Yıldız",
     "objects_list": "ZTAXTR, V1, V2, V3, V0"},
    {"fs_key": "ENH-MM-001",
     "title": "TS — Raf Ömrü FIFO/FEFO Teknik Tasarım",
     "description": "EWM lot selection strategy + shelf life BAdI.",
     "content": "## Objeler\n- BAdI: ZCL_SHELF_LIFE_CHECK\n- EWM Strategy: ZFEFO\n- Alert: ZSHELF_LIFE_WARN",
     "version": "1.0", "status": "draft", "author": "Elif Kara",
     "objects_list": "ZCL_SHELF_LIFE_CHECK, ZFEFO"},
]

# ═════════════════════════════════════════════════════════════════════════════
# TEST PLANS + CYCLES
# ═════════════════════════════════════════════════════════════════════════════

TEST_PLAN_DATA = [
    {
        "name": "SIT Master Plan — Entegre Sistem Testi",
        "description": "System Integration Test. Tüm E2E süreçleri kapsayan entegre test planı.",
        "status": "active",
        "test_strategy": "Modül bazlı SIT → cross-module entegrasyon. Defect P1/P2 sıfır hedef.",
        "entry_criteria": "Birim testler pass, konfigürasyon tamamlanmış, test verisi hazır",
        "exit_criteria": "P1/P2=0, geçiş oranı ≥ %95, tüm E2E senaryolar test edilmiş",
        "start_date": "2026-03-01", "end_date": "2026-05-31",
        "cycles": [
            {"name": "SIT Cycle 1 — Temel Akışlar", "test_layer": "sit",
             "status": "completed", "start_date": "2026-03-01", "end_date": "2026-03-21"},
            {"name": "SIT Cycle 2 — Hata Düzeltme & Regresyon", "test_layer": "sit",
             "status": "in_progress", "start_date": "2026-03-24", "end_date": "2026-04-11"},
        ],
    },
    {
        "name": "UAT Plan — Kullanıcı Kabul Testi",
        "description": "Son kullanıcılar tarafından iş senaryosu bazlı kabul testi.",
        "status": "draft",
        "test_strategy": "İş senaryosu bazlı test. Anahtar kullanıcılar yönetir.",
        "entry_criteria": "SIT tamamlanmış, P1/P2=0, eğitim verilmiş",
        "exit_criteria": "Tüm iş senaryoları onaylı, UAT sign-off imzalı",
        "start_date": "2026-07-01", "end_date": "2026-08-31",
        "cycles": [
            {"name": "UAT Cycle 1 — İş Senaryoları", "test_layer": "uat",
             "status": "planning", "start_date": "2026-07-01", "end_date": "2026-07-31"},
            {"name": "Regression Cycle — Go-Live Öncesi", "test_layer": "regression",
             "status": "planning", "start_date": "2026-10-01", "end_date": "2026-10-15"},
        ],
    },
]

# ═════════════════════════════════════════════════════════════════════════════
# TEST CASES — req_code ile requirement'a bağlanır
# ═════════════════════════════════════════════════════════════════════════════

TEST_CASE_DATA = [
    # ── FI ──
    {"code": "TC-FI-001", "title": "Satınalma faturası kayıt ve 3-way matching",
     "module": "FI", "test_layer": "sit", "status": "approved", "priority": "critical",
     "req_code": "REQ-FI-001",
     "preconditions": "Tedarikçi, malzeme, PO, GR mevcut",
     "test_steps": "1. MIRO ile fatura gir\n2. PO ve GR ile eşleştir\n3. Tutar farkı kontrolü\n4. Hesaplara yansıma kontrolü",
     "expected_result": "Fatura 3-way match ile onaylanır, muhasebe kayıtları doğru",
     "is_regression": True},
    {"code": "TC-FI-002", "title": "KDV hesaplama — gıda ürünleri %1 / %10 / %20",
     "module": "FI", "test_layer": "sit", "status": "approved", "priority": "critical",
     "req_code": "REQ-FI-001",
     "preconditions": "Vergi kodları V1/V2/V3 konfigüre edilmiş",
     "test_steps": "1. Temel gıda ile satış faturası (%1)\n2. İşlenmiş gıda (%10)\n3. İçecek (%20 + ÖİV)\n4. Muaf ürün",
     "expected_result": "Her ürün tipinde doğru KDV oranı hesaplanır",
     "is_regression": True},
    {"code": "TC-FI-003", "title": "Konsolide bilanço raporu — 3 şirket kodu",
     "module": "FI", "test_layer": "sit", "status": "approved", "priority": "high",
     "req_code": "REQ-BIZ-001",
     "preconditions": "3 şirket kodunda FI kayıtları mevcut",
     "test_steps": "1. Raporu çalıştır (TFRS)\n2. Konsolidasyon kontrolü\n3. VUK versiyonu\n4. Döviz çevrimi doğrulama",
     "expected_result": "Konsolide bakiye doğru, TFRS/VUK paralel"},

    # ── MM ──
    {"code": "TC-MM-001", "title": "Satınalma siparişi oluşturma ve 4 kademe onay",
     "module": "MM", "test_layer": "sit", "status": "approved", "priority": "critical",
     "req_code": "REQ-MM-001",
     "preconditions": "Tedarikçi, malzeme, info record mevcut, WF aktif",
     "test_steps": "1. ME21N ile PO oluştur (<₺25K)\n2. Otomatik onay doğrula\n3. ₺200K PO oluştur → direktör onay\n4. ₺600K PO → CEO onay",
     "expected_result": "Her tutar kademesinde doğru onaylayıcıya yönlendirilir",
     "is_regression": True},
    {"code": "TC-MM-002", "title": "Raf ömrü kontrolü — FEFO lot seçim",
     "module": "MM", "test_layer": "sit", "status": "approved", "priority": "high",
     "req_code": "REQ-MM-002",
     "preconditions": "Farklı SKT'li lotlar stokta mevcut",
     "test_steps": "1. Sevkiyat için malzeme seç\n2. FEFO kuralı ile lot öner\n3. SKT < 30 gün → bloke kontrolü\n4. FIFO alternatif",
     "expected_result": "En yakın SKT'li lot önce önerilir, kısa SKT bloke"},
    {"code": "TC-MM-003", "title": "Malzeme ana veri göçü doğrulama (60K kayıt)",
     "module": "MM", "test_layer": "sit", "status": "ready", "priority": "critical",
     "req_code": "REQ-TEC-002",
     "preconditions": "Göç programı çalıştırılmış, staging tablo dolu",
     "test_steps": "1. Kayıt sayısı doğrula\n2. Malzeme tipi mapping kontrolü\n3. BOM doğrulama\n4. Reçete doğrulama",
     "expected_result": "60K kayıt başarılı göç, hata oranı < %0.5"},

    # ── SD ──
    {"code": "TC-SD-001", "title": "Order-to-Cash E2E — sipariş → sevkiyat → fatura",
     "module": "SD", "test_layer": "uat", "status": "approved", "priority": "critical",
     "req_code": "REQ-SD-001",
     "preconditions": "Müşteri, malzeme, fiyat koşulları mevcut",
     "test_steps": "1. VA01 satış siparişi\n2. VL01N sevkiyat\n3. PGI mal çıkışı\n4. VF01 fatura\n5. Muhasebe kaydı kontrol",
     "expected_result": "Sipariş→sevkiyat→fatura→muhasebe akışı sorunsuz",
     "is_regression": True},
    {"code": "TC-SD-002", "title": "e-Fatura GİB gönderim ve yanıt kontrolü",
     "module": "SD", "test_layer": "uat", "status": "approved", "priority": "critical",
     "req_code": "REQ-INT-001",
     "preconditions": "GİB test ortamı bağlantısı aktif, sertifika geçerli",
     "test_steps": "1. VF01 fatura oluştur\n2. e-Fatura tetikle\n3. UBL-TR XML kontrolü\n4. GİB yanıt (kabul/red)\n5. İrsaliye gönderim",
     "expected_result": "GİB'e başarılı gönderim, kabul yanıtı alınır",
     "is_regression": True},
    {"code": "TC-SD-003", "title": "Kanal bazlı fiyatlandırma koşulları",
     "module": "SD", "test_layer": "uat", "status": "in_review", "priority": "high",
     "req_code": "REQ-SD-001",
     "preconditions": "ZPRC01 prosedürü, kanal koşul tipleri konfigüre",
     "test_steps": "1. Perakende kanalı sipariş (ZK01)\n2. Toptan kanal sipariş\n3. E-ticaret kanalı\n4. İskonto hesaplama",
     "expected_result": "Her kanalda doğru fiyat ve iskonto uygulanır"},

    # ── PP/QM ──
    {"code": "TC-PP-001", "title": "Plan-to-Produce E2E — MRP → üretim emri → onay",
     "module": "PP", "test_layer": "uat", "status": "in_review", "priority": "critical",
     "req_code": "REQ-PP-001",
     "preconditions": "BOM, reçete, iş merkezi, MRP parametreleri hazır",
     "test_steps": "1. MD01 MRP çalıştır\n2. Planlı sipariş → üretim emri\n3. Emri serbest bırak\n4. Onay gir\n5. Maliyet hesaplama",
     "expected_result": "MRP doğru planlı sipariş oluşturur, üretim emri tamamlanır"},
    {"code": "TC-PP-002", "title": "MES → SAP üretim onay arayüz testi",
     "module": "PP", "test_layer": "e2e", "status": "ready", "priority": "high",
     "req_code": "REQ-INT-002",
     "preconditions": "MES bağlantısı aktif, test üretim emri serbest",
     "test_steps": "1. MES'ten onay mesajı gönder\n2. SAP'de BAPI ile onay oluştur\n3. Hurda miktarı doğrula\n4. Hata mesaj kontrolü",
     "expected_result": "MES onayı SAP'ye başarılı aktarılır"},
    {"code": "TC-QM-001", "title": "HACCP kontrol noktası muayene tetikleme",
     "module": "QM", "test_layer": "e2e", "status": "draft", "priority": "high",
     "req_code": "REQ-NFR-001",
     "preconditions": "Muayene planı, HACCP kontrol noktaları tanımlı",
     "test_steps": "1. Mal girişi yap (gıda hammaddesi)\n2. Otomatik muayene lotu kontrolü\n3. HACCP sonuç gir\n4. Kabul/red kararı",
     "expected_result": "Gıda hammaddesi girişinde otomatik muayene tetiklenir"},

    # ── EWM ──
    {"code": "TC-EWM-001", "title": "Depo sevkiyat süreci — wave picking",
     "module": "EWM", "test_layer": "e2e", "status": "draft", "priority": "high",
     "req_code": "REQ-BIZ-003",
     "preconditions": "Depo yapısı, raf tipleri, stratejiler tanımlı",
     "test_steps": "1. Outbound delivery oluştur\n2. Wave ata\n3. Picking task başlat\n4. Teyit ve PGI",
     "expected_result": "Wave picking doğru çalışır, stok hareketi SAP'ye yansır"},

    # ── Integration ──
    {"code": "TC-INT-001", "title": "Banka hesap özeti (MT940) alım testi",
     "module": "FI", "test_layer": "e2e", "status": "in_review", "priority": "medium",
     "req_code": "REQ-INT-003",
     "preconditions": "Banka bağlantısı konfigüre, elektronik hesap özeti aktif",
     "test_steps": "1. MT940 dosyası yükle\n2. Otomatik eşleştirme çalıştır\n3. Eşleşmeyen kalemleri kontrol\n4. Hesap bakiyesi doğrulama",
     "expected_result": "MT940 başarılı parse, otomatik eşleştirme ≥ %90"},

    # ── Cross-Module (E2E) ──
    {"code": "TC-E2E-001", "title": "Procure-to-Pay tam akış entegrasyon testi",
     "module": "MM", "test_layer": "regression", "status": "approved", "priority": "critical",
     "req_code": "REQ-MM-001",
     "preconditions": "Tüm MM/FI konfigürasyon tamamlanmış",
     "test_steps": "1. Satınalma talebi\n2. PO oluştur + onay WF\n3. Mal girişi\n4. Fatura girişi (MIRO)\n5. Ödeme (F110)\n6. Muhasebe kontrol",
     "expected_result": "PR→PO→GR→IR→Payment akışı sorunsuz",
     "is_regression": True},
    {"code": "TC-E2E-002", "title": "Record-to-Report ay sonu kapanış testi",
     "module": "FI", "test_layer": "regression", "status": "ready", "priority": "high",
     "req_code": "REQ-FI-002",
     "preconditions": "Ay içi FI kayıtları mevcut",
     "test_steps": "1. Tahakkuk kayıtları\n2. Amortisman çalıştır\n3. FX revaluation\n4. Dönem kapanış\n5. Raporlama kontrolü",
     "expected_result": "Ay sonu kapanış prosedürü < 4 saat, raporlar doğru"},
]

# ═════════════════════════════════════════════════════════════════════════════
# TEST EXECUTIONS — SIT Cycle 1 sonuçları
# ═════════════════════════════════════════════════════════════════════════════

EXECUTION_DATA = [
    {"tc_code": "TC-FI-001", "result": "pass", "executed_by": "Ahmet Yıldız",
     "duration_minutes": 25, "notes": "3-way match sorunsuz çalıştı"},
    {"tc_code": "TC-FI-002", "result": "pass", "executed_by": "Ahmet Yıldız",
     "duration_minutes": 30, "notes": "KDV %1/%10/%20 hepsi doğru hesaplandı"},
    {"tc_code": "TC-FI-003", "result": "fail", "executed_by": "Ahmet Yıldız",
     "duration_minutes": 45, "notes": "2. şirket kodu döviz çevrimi hatalı → DEF-FI-001"},
    {"tc_code": "TC-MM-001", "result": "pass", "executed_by": "Elif Kara",
     "duration_minutes": 35, "notes": "4 kademe onay tamamlandı"},
    {"tc_code": "TC-MM-002", "result": "pass", "executed_by": "Elif Kara",
     "duration_minutes": 20, "notes": "FEFO lot seçim doğru çalışıyor"},
    {"tc_code": "TC-MM-003", "result": "blocked", "executed_by": "Hakan Güneş",
     "duration_minutes": 10, "notes": "Göç verisi henüz yüklenmedi → bloke"},
    {"tc_code": "TC-SD-001", "result": "pass", "executed_by": "Burak Şahin",
     "duration_minutes": 40, "notes": "OTC E2E sorunsuz tamamlandı"},
    {"tc_code": "TC-SD-002", "result": "fail", "executed_by": "Zeynep Koç",
     "duration_minutes": 60, "notes": "GİB yanıt timeout → DEF-SD-001"},
    {"tc_code": "TC-SD-003", "result": "pass", "executed_by": "Burak Şahin",
     "duration_minutes": 25, "notes": "Kanal fiyatlandırma doğru"},
    {"tc_code": "TC-PP-001", "result": "pass", "executed_by": "Deniz Aydın",
     "duration_minutes": 50, "notes": "MRP → üretim emri → onay akışı tamam"},
    {"tc_code": "TC-PP-002", "result": "fail", "executed_by": "Zeynep Koç",
     "duration_minutes": 30, "notes": "MES hurda miktarı negatif geldi → DEF-PP-001"},
    {"tc_code": "TC-QM-001", "result": "pass", "executed_by": "Deniz Aydın",
     "duration_minutes": 20, "notes": "HACCP muayene otomatik tetiklendi"},
    {"tc_code": "TC-EWM-001", "result": "pass", "executed_by": "Gökhan Demir",
     "duration_minutes": 35, "notes": "Wave picking sorunsuz"},
    {"tc_code": "TC-INT-001", "result": "deferred", "executed_by": "Zeynep Koç",
     "duration_minutes": 5, "notes": "Banka test ortamı henüz hazır değil"},
    {"tc_code": "TC-E2E-001", "result": "pass", "executed_by": "Elif Kara",
     "duration_minutes": 55, "notes": "P2P tam akış başarılı"},
    {"tc_code": "TC-E2E-002", "result": "fail", "executed_by": "Ahmet Yıldız",
     "duration_minutes": 40, "notes": "Amortisman hesaplama sapma → DEF-FI-002"},
    {"tc_code": "TC-FI-001", "result": "pass", "executed_by": "Ayşe Polat",
     "duration_minutes": 20, "notes": "Regresyon — onaylı"},
    {"tc_code": "TC-SD-001", "result": "pass", "executed_by": "Ayşe Polat",
     "duration_minutes": 35, "notes": "Regresyon — OTC tekrar test"},
]

# ═════════════════════════════════════════════════════════════════════════════
# DEFECTS — tc_code ile test case'e bağlanır
# ═════════════════════════════════════════════════════════════════════════════

DEFECT_DATA = [
    {"code": "DEF-FI-001", "title": "Konsolide bilanço — 2. şirket kodu döviz çevrimi hatası",
     "tc_code": "TC-FI-003", "module": "FI", "severity": "S2", "status": "resolved",
     "environment": "QAS",
     "description": "Şirket kodu 2000 (USD bazlı) döviz çevrimi yanlış kur kullanıyor.",
     "steps_to_reproduce": "1. ZFI_BALANCE çalıştır\n2. Şirket kodu 2000 seç\n3. Konsolide et → EUR satırı yanlış",
     "reported_by": "Ahmet Yıldız", "assigned_to": "Ahmet Yıldız",
     "found_in_cycle": "SIT Cycle 1",
     "resolution": "CDS view ZI_BALANCE_SHEET kur dönüşüm mantığı düzeltildi",
     "root_cause": "Kur tablosu TCURR yerine sabit kur kullanılmış",
     "reopen_count": 0},
    {"code": "DEF-SD-001", "title": "e-Fatura GİB yanıtı timeout — 60sn aşımı",
     "tc_code": "TC-SD-002", "module": "SD", "severity": "S1", "status": "in_progress",
     "environment": "QAS",
     "description": "GİB test ortamına e-fatura gönderiminde 60 saniye timeout.",
     "steps_to_reproduce": "1. VF01 ile fatura oluştur\n2. e-Fatura tetikle\n3. 60 saniye bekle → timeout hatası",
     "reported_by": "Zeynep Koç", "assigned_to": "Zeynep Koç",
     "found_in_cycle": "SIT Cycle 1"},
    {"code": "DEF-PP-001", "title": "MES hurda miktarı negatif değer gönderiyor",
     "tc_code": "TC-PP-002", "module": "PP", "severity": "S2", "status": "new",
     "environment": "QAS",
     "description": "MES sisteminden gelen hurda miktarı alanı negatif değer içeriyor.",
     "steps_to_reproduce": "1. MES'ten üretim onay gönder\n2. Hurda = -5 geldi\n3. BAPI hata verdi",
     "reported_by": "Zeynep Koç", "assigned_to": "Deniz Aydın",
     "found_in_cycle": "SIT Cycle 1"},
    {"code": "DEF-FI-002", "title": "Amortisman hesaplama sapma — yuvarlama hatası",
     "tc_code": "TC-E2E-002", "module": "FI", "severity": "S3", "status": "resolved",
     "environment": "QAS",
     "description": "Sabit kıymet amortismanında 0.01 TL yuvarlama farkı oluşuyor.",
     "steps_to_reproduce": "1. AFAB çalıştır\n2. Kıymet 10001 kontrol → 0.01 fark",
     "reported_by": "Ahmet Yıldız", "assigned_to": "Ahmet Yıldız",
     "found_in_cycle": "SIT Cycle 1",
     "resolution": "Yuvarlama kuralı ROUND_HALF_UP olarak güncellendi",
     "root_cause": "Python-style banker's rounding kullanılıyordu",
     "reopen_count": 0},
    {"code": "DEF-MM-001", "title": "FEFO lot seçim — aynı SKT'li lotlarda önceliklendirme yok",
     "tc_code": "TC-MM-002", "module": "MM", "severity": "S4", "status": "new",
     "environment": "QAS",
     "description": "Aynı son kullanma tarihli 2 lot olduğunda rastgele seçim yapılıyor, FIFO ikincil kural uygulanmıyor.",
     "reported_by": "Elif Kara", "assigned_to": "Gökhan Demir",
     "found_in_cycle": "SIT Cycle 1"},
    {"code": "DEF-SD-002", "title": "Sevk irsaliyesi formunda barkod basılmıyor",
     "tc_code": "TC-SD-001", "module": "SD", "severity": "S3", "status": "retest",
     "environment": "QAS",
     "description": "Adobe Form sevk irsaliyesinde EAN-13 barkod alanı boş geliyor.",
     "steps_to_reproduce": "1. VL01N sevkiyat oluştur\n2. İrsaliye yazdır\n3. Barkod alanı boş",
     "reported_by": "Burak Şahin", "assigned_to": "Burak Şahin",
     "found_in_cycle": "SIT Cycle 1",
     "resolution": "Adobe Form'da barkod font mapping eklendi",
     "root_cause": "BC417 barkod fontu sunucuya yüklenmemişti"},
    {"code": "DEF-EWM-001", "title": "Wave picking — büyük sipariş split hatası",
     "tc_code": "TC-EWM-001", "module": "EWM", "severity": "S3", "status": "new",
     "environment": "QAS",
     "description": "500+ kalemli siparişte wave split düzgün çalışmıyor.",
     "reported_by": "Gökhan Demir", "assigned_to": "Gökhan Demir",
     "found_in_cycle": "SIT Cycle 1"},
    {"code": "DEF-INT-001", "title": "CPI iFlow — retry mekanizması çalışmıyor",
     "tc_code": "TC-SD-002", "module": "BC", "severity": "S2", "status": "in_progress",
     "environment": "QAS",
     "description": "BTP CPI iFlow'da GİB timeout sonrası retry mekanizması tetiklenmiyor.",
     "steps_to_reproduce": "1. e-Fatura gönder\n2. GİB timeout\n3. Retry 0/3 — retry tetiklenmedi",
     "reported_by": "Zeynep Koç", "assigned_to": "Zeynep Koç",
     "found_in_cycle": "SIT Cycle 1"},
]

# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITES — Test Case grupları  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

SUITE_DATA = [
    {"name": "SIT-Finance — Finans Entegrasyon Paketi",
     "description": "FI modülü SIT test case'lerini içeren ana suite. 3-way match, KDV, konsolidasyon.",
     "suite_type": "SIT", "status": "active", "module": "FI",
     "owner": "Ahmet Yıldız",
     "tags": "finance,sit,fi",
     "tc_codes": ["TC-FI-001", "TC-FI-002", "TC-FI-003", "TC-INT-001"]},
    {"name": "UAT-Logistics — Lojistik Kabul Paketi",
     "description": "MM/SD/PP/EWM UAT test case'leri. Tedarik zinciri uçtan uca doğrulama.",
     "suite_type": "UAT", "status": "draft", "module": "MM",
     "owner": "Elif Kara",
     "tags": "logistics,uat,mm,sd,pp",
     "tc_codes": ["TC-MM-001", "TC-MM-002", "TC-MM-003", "TC-SD-001", "TC-SD-002",
                   "TC-SD-003", "TC-PP-001", "TC-PP-002", "TC-QM-001", "TC-EWM-001"]},
    {"name": "Regression-Core — Go-Live Öncesi Regresyon",
     "description": "Go-Live öncesi kritik E2E regresyon suite. is_regression=True olan TC'ler.",
     "suite_type": "Regression", "status": "draft", "module": "CROSS",
     "owner": "Deniz Aydın",
     "tags": "regression,e2e,golive",
     "tc_codes": ["TC-FI-001", "TC-FI-002", "TC-MM-001", "TC-SD-001",
                   "TC-SD-002", "TC-E2E-001", "TC-E2E-002"]},
]

# ═════════════════════════════════════════════════════════════════════════════
# TEST STEPS — Her TC için detaylı adımlar  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

STEP_DATA = [
    # ── TC-FI-001 ──
    {"tc_code": "TC-FI-001", "step_no": 1,
     "action": "MIRO ile satınalma faturası gir (PO numarası referansla)",
     "expected_result": "Fatura başlığı oluşturulur, PO kalemi otomatik getirilir",
     "test_data": "PO: 4500001234, Tutar: ₺125.000"},
    {"tc_code": "TC-FI-001", "step_no": 2,
     "action": "3-way matching kontrolü yap (PO-GR-IR)",
     "expected_result": "Tutar farkı tolerans içinde, muhasebe kayıtları otomatik oluşur",
     "test_data": "Tolerans: ±%2"},
    # ── TC-FI-002 ──
    {"tc_code": "TC-FI-002", "step_no": 1,
     "action": "Temel gıda ürünü ile satış faturası oluştur (V1 vergi kodu)",
     "expected_result": "KDV %1 otomatik hesaplanır",
     "test_data": "Malzeme: MAT-FOOD-001, Vergi kodu: V1"},
    {"tc_code": "TC-FI-002", "step_no": 2,
     "action": "İçecek ürünü ile satış faturası oluştur (V3 + ÖİV)",
     "expected_result": "KDV %20 + ÖİV doğru hesaplanır, vergi satırları ayrı görünür",
     "test_data": "Malzeme: MAT-BEV-001, Vergi kodu: V3"},
    # ── TC-FI-003 ──
    {"tc_code": "TC-FI-003", "step_no": 1,
     "action": "ZFI_BALANCE raporu çalıştır — 3 şirket kodu seç (TFRS)",
     "expected_result": "Konsolide bilanço raporu oluşur, döviz çevrimi doğru",
     "test_data": "Şirket kodları: 1000/2000/3000, Dönem: 2026-03"},
    {"tc_code": "TC-FI-003", "step_no": 2,
     "action": "VUK versiyonu ile karşılaştır",
     "expected_result": "TFRS ve VUK bakiyeleri paralel görünür, farklar açıklanır"},
    # ── TC-MM-001 ──
    {"tc_code": "TC-MM-001", "step_no": 1,
     "action": "ME21N ile ₺200K tutarlı PO oluştur",
     "expected_result": "PO oluşur, onay WF tetiklenir — Direktör onayına düşer",
     "test_data": "Tedarikçi: 100001, Malzeme: MAT-RAW-001, Tutar: ₺200.000"},
    {"tc_code": "TC-MM-001", "step_no": 2,
     "action": "Onay WF'yi 4 kademe boyunca tamamla",
     "expected_result": "Her kademede doğru onaylayıcıya yönlendirilir, PO serbest bırakılır"},
    # ── TC-MM-002 ──
    {"tc_code": "TC-MM-002", "step_no": 1,
     "action": "Farklı SKT'li 3 lot stokta oluştur ve sevkiyat talebi gir",
     "expected_result": "FEFO kuralı ile en yakın SKT'li lot önerilir",
     "test_data": "Lot A: SKT 2026-04-15, Lot B: SKT 2026-05-01, Lot C: SKT 2026-06-30"},
    {"tc_code": "TC-MM-002", "step_no": 2,
     "action": "SKT < 30 gün olan lot için bloke kontrolü yap",
     "expected_result": "Kısa ömürlü lot otomatik bloke, uyarı mesajı"},
    # ── TC-MM-003 ──
    {"tc_code": "TC-MM-003", "step_no": 1,
     "action": "Göç programını çalıştır, staging tablodan yükle",
     "expected_result": "60.000 kayıt işlenir, hata logu oluşur",
     "test_data": "Staging tablo: ZTMP_MAT_STG, Kayıt sayısı: 60.000"},
    {"tc_code": "TC-MM-003", "step_no": 2,
     "action": "Malzeme tipi mapping ve BOM doğrulama yap",
     "expected_result": "Hata oranı < %0.5, tüm malzeme tipleri doğru eşleşmiş"},
    # ── TC-SD-001 ──
    {"tc_code": "TC-SD-001", "step_no": 1,
     "action": "VA01 → VL01N → VF01 tam akış çalıştır",
     "expected_result": "Sipariş → sevkiyat → fatura akışı sorunsuz tamamlanır",
     "test_data": "Müşteri: 200001, Malzeme: MAT-FG-001, Miktar: 100 AD"},
    {"tc_code": "TC-SD-001", "step_no": 2,
     "action": "Muhasebe kayıtlarını kontrol et (gelir/maliyet/KDV)",
     "expected_result": "FI kayıtları otomatik oluşur, bakiye doğru"},
    # ── TC-SD-002 ──
    {"tc_code": "TC-SD-002", "step_no": 1,
     "action": "VF01 fatura oluştur ve e-Fatura tetikle",
     "expected_result": "UBL-TR XML oluşur, GİB'e iletilir",
     "test_data": "Fatura tipi: ZF1, GİB ortamı: TEST"},
    {"tc_code": "TC-SD-002", "step_no": 2,
     "action": "GİB yanıtını (kabul/red) kontrol et",
     "expected_result": "Kabul yanıtı alınır, durum 'Onaylı' olarak güncellenir"},
    # ── TC-SD-003 ──
    {"tc_code": "TC-SD-003", "step_no": 1,
     "action": "Perakende kanalı üzerinden sipariş gir (ZK01 koşulu)",
     "expected_result": "Kanal iskontosu otomatik uygulanır",
     "test_data": "Kanal: Perakende, İskonto: %5"},
    {"tc_code": "TC-SD-003", "step_no": 2,
     "action": "Toptan ve e-ticaret kanalıyla aynı ürün siparişi gir, fiyat karşılaştır",
     "expected_result": "Her kanalda farklı fiyat/iskonto doğru uygulanır"},
    # ── TC-PP-001 ──
    {"tc_code": "TC-PP-001", "step_no": 1,
     "action": "MD01 MRP çalıştır, planlı sipariş → üretim emrine dönüştür",
     "expected_result": "Doğru miktar ve tarihte planlı sipariş oluşur",
     "test_data": "Malzeme: MAT-FG-001, Talep: 500 AD"},
    {"tc_code": "TC-PP-001", "step_no": 2,
     "action": "Üretim emrini serbest bırak, onay gir, maliyet hesaplat",
     "expected_result": "Emri tamamlanır, fiili maliyet hesaplanır"},
    # ── TC-PP-002 ──
    {"tc_code": "TC-PP-002", "step_no": 1,
     "action": "MES'ten üretim onay mesajı gönder (OData API)",
     "expected_result": "SAP'de BAPI ile onay kaydı oluşur",
     "test_data": "Üretim emri: 1000001, Operasyon: 0010, Miktar: 100, Hurda: 5"},
    {"tc_code": "TC-PP-002", "step_no": 2,
     "action": "Hurda miktarını doğrula ve hata mesajlarını kontrol et",
     "expected_result": "Hurda miktarı pozitif, onay başarılı kaydedilir"},
    # ── TC-QM-001 ──
    {"tc_code": "TC-QM-001", "step_no": 1,
     "action": "Gıda hammaddesi mal girişi yap (MIGO)",
     "expected_result": "Otomatik muayene lotu oluşur, HACCP kontrol noktası tetiklenir",
     "test_data": "Malzeme: MAT-RAW-FOOD-01, Muayene planı: QP-001"},
    {"tc_code": "TC-QM-001", "step_no": 2,
     "action": "HACCP sonuç gir ve kabul/red kararı ver",
     "expected_result": "Kabul → stok serbest, Red → bloke stok"},
    # ── TC-EWM-001 ──
    {"tc_code": "TC-EWM-001", "step_no": 1,
     "action": "Outbound delivery oluştur ve wave ata",
     "expected_result": "Wave oluşur, picking task otomatik başlatılır",
     "test_data": "Depo: WH01, Alan: PICK-01"},
    {"tc_code": "TC-EWM-001", "step_no": 2,
     "action": "Picking teyidi gir ve PGI yap",
     "expected_result": "Stok hareketi SAP'ye yansır, sevk irsaliyesi yazdırılabilir"},
    # ── TC-INT-001 ──
    {"tc_code": "TC-INT-001", "step_no": 1,
     "action": "MT940 banka hesap özeti dosyasını sisteme yükle",
     "expected_result": "Dosya başarılı parse edilir, ekstre kalemleri listelenir",
     "test_data": "Banka: AKBANK, Hesap: TR12 0004 6001"},
    {"tc_code": "TC-INT-001", "step_no": 2,
     "action": "Otomatik eşleştirme çalıştır, eşleşmeyen kalemleri kontrol et",
     "expected_result": "Eşleşme oranı ≥ %90, kalan kalemler işaretlenir"},
    # ── TC-E2E-001 ──
    {"tc_code": "TC-E2E-001", "step_no": 1,
     "action": "PR → PO → GR → IR tam akışı çalıştır",
     "expected_result": "Satınalma talebi → sipariş → mal girişi → fatura akışı sorunsuz",
     "test_data": "Tedarikçi: 100002, Malzeme: MAT-RAW-002, Tutar: ₺75.000"},
    {"tc_code": "TC-E2E-001", "step_no": 2,
     "action": "F110 ödeme çalıştır ve muhasebe kayıtlarını doğrula",
     "expected_result": "Ödeme tamamlanır, banka hesabı bakiyesi güncellenir"},
    # ── TC-E2E-002 ──
    {"tc_code": "TC-E2E-002", "step_no": 1,
     "action": "Ay içi FI kayıtları üzerinden tahakkuk ve amortisman çalıştır",
     "expected_result": "Tahakkuk kayıtları oluşur, amortisman doğru hesaplanır",
     "test_data": "Dönem: 2026-03, Şirket kodu: 1000"},
    {"tc_code": "TC-E2E-002", "step_no": 2,
     "action": "Dönem kapanış prosedürü ve raporlama kontrolü",
     "expected_result": "Kapanış < 4 saat, bilanço/gelir tablosu doğru"},
]

# ═════════════════════════════════════════════════════════════════════════════
# CYCLE ↔ SUITE atama  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

CYCLE_SUITE_DATA = [
    # SIT Cycle 1 ← SIT-Finance suite
    {"cycle_name": "SIT Cycle 1 — Temel Akışlar",
     "suite_name": "SIT-Finance — Finans Entegrasyon Paketi", "order": 1},
    # SIT Cycle 2 ← SIT-Finance suite (regresyon)
    {"cycle_name": "SIT Cycle 2 — Hata Düzeltme & Regresyon",
     "suite_name": "SIT-Finance — Finans Entegrasyon Paketi", "order": 1},
    # UAT Cycle 1 ← UAT-Logistics suite
    {"cycle_name": "UAT Cycle 1 — İş Senaryoları",
     "suite_name": "UAT-Logistics — Lojistik Kabul Paketi", "order": 1},
    # Regression Cycle ← Regression-Core suite
    {"cycle_name": "Regression Cycle — Go-Live Öncesi",
     "suite_name": "Regression-Core — Go-Live Öncesi Regresyon", "order": 1},
]


# ═════════════════════════════════════════════════════════════════════════════
# TEST RUNS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

TEST_RUN_DATA = [
    {"cycle_name": "SIT Cycle 1 — Temel Akışlar",
     "tc_code": "TC-FI-001", "run_type": "manual", "status": "completed",
     "result": "pass", "environment": "SIT", "tester": "Ahmet Yıldız",
     "notes": "Tüm kontrol noktaları başarılı", "duration_minutes": 35},
    {"cycle_name": "SIT Cycle 1 — Temel Akışlar",
     "tc_code": "TC-FI-002", "run_type": "manual", "status": "completed",
     "result": "fail", "environment": "SIT", "tester": "Ahmet Yıldız",
     "notes": "KDV hesaplama farkı bulundu", "duration_minutes": 28},
    {"cycle_name": "SIT Cycle 1 — Temel Akışlar",
     "tc_code": "TC-MM-001", "run_type": "manual", "status": "completed",
     "result": "pass", "environment": "SIT", "tester": "Zeynep Koç",
     "notes": "PR → PO akışı sorunsuz", "duration_minutes": 40},
    {"cycle_name": "SIT Cycle 1 — Temel Akışlar",
     "tc_code": "TC-SD-001", "run_type": "automated", "status": "completed",
     "result": "pass", "environment": "SIT", "tester": "Otomasyon",
     "notes": "Selenium ile siparişten faturaya test edildi", "duration_minutes": 12},
    {"cycle_name": "UAT Cycle 1 — İş Senaryoları",
     "tc_code": "TC-WM-001", "run_type": "manual", "status": "in_progress",
     "result": "not_run", "environment": "UAT", "tester": "Hakan Güneş",
     "notes": "Depo transferi senaryosu devam ediyor"},
    {"cycle_name": "UAT Cycle 1 — İş Senaryoları",
     "tc_code": "TC-PP-001", "run_type": "manual", "status": "not_started",
     "result": "not_run", "environment": "UAT", "tester": "Elif Kara"},
]


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEP RESULTS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

STEP_RESULT_DATA = [
    # Exec 0 (TC-FI-001, pass) — 2 steps
    {"exec_index": 0, "step_no": 1, "result": "pass",
     "actual_result": "Hesap planı doğru yüklendi, bakiyeler tutarlı"},
    {"exec_index": 0, "step_no": 2, "result": "pass",
     "actual_result": "BKPF/BSEG kayıtları doğrulandı"},
    # Exec 1 (TC-FI-002, pass) — 2 steps
    {"exec_index": 1, "step_no": 1, "result": "pass",
     "actual_result": "Fatura oluşturuldu"},
    {"exec_index": 1, "step_no": 2, "result": "pass",
     "actual_result": "KDV hesaplaması doğru"},
    # Exec 2 (TC-FI-003, fail) — 2 steps
    {"exec_index": 2, "step_no": 1, "result": "pass",
     "actual_result": "Konsolide bilanço raporu çalıştı"},
    {"exec_index": 2, "step_no": 2, "result": "fail",
     "actual_result": "2. şirket kodu döviz çevrimi hatalı — kur farkı var",
     "notes": "DEF-FI-001 açıldı"},
    # Exec 3 (TC-MM-001, pass) — 2 steps
    {"exec_index": 3, "step_no": 1, "result": "pass",
     "actual_result": "PR otomatik oluşturuldu, tutar limiti doğru"},
    {"exec_index": 3, "step_no": 2, "result": "pass",
     "actual_result": "PO onay akışı 4 kademe tamamlandı"},
    # Exec 6 (TC-SD-001, pass) — 2 steps
    {"exec_index": 6, "step_no": 1, "result": "pass",
     "actual_result": "Siparişten teslimata akış başarılı"},
    {"exec_index": 6, "step_no": 2, "result": "pass",
     "actual_result": "Fatura ve muhasebe kayıtları eşleşti"},
]


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT COMMENTS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

DEFECT_COMMENT_DATA = [
    # Defect index 0 (P1 blocker — KDV farkı)
    {"defect_index": 0, "author": "Ahmet Yıldız",
     "body": "SIT ortamında KDV %18 yerine %10 hesaplanıyor. Gıda kategorisi mapping tablosu kontrol edilmeli."},
    {"defect_index": 0, "author": "Elif Kara",
     "body": "BAdI TAX_CALC_ENHANCE'da condition type koşulu eksik. Fix branch açıldı."},
    {"defect_index": 0, "author": "Kemal Erdoğan",
     "body": "Transport K900123 ile düzeltme taşındı. Retest bekleniyor."},
    # Defect index 1 (PO onay)
    {"defect_index": 1, "author": "Zeynep Koç",
     "body": "PO onay timeout yapısı BRF+'da kontrol edilecek. SLA 24 saat."},
    # Defect index 3 (Batch yönetimi)
    {"defect_index": 3, "author": "Hakan Güneş",
     "body": "FEFO sıralamasında aynı batch tarihi olan kayıtlarda FIFO uygulanmalı."},
    {"defect_index": 3, "author": "Deniz Aydın",
     "body": "User exit ZFEFO_SORT'a ek sort kriteri eklendi."},
]


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT HISTORY  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

DEFECT_HISTORY_DATA = [
    # Defect index 0 lifecycle
    {"defect_index": 0, "field": "status", "old_value": "open",
     "new_value": "in_progress", "changed_by": "Elif Kara"},
    {"defect_index": 0, "field": "assigned_to", "old_value": "",
     "new_value": "Elif Kara", "changed_by": "Deniz Aydın"},
    {"defect_index": 0, "field": "status", "old_value": "in_progress",
     "new_value": "resolved", "changed_by": "Elif Kara"},
    {"defect_index": 0, "field": "resolution", "old_value": "",
     "new_value": "BAdI condition type düzeltildi", "changed_by": "Elif Kara"},
    # Defect index 2 (GR-IR)
    {"defect_index": 2, "field": "severity", "old_value": "medium",
     "new_value": "high", "changed_by": "Kemal Erdoğan"},
    {"defect_index": 2, "field": "status", "old_value": "open",
     "new_value": "in_progress", "changed_by": "Ahmet Yıldız"},
]


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT LINKS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

DEFECT_LINK_DATA = [
    # Defect 0 ↔ Defect 1: related (KDV + PO onay her ikisi de Finans)
    {"source_index": 0, "target_index": 1,
     "link_type": "related", "notes": "Her ikisi de SIT-Finance paketinde tespit edildi"},
    # Defect 3 ↔ Defect 4: related (Batch + MES)
    {"source_index": 3, "target_index": 4,
     "link_type": "related", "notes": "Her ikisi de envanter yönetimi ile ilgili"},
    # Defect 5 blocks Defect 6 (E2E → Konsolidasyon)
    {"source_index": 5, "target_index": 6,
     "link_type": "blocks", "notes": "E2E akış kapanmadan konsolidasyon testi yapılamaz"},
]


# ═════════════════════════════════════════════════════════════════════════════
# UAT SIGN-OFFS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

UAT_SIGNOFF_DATA = [
    {"cycle_name": "UAT Cycle 1 — İş Senaryoları",
     "process_area": "Finance", "scope_item_id": None,
     "signed_off_by": "Kemal Erdoğan", "role": "PM",
     "status": "approved", "comments": "Tüm finans senaryoları başarılı test edildi"},
    {"cycle_name": "UAT Cycle 1 — İş Senaryoları",
     "process_area": "Logistics", "scope_item_id": None,
     "signed_off_by": "Elif Kara", "role": "BPO",
     "status": "approved", "comments": "Tedarik zinciri süreçleri onaylandı"},
    {"cycle_name": "UAT Cycle 1 — İş Senaryoları",
     "process_area": "Production", "scope_item_id": None,
     "signed_off_by": "Deniz Aydın", "role": "BPO",
     "status": "pending", "comments": "MES entegrasyonu bekleniyor"},
]


# ═════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TEST RESULTS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

PERF_RESULT_DATA = [
    {"tc_code": "TC-FI-001", "run_index": 0,
     "response_time_ms": 1200, "throughput_rps": 85.5,
     "concurrent_users": 50, "target_response_ms": 2000,
     "target_throughput_rps": 80.0, "environment": "PERF",
     "notes": "Fatura kayıt performansı hedef dahilinde"},
    {"tc_code": "TC-SD-001", "run_index": 3,
     "response_time_ms": 3500, "throughput_rps": 45.2,
     "concurrent_users": 100, "target_response_ms": 3000,
     "target_throughput_rps": 50.0, "environment": "PERF",
     "notes": "OTC E2E performansı hedef üzerinde — optimizasyon gerekli"},
    {"tc_code": "TC-MM-001", "run_index": 2,
     "response_time_ms": 800, "throughput_rps": 120.0,
     "concurrent_users": 50, "target_response_ms": 1500,
     "target_throughput_rps": 100.0, "environment": "PERF",
     "notes": "PO oluşturma performansı mükemmel"},
]


# ═════════════════════════════════════════════════════════════════════════════
# TEST DAILY SNAPSHOTS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

SNAPSHOT_DATA = [
    {"snapshot_date": "2026-03-10", "cycle_name": "SIT Cycle 1 — Temel Akışlar",
     "wave": "Wave 1", "total_cases": 18, "passed": 10, "failed": 3,
     "blocked": 1, "not_run": 4,
     "open_defects_s1": 1, "open_defects_s2": 2,
     "open_defects_s3": 3, "open_defects_s4": 1, "closed_defects": 1},
    {"snapshot_date": "2026-03-15", "cycle_name": "SIT Cycle 1 — Temel Akışlar",
     "wave": "Wave 1", "total_cases": 18, "passed": 14, "failed": 2,
     "blocked": 0, "not_run": 2,
     "open_defects_s1": 0, "open_defects_s2": 1,
     "open_defects_s3": 2, "open_defects_s4": 1, "closed_defects": 4},
    {"snapshot_date": "2026-03-20", "cycle_name": "SIT Cycle 1 — Temel Akışlar",
     "wave": "Wave 1", "total_cases": 18, "passed": 16, "failed": 1,
     "blocked": 0, "not_run": 1,
     "open_defects_s1": 0, "open_defects_s2": 0,
     "open_defects_s3": 1, "open_defects_s4": 1, "closed_defects": 6},
]
