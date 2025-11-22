"""Обработчики турниров (пользовательские и админские)."""
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards import kb, Emoji
from utils import (
    format_tournament_info, format_datetime, escape_html,
    get_time_until
)
from config import config

router = Router()


async def _update_channel_post_if_exists(tournament_id: int, bot) -> None:
    """Обновить пост в канале, если он существует."""
    post = await db.get_tournament_post(tournament_id)
    if post:
        from services.channel import init_channel_service
        channel_service = init_channel_service(bot)
        await channel_service.update_post(tournament_id)


class CreateTournamentStates(StatesGroup):
    """Состояния создания турнира."""
    waiting_name = State()
    waiting_format = State()
    waiting_maps = State()
    waiting_participants = State()
    waiting_custom_participants = State()
    waiting_prize_type = State()
    waiting_prize_amount = State()
    waiting_date = State()
    waiting_time = State()
    waiting_checkin = State()
    confirm = State()


class BroadcastStates(StatesGroup):
    """Состояния рассылки."""
    waiting_message = State()


# ==================== ПРОСМОТР ТУРНИРОВ (USER) ====================

@router.callback_query(F.data == "tournaments")
async def callback_tournaments(callback: CallbackQuery):
    """Меню турниров."""
    await callback.message.edit_text(
        f"<b>{Emoji.TROPHY} Турниры</b>\n\nВыберите раздел:",
        reply_markup=kb.tournaments_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "active_tournaments")
async def callback_active_tournaments(callback: CallbackQuery):
    """Активные турниры."""
    tournaments = await db.get_active_tournaments()

    if not tournaments:
        await callback.message.edit_text(
            f"{Emoji.INFO} Сейчас нет активных турниров.\n"
            "Следите за анонсами!",
            reply_markup=kb.back_button("tournaments"),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"<b>{Emoji.FIRE} Активные турниры</b>\n\n"
            "Выберите турнир для просмотра:",
            reply_markup=kb.tournament_list(tournaments, "tournaments"),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "my_tournaments")
async def callback_my_tournaments(callback: CallbackQuery):
    """Мои турниры."""
    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    # Получаем турниры, где игрок зарегистрирован
    all_tournaments = await db.get_active_tournaments()
    my_tournaments = []

    for t in all_tournaments:
        if t["format"] == "1v1":
            if await db.is_player_registered(t["id"], player["id"]):
                my_tournaments.append(t)
        else:
            # Проверяем команды игрока
            teams = await db.get_player_teams(player["id"])
            for team in teams:
                if await db.is_team_registered(t["id"], team["id"]):
                    my_tournaments.append(t)
                    break

    if not my_tournaments:
        await callback.message.edit_text(
            f"{Emoji.INFO} Вы не зарегистрированы ни на один турнир.",
            reply_markup=kb.back_button("tournaments"),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"<b>{Emoji.LIST} Мои турниры</b>\n\n"
            "Турниры, на которые вы зарегистрированы:",
            reply_markup=kb.tournament_list(my_tournaments, "tournaments"),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^tournament_(\d+)$"))
async def callback_tournament_view(callback: CallbackQuery):
    """Просмотр турнира."""
    tournament_id = int(callback.data.split("_")[1])
    tournament = await db.get_tournament(tournament_id)

    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    player = await db.get_player(callback.from_user.id)
    participant_count = await db.get_tournament_participant_count(tournament_id)

    is_registered = False
    can_register = False
    checked_in = False

    if player:
        if tournament["format"] == "1v1":
            is_registered = await db.is_player_registered(tournament_id, player["id"])
            can_register = True
        else:
            # Проверяем команду нужного формата
            team = await db.get_player_team_by_format(player["id"], tournament["format"])
            if team:
                is_registered = await db.is_team_registered(tournament_id, team["id"])
                # Только капитан может регистрировать
                can_register = team["captain_id"] == player["id"]

    is_checkin = tournament["status"] == "checkin"

    text = format_tournament_info(tournament, participant_count)

    await callback.message.edit_text(
        text,
        reply_markup=kb.tournament_view(
            tournament, is_registered, can_register, is_checkin, checked_in
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^tournament_reg_(\d+)$"))
async def callback_tournament_register(callback: CallbackQuery):
    """Регистрация на турнир."""
    tournament_id = int(callback.data.split("_")[2])
    tournament = await db.get_tournament(tournament_id)

    if not tournament or tournament["status"] != "open":
        await callback.answer("Регистрация закрыта!", show_alert=True)
        return

    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    participant_count = await db.get_tournament_participant_count(tournament_id)
    if participant_count >= tournament["max_participants"]:
        await callback.answer("Турнир заполнен!", show_alert=True)
        return

    if tournament["format"] == "1v1":
        success = await db.register_player_to_tournament(tournament_id, player["id"])
        if success:
            await callback.answer("Вы зарегистрированы на турнир!", show_alert=True)
            # Обновляем пост в канале
            await _update_channel_post_if_exists(tournament_id, callback.bot)
        else:
            await callback.answer("Вы уже зарегистрированы!", show_alert=True)
    else:
        team = await db.get_player_team_by_format(player["id"], tournament["format"])
        if not team:
            await callback.answer(
                f"У вас нет команды формата {tournament['format']}!",
                show_alert=True
            )
            return

        if team["captain_id"] != player["id"]:
            await callback.answer(
                "Только капитан может регистрировать команду!",
                show_alert=True
            )
            return

        # Проверяем полноту состава
        team_size = config.TOURNAMENT_FORMATS[tournament["format"]]["team_size"]
        member_count = await db.get_team_member_count(team["id"])
        if member_count < team_size:
            await callback.answer(
                f"Неполный состав! ({member_count}/{team_size})",
                show_alert=True
            )
            return

        success = await db.register_team_to_tournament(tournament_id, team["id"])
        if success:
            await callback.answer(
                f"Команда {team['name']} зарегистрирована!",
                show_alert=True
            )
            # Обновляем пост в канале
            await _update_channel_post_if_exists(tournament_id, callback.bot)
        else:
            await callback.answer("Команда уже зарегистрирована!", show_alert=True)

    # Обновляем просмотр
    await callback_tournament_view(callback)


@router.callback_query(F.data.regexp(r"^tournament_unreg_(\d+)$"))
async def callback_tournament_unregister(callback: CallbackQuery):
    """Отмена регистрации."""
    tournament_id = int(callback.data.split("_")[2])
    tournament = await db.get_tournament(tournament_id)

    if not tournament or tournament["status"] not in ("open", "checkin"):
        await callback.answer("Нельзя отменить регистрацию!", show_alert=True)
        return

    player = await db.get_player(callback.from_user.id)

    if tournament["format"] == "1v1":
        await db.unregister_player_from_tournament(tournament_id, player["id"])
    else:
        team = await db.get_player_team_by_format(player["id"], tournament["format"])
        if team and team["captain_id"] == player["id"]:
            await db.unregister_team_from_tournament(tournament_id, team["id"])

    await callback.answer("Регистрация отменена!", show_alert=True)
    # Обновляем пост в канале
    await _update_channel_post_if_exists(tournament_id, callback.bot)
    await callback_tournament_view(callback)


@router.callback_query(F.data.regexp(r"^tournament_checkin_(\d+)$"))
async def callback_tournament_checkin(callback: CallbackQuery):
    """Check-in на турнир."""
    tournament_id = int(callback.data.split("_")[2])
    tournament = await db.get_tournament(tournament_id)

    if not tournament or tournament["status"] != "checkin":
        await callback.answer("Check-in недоступен!", show_alert=True)
        return

    player = await db.get_player(callback.from_user.id)

    if tournament["format"] == "1v1":
        await db.checkin_player(tournament_id, player["id"])
    else:
        team = await db.get_player_team_by_format(player["id"], tournament["format"])
        if team:
            await db.checkin_team(tournament_id, team["id"])

    await callback.answer("Check-in выполнен!", show_alert=True)
    await callback_tournament_view(callback)


@router.callback_query(F.data.regexp(r"^tournament_participants_(\d+)$"))
async def callback_tournament_participants(callback: CallbackQuery):
    """Список участников турнира."""
    tournament_id = int(callback.data.split("_")[2])
    tournament = await db.get_tournament(tournament_id)

    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    text = f"<b>{Emoji.PEOPLE} Участники турнира</b>\n"
    text += f"<b>{tournament['name']}</b>\n\n"

    if tournament["format"] == "1v1":
        players = await db.get_tournament_players(tournament_id)
        for i, p in enumerate(players, 1):
            check = Emoji.CHECK if p.get("checked_in") else ""
            text += f"{i}. {escape_html(p['nickname'])} {check}\n"
        text += f"\n<b>Всего:</b> {len(players)}/{tournament['max_participants']}"
    else:
        teams = await db.get_tournament_teams(tournament_id)
        for i, t in enumerate(teams, 1):
            check = Emoji.CHECK if t.get("checked_in") else ""
            text += f"{i}. {escape_html(t['name'])} {check}\n"
        text += f"\n<b>Всего:</b> {len(teams)}/{tournament['max_participants']}"

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button(f"tournament_{tournament_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== АДМИН: УПРАВЛЕНИЕ ТУРНИРАМИ ====================

@router.callback_query(F.data == "admin_tournaments")
async def callback_admin_tournaments(callback: CallbackQuery):
    """Выбор статуса турниров."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.GEAR} Управление турнирами</b>\n\n"
        "Выберите статус для просмотра:",
        reply_markup=kb.admin_tournament_statuses(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_tournaments_(\w+)$"))
async def callback_admin_tournaments_by_status(callback: CallbackQuery):
    """Турниры по статусу."""
    status = callback.data.split("_")[2]

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournaments = await db.get_tournaments_by_status(status)
    status_name = config.TOURNAMENT_STATUSES.get(status, status)

    if not tournaments:
        await callback.message.edit_text(
            f"{Emoji.INFO} Нет турниров со статусом «{status_name}»",
            reply_markup=kb.back_button("admin_tournaments"),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"<b>{Emoji.LIST} {status_name}</b>\n\n"
            "Выберите турнир:",
            reply_markup=kb.tournament_list(tournaments, "admin_tournaments"),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_t_manage_(\d+)$"))
async def callback_admin_tournament_manage(callback: CallbackQuery):
    """Управление турниром."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    participant_count = await db.get_tournament_participant_count(tournament_id)
    text = format_tournament_info(tournament, participant_count)

    await callback.message.edit_text(
        text,
        reply_markup=kb.admin_tournament_manage(tournament),
        parse_mode="HTML"
    )
    await callback.answer()


# При клике на турнир из списка - показываем управление
@router.callback_query(F.data.regexp(r"^tournament_(\d+)$"))
async def callback_tournament_click(callback: CallbackQuery):
    """Клик на турнир (определяем контекст)."""
    # Если админ - показываем управление
    if await db.is_admin(callback.from_user.id):
        tournament_id = callback.data.split("_")[1]
        callback.data = f"admin_t_manage_{tournament_id}"
        await callback_admin_tournament_manage(callback)
    else:
        await callback_tournament_view(callback)


@router.callback_query(F.data.regexp(r"^admin_t_open_(\d+)$"))
async def callback_admin_open_tournament(callback: CallbackQuery):
    """Открыть регистрацию."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await db.update_tournament_status(tournament_id, "open")
    await db.log_action(callback.from_user.id, "tournament_open", f"ID: {tournament_id}")

    await callback.answer("Регистрация открыта!", show_alert=True)

    # Обновляем просмотр
    callback.data = f"admin_t_manage_{tournament_id}"
    await callback_admin_tournament_manage(callback)


@router.callback_query(F.data.regexp(r"^admin_t_close_(\d+)$"))
async def callback_admin_close_tournament(callback: CallbackQuery):
    """Закрыть регистрацию."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await db.update_tournament_status(tournament_id, "draft")
    await callback.answer("Регистрация закрыта!", show_alert=True)

    callback.data = f"admin_t_manage_{tournament_id}"
    await callback_admin_tournament_manage(callback)


@router.callback_query(F.data.regexp(r"^admin_t_checkin_(\d+)$"))
async def callback_admin_start_checkin(callback: CallbackQuery):
    """Запустить check-in."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await db.update_tournament_status(tournament_id, "checkin")
    await db.log_action(callback.from_user.id, "tournament_checkin", f"ID: {tournament_id}")

    await callback.answer("Check-in запущен!", show_alert=True)

    callback.data = f"admin_t_manage_{tournament_id}"
    await callback_admin_tournament_manage(callback)


@router.callback_query(F.data.regexp(r"^admin_t_start_(\d+)$"))
async def callback_admin_start_tournament(callback: CallbackQuery):
    """Начать турнир."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)

    # Импортируем генератор сетки
    from services.bracket import BracketGenerator

    # Получаем участников
    if tournament["format"] == "1v1":
        if tournament["checkin_hours"] > 0:
            participants = await db.get_checked_in_players(tournament_id)
        else:
            participants = await db.get_tournament_players(tournament_id)
        participant_type = "player"
    else:
        if tournament["checkin_hours"] > 0:
            participants = await db.get_checked_in_teams(tournament_id)
        else:
            participants = await db.get_tournament_teams(tournament_id)
        participant_type = "team"

    if len(participants) < 2:
        await callback.answer("Недостаточно участников!", show_alert=True)
        return

    # Генерируем сетку
    bracket = BracketGenerator(tournament_id, participants, participant_type)
    await bracket.generate()

    await db.update_tournament_status(tournament_id, "active")
    await db.log_action(callback.from_user.id, "tournament_start", f"ID: {tournament_id}")

    await callback.answer("Турнир начался!", show_alert=True)

    callback.data = f"admin_t_manage_{tournament_id}"
    await callback_admin_tournament_manage(callback)


@router.callback_query(F.data.regexp(r"^admin_t_cancel_(\d+)$"))
async def callback_admin_cancel_tournament(callback: CallbackQuery):
    """Отменить турнир."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)

    await callback.message.edit_text(
        f"<b>{Emoji.WARNING} Отмена турнира</b>\n\n"
        f"Вы уверены, что хотите отменить турнир "
        f"<b>{escape_html(tournament['name'])}</b>?",
        reply_markup=kb.confirm_cancel(
            f"admin_t_docancel_{tournament_id}",
            f"admin_t_manage_{tournament_id}"
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_t_docancel_(\d+)$"))
async def callback_admin_docancel_tournament(callback: CallbackQuery):
    """Подтверждение отмены турнира."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await db.update_tournament_status(tournament_id, "cancelled")
    await db.log_action(callback.from_user.id, "tournament_cancel", f"ID: {tournament_id}")

    await callback.answer("Турнир отменён!", show_alert=True)

    await callback.message.edit_text(
        f"{Emoji.CHECK} Турнир отменён.",
        reply_markup=kb.back_button("admin_tournaments"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^admin_t_participants_(\d+)$"))
async def callback_admin_participants(callback: CallbackQuery):
    """Участники турнира (админ)."""
    tournament_id = int(callback.data.split("_")[3])
    callback.data = f"tournament_participants_{tournament_id}"
    await callback_tournament_participants(callback)


# ==================== СОЗДАНИЕ ТУРНИРА ====================

@router.callback_query(F.data == "admin_create_tournament")
async def callback_admin_create_tournament(callback: CallbackQuery, state: FSMContext):
    """Начало создания турнира."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await state.update_data(maps=[])

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 1:</b> Введите название турнира:",
        reply_markup=kb.back_button("admin"),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_name)
    await callback.answer()


@router.message(CreateTournamentStates.waiting_name)
async def process_tournament_name(message: Message, state: FSMContext):
    """Обработка названия турнира."""
    name = message.text.strip()

    if len(name) < 3 or len(name) > 64:
        await message.answer(
            f"{Emoji.CROSS} Название должно быть от 3 до 64 символов.",
            reply_markup=kb.back_button("admin"),
            parse_mode="HTML"
        )
        return

    await state.update_data(name=name)

    await message.answer(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 2:</b> Выберите формат:",
        reply_markup=kb.tournament_format_select(),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_format)


@router.callback_query(F.data.startswith("t_format_"), CreateTournamentStates.waiting_format)
async def process_tournament_format(callback: CallbackQuery, state: FSMContext):
    """Выбор формата турнира."""
    format_type = callback.data.replace("t_format_", "")
    await state.update_data(format=format_type)

    data = await state.get_data()
    selected_maps = data.get("maps", [])

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 3:</b> Выберите карты (можно несколько):\n"
        f"Выбрано: {len(selected_maps)}",
        reply_markup=kb.maps_select(selected_maps),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_maps)
    await callback.answer()


@router.callback_query(F.data.startswith("t_map_"), CreateTournamentStates.waiting_maps)
async def process_map_toggle(callback: CallbackQuery, state: FSMContext):
    """Переключение карты."""
    map_name = callback.data.replace("t_map_", "")
    data = await state.get_data()
    maps = data.get("maps", [])

    if map_name in maps:
        maps.remove(map_name)
    else:
        maps.append(map_name)

    await state.update_data(maps=maps)

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 3:</b> Выберите карты (можно несколько):\n"
        f"Выбрано: {len(maps)}",
        reply_markup=kb.maps_select(maps),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "t_maps_done", CreateTournamentStates.waiting_maps)
async def process_maps_done(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора карт."""
    data = await state.get_data()
    maps = data.get("maps", [])

    if not maps:
        await callback.answer("Выберите хотя бы одну карту!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 4:</b> Выберите максимальное количество участников:",
        reply_markup=kb.participants_select(),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_participants)
    await callback.answer()


@router.callback_query(F.data.startswith("t_participants_"), CreateTournamentStates.waiting_participants)
async def process_participants(callback: CallbackQuery, state: FSMContext):
    """Выбор количества участников."""
    value = callback.data.replace("t_participants_", "")

    if value == "custom":
        await callback.message.edit_text(
            f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
            f"Введите количество участников (от 4 до 128):",
            reply_markup=kb.back_button("admin_create_tournament"),
            parse_mode="HTML"
        )
        await state.set_state(CreateTournamentStates.waiting_custom_participants)
        await callback.answer()
        return

    await state.update_data(max_participants=int(value))

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 5:</b> Выберите тип приза:",
        reply_markup=kb.prize_type_select(),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_prize_type)
    await callback.answer()


@router.message(CreateTournamentStates.waiting_custom_participants)
async def process_custom_participants(message: Message, state: FSMContext):
    """Ввод своего количества участников."""
    try:
        num = int(message.text.strip())
        if num < 4 or num > 128:
            raise ValueError()
    except ValueError:
        await message.answer(
            f"{Emoji.CROSS} Введите число от 4 до 128.",
            reply_markup=kb.back_button("admin_create_tournament"),
            parse_mode="HTML"
        )
        return

    await state.update_data(max_participants=num)

    await message.answer(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 5:</b> Выберите тип приза:",
        reply_markup=kb.prize_type_select(),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_prize_type)


@router.callback_query(F.data.startswith("t_prize_"), CreateTournamentStates.waiting_prize_type)
async def process_prize_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа приза."""
    prize_type = callback.data.replace("t_prize_", "")
    await state.update_data(prize_type=prize_type)

    if prize_type == "none":
        await state.update_data(prize_amount=0)
        # Переходим к выбору даты
        now = datetime.now()
        await callback.message.edit_text(
            f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
            f"<b>Шаг 6:</b> Выберите дату старта:",
            reply_markup=kb.calendar(now.year, now.month),
            parse_mode="HTML"
        )
        await state.set_state(CreateTournamentStates.waiting_date)
    else:
        prize_name = config.PRIZE_TYPES[prize_type]
        await callback.message.edit_text(
            f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
            f"Тип приза: <b>{prize_name}</b>\n\n"
            f"Введите сумму приза:",
            reply_markup=kb.back_button("admin_create_tournament"),
            parse_mode="HTML"
        )
        await state.set_state(CreateTournamentStates.waiting_prize_amount)
    await callback.answer()


@router.message(CreateTournamentStates.waiting_prize_amount)
async def process_prize_amount(message: Message, state: FSMContext):
    """Ввод суммы приза."""
    try:
        amount = int(message.text.strip().replace(" ", ""))
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            f"{Emoji.CROSS} Введите положительное число.",
            reply_markup=kb.back_button("admin_create_tournament"),
            parse_mode="HTML"
        )
        return

    await state.update_data(prize_amount=amount)

    now = datetime.now()
    await message.answer(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 6:</b> Выберите дату старта:",
        reply_markup=kb.calendar(now.year, now.month),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_date)


@router.callback_query(F.data.startswith("calendar_nav_"))
async def process_calendar_nav(callback: CallbackQuery, state: FSMContext):
    """Навигация по календарю."""
    parts = callback.data.split("_")
    year = int(parts[2])
    month = int(parts[3])

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 6:</b> Выберите дату старта:",
        reply_markup=kb.calendar(year, month),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("calendar_day_"))
async def process_calendar_day(callback: CallbackQuery, state: FSMContext):
    """Выбор дня."""
    parts = callback.data.split("_")
    year = int(parts[2])
    month = int(parts[3])
    day = int(parts[4])

    selected_date = datetime(year, month, day)
    await state.update_data(selected_date=selected_date)

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 7:</b> Выберите время старта:\n"
        f"Дата: <b>{format_datetime(selected_date, False).split(',')[0]}</b>",
        reply_markup=kb.time_select(selected_date),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_time)
    await callback.answer()


@router.callback_query(F.data == "calendar_ignore")
async def process_calendar_ignore(callback: CallbackQuery):
    """Игнорируем клики на заголовки календаря."""
    await callback.answer()


@router.callback_query(F.data.startswith("t_time_"), CreateTournamentStates.waiting_time)
async def process_time_select(callback: CallbackQuery, state: FSMContext):
    """Выбор времени."""
    parts = callback.data.split("_")
    date_str = parts[2]
    time_str = parts[3]

    hour, minute = map(int, time_str.split(":"))
    date_parts = date_str.split("-")
    start_time = datetime(
        int(date_parts[0]), int(date_parts[1]), int(date_parts[2]),
        hour, minute
    )

    await state.update_data(start_time=start_time)

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 8:</b> Выберите время check-in:",
        reply_markup=kb.checkin_select(),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_checkin)
    await callback.answer()


@router.callback_query(F.data.startswith("t_checkin_"), CreateTournamentStates.waiting_checkin)
async def process_checkin_select(callback: CallbackQuery, state: FSMContext):
    """Выбор времени check-in."""
    checkin_hours = int(callback.data.replace("t_checkin_", ""))
    await state.update_data(checkin_hours=checkin_hours)

    # Показываем итоговую информацию
    data = await state.get_data()

    format_name = config.TOURNAMENT_FORMATS[data["format"]]["name"]
    maps_text = ", ".join(m.replace("de_", "") for m in data["maps"])
    prize_text = "Без приза"
    if data["prize_type"] != "none":
        prize_text = f"{data['prize_amount']} ({config.PRIZE_TYPES[data['prize_type']]})"

    checkin_text = "Без check-in" if checkin_hours == 0 else f"За {checkin_hours} ч."

    text = (
        f"<b>{Emoji.CHECK} Подтверждение создания</b>\n\n"
        f"{Emoji.TROPHY} <b>Название:</b> {escape_html(data['name'])}\n"
        f"{Emoji.GAME} <b>Формат:</b> {format_name}\n"
        f"{Emoji.MAP} <b>Карты:</b> {maps_text}\n"
        f"{Emoji.PEOPLE} <b>Участников:</b> {data['max_participants']}\n"
        f"{Emoji.GIFT} <b>Приз:</b> {prize_text}\n"
        f"{Emoji.CALENDAR} <b>Старт:</b> {format_datetime(data['start_time'])}\n"
        f"{Emoji.BELL} <b>Check-in:</b> {checkin_text}\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.tournament_confirm(data),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.confirm)
    await callback.answer()


@router.callback_query(F.data == "t_confirm_create", CreateTournamentStates.confirm)
async def process_tournament_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания турнира."""
    data = await state.get_data()
    await state.clear()

    player = await db.get_player(callback.from_user.id)

    # Дедлайн регистрации = за час до старта
    registration_deadline = data["start_time"] - timedelta(hours=1)

    tournament_id = await db.create_tournament(
        name=data["name"],
        format=data["format"],
        maps=data["maps"],
        max_participants=data["max_participants"],
        prize_type=data["prize_type"],
        prize_amount=data["prize_amount"],
        start_time=data["start_time"],
        registration_deadline=registration_deadline,
        checkin_hours=data["checkin_hours"],
        created_by=player["id"] if player else callback.from_user.id
    )

    await db.log_action(callback.from_user.id, "tournament_create", f"ID: {tournament_id}")

    await callback.message.edit_text(
        f"{Emoji.CHECK} <b>Турнир создан!</b>\n\n"
        f"ID: {tournament_id}\n"
        f"Статус: Черновик\n\n"
        f"Откройте регистрацию, когда будете готовы.",
        reply_markup=kb.back_button("admin"),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ШАБЛОНЫ ====================

@router.callback_query(F.data == "admin_from_template")
async def callback_admin_from_template(callback: CallbackQuery):
    """Создание из шаблона."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    templates = await db.get_all_templates()

    await callback.message.edit_text(
        f"<b>{Emoji.STAR} Шаблоны турниров</b>\n\n"
        "Выберите шаблон:",
        reply_markup=kb.templates_list(templates),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("template_builtin_"))
async def callback_template_builtin(callback: CallbackQuery, state: FSMContext):
    """Использование встроенного шаблона."""
    template_key = callback.data.replace("template_builtin_", "")
    template = config.TOURNAMENT_TEMPLATES.get(template_key)

    if not template:
        await callback.answer("Шаблон не найден!", show_alert=True)
        return

    # Заполняем данные из шаблона
    await state.update_data(
        name=template["name"],
        format=template["format"],
        maps=template["maps"],
        max_participants=template["max_participants"],
        prize_type=template["prize_type"],
        prize_amount=template["prize_amount"],
        checkin_hours=1
    )

    # Показываем календарь для выбора даты
    now = datetime.now()
    await callback.message.edit_text(
        f"<b>{Emoji.STAR} Турнир из шаблона: {template['name']}</b>\n\n"
        f"Выберите дату старта:",
        reply_markup=kb.calendar(now.year, now.month),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_date)
    await callback.answer()


# ==================== РАССЫЛКА ====================

@router.callback_query(F.data.regexp(r"^admin_t_broadcast_(\d+)$"))
async def callback_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Рассылка участникам турнира."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(broadcast_tournament_id=tournament_id)

    await callback.message.edit_text(
        f"<b>{Emoji.SEND} Рассылка участникам</b>\n\n"
        f"Введите текст сообщения:",
        reply_markup=kb.back_button(f"admin_t_manage_{tournament_id}"),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_message)
    await callback.answer()


@router.message(BroadcastStates.waiting_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Отправка рассылки."""
    data = await state.get_data()
    tournament_id = data.get("broadcast_tournament_id")
    await state.clear()

    tournament = await db.get_tournament(tournament_id)

    # Получаем telegram_id участников
    recipients = []
    if tournament["format"] == "1v1":
        players = await db.get_tournament_players(tournament_id)
        recipients = [p["telegram_id"] for p in players]
    else:
        teams = await db.get_tournament_teams(tournament_id)
        for team in teams:
            members = await db.get_team_members(team["id"])
            recipients.extend([m["telegram_id"] for m in members])

    sent = 0
    from aiogram import Bot
    bot = message.bot

    for tid in recipients:
        try:
            await bot.send_message(
                tid,
                f"<b>{Emoji.BELL} Сообщение от организаторов</b>\n"
                f"<b>Турнир:</b> {tournament['name']}\n\n"
                f"{message.text}",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            pass

    await message.answer(
        f"{Emoji.CHECK} Рассылка отправлена!\n"
        f"Доставлено: {sent}/{len(recipients)}",
        reply_markup=kb.back_button("admin"),
        parse_mode="HTML"
    )


# ==================== ЭКСПОРТ ====================

@router.callback_query(F.data.regexp(r"^admin_t_export_(\d+)$"))
async def callback_admin_export(callback: CallbackQuery):
    """Экспорт списка участников."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)

    text = f"📋 Участники турнира: {tournament['name']}\n"
    text += f"Формат: {tournament['format']}\n\n"

    if tournament["format"] == "1v1":
        players = await db.get_tournament_players(tournament_id)
        for i, p in enumerate(players, 1):
            text += f"{i}. {p['nickname']}\n"
            text += f"   Steam: {p['steam_link']}\n"
            text += f"   Контакт: {p['contact']}\n\n"
    else:
        teams = await db.get_tournament_teams(tournament_id)
        for i, t in enumerate(teams, 1):
            members = await db.get_team_members(t["id"])
            text += f"{i}. {t['name']}\n"
            for m in members:
                captain_mark = " (К)" if m["id"] == t["captain_id"] else ""
                text += f"   - {m['nickname']}{captain_mark}\n"
            text += "\n"

    # Отправляем как документ
    from io import BytesIO
    file = BytesIO(text.encode())
    file.name = f"participants_{tournament_id}.txt"

    from aiogram.types import BufferedInputFile
    await callback.message.answer_document(
        BufferedInputFile(file.getvalue(), filename=file.name),
        caption=f"Список участников турнира #{tournament_id}"
    )
    await callback.answer()


# ==================== НАСТРОЙКИ КАНАЛА ====================

class ChannelStates(StatesGroup):
    """Состояния настройки канала."""
    waiting_channel = State()


@router.callback_query(F.data == "admin_channel")
async def callback_admin_channel(callback: CallbackQuery):
    """Настройки канала."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    channel = await db.get_channel()

    if channel:
        channel_text = f"@{channel['channel_username']}" if channel.get('channel_username') else f"ID: {channel['channel_id']}"
        text = (
            f"<b>{Emoji.SEND} Настройки канала</b>\n\n"
            f"{Emoji.CHECK} Канал привязан: <b>{channel_text}</b>\n\n"
            f"Бот будет публиковать посты о турнирах в этот канал."
        )
    else:
        text = (
            f"<b>{Emoji.SEND} Настройки канала</b>\n\n"
            f"{Emoji.CROSS} Канал не привязан.\n\n"
            f"Привяжите канал, чтобы публиковать посты о турнирах."
        )

    await callback.message.edit_text(
        text,
        reply_markup=kb.channel_settings(channel),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_channel_add")
async def callback_admin_channel_add(callback: CallbackQuery, state: FSMContext):
    """Добавление канала."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Привязка канала</b>\n\n"
        f"Отправьте @username канала или перешлите сообщение из канала.\n\n"
        f"<b>Важно:</b> Бот должен быть администратором канала с правами:\n"
        f"• Публикация сообщений\n"
        f"• Редактирование сообщений",
        reply_markup=kb.back_button("admin_channel"),
        parse_mode="HTML"
    )
    await state.set_state(ChannelStates.waiting_channel)
    await callback.answer()


@router.message(ChannelStates.waiting_channel)
async def process_channel_input(message: Message, state: FSMContext):
    """Обработка ввода канала."""
    from services.channel import init_channel_service

    # Инициализируем сервис если нужно
    channel_service = init_channel_service(message.bot)

    channel_id = None
    channel_username = None

    # Если переслано сообщение
    if message.forward_from_chat:
        channel_id = message.forward_from_chat.id
        channel_username = message.forward_from_chat.username
    # Если введён @username
    elif message.text and message.text.startswith("@"):
        channel_username = message.text[1:]  # убираем @
        try:
            chat = await message.bot.get_chat(f"@{channel_username}")
            channel_id = chat.id
        except Exception as e:
            await message.answer(
                f"{Emoji.CROSS} Канал не найден. Проверьте username.",
                reply_markup=kb.back_button("admin_channel"),
                parse_mode="HTML"
            )
            return
    else:
        await message.answer(
            f"{Emoji.CROSS} Отправьте @username канала или перешлите сообщение из канала.",
            reply_markup=kb.back_button("admin_channel"),
            parse_mode="HTML"
        )
        return

    await state.clear()

    # Проверяем права
    has_rights, error = await channel_service.check_bot_permissions(channel_id)
    if not has_rights:
        await message.answer(
            f"{Emoji.CROSS} {error}\n\n"
            f"Добавьте бота как администратора канала.",
            reply_markup=kb.back_button("admin_channel"),
            parse_mode="HTML"
        )
        return

    # Сохраняем канал
    await db.set_channel(channel_id, channel_username, message.from_user.id)
    await db.log_action(message.from_user.id, "channel_set", f"@{channel_username}")

    channel_text = f"@{channel_username}" if channel_username else f"ID: {channel_id}"
    await message.answer(
        f"{Emoji.CHECK} Канал <b>{channel_text}</b> успешно привязан!",
        reply_markup=kb.back_button("admin_channel"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_channel_check")
async def callback_admin_channel_check(callback: CallbackQuery):
    """Проверка прав в канале."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    channel = await db.get_channel()
    if not channel:
        await callback.answer("Канал не привязан!", show_alert=True)
        return

    from services.channel import init_channel_service
    channel_service = init_channel_service(callback.bot)

    has_rights, error = await channel_service.check_bot_permissions(channel["channel_id"])

    if has_rights:
        await callback.answer("✅ Все права в порядке!", show_alert=True)
    else:
        await callback.answer(f"❌ {error}", show_alert=True)


@router.callback_query(F.data == "admin_channel_remove")
async def callback_admin_channel_remove(callback: CallbackQuery):
    """Отвязка канала."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await db.remove_channel()
    await db.log_action(callback.from_user.id, "channel_remove", None)

    await callback.answer("Канал отвязан!", show_alert=True)

    # Обновляем меню
    await callback.message.edit_text(
        f"<b>{Emoji.SEND} Настройки канала</b>\n\n"
        f"{Emoji.CROSS} Канал не привязан.\n\n"
        f"Привяжите канал, чтобы публиковать посты о турнирах.",
        reply_markup=kb.channel_settings(None),
        parse_mode="HTML"
    )


# ==================== ПУБЛИКАЦИЯ В КАНАЛ ====================

@router.callback_query(F.data.regexp(r"^admin_t_publish_(\d+)$"))
async def callback_admin_publish(callback: CallbackQuery):
    """Публикация поста о турнире в канал."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    channel = await db.get_channel()
    if not channel:
        await callback.answer("Сначала привяжите канал в настройках!", show_alert=True)
        return

    from services.channel import init_channel_service
    channel_service = init_channel_service(callback.bot)

    # Проверяем, есть ли уже пост
    existing_post = await db.get_tournament_post(tournament_id)

    if existing_post:
        # Обновляем существующий пост
        success, message = await channel_service.update_post(tournament_id)
    else:
        # Публикуем новый пост
        success, message = await channel_service.publish_post(tournament_id)

    if success:
        await callback.answer(message, show_alert=True)
        await db.log_action(callback.from_user.id, "tournament_publish", f"ID: {tournament_id}")
    else:
        await callback.answer(f"❌ {message}", show_alert=True)
