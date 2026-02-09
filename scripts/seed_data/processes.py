"""
Aşama 3 — Process Hierarchy (Signavio L2→L3→L4) + Analysis
Şirket: Anadolu Gıda ve İçecek A.Ş.

_area key maps each L2 tree to its parent Scenario's process_area.
Hierarchy:
  L2 = Process Area (scope_confirmation)
  L3 = E2E Process  (scope_decision, fit_gap, cloud_alm_ref, test_scope)
  L4 = Sub Process  (activate_output, wricef_type, test_levels)
"""

from datetime import date

# ═══════════════════════════════════════════════════════════════════════════
# ORDER-TO-CASH  (maps to Scenario L1.3)
# ═══════════════════════════════════════════════════════════════════════════

_OTC_1 = {
    "_area": "order_to_cash",
    "name": "Satış Sipariş Yönetimi", "level": "L2", "module": "SD",
    "process_id_code": "O2C-01", "order": 1, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Standart Satış Siparişi", "level": "L3", "module": "SD", "order": 1,
         "code": "1OC", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-1OC", "sap_tcode": "VA01", "priority": "critical",
         "cloud_alm_ref": "CALM-OTC-001", "test_scope": "full",
         "analyses": [
             {"name": "Satış Siparişi Fit-Gap", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "fit",
              "decision": "Standart SAP konfigürasyonu yeterli.",
              "attendees": "Burak Şahin, Satış Müdürü", "date": date(2025, 9, 18)},
         ],
         "children": [
             {"name": "Sipariş Oluşturma", "level": "L4", "module": "SD", "order": 1,
              "code": "1OC-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "wricef_type": "", "test_levels": "unit,sit,uat"},
             {"name": "Fiyatlandırma Hesaplama", "level": "L4", "module": "SD", "order": 2,
              "code": "1OC-02", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
             {"name": "Kredi Kontrol", "level": "L4", "module": "SD", "order": 3,
              "code": "1OC-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "wricef", "wricef_type": "workflow", "test_levels": "unit,sit,uat"},
             {"name": "ATP Kontrolü", "level": "L4", "module": "SD", "order": 4,
              "code": "1OC-04", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "wricef_type": "", "test_levels": "sit,uat"},
         ]},
        {"name": "Konsinye Satış", "level": "L3", "module": "SD", "order": 2,
         "code": "2OC", "scope_decision": "deferred", "priority": "low",
         "sap_reference": "BP-2OC", "cloud_alm_ref": "CALM-OTC-002"},
    ],
}

_OTC_2 = {
    "_area": "order_to_cash",
    "name": "Teslimat ve Sevkiyat", "level": "L2", "module": "SD",
    "process_id_code": "O2C-02", "order": 2, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Standart Teslimat Süreci", "level": "L3", "module": "SD", "order": 1,
         "code": "3OC", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-3OC", "sap_tcode": "VL01N", "priority": "high",
         "cloud_alm_ref": "CALM-OTC-003", "test_scope": "full",
         "children": [
             {"name": "Teslimat Oluşturma", "level": "L4", "module": "SD", "order": 1,
              "code": "3OC-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Malzeme Çıkışı (GI)", "level": "L4", "module": "SD", "order": 2,
              "code": "3OC-02", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
             {"name": "Sevk İrsaliyesi Yazdırma", "level": "L4", "module": "SD", "order": 3,
              "code": "3OC-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "form", "wricef_type": "form", "test_levels": "unit,sit,uat"},
         ]},
    ],
}

_OTC_3 = {
    "_area": "order_to_cash",
    "name": "Faturalama ve Tahsilat", "level": "L2", "module": "SD",
    "process_id_code": "O2C-03", "order": 3, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Fatura İşleme", "level": "L3", "module": "SD", "order": 1,
         "code": "4OC", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-4OC", "sap_tcode": "VF01", "priority": "critical",
         "cloud_alm_ref": "CALM-OTC-004", "test_scope": "full",
         "analyses": [
             {"name": "Faturalama Fit-Gap", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "partial_fit",
              "decision": "e-Fatura/e-İrsaliye için GİB entegrasyonu gerekli.",
              "attendees": "Burak Şahin, Muhasebe", "date": date(2025, 9, 20)},
         ],
         "children": [
             {"name": "Fatura Oluşturma", "level": "L4", "module": "SD", "order": 1,
              "code": "4OC-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "e-Fatura GİB Entegrasyonu", "level": "L4", "module": "SD", "order": 2,
              "code": "4OC-02", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "interface", "wricef_type": "interface", "test_levels": "unit,sit,uat"},
             {"name": "e-İrsaliye GİB Entegrasyonu", "level": "L4", "module": "SD", "order": 3,
              "code": "4OC-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "interface", "wricef_type": "interface", "test_levels": "unit,sit,uat"},
             {"name": "Tahsilat ve Mutabakat", "level": "L4", "module": "FI", "order": 4,
              "code": "4OC-04", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
         ]},
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# PROCURE-TO-PAY  (maps to Scenario L1.4)
# ═══════════════════════════════════════════════════════════════════════════

_P2P_1 = {
    "_area": "procure_to_pay",
    "name": "Satınalma Süreci", "level": "L2", "module": "MM",
    "process_id_code": "P2P-01", "order": 1, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Direkt Malzeme Satınalma", "level": "L3", "module": "MM", "order": 1,
         "code": "1PP", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-1PP", "sap_tcode": "ME21N", "priority": "critical",
         "cloud_alm_ref": "CALM-P2P-001", "test_scope": "full",
         "analyses": [
             {"name": "Satınalma Fit-Gap Workshop", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "fit",
              "decision": "Standart SAP satınalma süreci kullanılacak.",
              "attendees": "Elif Kara, Satınalma Müdürü", "date": date(2025, 9, 20)},
         ],
         "children": [
             {"name": "Satınalma Talebi (PR)", "level": "L4", "module": "MM", "order": 1,
              "code": "1PP-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Teklif Toplama (RFQ)", "level": "L4", "module": "MM", "order": 2,
              "code": "1PP-02", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit"},
             {"name": "PO Onay İş Akışı", "level": "L4", "module": "MM", "order": 3,
              "code": "1PP-03", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "workflow_config", "wricef_type": "workflow", "test_levels": "unit,sit,uat"},
             {"name": "Mal Girişi (GR)", "level": "L4", "module": "MM", "order": 4,
              "code": "1PP-04", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
             {"name": "Fatura Doğrulama (IV)", "level": "L4", "module": "MM", "order": 5,
              "code": "1PP-05", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
         ]},
        {"name": "Hizmet Satınalma", "level": "L3", "module": "MM", "order": 2,
         "code": "2PP", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-2PP", "sap_tcode": "ME23N", "priority": "medium",
         "cloud_alm_ref": "CALM-P2P-002", "test_scope": "regression",
         "children": [
             {"name": "Hizmet Giriş Belgesi", "level": "L4", "module": "MM", "order": 1,
              "code": "2PP-01", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
         ]},
    ],
}

_P2P_2 = {
    "_area": "procure_to_pay",
    "name": "Stok Yönetimi", "level": "L2", "module": "MM",
    "process_id_code": "P2P-02", "order": 2, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Stok Transferi ve Sayımı", "level": "L3", "module": "MM", "order": 1,
         "code": "3PP", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-3PP", "sap_tcode": "MB1B", "priority": "high",
         "cloud_alm_ref": "CALM-P2P-003", "test_scope": "full",
         "children": [
             {"name": "Tesisler Arası Transfer", "level": "L4", "module": "MM", "order": 1,
              "code": "3PP-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
             {"name": "Stok Sayımı (MI01)", "level": "L4", "module": "MM", "order": 2,
              "code": "3PP-02", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Stok Değerleme Raporu", "level": "L4", "module": "MM", "order": 3,
              "code": "3PP-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "report", "wricef_type": "report", "test_levels": "unit,sit,uat"},
         ]},
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# RECORD-TO-REPORT  (maps to Scenario L1.2 — Finansal Muhasebe)
# ═══════════════════════════════════════════════════════════════════════════

_R2R_1 = {
    "_area": "record_to_report",
    "name": "Genel Muhasebe (GL)", "level": "L2", "module": "FI",
    "process_id_code": "R2R-01", "order": 1, "scope_confirmation": "confirmed",
    "children": [
        {"name": "GL Kayıt ve Dönem Kapanışı", "level": "L3", "module": "FI", "order": 1,
         "code": "1RR", "scope_decision": "in_scope", "fit_gap": "gap",
         "sap_reference": "BP-1RR", "sap_tcode": "FB50", "priority": "critical",
         "cloud_alm_ref": "CALM-R2R-001", "test_scope": "full",
         "analyses": [
             {"name": "FI Genel Muhasebe Fit-Gap", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "gap",
              "decision": "VUK uyumu için ek geliştirme gerekli. TFRS paralel raporlama.",
              "attendees": "Ahmet Yıldız, CFO, YMM", "date": date(2025, 9, 15)},
         ],
         "children": [
             {"name": "GL Kayıt Girişi", "level": "L4", "module": "FI", "order": 1,
              "code": "1RR-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "VUK Uyum Raporları", "level": "L4", "module": "FI", "order": 2,
              "code": "1RR-02", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "report", "wricef_type": "report", "test_levels": "unit,sit,uat"},
             {"name": "Dönem Kapanışı", "level": "L4", "module": "FI", "order": 3,
              "code": "1RR-03", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
             {"name": "Banka Mutabakatı", "level": "L4", "module": "FI", "order": 4,
              "code": "1RR-04", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "interface", "wricef_type": "interface", "test_levels": "unit,sit,uat"},
         ]},
    ],
}

_R2R_2 = {
    "_area": "record_to_report",
    "name": "Borç / Alacak Yönetimi", "level": "L2", "module": "FI",
    "process_id_code": "R2R-02", "order": 2, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Tedarikçi Fatura ve Ödeme", "level": "L3", "module": "FI", "order": 1,
         "code": "2RR", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-2RR", "sap_tcode": "FB60", "priority": "high",
         "cloud_alm_ref": "CALM-R2R-002", "test_scope": "full",
         "children": [
             {"name": "Gelen Fatura Kaydı", "level": "L4", "module": "FI", "order": 1,
              "code": "2RR-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Otomatik Ödeme (F110)", "level": "L4", "module": "FI", "order": 2,
              "code": "2RR-02", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
             {"name": "Banka Ödeme Dosyası", "level": "L4", "module": "FI", "order": 3,
              "code": "2RR-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "interface", "wricef_type": "interface", "test_levels": "unit,sit,uat"},
         ]},
        {"name": "Sabit Kıymet Yönetimi", "level": "L3", "module": "FI", "order": 2,
         "code": "3RR", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-3RR", "sap_tcode": "AS01", "priority": "high",
         "cloud_alm_ref": "CALM-R2R-003", "test_scope": "regression"},
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# PLAN-TO-PRODUCE  (maps to Scenario L1.5)
# ═══════════════════════════════════════════════════════════════════════════

_P2M_1 = {
    "_area": "plan_to_produce",
    "name": "Üretim Planlama (MRP)", "level": "L2", "module": "PP",
    "process_id_code": "P2M-01", "order": 1, "scope_confirmation": "confirmed",
    "children": [
        {"name": "MRP ve Talep Planlama", "level": "L3", "module": "PP", "order": 1,
         "code": "1PM", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-1PM", "sap_tcode": "MD01", "priority": "critical",
         "cloud_alm_ref": "CALM-P2M-001", "test_scope": "full",
         "analyses": [
             {"name": "PP MRP Fit-Gap Workshop", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "partial_fit",
              "decision": "MRP parametreleri gıda sektörüne uyarlanacak. Raf ömrü kontrolü ek geliştirme.",
              "attendees": "Deniz Aydın, Üretim Müdürü, Planlama Şefi", "date": date(2025, 10, 15)},
         ],
         "children": [
             {"name": "MRP Çalıştırma", "level": "L4", "module": "PP", "order": 1,
              "code": "1PM-01", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Üretim Emri Oluşturma", "level": "L4", "module": "PP", "order": 2,
              "code": "1PM-02", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
             {"name": "Kapasite Planlama", "level": "L4", "module": "PP", "order": 3,
              "code": "1PM-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "wricef", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
         ]},
    ],
}

_P2M_2 = {
    "_area": "plan_to_produce",
    "name": "Üretim Yürütme", "level": "L2", "module": "PP",
    "process_id_code": "P2M-02", "order": 2, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Üretim Onay ve Tüketim", "level": "L3", "module": "PP", "order": 1,
         "code": "2PM", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-2PM", "sap_tcode": "CO11N", "priority": "high",
         "cloud_alm_ref": "CALM-P2M-002", "test_scope": "full",
         "children": [
             {"name": "Üretim Onayı (Confirmation)", "level": "L4", "module": "PP", "order": 1,
              "code": "2PM-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
             {"name": "MES Entegrasyonu", "level": "L4", "module": "PP", "order": 2,
              "code": "2PM-02", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "interface", "wricef_type": "interface", "test_levels": "unit,sit,uat"},
             {"name": "Hurda ve Fire Bildirimi", "level": "L4", "module": "PP", "order": 3,
              "code": "2PM-03", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
         ]},
        {"name": "Kalite Kontrol (QM)", "level": "L3", "module": "QM", "order": 2,
         "code": "3PM", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-3PM", "sap_tcode": "QA01", "priority": "high",
         "cloud_alm_ref": "CALM-P2M-003", "test_scope": "full",
         "analyses": [
             {"name": "QM HACCP Workshop", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "partial_fit",
              "decision": "HACCP kontrol noktaları konfigüre edilecek. Ek sertifika raporu gerekli.",
              "attendees": "Deniz Aydın, Kalite Direktörü, HACCP Sorumlusu", "date": date(2025, 10, 22)},
         ],
         "children": [
             {"name": "Kalite Muayene Emri", "level": "L4", "module": "QM", "order": 1,
              "code": "3PM-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "HACCP Kontrol Noktası", "level": "L4", "module": "QM", "order": 2,
              "code": "3PM-02", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
             {"name": "Kalite Sertifikası Yazdırma", "level": "L4", "module": "QM", "order": 3,
              "code": "3PM-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "form", "wricef_type": "form", "test_levels": "unit,sit,uat"},
         ]},
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# WAREHOUSE MANAGEMENT  (maps to Scenario L1.6)
# ═══════════════════════════════════════════════════════════════════════════

_WM_1 = {
    "_area": "warehouse_mgmt",
    "name": "Depo İçi Operasyonlar", "level": "L2", "module": "EWM",
    "process_id_code": "WM-01", "order": 1, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Mal Kabul ve Yerine Koyma", "level": "L3", "module": "EWM", "order": 1,
         "code": "1WM", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-1WM", "priority": "high",
         "cloud_alm_ref": "CALM-WM-001", "test_scope": "full",
         "children": [
             {"name": "Mal Kabul (Inbound)", "level": "L4", "module": "EWM", "order": 1,
              "code": "1WM-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Raf Atama (Putaway)", "level": "L4", "module": "EWM", "order": 2,
              "code": "1WM-02", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
         ]},
        {"name": "Toplama ve Sevkiyat", "level": "L3", "module": "EWM", "order": 2,
         "code": "2WM", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-2WM", "priority": "high",
         "cloud_alm_ref": "CALM-WM-002", "test_scope": "full",
         "children": [
             {"name": "Wave Picking", "level": "L4", "module": "EWM", "order": 1,
              "code": "2WM-01", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Yükleme ve Sevk", "level": "L4", "module": "EWM", "order": 2,
              "code": "2WM-02", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
         ]},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# ASSEMBLED LIST
# ═══════════════════════════════════════════════════════════════════════════

PROCESS_SEED = [
    # Order-to-Cash
    _OTC_1, _OTC_2, _OTC_3,
    # Procure-to-Pay
    _P2P_1, _P2P_2,
    # Record-to-Report
    _R2R_1, _R2R_2,
    # Plan-to-Produce
    _P2M_1, _P2M_2,
    # Warehouse
    _WM_1,
]
