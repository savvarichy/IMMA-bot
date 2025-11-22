"""Клавиатуры и эмодзи для бота."""
from datetime import datetime, timedelta
from typing import Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config


class Emoji:
    """Класс с эмодзи для интерфейса."""

    # Общие
    HOME = "🏠"
    BACK = "◀️"
    NEXT = "▶️"
    CHECK = "✅"
    CROSS = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    STAR = "⭐"
    FIRE = "🔥"
    TROPHY = "🏆"
    MEDAL = "🥇"
    CLOCK = "🕐"
    CALENDAR = "📅"
    BELL = "🔔"
    GEAR = "⚙️"
    PENCIL = "✏️"
    TRASH = "🗑️"
    LOCK = "🔒"
    UNLOCK = "🔓"
    LINK = "🔗"
    PERSON = "👤"
    PEOPLE = "👥"
    CROWN = "👑"
    GAME = "🎮"
    TARGET = "🎯"
    CHART = "📊"
    LIST = "📋"
    MONEY = "💰"
    GIFT = "🎁"
    SEARCH = "🔍"
    PLUS = "➕"
    MINUS = "➖"
    PLAY = "▶️"
    PAUSE = "⏸️"
    STOP = "⏹️"
    REFRESH = "🔄"
    SEND = "📤"
    INBOX = "📥"
    KEY = "🔑"
    SHIELD = "🛡️"
    SWORD = "⚔️"
    MAP = "🗺️"
    PIN = "📍"
    FLAG = "🚩"
    BOOM = "💥"

    # Прогресс-бар
    FILLED = "▓"
    EMPTY = "░"

    @classmethod
    def progress_bar(cls, current: int, total: int, length: int = 10) -> str:
        """Создать прогресс-бар."""
        if total == 0:
            return cls.EMPTY * length
        filled = int((current / total) * length)
        return cls.FILLED * filled + cls.EMPTY * (length - filled)


class Keyboards:
    """Класс с клавиатурами."""

    # ==================== ГЛАВНОЕ МЕНЮ ====================

    @staticmethod
    def main_menu(is_registered: bool = False) -> InlineKeyboardMarkup:
        """Главное меню."""
        builder = InlineKeyboardBuilder()

        if not is_registered:
            builder.button(
                text=f"{Emoji.PENCIL} Регистрация",
                callback_data="register"
            )
        else:
            builder.button(
                text=f"{Emoji.TROPHY} Турниры",
                callback_data="tournaments"
            )
            builder.button(
                text=f"{Emoji.PEOPLE} Мои команды",
                callback_data="my_teams"
            )
            builder.button(
                text=f"{Emoji.PERSON} Мой профиль",
                callback_data="profile"
            )
            builder.button(
                text=f"{Emoji.CHART} Рейтинг",
                callback_data="rating"
            )

        builder.adjust(2)
        return builder.as_markup()

    @staticmethod
    def back_button(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
        """Кнопка назад."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{Emoji.BACK} Назад",
                callback_data=callback_data
            )]
        ])

    @staticmethod
    def confirm_cancel(
        confirm_data: str,
        cancel_data: str = "main_menu"
    ) -> InlineKeyboardMarkup:
        """Кнопки подтверждения/отмены."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{Emoji.CHECK} Подтвердить",
                    callback_data=confirm_data
                ),
                InlineKeyboardButton(
                    text=f"{Emoji.CROSS} Отмена",
                    callback_data=cancel_data
                )
            ]
        ])

    # ==================== РЕГИСТРАЦИЯ ====================

    @staticmethod
    def cancel_registration() -> InlineKeyboardMarkup:
        """Отмена регистрации."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{Emoji.CROSS} Отменить регистрацию",
                callback_data="cancel_registration"
            )]
        ])

    # ==================== ПРОФИЛЬ ====================

    @staticmethod
    def profile_menu() -> InlineKeyboardMarkup:
        """Меню профиля."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.PENCIL} Редактировать",
            callback_data="edit_profile"
        )
        builder.button(
            text=f"{Emoji.CHART} Моя статистика",
            callback_data="my_stats"
        )
        builder.button(
            text=f"{Emoji.BACK} Главное меню",
            callback_data="main_menu"
        )
        builder.adjust(2, 1)
        return builder.as_markup()

    @staticmethod
    def edit_profile_menu() -> InlineKeyboardMarkup:
        """Меню редактирования профиля."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.GAME} Изменить никнейм",
            callback_data="edit_nickname"
        )
        builder.button(
            text=f"{Emoji.LINK} Изменить Steam",
            callback_data="edit_steam"
        )
        builder.button(
            text=f"{Emoji.SEND} Изменить контакт",
            callback_data="edit_contact"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="profile"
        )
        builder.adjust(1)
        return builder.as_markup()

    # ==================== КОМАНДЫ ====================

    @staticmethod
    def teams_menu() -> InlineKeyboardMarkup:
        """Меню команд."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.PLUS} Создать команду",
            callback_data="create_team"
        )
        builder.button(
            text=f"{Emoji.KEY} Присоединиться",
            callback_data="join_team"
        )
        builder.button(
            text=f"{Emoji.BACK} Главное меню",
            callback_data="main_menu"
        )
        builder.adjust(2, 1)
        return builder.as_markup()

    @staticmethod
    def team_format_select() -> InlineKeyboardMarkup:
        """Выбор формата команды."""
        builder = InlineKeyboardBuilder()
        builder.button(text="2v2", callback_data="team_format_2v2")
        builder.button(text="5v5", callback_data="team_format_5v5")
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="my_teams"
        )
        builder.adjust(2, 1)
        return builder.as_markup()

    @staticmethod
    def team_list(teams: list[dict]) -> InlineKeyboardMarkup:
        """Список команд игрока."""
        builder = InlineKeyboardBuilder()

        for team in teams:
            format_emoji = Emoji.PEOPLE if team["format"] == "5v5" else Emoji.PERSON
            builder.button(
                text=f"{format_emoji} {team['name']} ({team['format']})",
                callback_data=f"team_{team['id']}"
            )

        builder.button(
            text=f"{Emoji.PLUS} Создать команду",
            callback_data="create_team"
        )
        builder.button(
            text=f"{Emoji.KEY} Присоединиться",
            callback_data="join_team"
        )
        builder.button(
            text=f"{Emoji.BACK} Главное меню",
            callback_data="main_menu"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def team_manage(
        team_id: int,
        is_captain: bool,
        members: list[dict]
    ) -> InlineKeyboardMarkup:
        """Управление командой."""
        builder = InlineKeyboardBuilder()

        builder.button(
            text=f"{Emoji.LIST} Состав команды",
            callback_data=f"team_roster_{team_id}"
        )

        if is_captain:
            builder.button(
                text=f"{Emoji.KEY} Новый инвайт-код",
                callback_data=f"team_new_invite_{team_id}"
            )
            builder.button(
                text=f"{Emoji.MINUS} Кикнуть игрока",
                callback_data=f"team_kick_{team_id}"
            )
            builder.button(
                text=f"{Emoji.CROWN} Передать капитанство",
                callback_data=f"team_transfer_{team_id}"
            )
            builder.button(
                text=f"{Emoji.TRASH} Распустить команду",
                callback_data=f"team_disband_{team_id}"
            )
        else:
            builder.button(
                text=f"{Emoji.CROSS} Покинуть команду",
                callback_data=f"team_leave_{team_id}"
            )

        builder.button(
            text=f"{Emoji.BACK} К командам",
            callback_data="my_teams"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def team_members_select(
        team_id: int,
        members: list[dict],
        action: str,
        exclude_id: Optional[int] = None
    ) -> InlineKeyboardMarkup:
        """Выбор участника команды."""
        builder = InlineKeyboardBuilder()

        for member in members:
            if exclude_id and member["id"] == exclude_id:
                continue
            builder.button(
                text=f"{Emoji.PERSON} {member['nickname']}",
                callback_data=f"team_{action}_{team_id}_{member['id']}"
            )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"team_{team_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    # ==================== ТУРНИРЫ ====================

    @staticmethod
    def tournaments_menu() -> InlineKeyboardMarkup:
        """Меню турниров."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.FIRE} Активные турниры",
            callback_data="active_tournaments"
        )
        builder.button(
            text=f"{Emoji.LIST} Мои турниры",
            callback_data="my_tournaments"
        )
        builder.button(
            text=f"{Emoji.BACK} Главное меню",
            callback_data="main_menu"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def tournament_list(
        tournaments: list[dict],
        back_callback: str = "tournaments"
    ) -> InlineKeyboardMarkup:
        """Список турниров."""
        builder = InlineKeyboardBuilder()

        for t in tournaments:
            status_emoji = {
                "open": Emoji.UNLOCK,
                "checkin": Emoji.BELL,
                "active": Emoji.FIRE,
                "finished": Emoji.TROPHY,
                "cancelled": Emoji.CROSS
            }.get(t["status"], Emoji.INFO)

            builder.button(
                text=f"{status_emoji} {t['name']} ({t['format']})",
                callback_data=f"tournament_{t['id']}"
            )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=back_callback
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def tournament_view(
        tournament: dict,
        is_registered: bool,
        can_register: bool,
        is_checkin: bool = False,
        checked_in: bool = False,
        is_in_reserve: bool = False
    ) -> InlineKeyboardMarkup:
        """Просмотр турнира."""
        builder = InlineKeyboardBuilder()

        if tournament["status"] == "open" and can_register:
            if is_registered:
                builder.button(
                    text=f"{Emoji.CROSS} Отменить регистрацию",
                    callback_data=f"tournament_unreg_{tournament['id']}"
                )
            elif is_in_reserve:
                builder.button(
                    text=f"{Emoji.CROSS} Покинуть резерв",
                    callback_data=f"tournament_leave_reserve_{tournament['id']}"
                )
            else:
                builder.button(
                    text=f"{Emoji.CHECK} Зарегистрироваться",
                    callback_data=f"tournament_reg_{tournament['id']}"
                )

        if is_checkin and is_registered and not checked_in:
            builder.button(
                text=f"{Emoji.BELL} Check-in",
                callback_data=f"tournament_checkin_{tournament['id']}"
            )

        if tournament["status"] == "active" and is_registered:
            builder.button(
                text=f"🟢 Лобби (Я готов)",
                callback_data=f"player_lobby_{tournament['id']}"
            )

        if tournament["status"] in ("active", "finished"):
            builder.button(
                text=f"{Emoji.TARGET} Сетка турнира",
                callback_data=f"tournament_bracket_{tournament['id']}"
            )

        builder.button(
            text=f"{Emoji.LIST} Участники",
            callback_data=f"tournament_participants_{tournament['id']}"
        )
        builder.button(
            text=f"{Emoji.BACK} К турнирам",
            callback_data="active_tournaments"
        )
        builder.adjust(1)
        return builder.as_markup()

    # ==================== РЕЙТИНГ ====================

    @staticmethod
    def rating_menu() -> InlineKeyboardMarkup:
        """Меню рейтинга."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.MEDAL} Топ игроков",
            callback_data="top_players"
        )
        builder.button(
            text=f"{Emoji.TROPHY} Топ команд",
            callback_data="top_teams"
        )
        builder.button(
            text=f"{Emoji.BACK} Главное меню",
            callback_data="main_menu"
        )
        builder.adjust(2, 1)
        return builder.as_markup()

    # ==================== АДМИН-ПАНЕЛЬ ====================

    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Главное меню админки (минималистичное)."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.PLUS} Новый турнир",
            callback_data="admin_create_tournament"
        )
        builder.button(
            text=f"{Emoji.GEAR} Управление турнирами",
            callback_data="admin_tournaments"
        )
        builder.button(
            text=f"{Emoji.GEAR} Другие возможности",
            callback_data="admin_other"
        )
        builder.button(
            text=f"{Emoji.BACK} Главное меню",
            callback_data="main_menu"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def admin_other_menu() -> InlineKeyboardMarkup:
        """Меню других возможностей."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.CHART} Статистика",
            callback_data="admin_stats"
        )
        builder.button(
            text=f"{Emoji.PEOPLE} Игроки",
            callback_data="admin_players"
        )
        builder.button(
            text=f"{Emoji.PEOPLE} Команды",
            callback_data="admin_teams"
        )
        builder.button(
            text=f"{Emoji.SEND} Настройки канала",
            callback_data="admin_channel"
        )
        builder.button(
            text=f"{Emoji.SHIELD} Админы",
            callback_data="admin_admins"
        )
        builder.button(
            text=f"{Emoji.LIST} Логи",
            callback_data="admin_logs"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin"
        )
        builder.adjust(2, 2, 2, 1)
        return builder.as_markup()

    @staticmethod
    def admin_tournament_statuses() -> InlineKeyboardMarkup:
        """Выбор статуса для просмотра турниров."""
        builder = InlineKeyboardBuilder()
        statuses = [
            ("draft", "Черновики"),
            ("open", "На регистрации"),
            ("checkin", "Check-in"),
            ("active", "Активные"),
            ("finished", "Завершённые"),
            ("cancelled", "Отменённые")
        ]

        for status, name in statuses:
            builder.button(
                text=name,
                callback_data=f"admin_tournaments_{status}"
            )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin"
        )
        builder.adjust(2, 3, 1)
        return builder.as_markup()

    @staticmethod
    def admin_tournament_manage(
        tournament: dict,
        is_registered: bool = False,
        can_register: bool = False,
        is_checkin: bool = False,
        is_in_reserve: bool = False
    ) -> InlineKeyboardMarkup:
        """Управление турниром (админ)."""
        builder = InlineKeyboardBuilder()
        status = tournament["status"]

        # Добавляем кнопки участия для админа-игрока
        if status == "open":
            if is_registered:
                builder.button(
                    text=f"{Emoji.CROSS} Отменить регистрацию",
                    callback_data=f"tournament_unreg_{tournament['id']}"
                )
            elif is_in_reserve:
                builder.button(
                    text=f"{Emoji.CLOCK} Покинуть резерв",
                    callback_data=f"tournament_leave_reserve_{tournament['id']}"
                )
            elif can_register:
                builder.button(
                    text=f"{Emoji.PLUS} Участвовать",
                    callback_data=f"tournament_reg_{tournament['id']}"
                )
        elif status == "checkin":
            if is_registered:
                builder.button(
                    text=f"{Emoji.CHECK} Check-in",
                    callback_data=f"tournament_checkin_{tournament['id']}"
                )

        if status == "draft":
            builder.button(
                text=f"{Emoji.UNLOCK} Открыть регистрацию",
                callback_data=f"admin_t_open_{tournament['id']}"
            )
            builder.button(
                text=f"{Emoji.PENCIL} Редактировать",
                callback_data=f"admin_t_edit_{tournament['id']}"
            )

        elif status == "open":
            if tournament["checkin_hours"] > 0:
                builder.button(
                    text=f"{Emoji.BELL} Запустить check-in",
                    callback_data=f"admin_t_checkin_{tournament['id']}"
                )
            else:
                builder.button(
                    text=f"{Emoji.PLAY} Начать турнир",
                    callback_data=f"admin_t_start_{tournament['id']}"
                )
            builder.button(
                text=f"{Emoji.LOCK} В черновик",
                callback_data=f"admin_t_close_{tournament['id']}"
            )

        elif status == "checkin":
            builder.button(
                text=f"{Emoji.PLAY} Начать турнир",
                callback_data=f"admin_t_start_{tournament['id']}"
            )

        elif status == "active":
            builder.button(
                text=f"🎮 Управление матчами",
                callback_data=f"mm_control_{tournament['id']}"
            )
            builder.button(
                text=f"{Emoji.PEOPLE} Лобби",
                callback_data=f"admin_t_lobby_{tournament['id']}"
            )
            builder.button(
                text=f"{Emoji.TARGET} Все матчи",
                callback_data=f"admin_t_matches_{tournament['id']}"
            )
            builder.button(
                text=f"{Emoji.TROPHY} Завершить турнир",
                callback_data=f"admin_t_finish_{tournament['id']}"
            )

        # Кнопка публикации в канал
        if status in ("draft", "open", "checkin"):
            builder.button(
                text=f"{Emoji.SEARCH} Превью поста",
                callback_data=f"admin_t_preview_{tournament['id']}"
            )
            builder.button(
                text=f"{Emoji.SEND} Опубликовать в канал",
                callback_data=f"admin_t_publish_{tournament['id']}"
            )

        builder.button(
            text=f"{Emoji.LIST} Участники",
            callback_data=f"admin_t_participants_{tournament['id']}"
        )

        builder.button(
            text=f"{Emoji.INBOX} Экспорт списка",
            callback_data=f"admin_t_export_{tournament['id']}"
        )

        if status in ("draft", "open"):
            builder.button(
                text=f"{Emoji.STAR} Сохранить как шаблон",
                callback_data=f"admin_t_save_template_{tournament['id']}"
            )

        if status not in ("finished", "cancelled"):
            builder.button(
                text=f"{Emoji.CROSS} Отменить турнир",
                callback_data=f"admin_t_cancel_{tournament['id']}"
            )

        if status in ("draft", "cancelled"):
            builder.button(
                text=f"{Emoji.TRASH} Удалить",
                callback_data=f"admin_t_delete_{tournament['id']}"
            )

        builder.button(
            text=f"{Emoji.BACK} К турнирам",
            callback_data="admin_tournaments"
        )
        builder.adjust(2)
        return builder.as_markup()

    # ==================== СОЗДАНИЕ ТУРНИРА ====================

    @staticmethod
    def tournament_format_select() -> InlineKeyboardMarkup:
        """Выбор формата турнира."""
        builder = InlineKeyboardBuilder()
        for fmt, data in config.TOURNAMENT_FORMATS.items():
            builder.button(
                text=data["name"],
                callback_data=f"t_format_{fmt}"
            )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin"
        )
        builder.adjust(3, 1)
        return builder.as_markup()

    @staticmethod
    def maps_select(selected: list[str]) -> InlineKeyboardMarkup:
        """Выбор карт."""
        builder = InlineKeyboardBuilder()

        for map_name in config.CS2_MAPS:
            is_selected = map_name in selected
            icon = Emoji.CHECK if is_selected else Emoji.EMPTY
            builder.button(
                text=f"{icon} {map_name.replace('de_', '')}",
                callback_data=f"t_map_{map_name}"
            )

        builder.button(
            text=f"{Emoji.CHECK} Готово",
            callback_data="t_maps_done"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin_create_tournament"
        )
        builder.adjust(4, 4, 2)
        return builder.as_markup()

    @staticmethod
    def map_select(selected: list[str], tournament_id: int = None) -> InlineKeyboardMarkup:
        """Выбор карт при редактировании турнира."""
        builder = InlineKeyboardBuilder()

        for map_name in config.CS2_MAPS:
            is_selected = map_name in selected
            icon = Emoji.CHECK if is_selected else Emoji.EMPTY
            builder.button(
                text=f"{icon} {map_name.replace('de_', '')}",
                callback_data=f"t_map_{map_name}"
            )

        builder.button(
            text=f"{Emoji.CHECK} Сохранить",
            callback_data="t_maps_save"
        )
        back_cb = f"admin_t_edit_{tournament_id}" if tournament_id else "admin"
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=back_cb
        )
        builder.adjust(4, 4, 2)
        return builder.as_markup()

    @staticmethod
    def participants_select() -> InlineKeyboardMarkup:
        """Выбор количества участников."""
        builder = InlineKeyboardBuilder()

        for num in config.PARTICIPANT_OPTIONS:
            builder.button(text=str(num), callback_data=f"t_participants_{num}")

        builder.button(
            text=f"{Emoji.PENCIL} Своё число",
            callback_data="t_participants_custom"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin_create_tournament"
        )
        builder.adjust(4, 1, 1)
        return builder.as_markup()

    @staticmethod
    def prize_type_select() -> InlineKeyboardMarkup:
        """Выбор типа приза."""
        builder = InlineKeyboardBuilder()

        for prize_type, name in config.PRIZE_TYPES.items():
            builder.button(text=name, callback_data=f"t_prize_{prize_type}")

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin_create_tournament"
        )
        builder.adjust(2, 2, 1, 1)
        return builder.as_markup()

    @staticmethod
    def prize_places_select() -> InlineKeyboardMarkup:
        """Выбор количества призовых мест."""
        builder = InlineKeyboardBuilder()
        builder.button(text="🥇 Только 1 место", callback_data="t_prize_places_1")
        builder.button(text="🥇🥈 2 места", callback_data="t_prize_places_2")
        builder.button(text="🥇🥈🥉 3 места", callback_data="t_prize_places_3")
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin_create_tournament"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def checkin_select() -> InlineKeyboardMarkup:
        """Выбор времени check-in."""
        builder = InlineKeyboardBuilder()

        builder.button(text="Без check-in", callback_data="t_checkin_0")
        builder.button(text="За 1 час", callback_data="t_checkin_1")
        builder.button(text="За 2 часа", callback_data="t_checkin_2")
        builder.button(text="За 3 часа", callback_data="t_checkin_3")
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin_create_tournament"
        )
        builder.adjust(4, 1)
        return builder.as_markup()

    @staticmethod
    def calendar(
        year: int,
        month: int,
        selected_date: Optional[datetime] = None,
        back_callback: str = "admin_create_tournament"
    ) -> InlineKeyboardMarkup:
        """Календарь для выбора даты."""
        builder = InlineKeyboardBuilder()

        # Заголовок месяца
        months_ru = [
            "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        builder.button(
            text=f"{months_ru[month]} {year}",
            callback_data="calendar_ignore"
        )

        # Дни недели
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for day in days:
            builder.button(text=day, callback_data="calendar_ignore")

        # Дни месяца
        import calendar
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(year, month)
        today = datetime.now().date()

        for week in month_days:
            for day in week:
                if day == 0:
                    builder.button(text=" ", callback_data="calendar_ignore")
                else:
                    date = datetime(year, month, day).date()
                    if date < today:
                        builder.button(text="·", callback_data="calendar_ignore")
                    else:
                        text = str(day)
                        if selected_date and date == selected_date.date():
                            text = f"[{day}]"
                        builder.button(
                            text=text,
                            callback_data=f"calendar_day_{year}_{month}_{day}"
                        )

        # Навигация
        prev_month = month - 1
        prev_year = year
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1

        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1

        builder.button(text="◀️", callback_data=f"calendar_nav_{prev_year}_{prev_month}")
        builder.button(text="▶️", callback_data=f"calendar_nav_{next_year}_{next_month}")

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=back_callback
        )

        builder.adjust(1, 7, 7, 7, 7, 7, 7, 2, 1)
        return builder.as_markup()

    @staticmethod
    def time_select(selected_date: datetime) -> InlineKeyboardMarkup:
        """Выбор времени."""
        builder = InlineKeyboardBuilder()

        # Часы с шагом 30 минут
        times = []
        for hour in range(10, 24):
            times.append(f"{hour:02d}:00")
            times.append(f"{hour:02d}:30")

        for time in times:
            builder.button(
                text=time,
                callback_data=f"t_time_{selected_date.strftime('%Y-%m-%d')}_{time}"
            )

        builder.button(
            text=f"{Emoji.BACK} К календарю",
            callback_data=f"calendar_nav_{selected_date.year}_{selected_date.month}"
        )
        builder.adjust(4)
        return builder.as_markup()

    @staticmethod
    def tournament_confirm(tournament_data: dict) -> InlineKeyboardMarkup:
        """Подтверждение создания турнира."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{Emoji.CHECK} Создать",
                    callback_data="t_confirm_create"
                ),
                InlineKeyboardButton(
                    text=f"{Emoji.CROSS} Отмена",
                    callback_data="admin"
                )
            ]
        ])

    @staticmethod
    def tournament_created_menu(tournament_id: int) -> InlineKeyboardMarkup:
        """Меню после создания турнира."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.PLAY} Быстрый старт (открыть + опубликовать)",
            callback_data=f"admin_t_quickstart_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.UNLOCK} Открыть регистрацию",
            callback_data=f"admin_t_open_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.PENCIL} Редактировать",
            callback_data=f"admin_t_edit_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.SEND} Опубликовать в канал",
            callback_data=f"admin_t_publish_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.LIST} В черновик",
            callback_data=f"admin_t_to_draft_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.TRASH} Удалить",
            callback_data=f"admin_t_delete_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.BACK} К турнирам",
            callback_data="admin_tournaments"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def tournament_edit_menu(tournament_id: int) -> InlineKeyboardMarkup:
        """Меню редактирования турнира."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.PENCIL} Название",
            callback_data=f"admin_t_edit_name_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.CALENDAR} Дата и время",
            callback_data=f"admin_t_edit_date_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.MAP} Карты",
            callback_data=f"admin_t_edit_maps_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.PEOPLE} Макс. участников",
            callback_data=f"admin_t_edit_participants_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.GIFT} Призы",
            callback_data=f"admin_t_edit_prizes_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"admin_t_manage_{tournament_id}"
        )
        builder.adjust(2, 2, 1, 1)
        return builder.as_markup()

    # ==================== НАСТРОЙКИ КАНАЛА ====================

    @staticmethod
    def channel_settings(channel: Optional[dict] = None) -> InlineKeyboardMarkup:
        """Настройки канала."""
        builder = InlineKeyboardBuilder()

        if channel:
            builder.button(
                text=f"{Emoji.CHECK} Проверить права",
                callback_data="admin_channel_check"
            )
            builder.button(
                text=f"{Emoji.TRASH} Отвязать канал",
                callback_data="admin_channel_remove"
            )
        else:
            builder.button(
                text=f"{Emoji.PLUS} Привязать канал",
                callback_data="admin_channel_add"
            )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin_other"
        )
        builder.adjust(1)
        return builder.as_markup()

    # ==================== ШАБЛОНЫ ====================

    @staticmethod
    def templates_list(
        templates: list[dict],
        include_builtin: bool = True
    ) -> InlineKeyboardMarkup:
        """Список шаблонов."""
        builder = InlineKeyboardBuilder()

        # Встроенные шаблоны
        if include_builtin:
            for key, tpl in config.TOURNAMENT_TEMPLATES.items():
                builder.button(
                    text=f"{Emoji.STAR} {tpl['name']}",
                    callback_data=f"template_builtin_{key}"
                )

        # Пользовательские шаблоны
        for tpl in templates:
            builder.button(
                text=f"{Emoji.LIST} {tpl['name']}",
                callback_data=f"template_custom_{tpl['id']}"
            )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin_create_tournament"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def template_manage(template_id: int) -> InlineKeyboardMarkup:
        """Управление шаблоном."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{Emoji.PLUS} Создать турнир",
                    callback_data=f"template_use_{template_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{Emoji.TRASH} Удалить шаблон",
                    callback_data=f"template_delete_{template_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{Emoji.BACK} Назад",
                    callback_data="templates_list"
                )
            ]
        ])

    # ==================== МАТЧИ ====================

    @staticmethod
    def matches_list(
        matches: list[dict],
        tournament_id: int
    ) -> InlineKeyboardMarkup:
        """Список матчей для ввода результата."""
        builder = InlineKeyboardBuilder()

        for match in matches:
            if match["status"] == "pending" and match["participant1_id"] and match["participant2_id"]:
                builder.button(
                    text=f"R{match['round']} M{match['match_number']}",
                    callback_data=f"match_result_{match['id']}"
                )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"admin_t_manage_{tournament_id}"
        )
        builder.adjust(4)
        return builder.as_markup()

    @staticmethod
    def active_matches_list(
        matches: list[dict],
        tournament_id: int
    ) -> InlineKeyboardMarkup:
        """Список активных матчей для ввода результата."""
        builder = InlineKeyboardBuilder()

        for match in matches:
            if match["participant1_id"] and match["participant2_id"]:
                builder.button(
                    text=f"🔴 R{match['round']} M{match['match_number']}",
                    callback_data=f"match_result_{match['id']}"
                )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"admin_t_manage_{tournament_id}"
        )
        builder.adjust(4)
        return builder.as_markup()

    @staticmethod
    def match_score_select(match_id: int, tournament_id: int) -> InlineKeyboardMarkup:
        """Выбор счёта матча."""
        builder = InlineKeyboardBuilder()

        # Типичные счета для CS2
        scores = [
            ("16-0", 16, 0), ("16-1", 16, 1), ("16-2", 16, 2),
            ("16-3", 16, 3), ("16-5", 16, 5), ("16-7", 16, 7),
            ("16-9", 16, 9), ("16-10", 16, 10), ("16-12", 16, 12),
            ("16-13", 16, 13), ("16-14", 16, 14),
            ("19-17", 19, 17), ("22-20", 22, 20)
        ]

        for text, s1, s2 in scores:
            # Победа первого участника
            builder.button(
                text=text,
                callback_data=f"match_set_{match_id}_{s1}_{s2}_1"
            )

        builder.button(
            text=f"{Emoji.REFRESH} Победа второго",
            callback_data=f"match_swap_{match_id}"
        )
        builder.button(
            text=f"{Emoji.PENCIL} Свой счёт",
            callback_data=f"match_custom_{match_id}"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"admin_t_manage_{tournament_id}"
        )
        builder.adjust(4, 4, 4, 1, 2)
        return builder.as_markup()

    # ==================== АДМИН: ИГРОКИ ====================

    @staticmethod
    def admin_players_menu() -> InlineKeyboardMarkup:
        """Меню управления игроками."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.LIST} Все игроки",
            callback_data="admin_players_all"
        )
        builder.button(
            text=f"{Emoji.SEARCH} Поиск",
            callback_data="admin_players_search"
        )
        builder.button(
            text=f"{Emoji.LOCK} Заблокированные",
            callback_data="admin_players_banned"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin"
        )
        builder.adjust(2, 1, 1)
        return builder.as_markup()

    @staticmethod
    def admin_player_manage(player: dict) -> InlineKeyboardMarkup:
        """Управление игроком (админ)."""
        builder = InlineKeyboardBuilder()

        if player["is_banned"]:
            builder.button(
                text=f"{Emoji.UNLOCK} Разблокировать",
                callback_data=f"admin_player_unban_{player['telegram_id']}"
            )
        else:
            builder.button(
                text=f"{Emoji.LOCK} Заблокировать",
                callback_data=f"admin_player_ban_{player['telegram_id']}"
            )

        builder.button(
            text=f"{Emoji.CHART} Статистика",
            callback_data=f"admin_player_stats_{player['telegram_id']}"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin_players"
        )
        builder.adjust(1)
        return builder.as_markup()

    # ==================== РАССЫЛКА ====================

    @staticmethod
    def broadcast_menu(tournament_id: int) -> InlineKeyboardMarkup:
        """Меню типа рассылки."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.BELL} Объявление",
            callback_data=f"broadcast_announce_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.GAME} Ссылка на матч",
            callback_data=f"broadcast_match_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.CLOCK} Напоминание о check-in",
            callback_data=f"broadcast_checkin_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"admin_t_manage_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    # ==================== БАНЫ ====================

    @staticmethod
    def ban_duration_menu(player_id: int) -> InlineKeyboardMarkup:
        """Выбор длительности бана."""
        builder = InlineKeyboardBuilder()
        builder.button(text="1 день", callback_data=f"ban_duration_{player_id}_1")
        builder.button(text="3 дня", callback_data=f"ban_duration_{player_id}_3")
        builder.button(text="7 дней", callback_data=f"ban_duration_{player_id}_7")
        builder.button(text="30 дней", callback_data=f"ban_duration_{player_id}_30")
        builder.button(text=f"{Emoji.CROSS} Навсегда", callback_data=f"ban_duration_{player_id}_perm")
        builder.button(text=f"{Emoji.BACK} Отмена", callback_data="admin_players")
        builder.adjust(2, 2, 1, 1)
        return builder.as_markup()

    @staticmethod
    def bans_list(bans: list[dict]) -> InlineKeyboardMarkup:
        """Список банов."""
        builder = InlineKeyboardBuilder()
        for ban in bans[:10]:  # Лимит 10
            builder.button(
                text=f"{Emoji.CROSS} {ban['nickname']}",
                callback_data=f"admin_ban_view_{ban['player_id']}"
            )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin"
        )
        builder.adjust(1)
        return builder.as_markup()

    # ==================== ОЧЕРЕДЬ МАТЧЕЙ ====================

    @staticmethod
    def match_queue(matches: list[dict], tournament_id: int, participants: dict, active_count: int, max_active: int) -> InlineKeyboardMarkup:
        """Очередь матчей с кнопками запуска."""
        builder = InlineKeyboardBuilder()

        for i, match in enumerate(matches[:8]):  # Лимит 8
            p1 = participants.get(match["participant1_id"], "TBD")
            p2 = participants.get(match["participant2_id"], "TBD")
            pos = i + 1

            # Можно запустить, если не превышен лимит
            if active_count < max_active:
                builder.button(
                    text=f"#{pos} {p1} vs {p2}",
                    callback_data=f"match_start_{match['id']}"
                )
            else:
                builder.button(
                    text=f"#{pos} ⏳ {p1} vs {p2}",
                    callback_data=f"match_info_{match['id']}"
                )

        if active_count >= max_active:
            builder.button(
                text=f"⚠️ Лимит: {active_count}/{max_active} активных матчей",
                callback_data="noop"
            )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"admin_t_manage_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def match_start_confirm(match_id: int, tournament_id: int) -> InlineKeyboardMarkup:
        """Подтверждение запуска матча с вводом ссылки."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.PLAY} Запустить без ссылки",
            callback_data=f"match_go_{match_id}"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"admin_t_queue_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    # ==================== ЛОББИ ====================

    @staticmethod
    def lobby_admin(tournament_id: int, ready_players: list, all_participants: int) -> InlineKeyboardMarkup:
        """Админское меню лобби."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"🟢 Готовы: {len(ready_players)}/{all_participants}",
            callback_data="noop"
        )
        builder.button(
            text=f"{Emoji.BELL} Напомнить всем",
            callback_data=f"lobby_remind_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"admin_t_manage_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def lobby_player(tournament_id: int, is_ready: bool) -> InlineKeyboardMarkup:
        """Кнопки лобби для игрока."""
        builder = InlineKeyboardBuilder()
        if is_ready:
            builder.button(
                text=f"{Emoji.CLOCK} Отошёл",
                callback_data=f"lobby_away_{tournament_id}"
            )
        else:
            builder.button(
                text=f"{Emoji.CHECK} Я готов!",
                callback_data=f"lobby_ready_{tournament_id}"
            )
        builder.button(
            text=f"{Emoji.BACK} К турниру",
            callback_data=f"tournament_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    # ==================== РУЧНАЯ СИСТЕМА МАТЧЕЙ ====================

    @staticmethod
    def manual_match_control(
        tournament_id: int,
        ready_count: int,
        in_match_count: int,
        eliminated_count: int,
        active_matches: int
    ) -> InlineKeyboardMarkup:
        """Главный экран управления ручными матчами."""
        builder = InlineKeyboardBuilder()

        builder.button(
            text=f"➕ Создать матч",
            callback_data=f"mm_create_{tournament_id}"
        )
        builder.button(
            text=f"🔴 Активные матчи ({active_matches})",
            callback_data=f"mm_active_{tournament_id}"
        )
        builder.button(
            text=f"📝 Ввести результат",
            callback_data=f"admin_t_result_{tournament_id}"
        )
        builder.button(
            text=f"👥 Участники ({ready_count}🟢 {in_match_count}🔴 {eliminated_count}❌)",
            callback_data=f"mm_participants_{tournament_id}"
        )
        builder.button(
            text=f"🔄 Вернуть игрока",
            callback_data=f"mm_restore_{tournament_id}"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"admin_t_manage_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def participant_select(
        participants: list[dict],
        tournament_id: int,
        action: str,
        exclude_id: int = None
    ) -> InlineKeyboardMarkup:
        """Выбор участника для матча."""
        builder = InlineKeyboardBuilder()

        status_icons = {
            "ready": "🟢",
            "in_match": "🔴",
            "eliminated": "❌"
        }

        for p in participants:
            if exclude_id and p["participant_id"] == exclude_id:
                continue

            icon = status_icons.get(p.get("status", "ready"), "")
            wins = p.get("wins", 0)
            name = p.get("name", f"ID:{p['participant_id']}")

            builder.button(
                text=f"{icon} {name} ({wins}W)",
                callback_data=f"mm_{action}_{tournament_id}_{p['participant_id']}"
            )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"mm_control_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def match_confirm(
        tournament_id: int,
        p1_id: int,
        p2_id: int,
        p1_name: str,
        p2_name: str
    ) -> InlineKeyboardMarkup:
        """Подтверждение создания матча."""
        builder = InlineKeyboardBuilder()

        builder.button(
            text=f"🚀 Создать без ссылки",
            callback_data=f"mm_go_{tournament_id}_{p1_id}_{p2_id}"
        )
        builder.button(
            text=f"🔗 Ввести ссылку на сервер",
            callback_data=f"mm_link_{tournament_id}_{p1_id}_{p2_id}"
        )
        builder.button(
            text=f"{Emoji.BACK} Отмена",
            callback_data=f"mm_control_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def active_matches_control(
        matches: list[dict],
        tournament_id: int,
        participants: dict
    ) -> InlineKeyboardMarkup:
        """Список активных матчей с управлением."""
        builder = InlineKeyboardBuilder()

        for match in matches:
            p1 = participants.get(match["participant1_id"], "?")
            p2 = participants.get(match["participant2_id"], "?")
            builder.button(
                text=f"🔴 {p1} vs {p2}",
                callback_data=f"mm_match_{match['id']}"
            )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"mm_control_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def match_actions(match_id: int, tournament_id: int) -> InlineKeyboardMarkup:
        """Действия с активным матчем."""
        builder = InlineKeyboardBuilder()

        builder.button(
            text=f"📝 Ввести результат",
            callback_data=f"match_result_{match_id}"
        )
        builder.button(
            text=f"❌ Отменить матч",
            callback_data=f"mm_cancel_{match_id}"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"mm_active_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def restore_participant_select(
        participants: list[dict],
        tournament_id: int
    ) -> InlineKeyboardMarkup:
        """Выбор выбывшего участника для возврата."""
        builder = InlineKeyboardBuilder()

        for p in participants:
            name = p.get("name", f"ID:{p['participant_id']}")
            wins = p.get("wins", 0)
            builder.button(
                text=f"❌ {name} ({wins}W)",
                callback_data=f"mm_do_restore_{tournament_id}_{p['participant_id']}"
            )

        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data=f"mm_control_{tournament_id}"
        )
        builder.adjust(1)
        return builder.as_markup()

    # ==================== СОЗДАНИЕ ТУРНИРА ====================

    @staticmethod
    def create_tournament_menu() -> InlineKeyboardMarkup:
        """Меню создания турнира."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{Emoji.PLUS} Новый турнир",
            callback_data="t_create_new"
        )
        builder.button(
            text=f"{Emoji.REFRESH} На основе прошлого",
            callback_data="t_create_from_prev"
        )
        builder.button(
            text=f"{Emoji.STAR} Из шаблона",
            callback_data="templates_list"
        )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="admin"
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def prev_tournaments_list(tournaments: list[dict]) -> InlineKeyboardMarkup:
        """Список прошлых турниров для дублирования."""
        builder = InlineKeyboardBuilder()
        for t in tournaments[:10]:  # Лимит 10
            builder.button(
                text=f"{t['name']}",
                callback_data=f"t_duplicate_{t['id']}"
            )
        builder.button(
            text=f"{Emoji.BACK} Назад",
            callback_data="t_create"
        )
        builder.adjust(1)
        return builder.as_markup()


# Создаём экземпляр
kb = Keyboards()
