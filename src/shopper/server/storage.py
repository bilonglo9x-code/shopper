"""Task storage - in-memory store with JSON persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from shopper.server.models import TaskResponse, TaskResult, TaskStatus, TaskType

logger = logging.getLogger(__name__)


class TaskStore:
    """In-memory task store with optional JSON file persistence."""

    def __init__(self, persist_path: Path | None = None) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}
        self._persist_path = persist_path
        if persist_path and persist_path.exists():
            self._load()

    def create_task(self, url: str, task_type: TaskType | None = None) -> str:
        """Create a new task and return its ID."""
        task_id = uuid4().hex[:12]
        self._tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "task_type": task_type,
            "url": url,
            "created_at": datetime.now(timezone.utc),
            "completed_at": None,
            "total_items": 0,
            "error": None,
            "data": None,
        }
        self._save()
        return task_id

    def set_running(self, task_id: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = TaskStatus.RUNNING
            self._save()

    def set_completed(self, task_id: str, data: Any, total_items: int = 0) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = TaskStatus.COMPLETED
            self._tasks[task_id]["completed_at"] = datetime.now(timezone.utc)
            self._tasks[task_id]["data"] = data
            self._tasks[task_id]["total_items"] = total_items
            self._save()

    def set_failed(self, task_id: str, error: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = TaskStatus.FAILED
            self._tasks[task_id]["completed_at"] = datetime.now(timezone.utc)
            self._tasks[task_id]["error"] = error
            self._save()

    def get_task(self, task_id: str) -> TaskResponse | None:
        task = self._tasks.get(task_id)
        if not task:
            return None
        return TaskResponse(**{k: v for k, v in task.items() if k != "data"})

    def get_task_result(self, task_id: str) -> TaskResult | None:
        task = self._tasks.get(task_id)
        if not task:
            return None
        return TaskResult(**task)

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskResponse]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        tasks.sort(key=lambda t: t["created_at"], reverse=True)
        return [
            TaskResponse(**{k: v for k, v in t.items() if k != "data"})
            for t in tasks[offset : offset + limit]
        ]

    def delete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save()
            return True
        return False

    def _save(self) -> None:
        if not self._persist_path:
            return
        try:
            serializable = {}
            for tid, task in self._tasks.items():
                t = dict(task)
                for key in ("created_at", "completed_at"):
                    if t[key]:
                        t[key] = t[key].isoformat()
                if t["status"]:
                    t["status"] = t["status"].value
                if t["task_type"]:
                    t["task_type"] = t["task_type"].value
                serializable[tid] = t
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(json.dumps(serializable, default=str, indent=2))
        except Exception:
            logger.warning("Failed to persist tasks", exc_info=True)

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            raw = json.loads(self._persist_path.read_text())
            for tid, task in raw.items():
                for key in ("created_at", "completed_at"):
                    if task[key]:
                        task[key] = datetime.fromisoformat(task[key])
                if task["status"]:
                    task["status"] = TaskStatus(task["status"])
                if task.get("task_type"):
                    task["task_type"] = TaskType(task["task_type"])
                self._tasks[tid] = task
        except Exception:
            logger.warning("Failed to load tasks", exc_info=True)
