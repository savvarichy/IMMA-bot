"""Планировщик задач для автоматических уведомлений."""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from aiogram import Bot

from database import db
from config import config


class SchedulerService:
    """Сервис планирования задач."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)
        self._notification_service = None

    @property
    def notification_service(self):
        """Ленивая инициализация NotificationService."""
        if self._notification_service is None:
            from services.notifications import NotificationService
            self._notification_service = NotificationService(self.bot)
        return self._notification_service

    def start(self) -> None:
        """Запуск планировщика."""
        self.scheduler.start()

    def stop(self) -> None:
        """Остановка планировщика."""
        self.scheduler.shutdown()

    async def schedule_tournament_reminders(self, tournament_id: int) -> None:
        """
        Планирование напоминаний для турнира.
        Создаёт задачи за 60, 30 и 15 минут до старта.
        """
        tournament = await db.get_tournament(tournament_id)
        if not tournament:
            return

        start_time = tournament["start_time"]
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)

        # Убираем timezone info для консистентности
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)

        now = datetime.now()

        # Напоминание за 60 минут
        remind_60 = start_time - timedelta(minutes=60)
        if remind_60 > now:
            self.scheduler.add_job(
                self._send_reminder,
                DateTrigger(run_date=remind_60),
                args=[tournament_id, 60],
                id=f"reminder_{tournament_id}_60",
                replace_existing=True
            )

        # Напоминание за 30 минут
        remind_30 = start_time - timedelta(minutes=30)
        if remind_30 > now:
            self.scheduler.add_job(
                self._send_reminder,
                DateTrigger(run_date=remind_30),
                args=[tournament_id, 30],
                id=f"reminder_{tournament_id}_30",
                replace_existing=True
            )

        # Напоминание за 15 минут
        remind_15 = start_time - timedelta(minutes=15)
        if remind_15 > now:
            self.scheduler.add_job(
                self._send_reminder,
                DateTrigger(run_date=remind_15),
                args=[tournament_id, 15],
                id=f"reminder_{tournament_id}_15",
                replace_existing=True
            )

        # Автоматический check-in (если настроен)
        checkin_hours = tournament.get("checkin_hours") or 0
        if checkin_hours > 0:
            checkin_time = start_time - timedelta(hours=tournament["checkin_hours"])
            if checkin_time > now:
                self.scheduler.add_job(
                    self._start_checkin,
                    DateTrigger(run_date=checkin_time),
                    args=[tournament_id],
                    id=f"checkin_{tournament_id}",
                    replace_existing=True
                )

    async def _send_reminder(self, tournament_id: int, minutes_before: int) -> None:
        """Отправка напоминания."""
        tournament = await db.get_tournament(tournament_id)
        if not tournament or tournament["status"] in ("finished", "cancelled"):
            return

        await self.notification_service.notify_reminder(tournament_id, minutes_before)

    async def _start_checkin(self, tournament_id: int) -> None:
        """Автоматический запуск check-in."""
        tournament = await db.get_tournament(tournament_id)
        if not tournament or tournament["status"] != "open":
            return

        await db.update_tournament_status(tournament_id, "checkin")
        await self.notification_service.notify_checkin_start(tournament_id)

    def cancel_tournament_jobs(self, tournament_id: int) -> None:
        """Отмена всех задач турнира."""
        job_ids = [
            f"reminder_{tournament_id}_60",
            f"reminder_{tournament_id}_30",
            f"reminder_{tournament_id}_15",
            f"checkin_{tournament_id}"
        ]

        for job_id in job_ids:
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass

    async def reschedule_all_tournaments(self) -> None:
        """Перепланирование всех активных турниров (при перезапуске бота)."""
        tournaments = await db.get_tournaments_by_status("open")
        tournaments.extend(await db.get_tournaments_by_status("checkin"))

        for tournament in tournaments:
            await self.schedule_tournament_reminders(tournament["id"])


# Глобальный экземпляр (инициализируется в bot.py)
scheduler: Optional[SchedulerService] = None


def get_scheduler() -> Optional[SchedulerService]:
    """Получить экземпляр планировщика."""
    return scheduler


def init_scheduler(bot: Bot) -> SchedulerService:
    """Инициализация планировщика."""
    global scheduler
    scheduler = SchedulerService(bot)
    return scheduler
