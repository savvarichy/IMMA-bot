"""Обработчики пользователей: регистрация, профиль, рейтинг."""
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards import kb, Emoji
from utils import (
    validate_nickname, validate_steam_link, validate_contact,
    format_player_info, format_tournament_info, escape_html, extract_steam_id
)
from config import config

router = Router()


class RegistrationStates(StatesGroup):
    """Состояния регистрации."""
    waiting_nickname = State()
    waiting_steam = State()
    waiting_contact = State()


class EditProfileStates(StatesGroup):
    """Состояния редактирования профиля."""
    waiting_nickname = State()
    waiting_steam = State()
    waiting_contact = State()


class PrizeAdminsStates(StatesGroup):
    """Состояния редактирования админов призов."""
    waiting_usernames = State()


# ==================== КОМАНДЫ ====================

@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message, command: CommandObject):
    """Обработчик /start с deep link (reg_XXX)."""
    args = command.args

    if not args or not args.startswith("reg_"):
        # Если не deep link для регистрации - обычный start
        await cmd_start(message)
        return

    # Парсим tournament_id
    try:
        tournament_id = int(args.replace("reg_", ""))
    except ValueError:
        await cmd_start(message)
        return

    # Проверяем игрока
    player = await db.get_player(message.from_user.id)

    if not player:
        # Не зарегистрирован - показываем регистрацию
        text = (
            f"{Emoji.TROPHY} <b>IMMA Championship Bot</b>\n\n"
            f"Для участия в турнирах необходимо сначала зарегистрироваться!"
        )
        await message.answer(text, reply_markup=kb.main_menu(False), parse_mode="HTML")
        return

    if player["is_banned"]:
        await message.answer(
            f"{Emoji.LOCK} <b>Вы заблокированы</b>\n\n"
            f"Причина: {player.get('ban_reason', 'Не указана')}",
            parse_mode="HTML"
        )
        return

    # Получаем турнир
    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await message.answer(
            f"{Emoji.CROSS} Турнир не найден.",
            reply_markup=kb.main_menu(True),
            parse_mode="HTML"
        )
        return

    # Показываем информацию о турнире с кнопкой регистрации
    participant_count = await db.get_tournament_participant_count(tournament_id)
    text = format_tournament_info(tournament, participant_count)

    # Определяем статус регистрации
    is_registered = False
    can_register = False

    if tournament["format"] == "1v1":
        is_registered = await db.is_player_registered(tournament_id, player["id"])
        can_register = True
    else:
        team = await db.get_player_team_by_format(player["id"], tournament["format"])
        if team:
            is_registered = await db.is_team_registered(tournament_id, team["id"])
            can_register = team["captain_id"] == player["id"]

    is_checkin = tournament["status"] == "checkin"

    await message.answer(
        text,
        reply_markup=kb.tournament_view(
            tournament, is_registered, can_register, is_checkin, False
        ),
        parse_mode="HTML"
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    player = await db.get_player(message.from_user.id)

    if player:
        if player["is_banned"]:
            await message.answer(
                f"{Emoji.LOCK} <b>Вы заблокированы</b>\n\n"
                f"Причина: {player.get('ban_reason', 'Не указана')}",
                parse_mode="HTML"
            )
            return

        text = (
            f"{Emoji.HOME} <b>Главное меню</b>\n\n"
            f"Привет, <b>{escape_html(player['nickname'])}</b>!\n"
            f"Выбери действие:"
        )
        await message.answer(text, reply_markup=kb.main_menu(True), parse_mode="HTML")
    else:
        text = (
            f"{Emoji.TROPHY} <b>IMMA Championship Bot</b>\n\n"
            f"Добро пожаловать в систему управления CS2 турнирами!\n\n"
            f"Для участия в турнирах необходимо пройти регистрацию."
        )
        await message.answer(text, reply_markup=kb.main_menu(False), parse_mode="HTML")


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    """Обработчик команды /menu."""
    await state.clear()
    await cmd_start(message)


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Обработчик команды /profile."""
    player = await db.get_player(message.from_user.id)

    if not player:
        await message.answer(
            f"{Emoji.WARNING} Вы ещё не зарегистрированы.\n"
            "Используйте /start для регистрации.",
            parse_mode="HTML"
        )
        return

    text = format_player_info(player)
    await message.answer(text, reply_markup=kb.profile_menu(), parse_mode="HTML")


@router.message(Command("top"))
async def cmd_top(message: Message):
    """Обработчик команды /top."""
    players = await db.get_top_players(10)

    if not players:
        await message.answer(
            f"{Emoji.INFO} Пока нет игроков в рейтинге.",
            parse_mode="HTML"
        )
        return

    text = f"<b>{Emoji.MEDAL} Топ-10 игроков</b>\n\n"

    for i, player in enumerate(players, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        winrate = 0
        if player["tournaments_played"] > 0:
            winrate = (player["tournaments_won"] / player["tournaments_played"]) * 100

        text += (
            f"{medal} <b>{escape_html(player['nickname'])}</b>\n"
            f"   Побед: {player['tournaments_won']} | "
            f"Турниров: {player['tournaments_played']} | "
            f"WR: {winrate:.0f}%\n"
        )

    await message.answer(text, reply_markup=kb.back_button("main_menu"), parse_mode="HTML")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Обработчик команды /admin."""
    if not await db.is_admin(message.from_user.id):
        await message.answer(
            f"{Emoji.LOCK} У вас нет доступа к админ-панели.",
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"<b>{Emoji.GEAR} Админ-панель</b>\n\nВыберите действие:",
        reply_markup=kb.admin_menu(),
        parse_mode="HTML"
    )


# ==================== ГЛАВНОЕ МЕНЮ ====================

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await state.clear()
    player = await db.get_player(callback.from_user.id)
    is_registered = player is not None

    if is_registered and player["is_banned"]:
        await callback.message.edit_text(
            f"{Emoji.LOCK} <b>Вы заблокированы</b>\n\n"
            f"Причина: {player.get('ban_reason', 'Не указана')}",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = f"{Emoji.HOME} <b>Главное меню</b>\n\n"
    if is_registered:
        text += f"Привет, <b>{escape_html(player['nickname'])}</b>!\nВыбери действие:"
    else:
        text += "Для участия в турнирах необходимо пройти регистрацию."

    await callback.message.edit_text(
        text,
        reply_markup=kb.main_menu(is_registered),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== РЕГИСТРАЦИЯ ====================

@router.callback_query(F.data == "register")
async def callback_register(callback: CallbackQuery, state: FSMContext):
    """Начало регистрации."""
    player = await db.get_player(callback.from_user.id)
    if player:
        await callback.answer("Вы уже зарегистрированы!", show_alert=True)
        return

    text = (
        f"<b>{Emoji.PENCIL} Регистрация</b>\n\n"
        f"<b>Шаг 1 из 3</b>\n\n"
        f"Введите ваш игровой никнейм (2-32 символа):"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.cancel_registration(),
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.waiting_nickname)
    await callback.answer()


@router.callback_query(F.data == "cancel_registration")
async def callback_cancel_registration(callback: CallbackQuery, state: FSMContext):
    """Отмена регистрации."""
    await state.clear()
    await callback_main_menu(callback, state)


@router.callback_query(F.data == "skip_contact")
async def callback_skip_contact(callback: CallbackQuery, state: FSMContext):
    """Пропуск ввода контакта."""
    data = await state.get_data()
    await state.clear()

    # Создаём игрока без контакта
    await db.create_player(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        nickname=data["nickname"],
        steam_link=data["steam_link"],
        contact=f"@{callback.from_user.username}" if callback.from_user.username else "Не указан"
    )

    text = (
        f"{Emoji.CHECK} <b>Регистрация завершена!</b>\n\n"
        f"{Emoji.GAME} <b>Никнейм:</b> {escape_html(data['nickname'])}\n"
        f"{Emoji.LINK} <b>Steam:</b> {data['steam_link']}\n\n"
        f"Теперь вы можете участвовать в турнирах!"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.main_menu(True),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(RegistrationStates.waiting_nickname)
async def process_nickname(message: Message, state: FSMContext):
    """Обработка ввода никнейма."""
    nickname = message.text.strip()
    is_valid, error = validate_nickname(nickname)

    if not is_valid:
        await message.answer(
            f"{Emoji.CROSS} {error}\n\nПопробуйте ещё раз:",
            reply_markup=kb.cancel_registration(),
            parse_mode="HTML"
        )
        return

    # Проверяем, не занят ли никнейм
    existing = await db.get_player_by_nickname(nickname)
    if existing:
        await message.answer(
            f"{Emoji.CROSS} Ник <b>{escape_html(nickname)}</b> уже занят.\n\n"
            f"Придумайте другой никнейм:",
            reply_markup=kb.cancel_registration(),
            parse_mode="HTML"
        )
        return

    await state.update_data(nickname=nickname)

    text = (
        f"<b>{Emoji.PENCIL} Регистрация</b>\n\n"
        f"<b>Шаг 2 из 3</b>\n\n"
        f"Отлично! Теперь отправьте ссылку на ваш Steam профиль:\n\n"
        f"<i>Примеры:</i>\n"
        f"• https://steamcommunity.com/id/your_id\n"
        f"• https://steamcommunity.com/profiles/76561198..."
    )

    await message.answer(
        text,
        reply_markup=kb.cancel_registration(),
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.waiting_steam)


@router.message(RegistrationStates.waiting_steam)
async def process_steam(message: Message, state: FSMContext):
    """Обработка ввода Steam ссылки."""
    steam_link = message.text.strip()
    is_valid, error = validate_steam_link(steam_link)

    if not is_valid:
        await message.answer(
            f"{Emoji.CROSS} {error}",
            reply_markup=kb.cancel_registration(),
            parse_mode="HTML"
        )
        return

    # Добавляем https:// если нет
    if not steam_link.startswith("http"):
        steam_link = "https://" + steam_link

    # Извлекаем Steam ID для превью
    steam_id = extract_steam_id(steam_link)

    await state.update_data(steam_link=steam_link)

    text = (
        f"<b>{Emoji.PENCIL} Регистрация</b>\n\n"
        f"<b>Шаг 3 из 3</b>\n\n"
        f"{Emoji.CHECK} Steam: <code>{steam_id}</code>\n\n"
        f"Укажите контакт для связи (Telegram, Discord и т.д.)\n"
        f"или нажмите <b>Пропустить</b>:"
    )

    await message.answer(
        text,
        reply_markup=kb.skip_contact(),
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.waiting_contact)


@router.message(RegistrationStates.waiting_contact)
async def process_contact(message: Message, state: FSMContext):
    """Обработка ввода контакта."""
    contact = message.text.strip()
    is_valid, error = validate_contact(contact)

    if not is_valid:
        await message.answer(
            f"{Emoji.CROSS} {error}",
            reply_markup=kb.cancel_registration(),
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    await state.clear()

    # Создаём игрока
    await db.create_player(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        nickname=data["nickname"],
        steam_link=data["steam_link"],
        contact=contact
    )

    text = (
        f"{Emoji.CHECK} <b>Регистрация завершена!</b>\n\n"
        f"{Emoji.GAME} <b>Никнейм:</b> {escape_html(data['nickname'])}\n"
        f"{Emoji.LINK} <b>Steam:</b> {data['steam_link']}\n"
        f"{Emoji.SEND} <b>Контакт:</b> {escape_html(contact)}\n\n"
        f"Теперь вы можете участвовать в турнирах!"
    )

    await message.answer(
        text,
        reply_markup=kb.main_menu(True),
        parse_mode="HTML"
    )


# ==================== ПРОФИЛЬ ====================

@router.callback_query(F.data == "profile")
async def callback_profile(callback: CallbackQuery):
    """Просмотр профиля."""
    player = await db.get_player(callback.from_user.id)

    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    text = format_player_info(player)

    # Добавляем информацию о последнем турнире
    last_tournament = await db.get_player_last_tournament(player["id"])
    if last_tournament:
        status_text = {
            "active": "В процессе",
            "finished": "Завершён"
        }.get(last_tournament["status"], last_tournament["status"])
        text += f"\n\n{Emoji.TROPHY} <b>Последний турнир:</b>\n{last_tournament['name']} ({status_text})"

    await callback.message.edit_text(
        text,
        reply_markup=kb.profile_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "my_stats")
async def callback_my_stats(callback: CallbackQuery):
    """Статистика игрока."""
    player = await db.get_player(callback.from_user.id)

    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    # Получаем место в рейтинге
    top_players = await db.get_top_players(100)
    rank = None
    for i, p in enumerate(top_players, 1):
        if p["telegram_id"] == callback.from_user.id:
            rank = i
            break

    winrate = 0
    if player["tournaments_played"] > 0:
        winrate = (player["tournaments_won"] / player["tournaments_played"]) * 100

    text = (
        f"<b>{Emoji.CHART} Ваша статистика</b>\n\n"
        f"{Emoji.TROPHY} Турниров сыграно: <b>{player['tournaments_played']}</b>\n"
        f"{Emoji.MEDAL} Побед: <b>{player['tournaments_won']}</b>\n"
        f"{Emoji.TARGET} Винрейт: <b>{winrate:.1f}%</b>\n"
        f"{Emoji.CROSS} Пропущено check-in: <b>{player['missed_checkins']}</b>\n"
    )

    if rank:
        text += f"\n{Emoji.STAR} Место в рейтинге: <b>#{rank}</b>"

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button("profile"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "edit_profile")
async def callback_edit_profile(callback: CallbackQuery):
    """Меню редактирования профиля."""
    await callback.message.edit_text(
        f"<b>{Emoji.PENCIL} Редактирование профиля</b>\n\n"
        "Что вы хотите изменить?",
        reply_markup=kb.edit_profile_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "edit_nickname")
async def callback_edit_nickname(callback: CallbackQuery, state: FSMContext):
    """Редактирование никнейма."""
    await callback.message.edit_text(
        f"<b>{Emoji.PENCIL} Изменение никнейма</b>\n\n"
        "Введите новый никнейм (2-32 символа):",
        reply_markup=kb.back_button("edit_profile"),
        parse_mode="HTML"
    )
    await state.set_state(EditProfileStates.waiting_nickname)
    await callback.answer()


@router.message(EditProfileStates.waiting_nickname)
async def process_edit_nickname(message: Message, state: FSMContext):
    """Обработка изменения никнейма."""
    nickname = message.text.strip()
    is_valid, error = validate_nickname(nickname)

    if not is_valid:
        await message.answer(
            f"{Emoji.CROSS} {error}\n\nПопробуйте ещё раз:",
            reply_markup=kb.back_button("edit_profile"),
            parse_mode="HTML"
        )
        return

    # Проверяем, не занят ли никнейм другим игроком
    existing = await db.get_player_by_nickname(nickname)
    if existing and existing["telegram_id"] != message.from_user.id:
        await message.answer(
            f"{Emoji.CROSS} Ник <b>{escape_html(nickname)}</b> уже занят.\n\n"
            f"Придумайте другой никнейм:",
            reply_markup=kb.back_button("edit_profile"),
            parse_mode="HTML"
        )
        return

    await state.clear()
    await db.update_player(message.from_user.id, nickname=nickname)

    await message.answer(
        f"{Emoji.CHECK} Никнейм успешно изменён на <b>{escape_html(nickname)}</b>!",
        reply_markup=kb.profile_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "edit_steam")
async def callback_edit_steam(callback: CallbackQuery, state: FSMContext):
    """Редактирование Steam ссылки."""
    await callback.message.edit_text(
        f"<b>{Emoji.LINK} Изменение Steam</b>\n\n"
        "Введите новую ссылку на Steam профиль:",
        reply_markup=kb.back_button("edit_profile"),
        parse_mode="HTML"
    )
    await state.set_state(EditProfileStates.waiting_steam)
    await callback.answer()


@router.message(EditProfileStates.waiting_steam)
async def process_edit_steam(message: Message, state: FSMContext):
    """Обработка изменения Steam ссылки."""
    steam_link = message.text.strip()
    is_valid, error = validate_steam_link(steam_link)

    if not is_valid:
        await message.answer(
            f"{Emoji.CROSS} {error}",
            reply_markup=kb.back_button("edit_profile"),
            parse_mode="HTML"
        )
        return

    if not steam_link.startswith("http"):
        steam_link = "https://" + steam_link

    await state.clear()
    await db.update_player(message.from_user.id, steam_link=steam_link)

    await message.answer(
        f"{Emoji.CHECK} Ссылка на Steam успешно изменена!",
        reply_markup=kb.profile_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "edit_contact")
async def callback_edit_contact(callback: CallbackQuery, state: FSMContext):
    """Редактирование контакта."""
    await callback.message.edit_text(
        f"<b>{Emoji.SEND} Изменение контакта</b>\n\n"
        "Введите новый контакт для связи:",
        reply_markup=kb.back_button("edit_profile"),
        parse_mode="HTML"
    )
    await state.set_state(EditProfileStates.waiting_contact)
    await callback.answer()


@router.message(EditProfileStates.waiting_contact)
async def process_edit_contact(message: Message, state: FSMContext):
    """Обработка изменения контакта."""
    contact = message.text.strip()
    is_valid, error = validate_contact(contact)

    if not is_valid:
        await message.answer(
            f"{Emoji.CROSS} {error}",
            reply_markup=kb.back_button("edit_profile"),
            parse_mode="HTML"
        )
        return

    await state.clear()
    await db.update_player(message.from_user.id, contact=contact)

    await message.answer(
        f"{Emoji.CHECK} Контакт успешно изменён!",
        reply_markup=kb.profile_menu(),
        parse_mode="HTML"
    )


# ==================== РЕЙТИНГ ====================

@router.callback_query(F.data == "rating")
async def callback_rating(callback: CallbackQuery):
    """Меню рейтинга."""
    await callback.message.edit_text(
        f"<b>{Emoji.CHART} Рейтинг</b>\n\n"
        "Выберите категорию:",
        reply_markup=kb.rating_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "top_players")
async def callback_top_players(callback: CallbackQuery):
    """Топ игроков."""
    players = await db.get_top_players(10)

    if not players:
        await callback.message.edit_text(
            f"{Emoji.INFO} Пока нет игроков в рейтинге.",
            reply_markup=kb.back_button("rating"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = f"<b>{Emoji.MEDAL} Топ-10 игроков</b>\n\n"

    for i, player in enumerate(players, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        winrate = 0
        if player["tournaments_played"] > 0:
            winrate = (player["tournaments_won"] / player["tournaments_played"]) * 100

        text += (
            f"{medal} <b>{escape_html(player['nickname'])}</b>\n"
            f"   Побед: {player['tournaments_won']} | "
            f"WR: {winrate:.0f}%\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button("rating"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "top_teams")
async def callback_top_teams(callback: CallbackQuery):
    """Топ команд."""
    teams = await db.get_top_teams(10)

    if not teams:
        await callback.message.edit_text(
            f"{Emoji.INFO} Пока нет команд в рейтинге.",
            reply_markup=kb.back_button("rating"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = f"<b>{Emoji.TROPHY} Топ-10 команд</b>\n\n"

    for i, team in enumerate(teams, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")

        text += (
            f"{medal} <b>{escape_html(team['name'])}</b> ({team['format']})\n"
            f"   Побед: {team['tournaments_won']} | "
            f"Турниров: {team['tournaments_played']}\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button("rating"),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== АДМИН-ПАНЕЛЬ ====================

@router.callback_query(F.data == "admin")
async def callback_admin(callback: CallbackQuery):
    """Админ-панель."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.GEAR} Админ-панель</b>\n\nВыберите действие:",
        reply_markup=kb.admin_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_other")
async def callback_admin_other(callback: CallbackQuery):
    """Другие возможности админки."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.GEAR} Другие возможности</b>\n\nВыберите раздел:",
        reply_markup=kb.admin_other_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_players")
async def callback_admin_players(callback: CallbackQuery):
    """Список игроков."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    players = await db.get_all_players(limit=20)

    text = f"<b>{Emoji.PEOPLE} Игроки</b>\n\n"
    if players:
        for p in players:
            ban_icon = "🔴 " if p.get("is_banned") else ""
            text += f"{ban_icon}{escape_html(p['nickname'])} (ID: {p['telegram_id']})\n"
    else:
        text += "Нет зарегистрированных игроков."

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button("admin_other"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_teams")
async def callback_admin_teams(callback: CallbackQuery):
    """Список команд."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    teams = await db.get_all_teams(limit=20)

    text = f"<b>{Emoji.PEOPLE} Команды</b>\n\n"
    if teams:
        for t in teams:
            text += f"• {escape_html(t['name'])} ({t['format']})\n"
    else:
        text += "Нет зарегистрированных команд."

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button("admin_other"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_admins")
async def callback_admin_admins(callback: CallbackQuery):
    """Список админов."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    admins = await db.get_all_admins()

    text = f"<b>{Emoji.SHIELD} Админы</b>\n\n"
    if admins:
        for a in admins:
            text += f"• ID: {a['telegram_id']}\n"
    else:
        text += "Нет админов в базе."

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button("admin_other"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_logs")
async def callback_admin_logs(callback: CallbackQuery):
    """Последние логи."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    logs = await db.get_logs(limit=15)

    text = f"<b>{Emoji.LIST} Последние действия</b>\n\n"
    if logs:
        for log in logs:
            action = escape_html(log['action'])
            details = escape_html(log.get('details', '') or '')[:30]
            text += f"• {action}: {details}\n"
    else:
        text += "Нет записей."

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button("admin_other"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_prize_admins")
async def callback_admin_prize_admins(callback: CallbackQuery):
    """Настройка админов призов."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    admins = await db.get_prize_admins()

    text = f"<b>{Emoji.GIFT} Админы призов</b>\n\n"
    text += "Эти контакты будут показаны победителям турнира для получения призов.\n\n"

    if admins:
        text += "<b>Текущие админы:</b>\n"
        for admin in admins:
            text += f"• @{admin}\n"
    else:
        text += "<i>Админы не указаны</i>\n"

    text += "\nНажмите «Изменить» чтобы задать список."

    await callback.message.edit_text(
        text,
        reply_markup=kb.prize_admins_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "edit_prize_admins")
async def callback_edit_prize_admins(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование админов призов."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    text = f"<b>{Emoji.EDIT} Редактирование админов призов</b>\n\n"
    text += "Отправьте username админов через запятую или каждый с новой строки.\n\n"
    text += "<i>Пример: admin1, admin2, admin3</i>\n"
    text += "<i>Или:</i>\n<i>admin1</i>\n<i>admin2</i>\n\n"
    text += "Символ @ в начале необязателен."

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button("admin_prize_admins"),
        parse_mode="HTML"
    )
    await state.set_state(PrizeAdminsStates.waiting_usernames)
    await callback.answer()


@router.message(PrizeAdminsStates.waiting_usernames)
async def process_prize_admins_input(message: Message, state: FSMContext):
    """Обработка ввода админов призов."""
    if not await db.is_admin(message.from_user.id):
        return

    text = message.text.strip()

    # Парсим username-ы
    if "," in text:
        usernames = [u.strip() for u in text.split(",")]
    else:
        usernames = [u.strip() for u in text.split("\n")]

    # Убираем @ и пустые строки
    usernames = [u.lstrip("@") for u in usernames if u.strip()]

    if not usernames:
        await message.answer(
            f"{Emoji.WARNING} Не найдено ни одного username. Попробуйте ещё раз.",
            parse_mode="HTML"
        )
        return

    # Сохраняем
    await db.set_prize_admins(usernames)
    await state.clear()

    text = f"{Emoji.CHECK} <b>Админы призов сохранены!</b>\n\n"
    for u in usernames:
        text += f"• @{u}\n"

    await message.answer(
        text,
        reply_markup=kb.back_button("admin_prize_admins"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "clear_prize_admins")
async def callback_clear_prize_admins(callback: CallbackQuery):
    """Очистить список админов призов."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await db.set_prize_admins([])

    await callback.message.edit_text(
        f"{Emoji.CHECK} Список админов призов очищен.",
        reply_markup=kb.back_button("admin_prize_admins"),
        parse_mode="HTML"
    )
    await callback.answer()
