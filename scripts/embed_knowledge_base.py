#!/usr/bin/env python3
"""
SAP Knowledge Base — Embedding Script (Sprint 7, Task 7.9).

Indexes existing entities into the ai_embeddings table for RAG retrieval.
Uses the RAGPipeline.index_entity() method to chunk, embed, and store vectors.

Supports:
  - Requirements, Scenarios, BacklogItems, ConfigItems
  - TestCases, Defects, Risks, Decisions, Issues, Actions
  - Phases, Gates, Processes, ScopeItems, Analyses

Usage:
    python scripts/embed_knowledge_base.py                  # Index all entities
    python scripts/embed_knowledge_base.py --entity-types requirement,risk
    python scripts/embed_knowledge_base.py --program-id 1   # Filter by program
    python scripts/embed_knowledge_base.py --clear           # Clear embeddings first
"""

import argparse
import sys
import time

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.ai import AIEmbedding

# ── Entity registry ──────────────────────────────────────────────────────
# Each entry: (entity_type_key, Model class path, text builder function)


def _build_requirement_text(r):
    parts = [f"Requirement: {r.title or ''}"]
    if r.code:
        parts.append(f"Code: {r.code}")
    if r.req_type:
        parts.append(f"Type: {r.req_type}")
    if r.fit_gap:
        parts.append(f"Fit/Gap: {r.fit_gap}")
    if r.module:
        parts.append(f"Module: {r.module}")
    if r.description:
        parts.append(f"Description: {r.description}")
    if r.acceptance_criteria:
        parts.append(f"Acceptance Criteria: {r.acceptance_criteria}")
    if r.notes:
        parts.append(f"Notes: {r.notes}")
    return "\n".join(parts)


def _build_scenario_text(s):
    parts = [f"Scenario: {s.name or ''}"]
    if s.scenario_type:
        parts.append(f"Type: {s.scenario_type}")
    if s.risk_level:
        parts.append(f"Risk Level: {s.risk_level}")
    if s.description:
        parts.append(f"Description: {s.description}")
    if s.pros:
        parts.append(f"Pros: {s.pros}")
    if s.cons:
        parts.append(f"Cons: {s.cons}")
    if s.assumptions:
        parts.append(f"Assumptions: {s.assumptions}")
    if s.recommendation:
        parts.append(f"Recommendation: {s.recommendation}")
    return "\n".join(parts)


def _build_backlog_item_text(b):
    parts = [f"Backlog Item: {b.title or ''}"]
    if hasattr(b, 'item_type') and b.item_type:
        parts.append(f"Type: {b.item_type}")
    if hasattr(b, 'priority') and b.priority:
        parts.append(f"Priority: {b.priority}")
    if b.description:
        parts.append(f"Description: {b.description}")
    if hasattr(b, 'acceptance_criteria') and b.acceptance_criteria:
        parts.append(f"Acceptance Criteria: {b.acceptance_criteria}")
    if hasattr(b, 'technical_notes') and b.technical_notes:
        parts.append(f"Technical Notes: {b.technical_notes}")
    return "\n".join(parts)


def _build_config_item_text(c):
    parts = [f"Config Item: {c.title or ''}"]
    if c.description:
        parts.append(f"Description: {c.description}")
    if hasattr(c, 'acceptance_criteria') and c.acceptance_criteria:
        parts.append(f"Acceptance Criteria: {c.acceptance_criteria}")
    if hasattr(c, 'notes') and c.notes:
        parts.append(f"Notes: {c.notes}")
    return "\n".join(parts)


def _build_test_case_text(tc):
    parts = [f"Test Case: {tc.title or ''}"]
    if tc.description:
        parts.append(f"Description: {tc.description}")
    if hasattr(tc, 'preconditions') and tc.preconditions:
        parts.append(f"Preconditions: {tc.preconditions}")
    if hasattr(tc, 'test_steps') and tc.test_steps:
        parts.append(f"Test Steps: {tc.test_steps}")
    if hasattr(tc, 'expected_result') and tc.expected_result:
        parts.append(f"Expected Result: {tc.expected_result}")
    return "\n".join(parts)


def _build_defect_text(d):
    parts = [f"Defect: {d.title or ''}"]
    if hasattr(d, 'severity') and d.severity:
        parts.append(f"Severity: {d.severity}")
    if d.description:
        parts.append(f"Description: {d.description}")
    if hasattr(d, 'steps_to_reproduce') and d.steps_to_reproduce:
        parts.append(f"Steps to Reproduce: {d.steps_to_reproduce}")
    if hasattr(d, 'root_cause') and d.root_cause:
        parts.append(f"Root Cause: {d.root_cause}")
    if hasattr(d, 'resolution') and d.resolution:
        parts.append(f"Resolution: {d.resolution}")
    return "\n".join(parts)


def _build_risk_text(r):
    parts = [f"Risk: {r.title or ''}"]
    if hasattr(r, 'category') and r.category:
        parts.append(f"Category: {r.category}")
    if r.description:
        parts.append(f"Description: {r.description}")
    if hasattr(r, 'mitigation_plan') and r.mitigation_plan:
        parts.append(f"Mitigation Plan: {r.mitigation_plan}")
    if hasattr(r, 'contingency_plan') and r.contingency_plan:
        parts.append(f"Contingency Plan: {r.contingency_plan}")
    if hasattr(r, 'trigger_event') and r.trigger_event:
        parts.append(f"Trigger Event: {r.trigger_event}")
    return "\n".join(parts)


def _build_decision_text(d):
    parts = [f"Decision: {d.title or ''}"]
    if d.description:
        parts.append(f"Description: {d.description}")
    if hasattr(d, 'alternatives') and d.alternatives:
        parts.append(f"Alternatives: {d.alternatives}")
    if hasattr(d, 'rationale') and d.rationale:
        parts.append(f"Rationale: {d.rationale}")
    if hasattr(d, 'impact_description') and d.impact_description:
        parts.append(f"Impact: {d.impact_description}")
    return "\n".join(parts)


def _build_issue_text(i):
    parts = [f"Issue: {i.title or ''}"]
    if i.description:
        parts.append(f"Description: {i.description}")
    if hasattr(i, 'root_cause') and i.root_cause:
        parts.append(f"Root Cause: {i.root_cause}")
    if hasattr(i, 'resolution') and i.resolution:
        parts.append(f"Resolution: {i.resolution}")
    return "\n".join(parts)


def _build_action_text(a):
    parts = [f"Action: {a.title or ''}"]
    if a.description:
        parts.append(f"Description: {a.description}")
    return "\n".join(parts)


def _build_phase_text(p):
    parts = [f"Phase: {p.name or ''}"]
    if p.description:
        parts.append(f"Description: {p.description}")
    return "\n".join(parts)


def _build_gate_text(g):
    parts = [f"Gate: {g.name or ''}"]
    if hasattr(g, 'gate_type') and g.gate_type:
        parts.append(f"Type: {g.gate_type}")
    if hasattr(g, 'criteria') and g.criteria:
        parts.append(f"Criteria: {g.criteria}")
    if hasattr(g, 'description') and g.description:
        parts.append(f"Description: {g.description}")
    return "\n".join(parts)


def _build_process_text(p):
    parts = [f"Process: {p.name or ''}"]
    if p.description:
        parts.append(f"Description: {p.description}")
    return "\n".join(parts)


def _build_scope_item_text(s):
    parts = [f"Scope Item: {s.name or ''}"]
    if s.description:
        parts.append(f"Description: {s.description}")
    if hasattr(s, 'notes') and s.notes:
        parts.append(f"Notes: {s.notes}")
    return "\n".join(parts)


def _build_analysis_text(a):
    parts = [f"Analysis: {a.name or ''}"]
    if a.description:
        parts.append(f"Description: {a.description}")
    if hasattr(a, 'decision') and a.decision:
        parts.append(f"Decision: {a.decision}")
    if hasattr(a, 'notes') and a.notes:
        parts.append(f"Notes: {a.notes}")
    return "\n".join(parts)


# ── Import and registry ──────────────────────────────────────────────────
def _get_entity_registry():
    """Lazy-import models and return entity registry."""
    from app.models.requirement import Requirement
    from app.models.scenario import Scenario
    from app.models.backlog import BacklogItem, ConfigItem
    from app.models.testing import TestCase, Defect
    from app.models.raid import Risk, Decision, Issue, Action
    from app.models.program import Phase, Gate
    from app.models.scope import Process, ScopeItem, Analysis

    return {
        "requirement":  (Requirement, _build_requirement_text, "program_id"),
        "scenario":     (Scenario, _build_scenario_text, "program_id"),
        "backlog_item": (BacklogItem, _build_backlog_item_text, "program_id"),
        "config_item":  (ConfigItem, _build_config_item_text, "program_id"),
        "test_case":    (TestCase, _build_test_case_text, None),
        "defect":       (Defect, _build_defect_text, None),
        "risk":         (Risk, _build_risk_text, "program_id"),
        "decision":     (Decision, _build_decision_text, "program_id"),
        "issue":        (Issue, _build_issue_text, "program_id"),
        "action":       (Action, _build_action_text, "program_id"),
        "phase":        (Phase, _build_phase_text, "program_id"),
        "gate":         (Gate, _build_gate_text, None),
        "process":      (Process, _build_process_text, "program_id"),
        "scope_item":   (ScopeItem, _build_scope_item_text, None),
        "analysis":     (Analysis, _build_analysis_text, None),
    }


# ── Lightweight local embedder (no API calls) ─────────────────────────────
def _local_embed(text, dim=64):
    """
    Produce a deterministic pseudo-embedding for local/dev use.
    Uses hash-based approach → consistent for same text.
    """
    import hashlib
    import json
    h = hashlib.sha256(text.encode()).hexdigest()
    # Generate dim floats from hash
    vec = []
    for i in range(dim):
        # Cycle through hash chars
        byte_val = int(h[(i * 2) % len(h):(i * 2) % len(h) + 2], 16)
        vec.append(round((byte_val / 255.0) * 2 - 1, 6))  # Normalize to [-1, 1]
    # Normalize to unit vector
    magnitude = sum(v ** 2 for v in vec) ** 0.5
    if magnitude > 0:
        vec = [round(v / magnitude, 6) for v in vec]
    return json.dumps(vec)


# ── Chunking helper ──────────────────────────────────────────────────────
def _chunk_text(text, max_chars=1500, overlap_chars=200):
    """Split long text into overlapping chunks."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap_chars
    return chunks


# ── Main embedding logic ─────────────────────────────────────────────────
def embed_entities(app, entity_types=None, program_id=None, clear=False):
    """Index entities into ai_embeddings table."""
    with app.app_context():
        registry = _get_entity_registry()

        if entity_types:
            selected = {k: v for k, v in registry.items() if k in entity_types}
        else:
            selected = registry

        if clear:
            if entity_types:
                for et in entity_types:
                    count = AIEmbedding.query.filter_by(entity_type=et).delete()
                    print(f"  🗑️  Cleared {count} embeddings for {et}")
            else:
                count = AIEmbedding.query.delete()
                print(f"  🗑️  Cleared all {count} embeddings")
            db.session.commit()

        total_embedded = 0
        total_chunks = 0
        start_time = time.time()

        for entity_type, (Model, text_builder, prog_fk) in selected.items():
            query = Model.query
            if program_id and prog_fk and hasattr(Model, prog_fk):
                query = query.filter(getattr(Model, prog_fk) == program_id)

            entities = query.all()
            if not entities:
                print(f"  ⏭️  {entity_type}: no entities found, skipping")
                continue

            entity_chunks = 0
            for entity in entities:
                text = text_builder(entity)
                if not text or len(text.strip()) < 10:
                    continue

                chunks = _chunk_text(text)
                for idx, chunk in enumerate(chunks):
                    embedding_json = _local_embed(chunk)

                    # Derive module from entity if available
                    module = None
                    if hasattr(entity, 'module'):
                        module = entity.module

                    emb = AIEmbedding(
                        entity_type=entity_type,
                        entity_id=entity.id,
                        chunk_text=chunk,
                        embedding_json=embedding_json,
                        module=module,
                        metadata_json=f'{{"chunk_index": {idx}, "total_chunks": {len(chunks)}}}',
                    )
                    db.session.add(emb)
                    entity_chunks += 1

                total_embedded += 1

            db.session.commit()
            total_chunks += entity_chunks
            print(f"  ✅ {entity_type}: {len(entities)} entities → {entity_chunks} chunks")

        elapsed = time.time() - start_time
        print(f"\n  📊 Summary: {total_embedded} entities, {total_chunks} chunks, {elapsed:.1f}s")
        return total_embedded, total_chunks


def main():
    parser = argparse.ArgumentParser(description="Embed SAP knowledge base entities for RAG")
    parser.add_argument(
        "--entity-types", type=str, default=None,
        help="Comma-separated entity types (e.g., requirement,risk,defect)"
    )
    parser.add_argument(
        "--program-id", type=int, default=None,
        help="Filter by program ID"
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Clear existing embeddings before indexing"
    )
    args = parser.parse_args()

    entity_types = None
    if args.entity_types:
        entity_types = [t.strip() for t in args.entity_types.split(",")]

    app = create_app()
    print(f"🎯 Target DB: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"📦 Entity types: {entity_types or 'ALL'}")
    if args.program_id:
        print(f"🔍 Program filter: {args.program_id}")
    print()

    embed_entities(app, entity_types=entity_types, program_id=args.program_id, clear=args.clear)
    print("\n🏁 Knowledge base embedding complete!")


if __name__ == "__main__":
    main()
