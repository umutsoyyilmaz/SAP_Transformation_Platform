"""AI NL query refinement service.

Applies small deterministic refinements to the last saved NL query result in a
conversation so the chat UI can support simple follow-up prompts without a full
multi-turn semantic planner.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc

from app.ai.assistants import sanitize_sql, validate_sql
from app.models.ai import AIConversation, AIConversationMessage
from app.services import ai_reporting_service

logger = logging.getLogger(__name__)

_STATUS_VALUES = {
    "open": "open",
    "approved": "approved",
    "rejected": "rejected",
    "closed": "closed",
    "blocked": "blocked",
    "draft": "draft",
    "ready": "ready",
    "deprecated": "deprecated",
    "in progress": "in_progress",
    "in_progress": "in_progress",
}

_SORT_KEYWORDS = {
    "status": "status",
    "priority": "priority",
    "module": "module",
    "code": "code",
    "title": "title",
    "updated": "updated_at",
    "updated at": "updated_at",
    "created": "created_at",
    "created at": "created_at",
    "date": "updated_at",
}

_GROUP_KEYWORDS = {
    "status": "status",
    "module": "module",
    "priority": "priority",
}

_MODULE_VALUES = {
    "fi": "FI",
    "co": "CO",
    "mm": "MM",
    "sd": "SD",
    "pp": "PP",
    "qm": "QM",
    "pm": "PM",
    "hcm": "HCM",
    "basis": "BASIS",
    "btp": "BTP",
}

_PRIORITY_VALUES = {
    "critical priority": "critical",
    "high priority": "high",
    "medium priority": "medium",
    "low priority": "low",
    "must have": "must_have",
    "must-have": "must_have",
    "should have": "should_have",
    "should-have": "should_have",
    "could have": "could_have",
    "could-have": "could_have",
    "wont have": "wont_have",
    "won't have": "wont_have",
    "medium": "medium",
    "high": "high",
    "low": "low",
    "critical": "critical",
}

_LIST_QUERY_MAPPINGS: dict[str, dict[str, Any]] = {
    "test_cases": {
        "default_alias": "tc",
        "columns": ["code", "title", "status", "priority", "module", "test_layer"],
        "order_by": ["updated_at DESC", "code ASC"],
    },
    "requirements": {
        "default_alias": "req",
        "columns": ["code", "title", "status", "priority", "module"],
        "order_by": ["updated_at DESC", "code ASC"],
    },
    "change_requests": {
        "default_alias": "cr",
        "columns": ["code", "title", "status", "change_model", "change_domain"],
        "order_by": ["updated_at DESC", "code ASC"],
    },
    "risks": {
        "default_alias": "r",
        "columns": ["code", "title", "status", "priority", "rag_status", "owner"],
        "order_by": ["risk_score DESC", "updated_at DESC", "code ASC"],
    },
    "defects": {
        "default_alias": "d",
        "columns": ["code", "title", "status", "severity", "module", "assigned_to", "reported_at"],
        "order_by": ["reported_at DESC", "code ASC"],
    },
}


def refine_saved_query(conversation_id: int, refinement: str) -> dict[str, Any]:
    """Apply a deterministic refinement to the most recent saved NL query."""
    conversation = AIConversation.query.get(conversation_id)
    if not conversation:
        return {"error": "Conversation not found"}
    if conversation.assistant_type != "nl_query":
        return {"error": "Conversation is not an NL query conversation"}

    last_payload = _get_last_nl_query_payload(conversation)
    if last_payload is None:
        return {"error": "No prior NL query result found in this conversation"}

    base_sql = last_payload.get("sql")
    if not base_sql:
        return {"error": "The last assistant result does not contain SQL to refine"}

    refined_sql, refinement_summary, refinement_error = _apply_refinement(base_sql, refinement)
    if refinement_error:
        return {
            "error": refinement_error,
            "suggestions": [
                "Only open ones",
                "For FI only",
                "Last 30 days",
                "Group by module",
            ],
        }
    if not refinement_summary:
        return {
            "error": "I could not apply that refinement yet. Try sort/filter/group/limit wording.",
            "suggestions": [
                "Only open ones",
                "For FI only",
                "Last 30 days",
                "Group by module",
            ],
        }

    cleaned = sanitize_sql(refined_sql)
    validation = validate_sql(cleaned)
    if not validation["valid"]:
        return {"error": validation["error"]}

    execution = ai_reporting_service.execute_readonly_sql(validation["cleaned_sql"])
    answer = _build_refinement_answer(execution)
    return {
        "type": "nl_query_result",
        "original_query": last_payload.get("original_query"),
        "refinement": refinement,
        "program_id": last_payload.get("program_id"),
        "project_id": last_payload.get("project_id"),
        "sql": execution["sql"],
        "results": execution["results"],
        "columns": execution["columns"],
        "row_count": execution["row_count"],
        "executed": True,
        "error": None,
        "answer": answer,
        "explanation": f"Applied refinement: {refinement_summary}.",
        "confidence": 0.78,
        "glossary_matches": last_payload.get("glossary_matches", []),
        "suggestions": _build_refinement_suggestions(refinement_summary),
    }


def _get_last_nl_query_payload(conversation: AIConversation) -> dict[str, Any] | None:
    messages = (
        AIConversationMessage.query.filter_by(conversation_id=conversation.id)
        .order_by(desc(AIConversationMessage.seq))
        .all()
    )
    for message in messages:
        if message.role != "assistant":
            continue
        try:
            payload = json.loads(message.content)
        except Exception:
            continue
        if isinstance(payload, dict) and payload.get("type") == "nl_query_result":
            return payload
    return None


def _apply_refinement(base_sql: str, refinement: str) -> tuple[str, str, str | None]:
    refined_sql = _strip_limit(base_sql)
    refinement_parts: list[str] = []
    alias = _extract_table_alias(refined_sql)
    normalized = re.sub(r"\s+", " ", refinement.lower()).strip()
    is_aggregate_count = _is_aggregate_count_query(refined_sql)
    is_grouped_aggregate = _is_grouped_aggregate_query(refined_sql)
    requested_limit = _detect_limit_value(normalized)

    if _is_list_intent(normalized):
        if is_grouped_aggregate:
            list_sql = _convert_grouped_query_to_list_query(refined_sql, normalized, requested_limit or 50)
            if not list_sql:
                return refined_sql, "", "I could not identify which grouped bucket to expand. Try a follow-up like 'List the SD ones' or 'List the blocked ones'."
            modified_list_sql, list_parts = _apply_list_modifiers(list_sql, normalized, suppress_limit_summary=bool(requested_limit))
            summary = _join_refinement_parts(
                [f"expanded the grouped result into a detailed list limited to {requested_limit or 50}", *list_parts]
            )
            return modified_list_sql, summary, None
        if not is_aggregate_count:
            return refined_sql, "", "The last result is already a detailed view. Try sorting, filtering, or grouping it instead."
        list_sql = _convert_count_to_list_query(refined_sql, requested_limit or 50)
        if not list_sql:
            return refined_sql, "", "I could not turn that count into a detailed list yet. Ask a fresh question for the records instead."
        modified_list_sql, list_parts = _apply_list_modifiers(list_sql, normalized, suppress_limit_summary=bool(requested_limit))
        summary = _join_refinement_parts([f"expanded the count into a detailed list limited to {requested_limit or 50}", *list_parts])
        return modified_list_sql, summary, None

    status_value = _detect_status_value(normalized)
    if status_value:
        status_column = _qualify_column(alias, "status")
        if status_value == "open":
            refined_sql = _inject_filter(refined_sql, f"{status_column} NOT IN ('closed', 'rejected', 'deprecated')")
        else:
            refined_sql = _inject_filter(refined_sql, f"{status_column} = '{status_value}'")
        refinement_parts.append(f"filtered to {status_value}")

    module_value = _detect_module_value(normalized)
    if module_value:
        module_column = _qualify_column(alias, "module")
        refined_sql = _inject_filter(refined_sql, f"{module_column} = '{module_value}'")
        refinement_parts.append(f"filtered to module {module_value}")

    priority_value = _detect_priority_value(normalized)
    if priority_value:
        priority_column = _qualify_column(alias, "priority")
        refined_sql = _inject_filter(refined_sql, f"{priority_column} = '{priority_value}'")
        refinement_parts.append(f"filtered to priority {priority_value}")

    date_window_days = _detect_recent_days(normalized)
    if date_window_days:
        date_column = _resolve_date_column(alias)
        cutoff = _build_cutoff_timestamp(date_window_days)
        refined_sql = _inject_filter(refined_sql, f"{date_column} >= '{cutoff}'")
        refinement_parts.append(f"restricted to the last {date_window_days} days")

    group_column = _detect_group_column(normalized)
    if group_column:
        target_column = _qualify_column(alias, group_column)
        refined_sql = _convert_to_group_query(refined_sql, target_column)
        refinement_parts.append(f"grouped by {group_column}")
    else:
        sort_column = _detect_sort_column(normalized)
        if sort_column:
            if is_aggregate_count:
                return refined_sql, "", "Sorting does not make sense on a single count result. Ask for a grouped or listed view instead."
            direction = "ASC" if re.search(r"\basc|ascending\b", normalized) else "DESC"
            refined_sql = _replace_order_by(refined_sql, _qualify_column(alias, sort_column), direction)
            refinement_parts.append(f"sorted by {sort_column} {direction.lower()}")

    limit_value = requested_limit
    if is_aggregate_count and limit_value:
        return refined_sql, "", "A top or limit refinement does not apply to a single count result. Ask to list the matching records first."
    final_limit = limit_value or 100
    refined_sql = _set_limit(refined_sql, final_limit)
    if limit_value:
        refinement_parts.append(f"limited to {limit_value}")

    return refined_sql, _join_refinement_parts(refinement_parts), None


def _strip_limit(sql: str) -> str:
    return re.sub(r"\s+LIMIT\s+\d+\s*$", "", sql, flags=re.IGNORECASE).strip()


def _extract_table_alias(sql: str) -> str | None:
    match = re.search(r"\bFROM\s+[a-zA-Z_]\w*(?:\s+([a-zA-Z_]\w*))?", sql, re.IGNORECASE)
    if not match:
        return None
    alias = match.group(1)
    if alias and alias.upper() not in {"WHERE", "ORDER", "GROUP", "LIMIT", "JOIN"}:
        return alias
    return None


def _qualify_column(alias: str | None, column: str) -> str:
    return f"{alias}.{column}" if alias else column


def _detect_status_value(normalized: str) -> str | None:
    for key, value in _STATUS_VALUES.items():
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", normalized):
            return value
    return None


def _detect_sort_column(normalized: str) -> str | None:
    if not re.search(r"\bsort\b|\bsorted by\b|\border by\b", normalized):
        return None
    for key, value in _SORT_KEYWORDS.items():
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", normalized):
            return value
    return "updated_at"


def _detect_group_column(normalized: str) -> str | None:
    if not re.search(r"\bgroup by\b|\bby\s+status\b|\bby\s+module\b|\bby\s+priority\b", normalized):
        return None
    for key, value in _GROUP_KEYWORDS.items():
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", normalized):
            return value
    return None


def _detect_limit_value(normalized: str) -> int | None:
    match = re.search(r"\b(?:top|limit|first)\s+(\d{1,3})\b", normalized)
    if not match:
        return None
    value = int(match.group(1))
    return max(1, min(value, 100))


def _is_list_intent(normalized: str) -> bool:
    return bool(
        re.search(
            r"\blist\b|\bshow\s+(them|records|items|rows|details)\b|\bwhich\s+ones\b|\bshow\s+me\b|\bones\b",
            normalized,
        )
    )


def _apply_list_modifiers(sql: str, normalized: str, suppress_limit_summary: bool = False) -> tuple[str, list[str]]:
    refined_sql = sql
    alias = _extract_table_alias(refined_sql)
    refinement_parts: list[str] = []

    status_value = _detect_status_value(normalized)
    if status_value:
        status_column = _qualify_column(alias, "status")
        if status_value == "open":
            refined_sql = _inject_filter(refined_sql, f"{status_column} NOT IN ('closed', 'rejected', 'deprecated')")
        else:
            refined_sql = _inject_filter(refined_sql, f"{status_column} = '{status_value}'")
        refinement_parts.append(f"filtered to {status_value}")

    module_value = _detect_module_value(normalized)
    if module_value:
        module_column = _qualify_column(alias, "module")
        if module_column.lower() not in refined_sql.lower() or f"'{module_value.lower()}'" not in refined_sql.lower():
            refined_sql = _inject_filter(refined_sql, f"{module_column} = '{module_value}'")
            refinement_parts.append(f"filtered to module {module_value}")

    priority_value = _detect_priority_value(normalized)
    if priority_value:
        priority_column = _qualify_column(alias, "priority")
        if priority_column.lower() not in refined_sql.lower() or f"'{priority_value.lower()}'" not in refined_sql.lower():
            refined_sql = _inject_filter(refined_sql, f"{priority_column} = '{priority_value}'")
            refinement_parts.append(f"filtered to priority {priority_value}")

    date_window_days = _detect_recent_days(normalized)
    if date_window_days:
        date_column = _resolve_date_column(alias)
        cutoff = _build_cutoff_timestamp(date_window_days)
        refined_sql = _inject_filter(refined_sql, f"{date_column} >= '{cutoff}'")
        refinement_parts.append(f"restricted to the last {date_window_days} days")

    sort_column = _detect_sort_column(normalized)
    if sort_column:
        direction = "ASC" if re.search(r"\basc|ascending\b", normalized) else "DESC"
        refined_sql = _replace_order_by(refined_sql, _qualify_column(alias, sort_column), direction)
        refinement_parts.append(f"sorted by {sort_column} {direction.lower()}")

    limit_value = _detect_limit_value(normalized)
    if limit_value:
        current_limit = _extract_limit_value(refined_sql)
        if current_limit != limit_value or re.search(r"\bORDER BY\b", refined_sql, re.IGNORECASE):
            refined_sql = _set_limit(refined_sql, limit_value)
        if not suppress_limit_summary:
            refinement_parts.append(f"limited to {limit_value}")

    return refined_sql, refinement_parts


def _join_refinement_parts(parts: list[str]) -> str:
    return ", ".join(part for part in parts if part)


def _extract_limit_value(sql: str) -> int | None:
    match = re.search(r"\bLIMIT\s+(\d+)\s*$", sql, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _detect_module_value(normalized: str) -> str | None:
    for key, value in _MODULE_VALUES.items():
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", normalized):
            return value
    return None


def _detect_priority_value(normalized: str) -> str | None:
    for key, value in _PRIORITY_VALUES.items():
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", normalized):
            return value
    return None


def _detect_recent_days(normalized: str) -> int | None:
    match = re.search(r"\blast\s+(\d{1,3})\s+(day|days|week|weeks|month|months)\b", normalized)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("week"):
            return max(1, min(amount * 7, 365))
        if unit.startswith("month"):
            return max(1, min(amount * 30, 365))
        return max(1, min(amount, 365))

    if re.search(r"\btoday\b", normalized):
        return 1
    if re.search(r"\bthis week\b", normalized):
        return 7
    if re.search(r"\bthis month\b", normalized):
        return 30
    return None


def _resolve_date_column(alias: str | None) -> str:
    return _qualify_column(alias, "updated_at")


def _build_cutoff_timestamp(days: int) -> str:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    return cutoff.replace(microsecond=0).isoformat(sep=" ")


def _is_aggregate_count_query(sql: str) -> bool:
    normalized = re.sub(r"\s+", " ", sql.strip().lower())
    if " group by " in normalized:
        return False
    select_match = re.match(r"select\s+(.+?)\s+from\s+", normalized, flags=re.DOTALL)
    if not select_match:
        return False
    projection = select_match.group(1).strip()
    return projection.startswith("count(") or bool(re.fullmatch(r"count\([^)]*\)\s+as\s+[a-z_][a-z0-9_]*", projection))


def _is_grouped_aggregate_query(sql: str) -> bool:
    normalized = re.sub(r"\s+", " ", sql.strip().lower())
    return " as refinement_group" in normalized and " as refinement_count" in normalized and " group by " in normalized


def _extract_table_name(sql: str) -> str | None:
    match = re.search(r"\bFROM\s+([a-zA-Z_]\w*)", sql, re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def _convert_count_to_list_query(sql: str, limit_value: int) -> str | None:
    table_name = _extract_table_name(sql)
    if not table_name:
        return None
    mapping = _LIST_QUERY_MAPPINGS.get(table_name)
    if not mapping:
        return None

    from_match = re.search(r"\bFROM\b.+", sql, re.IGNORECASE | re.DOTALL)
    if not from_match:
        return None

    alias = _extract_table_alias(sql) or str(mapping["default_alias"])
    tail = from_match.group(0)
    tail = re.sub(r"\bORDER BY\b.+$", "", tail, flags=re.IGNORECASE)
    tail = re.sub(r"\bLIMIT\b\s+\d+\s*$", "", tail, flags=re.IGNORECASE)
    columns = ", ".join(f"{alias}.{column}" for column in mapping["columns"])
    order_by = ", ".join(f"{alias}.{column_order}" for column_order in mapping["order_by"])
    return f"SELECT {columns} {tail} ORDER BY {order_by} LIMIT {limit_value}".strip()


def _extract_grouped_query_parts(sql: str) -> tuple[str, str, str, str | None] | None:
    pattern = re.compile(
        r"SELECT\s+(?P<group_expr>[\w\.]+)\s+AS\s+refinement_group\s*,\s*COUNT\(\*\)\s+AS\s+refinement_count\s+(?P<tail>FROM\s+.+?)\s+GROUP\s+BY\s+(?P=group_expr)\s+ORDER\s+BY\s+.+$",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(sql.strip())
    if not match:
        return None
    group_expr = match.group("group_expr")
    tail = match.group("tail")
    alias = _extract_table_alias(sql)
    table_name = _extract_table_name(sql)
    return group_expr, tail, alias or "", table_name


def _convert_grouped_query_to_list_query(sql: str, normalized: str, limit_value: int) -> str | None:
    grouped_parts = _extract_grouped_query_parts(sql)
    if not grouped_parts:
        return None

    group_expr, tail, alias, table_name = grouped_parts
    mapping = _LIST_QUERY_MAPPINGS.get(table_name or "")
    if not mapping:
        return None

    target_value = _detect_group_bucket_value(group_expr, normalized)
    if target_value is None:
        return None

    effective_alias = alias or str(mapping["default_alias"])
    columns = ", ".join(f"{effective_alias}.{column}" for column in mapping["columns"])
    order_by = ", ".join(f"{effective_alias}.{column_order}" for column_order in mapping["order_by"])
    list_tail = _append_group_bucket_filter(tail, group_expr, target_value)
    return f"SELECT {columns} {list_tail} ORDER BY {order_by} LIMIT {limit_value}".strip()


def _detect_group_bucket_value(group_expr: str, normalized: str) -> str | None:
    group_column = group_expr.split(".")[-1].lower()
    if group_column == "module":
        return _detect_module_value(normalized)
    if group_column == "status":
        return _detect_status_value(normalized)
    if group_column == "priority":
        return _detect_priority_value(normalized)
    return None


def _append_group_bucket_filter(tail: str, group_expr: str, target_value: str) -> str:
    if re.search(r"\bWHERE\b", tail, re.IGNORECASE):
        return re.sub(r"\bWHERE\b", f"WHERE {group_expr} = '{target_value}' AND ", tail, count=1, flags=re.IGNORECASE)
    return f"{tail} WHERE {group_expr} = '{target_value}'"


def _inject_filter(sql: str, clause: str) -> str:
    if re.search(r"\bWHERE\b", sql, re.IGNORECASE):
        return re.sub(r"\bWHERE\b", f"WHERE {clause} AND ", sql, count=1, flags=re.IGNORECASE)
    if re.search(r"\bGROUP BY\b", sql, re.IGNORECASE):
        return re.sub(r"\bGROUP BY\b", f"WHERE {clause} GROUP BY", sql, count=1, flags=re.IGNORECASE)
    if re.search(r"\bORDER BY\b", sql, re.IGNORECASE):
        return re.sub(r"\bORDER BY\b", f"WHERE {clause} ORDER BY", sql, count=1, flags=re.IGNORECASE)
    return f"{sql} WHERE {clause}"


def _replace_order_by(sql: str, column: str, direction: str) -> str:
    if re.search(r"\bORDER BY\b", sql, re.IGNORECASE):
        return re.sub(r"\bORDER BY\b.+$", f"ORDER BY {column} {direction}", sql, flags=re.IGNORECASE)
    return f"{sql} ORDER BY {column} {direction}"


def _set_limit(sql: str, limit_value: int) -> str:
    sql = _strip_limit(sql)
    return f"{sql} LIMIT {limit_value}"


def _convert_to_group_query(sql: str, target_column: str) -> str:
    from_match = re.search(r"\bFROM\b.+", sql, re.IGNORECASE | re.DOTALL)
    if not from_match:
        return sql
    tail = from_match.group(0)
    tail = re.sub(r"\bORDER BY\b.+$", "", tail, flags=re.IGNORECASE)
    tail = re.sub(r"\bLIMIT\b\s+\d+\s*$", "", tail, flags=re.IGNORECASE)
    tail = re.sub(r"\bGROUP BY\b.+$", "", tail, flags=re.IGNORECASE)
    return (
        f"SELECT {target_column} AS refinement_group, COUNT(*) AS refinement_count "
        f"{tail} GROUP BY {target_column} ORDER BY refinement_count DESC, refinement_group ASC"
    ).strip()


def _build_refinement_answer(execution: dict[str, Any]) -> str:
    row_count = execution.get("row_count", 0)
    if row_count == 0:
        return "I applied the refinement, but it returned no matching rows."
    if row_count == 1 and execution.get("columns") and len(execution["columns"]) == 1:
        return f"The refined query returned {execution['results'][0][execution['columns'][0]]}."
    return f"I applied the refinement and found {row_count} row{'s' if row_count != 1 else ''}."


def _build_refinement_suggestions(refinement_summary: str) -> list[str]:
    if "expanded the grouped result into a detailed list" in refinement_summary:
        return ["Sort by priority", "Only medium priority", "Last 30 days"]
    if "expanded the count into a detailed list" in refinement_summary:
        return ["Sort by priority", "Only open ones", "For FI only"]
    if "grouped by" in refinement_summary:
        return ["Sort by status", "Only open ones", "Last 30 days"]
    if "sorted by" in refinement_summary:
        return ["Only open ones", "Group by status", "For FI only"]
    if "filtered to priority" in refinement_summary:
        return ["Sort by priority", "Group by status", "Last 30 days"]
    return ["Sort by status", "Group by status", "Last 30 days"]
