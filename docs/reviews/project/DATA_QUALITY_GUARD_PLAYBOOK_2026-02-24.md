# Data Quality Guard Playbook (Story 5.2)

Date: 2026-02-24  
Mode: Report-only (no auto-fix)  
Owner: Data Governance + Platform Ops

## 1. Scope
Günlük çalışan guard job aşağıdaki bozulmaları raporlar:
1. `project_id IS NULL`
2. `project_id` invalid (projects tablosunda karşılığı yok)
3. `program_id` ile `project_id -> projects.program_id` uyuşmazlığı
4. `tenant_id` ile `project_id -> projects.tenant_id` cross-tenant anomalisi

## 2. Daily Job
Job adı: `data_quality_guard_daily`  
Default schedule: Her gün `03:30` (local scheduler config)

## 3. Alert Policy
1. Critical condition:
   - invalid `project_id` > 0
   - program/project mismatch > 0
   - cross-tenant anomaly > 0
2. Critical durumda `system/error` notification üretilir.

## 4. Triage Workflow
1. En son job sonucunu al:
   - `POST /api/v1/admin/scheduled-jobs/data_quality_guard_daily/run` (manual)
2. Etkilenen tabloları ve sample row’ları incele.
3. Önce owner ekip doğrulaması al (domain owner + platform owner).
4. Fix SQL’i önce dry-run (`SELECT`) ile doğrula.
5. Change window’da kontrollü `UPDATE` uygula.
6. Job’u tekrar çalıştır ve anomaly sıfırlanmasını doğrula.

## 5. Remediation SQL Templates
`<TABLE>` ve `<PK>` alanlarını job raporundaki tablo bilgisine göre değiştir.

1. Null project_id tespiti:
```sql
SELECT <PK>, tenant_id, program_id
FROM <TABLE>
WHERE project_id IS NULL;
```

2. Invalid project_id tespiti:
```sql
SELECT t.<PK>, t.tenant_id, t.program_id, t.project_id
FROM <TABLE> t
LEFT JOIN projects p ON p.id = t.project_id
WHERE t.project_id IS NOT NULL
  AND p.id IS NULL;
```

3. Program/project mismatch tespiti:
```sql
SELECT t.<PK>, t.program_id, p.program_id AS expected_program_id, t.project_id
FROM <TABLE> t
JOIN projects p ON p.id = t.project_id
WHERE t.program_id IS NOT NULL
  AND t.program_id <> p.program_id;
```

4. Cross-tenant anomaly tespiti:
```sql
SELECT t.<PK>, t.tenant_id, p.tenant_id AS expected_tenant_id, t.project_id
FROM <TABLE> t
JOIN projects p ON p.id = t.project_id
WHERE t.tenant_id IS NOT NULL
  AND t.tenant_id <> p.tenant_id;
```

5. Örnek kontrollü düzeltme (program bazında default project backfill):
```sql
UPDATE <TABLE> t
SET project_id = p.id
FROM projects p
WHERE t.project_id IS NULL
  AND p.program_id = t.program_id
  AND p.is_default = TRUE;
```

## 6. Exit Criteria
1. `critical_rows = 0`
2. `critical_tables = 0`
3. En az iki ardışık günlük çalışmada regresyon yok.

