# 🧪 PERGA — Archived E2E Test Prompt

This file is an archived manual test prompt/reference. It is not part of the
automated Playwright or pytest suites.

# Full E2E Test Prompt: Data Reset → SAP Activate Lifecycle → UI & Traceability Validation

**Tarih:** 2026-03-02
**Amaç:** Tüm örnek datayı sıfırla → sıfırdan Program & Proje yarat → gerçek bir S/4HANA dönüşüm projesi gibi tüm entityleri mantıksal sırayla oluştur → her UI butonunu test et → traceability zincirini doğrula → tüm defect ve eksikleri raporla
**Hedef Ortam:** SAP Transformation Platform (Flask + PostgreSQL), `umutsoyyilmaz/SAP_Transformation_Platform`, `main` branch
**Platform:** GitHub Codespaces
**Server:** `http://localhost:5000` (veya aktif port)

---

## KRİTİK KURALLAR

1. ❌ ASLA toplu sed/replace kullanma
2. ❌ Mevcut çalışan kodu kırma — sadece TEST et, düzeltme yapma
3. ✅ Her adımda beklenen sonuç (Expected) ile gerçek sonucu (Actual) karşılaştır
4. ✅ Her hata/eksiklik için DEFECT-XXX kodu ile kayıt oluştur
5. ✅ Browser testlerinde F12 Console'u her zaman açık tut
6. ✅ Network tab'da 4xx/5xx hataları kaydet
7. ✅ Her BLOCK sonunda bulunan defectlerin özetini ver

---

## DEFECT KAYIT FORMATI

Her bulunan hata/eksiklik için şu formatı kullan:

```
DEFECT-XXX | Severity: P1/P2/P3 | Kategori: API/UI/DATA/TRACE/UX
Başlık: Kısa açıklama
Adım: Hangi test adımında bulundu
Beklenen: Ne olmalıydı
Gerçek: Ne oldu
Ekran/Endpoint: İlgili URL veya ekran adı
```

Severity tanımları:
- **P1 — Critical:** Fonksiyon tamamen çalışmıyor, veri kaybı, 500 hatası
- **P2 — Major:** Fonksiyon kısmen çalışıyor, yanlış veri, UX kırık
- **P3 — Minor:** Kozmetik, label yanlış, eksik tooltip, minor UX iyileştirme

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 0: DATA RESET & HEALTH CHECK
# ═══════════════════════════════════════════════════════════════

## 0.1 — Mevcut Veriyi Tamamen Sıfırla

Amacımız platformu sıfırdan test etmek. Tüm demo/test verisini temizle.

```bash
# Seed script'in reset modunu kullan (varsa)
cd /workspaces/SAP_Transformation_Platform
# Veya proje root'u neredeyse

# Seçenek A: Seed script ile temizle
python -c "
from app import create_app
from app.models import db
app = create_app()
with app.app_context():
    # Tüm tabloları listele ve sırayla temizle (FK constraint sırasına dikkat)
    meta = db.metadata
    # Reverse order for FK dependencies
    for table in reversed(meta.sorted_tables):
        print(f'Clearing {table.name}...')
        db.session.execute(table.delete())
    db.session.commit()
    print('✅ All tables cleared')
"

# Seçenek B: Eğer Seçenek A çalışmazsa, Alembic reset
# flask db downgrade base
# flask db upgrade head
```

**📝 NOT:** Eğer veritabanı sıfırlanamıyorsa, tam hata mesajını DEFECT-001 olarak kaydet ve devam et.

## 0.2 — Server Health Check

```bash
# Server çalışıyor mu?
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/
# Beklenen: 200

# DB bağlantısı
curl -s http://localhost:5000/api/v1/projects | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        print(f'✅ DB OK — {len(data)} projects (should be 0 after reset)')
    elif isinstance(data, dict) and 'items' in data:
        print(f'✅ DB OK — {len(data[\"items\"])} projects (should be 0 after reset)')
    else:
        print(f'⚠️ Unexpected response format: {type(data)}')
except Exception as e:
    print(f'❌ DB Error: {e}')
"
```

## 0.3 — Full Endpoint Smoke Test

Tüm ana endpoint'lere GET isteği at. Hepsi 200 dönmeli (boş liste OK).

```bash
#!/bin/bash
BASE="http://localhost:5000"
PASS=0; FAIL=0; ERRORS=""

test_ep() {
    local name=$1; local path=$2
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$path")
    if [ "$status" = "200" ]; then
        echo "  ✅ $name → $status"
        PASS=$((PASS+1))
    else
        echo "  ❌ $name → $status"
        FAIL=$((FAIL+1))
        ERRORS="$ERRORS\n  DEFECT: $name → $status"
    fi
}

echo "═══ BLOCK 0: Endpoint Health Check ═══"
echo ""
echo "--- Core ---"
test_ep "Projects"          "/api/v1/projects"
test_ep "Scenarios"         "/api/v1/scenarios"

echo ""
echo "--- Explore ---"
test_ep "Workshops"         "/api/v1/explore/workshops"
test_ep "Requirements"      "/api/v1/explore/requirements"
test_ep "Open Items"        "/api/v1/explore/open-items"
test_ep "Process Levels"    "/api/v1/explore/process-levels"
test_ep "Explore Dashboard" "/api/v1/explore/dashboard"

echo ""
echo "--- Backlog & Config ---"
test_ep "Backlog Items"     "/api/v1/backlog"
test_ep "Config Items"      "/api/v1/config-items"

echo ""
echo "--- Testing ---"
test_ep "Test Cases"        "/api/v1/testing/test-cases"
test_ep "Test Suites"       "/api/v1/testing/test-suites"
test_ep "Test Executions"   "/api/v1/testing/test-executions"
test_ep "Defects"           "/api/v1/testing/defects"

echo ""
echo "--- Supporting ---"
test_ep "Team Members"      "/api/v1/team-members"
test_ep "Interfaces"        "/api/v1/interfaces"
test_ep "Programs"          "/api/v1/programs"

echo ""
echo "--- Governance & RAID ---"
test_ep "RAID Items"        "/api/v1/raid"
test_ep "Notifications"     "/api/v1/notifications"
test_ep "Cutover Tasks"     "/api/v1/cutover/tasks"

echo ""
echo "═══════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
if [ -n "$ERRORS" ]; then
    echo -e "\n  Failed endpoints:$ERRORS"
fi
echo "═══════════════════════════════════════"
```

**📝 RAPORLA:** Çalışmayan endpoint'leri DEFECT olarak kaydet. Not: Bazı endpoint URL'leri farklı olabilir — 404 alanlar için `grep -rn "@.*_bp.route" app/blueprints/` ile doğru path'i bul ve tekrar dene.

## 0.4 — Frontend Navigation Smoke Test

Browser'da aşağıdaki sayfaları aç. F12 Console açık olsun.

| # | Sayfa | Sidebar Path | Kontrol |
|---|-------|-------------|---------|
| 1 | Dashboard | Ana sayfa (/) | Yükleniyor, JS error yok |
| 2 | Programs | Sidebar → Programs | Liste sayfası |
| 3 | Projects | Sidebar → Projects | Liste sayfası |
| 4 | Scenarios | Sidebar → Scenarios | Liste sayfası |
| 5 | Process Hierarchy | Sidebar → Process / Scope | Tree view |
| 6 | Explore Dashboard | Sidebar → Explore Dashboard | KPI kartları |
| 7 | Workshops | Sidebar → Workshops | Liste sayfası |
| 8 | Requirements | Sidebar → Requirements | Liste + filtre |
| 9 | Open Items | Sidebar → Open Items | Liste |
| 10 | Backlog | Sidebar → Backlog | WRICEF listesi |
| 11 | Config Items | Sidebar → Config Items | Config listesi |
| 12 | Test Management | Sidebar → Testing | Test suites/cases |
| 13 | Team Members | Sidebar → Team | Üye listesi |
| 14 | RAID | Sidebar → RAID | Risk/Issue listesi |

**📝 RAPORLA:** Her sayfa için:
- ✅ Yükleniyor / ❌ Hata
- Console'da JS error var mı?
- Network tab'da 4xx/5xx var mı?
- Boş (sıfırlanmış) veri mesajı gösteriyor mu?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 1: DISCOVER & PREPARE — Program & Proje Kurulumu
# ═══════════════════════════════════════════════════════════════

## SAP Activate Bağlam
Discover: Proje tanımı, scope belirleme, fırsat analizi
Prepare: Ekip kurulumu, detaylı planlama, süreç hiyerarşisi, workshop planlaması

---

### 1.1 — Program Oluşturma

```bash
curl -s -X POST http://localhost:5000/api/v1/programs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ACME Global Transformation",
    "code": "ACME-GTX",
    "description": "Global SAP S/4HANA 2023 FPS02 transformation program for ACME Manufacturing. Multi-country rollout: TR, DE, US, UK. Budget: €12M, Duration: 24 months.",
    "status": "active"
  }' | python3 -m json.tool
```

**Beklenen:** 201, program ID dönmeli. ID'yi kaydet → `$PROGRAM_ID`

**📝 TEST:** Browser'da Programs sayfasını aç → yeni program kartı görünüyor mu?

### 1.2 — Proje Oluşturma (Program Altında)

```bash
curl -s -X POST http://localhost:5000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ACME Turkey S/4HANA Greenfield",
    "code": "ACME-TR-S4H",
    "description": "Turkey pilot: SAP ECC 6.0 → S/4HANA 2023 FPS02 Greenfield. Scope: MM, PP, SD, FI/CO, QM, EWM. 450 users, 2 plants (Istanbul, Bursa). Go-live: Q4 2027.",
    "customer": "ACME Manufacturing A.Ş.",
    "program_id": '$PROGRAM_ID',
    "sap_product": "S/4HANA 2023 FPS02",
    "methodology": "SAP Activate",
    "status": "active",
    "start_date": "2026-03-01",
    "target_go_live": "2027-10-01"
  }' | python3 -m json.tool
```

**Beklenen:** 201, project ID dönmeli → `$PROJECT_ID`

**📝 UI TESTLERİ:**
1. Projects sayfasını aç → proje kartı görünüyor mu?
2. Proje kartına tıkla → Detay sayfası açılıyor mu?
3. "Edit" butonu çalışıyor mu?
4. Program ile ilişki görünüyor mu?

### 1.3 — Proje Bazlı Global Context Ayarla

Browser'da proje seçiciyi (sidebar veya header'daki dropdown) kullanarak ACME-TR-S4H projesini aktif proje olarak seç.

**📝 TEST:** Tüm sayfalarda proje filtresi çalışıyor mu? Sadece bu projeye ait veri mi gösteriliyor?

### 1.4 — Senaryo Oluşturma (5 E2E Senaryo)

```bash
PROJECT_ID=<yukarıdan gelen ID>

# Senaryo 1: Order to Cash
curl -s -X POST http://localhost:5000/api/v1/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Order to Cash (O2C)",
    "code": "O2C",
    "description": "End-to-end order management: Sales Order → Delivery → Billing → Payment. Modules: SD, FI, MM (ATP). Plants: Istanbul, Bursa.",
    "project_id": '$PROJECT_ID',
    "scenario_type": "e2e",
    "status": "active"
  }' | python3 -m json.tool

# Senaryo 2: Procure to Pay
curl -s -X POST http://localhost:5000/api/v1/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Procure to Pay (P2P)",
    "code": "P2P",
    "description": "Full procurement cycle: Purchase Requisition → PO → Goods Receipt → Invoice → Payment. Modules: MM, FI.",
    "project_id": '$PROJECT_ID',
    "scenario_type": "e2e",
    "status": "active"
  }' | python3 -m json.tool

# Senaryo 3: Plan to Produce
curl -s -X POST http://localhost:5000/api/v1/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Plan to Produce (P2P-MFG)",
    "code": "PTP",
    "description": "Manufacturing planning and execution: Demand Planning → MRP → Production Order → Confirmation → GI/GR. Modules: PP, QM, MM.",
    "project_id": '$PROJECT_ID',
    "scenario_type": "e2e",
    "status": "active"
  }' | python3 -m json.tool

# Senaryo 4: Record to Report
curl -s -X POST http://localhost:5000/api/v1/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Record to Report (R2R)",
    "code": "R2R",
    "description": "Financial closing and reporting: Journal Entry → Period Close → Consolidation → Financial Statements. Modules: FI/CO.",
    "project_id": '$PROJECT_ID',
    "scenario_type": "e2e",
    "status": "active"
  }' | python3 -m json.tool

# Senaryo 5: Warehouse Management
curl -s -X POST http://localhost:5000/api/v1/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Warehouse Operations (WM)",
    "code": "WM-OPS",
    "description": "EWM-based warehouse operations: Inbound → Putaway → Storage → Picking → Packing → Outbound. Modules: EWM, MM, SD.",
    "project_id": '$PROJECT_ID',
    "scenario_type": "e2e",
    "status": "active"
  }' | python3 -m json.tool
```

**📝 UI TESTLERİ:**
1. Scenarios sayfasında 5 senaryo listelenyor mu?
2. Her senaryo satırına tıklayınca detay açılıyor mu?
3. Senaryo düzenleme (Edit) çalışıyor mu?
4. Senaryo silme (Delete) butonu var mı ve çalışıyor mu? (Silme testini son senaryoda yapma, sadece butonun varlığını kontrol et)

### 1.5 — Ekip Üyeleri Oluşturma

```bash
# Program Manager
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Umut Soyyılmaz",
    "email": "umut@acme.com",
    "role": "program_manager",
    "department": "PMO",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool

# SD Consultant
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Elif Yıldız",
    "email": "elif@partner.com",
    "role": "functional_consultant",
    "department": "SD",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool

# MM Consultant
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mehmet Kaya",
    "email": "mehmet@partner.com",
    "role": "functional_consultant",
    "department": "MM",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool

# Technical Architect
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Can Demir",
    "email": "can@partner.com",
    "role": "technical_architect",
    "department": "Basis/ABAP",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool

# QM Consultant
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ayşe Arslan",
    "email": "ayse@acme.com",
    "role": "functional_consultant",
    "department": "QM",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool

# Test Manager
curl -s -X POST http://localhost:5000/api/v1/team-members \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Deniz Koç",
    "email": "deniz@partner.com",
    "role": "test_manager",
    "department": "QA",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
```

**📝 UI TESTLERİ:**
1. Team Members sayfasında 6 üye listelenyor mu?
2. Üye kartına tıklayınca detay açılıyor mu?
3. Üye düzenleme (Edit) çalışıyor mu?
4. Rol ve departman filtreleri çalışıyor mu?

### 1.6 — Süreç Hiyerarşisi Oluşturma (L1 → L4)

```bash
# L1: Sales (SD alanı)
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales",
    "level": 1,
    "process_area": "SD",
    "scope_status": "in_scope",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
# → $L1_SALES_ID

# L2: Order Management (under Sales)
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Order Management",
    "level": 2,
    "process_area": "SD",
    "scope_status": "in_scope",
    "parent_id": '$L1_SALES_ID',
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
# → $L2_ORDER_MGMT_ID

# L3 (Scope Item): Standard Sales Order Processing
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Standard Sales Order Processing",
    "code": "1YG",
    "level": 3,
    "process_area": "SD",
    "scope_status": "in_scope",
    "parent_id": '$L2_ORDER_MGMT_ID',
    "project_id": '$PROJECT_ID',
    "wave": 1
  }' | python3 -m json.tool
# → $L3_SO_ID

# L4: Create Sales Order
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Create Sales Order",
    "level": 4,
    "process_area": "SD",
    "scope_status": "in_scope",
    "parent_id": '$L3_SO_ID',
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
# → $L4_CREATE_SO_ID

# L4: Sales Order Pricing
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Order Pricing",
    "level": 4,
    "process_area": "SD",
    "scope_status": "in_scope",
    "parent_id": '$L3_SO_ID',
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
# → $L4_PRICING_ID

# L4: Available to Promise (ATP)
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Available to Promise Check",
    "level": 4,
    "process_area": "SD",
    "scope_status": "in_scope",
    "parent_id": '$L3_SO_ID',
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
# → $L4_ATP_ID

# L4: Delivery Processing
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Delivery Processing",
    "level": 4,
    "process_area": "SD",
    "scope_status": "in_scope",
    "parent_id": '$L3_SO_ID',
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
# → $L4_DELIVERY_ID

# --- MM Alanı ---
# L1: Procurement
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Procurement",
    "level": 1,
    "process_area": "MM",
    "scope_status": "in_scope",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
# → $L1_PROC_ID

# L2: Purchase Order Management
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Purchase Order Management",
    "level": 2,
    "process_area": "MM",
    "scope_status": "in_scope",
    "parent_id": '$L1_PROC_ID',
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
# → $L2_PO_MGMT_ID

# L3: Standard PO Processing (2FM)
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Standard Purchase Order Processing",
    "code": "2FM",
    "level": 3,
    "process_area": "MM",
    "scope_status": "in_scope",
    "parent_id": '$L2_PO_MGMT_ID',
    "project_id": '$PROJECT_ID',
    "wave": 1
  }' | python3 -m json.tool
# → $L3_PO_ID

# L4: Create Purchase Order
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Create Purchase Order",
    "level": 4,
    "process_area": "MM",
    "scope_status": "in_scope",
    "parent_id": '$L3_PO_ID',
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool

# L4: Goods Receipt
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Goods Receipt Processing",
    "level": 4,
    "process_area": "MM",
    "scope_status": "in_scope",
    "parent_id": '$L3_PO_ID',
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool

# L4: Invoice Verification
curl -s -X POST http://localhost:5000/api/v1/explore/process-levels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Invoice Verification",
    "level": 4,
    "process_area": "MM",
    "scope_status": "in_scope",
    "parent_id": '$L3_PO_ID',
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
```

**📝 UI TESTLERİ (Process Hierarchy sayfası):**
1. Tree view açılıyor mu?
2. L1 → L2 → L3 → L4 drill-down çalışıyor mu?
3. Scope Status badge'leri doğru renkte mi? (in_scope = yeşil, out_scope = gri)
4. KPI strip'te doğru level sayıları var mı? (L1:2, L2:2, L3:2, L4:7)
5. Scope Matrix görünümü çalışıyor mu?
6. Process Level düzenleme (Edit) çalışıyor mu?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 2: EXPLORE — Workshop & Fit-Gap Analizi
# ═══════════════════════════════════════════════════════════════

## SAP Activate Bağlam
Explore fazında mevcut iş süreçleri analiz edilir, Fit-Gap değerlendirmesi yapılır,
gereksinimler belirlenir ve açık noktalar kayıt altına alınır.

---

### 2.1 — Workshop Oluşturma

```bash
# Workshop 1: O2C Sales Order Workshop (SD)
curl -s -X POST http://localhost:5000/api/v1/explore/workshops \
  -H "Content-Type: application/json" \
  -d '{
    "name": "O2C Sales Order Processing Workshop",
    "project_id": '$PROJECT_ID',
    "scope_item_id": '$L3_SO_ID',
    "process_area": "SD",
    "wave": 1,
    "facilitator_id": "<ELIF_TEAM_MEMBER_ID>",
    "planned_date": "2026-04-15",
    "status": "draft",
    "description": "Fit-Gap analysis for standard sales order processing. Covers: SO creation, pricing, ATP check, delivery, billing."
  }' | python3 -m json.tool
# → $WS_O2C_ID

# Workshop 2: P2P Purchase Order Workshop (MM)
curl -s -X POST http://localhost:5000/api/v1/explore/workshops \
  -H "Content-Type: application/json" \
  -d '{
    "name": "P2P Purchase Order Processing Workshop",
    "project_id": '$PROJECT_ID',
    "scope_item_id": '$L3_PO_ID',
    "process_area": "MM",
    "wave": 1,
    "facilitator_id": "<MEHMET_TEAM_MEMBER_ID>",
    "planned_date": "2026-04-22",
    "status": "draft",
    "description": "Fit-Gap analysis for standard procurement process. Covers: PR, PO, GR, IV."
  }' | python3 -m json.tool
# → $WS_P2P_ID
```

**📝 UI TESTLERİ (Workshops Hub sayfası):**
1. 2 workshop listelenyor mu?
2. Workshop kartına tıklayınca detay açılıyor mu?
3. Status badge doğru mu? (draft = gri)
4. Process area ve wave filtresi çalışıyor mu?
5. "New Workshop" butonu çalışıyor mu?

### 2.2 — Workshop Schedule & Start

```bash
# Workshop 1'i schedule et
curl -s -X PUT http://localhost:5000/api/v1/explore/workshops/$WS_O2C_ID \
  -H "Content-Type: application/json" \
  -d '{"status": "scheduled"}' | python3 -m json.tool

# Workshop 1'i başlat (bu adım L4 process step'leri otomatik oluşturmalı)
curl -s -X POST http://localhost:5000/api/v1/explore/workshops/$WS_O2C_ID/start \
  -H "Content-Type: application/json" | python3 -m json.tool
```

**Beklenen:** Start endpoint'i L4 process step'leri oluşturmalı (Create SO, Pricing, ATP, Delivery)

**📝 UI TESTLERİ:**
1. Workshop detayında status "in_progress" olarak güncellendi mi?
2. Process Steps tab'ında L4 adımları görünüyor mu?
3. Her adım için Fit/Gap/Partial butonları var mı?

### 2.3 — Fit-Gap Kararları Girme (Process Step Bazında)

Workshop detay sayfasında her L4 process step için Fit-Gap kararı ver:

```bash
# Process Step 1: Create Sales Order → FIT
curl -s -X PUT http://localhost:5000/api/v1/explore/process-steps/$L4_CREATE_SO_STEP_ID \
  -H "Content-Type: application/json" \
  -d '{
    "fit_decision": "fit",
    "notes": "Standard SAP sales order creation process (VA01) covers ACME requirements. No customization needed."
  }' | python3 -m json.tool

# Process Step 2: Sales Order Pricing → GAP
curl -s -X PUT http://localhost:5000/api/v1/explore/process-steps/$L4_PRICING_STEP_ID \
  -H "Content-Type: application/json" \
  -d '{
    "fit_decision": "gap",
    "notes": "ACME uses multi-tier volume-based pricing with retroactive rebates. Standard pricing procedure does not cover this. Custom condition type and pricing procedure needed."
  }' | python3 -m json.tool

# Process Step 3: ATP Check → PARTIAL FIT
curl -s -X PUT http://localhost:5000/api/v1/explore/process-steps/$L4_ATP_STEP_ID \
  -H "Content-Type: application/json" \
  -d '{
    "fit_decision": "partial_fit",
    "notes": "Standard ATP covers basic availability. However, ACME needs cross-plant ATP with transportation lead time. Configuration change required."
  }' | python3 -m json.tool

# Process Step 4: Delivery Processing → FIT
curl -s -X PUT http://localhost:5000/api/v1/explore/process-steps/$L4_DELIVERY_STEP_ID \
  -H "Content-Type: application/json" \
  -d '{
    "fit_decision": "fit",
    "notes": "Standard outbound delivery process (VL01N) meets requirements. Delivery split and partial delivery supported."
  }' | python3 -m json.tool
```

**📝 UI TESTLERİ:**
1. Her process step'te fit/gap/partial karar butonu çalışıyor mu?
2. Karar verildikten sonra badge rengi güncelleniyor mu? (Fit=yeşil, Gap=kırmızı, Partial=sarı)
3. Notes alanı kaydediliyor mu?
4. L3 seviyesinde fit summary otomatik hesaplanıyor mu? (2 Fit, 1 Gap, 1 Partial)

### 2.4 — Decision Kayıtları

```bash
# Gap process step'ine karar ekle
curl -s -X POST http://localhost:5000/api/v1/explore/process-steps/$L4_PRICING_STEP_ID/decisions \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Custom pricing procedure will be developed. ABAP enhancement for retroactive rebate calculation. Estimated effort: 15 MD.",
    "decided_by": "Elif Yıldız",
    "category": "development",
    "rationale": "Business requirement cannot be met with standard configuration. Volume-based retroactive rebates are critical for ACME customer contracts."
  }' | python3 -m json.tool

# Partial fit step'ine karar ekle
curl -s -X POST http://localhost:5000/api/v1/explore/process-steps/$L4_ATP_STEP_ID/decisions \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Cross-plant ATP will be activated via configuration. No ABAP development needed. Transport lead time will be maintained in customizing.",
    "decided_by": "Elif Yıldız",
    "category": "configuration",
    "rationale": "SAP standard ATP supports cross-plant check with proper configuration."
  }' | python3 -m json.tool
```

**📝 UI TESTLERİ:**
1. Decision log görünüyor mu?
2. Decision'a tıklayınca detay açılıyor mu?
3. Decision düzenleme çalışıyor mu?

### 2.5 — Open Item Oluşturma

```bash
# Pricing gap'i için open item
curl -s -X POST http://localhost:5000/api/v1/explore/process-steps/$L4_PRICING_STEP_ID/open-items \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Clarify retroactive rebate business rules",
    "description": "Need detailed business rules for volume-based retroactive rebate calculation: tiers, periods, customer groups, approval workflow.",
    "priority": "high",
    "assigned_to": "Elif Yıldız",
    "due_date": "2026-04-30",
    "category": "business_clarification"
  }' | python3 -m json.tool
# → $OI_REBATE_ID

# ATP cross-plant için open item
curl -s -X POST http://localhost:5000/api/v1/explore/process-steps/$L4_ATP_STEP_ID/open-items \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Provide transport lead times per route",
    "description": "ACME logistics team to provide transport lead times for all plant-to-customer routes for ATP calculation.",
    "priority": "medium",
    "assigned_to": "Mehmet Kaya",
    "due_date": "2026-05-15",
    "category": "data_collection"
  }' | python3 -m json.tool
# → $OI_TRANSPORT_ID

# Genel bir open item
curl -s -X POST http://localhost:5000/api/v1/explore/open-items \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Confirm chart of accounts structure for S/4HANA",
    "description": "FI team to confirm if current CoA can be migrated or if new CoA is needed for S/4HANA universal journal.",
    "priority": "critical",
    "assigned_to": "Umut Soyyılmaz",
    "due_date": "2026-04-20",
    "project_id": '$PROJECT_ID',
    "category": "decision_required"
  }' | python3 -m json.tool
```

**📝 UI TESTLERİ:**
1. Open Items sayfasında 3 OI listelenyor mu?
2. Priority badge renkleri doğru mu? (critical=kırmızı, high=turuncu, medium=mavi)
3. Status lifecycle: Open → In Progress → Closed çalışıyor mu?
4. OI'ye tıklayınca detay açılıyor mu?
5. Edit/Update butonu çalışıyor mu?
6. Due date ve assignee gösteriliyor mu?
7. Workshop ilişkisi doğru mu? (process step'ten oluşturulanlar workshop'a bağlı mı?)

### 2.6 — Requirement Oluşturma (Gap'lerden)

```bash
# Gap: Pricing Enhancement Requirement
curl -s -X POST http://localhost:5000/api/v1/explore/process-steps/$L4_PRICING_STEP_ID/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Custom Volume-Based Retroactive Rebate Pricing",
    "description": "Develop custom pricing procedure with:\n1. Multi-tier volume-based pricing\n2. Retroactive rebate calculation\n3. Rebate agreement management\n4. Settlement to FI",
    "requirement_type": "gap",
    "priority": "high",
    "complexity": "high",
    "effort_estimate": 15,
    "module": "SD"
  }' | python3 -m json.tool
# → $REQ_PRICING_ID

# Partial Fit: Cross-Plant ATP Configuration
curl -s -X POST http://localhost:5000/api/v1/explore/process-steps/$L4_ATP_STEP_ID/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cross-Plant ATP with Transport Lead Time",
    "description": "Configure cross-plant ATP check:\n1. Activate cross-plant availability check\n2. Maintain transportation lead times\n3. Configure checking group for cross-plant",
    "requirement_type": "partial_fit",
    "priority": "medium",
    "complexity": "medium",
    "effort_estimate": 5,
    "module": "SD"
  }' | python3 -m json.tool
# → $REQ_ATP_ID

# Fit: Standard SO Processing (config only)
curl -s -X POST http://localhost:5000/api/v1/explore/process-steps/$L4_CREATE_SO_STEP_ID/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Standard Sales Order Configuration",
    "description": "Configure standard sales order type (OR):\n1. Sales document type setup\n2. Item category determination\n3. Partner determination procedure\n4. Output determination",
    "requirement_type": "fit",
    "priority": "medium",
    "complexity": "low",
    "effort_estimate": 3,
    "module": "SD"
  }' | python3 -m json.tool
# → $REQ_SO_ID
```

**📝 UI TESTLERİ:**
1. Requirements sayfasında 3 requirement listelenyor mu?
2. Requirement type badge doğru mu? (gap=kırmızı, partial_fit=sarı, fit=yeşil)
3. Detay sayfası açılıyor mu?
4. Edit butonu çalışıyor mu?
5. Process Step ve Workshop ilişkileri görünüyor mu?
6. Open Item ile linking yapılabiliyor mu?
7. Status lifecycle çalışıyor mu? (draft → review → approved → backlog → realized → verified)

### 2.7 — Requirement ↔ Open Item Linking

```bash
# Pricing requirement'ı rebate open item'a bağla
curl -s -X POST http://localhost:5000/api/v1/explore/requirements/$REQ_PRICING_ID/link-open-item \
  -H "Content-Type: application/json" \
  -d '{"open_item_id": '$OI_REBATE_ID'}' | python3 -m json.tool
```

**📝 UI TESTLERİ:**
1. Requirement detayında linked Open Items görünüyor mu?
2. Open Item detayında linked Requirements görünüyor mu?
3. Link kaldırma (unlink) butonu var mı ve çalışıyor mu?

### 2.8 — Workshop Complete

```bash
# Workshop'u tamamla (tüm process step'lerde fit_decision set olmalı)
curl -s -X POST http://localhost:5000/api/v1/explore/workshops/$WS_O2C_ID/complete \
  -H "Content-Type: application/json" | python3 -m json.tool
```

**Beklenen:**
- Status → "completed"
- L4 fit_decision'ları L3 seviyesine propagate edilmeli
- L3 fit_summary hesaplanmalı

**📝 UI TESTLERİ:**
1. Workshop status "completed" olarak güncellendi mi?
2. Process Hierarchy'de L3 node'unda fit summary güncellenmiş mi?
3. Workshop'u tekrar açma (reopen) butonu var mı?
4. Completed workshop'ta edit engelleniyor mu?

### 2.9 — Explore Dashboard Kontrolü

Browser'da Explore Dashboard sayfasını aç.

**📝 KPI TESTLERİ:**
1. Workshops KPI: 2 (1 completed, 1 draft)
2. WS Completion %: 50%
3. Requirements: 3
4. Open Items: 3
5. Fit/Gap donut/bar chart doğru veri gösteriyor mu?
6. Grafiklerdeki veriler mantıklı mı?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 3: REALIZE — Backlog, Config, FS/TS
# ═══════════════════════════════════════════════════════════════

## SAP Activate Bağlam
Realize fazında gap'ler geliştirme backlog'una alınır, fit'ler config olarak tanımlanır,
fonksiyonel ve teknik spesifikasyonlar yazılır.

---

### 3.1 — Requirement → Backlog Item Dönüşümü

Requirement'lar approve edildikten sonra backlog'a dönüşmeli.

```bash
# Önce requirement'ı approve et
curl -s -X PUT http://localhost:5000/api/v1/explore/requirements/$REQ_PRICING_ID \
  -H "Content-Type: application/json" \
  -d '{"status": "approved"}' | python3 -m json.tool

# Backlog item oluştur (requirement'tan)
curl -s -X POST http://localhost:5000/api/v1/backlog \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Custom Volume-Based Retroactive Rebate Pricing",
    "description": "Develop custom pricing procedure with multi-tier volume-based pricing, retroactive rebate calculation, rebate agreement management, and settlement to FI.",
    "wricef_type": "enhancement",
    "priority": "high",
    "status": "new",
    "project_id": '$PROJECT_ID',
    "requirement_id": "'$REQ_PRICING_ID'",
    "module": "SD",
    "estimated_effort": 15
  }' | python3 -m json.tool
# → $BL_PRICING_ID

# ATP config backlog
curl -s -X POST http://localhost:5000/api/v1/backlog \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cross-Plant ATP Configuration",
    "description": "Configure cross-plant ATP check with transportation lead times.",
    "wricef_type": "configuration",
    "priority": "medium",
    "status": "new",
    "project_id": '$PROJECT_ID',
    "requirement_id": "'$REQ_ATP_ID'",
    "module": "SD",
    "estimated_effort": 5
  }' | python3 -m json.tool
# → $BL_ATP_ID
```

**📝 UI TESTLERİ (Backlog sayfası):**
1. Backlog Items sayfasında 2 item listelenyor mu?
2. WRICEF type badge doğru mu? (enhancement, configuration)
3. Detay sayfası açılıyor mu?
4. Requirement linkage görünüyor mu?
5. Status lifecycle: new → in_dev → dev_complete → testing → done çalışıyor mu?
6. Sprint/Wave atama yapılabiliyor mu?
7. Edit butonu çalışıyor mu?

### 3.2 — Config Item Oluşturma (Fit Requirement İçin)

```bash
curl -s -X POST http://localhost:5000/api/v1/config-items \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Standard Sales Order Type (OR) Configuration",
    "description": "Configure sales document type OR: item category determination, partner determination, output determination, pricing procedure assignment.",
    "config_type": "customizing",
    "t_code": "VOV8",
    "module": "SD",
    "status": "planned",
    "project_id": '$PROJECT_ID',
    "requirement_id": "'$REQ_SO_ID'"
  }' | python3 -m json.tool
# → $CFG_SO_ID
```

**📝 UI TESTLERİ (Config Items sayfası):**
1. Config Items sayfasında 1 item listelenyor mu?
2. T-Code görünüyor mu?
3. Detay sayfası açılıyor mu?
4. Config details (transport request, step-by-step) girilebiliyor mu?

### 3.3 — Functional Spec (FS) Yazma

```bash
# Backlog item için FS
curl -s -X POST http://localhost:5000/api/v1/backlog/$BL_PRICING_ID/functional-spec \
  -H "Content-Type: application/json" \
  -d '{
    "title": "FS: Custom Volume-Based Retroactive Rebate Pricing",
    "content": "## 1. Overview\nCustom pricing procedure Z_REBATE for multi-tier volume-based retroactive rebate calculation.\n\n## 2. Business Process\n- Sales orders capture line item pricing\n- Monthly rebate calculation job runs\n- Retroactive adjustment via credit memo\n- Settlement posting to FI\n\n## 3. Configuration\n- New condition type ZREB (rebate)\n- New pricing procedure ZACME with ZREB step\n- Rebate agreement type 0003 copy\n\n## 4. Development\n- ABAP enhancement: Rebate calculation engine\n- Custom table: ZREBATE_TIERS (volume tiers)\n- SmartForm: Rebate settlement report",
    "status": "draft",
    "author": "Elif Yıldız"
  }' | python3 -m json.tool
# → $FS_PRICING_ID
```

**📝 UI TESTLERİ:**
1. Backlog item detayında FS tab'ı görünüyor mu?
2. FS içeriği (markdown/rich text) render ediliyor mu?
3. FS düzenleme çalışıyor mu?
4. FS status lifecycle: draft → review → approved çalışıyor mu?

### 3.4 — Technical Spec (TS) Yazma

```bash
curl -s -X POST http://localhost:5000/api/v1/backlog/$BL_PRICING_ID/technical-spec \
  -H "Content-Type: application/json" \
  -d '{
    "title": "TS: Custom Volume-Based Retroactive Rebate Pricing",
    "content": "## 1. Technical Design\n\n### Custom Table\n- ZREBATE_TIERS: MANDT, KUNNR, MATNR, TIER_FROM, TIER_TO, REBATE_PCT, VALID_FROM, VALID_TO\n\n### Enhancement\n- Enhancement Spot: Z_REBATE_CALC\n- BAdI Implementation: Z_BADI_REBATE\n- Method: CALCULATE_REBATE\n\n### Reports\n- Z_REBATE_SETTLEMENT: Monthly rebate settlement report\n- Z_REBATE_ANALYSIS: Rebate tier analysis\n\n### Interfaces\n- None (internal only)\n\n## 2. Unit Test Plan\n1. Create rebate tiers\n2. Create sales order with qualifying quantity\n3. Run rebate calculation\n4. Verify credit memo creation\n5. Verify FI posting",
    "status": "draft",
    "author": "Can Demir"
  }' | python3 -m json.tool
# → $TS_PRICING_ID
```

**📝 UI TESTLERİ:**
1. TS tab görünüyor mu?
2. TS içeriği render ediliyor mu?
3. TS düzenleme ve status lifecycle çalışıyor mu?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 4: TEST — Test Cases, Suites, Execution, Defects
# ═══════════════════════════════════════════════════════════════

## SAP Activate Bağlam
Test fazında unit test → SIT → UAT → Regression → Performance testleri sırayla yürütülür.

---

### 4.1 — Test Case Oluşturma

```bash
# Unit Test: Rebate Pricing
curl -s -X POST http://localhost:5000/api/v1/testing/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UT: Rebate Pricing - Tier 1 Volume",
    "description": "Verify rebate calculation for Tier 1 volume (0-100 units, 2% rebate)",
    "test_level": "unit",
    "priority": "high",
    "status": "ready",
    "project_id": '$PROJECT_ID',
    "backlog_item_id": "'$BL_PRICING_ID'",
    "module": "SD",
    "preconditions": "Rebate tier table maintained with Tier 1: 0-100 units = 2%",
    "steps": "1. Create SO for customer 1000 with material M100, qty 50\n2. Run rebate calculation report\n3. Verify credit memo amount = order value * 2%\n4. Verify FI document posted",
    "expected_result": "Credit memo created with correct rebate amount, FI posting successful"
  }' | python3 -m json.tool
# → $TC_UNIT_1_ID

# SIT Test: End-to-End O2C with Rebate
curl -s -X POST http://localhost:5000/api/v1/testing/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "SIT: E2E O2C with Volume Rebate Settlement",
    "description": "End-to-end test: Sales Order → Delivery → Billing → Rebate Calculation → Credit Memo → Payment",
    "test_level": "sit",
    "priority": "high",
    "status": "ready",
    "project_id": '$PROJECT_ID',
    "backlog_item_id": "'$BL_PRICING_ID'",
    "module": "SD",
    "preconditions": "Customer master, material master, pricing procedure, rebate tiers all configured",
    "steps": "1. Create SO (VA01) with qty crossing Tier 1\n2. Create delivery (VL01N)\n3. Post goods issue\n4. Create invoice (VF01)\n5. Run rebate settlement\n6. Verify credit memo\n7. Process payment",
    "expected_result": "Full O2C cycle complete with correct rebate settlement"
  }' | python3 -m json.tool
# → $TC_SIT_1_ID

# UAT Test: Business User Acceptance
curl -s -X POST http://localhost:5000/api/v1/testing/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UAT: Sales Manager - Volume Rebate Scenario",
    "description": "Business user validates the complete rebate scenario from sales order through settlement",
    "test_level": "uat",
    "priority": "critical",
    "status": "draft",
    "project_id": '$PROJECT_ID',
    "module": "SD",
    "preconditions": "Business user access configured, test data prepared",
    "steps": "1. Sales manager creates order for key customer\n2. Verify pricing includes rebate condition\n3. Process full O2C cycle\n4. Review rebate settlement report\n5. Approve credit memo\n6. Verify customer account balance",
    "expected_result": "Business user confirms process meets business requirements"
  }' | python3 -m json.tool
# → $TC_UAT_1_ID

# Config Test: ATP Cross-Plant
curl -s -X POST http://localhost:5000/api/v1/testing/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UT: Cross-Plant ATP Check",
    "description": "Verify ATP check considers stock across multiple plants with transport lead time",
    "test_level": "unit",
    "priority": "medium",
    "status": "ready",
    "project_id": '$PROJECT_ID',
    "backlog_item_id": "'$BL_ATP_ID'",
    "module": "SD",
    "steps": "1. Set stock: Plant IST=50, Plant BRS=100\n2. Create SO for 80 units\n3. Verify ATP proposes split: 50 from IST + 30 from BRS\n4. Verify delivery dates include transport lead time",
    "expected_result": "ATP correctly splits across plants with appropriate lead times"
  }' | python3 -m json.tool
# → $TC_UNIT_2_ID
```

**📝 UI TESTLERİ:**
1. Test Cases sayfasında 4 test case listelenyor mu?
2. Test level filtresi çalışıyor mu? (unit/sit/uat tabs)
3. Priority ve status badge'leri doğru mu?
4. Detay sayfası açılıyor mu?
5. Steps ve expected result alanları görünüyor mu?
6. Edit butonu çalışıyor mu?
7. Backlog Item linkage görünüyor mu?

### 4.2 — Test Suite Oluşturma

```bash
curl -s -X POST http://localhost:5000/api/v1/testing/test-suites \
  -H "Content-Type: application/json" \
  -d '{
    "name": "O2C Rebate Pricing - SIT Cycle 1",
    "description": "System Integration Test suite for O2C rebate pricing functionality",
    "test_level": "sit",
    "project_id": '$PROJECT_ID',
    "status": "planned"
  }' | python3 -m json.tool
# → $TS_SIT_ID
```

**📝 UI TESTLERİ:**
1. Test Suites sayfasında suite listelenyor mu?
2. Suite'e test case atama yapılabiliyor mu?
3. Suite progress (pass/fail/pending) bar gösteriliyor mu?

### 4.3 — Test Execution

```bash
# Unit test execute — PASS
curl -s -X POST http://localhost:5000/api/v1/testing/test-executions \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "'$TC_UNIT_1_ID'",
    "test_suite_id": "'$TS_SIT_ID'",
    "status": "passed",
    "executed_by": "Deniz Koç",
    "executed_at": "2026-06-15T14:30:00",
    "notes": "All steps passed. Rebate calculation correct for Tier 1.",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
# → $EX_1_ID

# SIT test execute — FAILED (to create defect)
curl -s -X POST http://localhost:5000/api/v1/testing/test-executions \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "'$TC_SIT_1_ID'",
    "test_suite_id": "'$TS_SIT_ID'",
    "status": "failed",
    "executed_by": "Deniz Koç",
    "executed_at": "2026-06-16T10:00:00",
    "notes": "Step 5 failed: Rebate settlement created credit memo with wrong amount. Expected 2% of order value, got 2% of net value (excluding tax).",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
# → $EX_2_ID

# Unit test ATP — PASS
curl -s -X POST http://localhost:5000/api/v1/testing/test-executions \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "'$TC_UNIT_2_ID'",
    "status": "passed",
    "executed_by": "Deniz Koç",
    "executed_at": "2026-06-17T09:00:00",
    "notes": "Cross-plant ATP working correctly.",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
```

**📝 UI TESTLERİ:**
1. Test Execution listesi görünüyor mu?
2. Pass/Fail badge'leri doğru renkte mi?
3. Execution detayında test case bilgisi linkli mi?
4. "Re-execute" butonu var mı?

### 4.4 — Defect Oluşturma (Failed Test'ten)

```bash
curl -s -X POST http://localhost:5000/api/v1/testing/defects \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Rebate settlement calculates on net value instead of gross order value",
    "description": "During SIT E2E test, rebate settlement job calculated 2% rebate on net value (excluding tax) instead of gross order value as per business requirement.\n\nExpected: Rebate = Order Gross Value * Rebate %\nActual: Rebate = Order Net Value * Rebate %\n\nImpact: Customers receive lower rebates than contractually agreed.",
    "severity": "critical",
    "priority": "high",
    "status": "new",
    "test_case_id": "'$TC_SIT_1_ID'",
    "test_execution_id": "'$EX_2_ID'",
    "backlog_item_id": "'$BL_PRICING_ID'",
    "assigned_to": "Can Demir",
    "project_id": '$PROJECT_ID',
    "module": "SD",
    "steps_to_reproduce": "1. Create SO qty 100, unit price 100 TRY, tax 18%\n2. Complete O2C cycle\n3. Run rebate settlement\n4. Check credit memo amount\n5. Expected: 200 TRY (2% of 10,000)\n6. Actual: 169.49 TRY (2% of 8,474.58 net)"
  }' | python3 -m json.tool
# → $DEFECT_1_ID
```

**📝 UI TESTLERİ:**
1. Defects sayfasında defect listelenyor mu?
2. Severity badge doğru mu? (critical=kırmızı)
3. Detay sayfası açılıyor mu?
4. Test Case ve Execution linkleri görünüyor mu?
5. Status lifecycle: new → assigned → in_progress → fixed → verified → closed çalışıyor mu?
6. Edit ve comment ekleme çalışıyor mu?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 5: TRACEABILITY — End-to-End Zincir Doğrulama
# ═══════════════════════════════════════════════════════════════

## SAP Activate Bağlam
Traceability, SAP transformasyonunun omurgasıdır. Her entity'nin
yukarı (upstream) ve aşağı (downstream) bağlantıları eksiksiz olmalıdır.

---

### 5.1 — API Trace Doğrulama

```bash
echo "═══ TRACEABILITY CHAIN TESTS ═══"

# 1. Requirement Trace (tam zincir bekleniyor)
echo ""
echo "--- Requirement Trace ---"
curl -s http://localhost:5000/api/v1/traceability/explore_requirement/$REQ_PRICING_ID | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('Entity:', d.get('entity', {}).get('title', 'N/A'))
    print('Upstream:', [x.get('type') for x in d.get('upstream', [])])
    print('Downstream:', [x.get('type') for x in d.get('downstream', [])])
    print('Lateral:', list(d.get('lateral', {}).keys()))
    print('Chain Depth:', d.get('chain_depth', 'N/A'))
    print('Gaps:', d.get('gaps', []))
except Exception as e:
    print(f'❌ Error: {e}')
"
# Beklenen upstream: process_step → workshop → scenario
# Beklenen downstream: backlog_item → FS/TS → test_case → test_execution → defect
# Beklenen lateral: open_items

# 2. Backlog Item Trace
echo ""
echo "--- Backlog Item Trace ---"
curl -s http://localhost:5000/api/v1/traceability/backlog_item/$BL_PRICING_ID | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('Entity:', d.get('entity', {}).get('title', 'N/A'))
    print('Upstream:', [x.get('type') for x in d.get('upstream', [])])
    print('Downstream:', [x.get('type') for x in d.get('downstream', [])])
    print('Chain Depth:', d.get('chain_depth', 'N/A'))
    print('Gaps:', d.get('gaps', []))
except Exception as e:
    print(f'❌ Error: {e}')
"
# Beklenen upstream: requirement → workshop → process → scenario
# Beklenen downstream: FS → TS → test_case → execution → defect

# 3. Test Case Trace
echo ""
echo "--- Test Case Trace ---"
curl -s http://localhost:5000/api/v1/traceability/test_case/$TC_SIT_1_ID | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('Entity:', d.get('entity', {}).get('title', 'N/A'))
    print('Upstream:', [x.get('type') for x in d.get('upstream', [])])
    print('Downstream:', [x.get('type') for x in d.get('downstream', [])])
    print('Chain Depth:', d.get('chain_depth', 'N/A'))
except Exception as e:
    print(f'❌ Error: {e}')
"
# Beklenen upstream: backlog_item → requirement → workshop → scenario
# Beklenen downstream: test_execution → defect

# 4. Defect Trace (en derin zincir)
echo ""
echo "--- Defect Trace ---"
curl -s http://localhost:5000/api/v1/traceability/defect/$DEFECT_1_ID | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('Entity:', d.get('entity', {}).get('title', 'N/A'))
    print('Upstream:', [x.get('type') for x in d.get('upstream', [])])
    print('Chain Depth:', d.get('chain_depth', 'N/A'))
except Exception as e:
    print(f'❌ Error: {e}')
"
# Beklenen: Defect → Execution → Test Case → Backlog → Requirement → Workshop → Process → Scenario

# 5. Scenario Trace (en üst seviye, aşağı doğru)
echo ""
echo "--- Scenario Trace ---"
curl -s http://localhost:5000/api/v1/traceability/scenario/<O2C_SCENARIO_ID> | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('Downstream types:', set(x.get('type') for x in d.get('downstream', [])))
    print('Chain Depth:', d.get('chain_depth', 'N/A'))
    counts = {}
    for x in d.get('downstream', []):
        t = x.get('type', 'unknown')
        counts[t] = counts.get(t, 0) + 1
    print('Coverage:', counts)
except Exception as e:
    print(f'❌ Error: {e}')
"
```

**📝 TRACE RAPORLA:**

| Trace Başlangıç | Upstream Tamamlanma | Downstream Tamamlanma | Chain Depth | Gaps |
|------------------|--------------------|-----------------------|-------------|------|
| Requirement | ? / tam | ? / tam | ?/6 | ? |
| Backlog Item | ? / tam | ? / tam | ?/6 | ? |
| Test Case | ? / tam | ? / tam | ?/6 | ? |
| Defect | ? / tam | N/A | ?/6 | ? |
| Scenario | N/A | ? / tam | ?/6 | ? |

### 5.2 — UI Trace Doğrulama

Browser'da her entity türünde "Trace" / "Traceability" butonuna tıkla:

| # | Entity | Sayfada Trace Butonu Var mı? | Modal/Tab Açılıyor mu? | Zincir Doğru mu? |
|---|--------|------------------------------|------------------------|------------------|
| 1 | Requirement detay | ? | ? | upstream + downstream |
| 2 | Backlog Item detay | ? | ? | upstream + downstream |
| 3 | Config Item detay | ? | ? | upstream + downstream |
| 4 | Test Case detay | ? | ? | upstream + downstream |
| 5 | Defect detay | ? | ? | upstream chain |

**📝 UI Trace TESTLERİ:**
1. Trace modal/component render ediliyor mu?
2. Node'lara tıklanabiliyor mu (ilgili entity'ye navigasyon)?
3. Chain depth indicator gösteriliyor mu?
4. Gap uyarıları gösteriliyor mu?
5. Renk kodlaması doğru mu? (entity type'a göre)
6. "Could not load traceability data" hatası var mı?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 6: RAID & GOVERNANCE
# ═══════════════════════════════════════════════════════════════

### 6.1 — RAID Item Oluşturma

```bash
# Risk
curl -s -X POST http://localhost:5000/api/v1/raid \
  -H "Content-Type: application/json" \
  -d '{
    "type": "risk",
    "title": "Custom rebate development delay may impact SIT timeline",
    "description": "Complex ABAP development for rebate pricing may take longer than estimated 15 MD. If delayed, SIT cycle 1 start date at risk.",
    "probability": "medium",
    "impact": "high",
    "status": "open",
    "owner": "Umut Soyyılmaz",
    "mitigation": "Early technical spike in Sprint 1. Parallel development tracks.",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool

# Issue
curl -s -X POST http://localhost:5000/api/v1/raid \
  -H "Content-Type: application/json" \
  -d '{
    "type": "issue",
    "title": "ACME finance team not yet assigned to project",
    "description": "FI/CO business process owners have not been formally assigned. R2R workshops cannot start without their participation.",
    "impact": "high",
    "status": "open",
    "owner": "Umut Soyyılmaz",
    "resolution_plan": "Escalate to steering committee for resource allocation.",
    "project_id": '$PROJECT_ID'
  }' | python3 -m json.tool
```

**📝 UI TESTLERİ:**
1. RAID sayfasında risk ve issue listelenyor mu?
2. Type filtresi çalışıyor mu? (risk/issue/assumption/dependency)
3. Risk score hesaplanıyor mu? (probability × impact)
4. Edit ve status güncelleme çalışıyor mu?

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 7: COMPREHENSIVE UI BUTTON TEST MATRIX
# ═══════════════════════════════════════════════════════════════

## Her sayfadaki tüm butonları sistematik test et.

### 7.1 — Global UI Elements

| # | Element | Konum | Test | Sonuç |
|---|---------|-------|------|-------|
| 1 | Sidebar navigation (tüm linkler) | Sol panel | Her linke tıkla, sayfa açılıyor mu? | |
| 2 | Project selector dropdown | Header/Sidebar | Proje değiştirince veri filtreleniyor mu? | |
| 3 | Notification bell | Header | Tıklayınca notification paneli açılıyor mu? | |
| 4 | Dark/Light mode toggle | Header (varsa) | Tema değişiyor mu? | |
| 5 | Search (global) | Header (varsa) | Arama çalışıyor mu? | |
| 6 | User menu | Header sağ üst | Profil/logout görünüyor mu? | |

### 7.2 — CRUD Butonları (Her Entity Sayfası İçin)

Aşağıdaki tabloyu HER entity sayfası için (Programs, Projects, Scenarios, Workshops, Requirements, Open Items, Backlog, Config, Test Cases, Test Suites, Test Executions, Defects, Team Members, RAID, Interfaces) doldur:

| Buton | Var mı? | Çalışıyor mu? | Not |
|-------|---------|---------------|-----|
| **New / Create (+)** | | | Modal/form açılıyor mu? |
| **Edit (kalem ikonu)** | | | Form doluyor mu, kayıt başarılı mı? |
| **Delete (çöp ikonu)** | | | Onay dialogu var mı? Sildikten sonra liste güncelleniyor mu? |
| **View Detail (satır tıklama)** | | | Detay sayfası/modal açılıyor mu? |
| **Filter dropdowns** | | | Filtre uygulanıyor mu? |
| **Search (arama kutusu)** | | | Sonuçlar filtreleniyor mu? |
| **Sort (kolon başlığı)** | | | Sıralama değişiyor mu? |
| **Pagination** | | | Sayfalama çalışıyor mu? (5+ kayıt varsa) |
| **Export (varsa)** | | | Dosya indiriliyor mu? |
| **Refresh** | | | Veri yeniden yükleniyor mu? |

### 7.3 — Özel Butonlar (Sayfa Bazlı)

| Sayfa | Buton | Çalışıyor mu? | Not |
|-------|-------|---------------|-----|
| Workshop | Schedule | | draft → scheduled |
| Workshop | Start | | scheduled → in_progress + process steps oluşturuyor mu? |
| Workshop | Complete | | in_progress → completed + validation |
| Workshop | Reopen | | completed → in_progress |
| Process Step | Fit/Gap/Partial butonları | | Karar kaydediliyor mu? |
| Process Step | Add Decision | | Decision oluşturuluyor mu? |
| Process Step | Add Open Item | | OI oluşturuluyor mu? |
| Process Step | Add Requirement | | Requirement oluşturuluyor mu? |
| Requirement | Link Open Item | | M:N linking çalışıyor mu? |
| Requirement | Status transition butonları | | draft→review→approved→backlog |
| Requirement | Trace butonu | | TraceChain modal açılıyor mu? |
| Backlog | FS/TS tab'ları | | Spec yazılabiliyor mu? |
| Backlog | Trace butonu | | Traceability çalışıyor mu? |
| Test Case | Execute butonu | | Execution oluşturuluyor mu? |
| Test Execution | Pass/Fail butonları | | Status güncelleniyor mu? |
| Test Execution | Create Defect (fail sonrası) | | Defect oluşturuluyor mu? |
| Defect | Link to Test Case | | Linkage çalışıyor mu? |
| Process Hierarchy | L3 Sign-off | | Sign-off workflow çalışıyor mu? |
| Process Hierarchy | Scope Matrix butonu | | Matrix görünümü açılıyor mu? |
| Process Hierarchy | Fit Consolidation | | L4→L3 propagation çalışıyor mu? |
| Explore Dashboard | KPI kartları | | Doğru sayıları gösteriyor mu? |
| Explore Dashboard | Snapshot Capture | | Snapshot kaydediliyor mu? |

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 8: FINAL REPORT — Defect Summary & Task List
# ═══════════════════════════════════════════════════════════════

### 8.1 — Tüm Bulguları Topla

Aşağıdaki tabloya tüm BLOCK'lardan bulunan defectleri derle:

```
| # | Defect ID | Severity | Kategori | Başlık | Block | Adım |
|---|-----------|----------|----------|--------|-------|------|
| 1 | DEFECT-001 | P1 | API | ... | 0 | 0.3 |
| 2 | DEFECT-002 | P2 | UI | ... | 1 | 1.2 |
| ... | | | | | | |
```

### 8.2 — Kategorilere Göre Özet

```
API Hataları (4xx/5xx):    __ adet (P1: __, P2: __, P3: __)
UI Hataları (JS error):    __ adet (P1: __, P2: __, P3: __)
Data Hataları (yanlış/eksik): __ adet (P1: __, P2: __, P3: __)
Traceability Kırıkları:   __ adet (P1: __, P2: __, P3: __)
UX İyileştirmeleri:        __ adet (P3: __)
Eksik Özellikler:          __ adet
```

### 8.3 — Fonksiyon Tamamlanma Matrisi

| Modül | Toplam Fonksiyon | Çalışan | Kırık | Eksik | Tamamlanma % |
|-------|-----------------|---------|-------|-------|-------------|
| Programs | | | | | |
| Projects | | | | | |
| Scenarios | | | | | |
| Process Hierarchy | | | | | |
| Workshops | | | | | |
| Requirements | | | | | |
| Open Items | | | | | |
| Backlog (WRICEF) | | | | | |
| Config Items | | | | | |
| FS/TS | | | | | |
| Test Cases | | | | | |
| Test Suites | | | | | |
| Test Execution | | | | | |
| Defects | | | | | |
| Traceability | | | | | |
| RAID | | | | | |
| Team Members | | | | | |
| Dashboard | | | | | |
| **TOPLAM** | | | | | **__%** |

### 8.4 — Traceability Tamamlanma

| Zincir | Beklenen Depth | Gerçek Depth | Status |
|--------|---------------|-------------|--------|
| Scenario → Defect | 6/6 | ? | ✅/❌ |
| Requirement → Test | 4/6 | ? | ✅/❌ |
| Backlog → Defect | 5/6 | ? | ✅/❌ |
| Defect → Scenario (reverse) | 6/6 | ? | ✅/❌ |

### 8.5 — Öncelikli Task Listesi (Sprint Planı İçin)

Defectleri öncelik sırasına göre task listesine dönüştür:

```
═══ P1 TASKS (Must Fix — Bu Sprint) ═══
[ ] TASK-001: [DEFECT-xxx] Başlık — Modül
[ ] TASK-002: [DEFECT-xxx] Başlık — Modül
...

═══ P2 TASKS (Should Fix — Sonraki Sprint) ═══
[ ] TASK-010: [DEFECT-xxx] Başlık — Modül
...

═══ P3 TASKS (Nice to Have — Backlog) ═══
[ ] TASK-020: [DEFECT-xxx] Başlık — Modül
...

═══ NEW FEATURE REQUESTS ═══
[ ] FEAT-001: Başlık — Modül — Açıklama
...
```

---

## ⚠️ EXECUTION NOTES

### Endpoint URL'leri Hakkında
Bu prompt'taki API path'leri mevcut bilgiye göre yazılmıştır. Gerçek path'ler farklıysa:
```bash
# Tüm route'ları listele
grep -rn "@.*_bp.route\|@app.route" app/blueprints/ app/__init__.py 2>/dev/null | head -50
# Veya
flask routes 2>/dev/null | head -50
```

### ID'ler Hakkında
`$PROJECT_ID`, `$WS_O2C_ID` gibi değişkenler her POST response'tan alınmalı. Copilot'a her adımda dönen ID'yi bir sonraki adımda kullanmasını söyle.

### Hata Durumunda
- 500 hatası → Stack trace'i kaydet (flask log veya response body)
- 404 hatası → Doğru URL'yi araştır
- 400 hatası → Request body'yi kontrol et, model alanlarını doğrula
- JS error → Console'daki tam hata mesajını kaydet

### Raporlama
Her BLOCK sonunda:
1. O BLOCK'ta bulunan tüm defectlerin listesi
2. Çalışan vs çalışmayan fonksiyonların özeti
3. Bir sonraki BLOCK'a geçmeden önce blocker var mı?

---

*Perga Full E2E Test Prompt — 2026-03-02*
*Versiyon: 1.0*
