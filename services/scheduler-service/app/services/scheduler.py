"""Scheduler service using APScheduler."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from urllib.parse import urlparse
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED,
    JobExecutionEvent
)

from app.config import settings
from app.models.job import JobDefinition, JobRun, JobStatus, JobTriggerType
from app.repositories.job_history import job_history_repo

logger = logging.getLogger(__name__)


class SchedulerService:
    """Centralized job scheduler service."""

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._job_runs: Dict[str, List[JobRun]] = {}  # In-memory run history
        self._max_history = 100  # Max runs to keep per job

    def initialize(self, redis_url: str = None):
        """Initialize the scheduler with Redis job store."""
        redis_url = redis_url or settings.redis_url

        jobstores = {
            'default': RedisJobStore(
                jobs_key=f'{settings.redis_jobs_key_prefix}jobs',
                run_times_key=f'{settings.redis_jobs_key_prefix}run_times',
                host=urlparse(redis_url).hostname or 'localhost',
                port=urlparse(redis_url).port or 6379,
                db=int((urlparse(redis_url).path or '/0').lstrip('/') or '0'),
                password=urlparse(redis_url).password or None,
            )
        }

        executors = {
            'default': ThreadPoolExecutor(20),
            'processpool': ProcessPoolExecutor(5)
        }

        job_defaults = {
            'coalesce': settings.job_coalesce,
            'max_instances': settings.job_max_instances,
            'misfire_grace_time': settings.job_misfire_grace_time
        }

        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        # Add event listeners
        self._scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)
        self._scheduler.add_listener(self._on_job_missed, EVENT_JOB_MISSED)

        logger.info("Scheduler initialized with Redis job store")

    def start(self):
        """Start the scheduler."""
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown")

    def add_job(
        self,
        job_def: JobDefinition,
        func: Callable,
        replace_existing: bool = True
    ):
        """Add a job to the scheduler."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        # Build trigger
        if job_def.trigger_type == JobTriggerType.CRON:
            trigger = CronTrigger(**job_def.trigger_args)
        elif job_def.trigger_type == JobTriggerType.INTERVAL:
            trigger = IntervalTrigger(**job_def.trigger_args)
        else:
            raise ValueError(f"Unsupported trigger type: {job_def.trigger_type}")

        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_def.id,
            name=job_def.name,
            args=job_def.args,
            kwargs=job_def.kwargs,
            max_instances=job_def.max_instances,
            coalesce=job_def.coalesce,
            misfire_grace_time=job_def.misfire_grace_time,
            replace_existing=replace_existing
        )

        logger.info(f"Job added: {job_def.id} ({job_def.name})")

    def remove_job(self, job_id: str):
        """Remove a job from the scheduler."""
        if self._scheduler:
            self._scheduler.remove_job(job_id)
            logger.info(f"Job removed: {job_id}")

    def pause_job(self, job_id: str):
        """Pause a job."""
        if self._scheduler:
            self._scheduler.pause_job(job_id)
            logger.info(f"Job paused: {job_id}")

    def resume_job(self, job_id: str):
        """Resume a paused job."""
        if self._scheduler:
            self._scheduler.resume_job(job_id)
            logger.info(f"Job resumed: {job_id}")

    def run_job_now(self, job_id: str):
        """Trigger immediate job execution."""
        if self._scheduler:
            job = self._scheduler.get_job(job_id)
            if job:
                self._scheduler.modify_job(job_id, next_run_time=datetime.now(timezone.utc))
                logger.info(f"Job triggered: {job_id}")

    def get_jobs(self) -> List[dict]:
        """Get all scheduled jobs."""
        if not self._scheduler:
            return []

        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'pending': job.pending,
            })
        return jobs

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get a specific job."""
        if not self._scheduler:
            return None

        job = self._scheduler.get_job(job_id)
        if not job:
            return None

        return {
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
            'pending': job.pending,
        }

    def get_job_history(self, job_id: str, limit: int = 10) -> List[JobRun]:
        """Get execution history for a job."""
        runs = self._job_runs.get(job_id, [])
        return runs[-limit:]

    def _on_job_executed(self, event: JobExecutionEvent):
        """Handle successful job execution."""
        run = JobRun(
            id=f"{event.job_id}_{event.scheduled_run_time.timestamp()}",
            job_id=event.job_id,
            status=JobStatus.SUCCESS,
            started_at=event.scheduled_run_time,
            finished_at=datetime.now(timezone.utc),
            duration_seconds=(datetime.now(timezone.utc) - event.scheduled_run_time).total_seconds()
        )
        self._add_run_to_history(event.job_id, run)

        # Persist to database
        try:
            job_history_repo.save_run(run)
        except Exception as e:
            logger.error(f"Failed to persist job history: {e}")

        if settings.log_job_execution:
            logger.info(f"Job executed successfully: {event.job_id}")

    def _on_job_error(self, event: JobExecutionEvent):
        """Handle job execution error."""
        run = JobRun(
            id=f"{event.job_id}_{event.scheduled_run_time.timestamp()}",
            job_id=event.job_id,
            status=JobStatus.FAILED,
            started_at=event.scheduled_run_time,
            finished_at=datetime.now(timezone.utc),
            error_message=str(event.exception) if event.exception else "Unknown error"
        )
        self._add_run_to_history(event.job_id, run)

        # Persist to database
        try:
            job_history_repo.save_run(run)
        except Exception as e:
            logger.error(f"Failed to persist job history: {e}")

        # Send failure alert
        self._send_failure_alert(event.job_id, run.error_message)

        logger.error(f"Job failed: {event.job_id} - {event.exception}")

    def _send_failure_alert(self, job_id: str, error_message: str):
        """Send Discord alert for job failure."""
        try:
            from app.services.notifications import send_job_failure_alert
            send_job_failure_alert(job_id, error_message)
        except Exception as e:
            logger.error(f"Failed to send failure alert: {e}")

    def _on_job_missed(self, event: JobExecutionEvent):
        """Handle missed job execution."""
        run = JobRun(
            id=f"{event.job_id}_{event.scheduled_run_time.timestamp()}",
            job_id=event.job_id,
            status=JobStatus.SKIPPED,
            started_at=event.scheduled_run_time,
            finished_at=datetime.now(timezone.utc),
            error_message="Job execution missed"
        )
        self._add_run_to_history(event.job_id, run)

        # Persist to database
        try:
            job_history_repo.save_run(run)
        except Exception as e:
            logger.error(f"Failed to persist job history: {e}")

        logger.warning(f"Job missed: {event.job_id}")

    def _add_run_to_history(self, job_id: str, run: JobRun):
        """Add a run to the job history."""
        if job_id not in self._job_runs:
            self._job_runs[job_id] = []
        
        self._job_runs[job_id].append(run)
        
        # Trim history if too long
        if len(self._job_runs[job_id]) > self._max_history:
            self._job_runs[job_id] = self._job_runs[job_id][-self._max_history:]


# Global scheduler instance
scheduler_service = SchedulerService()
