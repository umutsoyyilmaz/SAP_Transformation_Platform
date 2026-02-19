# QMetry Test Management — Competitive Analysis

> **Tarih:** 2026-02-19  
> **Amaç:** QMetry TM ürününü analiz ederek SAP Transformation Platform Test Management modülünü aynı seviye/ölçeğe taşımak için gap tespiti ve yol haritası belirlemek.

---

## 1. QMetry Ürün Profili

| Boyut | Detay |
|-------|-------|
| **Sahip** | SmartBear Software (2024 satın alma) |
| **Deployment** | Cloud + On-Premise (EU hosted — GDPR uyumlu) |
| **Ölçek** | 10 – 10.000+ kullanıcı; milyonlarca test case |
| **Pricing** | Enterprise / Enterprise Plus (e-signature, advanced rapor ayrı tier) |
| **Hedef** | TestRail alternatifi; kurumsal QA takımları |
| **AI Odağı** | QQBot — test case üretimi, flaky detection, smart suite optimization, root-cause analysis |

---

## 2. QMetry Yetenek Haritası (Feature Matrix)

### 2.1 Test Authoring
- BDD/Gherkin sync (Git, SVN, GitLab, BitBucket)
- Paylaşılabilir (shareable) test step'leri — cross-project reuse
- Test data parametrization (data-driven testing)
- AI ile requirement'tan otomatik test case üretimi
- Duplicate/matching test case tespiti (AI)
- Custom field'lar — tüm modüllerde

### 2.2 Test Case Management
- Multi-version test case'ler + versiyon karşılaştırması
- Arşivleme, klonlama, toplu silme
- Hiyerarşik klasör yapısı (nested folders)
- Custom layout/template desteği
- Test case sharing across projects

### 2.3 Test Execution
- 2 farklı execution görünümü (list + detail)
- Test suite bazlı execution — folder hierarchy'li
- Bulk operation (toplu atama, toplu durum)
- Platform/environment binding per suite
- Bi-directional sync (dış platformlarla)
- Otomasyon sonucu import (Selenium, TestNG, Cucumber, Robot FW)

### 2.4 Test Planning & Cycles
- Release/Sprint bazlı planlama
- Cycle management — populate, carry-forward

### 2.5 Traceability
- Requirement → TC → Execution → Defect uçtan uca izlenebilirlik
- Story-level TC görüntüleme (Jira panel'de)
- Traceability raporları

### 2.6 AI Özellikleri
| AI Feature | Açıklama |
|-----------|----------|
| Auto Test Case Generation | User story/requirement/acceptance criteria'dan TC üretimi |
| Duplicate/Matching Detection | AI ile repo'daki benzer/aynı TC'leri bulma |
| Flaky Test Detection | Kararsız testleri tespit etme |
| Predictive Test Coverage | Defect-prone alanları tahmin |
| Smart Suite Optimization | Risk/değişiklik bazlı çalıştırma önceliği |
| Root Cause Analysis | Hata kök neden analizi |
| AI-Powered Search | Natural language arama |
| Automated Test Maintenance | TC'leri otomatik güncelleme |

### 2.7 Reporting & Dashboard
- 140+ hazır rapor
- Custom SQL reporting
- Personalize edilebilir dashboard gadget'ları
- Real-time KPI visibility
- Email ile rapor paylaşımı
- Drill-down analytics
- Traceability/coverage raporları
- PDF export (audit/compliance kanıtı)

### 2.8 Compliance & Governance
- 21 CFR Part 11 uyumluluk
- Multi-level e-signature/approval workflow
- Forced approval akışı (authoring + execution)
- Tam audit trail — tüm aşamalar e-signed
- Export to PDF for compliance evidence

### 2.9 Entegrasyon Ekosistemi
- **Project Tracking:** Jira (deep), Azure DevOps, Rally
- **CI/CD:** Jenkins, Bamboo, CircleCI, BitBucket Pipelines, GitHub Actions
- **Automation:** Selenium, TestNG, JUnit, Cucumber, Robot Framework
- **VCS:** Git, SVN, GitLab, BitBucket
- **Device Cloud:** BrowserStack, SauceLabs, LambdaTest
- **Other:** Confluence, Slack, REST API (150+ endpoints)

### 2.10 Exploratory Testing
- Dedicated plugin — investigation over documentation
- Session-based test management (SBTM)
- Screenshot/evidence capture inline

---

## 3. Competitive Gap Analysis — QMetry vs. SAP Transformation Platform

### 3.1 GAP Matrisi

| # | Yetenek | QMetry | Biz (Mevcut) | GAP Seviyesi |
|---|---------|--------|-------------|-------------|
| 1 | Test Case CRUD | ✅ Full | ✅ Full | — |
| 2 | Test Steps CRUD | ✅ Full | ✅ Full | — |
| 3 | Test Suite Management | ✅ Hierarchical folders | ✅ Flat (M:N links) | 🟡 Medium |
| 4 | Test Plan/Cycle | ✅ Full | ✅ Full | — |
| 5 | Test Execution | ✅ 2 views + bulk | ✅ Basic (single view) | 🟡 Medium |
| 6 | Step-level Execution | ✅ Full | ✅ Full | — |
| 7 | Defect Management | ✅ Full + SLA | ✅ Full + SLA + FSM | — |
| 8 | Traceability | ✅ Req→TC→Exec→Defect | ✅ Deep (L1→L4→TC→Defect) | ✅ Advantage |
| 9 | UAT Sign-Off | ❌ No native | ✅ Native | ✅ Advantage |
| 10 | Cutover/Hypercare Test | ❌ No | ✅ Native | ✅ Advantage |
| 11 | SAP Process Ontology | ❌ No | ✅ L1→L4 + Tcode | ✅ Advantage |
| 12 | Data Factory Integration | ❌ No | ✅ Data sets linked | ✅ Advantage |
| 13 | **TC Versioning + Diff** | ✅ Full | ❌ Field only | 🔴 Critical |
| 14 | **AI TC Generation** | ✅ Advanced | 🟡 Basic generator | 🟡 Medium |
| 15 | **AI Flaky Detection** | ✅ Full | ❌ None | 🔴 Critical |
| 16 | **AI Smart Suite Opt.** | ✅ Full | ❌ None | 🔴 Critical |
| 17 | **AI Predictive Coverage** | ✅ Full | ❌ None | 🔴 Critical |
| 18 | **AI Root Cause Analysis** | ✅ Full | 🟡 Defect triage | 🟡 Medium |
| 19 | **AI Smart Search** | ✅ NLQ | ❌ None | 🔴 Critical |
| 20 | **BDD/Gherkin Support** | ✅ Deep | ❌ None | 🟡 Medium |
| 21 | **Shareable Steps** | ✅ Cross-project | ❌ None | 🟡 Medium |
| 22 | **Data Parametrization** | ✅ Full | ❌ None | 🟡 Medium |
| 23 | **Hierarchical Folders** | ✅ Nested | ❌ Flat | 🟡 Medium |
| 24 | **Bulk Operations** | ✅ Full | ❌ Limited | 🟡 Medium |
| 25 | **Approval Workflow** | ✅ e-Signature | ❌ None | 🔴 Critical |
| 26 | **Custom Reporting Engine** | ✅ SQL + Gadgets | ❌ Fixed dashboard | 🔴 Critical |
| 27 | **Dashboard Gadgets** | ✅ Configurable | ❌ Fixed | 🔴 Critical |
| 28 | **PDF Export** | ✅ Compliance | ❌ None | 🟡 Medium |
| 29 | **Exploratory Testing** | ✅ Plugin | ❌ None | 🟡 Medium |
| 30 | **External Integrations** | ✅ 20+ connectors | ❌ API only | 🟡 Medium |
| 31 | **Custom Fields** | ✅ All modules | ❌ None | 🟡 Medium |
| 32 | **Multi-Project Reuse** | ✅ Cross-project | ❌ Program-scoped | 🟡 Medium |

### 3.2 Bizim Stratejik Avantajlarımız

| # | Avantaj | QMetry'de Durumu |
|---|---------|-----------------|
| 1 | SAP Activate faz entegrasyonu (Discover→Run) | Yok |
| 2 | L1→L4 süreç hiyerarşisi + scope tracing | Yok |
| 3 | WRICEF/Config Item → TC auto-generation | Yok |
| 4 | Cutover rehearsal test layer | Yok |
| 5 | Hypercare SLA + Go/No-Go scorecard | Yok |
| 6 | Test Data Factory (data set → TC binding) | Yok |
| 7 | 9-state defect lifecycle FSM + SLA matrix | Basit lifecycle |
| 8 | TestCaseTraceLink (L3 trace group) | Yok |
| 9 | Requirement lifecycle → TC auto-suggest | Yok |
| 10 | UAT sign-off per process area | Yok |

---

## 4. Sonuç

QMetry, **genel amaçlı kurumsal test yönetiminde** geniş yetenek seti sunan, AI ve compliance odaklı bir enterprise üründür. Ancak **SAP transformasyonuna özgü süreç ontolojisi, cutover/hypercare entegrasyonu ve scope tracing** yetenekleri bulunmaz — bu bizim stratejik hendeğimizdir.

**Öncelik sırası:** QMetry pariteye ulaşmak için en kritik 7 gap: TC Versioning, AI Test Authoring pipeline, Approval Workflow, Smart Search, Reporting Engine, Dashboard Gadgets ve Flaky Detection. Bu gap'lerin kapatılması hem feature-parity hem enterprise-readiness için gereklidir.

---

*Detaylı uygulama planı: [TEST-MANAGEMENT-MASTER-PLAN.md](TEST-MANAGEMENT-MASTER-PLAN.md)*
