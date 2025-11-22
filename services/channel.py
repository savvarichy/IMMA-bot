"""Сервис работы с каналом и постами турниров."""
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from database import db
from keyboards import Emoji
from utils import format_datetime, format_prizes, get_time_until, format_prize_value
from config import config


class ChannelService:
    """Сервис для работы с каналом."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def check_bot_permissions(self, channel_id: int) -> tuple[bool, str]:
        """
        Проверить права бота в канале.
        Возвращает (success, error_message).
        """
        try:
            chat = await self.bot.get_chat(channel_id)
            member = await self.bot.get_chat_member(channel_id, self.bot.id)

            if member.status not in ("administrator", "creator"):
                return False, "Бот должен быть администратором канала"

            # Проверяем права на публикацию и редактирование
            if hasattr(member, "can_post_messages") and not member.can_post_messages:
                return False, "Боту нужно право на публикацию сообщений"

            if hasattr(member, "can_edit_messages") and not member.can_edit_messages:
                return False, "Боту нужно право на редактирование сообщений"

            return True, ""
        except TelegramBadRequest as e:
            return False, f"Ошибка: {e.message}"
        except Exception as e:
            return False, f"Не удалось проверить канал: {str(e)}"

    async def get_bot_username(self) -> str:
        """Получить username бота."""
        bot_info = await self.bot.get_me()
        return bot_info.username

    def generate_post_text(
        self,
        tournament: dict,
        participant_count: int,
        bot_username: str
    ) -> str:
        """Генерация текста поста для канала."""
        format_name = config.TOURNAMENT_FORMATS.get(
            tournament["format"], {}
        ).get("name", tournament["format"])

        maps_list = tournament.get("maps", [])
        maps_text = ", ".join(m.replace("de_", "").capitalize() for m in maps_list)

        prize_text = format_prizes(tournament)
        progress = Emoji.progress_bar(participant_count, tournament["max_participants"])

        # Время до начала
        time_until = get_time_until(tournament["start_time"])

        # Для командных форматов показываем "Команды"
        participant_label = "Команды" if tournament["format"] != "1v1" else "Участники"

        text = f"""🏆 <b>IMMA Championship</b>

📛 <b>{tournament['name']}</b>

🎮 Формат: <b>{format_name}</b>
🗺️ Карты: {maps_text}

👥 {participant_label}: <b>{participant_count}/{tournament['max_participants']}</b>
{progress}

🎁 Призы:
{prize_text}

📅 {format_datetime(tournament['start_time'])}
⏰ До начала: <b>{time_until}</b>"""

        # Добавляем статус
        # Проверяем "скоро начало" - если до старта меньше 15 минут
        from datetime import datetime
        start_time = tournament["start_time"]
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        minutes_until = (start_time - datetime.now()).total_seconds() / 60

        if tournament["status"] == "open":
            if 0 < minutes_until <= config.STARTING_SOON_MINUTES:
                text += "\n\n⏰ <b>Скоро начало!</b>"
            else:
                text += "\n\n✅ <b>Регистрация открыта!</b>"
        elif tournament["status"] == "checkin":
            if 0 < minutes_until <= config.STARTING_SOON_MINUTES:
                text += "\n\n⏰ <b>Скоро начало! Check-in идёт!</b>"
            else:
                text += "\n\n🔔 <b>Check-in идёт!</b>"
        elif tournament["status"] == "active":
            text += "\n\n🔥 <b>Турнир идёт!</b>"
        elif tournament["status"] == "finished":
            text += "\n\n🏁 <b>Турнир завершён</b>"

        return text

    def generate_post_keyboard(
        self,
        tournament_id: int,
        bot_username: str,
        tournament_status: str
    ) -> Optional[InlineKeyboardMarkup]:
        """Генерация клавиатуры для поста."""
        if tournament_status not in ("open", "checkin"):
            return None

        button_text = "🎯 Участвовать" if tournament_status == "open" else "🔔 Check-in"
        url = f"https://t.me/{bot_username}?start=reg_{tournament_id}"

        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=url)]
        ])

    async def publish_post(self, tournament_id: int) -> tuple[bool, str]:
        """
        Опубликовать пост о турнире в канал.
        Возвращает (success, message).
        """
        # Получаем канал
        channel = await db.get_channel()
        if not channel:
            return False, "Канал не привязан. Сначала привяжите канал."

        # Получаем турнир
        tournament = await db.get_tournament(tournament_id)
        if not tournament:
            return False, "Турнир не найден"

        # Проверяем права
        has_rights, error = await self.check_bot_permissions(channel["channel_id"])
        if not has_rights:
            return False, error

        # Получаем количество участников
        participant_count = await db.get_tournament_participant_count(tournament_id)

        # Генерируем пост
        bot_username = await self.get_bot_username()
        text = self.generate_post_text(tournament, participant_count, bot_username)
        keyboard = self.generate_post_keyboard(tournament_id, bot_username, tournament["status"])

        try:
            # Публикуем
            message = await self.bot.send_message(
                channel["channel_id"],
                text,
                parse_mode="HTML",
                reply_markup=keyboard
            )

            # Сохраняем информацию о посте
            await db.save_tournament_post(
                tournament_id,
                channel["channel_id"],
                message.message_id
            )

            return True, "Пост опубликован!"
        except Exception as e:
            return False, f"Ошибка публикации: {str(e)}"

    async def update_post(self, tournament_id: int) -> tuple[bool, str]:
        """
        Обновить пост о турнире в канале.
        Возвращает (success, message).
        """
        # Получаем информацию о посте
        post = await db.get_tournament_post(tournament_id)
        if not post:
            return False, "Пост не найден"

        # Получаем турнир
        tournament = await db.get_tournament(tournament_id)
        if not tournament:
            return False, "Турнир не найден"

        # Получаем количество участников
        participant_count = await db.get_tournament_participant_count(tournament_id)

        # Генерируем обновлённый пост
        bot_username = await self.get_bot_username()
        text = self.generate_post_text(tournament, participant_count, bot_username)
        keyboard = self.generate_post_keyboard(tournament_id, bot_username, tournament["status"])

        try:
            await self.bot.edit_message_text(
                text,
                chat_id=post["channel_id"],
                message_id=post["message_id"],
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return True, "Пост обновлён!"
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return True, "Изменений нет"
            return False, f"Ошибка: {e.message}"
        except Exception as e:
            return False, f"Ошибка обновления: {str(e)}"

    async def delete_post(self, tournament_id: int) -> tuple[bool, str]:
        """
        Удалить пост о турнире из канала.
        Возвращает (success, message).
        """
        post = await db.get_tournament_post(tournament_id)
        if not post:
            return False, "Пост не найден"

        try:
            await self.bot.delete_message(
                chat_id=post["channel_id"],
                message_id=post["message_id"]
            )
            await db.delete_tournament_post(tournament_id)
            return True, "Пост удалён!"
        except Exception as e:
            # Удаляем запись даже если сообщение уже удалено
            await db.delete_tournament_post(tournament_id)
            return True, "Запись удалена"

    async def generate_results_text(
        self,
        tournament: dict,
        standings: list[dict],
        matches: list[dict],
        participants_names: dict[int, str]
    ) -> str:
        """Генерация текста результатов турнира для канала."""
        format_name = config.TOURNAMENT_FORMATS.get(
            tournament["format"], {}
        ).get("name", tournament["format"])

        # Получаем призы для отображения
        prizes = tournament.get("prizes", {}) or {}
        prize_type = tournament.get("prize_type", "none")
        if isinstance(prizes, str):
            import json
            try:
                prizes = json.loads(prizes)
            except Exception:
                prizes = {}

        # Преобразуем в список с форматированием валюты
        if isinstance(prizes, dict):
            prizes_list = [
                format_prize_value(prizes.get(str(i + 1), ""), prize_type)
                for i in range(3)
            ]
        else:
            prizes_list = [
                format_prize_value(p, prize_type) for p in (list(prizes)[:3] if prizes else [])
            ]

        text = f"""🏆 <b>ТУРНИР ЗАВЕРШЁН!</b>

📛 <b>{tournament['name']}</b>
🎮 Формат: {format_name}

🏅 <b>ПРИЗЁРЫ:</b>

"""
        # Медали для мест - только ТОП-3
        place_medals = ["🥇", "🥈", "🥉"]

        for i, s in enumerate(standings[:3]):  # Только первые 3 места
            pid = s["participant_id"]
            name = participants_names.get(pid, f"ID:{pid}")
            wins = s.get("wins", 0)
            losses = s.get("losses", 0)

            place_icon = place_medals[i]

            prize_info = ""
            if i < len(prizes_list) and prizes_list[i]:
                prize_info = f" — <b>{prizes_list[i]}</b>"

            text += f"{place_icon} {name} ({wins}W/{losses}L){prize_info}\n"

        # История матчей в сворачиваемом блоке
        completed_matches = [m for m in matches if m["status"] == "completed"]
        if completed_matches:
            text += f"\n⚔️ <b>ИСТОРИЯ МАТЧЕЙ ({len(completed_matches)}):</b>\n"
            text += "<blockquote expandable>"

            for match in completed_matches:
                p1_name = participants_names.get(match["participant1_id"], "?")
                p2_name = participants_names.get(match["participant2_id"], "?")
                winner_id = match.get("winner_id")

                # Выделяем победителя
                if winner_id == match["participant1_id"]:
                    result_text = f"<b>{p1_name}</b> {match['score1']}:{match['score2']} {p2_name}"
                else:
                    result_text = f"{p1_name} {match['score1']}:{match['score2']} <b>{p2_name}</b>"

                text += f"• {result_text}\n"

            text += "</blockquote>"

        text += f"\n🏁 <b>IMMA Championship</b>"

        return text

    async def publish_results(self, tournament_id: int) -> tuple[bool, str]:
        """
        Обновить пост в канале результатами турнира.
        Возвращает (success, message).
        """
        # Получаем пост
        post = await db.get_tournament_post(tournament_id)
        if not post:
            return False, "Пост не найден в канале"

        # Получаем турнир
        tournament = await db.get_tournament(tournament_id)
        if not tournament:
            return False, "Турнир не найден"

        # Получаем статистику участников
        standings = await db.get_tournament_standings(tournament_id)
        sorted_standings = sorted(
            standings,
            key=lambda x: (-x.get("wins", 0), x.get("losses", 0))
        )

        # Получаем имена участников
        participants_names = {}
        for s in sorted_standings:
            if s["participant_type"] == "player":
                p = await db.get_player_by_id(s["participant_id"])
                participants_names[s["participant_id"]] = p["nickname"] if p else f"ID:{s['participant_id']}"
            else:
                t = await db.get_team(s["participant_id"])
                participants_names[s["participant_id"]] = t["name"] if t else f"ID:{s['participant_id']}"

        # Получаем матчи
        matches = await db.get_tournament_matches(tournament_id)

        # Генерируем текст результатов
        text = await self.generate_results_text(
            tournament, sorted_standings, matches, participants_names
        )

        try:
            await self.bot.edit_message_text(
                text,
                chat_id=post["channel_id"],
                message_id=post["message_id"],
                parse_mode="HTML",
                reply_markup=None  # Убираем кнопку регистрации
            )
            return True, "Результаты опубликованы в канал!"
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return True, "Изменений нет"
            return False, f"Ошибка: {e.message}"
        except Exception as e:
            return False, f"Ошибка обновления: {str(e)}"


# Глобальный экземпляр (инициализируется в bot.py)
channel_service: Optional[ChannelService] = None


def get_channel_service() -> Optional[ChannelService]:
    """Получить экземпляр сервиса."""
    return channel_service


def init_channel_service(bot: Bot) -> ChannelService:
    """Инициализация сервиса."""
    global channel_service
    channel_service = ChannelService(bot)
    return channel_service
