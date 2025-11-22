#!/usr/bin/env python3
"""
IMMA Championship Bot - Telegram бот для управления CS2 турнирами.

Запуск: python bot.py
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
from database import db
from handlers import setup_routers
from services.scheduler import init_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота."""
    logger.info("Подключение к базе данных...")
    await db.connect()

    # Инициализация планировщика
    logger.info("Инициализация планировщика...")
    scheduler = init_scheduler(bot)
    scheduler.start()

    # Перепланирование задач для активных турниров
    await scheduler.reschedule_all_tournaments()

    # Информация о боте
    bot_info = await bot.get_me()
    logger.info(f"Бот запущен: @{bot_info.username}")


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота."""
    logger.info("Остановка бота...")

    # Остановка планировщика
    from services.scheduler import get_scheduler
    scheduler = get_scheduler()
    if scheduler:
        scheduler.stop()

    # Отключение от БД
    await db.disconnect()
    logger.info("Бот остановлен")


async def main() -> None:
    """Главная функция запуска бота."""
    # Проверка токена
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен! Создайте файл .env")
        sys.exit(1)

    # Создание бота и диспетчера
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    # Регистрация роутеров
    router = setup_routers()
    dp.include_router(router)

    # Регистрация startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запуск polling
    logger.info("Запуск бота...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)
