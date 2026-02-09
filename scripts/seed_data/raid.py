"""
Aşama 7 — RAID: Risk, Action, Issue, Decision
Şirket: Anadolu Gıda ve İçecek A.Ş.

 8 Risks     (probability × impact scoring, RAG)
10 Actions   (preventive, corrective, follow_up)
 6 Issues    (open, investigating, escalated, resolved, closed)
 8 Decisions (approved, pending_approval, proposed)
"""

# ═════════════════════════════════════════════════════════════════════════════
# RISKS — probability(1-5) × impact(1-5) → score, rag_status otomatik hesaplanır
# ═════════════════════════════════════════════════════════════════════════════

RISK_DATA = [
    {"title": "Veri göçü gecikme riski — 60K malzeme ana veri",
     "description": "60.000 malzeme kaydının göçü planlanan sürede tamamlanamayabilir. BOM, reçete, raf ömrü bilgileri karmaşık dönüşüm gerektiriyor.",
     "status": "mitigating", "owner": "Hakan Güneş", "priority": "critical",
     "probability": 4, "impact": 5,
     "risk_category": "technical", "risk_response": "mitigate",
     "mitigation_plan": "Paralel göç yaklaşımı: 3 takım, her biri 20K kayıt. Delta göç stratejisi.",
     "contingency_plan": "Go-live'ı 1 ay ertele. Kritik malzemeleri öncelikle göç et.",
     "trigger_event": "Sprint 3 sonunda göç pilot testi %80 altında kalırsa"},

    {"title": "GİB e-Fatura entegrasyon kesintisi riski",
     "description": "GİB altyapı güncellemesi nedeniyle e-Fatura/e-İrsaliye servisi kesintiye uğrayabilir.",
     "status": "identified", "owner": "Zeynep Koç", "priority": "high",
     "probability": 3, "impact": 5,
     "risk_category": "external", "risk_response": "mitigate",
     "mitigation_plan": "Offline kuyruk mekanizması. GİB kesintisinde faturalar kuyruğa alınır, servis gelince otomatik gönderim.",
     "contingency_plan": "Manuel GİB portal üzerinden fatura gönderim prosedürü hazırla.",
     "trigger_event": "GİB'den bakım duyurusu veya 30dk+ timeout"},

    {"title": "Anahtar kullanıcı kaynak yetersizliği",
     "description": "Anahtar kullanıcılar günlük operasyondan çekilemiyor. Explore fazında workshop katılım oranı %65'e düşmüştü.",
     "status": "mitigating", "owner": "Canan Öztürk", "priority": "high",
     "probability": 4, "impact": 4,
     "risk_category": "resource", "risk_response": "mitigate",
     "mitigation_plan": "Yönetimden resmi destek mektubu. Anahtar kullanıcılar %50 proje tahsisi. Yedek kullanıcı belirleme.",
     "contingency_plan": "Dış danışman ile anahtar kullanıcı desteği.",
     "trigger_event": "Workshop katılım oranı %70 altına düşerse"},

    {"title": "BTP CPI lisans ve kapasite sınırı riski",
     "description": "BTP CPI integration credits yetersiz kalabilir. 6 arayüz + e-Belge yoğun mesaj trafiği.",
     "status": "analysed", "owner": "Murat Çelik", "priority": "medium",
     "probability": 2, "impact": 4,
     "risk_category": "commercial", "risk_response": "accept",
     "mitigation_plan": "Mevcut credit kullanımı izle. Batch optimizasyonu ile mesaj sayısını düşür.",
     "contingency_plan": "Ek credit paketi satın al (₺150K bütçe ayrıldı).",
     "trigger_event": "Credit kullanımı %80'i aşarsa"},

    {"title": "Gıda mevzuat değişikliği — KDV oranı güncellemesi",
     "description": "Hükümetin gıda KDV oranlarını değiştirme olasılığı. Son 2 yılda 3 kez güncellendi.",
     "status": "identified", "owner": "Ahmet Yıldız", "priority": "medium",
     "probability": 3, "impact": 3,
     "risk_category": "external", "risk_response": "accept",
     "mitigation_plan": "Vergi kodları parametre bazlı tasarlandı. Değişiklik 1 gün içinde uygulanabilir.",
     "contingency_plan": "Acil konfigürasyon değişiklik prosedürü ve CAB hızlı onay akışı.",
     "trigger_event": "Resmi Gazete'de KDV oranı değişikliği yayınlanırsa"},

    {"title": "Go-Live tarihinde üretim dondurma süresi uzama riski",
     "description": "Cutover sırasında üretim/sevkiyat durdurma süresi planlanan 48 saati aşabilir.",
     "status": "identified", "owner": "Kemal Erdoğan", "priority": "critical",
     "probability": 3, "impact": 5,
     "risk_category": "schedule", "risk_response": "mitigate",
     "mitigation_plan": "2 cutover rehearsal planlı. Her rehearsal'da süre optimize edilecek. Paralel çalıştırma senaryosu.",
     "contingency_plan": "Go-live'ı uzun tatil dönemine kaydır (hafta sonu + resmi tatil).",
     "trigger_event": "Cutover rehearsal 1'de süre 48 saati aşarsa"},

    {"title": "SOD (Segregation of Duties) ihlal riski",
     "description": "Yetkilendirme rol tanımlarında görevler ayrılığı prensibi ihlal edilebilir. GRC analizi henüz başlamadı.",
     "status": "identified", "owner": "Murat Çelik", "priority": "high",
     "probability": 3, "impact": 4,
     "risk_category": "organisational", "risk_response": "mitigate",
     "mitigation_plan": "GRC Access Control erken implementasyon. SOD risk analizi Realize fazı ortasında tamamlanacak.",
     "contingency_plan": "Mitigating control tanımlayarak geçici istisnalar.",
     "trigger_event": "GRC analiz raporunda yüksek riskli SOD çakışması bulunursa"},

    {"title": "MES entegrasyon partner'ı gecikme riski",
     "description": "MES tarafındaki API geliştirmesi 3. parti firma tarafından yapılıyor. Takvim kontrolümüzde değil.",
     "status": "mitigating", "owner": "Zeynep Koç", "priority": "medium",
     "probability": 3, "impact": 3,
     "risk_category": "external", "risk_response": "mitigate",
     "mitigation_plan": "Haftalık MES firma ile sync toplantısı. Mock API ile paralel geliştirme.",
     "contingency_plan": "MES entegrasyonu go-live+1 fazına ertelenebilir. Manuel onay girişi devreye alınır.",
     "trigger_event": "MES API milestone 2 hafta geçikirse"},
]

# ═════════════════════════════════════════════════════════════════════════════
# ACTIONS
# ═════════════════════════════════════════════════════════════════════════════

ACTION_DATA = [
    {"title": "Veri göçü pilot çalıştırma — 1.000 malzeme",
     "description": "Göç programının 1.000 kayıtlık pilot testi. Hata oranı ve performans ölçümü.",
     "status": "completed", "owner": "Hakan Güneş", "priority": "critical",
     "action_type": "preventive",
     "due_date": "2026-01-30", "completed_date": "2026-01-28"},

    {"title": "GİB test ortamı sertifika yenileme",
     "description": "GİB özel entegratör mTLS sertifikası 2026-02-28'de bitiyor. Yenileme başvurusu yapılmalı.",
     "status": "in_progress", "owner": "Zeynep Koç", "priority": "high",
     "action_type": "preventive",
     "due_date": "2026-02-15"},

    {"title": "Anahtar kullanıcı tahsis mektubu — yönetim onayı",
     "description": "Anahtar kullanıcıların %50 proje tahsisi için üst yönetim onay mektubu.",
     "status": "completed", "owner": "Canan Öztürk", "priority": "high",
     "action_type": "corrective",
     "due_date": "2026-01-15", "completed_date": "2026-01-12"},

    {"title": "BTP CPI credit kullanım dashboard'u oluştur",
     "description": "Aylık credit tüketimi izleme dashboard'u. Alert threshold %80.",
     "status": "open", "owner": "Murat Çelik", "priority": "medium",
     "action_type": "detective",
     "due_date": "2026-02-28"},

    {"title": "Cutover rehearsal 1 planı hazırla",
     "description": "İlk cutover rehearsal senaryosu. Adım adım plan, başarı kriterleri, rollback prosedürü.",
     "status": "open", "owner": "Kemal Erdoğan", "priority": "critical",
     "action_type": "preventive",
     "due_date": "2026-04-30"},

    {"title": "SOD risk matrisi oluştur",
     "description": "SAP GRC Access Control ile SOD risk matrisi. Kritik işlem çakışmaları.",
     "status": "open", "owner": "Murat Çelik", "priority": "high",
     "action_type": "preventive",
     "due_date": "2026-03-31"},

    {"title": "MES API mock server kurulumu",
     "description": "MES firma API'si hazır olana kadar mock server ile paralel geliştirme.",
     "status": "completed", "owner": "Zeynep Koç", "priority": "medium",
     "action_type": "corrective",
     "due_date": "2026-01-20", "completed_date": "2026-01-18"},

    {"title": "SIT Cycle 1 defect triage toplantısı düzenle",
     "description": "SIT C1 sonrası P1/P2 defectlerin kök neden analizi ve fix planı.",
     "status": "completed", "owner": "Ayşe Polat", "priority": "high",
     "action_type": "corrective",
     "due_date": "2026-03-22", "completed_date": "2026-03-22"},

    {"title": "UAT test senaryosu hazırlık — anahtar kullanıcı eğitimi",
     "description": "Anahtar kullanıcılara UAT test senaryosu yazma eğitimi.",
     "status": "open", "owner": "Ayşe Polat", "priority": "medium",
     "action_type": "preventive",
     "due_date": "2026-06-15"},

    {"title": "Eğitim materyali hazırlık — son kullanıcı kılavuzları",
     "description": "FI/MM/SD/PP modülleri için son kullanıcı eğitim kılavuzları (Türkçe).",
     "status": "open", "owner": "Canan Öztürk", "priority": "medium",
     "action_type": "follow_up",
     "due_date": "2026-08-31"},
]

# ═════════════════════════════════════════════════════════════════════════════
# ISSUES
# ═════════════════════════════════════════════════════════════════════════════

ISSUE_DATA = [
    {"title": "QAS ortamı performans düşüklüğü — SIT yavaşlığı",
     "description": "QAS ortamında uzun süren HANA sorguları var. SIT testleri hedef sürenin 2 katı sürüyor.",
     "status": "investigating", "owner": "Murat Çelik", "priority": "high",
     "severity": "major",
     "escalation_path": "Basis Lead → SAP Support → Architecture Board",
     "root_cause": "HANA memory allocation yetersiz. Test verisinin boyutu production'a yakın.",
     "resolution": ""},

    {"title": "e-Fatura GİB timeout sorunu — 60sn aşımı",
     "description": "SIT sırasında GİB test ortamında sürekli timeout. P1 defect (DEF-SD-001) ile bağlantılı.",
     "status": "escalated", "owner": "Zeynep Koç", "priority": "critical",
     "severity": "critical",
     "escalation_path": "Integration Lead → Architecture Board → Steering Committee",
     "root_cause": "GİB test ortamı kapasite sınırı + CPI retry mekanizması eksik",
     "resolution": ""},

    {"title": "Explore fazı workshop kararları belgelenmemiş",
     "description": "Bazı Explore fazı workshop'larında alınan kararlar resmi karar loguna işlenmemiş. 8 workshop'ta eksik.",
     "status": "resolved", "owner": "Canan Öztürk", "priority": "medium",
     "severity": "moderate",
     "root_cause": "Workshop moderatörleri karar log prosedürüne uymadı",
     "resolution": "Eksik kararlar geriye dönük belgelendi. Prosedür hatırlatma eğitimi verildi.",
     "resolution_date": "2026-01-25"},

    {"title": "MES firma API dokümanı eksik — field mapping tamamlanamıyor",
     "description": "MES firmasından beklenen API spesifikasyonu 2 haftadır gecikiyor. INT-PP-001 bloke.",
     "status": "open", "owner": "Zeynep Koç", "priority": "high",
     "severity": "major",
     "escalation_path": "Integration Lead → PMO → Steering Committee"},

    {"title": "Tedarikçi ana veri kalitesi düşük — göç engeli",
     "description": "ECC'deki 4.000 tedarikçi kaydının %35'inde adres bilgisi eksik veya tutarsız.",
     "status": "investigating", "owner": "Hakan Güneş", "priority": "high",
     "severity": "major",
     "root_cause": "ECC'de veri kalite kontrolü uygulanmamış. 10+ yıllık kirli veri birikimi."},

    {"title": "Fiori Launchpad erişim sorunu — bazı roller eksik",
     "description": "Test kullanıcılarının %30'u Fiori Launchpad'e erişemiyor. Katalog / grup ataması eksik.",
     "status": "resolved", "owner": "Murat Çelik", "priority": "medium",
     "severity": "moderate",
     "root_cause": "Composite role tanımlarında katalog referansı eksik",
     "resolution": "PFCG ile composite roller güncellendi, 12 katalog ataması eklendi.",
     "resolution_date": "2026-02-05"},
]

# ═════════════════════════════════════════════════════════════════════════════
# DECISIONS
# ═════════════════════════════════════════════════════════════════════════════

DECISION_DATA = [
    {"title": "S/4HANA Cloud — Greenfield yaklaşımı",
     "description": "Mevcut ECC'den brownfield yerine greenfield dönüşüm seçildi.",
     "status": "approved", "owner": "Kemal Erdoğan", "priority": "critical",
     "decision_date": "2025-05-15", "decision_owner": "Osman Aydın (CEO)",
     "alternatives": "1. Brownfield (system conversion)\n2. Greenfield (new implementation)\n3. Selective data transition",
     "rationale": "ECC 15 yıllık customization yükü. Greenfield ile best practice süreçler. Cloud roadmap uyumu.",
     "impact_description": "Tüm süreçler sıfırdan tasarlanacak. Veri göçü gerekiyor. %30 daha fazla efor ancak uzun vadede %40 daha düşük TCO.",
     "reversible": False},

    {"title": "e-Belge entegrasyonu: BTP CPI üzerinden (direkt GİB)",
     "description": "e-Fatura/e-İrsaliye için özel entegratör yerine BTP CPI ile direkt GİB entegrasyonu.",
     "status": "approved", "owner": "Zeynep Koç", "priority": "high",
     "decision_date": "2025-10-20", "decision_owner": "Zeynep Koç",
     "alternatives": "1. Özel entegratör (Foriba/Logo)\n2. BTP CPI direkt GİB\n3. Hybrid (entegratör + CPI)",
     "rationale": "Ek lisans maliyeti yok. Tam kontrol. SAP roadmap uyumu. GİB UBL-TR 1.2 doğrudan.",
     "impact_description": "CPI geliştirme eforu daha yüksek. Ancak yıllık entegratör ücreti ₺200K tasarruf.",
     "reversible": True},

    {"title": "Üretim: Proses tipi üretim emri kullanımı (PP-PI)",
     "description": "Gıda üretimi için diskret yerine proses tipi üretim emri (PP-PI) kullanımı.",
     "status": "approved", "owner": "Deniz Aydın", "priority": "high",
     "decision_date": "2025-11-10", "decision_owner": "Deniz Aydın",
     "alternatives": "1. Diskret üretim (PP)\n2. Proses üretim (PP-PI)\n3. Karma (bazı hatlar diskret, bazıları proses)",
     "rationale": "Gıda sektörü doğası gereği proses üretim. Reçete yönetimi, batch traceability, kalite entegrasyonu.",
     "impact_description": "PP-PI konfigürasyon karmaşıklığı. Anahtar kullanıcı eğitimi ek 2 hafta.",
     "reversible": False},

    {"title": "Depo yönetimi: EWM kullanımı (WM yerine)",
     "description": "Klasik WM yerine Extended Warehouse Management (EWM) kullanılacak.",
     "status": "approved", "owner": "Gökhan Demir", "priority": "high",
     "decision_date": "2025-11-15", "decision_owner": "Gökhan Demir",
     "alternatives": "1. Stock Room Management (basit)\n2. Classic WM (uyumluluk modu)\n3. Embedded EWM (S/4 native)",
     "rationale": "8 depo, wave picking, put-away stratejileri gerekli. S/4'te WM deprecated. EWM gelecek standardı.",
     "impact_description": "EWM eğitim süresi 3 hafta. Ancak S/4 roadmap uyumu sağlanır.",
     "reversible": False},

    {"title": "Fiyatlandırma: Kanal bazlı koşul tipi stratejisi",
     "description": "Perakende, toptan, e-ticaret kanallarına özel koşul tipi yapısı.",
     "status": "approved", "owner": "Burak Şahin", "priority": "medium",
     "decision_date": "2025-12-01", "decision_owner": "Burak Şahin",
     "alternatives": "1. Tek fiyatlandırma prosedürü + koşul tablosu ayrımı\n2. Kanal başına ayrı prosedür\n3. Karma: tek prosedür + kanal koşul tipleri",
     "rationale": "Alternatif 3 seçildi. Bakım kolaylığı + kanal esnekliği. Raporlama ihtiyacı karşılanır.",
     "impact_description": "5 yeni özel koşul tipi (ZK01-ZK05). Condition record bakımı anahtar kullanıcıda.",
     "reversible": True},

    {"title": "Veri göçü: LTMC (Migration Cockpit) kullanımı",
     "description": "Veri göçü için LSMW yerine S/4 native Migration Cockpit (LTMC) kullanılacak.",
     "status": "approved", "owner": "Hakan Güneş", "priority": "medium",
     "decision_date": "2025-09-20", "decision_owner": "Hakan Güneş",
     "alternatives": "1. LSMW (eski)\n2. LTMC / Migration Cockpit (native)\n3. 3. parti göç aracı (SNP, Syniti)",
     "rationale": "LTMC S/4 native, ücretsiz, SAP destekli. Standart şablonlar mevcut. LSMW S/4'te deprecated.",
     "impact_description": "LTMC öğrenme eğrisi 2 hafta. Ancak standart şablonlarla hızlı başlangıç.",
     "reversible": True},

    {"title": "Test yönetimi: Platform içi test hub kullanımı",
     "description": "SAP Solution Manager yerine platform içi test yönetim modülü kullanılacak.",
     "status": "approved", "owner": "Ayşe Polat", "priority": "medium",
     "decision_date": "2025-10-05", "decision_owner": "Kemal Erdoğan",
     "alternatives": "1. SAP Solution Manager Test Suite\n2. HP ALM / Micro Focus\n3. Platform içi Test Hub modülü",
     "rationale": "Platform zaten test plan/cycle/case/execution/defect yönetiyor. Ek lisans gereksiz.",
     "impact_description": "Ek entegrasyon gerekmez. SAP SolMan test raporlama eksikliği kabul edilebilir.",
     "reversible": True},

    {"title": "Yetkilendirme: Fiori Space/Page tabanlı navigasyon",
     "description": "Klasik Fiori Group/Catalog yerine yeni Space/Page tabanlı navigasyon.",
     "status": "pending_approval", "owner": "Murat Çelik", "priority": "medium",
     "decision_date": None, "decision_owner": "Murat Çelik",
     "alternatives": "1. Klasik Fiori Catalog/Group\n2. Space/Page (yeni model)\n3. Hybrid: ikisi birlikte",
     "rationale": "SAP roadmap Space/Page yönünde. Ancak dokümantasyon henüz az. Pilot başlatılması öneriliyor.",
     "impact_description": "Tüm roller yeniden tanımlanmalı. Geçiş süresi 2 hafta ek efor.",
     "reversible": True},
]
