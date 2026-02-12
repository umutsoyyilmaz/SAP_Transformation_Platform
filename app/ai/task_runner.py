"""
SAP Transformation Management Platform
Async AI Task Runner — Sprint 21.

Lightweight async task runner for long-running AI operations.
Tasks run in background threads with status polling via the API.
"""

import json
import logging
import threading
from datetime import datetime, timezone

from app.models import db
from app.models.ai import AITask

logger = logging.getLogger(__name__)

# In-memory registry of running jobs (task_id → Thread)
_running_tasks: dict[int, threading.Thread] = {}


class TaskRunner:
    """Runs AI tasks asynchronously and tracks progress."""

    def submit(
        self,
        task_type: str,
        input_data: dict,
        *,
        user: str = "system",
        program_id: int | None = None,
        workflow_name: str | None = None,
        execute_fn=None,
    ) -> dict:
        """
        Submit an async AI task.

        Args:
            task_type: e.g. "batch_analysis", "workflow_execution"
            input_data: Input payload for the task.
            user: Who submitted the task.
            program_id: Associated program.
            workflow_name: Associated workflow (if orchestration).
            execute_fn: Callable(input_data) → dict result.
                        If None, task stays pending for external pickup.

        Returns:
            Task dict (serializable).
        """
        task = AITask(
            task_type=task_type,
            status="pending",
            progress_pct=0,
            input_json=json.dumps(input_data, default=str),
            user=user,
            program_id=program_id,
            workflow_name=workflow_name,
        )
        db.session.add(task)
        db.session.flush()
        task_id = task.id

        if execute_fn:
            task.status = "running"
            task.started_at = datetime.now(timezone.utc)
            db.session.flush()
            # NOTE: we commit here so the background thread can read the task
            db.session.commit()

            t = threading.Thread(
                target=self._execute_in_background,
                args=(task_id, input_data, execute_fn),
                daemon=True,
            )
            _running_tasks[task_id] = t
            t.start()

        return task.to_dict()

    def get_status(self, task_id: int) -> dict | None:
        """Get task status."""
        task = db.session.get(AITask, task_id)
        if not task:
            return None
        return task.to_dict()

    def cancel(self, task_id: int) -> dict | None:
        """Cancel a pending/running task."""
        task = db.session.get(AITask, task_id)
        if not task:
            return None
        if task.status in ("completed", "failed", "cancelled"):
            return task.to_dict()
        task.status = "cancelled"
        task.completed_at = datetime.now(timezone.utc)
        db.session.flush()
        # Remove from running registry
        _running_tasks.pop(task_id, None)
        return task.to_dict()

    def list_tasks(
        self,
        user: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List tasks with optional filters."""
        q = AITask.query.order_by(AITask.created_at.desc())
        if user:
            q = q.filter_by(user=user)
        if status:
            q = q.filter_by(status=status)
        return [t.to_dict() for t in q.limit(limit).all()]

    def update_progress(self, task_id: int, progress_pct: int):
        """Update task progress (called from within execute_fn)."""
        task = db.session.get(AITask, task_id)
        if task and task.status == "running":
            task.progress_pct = min(progress_pct, 100)
            db.session.flush()

    # ── Internal ──────────────────────────────────────────────────────────

    def _execute_in_background(self, task_id: int, input_data: dict, execute_fn):
        """Run the task function in a background thread."""
        # We need an app context for DB access
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            # If no app context, try to import and create one
            try:
                from app import create_app
                app = create_app()
            except Exception:
                logger.error("TaskRunner: Cannot obtain Flask app for background task %d", task_id)
                return

        with app.app_context():
            try:
                result = execute_fn(input_data)
                task = db.session.get(AITask, task_id)
                if task and task.status != "cancelled":
                    task.status = "completed"
                    task.progress_pct = 100
                    task.result_json = json.dumps(result, default=str)
                    task.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
            except Exception as e:
                logger.error("TaskRunner: Task %d failed: %s", task_id, e)
                try:
                    task = db.session.get(AITask, task_id)
                    if task:
                        task.status = "failed"
                        task.error_message = str(e)
                        task.completed_at = datetime.now(timezone.utc)
                        db.session.commit()
                except Exception:
                    pass
            finally:
                _running_tasks.pop(task_id, None)
