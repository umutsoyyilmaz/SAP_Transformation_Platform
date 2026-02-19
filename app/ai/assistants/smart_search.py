"""
F4 — Smart Search Assistant.

Natural language → structured query → SQL filter → ranked results.

Pipeline:
  1. NLQ parse: extract module, test_layer, result, date_range, keywords
  2. Query builder: construct SQLAlchemy filters
  3. Execute + rank by relevance
  4. Optional LLM-powered summary
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_

from app.models import db
from app.models.testing import TestCase, TestExecution, Defect

logger = logging.getLogger(__name__)

# ── Query term mapping (extension of NLQueryAssistant glossary) ──────────

TERM_MAP = {
    # Modules
    "fi": "FI", "co": "CO", "sd": "SD", "mm": "MM", "pp": "PP",
    "hr": "HR", "hcm": "HCM", "qm": "QM", "pm": "PM", "wm": "WM",
    "ewm": "EWM", "ps": "PS", "basis": "BASIS", "abap": "ABAP",
    # Results
    "pass": "pass", "passed": "pass", "fail": "fail", "failed": "fail",
    "blocked": "blocked", "deferred": "deferred", "not_run": "not_run",
    # Layers
    "unit": "unit", "sit": "sit", "uat": "uat",
    "regression": "regression", "performance": "performance",
    "integration": "sit",
    # Status
    "draft": "draft", "ready": "ready", "approved": "approved",
    "deprecated": "deprecated", "submitted": "submitted",
    # Priorities
    "critical": "Critical", "high": "High", "medium": "Medium", "low": "Low",
    # Turkish aliases
    "başarılı": "pass", "başarısız": "fail", "engelli": "blocked",
    "son": "recent", "hafta": "week", "gün": "day", "ay": "month",
}

DATE_PATTERNS = [
    (r"last\s+(\d+)\s*days?|son\s+(\d+)\s*gün", "days"),
    (r"last\s+(\d+)\s*weeks?|son\s+(\d+)\s*hafta", "weeks"),
    (r"last\s+(\d+)\s*months?|son\s+(\d+)\s*ay", "months"),
]


class SmartSearch:
    """Natural language test management search engine."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag

    def search(self, query: str, program_id: int, *, limit: int = 50) -> dict:
        """Parse natural language query and return matching entities."""
        parsed = self._parse_query(query)
        results = self._execute(parsed, program_id, limit)
        return {
            "query": query,
            "parsed": parsed,
            "results": results,
            "count": len(results),
        }

    def _parse_query(self, query: str) -> dict:
        """Extract structured filters from natural language."""
        q = query.lower().strip()
        parsed = {
            "modules": [],
            "layers": [],
            "results": [],
            "statuses": [],
            "priorities": [],
            "date_range_days": None,
            "keywords": [],
            "entity_type": "test_case",  # default
        }

        # Detect entity type
        if any(w in q for w in ("defect", "bug", "hata", "kusur")):
            parsed["entity_type"] = "defect"
        elif any(w in q for w in ("execution", "run", "çalıştırma", "yürütme")):
            parsed["entity_type"] = "execution"

        # Extract date ranges
        for pattern, unit in DATE_PATTERNS:
            m = re.search(pattern, q)
            if m:
                val = int(m.group(1) or m.group(2))
                if unit == "weeks":
                    val *= 7
                elif unit == "months":
                    val *= 30
                parsed["date_range_days"] = val
                break

        # Token-based extraction
        tokens = re.findall(r'[a-zA-ZçğıöşüÇĞİÖŞÜ_]+', q)
        for token in tokens:
            mapped = TERM_MAP.get(token)
            if not mapped:
                continue
            if mapped in ("FI", "CO", "SD", "MM", "PP", "HR", "HCM", "QM", "PM", "WM", "EWM", "PS", "BASIS", "ABAP"):
                parsed["modules"].append(mapped)
            elif mapped in ("pass", "fail", "blocked", "deferred", "not_run"):
                parsed["results"].append(mapped)
            elif mapped in ("unit", "sit", "uat", "regression", "performance"):
                parsed["layers"].append(mapped)
            elif mapped in ("draft", "ready", "approved", "deprecated", "submitted"):
                parsed["statuses"].append(mapped)
            elif mapped in ("Critical", "High", "Medium", "Low"):
                parsed["priorities"].append(mapped)

        # Extract remaining keywords (not mapped)
        noise = set(TERM_MAP.keys()) | {"the", "in", "of", "for", "with", "and", "or", "a", "an",
                                         "test", "case", "cases", "tests", "olan", "ve", "ile",
                                         "modülü", "modül", "olan", "olmayan", "tüm", "all", "list",
                                         "show", "find", "search", "göster", "bul", "ara"}
        parsed["keywords"] = [t for t in tokens if t not in noise and len(t) > 2]

        return parsed

    def _execute(self, parsed: dict, program_id: int, limit: int) -> list:
        """Execute parsed query against the database."""
        entity = parsed["entity_type"]

        if entity == "defect":
            return self._search_defects(parsed, program_id, limit)
        elif entity == "execution":
            return self._search_executions(parsed, program_id, limit)
        return self._search_test_cases(parsed, program_id, limit)

    def _search_test_cases(self, p: dict, pid: int, limit: int) -> list:
        q = TestCase.query.filter_by(program_id=pid)
        if p["modules"]:
            q = q.filter(TestCase.module.in_(p["modules"]))
        if p["layers"]:
            q = q.filter(TestCase.test_layer.in_(p["layers"]))
        if p["statuses"]:
            q = q.filter(TestCase.status.in_(p["statuses"]))
        if p["priorities"]:
            q = q.filter(TestCase.priority.in_(p["priorities"]))
        if p["keywords"]:
            kw_filters = [TestCase.title.ilike(f"%{kw}%") for kw in p["keywords"]]
            q = q.filter(or_(*kw_filters))
        if p["date_range_days"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=p["date_range_days"])
            q = q.filter(TestCase.updated_at >= cutoff)

        rows = q.order_by(TestCase.updated_at.desc()).limit(limit).all()
        return [tc.to_dict() for tc in rows]

    def _search_defects(self, p: dict, pid: int, limit: int) -> list:
        q = Defect.query.filter_by(program_id=pid)
        if p["modules"]:
            q = q.filter(Defect.module.in_(p["modules"]))
        if p["results"]:  # map to severity
            pass  # defects don't have "result"
        if p["priorities"]:
            q = q.filter(Defect.priority.in_(p["priorities"]))
        if p["keywords"]:
            kw_filters = [Defect.title.ilike(f"%{kw}%") for kw in p["keywords"]]
            q = q.filter(or_(*kw_filters))
        if p["date_range_days"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=p["date_range_days"])
            q = q.filter(Defect.created_at >= cutoff)

        rows = q.order_by(Defect.created_at.desc()).limit(limit).all()
        return [d.to_dict() for d in rows]

    def _search_executions(self, p: dict, pid: int, limit: int) -> list:
        q = TestExecution.query.join(TestCase).filter(TestCase.program_id == pid)
        if p["modules"]:
            q = q.filter(TestCase.module.in_(p["modules"]))
        if p["layers"]:
            q = q.filter(TestCase.test_layer.in_(p["layers"]))
        if p["results"]:
            q = q.filter(TestExecution.result.in_(p["results"]))
        if p["date_range_days"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=p["date_range_days"])
            q = q.filter(TestExecution.executed_at >= cutoff)

        rows = q.order_by(TestExecution.executed_at.desc()).limit(limit).all()
        return [e.to_dict() for e in rows]
