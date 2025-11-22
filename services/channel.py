"""Сервис работы с каналом и постами турниров."""
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from database import db
from keyboards import Emoji
from utils import format_datetime, format_prize, get_time_until
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

        prize_text = format_prize(tournament["prize_type"], tournament["prize_amount"])
        progress = Emoji.progress_bar(participant_count, tournament["max_participants"])

        # Время до начала
        time_until = get_time_until(tournament["start_time"])

        text = f"""🏆 <b>IMMA Championship</b>

📛 <b>{tournament['name']}</b>

🎮 Формат: <b>{format_name}</b>
🗺️ Карты: {maps_text}

👥 Участники: <b>{participant_count}/{tournament['max_participants']}</b>
{progress}

🎁 Приз: <b>{prize_text}</b>
📅 {format_datetime(tournament['start_time'])}
⏰ До начала: <b>{time_until}</b>"""

        # Добавляем статус
        if tournament["status"] == "open":
            text += "\n\n✅ <b>Регистрация открыта!</b>"
        elif tournament["status"] == "checkin":
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
