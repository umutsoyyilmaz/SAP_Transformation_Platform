# 🧪 PERGA PLATFORM — SAP Activate End-to-End Test Plan
## Copilot Execution Prompt: Full S/4HANA Transformation Simulation

**Tarih:** 2026-02-13  
**Hazırlayan:** Senior SAP Activate Program Manager  
**Amaç:** Platformun tüm fonksiyonlarını gerçekçi bir S/4HANA dönüşüm projesi senaryosuyla uçtan uca test etmek  
**Kapsam:** SAP Activate 6 Fazı — Discover → Prepare → Explore → Realize → Deploy → Run  
**Platform:** SAP Transformation Platform (Perga) — Flask + PostgreSQL + Alembic  
**Repo:** umutsoyyilmaz/SAP_Transformation_Platform

---

## 📋 TEST SENARYOSU: ACME Manufacturing S/4HANA Dönüşümü

**Müşteri:** ACME Manufacturing A.Ş. (Otomotiv yedek parça üreticisi)  
**Proje Tipi:** SAP ECC 6.0 → S/4HANA 2023 FPS02 Greenfield  
**Modüller:** MM, PP, SD, FI/CO, QM, WM→EWM, PM→S4  
**Go-Live Hedef:** 2026-Q4  
**Kullanıcı Sayısı:** 850  
**Lokasyonlar:** İstanbul (HQ), Bursa (Fabrika), Ankara (Depo), Almanya (Satış Ofisi)  

### Test Veri Seti Özeti
| Entity | Adet | Açıklama |
|--------|------|----------|
| Scenarios | 8 | O2C, P2P, M2S, R2R, H2R, P2D, W2S, QM |
| Workshops | 16 | Her senaryo için 2 workshop |
| Requirements | 60+ | Fit, Partial Fit, Gap karışımı |
| WRICEF/Backlog | 25+ | Enhancement, Report, Interface, Conversion, Form, Workflow |
| Config Items | 15+ | Standard SAP konfigürasyonlar |
| Process Levels | L1→L4 | 4 seviye süreç ağacı |
| Test Cases | 40+ | Unit, SIT, UAT, Regression |
| Test Cycles | 4 | SIT Round 1, SIT Round 2, UAT, Regression |
| Defects | 15+ | Critical, High, Medium, Low |
| Open Items | 20+ | Her fazda izlenecek açık konular |
| Team Members | 12 | Farklı roller |
| Interfaces | 8 | Inbound/Outbound |
| Cutover Tasks | 20+ | Go-Live hazırlık |

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 0: PLATFORM HEALTH CHECK & PREREQUISITES
# ═══════════════════════════════════════════════════════════════

## Amaç
Teste başlamadan önce platformun sağlıklı çalıştığını doğrula.

## Adımlar

### 0.1 — Server & DB Status
```bash
# Server çalışıyor mu?
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/
# Beklenen: 200

# DB bağlantısı
curl -s http://localhost:5000/api/v1/projects | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✅ DB OK — {len(data)} existing projects')
except:
    print('❌ DB connection failed')
"
```

### 0.2 — Endpoint Inventory Smoke Test
Aşağıdaki tüm base endpoint'lere GET isteği at, 200 veya boş liste dönmeli:

```bash
ENDPOINTS=(
    "/api/v1/projects"
    "/api/v1/scenarios"
    "/api/v1/explore/workshops"
    "/api/v1/explore/requirements"
    "/api/v1/backlog"
    "/api/v1/config-items"
    "/api/v1/testing/test-cases"
    "/api/v1/testing/test-suites"
    "/api/v1/testing/test-executions"
    "/api/v1/testing/defects"
    "/api/v1/processes"
    "/api/v1/team-members"
    "/api/v1/explore/open-items"
    "/api/v1/interfaces"
)

echo "═══ Endpoint Health Check ═══"
for EP in "${ENDPOINTS[@]}"; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5000$EP")
    if [ "$STATUS" = "200" ]; then
        echo "  ✅ $EP → $STATUS"
    else
        echo "  ❌ $EP → $STATUS"
    fi
done
```

### 0.3 — Frontend Navigation Check
Browser'da aşağıdaki sayfaları aç, F12 Console hatasız yüklenmeli:

| # | Sayfa | URL/Navigation | Kontrol |
|---|-------|----------------|---------|
| 1 | Dashboard | / | Stat kartları yükleniyor |
| 2 | Projects | Sidebar → Projects | Proje listesi |
| 3 | Scenarios | Sidebar → Scenarios | Senaryo listesi |
| 4 | Explore Workshops | Sidebar → Explore → Workshops | Workshop listesi |
| 5 | Requirements | Sidebar → Explore → Requirements | Requirement listesi |
| 6 | Backlog | Sidebar → Backlog | WRICEF listesi |
| 7 | Config Items | Sidebar → Config Items | Config listesi |
| 8 | Test Management | Sidebar → Testing | Test suites |
| 9 | Process Hierarchy | Sidebar → Processes | Süreç ağacı |
| 10 | Team Members | Sidebar → Team | Üye listesi |

**📝 RAPORLA:**
- Kaç endpoint çalışıyor / çalışmıyor?
- Hangi sayfalarda JS console hatası var?
- Dashboard stat'leri doğru veri gösteriyor mu?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 1: DISCOVER & PREPARE — Proje Kurulumu
# ═══════════════════════════════════════════════════════════════

## SAP Activate Bağlamı
Discover fazında proje tanımlanır, Prepare fazında ekip kurulur, scope belirlenir, 
süreç hiyerarşisi oluşturulur ve workshop planlaması yapılır.

---

### 1.1 — Proje Oluşturma

```bash
curl -s -X POST http://localhost:5000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ACME S/4HANA Transformation",
    "code": "ACME-S4H",
    "description": "SAP ECC 6.0 to S/4HANA 2023 FPS02 Greenfield transformation for ACME Manufacturing. Scope: MM, PP, SD, FI/CO, QM, EWM, PM. 850 users across 4 locations.",
    "customer": "ACME Manufacturing A.Ş.",
    "status": "Active",
    "start_date": "2026-03-01",
    "end_date": "2026-12-15",
    "methodology": "SAP Activate",
    "project_type": "Greenfield"
  }' | python3 -m json.tool
```

**📝 TEST KONTROL:**
- [ ] Proje oluştu mu? ID not et → `PROJECT_ID`
- [ ] Proje kodu (ACME-S4H) auto-generate mi yoksa manuel mi?
- [ ] `start_date`, `end_date` alanları var mı model'de?
- [ ] `methodology`, `project_type` alanları kabul edildi mi yoksa ignore edildi mi?
- [ ] Dashboard'da proje sayısı 1 arttı mı?
- [ ] ❓ EKSİK Mİ: Proje fazları (Discover/Prepare/Explore/Realize/Deploy/Run) takibi?
- [ ] ❓ EKSİK Mİ: Proje bazlı milestone yönetimi?
- [ ] ❓ EKSİK Mİ: Proje bütçe/effort takibi?

---

### 1.2 — Ekip Üyeleri Oluşturma

SAP projesinde tipik roller:

```bash
# Project Manager
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mehmet Yılmaz",
    "role": "Project Manager",
    "email": "mehmet.yilmaz@acme.com.tr",
    "department": "IT",
    "project_id": PROJECT_ID
  }' | python3 -m json.tool

# Solution Architect
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ayşe Kaya",
    "role": "Solution Architect",
    "email": "ayse.kaya@acme.com.tr",
    "department": "IT",
    "project_id": PROJECT_ID
  }'

# MM Functional Consultant
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ali Demir",
    "role": "MM Functional Consultant",
    "email": "ali.demir@partner.com",
    "department": "Consulting",
    "project_id": PROJECT_ID
  }'

# SD Functional Consultant
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Zeynep Arslan",
    "role": "SD Functional Consultant",
    "email": "zeynep.arslan@partner.com",
    "department": "Consulting",
    "project_id": PROJECT_ID
  }'

# FI/CO Functional Consultant
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Can Öztürk",
    "role": "FI/CO Functional Consultant",
    "email": "can.ozturk@partner.com",
    "department": "Consulting",
    "project_id": PROJECT_ID
  }'

# ABAP Developer
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Burak Şahin",
    "role": "ABAP Developer",
    "email": "burak.sahin@partner.com",
    "department": "Development",
    "project_id": PROJECT_ID
  }'

# Basis Consultant
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Emre Çelik",
    "role": "Basis/Tech Consultant",
    "email": "emre.celik@partner.com",
    "department": "Technical",
    "project_id": PROJECT_ID
  }'

# Business Process Owner (Customer Side)
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hakan Aydın",
    "role": "Business Process Owner - Supply Chain",
    "email": "hakan.aydin@acme.com.tr",
    "department": "Supply Chain",
    "project_id": PROJECT_ID
  }'

# Key User - Sales
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Selin Yıldız",
    "role": "Key User - Sales",
    "email": "selin.yildiz@acme.com.tr",
    "department": "Sales",
    "project_id": PROJECT_ID
  }'

# Key User - Finance
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Deniz Koç",
    "role": "Key User - Finance",
    "email": "deniz.koc@acme.com.tr",
    "department": "Finance",
    "project_id": PROJECT_ID
  }'

# Test Manager
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gizem Aktaş",
    "role": "Test Manager",
    "email": "gizem.aktas@partner.com",
    "department": "Quality",
    "project_id": PROJECT_ID
  }'

# Change Management Lead
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Berna Güneş",
    "role": "Change Management Lead",
    "email": "berna.gunes@acme.com.tr",
    "department": "HR",
    "project_id": PROJECT_ID
  }'
```

**📝 TEST KONTROL:**
- [ ] 12 ekip üyesi oluştu mu?
- [ ] GET /api/v1/team-members?project_id=X ile filtreleme çalışıyor mu?
- [ ] ❓ EKSİK Mİ: Rol bazlı yetkilendirme (RACI matrisi)?
- [ ] ❓ EKSİK Mİ: Ekip üyesi availability/allocation takibi?
- [ ] ❓ EKSİK Mİ: Dış danışman vs. müşteri tarafı ayrımı?
- [ ] ❓ EKSİK Mİ: Lokasyon bilgisi (İstanbul/Bursa/Ankara/Almanya)?

---

### 1.3 — Süreç Hiyerarşisi Oluşturma (L1→L4)

SAP Best Practice süreç ağacı:

```bash
# ══ L1: Order to Cash ══
curl -s -X POST http://localhost:5000/api/v1/processes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Order to Cash",
    "code": "O2C",
    "level": 1,
    "description": "End-to-end order to cash process covering inquiry, quotation, sales order, delivery, billing and payment collection",
    "project_id": PROJECT_ID
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'L1 O2C ID: {d.get(\"id\",\"?\")}')"

# L2: Sales Order Management (child of O2C)
curl -s -X POST http://localhost:5000/api/v1/processes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Order Management",
    "code": "O2C-SOM",
    "level": 2,
    "parent_id": O2C_L1_ID,
    "project_id": PROJECT_ID
  }'

# L3: Standard Sales Order (child of Sales Order Management)
curl -s -X POST http://localhost:5000/api/v1/processes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Standard Sales Order Processing",
    "code": "O2C-SOM-001",
    "level": 3,
    "parent_id": SOM_L2_ID,
    "sap_process_id": "1YG",
    "project_id": PROJECT_ID
  }'

# L4: Create Sales Order (child of Standard Sales Order)
curl -s -X POST http://localhost:5000/api/v1/processes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Create Sales Order with Reference to Quotation",
    "code": "O2C-SOM-001-01",
    "level": 4,
    "parent_id": SSO_L3_ID,
    "t_code": "VA01",
    "project_id": PROJECT_ID
  }'

# ══ L1: Procure to Pay ══
curl -s -X POST http://localhost:5000/api/v1/processes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Procure to Pay",
    "code": "P2P",
    "level": 1,
    "description": "End-to-end procurement process: purchase requisition, purchase order, goods receipt, invoice verification, payment",
    "project_id": PROJECT_ID
  }'

# L2: Purchase Order Processing
curl -s -X POST http://localhost:5000/api/v1/processes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Purchase Order Processing",
    "code": "P2P-POP",
    "level": 2,
    "parent_id": P2P_L1_ID,
    "project_id": PROJECT_ID
  }'

# L3: Standard PO
curl -s -X POST http://localhost:5000/api/v1/processes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Standard Purchase Order",
    "code": "P2P-POP-001",
    "level": 3,
    "parent_id": POP_L2_ID,
    "sap_process_id": "2UW",
    "project_id": PROJECT_ID
  }'

# ══ L1: Make to Stock / Production ══
curl -s -X POST http://localhost:5000/api/v1/processes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Make to Stock",
    "code": "M2S",
    "level": 1,
    "description": "Production planning and execution: demand management, MRP, production orders, confirmation, goods issue/receipt",
    "project_id": PROJECT_ID
  }'

# ══ L1: Record to Report ══
curl -s -X POST http://localhost:5000/api/v1/processes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Record to Report",
    "code": "R2R",
    "level": 1,
    "description": "Financial closing and reporting: GL posting, period-end closing, financial statements, consolidation",
    "project_id": PROJECT_ID
  }'
```

**📝 TEST KONTROL:**
- [ ] L1→L4 hiyerarşi doğru oluştu mu?
- [ ] `parent_id` FK ilişkisi çalışıyor mu?
- [ ] GET /api/v1/processes?project_id=X&level=1 filtreleme çalışıyor mu?
- [ ] Process tree görselleştirmesi frontend'de var mı?
- [ ] `sap_process_id` (Best Practice ID) ve `t_code` alanları kabul ediliyor mu?
- [ ] ❓ EKSİK Mİ: Process step sıralaması (sequence/order)?
- [ ] ❓ EKSİK Mİ: Scope Item (SAP Best Practice) entity'si?
- [ ] ❓ EKSİK Mİ: In Scope / Out of Scope işaretleme?
- [ ] ❓ EKSİK Mİ: L3 süreçlere SAP Fiori app ataması?
- [ ] ❓ EKSİK Mİ: Süreç akış diyagramı (BPMN-like) görselleştirme?

---

### 1.4 — Senaryo Oluşturma

```bash
# Tüm ana senaryolar
SCENARIOS='[
  {"name":"Order to Cash (O2C)","code":"S-O2C","description":"Standard and export sales, returns, credit/debit memo, consignment","module":"SD","status":"Active"},
  {"name":"Procure to Pay (P2P)","code":"S-P2P","description":"Domestic and import procurement, subcontracting, consignment, service procurement","module":"MM","status":"Active"},
  {"name":"Make to Stock (M2S)","code":"S-M2S","description":"Discrete and repetitive manufacturing, MRP, shop floor, quality in production","module":"PP","status":"Active"},
  {"name":"Record to Report (R2R)","code":"S-R2R","description":"GL, AP, AR, asset accounting, cost center, profit center, period-end closing","module":"FI/CO","status":"Active"},
  {"name":"Hire to Retire (H2R)","code":"S-H2R","description":"Employee lifecycle in SuccessFactors integration with S/4HANA payroll","module":"HCM","status":"Active"},
  {"name":"Plan to Deliver (P2D)","code":"S-P2D","description":"Warehouse management with EWM, shipping, transportation","module":"EWM","status":"Active"},
  {"name":"Warehouse to Ship (W2S)","code":"S-W2S","description":"EWM inbound/outbound processes, wave management, packing","module":"EWM","status":"Active"},
  {"name":"Quality Management (QM)","code":"S-QM","description":"Quality planning, inspection, notifications, certificates","module":"QM","status":"Active"}
]'

# Her senaryo için POST (loop veya tek tek)
echo "$SCENARIOS" | python3 -c "
import sys, json, urllib.request
scenarios = json.load(sys.stdin)
for s in scenarios:
    s['project_id'] = PROJECT_ID  # ← Gerçek ID ile değiştir
    req = urllib.request.Request(
        'http://localhost:5000/api/v1/scenarios',
        data=json.dumps(s).encode(),
        headers={'Content-Type':'application/json'},
        method='POST'
    )
    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        print(f'  ✅ {s[\"code\"]} → ID: {result.get(\"id\",\"?\")}')
    except Exception as e:
        print(f'  ❌ {s[\"code\"]} → {e}')
"
```

**📝 TEST KONTROL:**
- [ ] 8 senaryo oluştu mu?
- [ ] Auto-code generation çalışıyor mu (S-001, S-002...)?
- [ ] `module` alanı var mı ve kabul ediliyor mu?
- [ ] Senaryo → Process (L1) bağlantısı kurulabiliyor mu?
- [ ] ❓ EKSİK Mİ: Composite scenario desteği (O2C+R2R = End-to-End)?
- [ ] ❓ EKSİK Mİ: Senaryo bazlı scope item mapping?
- [ ] ❓ EKSİK Mİ: Senaryo prioritization / complexity scoring?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 2: EXPLORE — Fit-GAP Workshop'ları
# ═══════════════════════════════════════════════════════════════

## SAP Activate Bağlamı
Explore fazı, SAP Best Practice süreçlerini müşteriye göstererek Fit/Gap analizi yapmaktır.
Her modül için 2-3 workshop planlanır. Workshop'larda requirement'lar çıkar.

---

### 2.1 — Workshop Oluşturma

```bash
# O2C Workshop 1 — Standard Sales
curl -s -X POST http://localhost:5000/api/v1/explore/workshops \
  -H "Content-Type: application/json" \
  -d '{
    "title": "O2C Workshop 1 — Standard Sales Order Processing",
    "scenario_id": O2C_SCENARIO_ID,
    "project_id": PROJECT_ID,
    "module": "SD",
    "status": "Planned",
    "scheduled_date": "2026-04-15",
    "facilitator": "Zeynep Arslan",
    "location": "ACME İstanbul HQ — Meeting Room A",
    "description": "Demonstrate SAP Best Practice for standard sales order processing. Cover: inquiry, quotation, sales order, delivery, billing. Include pricing, ATP, credit check, output management."
  }' | python3 -m json.tool

# O2C Workshop 2 — Returns & Credit
curl -s -X POST http://localhost:5000/api/v1/explore/workshops \
  -H "Content-Type: application/json" \
  -d '{
    "title": "O2C Workshop 2 — Returns, Credit/Debit Memo, Consignment",
    "scenario_id": O2C_SCENARIO_ID,
    "project_id": PROJECT_ID,
    "module": "SD",
    "status": "Planned",
    "scheduled_date": "2026-04-17",
    "facilitator": "Zeynep Arslan",
    "location": "ACME İstanbul HQ — Meeting Room A"
  }'

# P2P Workshop 1 — Standard Procurement
curl -s -X POST http://localhost:5000/api/v1/explore/workshops \
  -H "Content-Type: application/json" \
  -d '{
    "title": "P2P Workshop 1 — Standard Procurement & Subcontracting",
    "scenario_id": P2P_SCENARIO_ID,
    "project_id": PROJECT_ID,
    "module": "MM",
    "status": "Planned",
    "scheduled_date": "2026-04-22",
    "facilitator": "Ali Demir"
  }'

# P2P Workshop 2 — Service & Import
curl -s -X POST http://localhost:5000/api/v1/explore/workshops \
  -H "Content-Type: application/json" \
  -d '{
    "title": "P2P Workshop 2 — Service Procurement & Import Process",
    "scenario_id": P2P_SCENARIO_ID,
    "project_id": PROJECT_ID,
    "module": "MM",
    "status": "Planned",
    "scheduled_date": "2026-04-24",
    "facilitator": "Ali Demir"
  }'

# R2R Workshop 1 — General Ledger & Closing
curl -s -X POST http://localhost:5000/api/v1/explore/workshops \
  -H "Content-Type: application/json" \
  -d '{
    "title": "R2R Workshop 1 — General Ledger, AP/AR, Period-End Closing",
    "scenario_id": R2R_SCENARIO_ID,
    "project_id": PROJECT_ID,
    "module": "FI/CO",
    "status": "Planned",
    "scheduled_date": "2026-04-29",
    "facilitator": "Can Öztürk"
  }'

# M2S Workshop 1 — Production Planning & Execution
curl -s -X POST http://localhost:5000/api/v1/explore/workshops \
  -H "Content-Type: application/json" \
  -d '{
    "title": "M2S Workshop 1 — Production Planning, MRP, Shop Floor Execution",
    "scenario_id": M2S_SCENARIO_ID,
    "project_id": PROJECT_ID,
    "module": "PP",
    "status": "Planned",
    "scheduled_date": "2026-05-06",
    "facilitator": "Ayşe Kaya"
  }'
```

**📝 TEST KONTROL:**
- [ ] Workshop'lar oluştu mu?
- [ ] Workshop → Scenario bağlantısı var mı?
- [ ] Workshop → Process (L3) bağlantısı kurulabiliyor mu?
- [ ] `facilitator` team member'a mı bağlı yoksa free text mi?
- [ ] `location`, `scheduled_date` alanları kabul ediliyor mu?
- [ ] Workshop status geçişleri (Planned → In Progress → Completed) çalışıyor mu?
- [ ] ❓ EKSİK Mİ: Workshop agenda yönetimi?
- [ ] ❓ EKSİK Mİ: Workshop katılımcı listesi (attendees)?
- [ ] ❓ EKSİK Mİ: Workshop meeting minutes?
- [ ] ❓ EKSİK Mİ: Workshop'a doküman/ekran görüntüsü ekleme?

---

### 2.2 — Requirement Oluşturma (Fit-Gap Analizi)

O2C Workshop 1 sonuçları — gerçekçi SAP requirement'ları:

```bash
# ═══ FIT REQUIREMENTS (Standard SAP — konfigürasyon yeterli) ═══

# REQ-001: Standard Sales Order — FIT
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Standard Sales Order Creation (VA01)",
    "description": "ACME standard sales order process aligns with SAP Best Practice. Order types OR (standard) and SO (rush) sufficient. No custom order types needed.",
    "classification": "Fit",
    "module": "SD",
    "area": "Sales",
    "priority": "High",
    "status": "Approved",
    "workshop_id": WS1_ID,
    "project_id": PROJECT_ID,
    "process_step_id": SSO_L3_ID,
    "fit_type": "Standard"
  }' | python3 -m json.tool

# REQ-002: Pricing — FIT
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Standard Pricing Procedure with Discounts",
    "description": "SAP standard pricing procedure covers ACME needs: base price (PR00), customer discount (K007), material group discount (K029), cash discount. No custom condition types needed.",
    "classification": "Fit",
    "module": "SD",
    "area": "Pricing",
    "priority": "High",
    "status": "Approved",
    "workshop_id": WS1_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Standard"
  }'

# REQ-003: ATP Check — FIT
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Available-to-Promise (ATP) Check",
    "description": "Standard ATP check with TOR (product availability) sufficient. ACME uses simple ATP without CTP/MRP-based ATP.",
    "classification": "Fit",
    "module": "SD",
    "area": "Sales",
    "priority": "Medium",
    "status": "Approved",
    "workshop_id": WS1_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Standard"
  }'

# ═══ PARTIAL FIT REQUIREMENTS (SAP standard + minor config/enhancement) ═══

# REQ-004: Credit Check — PARTIAL FIT
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Automatic Credit Check with Custom Thresholds",
    "description": "SAP standard credit management covers 90% of need. However, ACME requires: (1) different credit limits by sales org (standard), (2) special approval workflow for orders exceeding 500K TRY — needs BRF+ rule enhancement, (3) credit block auto-release for VIP customers.",
    "classification": "Partial Fit",
    "module": "SD",
    "area": "Credit Management",
    "priority": "High",
    "status": "Approved",
    "workshop_id": WS1_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Enhancement"
  }'

# REQ-005: Output Management — PARTIAL FIT
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sales Order Confirmation & Delivery Note Output",
    "description": "SAP standard output types (BA00, LD00) cover basic need. ACME requires: (1) custom layout for order confirmation with company logo and bilingual (TR/EN), (2) delivery note with barcode for warehouse scanning, (3) email distribution via BTP Integration Suite.",
    "classification": "Partial Fit",
    "module": "SD",
    "area": "Output Management",
    "priority": "Medium",
    "status": "Approved",
    "workshop_id": WS1_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Enhancement"
  }'

# ═══ GAP REQUIREMENTS (Custom development needed) ═══

# REQ-006: Intercompany Sales — GAP
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Intercompany Sales with Transfer Pricing",
    "description": "ACME sells products manufactured in Bursa factory through Germany sales office. Requires automatic intercompany billing with: (1) transfer pricing based on cost-plus method, (2) automatic STO creation from sales order, (3) foreign currency handling EUR/TRY, (4) customs documentation for EU export. SAP standard intercompany exists but transfer pricing logic needs custom ABAP enhancement.",
    "classification": "Gap",
    "module": "SD",
    "area": "Intercompany",
    "priority": "Critical",
    "status": "Approved",
    "workshop_id": WS1_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Custom Development"
  }'

# REQ-007: Special Pricing Agreement — GAP
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Customer-Specific Pricing Agreement Portal",
    "description": "ACME has annual pricing agreements with 200+ OEM customers. Current process uses Excel. Need: (1) customer self-service portal for agreement negotiation, (2) automatic condition record creation from approved agreements, (3) agreement validity management with renewal reminders. Requires Fiori launchpad extension + custom CDS views.",
    "classification": "Gap",
    "module": "SD",
    "area": "Pricing",
    "priority": "High",
    "status": "In Review",
    "workshop_id": WS1_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Custom Development"
  }'

# REQ-008: e-Invoice Integration — GAP
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Turkish e-Invoice (e-Fatura) Integration",
    "description": "Legal requirement: all invoices must be sent as e-Fatura via GIB (Revenue Administration) portal. Need: (1) UBL-TR XML generation from billing document, (2) digital signature with qualified certificate, (3) real-time submission to GIB portal, (4) e-Archive for B2C invoices, (5) e-Dispatch note for shipments. Requires integration via middleware (Foriba/Logo/Uyumsoft).",
    "classification": "Gap",
    "module": "FI",
    "area": "Legal/Compliance",
    "priority": "Critical",
    "status": "Approved",
    "workshop_id": WS1_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Interface"
  }'

# ═══ P2P REQUIREMENTS (Procurement Workshop) ═══

# REQ-009: MRP-based Procurement — FIT
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MRP-Driven Purchase Requisition to Purchase Order",
    "description": "Standard MRP run (MD01/MD02) creates purchase requisitions, automatic conversion to PO via ME59N. ACME procurement process fits SAP standard.",
    "classification": "Fit",
    "module": "MM",
    "area": "Procurement",
    "priority": "High",
    "status": "Approved",
    "workshop_id": WS3_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Standard"
  }'

# REQ-010: Vendor Evaluation — PARTIAL FIT
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Vendor Evaluation with Custom Criteria",
    "description": "SAP standard vendor evaluation covers quality, price, delivery. ACME additionally needs: (1) sustainability scoring, (2) ISO certification tracking, (3) automatic block for vendors below threshold. Standard criteria + 2 custom subcriteria needed.",
    "classification": "Partial Fit",
    "module": "MM",
    "area": "Vendor Management",
    "priority": "Medium",
    "status": "Approved",
    "workshop_id": WS3_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Enhancement"
  }'

# REQ-011: Subcontracting — PARTIAL FIT
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Subcontracting with Component Tracking",
    "description": "SAP standard subcontracting (ME21N item cat L) covers base process. ACME needs enhanced component tracking: (1) real-time stock visibility at subcontractor, (2) quality inspection at receipt, (3) cost allocation per component. Minor enhancement needed for tracking report.",
    "classification": "Partial Fit",
    "module": "MM",
    "area": "Procurement",
    "priority": "High",
    "status": "Approved",
    "workshop_id": WS3_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Enhancement"
  }'

# REQ-012: Goods Receipt with Barcode — GAP
curl -s -X POST http://localhost:5000/api/v1/explore/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Mobile Goods Receipt with Barcode/QR Scanning",
    "description": "ACME warehouse requires mobile GR process: (1) scan PO barcode on delivery, (2) automatic MIGO posting via Fiori app, (3) label printing for internal barcode, (4) integration with EWM inbound delivery. Requires custom Fiori app + RF scanner integration.",
    "classification": "Gap",
    "module": "MM/EWM",
    "area": "Warehouse",
    "priority": "High",
    "status": "Approved",
    "workshop_id": WS3_ID,
    "project_id": PROJECT_ID,
    "fit_type": "Custom Development"
  }'
```

**📝 TEST KONTROL (EN KRİTİK BÖLÜM):**
- [ ] Tüm requirement'lar oluştu mu? Auto-code (REQ-001...) çalışıyor mu?
- [ ] Classification (Fit/Partial Fit/Gap) doğru kaydediliyor mu?
- [ ] Workshop bağlantısı (workshop_id FK) çalışıyor mu?
- [ ] Process step bağlantısı (L3 FK) çalışıyor mu?
- [ ] Filtreleme: GET /api/v1/explore/requirements?classification=Gap çalışıyor mu?
- [ ] Filtreleme: GET /api/v1/explore/requirements?module=SD çalışıyor mu?
- [ ] Filtreleme: GET /api/v1/explore/requirements?workshop_id=X çalışıyor mu?
- [ ] Priority field kabul ediliyor mu (Critical/High/Medium/Low)?
- [ ] Status geçişleri çalışıyor mu?
- [ ] `area` field kabul ediliyor mu?
- [ ] `fit_type` field kabul ediliyor mu?
- [ ] Requirement listesi sayfasında classification badge renkleri doğru mu?
- [ ] ❓ EKSİK Mİ: Requirement → Process mapping (M:N ilişki)?
- [ ] ❓ EKSİK Mİ: Requirement approval workflow?
- [ ] ❓ EKSİK Mİ: Requirement impact analysis (hangi süreçleri etkiler)?
- [ ] ❓ EKSİK Mİ: Requirement dependency yönetimi (REQ-006 depends on REQ-008)?
- [ ] ❓ EKSİK Mİ: Requirement effort estimation?

---

### 2.3 — Open Items Oluşturma

Workshop'lardan çıkan açık konular:

```bash
# OI-001: Data Migration Strategy
curl -s -X POST http://localhost:5000/api/v1/explore/open-items \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Master Data Migration Strategy Decision",
    "description": "Need to decide: (1) Customer master data migration approach — full history or active only? (2) Material master data — migrate all 45K materials or only active 12K? (3) Open sales orders/POs — migrate or re-create? Decision needed by end of Explore phase.",
    "status": "Open",
    "priority": "Critical",
    "assigned_to": "Mehmet Yılmaz",
    "due_date": "2026-05-15",
    "category": "Data Migration",
    "project_id": PROJECT_ID,
    "workshop_id": WS1_ID
  }' | python3 -m json.tool

# OI-002: Integration Architecture
curl -s -X POST http://localhost:5000/api/v1/explore/open-items \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Integration Architecture — BTP vs Middleware",
    "description": "ACME has 12 interfaces with external systems. Decision needed: use SAP BTP Integration Suite or keep existing middleware (MuleSoft)? Cost-benefit analysis required. Impacts e-Invoice, EDI, bank integration, MES interface.",
    "status": "Open",
    "priority": "High",
    "assigned_to": "Emre Çelik",
    "due_date": "2026-05-01",
    "category": "Technical Architecture",
    "project_id": PROJECT_ID
  }'

# OI-003: Organizational Structure
curl -s -X POST http://localhost:5000/api/v1/explore/open-items \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Organizational Structure — Sales Org & Distribution Channel",
    "description": "Current ECC has 3 sales orgs (domestic, export, intercompany). S/4 recommendation: simplify to 2 sales orgs with distribution channel differentiation. Customer needs to confirm if product division restructuring also needed.",
    "status": "Open",
    "priority": "High",
    "assigned_to": "Selin Yıldız",
    "due_date": "2026-04-30",
    "category": "Org Structure",
    "project_id": PROJECT_ID
  }'

# OI-004: Cutover Window
curl -s -X POST http://localhost:5000/api/v1/explore/open-items \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Go-Live Cutover Window Confirmation",
    "description": "Proposed go-live: December 2026 year-end. ACME management needs to confirm: (1) factory shutdown window for cutover (minimum 3 days), (2) parallel run duration, (3) fallback strategy. Finance team prefers January 2027 for clean fiscal year start.",
    "status": "Open",
    "priority": "Critical",
    "assigned_to": "Hakan Aydın",
    "due_date": "2026-05-30",
    "category": "Cutover",
    "project_id": PROJECT_ID
  }'
```

**📝 TEST KONTROL:**
- [ ] Open item'lar oluştu mu?
- [ ] Open Item → Requirement bağlantısı (M:N) kurulabiliyor mu?
- [ ] Open Item → Workshop bağlantısı var mı?
- [ ] Status geçişleri: Open → In Progress → Resolved → Closed?
- [ ] `assigned_to` team member'a FK mı yoksa free text mi?
- [ ] `due_date` ile overdue takibi var mı?
- [ ] `category` alanı var mı?
- [ ] ❓ EKSİK Mİ: Open item aging raporu?
- [ ] ❓ EKSİK Mİ: Open item → Decision dönüşümü?
- [ ] ❓ EKSİK Mİ: Escalation mekanizması (overdue items)?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 3: REALIZE — Build, Configure & Develop
# ═══════════════════════════════════════════════════════════════

## SAP Activate Bağlamı
Realize fazında Fit requirement'lar konfigüre edilir, Gap requirement'lar develop edilir,
FS/TS dokümanları yazılır, unit test'ler yapılır.

---

### 3.1 — Requirement → Config Item Dönüşümü (Fit Requirements)

```bash
# REQ-001 (Standard Sales Order) → Config Item
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_001_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "config"}' | python3 -m json.tool

# REQ-002 (Pricing) → Config Item  
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_002_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "config"}'

# REQ-003 (ATP) → Config Item
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_003_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "config"}'

# REQ-009 (MRP Procurement) → Config Item
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_009_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "config"}'
```

**📝 TEST KONTROL:**
- [ ] Convert endpoint var mı ve çalışıyor mu?
- [ ] Convert URL pattern'i ne? (/convert, /convert-to-config, vs.)
- [ ] Config Item otomatik oluşuyor mu? Requirement field'ları taşınıyor mu?
- [ ] Requirement'ta conversion_status güncelleniyor mu?
- [ ] Aynı requirement ikinci kez convert edilebiliyor mu? (Olmamalı)
- [ ] Config Item'da requirement_id FK bağlantısı var mı?
- [ ] ❓ EKSİK Mİ: Bulk convert (birden fazla requirement'ı toplu convert)?
- [ ] ❓ EKSİK Mİ: Convert geri alma (unconvert)?

---

### 3.2 — Requirement → Backlog/WRICEF Item Dönüşümü (Gap Requirements)

```bash
# REQ-004 (Credit Check) → Enhancement (E)
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_004_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "backlog", "wricef_type": "E"}'

# REQ-005 (Output Management) → Form (F)
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_005_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "backlog", "wricef_type": "F"}'

# REQ-006 (Intercompany) → Enhancement (E)
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_006_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "backlog", "wricef_type": "E"}'

# REQ-007 (Pricing Portal) → Report + Enhancement
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_007_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "backlog", "wricef_type": "E"}'

# REQ-008 (e-Invoice) → Interface (I)
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_008_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "backlog", "wricef_type": "I"}'

# REQ-010 (Vendor Eval) → Enhancement (E)
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_010_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "backlog", "wricef_type": "E"}'

# REQ-011 (Subcontracting) → Report (R)
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_011_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "backlog", "wricef_type": "R"}'

# REQ-012 (Mobile GR) → Enhancement + Workflow
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/REQ_012_ID/convert \
  -H "Content-Type: application/json" \
  -d '{"target_type": "backlog", "wricef_type": "W"}'
```

**📝 TEST KONTROL:**
- [ ] WRICEF type (W/R/I/C/E/F) doğru atanıyor mu?
- [ ] Backlog item'larda requirement bağlantısı var mı?
- [ ] Backlog listesinde WRICEF type badge'leri doğru mu?
- [ ] ❓ EKSİK Mİ: Bir requirement'tan birden fazla backlog item oluşturma?
- [ ] ❓ EKSİK Mİ: Backlog item effort estimation (story points, man-days)?
- [ ] ❓ EKSİK Mİ: Development sprint assignment?
- [ ] ❓ EKSİK Mİ: Developer assignment (assigned_to)?

---

### 3.3 — Functional Spec & Technical Spec Yazma

```bash
# e-Invoice Interface (REQ-008 → Backlog Item) için FS
curl -s -X POST http://localhost:5000/api/v1/backlog/EINVOICE_BACKLOG_ID/functional-spec \
  -H "Content-Type: application/json" \
  -d '{
    "title": "FS — Turkish e-Invoice Integration",
    "content": "## 1. Overview\nIntegration between SAP S/4HANA billing documents and Turkish Revenue Administration (GIB) e-Invoice system.\n\n## 2. Scope\n- e-Fatura (B2B)\n- e-Arşiv (B2C)\n- e-İrsaliye (Dispatch Note)\n\n## 3. Business Process\n1. Billing document created in S/4 (VF01/VF04)\n2. Output determination triggers e-Invoice\n3. UBL-TR XML generated\n4. XML signed with qualified certificate\n5. Submitted to GIB via middleware\n6. Response (accept/reject) posted back to S/4\n\n## 4. Technical Requirements\n- Middleware: Foriba Connect\n- Protocol: REST API\n- Format: UBL-TR 1.2\n- Certificate: Qualified e-Signature",
    "status": "Draft",
    "version": "1.0",
    "author": "Can Öztürk"
  }' | python3 -m json.tool

# Same backlog item → Technical Spec
curl -s -X POST http://localhost:5000/api/v1/backlog/EINVOICE_BACKLOG_ID/technical-spec \
  -H "Content-Type: application/json" \
  -d '{
    "title": "TS — Turkish e-Invoice Integration",
    "content": "## 1. Architecture\nCustom ABAP class ZCL_EINVOICE_HANDLER implements IF_BADI_SD_BILLING_OUTPUT.\n\n## 2. Custom Objects\n- ZCL_EINVOICE_HANDLER (ABAP Class)\n- ZCL_UBL_TR_GENERATOR (XML Builder)\n- ZTABLE_EINV_LOG (Custom Table)\n- ZTABLE_EINV_CERT (Certificate Store)\n\n## 3. Integration\n- RFC destination to middleware\n- REST API consumer class\n- Async processing with bgRFC\n\n## 4. Error Handling\n- Retry mechanism (3 attempts)\n- Error log with ALV display\n- Email notification on failure",
    "status": "Draft",
    "version": "1.0",
    "author": "Burak Şahin"
  }'
```

**📝 TEST KONTROL:**
- [ ] FS/TS endpoint'leri var mı? URL pattern'i ne?
- [ ] FS → Backlog Item bağlantısı çalışıyor mu?
- [ ] FS/TS content Markdown destekliyor mu?
- [ ] Version management var mı?
- [ ] FS/TS approval workflow var mı?
- [ ] ❓ EKSİK Mİ: FS/TS template sistemi?
- [ ] ❓ EKSİK Mİ: FS/TS review/approval status?
- [ ] ❓ EKSİK Mİ: FS dokümanından PDF export?
- [ ] ❓ EKSİK Mİ: FS → TS bağlantısı (traceability)?

---

### 3.4 — Interface Tanımlama

```bash
# INT-001: e-Invoice (Outbound)
curl -s -X POST http://localhost:5000/api/v1/interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "name": "e-Invoice Integration (GIB)",
    "code": "INT-001",
    "direction": "Outbound",
    "source_system": "SAP S/4HANA",
    "target_system": "Foriba Connect → GIB Portal",
    "protocol": "REST API",
    "format": "UBL-TR XML",
    "frequency": "Real-time",
    "status": "Design",
    "backlog_item_id": EINVOICE_BACKLOG_ID,
    "project_id": PROJECT_ID
  }' | python3 -m json.tool

# INT-002: Bank Statement (Inbound)
curl -s -X POST http://localhost:5000/api/v1/interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bank Statement Import (MT940/CAMT.053)",
    "code": "INT-002",
    "direction": "Inbound",
    "source_system": "İş Bankası / Garanti BBVA",
    "target_system": "SAP S/4HANA FI",
    "protocol": "SFTP",
    "format": "MT940 / CAMT.053",
    "frequency": "Daily (06:00)",
    "status": "Design",
    "project_id": PROJECT_ID
  }'

# INT-003: EDI with OEM Customers (Bidirectional)
curl -s -X POST http://localhost:5000/api/v1/interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "name": "EDI Integration with OEM Customers",
    "code": "INT-003",
    "direction": "Bidirectional",
    "source_system": "SAP S/4HANA SD",
    "target_system": "Customer EDI Platforms (via Ediges)",
    "protocol": "AS2/SFTP",
    "format": "EDIFACT D96A",
    "frequency": "Real-time",
    "description": "Handles ORDERS, ORDRSP, DESADV, INVOIC message types",
    "status": "Design",
    "project_id": PROJECT_ID
  }'

# INT-004: MES Integration (Bidirectional)
curl -s -X POST http://localhost:5000/api/v1/interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Manufacturing Execution System (MES) Integration",
    "code": "INT-004",
    "direction": "Bidirectional",
    "source_system": "SAP S/4HANA PP",
    "target_system": "Siemens SIMATIC IT MES",
    "protocol": "OPC-UA / REST",
    "format": "JSON",
    "frequency": "Real-time",
    "description": "Production order download, confirmation upload, quality data exchange",
    "status": "Design",
    "project_id": PROJECT_ID
  }'
```

**📝 TEST KONTROL:**
- [ ] Interface entity var mı?
- [ ] Interface → Backlog Item bağlantısı çalışıyor mu?
- [ ] Direction (Inbound/Outbound/Bidirectional) alanı var mı?
- [ ] ❓ EKSİK Mİ: Connectivity Test entity (interface test kayıtları)?
- [ ] ❓ EKSİK Mİ: Interface flow diyagramı?
- [ ] ❓ EKSİK Mİ: Interface SLA tanımlama?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 4: TEST — Unit Test, SIT, UAT
# ═══════════════════════════════════════════════════════════════

## SAP Activate Bağlamı
Test fazı 4 aşamadan oluşur: Unit Test → SIT (System Integration Test) → 
UAT (User Acceptance Test) → Regression Test. Her aşama için test cycle'lar oluşturulur.

---

### 4.1 — Test Suite / Test Case Oluşturma

```bash
# ══ UNIT TEST: Standard Sales Order Config ══
curl -s -X POST http://localhost:5000/api/v1/testing/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UT — Standard Sales Order Creation & Delivery",
    "description": "Verify standard sales order (OR) creation with reference to quotation, ATP check, delivery creation, PGI, and billing.",
    "test_type": "Unit",
    "module": "SD",
    "priority": "High",
    "status": "Draft",
    "source_type": "config_item",
    "source_id": CONFIG_SALES_ORDER_ID,
    "project_id": PROJECT_ID,
    "steps": "1. Create quotation (VA21) for customer 100001, material MAT-001, qty 100 EA\n2. Create sales order (VA01) with reference to quotation\n3. Verify pricing: PR00 = 150 TRY, K007 = -5%\n4. Run ATP check — confirm availability date\n5. Create delivery (VL01N)\n6. Post goods issue (VL02N)\n7. Create billing document (VF01)\n8. Verify accounting document created in FI",
    "expected_result": "All documents created successfully. Pricing correct. ATP date reasonable. Accounting entries balanced.",
    "assigned_to": "Zeynep Arslan"
  }' | python3 -m json.tool

# ══ UNIT TEST: e-Invoice Interface ══
curl -s -X POST http://localhost:5000/api/v1/testing/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UT — e-Invoice XML Generation & Submission",
    "description": "Verify UBL-TR XML generation from billing document, digital signature, and submission to GIB test environment.",
    "test_type": "Unit",
    "module": "FI",
    "priority": "Critical",
    "status": "Draft",
    "source_type": "backlog_item",
    "source_id": EINVOICE_BACKLOG_ID,
    "project_id": PROJECT_ID,
    "steps": "1. Create billing document for e-Invoice registered customer\n2. Trigger output determination\n3. Verify UBL-TR XML generated correctly\n4. Check mandatory fields (VKN, invoice lines, tax amounts)\n5. Verify digital signature applied\n6. Submit to GIB test portal\n7. Check response status (accepted/rejected)\n8. Verify log entry in ZTABLE_EINV_LOG",
    "expected_result": "XML generated in UBL-TR 1.2 format. Digital signature valid. GIB test portal accepts invoice. Log entry created."
  }'

# ══ SIT TEST: Order to Cash End-to-End ══
curl -s -X POST http://localhost:5000/api/v1/testing/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "SIT — Order to Cash Full Cycle",
    "description": "End-to-end integration test: quotation → order → delivery → billing → e-invoice → payment → clearing",
    "test_type": "SIT",
    "module": "SD/FI",
    "priority": "Critical",
    "status": "Draft",
    "project_id": PROJECT_ID,
    "steps": "1. Create customer inquiry\n2. Create quotation with pricing\n3. Create sales order (reference quotation)\n4. Credit check passes\n5. Create outbound delivery\n6. Pick, pack in EWM\n7. Post goods issue\n8. Create billing document\n9. e-Invoice generated and sent\n10. Customer payment received (F-28)\n11. Automatic clearing\n12. Check all FI postings balanced",
    "expected_result": "Complete O2C cycle without manual intervention. All integration points working. FI documents balanced."
  }'

# ══ UAT TEST: Business Scenario Validation ══
curl -s -X POST http://localhost:5000/api/v1/testing/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UAT — Export Sales to Germany with Intercompany",
    "description": "Business user validates export sales scenario: Turkish entity sells to German customer via German sales office. Intercompany billing between TR and DE company codes.",
    "test_type": "UAT",
    "module": "SD/FI",
    "priority": "Critical",
    "status": "Draft",
    "project_id": PROJECT_ID,
    "steps": "1. German customer places order (EUR pricing)\n2. Order created in DE sales org\n3. Intercompany STO triggered automatically\n4. Delivery from TR plant to customer\n5. Intercompany billing (TR → DE)\n6. Customer billing (DE → Customer)\n7. Transfer pricing check (cost-plus margin)\n8. Customs documentation generated\n9. EUR/TRY currency translation verified\n10. Business user confirms process matches business requirements",
    "expected_result": "Export process runs end-to-end. Transfer pricing correct. Currency handling accurate. Customs docs generated."
  }'
```

**📝 TEST KONTROL:**
- [ ] Test case oluştu mu? Auto-code var mı (TC-001)?
- [ ] test_type (Unit/SIT/UAT/Regression) doğru kaydediliyor mu?
- [ ] source_type + source_id (config/backlog bağlantısı) çalışıyor mu?
- [ ] steps ve expected_result alanları kabul ediliyor mu?
- [ ] assigned_to alanı var mı?
- [ ] Test case → Requirement traceability var mı?
- [ ] ❓ EKSİK Mİ: Test case prerequisite / test data section?
- [ ] ❓ EKSİK Mİ: Test case parameterization (veri setleri)?
- [ ] ❓ EKSİK Mİ: Test case clone/copy fonksiyonu?

---

### 4.2 — Test Cycle Oluşturma & Execution

```bash
# ══ TEST CYCLE: SIT Round 1 ══
curl -s -X POST http://localhost:5000/api/v1/testing/test-suites \
  -H "Content-Type: application/json" \
  -d '{
    "title": "SIT Round 1 — System Integration Testing",
    "description": "First round of integration testing covering all end-to-end scenarios",
    "status": "Planned",
    "start_date": "2026-09-01",
    "end_date": "2026-09-15",
    "test_type": "SIT",
    "project_id": PROJECT_ID
  }' | python3 -m json.tool

# ══ TEST EXECUTION ══
# Test case execution kaydı
curl -s -X POST http://localhost:5000/api/v1/testing/test-executions \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": TC_SALES_ORDER_ID,
    "test_suite_id": SIT_R1_ID,
    "status": "Pass",
    "executed_by": "Zeynep Arslan",
    "executed_date": "2026-09-03",
    "actual_result": "Sales order created successfully. Pricing correct. ATP date 2026-09-05. Delivery and billing created without errors.",
    "duration_minutes": 45,
    "environment": "QAS-100",
    "project_id": PROJECT_ID
  }' | python3 -m json.tool

# Failed execution → creates defect
curl -s -X POST http://localhost:5000/api/v1/testing/test-executions \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": TC_EINVOICE_ID,
    "test_suite_id": SIT_R1_ID,
    "status": "Fail",
    "executed_by": "Can Öztürk",
    "executed_date": "2026-09-05",
    "actual_result": "XML generation successful but digital signature fails with error: CERT_EXPIRED. Test certificate has expired. Need to renew test certificate from test GIB portal.",
    "duration_minutes": 60,
    "environment": "QAS-100",
    "project_id": PROJECT_ID
  }'
```

**📝 TEST KONTROL:**
- [ ] Test suite/cycle oluştu mu?
- [ ] Test execution kaydı oluştu mu?
- [ ] Execution → Test Case bağlantısı çalışıyor mu?
- [ ] Execution → Test Suite bağlantısı çalışıyor mu?
- [ ] Status (Pass/Fail/Blocked/Not Run) doğru çalışıyor mu?
- [ ] Test suite istatistikleri otomatik hesaplanıyor mu (pass rate)?
- [ ] ❓ EKSİK Mİ: Fail → Defect otomatik bağlantısı?
- [ ] ❓ EKSİK Mİ: Test execution screenshot/attachment?
- [ ] ❓ EKSİK Mİ: Retest/rerun tracking?
- [ ] ❓ EKSİK Mİ: Test cycle progress dashboard (bar chart)?

---

### 4.3 — Defect Yönetimi

```bash
# DEF-001: e-Invoice Certificate Error
curl -s -X POST http://localhost:5000/api/v1/testing/defects \
  -H "Content-Type: application/json" \
  -d '{
    "title": "e-Invoice digital signature fails — expired test certificate",
    "description": "During SIT Round 1, e-Invoice unit test fails at step 5 (digital signature). Error: CERT_EXPIRED. Root cause: test certificate from GIB test portal expired on 2026-08-31. Need to renew test certificate and update STRUST.",
    "severity": "High",
    "priority": "High",
    "status": "Open",
    "module": "FI",
    "assigned_to": "Emre Çelik",
    "test_case_id": TC_EINVOICE_ID,
    "test_execution_id": EXEC_EINVOICE_ID,
    "backlog_item_id": EINVOICE_BACKLOG_ID,
    "environment": "QAS-100",
    "steps_to_reproduce": "1. Create billing document\n2. Trigger e-Invoice output\n3. Check ZTABLE_EINV_LOG → error CERT_EXPIRED",
    "project_id": PROJECT_ID
  }' | python3 -m json.tool

# DEF-002: Intercompany Pricing Error
curl -s -X POST http://localhost:5000/api/v1/testing/defects \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Intercompany billing uses wrong transfer price",
    "description": "Intercompany billing document between TR (1000) and DE (2000) company codes shows wrong transfer price. Expected: cost + 5% margin. Actual: using sales price instead of cost-plus. Pricing procedure ZVKIC needs correction in IV01 condition.",
    "severity": "Critical",
    "priority": "Critical",
    "status": "Open",
    "module": "SD",
    "assigned_to": "Zeynep Arslan",
    "test_case_id": TC_UAT_EXPORT_ID,
    "environment": "QAS-100",
    "project_id": PROJECT_ID
  }'

# DEF-003: Performance Issue
curl -s -X POST http://localhost:5000/api/v1/testing/defects \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MRP run takes 4+ hours for full planning run",
    "description": "Full MRP run (MD01 for all plants) takes 4+ hours. Target: under 2 hours. Possible causes: (1) too many MRP areas, (2) missing secondary indexes on MDKP/MDTB, (3) BOM explosion depth, (4) need to evaluate parallel MRP (MRP Live).",
    "severity": "High",
    "priority": "Medium",
    "status": "Open",
    "module": "PP",
    "assigned_to": "Emre Çelik",
    "environment": "QAS-100",
    "category": "Performance",
    "project_id": PROJECT_ID
  }'
```

**📝 TEST KONTROL:**
- [ ] Defect oluştu mu? Auto-code (DEF-001)?
- [ ] Severity vs Priority ayrımı destekleniyor mu?
- [ ] Defect → Test Case bağlantısı var mı?
- [ ] Defect → Test Execution bağlantısı var mı?
- [ ] Defect → Backlog Item bağlantısı var mı?
- [ ] Defect lifecycle: Open → In Progress → Fixed → Verified → Closed?
- [ ] ❓ EKSİK Mİ: Defect reopen count?
- [ ] ❓ EKSİK Mİ: Defect aging raporu?
- [ ] ❓ EKSİK Mİ: Defect → Root cause analysis field?
- [ ] ❓ EKSİK Mİ: Defect fix version / transport number?
- [ ] ❓ EKSİK Mİ: Defect SLA (Critical=24h, High=48h, Medium=5d)?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 5: DEPLOY — Cutover & Go-Live
# ═══════════════════════════════════════════════════════════════

## SAP Activate Bağlamı
Deploy fazı: cutover plan, data migration, transport management, go-live checklist,
hypercare planı. Bu fazda platformun cutover ve go-live desteği test edilir.

---

### 5.1 — Cutover Planı (Platform'da bu var mı?)

Bu bölüm platformda muhtemelen eksik olan alanı test eder:

```bash
# Cutover task'ları — Platformda endpoint var mı?
# Eğer yoksa, bu bir GAP olarak raporla

# Deneme: Cutover Task oluşturma
curl -s -X POST http://localhost:5000/api/v1/cutover-tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Freeze ECC system for final data migration",
    "sequence": 1,
    "category": "System",
    "responsible": "Emre Çelik",
    "planned_start": "2026-12-12T18:00:00",
    "planned_end": "2026-12-12T20:00:00",
    "duration_hours": 2,
    "predecessor_id": null,
    "status": "Planned",
    "notes": "Communicate freeze to all departments 48h before. Lock transactions via SM01.",
    "project_id": PROJECT_ID
  }'

# Eğer 404 dönerse → Cutover Management modülü YOK → Major GAP
```

**📝 Cutover Task Listesi (Eğer modül varsa test et, yoksa GAP olarak raporla):**

| # | Task | Category | Duration | Predecessor |
|---|------|----------|----------|-------------|
| 1 | ECC system freeze | System | 2h | — |
| 2 | Final master data extract | Data | 4h | 1 |
| 3 | Master data load to S/4 | Data | 8h | 2 |
| 4 | Open document migration (SO, PO) | Data | 6h | 3 |
| 5 | Financial balance migration | Data | 4h | 3 |
| 6 | Data reconciliation & validation | QA | 4h | 4,5 |
| 7 | Transport import to PRD | System | 2h | 6 |
| 8 | System integration smoke test | QA | 3h | 7 |
| 9 | e-Invoice production certificate | System | 1h | 7 |
| 10 | Interface activation | System | 2h | 7 |
| 11 | User provisioning (850 users) | Security | 4h | 7 |
| 12 | Fiori launchpad validation | QA | 2h | 11 |
| 13 | Management go/no-go decision | Milestone | 1h | 8,12 |
| 14 | Go-Live announcement | Communication | 0.5h | 13 |
| 15 | Production transaction opening | System | 0.5h | 14 |
| 16 | Day 1 monitoring & support | Hypercare | 12h | 15 |

**📝 TEST KONTROL (CUTOVER):**
- [ ] ❓ Cutover management modülü VAR MI?
- [ ] ❓ Cutover task CRUD (oluşturma, sıralama, bağımlılık)?
- [ ] ❓ Gantt chart veya timeline görselleştirmesi?
- [ ] ❓ Cutover rehearsal tracking (mock cutover)?
- [ ] ❓ Go/No-Go checklist?
- [ ] ❓ Cutover task status tracking (real-time)?

---

### 5.2 — Data Migration Tracking (Platform'da bu var mı?)

```bash
# Data migration object tracking
curl -s -X POST http://localhost:5000/api/v1/data-migration \
  -H "Content-Type: application/json" \
  -d '{
    "object_name": "Customer Master (KNA1/KNVV/KNVP)",
    "source_system": "ECC 6.0",
    "record_count_source": 15000,
    "record_count_target": null,
    "migration_tool": "SAP S/4HANA Migration Cockpit",
    "status": "Mapping",
    "responsible": "Ali Demir",
    "project_id": PROJECT_ID
  }'
# Eğer 404 → Data Migration module YOK → GAP
```

**📝 TEST KONTROL (DATA MIGRATION):**
- [ ] ❓ Data migration tracking modülü VAR MI?
- [ ] ❓ Migration object CRUD?
- [ ] ❓ Source → Target record count reconciliation?
- [ ] ❓ Migration run tracking (trial, dress rehearsal, final)?
- [ ] ❓ Data quality issue logging?

---

### 5.3 — Transport Management (Platform'da bu var mı?)

```bash
# ABAP transport tracking
curl -s -X POST http://localhost:5000/api/v1/transports \
  -H "Content-Type: application/json" \
  -d '{
    "transport_number": "DEVK900123",
    "description": "e-Invoice ABAP objects — ZCL_EINVOICE_HANDLER",
    "type": "Workbench",
    "owner": "Burak Şahin",
    "source_system": "DEV-100",
    "target_system": "QAS-100",
    "status": "Released",
    "backlog_item_id": EINVOICE_BACKLOG_ID,
    "project_id": PROJECT_ID
  }'
# Eğer 404 → Transport Management YOK → nice-to-have GAP
```

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 6: TRACEABILITY & CROSS-CUTTING CONCERNS
# ═══════════════════════════════════════════════════════════════

## Amaç
End-to-end traceability'nin çalışıp çalışmadığını doğrula.

---

### 6.1 — Full Chain Traceability Test

```bash
# REQ-008 (e-Invoice) için tam zincir:
# Scenario → Process → Workshop → Requirement → Backlog Item → FS/TS → Interface → Test Case → Execution → Defect

# Traceability endpoint test
curl -s http://localhost:5000/api/v1/traceability/explore_requirement/REQ_008_ID | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('═══ TRACEABILITY CHAIN ═══')
print(f'Chain Depth: {data.get(\"chain_depth\", \"?\")}/6')
print(f'Upstream: {len(data.get(\"upstream\", []))} entities')
for u in data.get('upstream', []):
    print(f'  ↑ {u.get(\"type\")}: {u.get(\"title\",\"\")}')
print(f'Downstream: {len(data.get(\"downstream\", []))} entities')  
for d in data.get('downstream', []):
    print(f'  ↓ {d.get(\"type\")}: {d.get(\"title\",\"\")}')
print(f'Lateral: {json.dumps(data.get(\"lateral\", {}), indent=2)}')
print(f'Gaps: {json.dumps(data.get(\"gaps\", []), indent=2)}')
"
```

**📝 TEST KONTROL (TRACEABILITY):**
- [ ] Traceability endpoint çalışıyor mu?
- [ ] Full chain depth 6/6 ulaşılabiliyor mu?
- [ ] Upstream (Scenario → Process → Workshop) görünüyor mu?
- [ ] Downstream (Backlog → FS/TS → Test → Defect) görünüyor mu?
- [ ] Lateral links (Open Items, Decisions) görünüyor mu?
- [ ] Gaps tespit ediliyor mu?
- [ ] Frontend'de traceability modal/tab çalışıyor mu?
- [ ] ❓ EKSİK Mİ: Traceability matrix export (Excel)?
- [ ] ❓ EKSİK Mİ: Coverage raporu (hangi requirement'ların testi yok)?
- [ ] ❓ EKSİK Mİ: Impact analysis (bir requirement değişirse neler etkilenir)?

---

### 6.2 — Dashboard & Reporting

```bash
# Dashboard stats
curl -s http://localhost:5000/api/v1/dashboard/stats?project_id=PROJECT_ID | python3 -m json.tool
```

**📝 TEST KONTROL (DASHBOARD):**
- [ ] Dashboard'da toplam proje sayısı doğru mu?
- [ ] Requirement breakdown (Fit/Partial Fit/Gap) grafik var mı?
- [ ] Test execution pass/fail rate var mı?
- [ ] Defect trend (open/closed by week) var mı?
- [ ] Open items count ve aging var mı?
- [ ] ❓ EKSİK Mİ: Project-level KPI dashboard?
- [ ] ❓ EKSİK Mİ: Steering committee raporu (PDF export)?
- [ ] ❓ EKSİK Mİ: Sprint/Wave progress tracking?
- [ ] ❓ EKSİK Mİ: Risk heatmap?
- [ ] ❓ EKSİK Mİ: Resource utilization chart?

---

### 6.3 — Search & Filter

Tüm entity'ler için:
```bash
# Requirement arama
curl -s "http://localhost:5000/api/v1/explore/requirements?search=invoice&project_id=PROJECT_ID"

# Backlog filtreleme
curl -s "http://localhost:5000/api/v1/backlog?wricef_type=I&status=Design&project_id=PROJECT_ID"

# Defect filtreleme
curl -s "http://localhost:5000/api/v1/testing/defects?severity=Critical&status=Open&project_id=PROJECT_ID"
```

**📝 TEST KONTROL (SEARCH):**
- [ ] Full-text search çalışıyor mu?
- [ ] Multi-field filtreleme çalışıyor mu?
- [ ] Pagination var mı?
- [ ] Sort destekleniyor mu?
- [ ] ❓ EKSİK Mİ: Saved filters / views?
- [ ] ❓ EKSİK Mİ: Cross-entity search (tüm modüllerde arama)?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 7: SONUÇ RAPORU ŞABLONU
# ═══════════════════════════════════════════════════════════════

Tüm testler tamamlandıktan sonra aşağıdaki raporu doldur:

## 📊 TEST SONUÇ RAPORU

### A) Endpoint Durumu
| Endpoint Grubu | Toplam | Çalışan | Hatalı | Eksik |
|---------------|--------|---------|--------|-------|
| Projects | | | | |
| Scenarios | | | | |
| Processes (L1-L4) | | | | |
| Workshops | | | | |
| Requirements | | | | |
| Open Items | | | | |
| Backlog/WRICEF | | | | |
| Config Items | | | | |
| FS/TS | | | | |
| Interfaces | | | | |
| Test Cases | | | | |
| Test Suites | | | | |
| Test Executions | | | | |
| Defects | | | | |
| Team Members | | | | |
| Traceability | | | | |
| Convert | | | | |
| Dashboard | | | | |
| Cutover | | | | |
| Data Migration | | | | |
| Transports | | | | |

### B) SAP Activate Phase Coverage
| Faz | Kapsam | Eksikler |
|-----|--------|----------|
| Discover | | |
| Prepare | | |
| Explore | | |
| Realize | | |
| Deploy | | |
| Run | | |

### C) Kritik GAP'ler (Platformda Olmayan Modüller)
| # | Modül | Öncelik | SAP Activate Fazı | Açıklama |
|---|-------|---------|-------------------|----------|
| 1 | | | | |

### D) İyileştirme Önerileri
| # | Alan | Öneri | Effort | Öncelik |
|---|------|-------|--------|---------|
| 1 | | | | |

### E) Traceability Derinlik Skoru
| Zincir | Beklenen Depth | Gerçekleşen | Gap |
|--------|---------------|-------------|-----|
| Scenario → Test | 6/6 | | |
| Requirement → Defect | 5/6 | | |
| Backlog → Defect | 3/6 | | |

### F) Frontend Hata Listesi
| # | Sayfa | Hata | Severity | Console Error |
|---|-------|------|----------|---------------|
| 1 | | | | |

---

*SAP Activate E2E Test Plan v1.0 — Perga Platform — 2026-02-13*
