"""Система уведомлений."""
from typing import Optional
from aiogram import Bot

from database import db
from keyboards import Emoji
from utils import format_datetime, escape_html


class NotificationService:
    """Сервис отправки уведомлений."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_to_user(
        self,
        telegram_id: int,
        text: str,
        reply_markup=None
    ) -> bool:
        """Отправка сообщения пользователю."""
        try:
            await self.bot.send_message(
                telegram_id,
                text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            return True
        except Exception:
            return False

    async def notify_tournament_open(self, tournament_id: int) -> int:
        """Уведомление об открытии регистрации."""
        tournament = await db.get_tournament(tournament_id)
        if not tournament:
            return 0

        text = (
            f"{Emoji.BELL} <b>Открыта регистрация!</b>\n\n"
            f"{Emoji.TROPHY} <b>{escape_html(tournament['name'])}</b>\n"
            f"{Emoji.GAME} Формат: {tournament['format']}\n"
            f"{Emoji.CALENDAR} Старт: {format_datetime(tournament['start_time'])}\n\n"
            f"Поспешите зарегистрироваться!"
        )

        # Отправляем всем игрокам (можно ограничить)
        players = await db.get_all_players()
        sent = 0

        for player in players:
            if not player["is_banned"]:
                if await self.send_to_user(player["telegram_id"], text):
                    sent += 1

        return sent

    async def notify_checkin_start(self, tournament_id: int) -> int:
        """Уведомление о начале check-in."""
        tournament = await db.get_tournament(tournament_id)
        if not tournament:
            return 0

        text = (
            f"{Emoji.BELL} <b>Check-in открыт!</b>\n\n"
            f"{Emoji.TROPHY} <b>{escape_html(tournament['name'])}</b>\n"
            f"{Emoji.CALENDAR} Старт: {format_datetime(tournament['start_time'])}\n\n"
            f"{Emoji.WARNING} Не забудьте подтвердить участие!"
        )

        return await self._notify_tournament_participants(tournament_id, text)

    async def notify_tournament_start(self, tournament_id: int) -> int:
        """Уведомление о старте турнира."""
        tournament = await db.get_tournament(tournament_id)
        if not tournament:
            return 0

        text = (
            f"{Emoji.FIRE} <b>Турнир начался!</b>\n\n"
            f"{Emoji.TROPHY} <b>{escape_html(tournament['name'])}</b>\n\n"
            f"Ожидайте свой матч, администратор скоро назначит соперника."
        )

        return await self._notify_tournament_participants(tournament_id, text)

    async def notify_reminder(
        self,
        tournament_id: int,
        minutes_before: int
    ) -> int:
        """Напоминание о скором старте."""
        tournament = await db.get_tournament(tournament_id)
        if not tournament:
            return 0

        if minutes_before == 60:
            time_text = "1 час"
        elif minutes_before == 30:
            time_text = "30 минут"
        elif minutes_before == 15:
            time_text = "15 минут"
        else:
            time_text = f"{minutes_before} мин."

        text = (
            f"{Emoji.CLOCK} <b>Напоминание!</b>\n\n"
            f"{Emoji.TROPHY} <b>{escape_html(tournament['name'])}</b>\n\n"
            f"До начала турнира осталось <b>{time_text}</b>!\n"
        )

        if tournament["status"] == "checkin":
            text += f"\n{Emoji.WARNING} Не забудьте пройти check-in!"

        return await self._notify_tournament_participants(tournament_id, text)

    async def notify_match_ready(
        self,
        match_id: int,
        opponent_name: str,
        participant_telegram_ids: list[int]
    ) -> int:
        """Уведомление о следующем матче."""
        match = await db.get_match(match_id)
        if not match:
            return 0

        text = (
            f"{Emoji.SWORD} <b>Ваш матч готов!</b>\n\n"
            f"Раунд: {match['round']}\n"
            f"Соперник: <b>{escape_html(opponent_name)}</b>\n"
        )

        if match.get("map"):
            text += f"Карта: {match['map'].replace('de_', '')}\n"

        sent = 0
        for tid in participant_telegram_ids:
            if await self.send_to_user(tid, text):
                sent += 1

        return sent

    async def notify_match_result(
        self,
        match_id: int,
        winner_name: str,
        loser_name: str,
        score: str,
        winner_telegram_ids: list[int],
        loser_telegram_ids: list[int]
    ) -> int:
        """Уведомление о результате матча."""
        win_text = (
            f"{Emoji.TROPHY} <b>Победа!</b>\n\n"
            f"Вы победили <b>{escape_html(loser_name)}</b>\n"
            f"Счёт: {score}\n\n"
            f"Ожидайте следующего матча!"
        )

        lose_text = (
            f"{Emoji.CROSS} <b>Поражение</b>\n\n"
            f"Победитель: <b>{escape_html(winner_name)}</b>\n"
            f"Счёт: {score}\n\n"
            f"Спасибо за участие!"
        )

        sent = 0
        for tid in winner_telegram_ids:
            if await self.send_to_user(tid, win_text):
                sent += 1

        for tid in loser_telegram_ids:
            if await self.send_to_user(tid, lose_text):
                sent += 1

        return sent

    async def notify_tournament_winner(
        self,
        tournament_id: int,
        winner_name: str,
        winner_telegram_ids: list[int]
    ) -> int:
        """Уведомление о победе в турнире."""
        tournament = await db.get_tournament(tournament_id)
        if not tournament:
            return 0

        winner_text = (
            f"{Emoji.TROPHY}{Emoji.TROPHY}{Emoji.TROPHY}\n"
            f"<b>ПОЗДРАВЛЯЕМ!</b>\n\n"
            f"Вы выиграли турнир\n"
            f"<b>{escape_html(tournament['name'])}</b>!\n\n"
            f"{Emoji.MEDAL} Вы - чемпион!"
        )

        all_participants_text = (
            f"{Emoji.TROPHY} <b>Турнир завершён!</b>\n\n"
            f"<b>{escape_html(tournament['name'])}</b>\n\n"
            f"Победитель: <b>{escape_html(winner_name)}</b>\n\n"
            f"Спасибо всем участникам!"
        )

        sent = 0

        # Уведомляем победителя
        for tid in winner_telegram_ids:
            if await self.send_to_user(tid, winner_text):
                sent += 1

        # Уведомляем остальных участников
        sent += await self._notify_tournament_participants(
            tournament_id,
            all_participants_text,
            exclude_ids=winner_telegram_ids
        )

        return sent

    async def _notify_tournament_participants(
        self,
        tournament_id: int,
        text: str,
        exclude_ids: Optional[list[int]] = None
    ) -> int:
        """Отправка уведомления всем участникам турнира."""
        tournament = await db.get_tournament(tournament_id)
        if not tournament:
            return 0

        exclude_ids = exclude_ids or []
        telegram_ids = []

        if tournament["format"] == "1v1":
            players = await db.get_tournament_players(tournament_id)
            telegram_ids = [p["telegram_id"] for p in players]
        else:
            teams = await db.get_tournament_teams(tournament_id)
            for team in teams:
                members = await db.get_team_members(team["id"])
                telegram_ids.extend([m["telegram_id"] for m in members])

        sent = 0
        for tid in telegram_ids:
            if tid not in exclude_ids:
                if await self.send_to_user(tid, text):
                    sent += 1

        return sent
