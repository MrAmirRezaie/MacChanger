"""
Scheduler - Handles scheduling and periodic MAC address changes.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum


class ScheduleFrequency(Enum):
    """Frequency options for scheduled tasks."""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # Custom interval in seconds


@dataclass
class ScheduledTask:
    """A scheduled MAC spoofing task."""
    name: str
    interface: str
    action: str  # "spoof_random", "spoof_specific", "restore"
    frequency: ScheduleFrequency
    enabled: bool = True
    mac_address: Optional[str] = None  # For spoof_specific action
    custom_interval_seconds: Optional[int] = None  # For custom frequency
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    max_runs: Optional[int] = None  # None = unlimited
    run_count: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['frequency'] = self.frequency.value
        return d

    def is_due(self) -> bool:
        """Check if task is due to run."""
        if self.next_run is None:
            return self.enabled

        next_run_time = datetime.fromisoformat(self.next_run)
        return datetime.now() >= next_run_time and self.enabled

    def update_next_run(self) -> None:
        """Calculate and update next run time."""
        if self.max_runs and self.run_count >= self.max_runs:
            self.next_run = None
            return

        now = datetime.now()

        if self.frequency == ScheduleFrequency.ONCE:
            self.next_run = None
        elif self.frequency == ScheduleFrequency.HOURLY:
            self.next_run = (now + timedelta(hours=1)).isoformat()
        elif self.frequency == ScheduleFrequency.DAILY:
            self.next_run = (now + timedelta(days=1)).isoformat()
        elif self.frequency == ScheduleFrequency.WEEKLY:
            self.next_run = (now + timedelta(weeks=1)).isoformat()
        elif self.frequency == ScheduleFrequency.MONTHLY:
            # Add 30 days as approximate month
            self.next_run = (now + timedelta(days=30)).isoformat()
        elif self.frequency == ScheduleFrequency.CUSTOM and self.custom_interval_seconds:
            self.next_run = (
                now + timedelta(seconds=self.custom_interval_seconds)
            ).isoformat()

    def record_execution(self) -> None:
        """Record execution of this task."""
        self.last_run = datetime.now().isoformat()
        self.run_count += 1
        self.update_next_run()


class Scheduler:
    """Manages scheduled MAC spoofing tasks."""

    def __init__(
        self,
        schedule_dir: Optional[str] = None,
        callback: Optional[Callable] = None
    ):
        """
        Initialize scheduler.

        Args:
            schedule_dir: Directory to store schedules
            callback: Callback function called when task is due (receives ScheduledTask)
        """
        self.logger = logging.getLogger(__name__)

        if schedule_dir is None:
            schedule_dir = str(Path.home() / ".mac-spoofer" / "schedules")

        self.schedule_dir = Path(schedule_dir)
        self.schedule_dir.mkdir(parents=True, exist_ok=True)

        self.tasks: Dict[str, ScheduledTask] = {}
        self.callback = callback
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None

        self._load_schedules()

    def _load_schedules(self) -> None:
        """Load schedules from disk."""
        try:
            for schedule_file in self.schedule_dir.glob("*.json"):
                try:
                    with open(schedule_file, 'r') as f:
                        task_data = json.load(f)
                        freq_str = task_data.get('frequency', 'once')
                        task_data['frequency'] = ScheduleFrequency(freq_str)
                        task = ScheduledTask(**task_data)
                        self.tasks[task.name] = task
                    self.logger.debug(f"Loaded schedule: {task.name}")
                except Exception as e:
                    self.logger.error(f"Error loading schedule {schedule_file}: {e}")
        except Exception as e:
            self.logger.error(f"Error loading schedules: {e}")

    def _save_schedule(self, task: ScheduledTask) -> bool:
        """Save a schedule to disk."""
        try:
            schedule_file = self.schedule_dir / f"{task.name}.json"
            with open(schedule_file, 'w') as f:
                json.dump(task.to_dict(), f, indent=2)
            self.logger.debug(f"Schedule saved: {task.name}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving schedule {task.name}: {e}")
            return False

    def create_task(
        self,
        name: str,
        interface: str,
        action: str,
        frequency: ScheduleFrequency,
        mac_address: Optional[str] = None,
        custom_interval_seconds: Optional[int] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        max_runs: Optional[int] = None
    ) -> Optional[ScheduledTask]:
        """
        Create a new scheduled task.

        Args:
            name: Task name (must be unique)
            interface: Target interface
            action: Action to perform (spoof_random, spoof_specific, restore)
            frequency: How often to run
            mac_address: For spoof_specific action
            custom_interval_seconds: For custom frequency
            description: Task description
            tags: Optional tags for organization
            max_runs: Maximum number of runs (None = unlimited)

        Returns:
            Created ScheduledTask or None on error
        """
        if name in self.tasks:
            self.logger.warning(f"Task '{name}' already exists")
            return None

        task = ScheduledTask(
            name=name,
            interface=interface,
            action=action,
            frequency=frequency,
            mac_address=mac_address,
            custom_interval_seconds=custom_interval_seconds,
            description=description,
            tags=tags or [],
            max_runs=max_runs
        )

        task.update_next_run()
        self.tasks[name] = task
        self._save_schedule(task)
        self.logger.info(f"Task created: {name}")
        return task

    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """Get a task by name."""
        return self.tasks.get(name)

    def list_tasks(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List all tasks."""
        tasks = []
        for task in self.tasks.values():
            if enabled_only and not task.enabled:
                continue
            tasks.append({
                'name': task.name,
                'interface': task.interface,
                'action': task.action,
                'frequency': task.frequency.value,
                'enabled': task.enabled,
                'next_run': task.next_run,
                'last_run': task.last_run,
                'run_count': task.run_count,
                'description': task.description
            })
        return sorted(tasks, key=lambda x: x['name'])

    def delete_task(self, name: str) -> bool:
        """Delete a task."""
        if name not in self.tasks:
            self.logger.warning(f"Task '{name}' not found")
            return False

        try:
            schedule_file = self.schedule_dir / f"{name}.json"
            if schedule_file.exists():
                schedule_file.unlink()

            del self.tasks[name]
            self.logger.info(f"Task deleted: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting task {name}: {e}")
            return False

    def enable_task(self, name: str) -> bool:
        """Enable a task."""
        task = self.get_task(name)
        if not task:
            return False

        task.enabled = True
        task.update_next_run()
        self._save_schedule(task)
        self.logger.info(f"Task enabled: {name}")
        return True

    def disable_task(self, name: str) -> bool:
        """Disable a task."""
        task = self.get_task(name)
        if not task:
            return False

        task.enabled = False
        self._save_schedule(task)
        self.logger.info(f"Task disabled: {name}")
        return True

    def get_due_tasks(self) -> List[ScheduledTask]:
        """Get all tasks that are due to run."""
        due_tasks = []
        for task in self.tasks.values():
            if task.is_due():
                due_tasks.append(task)
        return due_tasks

    def run_task(self, name: str) -> bool:
        """Manually run a task."""
        task = self.get_task(name)
        if not task:
            return False

        try:
            if self.callback:
                self.callback(task)
            task.record_execution()
            self._save_schedule(task)
            self.logger.info(f"Task executed: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Error running task {name}: {e}")
            return False

    def start(self, interval_seconds: int = 60) -> None:
        """
        Start the scheduler in background thread.

        Args:
            interval_seconds: Check interval for due tasks
        """
        if self.running:
            self.logger.warning("Scheduler is already running")
            return

        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.scheduler_thread.start()
        self.logger.info(f"Scheduler started (check interval: {interval_seconds}s)")

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.running:
            return

        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("Scheduler stopped")

    def _scheduler_loop(self, interval_seconds: int) -> None:
        """Main scheduler loop."""
        while self.running:
            try:
                due_tasks = self.get_due_tasks()
                for task in due_tasks:
                    self.run_task(task.name)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")

            time.sleep(interval_seconds)

    def search_tasks(self, keyword: str) -> List[Dict[str, Any]]:
        """Search tasks by keyword."""
        keyword_lower = keyword.lower()
        results = []

        for task in self.tasks.values():
            if (
                keyword_lower in task.name.lower()
                or keyword_lower in task.interface.lower()
                or keyword_lower in task.description.lower()
                or any(keyword_lower in tag.lower() for tag in task.tags)
            ):
                results.append({
                    'name': task.name,
                    'interface': task.interface,
                    'action': task.action,
                    'frequency': task.frequency.value,
                    'enabled': task.enabled,
                    'next_run': task.next_run
                })

        return results

    def clear_completed_tasks(self) -> int:
        """Delete tasks that have reached their max runs."""
        completed = []
        for task_name, task in self.tasks.items():
            if task.max_runs and task.run_count >= task.max_runs:
                completed.append(task_name)

        for task_name in completed:
            self.delete_task(task_name)

        if completed:
            self.logger.info(f"Cleared {len(completed)} completed tasks")

        return len(completed)

    def __str__(self) -> str:
        """String representation."""
        enabled_count = sum(1 for t in self.tasks.values() if t.enabled)
        return (
            f"Scheduler(total_tasks={len(self.tasks)}, "
            f"enabled={enabled_count}, running={self.running})"
        )


def test_scheduler():
    """Test the scheduler."""
    print("=" * 60)
    print("Scheduler Tests")
    print("=" * 60)

    logging.basicConfig(level=logging.INFO)

    def task_callback(task: ScheduledTask):
        print(f"[CALLBACK] Task executed: {task.name} on {task.interface}")

    scheduler = Scheduler(callback=task_callback)

    # Create some tasks
    print("\nCreating tasks...")
    scheduler.create_task(
        "daily_spoof_eth0",
        "eth0",
        "spoof_random",
        ScheduleFrequency.DAILY,
        description="Change MAC daily"
    )

    scheduler.create_task(
        "hourly_spoof_eth1",
        "eth1",
        "spoof_random",
        ScheduleFrequency.HOURLY,
        description="Change MAC hourly"
    )

    # List tasks
    print("\nScheduled tasks:")
    for task_info in scheduler.list_tasks():
        print(
            f"  - {task_info['name']}: {task_info['interface']} "
            f"({task_info['frequency']})"
        )

    print(f"\n{scheduler}")


if __name__ == "__main__":
    test_scheduler()
