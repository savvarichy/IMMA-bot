"""Модуль обработчиков."""
from aiogram import Router

from .user import router as user_router
from .teams import router as teams_router
from .tournaments import router as tournaments_router
from .matches import router as matches_router


def setup_routers() -> Router:
    """Настройка всех роутеров."""
    router = Router()
    router.include_router(user_router)
    router.include_router(teams_router)
    router.include_router(tournaments_router)
    router.include_router(matches_router)
    return router
