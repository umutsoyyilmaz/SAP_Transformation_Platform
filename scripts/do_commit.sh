#!/bin/bash
cd /Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main
git add -A
git commit -m "fix: single source of truth - link ScopeItem to Requirement bidirectionally

- Add requirement_id FK to scope_items table (migration d1a4e571c168)
- doAddRequirement creates both Requirement + ScopeItem + Analysis
- Requirements page shows linked scope items count and detail
- Scope item detail shows linked requirement cross-link
- 3XX Pricing Line now visible as REQ-SD-003 on Requirements page
- All 425 tests pass"
