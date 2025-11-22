"""Конфигурация бота."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Настройки бота."""

    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list[int] = [
        int(x.strip())
        for x in os.getenv("ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    ]
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_database.db")

    # Форматы турниров
    TOURNAMENT_FORMATS = {
        "1v1": {"team_size": 1, "name": "1v1 (Соло)"},
        "2v2": {"team_size": 2, "name": "2v2 (Команды)"},
        "5v5": {"team_size": 5, "name": "5v5 (Команды)"},
    }

    # Карты CS2
    CS2_MAPS = [
        "de_mirage", "de_inferno", "de_nuke", "de_overpass",
        "de_vertigo", "de_ancient", "de_anubis", "de_dust2"
    ]

    # Варианты количества участников
    PARTICIPANT_OPTIONS = [8, 16, 32, 64]

    # Типы призов
    PRIZE_TYPES = {
        "none": "Без приза",
        "stars": "TG Stars ⭐",
        "skins": "Скины CS2",
        "rub": "Рубли ₽",
        "custom": "Своё описание"
    }

    # Эмодзи для призовых мест
    PRIZE_PLACES = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    # Варианты времени check-in (часы до старта)
    CHECKIN_OPTIONS = [0, 1, 2, 3]  # 0 = без check-in

    # Статусы турнира
    TOURNAMENT_STATUSES = {
        "draft": "Черновик",
        "open": "Регистрация открыта",
        "starting_soon": "Скоро начало",
        "checkin": "Check-in",
        "active": "Идёт турнир",
        "finished": "Завершён",
        "cancelled": "Отменён"
    }

    # Время жизни инвайт-кода команды (секунды)
    INVITE_CODE_LIFETIME = 24 * 60 * 60  # 24 часа

    # Лимит активных турниров на игрока (0 = без лимита)
    MAX_ACTIVE_TOURNAMENTS_PER_PLAYER = 3

    # Лимит резервного списка (максимум игроков в резерве)
    RESERVE_LIST_SIZE = 5

    # Время до начала для статуса "Скоро начало" (минуты)
    STARTING_SOON_MINUTES = 15

    # Шаблоны турниров
    TOURNAMENT_TEMPLATES = {
        "evening_1v1": {
            "name": "Вечерний 1v1",
            "format": "1v1",
            "max_participants": 16,
            "prize_type": "rub",
            "prize_amount": 500,
            "default_hour": 20,
            "default_minute": 0,
            "maps": ["de_mirage", "de_inferno", "de_dust2"]
        },
        "weekend_5v5": {
            "name": "Выходной 5v5",
            "format": "5v5",
            "max_participants": 8,
            "prize_type": "rub",
            "prize_amount": 5000,
            "default_hour": 15,
            "default_minute": 0,
            "maps": ["de_mirage", "de_inferno", "de_nuke", "de_overpass", "de_ancient"]
        },
        "mini_tournament": {
            "name": "Мини-турнир",
            "format": "1v1",
            "max_participants": 8,
            "prize_type": "none",
            "prize_amount": 0,
            "default_hour": 19,
            "default_minute": 0,
            "maps": ["de_mirage", "de_dust2"]
        }
    }


config = Config()
