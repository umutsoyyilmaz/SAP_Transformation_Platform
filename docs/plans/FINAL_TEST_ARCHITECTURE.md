# 🏗️ PERGA — Final Test Architecture (ADR-FINAL)

**Date:** 2026-02-17  
**Author:** Claude (Architecture Decision)  
**Status:** PROPOSAL — Umut onayı bekleniyor  
**Problem:** L3/WRICEF → SIT bağlantısı çözülemiyor, execution yapısı karmaşık

---

## ASIL PROBLEM

Şu soruyu cevaplayamıyorsun:

> "SIT planım var. MM modülündeki L3 process'leri test etmek istiyorum. Hangi test case'ler lazım?"

Çünkü mevcut yol:

```
L3 Process ──→ RequirementProcessMapping ──→ ExploreRequirement ──→ BacklogItem ──→ TestCase
     │                  │                          │                     │             │
   Tablo 1           Tablo 2                    Tablo 3              Tablo 4        Tablo 5
                                                  ↑
                                          Conversion Engine YOK!
                                          (ExploreReq → BacklogItem
                                           otomatik dönüşüm eksik)
```

**4 hop, 5 tablo, 3 farklı FK pattern, ortadaki köprü (Conversion Engine) fiilen yok.**

---

## ÇÖZÜM: İKİ KATMANLI MİMARİ

### Katman 1: TestCase Üzerindeki Direkt FK'lar (Zaten Var!)

TestCase modelinde şu FK'lar **zaten mevcut**:

```python
class TestCase:
    requirement_id   = FK → requirements        # "Bu TC hangi Requirement'ı test ediyor?"
    backlog_item_id  = FK → backlog_items        # "Bu TC hangi WRICEF'i test ediyor?"
    config_item_id   = FK → config_items         # "Bu TC hangi Config'i test ediyor?"
    process_level_id = FK → process_levels       # "Bu TC hangi L3/L4'ü test ediyor?"
    explore_requirement_id = FK → explore_req... # "Bu TC hangi Workshop Req'ini test ediyor?"
```

**Problem:** Bu FK'lar var ama çoğu boş (populated değil).

**Çözüm:** TC oluşturulurken veya import edilirken bu FK'lar **mutlaka doldurulmalı**. 
Özellikle `process_level_id` → SIT'te L3 bazlı TC bulmak için yeterli.

### Katman 2: PlanScope (Yeni — Plan Seviyesinde Kapsam Tanımı)

PlanScope = "Bu SIT planı neyi kapsıyor?" sorusunun cevabı.

```python
class PlanScope:
    plan_id      = FK → test_plans
    source_type  = "process_l3" | "scenario" | "requirement" | "backlog_item" | "config_item"
    source_id    = Integer (hangi L3, hangi scenario, hangi WRICEF)
    source_code  = "MM-030" (denormalized — hız için)
    source_title = "Purchase Order Processing" (denormalized)
```

**Bağlantı TEK SORGU:**

```sql
-- "SIT planımdaki L3 process'ler için hangi TC'ler var?"
SELECT tc.* FROM test_cases tc
JOIN plan_scopes ps ON ps.plan_id = :plan_id
WHERE ps.source_type = 'process_l3'
  AND tc.process_level_id = ps.source_id

-- "SIT planımdaki WRICEF'ler için hangi TC'ler var?"  
SELECT tc.* FROM test_cases tc
JOIN plan_scopes ps ON ps.plan_id = :plan_id
WHERE ps.source_type = 'backlog_item'
  AND tc.backlog_item_id = ps.source_id
```

**Hop sayısı: 1.** Tek JOIN. Karmaşık traversal yok.

---

## FİNAL HİYERARŞİ AĞACI

```
Program
 └── TestPlan (SIT / UAT / Regression / Performance / E2E / Cutover)
      │
      ├── PlanScope[] ←────── "Plan neyi kapsıyor?"
      │    ├── source_type: process_l3  →  MM-030 Purchase Order Processing
      │    ├── source_type: process_l3  →  SD-010 Sales Order Management  
      │    ├── source_type: scenario    →  O2C Order-to-Cash
      │    └── source_type: backlog_item → ENH-009 Custom Pricing Logic
      │
      ├── PlanTestCase[] ←─── "Plan'da hangi TC'ler var?"
      │    │   (PlanScope'tan suggest edilir VEYA manual eklenir VEYA suite'ten import edilir)
      │    ├── TC-MM-001 → process_level_id = MM-030
      │    ├── TC-MM-002 → process_level_id = MM-030
      │    ├── TC-SD-001 → process_level_id = SD-010
      │    └── TC-ENH-009-UT → backlog_item_id = ENH-009
      │
      ├── PlanDataSet[] ←──── "Plan hangi test verisini kullanıyor?"
      │    └── DS-001 MM Master Data (mandatory)
      │
      └── TestCycle[] ←────── "Ne zaman, hangi ortamda koşulacak?"
           ├── SIT-Cycle-1 (environment: QAS, build_tag: TR-2026-W08)
           │    └── TestExecution[] ←── Cycle × TC = 1 satır
           │         ├── TC-MM-001 → Pass ✅
           │         ├── TC-MM-002 → Fail ❌ → Defect DEF-017
           │         ├── TC-SD-001 → Blocked 🚫
           │         └── TC-ENH-009-UT → Pass ✅
           │
           └── SIT-Cycle-2 (carry forward: failed + blocked from Cycle-1)
                └── TestExecution[]
                     ├── TC-MM-002 → Pass ✅ (retest)
                     └── TC-SD-001 → Pass ✅ (unblocked)
```

---

## EXECUTION MİMARİSİ (Dual System Çözümü)

### Mevcut Durum (Problem)

```
TestExecution (legacy) = Cycle × TC = 1 satır, flat pass/fail
    Dashboard bunu okuyor ✅
    Governance bunu okuyor ✅

TestRun + TestStepResult (yeni) = Granular step-level sonuç
    Dashboard bunu OKUMUYOR ❌
    Governance bunu OKUMUYOR ❌
```

### Çözüm: TestExecution Ana Kayıt, TestStepResult Altında

```
TestCycle (SIT-1)
 └── TestExecution (Cycle × TC = 1 satır)    ← Dashboard + Governance BUNU okur
      │  result: pass / fail / blocked / not_run
      │  executed_by: "Ayşe"
      │  executed_at: 2026-02-17T14:30
      │  attempt_number: 1               ← kaçıncı deneme (retest tracking)
      │
      └── TestStepResult[] (opsiyonel granular detay)
           ├── Step 1: "Login SAP" → pass
           ├── Step 2: "Create PO" → pass  
           ├── Step 3: "Approve PO" → fail  ← defect buradan açılır
           └── Step 4: "GR" → not_run (blocked by step 3)
```

**Kurallar:**
1. `TestExecution.result` = **tek kaynak (Single Source of Truth)**
2. Dashboard, coverage, go/no-go → hep `TestExecution` tablosunu sorgular
3. `TestStepResult` opsiyonel — step bazlı detay gerektiğinde doldurulur
4. `TestStepResult` var ise, `TestExecution.result` otomatik türetilebilir:
   - Tüm step'ler pass → execution pass
   - Herhangi step fail → execution fail
   - Herhangi step blocked (fail yok) → execution blocked

**TestRun ne olur?**
TestRun **kaldırılmaz** ama rolü değişir:
- TestRun = "Kim, ne zaman, hangi attempt, hangi ortamda çalıştırdı" metadata container
- TestExecution.test_run_id (nullable FK) → opsiyonel bağlantı
- TestRun OLMADAN da TestExecution çalışabilir (legacy uyumluluk)

---

## SUITE KONUSU

ChatGPT "Suite'i kaldır" dedi. **Katılmıyorum.**

```
Suite ≠ Plan Type

Suite = "MM Procurement Test Cases" (fonksiyonel katalog grubu, yeniden kullanılabilir)
Plan Type = "SIT" (test fazı)

Aynı Suite birden fazla Plan'da kullanılabilir:
  - "MM Procurement TCs" suite'i → SIT Plan'da da var, UAT Plan'da da var
  - SIT Plan'da priority=high, UAT Plan'da priority=medium (PlanTestCase ile farklılaşır)
```

**Suite kalır, ama rolü net:**
- Suite = TC organizasyon klasörü (reusable catalog)
- PlanTestCase = Plan'a özel TC seçimi (plan-specific metadata)
- İkisi farklı abstraction level'ları

---

## KULLANICI AKIŞI: "SIT Planı Oluştur"

```
ADIM 1: Plan oluştur
  └── "SIT Plan — Wave 1" (plan_type: sit)

ADIM 2: Scope tanımla (PlanScope)
  └── "Bu SIT neyi kapsıyor?"
       ├── + Add L3 Process → "MM-030 Purchase Order" 
       ├── + Add L3 Process → "SD-010 Sales Order"
       └── + Add WRICEF → "ENH-009 Custom Pricing"

ADIM 3: TC Pool oluştur (PlanTestCase)
  └── 3 yöntem:
       ├── [Suggest from Scope] → Sistem L3/WRICEF FK'larından TC'leri bulur
       │    "MM-030 için 5 TC buldum, SD-010 için 3 TC, ENH-009 için 1 TC"
       │    → Onayla / Reddet
       ├── [Import from Suite] → "MM Procurement" suite'ini seç → 12 TC import et
       └── [Manual Add] → Katalogdan TC seç

ADIM 4: Cycle oluştur (TestCycle)
  └── "SIT-Cycle-1" (environment: QAS, build_tag: TR-2026-W08)

ADIM 5: Populate et
  └── Plan'daki TC Pool → Cycle'a TestExecution kayıtları oluştur
       Her TC için 1 TestExecution (result: not_run, assigned_to: planned_tester)

ADIM 6: Execute et
  └── Tester açar → TC-MM-001 → pass/fail/blocked girer
       (Opsiyonel: step-by-step TestStepResult da girebilir)

ADIM 7: Governance
  └── Coverage: 9/9 TC çalıştı → %100
       Pass Rate: 7/9 pass → %78
       → Go/No-Go: ❌ (< %95 threshold)
       → Carry Forward: failed 2 TC → SIT-Cycle-2'ye taşı
```

---

## suggest_test_cases() SERVİS MANTIĞI

Bu fonksiyon PlanScope'taki her item için TC'leri bulur:

```python
def suggest_test_cases(plan_id):
    """
    PlanScope'taki her scope item için ilgili TC'leri öner.
    Direkt FK kullanır — karmaşık traversal YOK.
    """
    scopes = PlanScope.query.filter_by(plan_id=plan_id).all()
    suggestions = []
    
    for scope in scopes:
        tcs = []
        
        if scope.source_type == 'process_l3':
            # Direkt: TC.process_level_id = scope.source_id
            tcs = TestCase.query.filter_by(process_level_id=scope.source_id).all()
            
        elif scope.source_type == 'backlog_item':
            # Direkt: TC.backlog_item_id = scope.source_id
            tcs = TestCase.query.filter_by(backlog_item_id=scope.source_id).all()
            
        elif scope.source_type == 'config_item':
            # Direkt: TC.config_item_id = scope.source_id
            tcs = TestCase.query.filter_by(config_item_id=scope.source_id).all()
            
        elif scope.source_type == 'requirement':
            # Direkt: TC.requirement_id = scope.source_id
            tcs = TestCase.query.filter_by(requirement_id=scope.source_id).all()
            
            # BONUS: Requirement'ın WRICEF'leri üzerinden de bul
            req = ExploreRequirement.query.get(scope.source_id)
            if req and req.backlog_item_id:
                wricef_tcs = TestCase.query.filter_by(
                    backlog_item_id=req.backlog_item_id
                ).all()
                tcs.extend(wricef_tcs)
                
        elif scope.source_type == 'scenario':
            # Scenario'nun tüm L3'leri → TC'ler
            processes = Process.query.filter_by(
                scenario_id=scope.source_id, level=3
            ).all()
            for p in processes:
                p_tcs = TestCase.query.filter_by(process_level_id=p.id).all()
                tcs.extend(p_tcs)
        
        # Deduplicate
        seen = set()
        for tc in tcs:
            if tc.id not in seen:
                seen.add(tc.id)
                suggestions.append({
                    'scope_item': scope.source_code,
                    'scope_type': scope.source_type,
                    'test_case_id': tc.id,
                    'test_case_code': tc.code,
                    'test_case_title': tc.title,
                    'test_layer': tc.test_layer,
                })
    
    return suggestions
```

**Neden basit?** Çünkü TC üzerindeki direkt FK'ları kullanıyoruz. Traversal yok.

---

## ÖN KOŞUL: TC FK'LARI DOLU OLMALI

Bu mimarinin çalışması için **TC oluşturulurken FK'lar doldurulmalı:**

| TC Oluşturma Yöntemi | Hangi FK Dolar |
|----------------------|----------------|
| generate-from-wricef | `backlog_item_id` = kaynak WRICEF |
| generate-from-process | `process_level_id` = kaynak L3/L4 |
| generate-from-config | `config_item_id` = kaynak Config |
| Manual oluşturma | UI'da kullanıcı seçer |
| Suite'ten import | Kaynak TC'nin FK'ları kopyalanır |

**Mevcut TC'ler FK'sız ise?** Batch güncelleme yapılır veya Coverage Dashboard'da uyarı gösterilir: "⚠️ 12 TC'nin L3 bağlantısı yok — coverage hesaplanamıyor"

---

## CHATGPT İLE FARKLARIM

| Konu | ChatGPT Diyor | Ben Diyorum | Neden |
|------|---------------|-------------|-------|
| Cycle kaldır | ✅ Kaldır, Run yap | ❌ Cycle kalır | SAP Cloud ALM, Tricentis hep Cycle kullanır. PM "SIT Cycle 2 pass rate?" sorar |
| Suite kaldır | ✅ Kaldır | ❌ Kalır, rolü net | Suite = reusable catalog, Plan Type = test fazı. Farklı abstraction |
| Dual execution | ✅ Birleştir | ✅ Birleştir — ama farklı şekilde | TestExecution SSOT kalır, TestStepResult altına taşınır |
| Run kaldır | ✅ Kaldır | ❌ Opsiyonel metadata olarak kalır | Retest tracking için gerekli |
| %80 doğru | ✅ | ✅ Katılıyorum | Ama %20 fark SAP domain bilgisi gerektiriyor |

---

## ÖZET: 3 YAPILACAK ŞEY

### 1. TestCase FK'larını Doldur (Ön koşul)
- `generate-from-wricef` → `backlog_item_id` otomatik doldursun
- `generate-from-process` → `process_level_id` otomatik doldursun
- Manual TC oluşturmada → UI'da L3/WRICEF seçtir

### 2. PlanScope Ekle (Yeni Tablo)
- TestPlan'a scope tanımlama özelliği ekle
- `suggest_test_cases()` servisi ile TC önerisi yap
- Direkt FK sorgusu — tek JOIN — karmaşık traversal yok

### 3. Execution Birleştir
- TestExecution = SSOT (Dashboard + Governance bunu okur)
- TestStepResult → TestExecution'a bağlı (TestRun'dan kopar)
- TestRun → opsiyonel metadata (attempt tracking)

---

## MODEL DEĞİŞİKLİKLERİ

```
DEĞİŞEN:
  TestStepResult.test_execution_id = FK → test_executions (ÖNCEKİ: test_run_id)
  TestExecution.attempt_number = Integer (YENİ alan)
  TestExecution.test_run_id = FK → test_runs (nullable, opsiyonel)

EKLENEN:
  PlanScope (yeni tablo)
  PlanTestCase (yeni tablo)  
  PlanDataSet (yeni tablo)
  TestDataSet + TestDataSetItem (yeni tablolar)

DEĞİŞMEYEN:
  TestPlan, TestCycle, TestSuite, TestCase, TestStep
  TestRun (kalır, opsiyonel)
  Defect, DefectComment, DefectHistory, DefectLink
  UATSignOff
```
