"""
SAP Transformation Management Platform
AI Orchestrator — Sprint 21.

Chains multiple AI assistants in predefined workflows.
Uses the TaskRunner for async execution tracking.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ── Workflow Definitions ──────────────────────────────────────────────────

WORKFLOW_DEFINITIONS = {
    "requirement_to_spec": {
        "name": "Requirement → Change Impact → Test Cases → WRICEF Spec",
        "description": "Full traceability pipeline from a requirement through to specification",
        "steps": [
            {"assistant": "requirement_analyst", "method": "analyze", "input_key": "text"},
            {"assistant": "change_impact", "method": "analyze", "input_key": "requirement_text",
             "map_from": {"requirement_text": "$.summary"}},
            {"assistant": "test_case_generator", "method": "generate", "input_key": "requirement_text",
             "map_from": {"requirement_text": "$.summary"}},
            {"assistant": "wricef_spec", "method": "generate_spec", "input_key": "requirement_text",
             "map_from": {"requirement_text": "$.summary"}},
        ],
    },
    "risk_to_mitigation": {
        "name": "Risk Assessment → Change Impact → Test Cases",
        "description": "From risk analysis through impact and test coverage",
        "steps": [
            {"assistant": "risk_assessment", "method": "assess", "input_key": "context"},
            {"assistant": "change_impact", "method": "analyze", "input_key": "requirement_text",
             "map_from": {"requirement_text": "$.top_risks"}},
            {"assistant": "test_case_generator", "method": "generate", "input_key": "requirement_text",
             "map_from": {"requirement_text": "$.top_risks"}},
        ],
    },
    "migration_full_analysis": {
        "name": "Data Migration → Reconciliation → Risk Assessment",
        "description": "Complete data migration workflow with reconciliation and risk",
        "steps": [
            {"assistant": "data_migration", "method": "analyze", "input_key": "scope"},
            {"assistant": "data_migration", "method": "reconciliation_check", "input_key": "data_object",
             "map_from": {"data_object": "$.strategy"}},
            {"assistant": "risk_assessment", "method": "assess", "input_key": "context",
             "map_from": {"context": "$.risk_areas"}},
        ],
    },
    "integration_validation": {
        "name": "Integration Dependencies → Switch Plan Validate → Risk",
        "description": "Integration analysis and switch plan validation workflow",
        "steps": [
            {"assistant": "integration_analyst", "method": "analyze_dependencies", "input_key": "program_id"},
            {"assistant": "risk_assessment", "method": "assess", "input_key": "context",
             "map_from": {"context": "$.risks"}},
        ],
    },
}


class AIOrchestrator:
    """
    Orchestrates multi-step AI workflows by chaining assistants
    and threading outputs forward as inputs to the next step.
    """

    def __init__(self, assistants: dict, task_runner=None):
        """
        Args:
            assistants: Dict mapping assistant_name → assistant instance.
            task_runner: Optional TaskRunner for async execution.
        """
        self.assistants = assistants
        self.task_runner = task_runner

    def list_workflows(self) -> list[dict]:
        """List all registered workflows."""
        return [
            {
                "workflow": key,
                "name": defn["name"],
                "description": defn["description"],
                "steps": len(defn["steps"]),
            }
            for key, defn in WORKFLOW_DEFINITIONS.items()
        ]

    def execute(self, workflow_name: str, initial_input: dict,
                program_id: int = 0, user: str = "system") -> dict:
        """
        Execute a workflow synchronously.

        Args:
            workflow_name: Key from WORKFLOW_DEFINITIONS.
            initial_input: Dict of initial parameters.
            program_id: Associated program.
            user: User triggering the workflow.

        Returns:
            Dict with step_results, final_output, workflow, status, etc.
        """
        defn = WORKFLOW_DEFINITIONS.get(workflow_name)
        if not defn:
            return {
                "error": f"Unknown workflow: {workflow_name}",
                "available_workflows": list(WORKFLOW_DEFINITIONS.keys()),
            }

        step_results = []
        current_data = dict(initial_input)
        last_output = {}

        for i, step in enumerate(defn["steps"]):
            assistant_name = step["assistant"]
            method_name = step["method"]
            input_key = step.get("input_key")

            assistant = self.assistants.get(assistant_name)
            if not assistant:
                step_results.append({
                    "step": i + 1,
                    "assistant": assistant_name,
                    "method": method_name,
                    "status": "skipped",
                    "reason": f"Assistant '{assistant_name}' not available",
                })
                continue

            method = getattr(assistant, method_name, None)
            if not method:
                step_results.append({
                    "step": i + 1,
                    "assistant": assistant_name,
                    "method": method_name,
                    "status": "skipped",
                    "reason": f"Method '{method_name}' not found",
                })
                continue

            # Build kwargs for this step
            kwargs = {"program_id": program_id}
            if "create_suggestion" in method.__code__.co_varnames:
                kwargs["create_suggestion"] = False

            # Map outputs from previous steps if mapping defined
            if step.get("map_from") and last_output:
                for param, json_path in step["map_from"].items():
                    mapped = self._resolve_path(last_output, json_path)
                    if mapped is not None:
                        kwargs[param] = mapped if isinstance(mapped, str) else json.dumps(mapped)

            # Provide input_key from initial_input if not already mapped
            if input_key and input_key not in kwargs:
                if input_key in current_data:
                    kwargs[input_key] = current_data[input_key]

            try:
                result = method(**kwargs)
                step_results.append({
                    "step": i + 1,
                    "assistant": assistant_name,
                    "method": method_name,
                    "status": "completed",
                    "output": result,
                })
                if isinstance(result, dict):
                    last_output = result
            except Exception as exc:
                logger.warning(
                    "Workflow %s step %d failed: %s", workflow_name, i + 1, exc
                )
                step_results.append({
                    "step": i + 1,
                    "assistant": assistant_name,
                    "method": method_name,
                    "status": "failed",
                    "error": str(exc),
                })
                last_output = {}

        completed_steps = sum(
            1 for s in step_results if s["status"] == "completed"
        )
        return {
            "workflow": workflow_name,
            "workflow_name": defn["name"],
            "status": "completed" if completed_steps == len(defn["steps"]) else "partial",
            "total_steps": len(defn["steps"]),
            "completed_steps": completed_steps,
            "step_results": step_results,
            "final_output": last_output,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "user": user,
            "program_id": program_id,
        }

    def execute_async(self, workflow_name: str, initial_input: dict,
                      program_id: int = 0, user: str = "system") -> dict:
        """Submit a workflow for async execution via the TaskRunner."""
        if not self.task_runner:
            return {"error": "TaskRunner not configured; use synchronous execute()"}

        defn = WORKFLOW_DEFINITIONS.get(workflow_name)
        if not defn:
            return {
                "error": f"Unknown workflow: {workflow_name}",
                "available_workflows": list(WORKFLOW_DEFINITIONS.keys()),
            }

        def _run(input_data):
            return self.execute(workflow_name, input_data, program_id, user)

        task = self.task_runner.submit(
            task_type=f"workflow_{workflow_name}",
            input_data=initial_input,
            user=user,
            program_id=program_id,
            workflow_name=workflow_name,
            execute_fn=_run,
        )
        return task

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_path(data: dict, json_path: str):
        """
        Resolve a simple JSON path like $.field or $.field.subfield.

        Only supports dot notation on dicts.
        """
        if not json_path.startswith("$."):
            return None
        parts = json_path[2:].split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
