"""Обработчики команд."""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards import kb, Emoji
from utils import generate_invite_code, format_team_info, escape_html
from config import config

router = Router()


class CreateTeamStates(StatesGroup):
    """Состояния создания команды."""
    waiting_format = State()
    waiting_name = State()


class JoinTeamStates(StatesGroup):
    """Состояния присоединения к команде."""
    waiting_code = State()


# ==================== МЕНЮ КОМАНД ====================

@router.callback_query(F.data == "my_teams")
async def callback_my_teams(callback: CallbackQuery):
    """Список команд игрока."""
    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    teams = await db.get_player_teams(player["id"])

    if not teams:
        await callback.message.edit_text(
            f"<b>{Emoji.PEOPLE} Мои команды</b>\n\n"
            f"У вас пока нет команд.\n"
            f"Создайте свою команду или присоединитесь по коду приглашения.",
            reply_markup=kb.teams_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"<b>{Emoji.PEOPLE} Мои команды</b>\n\n"
            f"Выберите команду для управления:",
            reply_markup=kb.team_list(teams),
            parse_mode="HTML"
        )
    await callback.answer()


# ==================== СОЗДАНИЕ КОМАНДЫ ====================

@router.callback_query(F.data == "create_team")
async def callback_create_team(callback: CallbackQuery, state: FSMContext):
    """Начало создания команды."""
    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание команды</b>\n\n"
        f"Выберите формат команды:",
        reply_markup=kb.team_format_select(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("team_format_"))
async def callback_team_format(callback: CallbackQuery, state: FSMContext):
    """Выбор формата команды."""
    format_type = callback.data.replace("team_format_", "")

    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    # Проверяем, нет ли уже команды такого формата
    existing_team = await db.get_player_team_by_format(player["id"], format_type)
    if existing_team:
        await callback.answer(
            f"У вас уже есть команда формата {format_type}!",
            show_alert=True
        )
        return

    await state.update_data(format=format_type)

    format_name = config.TOURNAMENT_FORMATS[format_type]["name"]
    team_size = config.TOURNAMENT_FORMATS[format_type]["team_size"]

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание команды</b>\n\n"
        f"{Emoji.GAME} Формат: <b>{format_name}</b>\n"
        f"{Emoji.PEOPLE} Размер: <b>{team_size} игроков</b>\n\n"
        f"Введите название команды:",
        reply_markup=kb.back_button("create_team"),
        parse_mode="HTML"
    )
    await state.set_state(CreateTeamStates.waiting_name)
    await callback.answer()


@router.message(CreateTeamStates.waiting_name)
async def process_team_name(message: Message, state: FSMContext):
    """Обработка названия команды."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            f"{Emoji.CROSS} Название слишком короткое (минимум 2 символа).",
            reply_markup=kb.back_button("create_team"),
            parse_mode="HTML"
        )
        return

    if len(name) > 32:
        await message.answer(
            f"{Emoji.CROSS} Название слишком длинное (максимум 32 символа).",
            reply_markup=kb.back_button("create_team"),
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    await state.clear()

    player = await db.get_player(message.from_user.id)
    if not player:
        await message.answer(
            f"{Emoji.CROSS} Вы не зарегистрированы!",
            reply_markup=kb.main_menu(),
            parse_mode="HTML"
        )
        return

    team_format = data.get("format")
    if not team_format or team_format not in config.TOURNAMENT_FORMATS:
        await message.answer(
            f"{Emoji.CROSS} Ошибка: неверный формат команды!",
            reply_markup=kb.main_menu(),
            parse_mode="HTML"
        )
        return

    invite_code = generate_invite_code()

    team_id = await db.create_team(
        name=name,
        captain_id=player["id"],
        format=team_format,
        invite_code=invite_code
    )

    format_name = config.TOURNAMENT_FORMATS[team_format]["name"]
    team_size = config.TOURNAMENT_FORMATS[team_format]["team_size"]

    await message.answer(
        f"{Emoji.CHECK} <b>Команда создана!</b>\n\n"
        f"{Emoji.PEOPLE} <b>Название:</b> {escape_html(name)}\n"
        f"{Emoji.GAME} <b>Формат:</b> {format_name}\n"
        f"{Emoji.CROWN} <b>Капитан:</b> {escape_html(player['nickname'])}\n\n"
        f"{Emoji.KEY} <b>Код приглашения:</b> <code>{invite_code}</code>\n"
        f"<i>Код действителен 24 часа</i>\n\n"
        f"Отправьте этот код тиммейтам для присоединения к команде.\n"
        f"Максимум участников: {team_size}",
        reply_markup=kb.back_button("my_teams"),
        parse_mode="HTML"
    )


# ==================== ПРИСОЕДИНЕНИЕ К КОМАНДЕ ====================

@router.callback_query(F.data == "join_team")
async def callback_join_team(callback: CallbackQuery, state: FSMContext):
    """Присоединение к команде."""
    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.KEY} Присоединиться к команде</b>\n\n"
        f"Введите код приглашения (формат: IMMA-XXXX):",
        reply_markup=kb.back_button("my_teams"),
        parse_mode="HTML"
    )
    await state.set_state(JoinTeamStates.waiting_code)
    await callback.answer()


@router.message(JoinTeamStates.waiting_code)
async def process_join_code(message: Message, state: FSMContext):
    """Обработка кода приглашения."""
    code = message.text.strip().upper()

    team = await db.get_team_by_invite(code)
    if not team:
        await message.answer(
            f"{Emoji.CROSS} Команда не найдена или код истёк.\n"
            f"Проверьте код и попробуйте снова.",
            reply_markup=kb.back_button("my_teams"),
            parse_mode="HTML"
        )
        return

    player = await db.get_player(message.from_user.id)

    # Проверяем, нет ли уже в команде этого формата
    existing = await db.get_player_team_by_format(player["id"], team["format"])
    if existing:
        await state.clear()
        await message.answer(
            f"{Emoji.CROSS} У вас уже есть команда формата {team['format']}!",
            reply_markup=kb.back_button("my_teams"),
            parse_mode="HTML"
        )
        return

    # Проверяем лимит участников
    team_size = config.TOURNAMENT_FORMATS[team["format"]]["team_size"]
    current_count = await db.get_team_member_count(team["id"])

    if current_count >= team_size:
        await state.clear()
        await message.answer(
            f"{Emoji.CROSS} Команда уже заполнена ({current_count}/{team_size}).",
            reply_markup=kb.back_button("my_teams"),
            parse_mode="HTML"
        )
        return

    await state.clear()

    # Добавляем в команду
    success = await db.add_team_member(team["id"], player["id"])
    if not success:
        await message.answer(
            f"{Emoji.CROSS} Вы уже состоите в этой команде.",
            reply_markup=kb.back_button("my_teams"),
            parse_mode="HTML"
        )
        return

    members = await db.get_team_members(team["id"])
    captain = await db.get_player_by_id(team["captain_id"])

    await message.answer(
        f"{Emoji.CHECK} <b>Вы присоединились к команде!</b>\n\n"
        f"{Emoji.PEOPLE} <b>Команда:</b> {escape_html(team['name'])}\n"
        f"{Emoji.GAME} <b>Формат:</b> {team['format']}\n"
        f"{Emoji.CROWN} <b>Капитан:</b> {escape_html(captain['nickname'])}\n"
        f"{Emoji.PERSON} <b>Участников:</b> {len(members)}/{team_size}",
        reply_markup=kb.back_button("my_teams"),
        parse_mode="HTML"
    )


# ==================== УПРАВЛЕНИЕ КОМАНДОЙ ====================

@router.callback_query(F.data.regexp(r"^team_(\d+)$"))
async def callback_team_view(callback: CallbackQuery):
    """Просмотр команды."""
    team_id = int(callback.data.split("_")[1])

    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    team = await db.get_team(team_id)
    if not team:
        await callback.answer("Команда не найдена!", show_alert=True)
        return

    members = await db.get_team_members(team_id)
    is_captain = team["captain_id"] == player["id"]

    text = format_team_info(team, members, team["captain_id"])

    await callback.message.edit_text(
        text,
        reply_markup=kb.team_manage(team_id, is_captain, members),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^team_roster_(\d+)$"))
async def callback_team_roster(callback: CallbackQuery):
    """Состав команды."""
    team_id = int(callback.data.split("_")[2])

    team = await db.get_team(team_id)
    if not team:
        await callback.answer("Команда не найдена!", show_alert=True)
        return

    members = await db.get_team_members(team_id)
    team_size = config.TOURNAMENT_FORMATS[team["format"]]["team_size"]

    text = f"<b>{Emoji.LIST} Состав команды {escape_html(team['name'])}</b>\n\n"

    for member in members:
        icon = Emoji.CROWN if member["id"] == team["captain_id"] else Emoji.PERSON
        text += (
            f"{icon} <b>{escape_html(member['nickname'])}</b>\n"
            f"   Steam: {member['steam_link']}\n"
            f"   Контакт: {escape_html(member['contact'])}\n\n"
        )

    text += f"<b>Участников:</b> {len(members)}/{team_size}"

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button(f"team_{team_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^team_new_invite_(\d+)$"))
async def callback_team_new_invite(callback: CallbackQuery):
    """Генерация нового инвайт-кода."""
    team_id = int(callback.data.split("_")[3])

    player = await db.get_player(callback.from_user.id)
    team = await db.get_team(team_id)

    if not player or not team or team["captain_id"] != player["id"]:
        await callback.answer("Вы не капитан этой команды!", show_alert=True)
        return

    new_code = generate_invite_code()
    await db.regenerate_invite_code(team_id, new_code)

    await callback.answer(f"Новый код: {new_code}", show_alert=True)

    # Обновляем сообщение
    members = await db.get_team_members(team_id)
    team = await db.get_team(team_id)  # Перезагружаем с новым кодом
    text = format_team_info(team, members, team["captain_id"])

    await callback.message.edit_text(
        text,
        reply_markup=kb.team_manage(team_id, True, members),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^team_kick_(\d+)$"))
async def callback_team_kick(callback: CallbackQuery):
    """Выбор игрока для кика."""
    team_id = int(callback.data.split("_")[2])

    player = await db.get_player(callback.from_user.id)
    team = await db.get_team(team_id)

    if not player or not team or team["captain_id"] != player["id"]:
        await callback.answer("Вы не капитан этой команды!", show_alert=True)
        return

    members = await db.get_team_members(team_id)

    if len(members) <= 1:
        await callback.answer("В команде нет других участников!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.MINUS} Кик игрока</b>\n\n"
        f"Выберите игрока для удаления из команды:",
        reply_markup=kb.team_members_select(team_id, members, "dokick", player["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^team_dokick_(\d+)_(\d+)$"))
async def callback_team_dokick(callback: CallbackQuery):
    """Кик игрока из команды."""
    parts = callback.data.split("_")
    team_id = int(parts[2])
    member_id = int(parts[3])

    player = await db.get_player(callback.from_user.id)
    team = await db.get_team(team_id)

    if not player or not team or team["captain_id"] != player["id"]:
        await callback.answer("Вы не капитан этой команды!", show_alert=True)
        return

    kicked_player = await db.get_player_by_id(member_id)
    if not kicked_player:
        await callback.answer("Игрок не найден!", show_alert=True)
        return

    await db.remove_team_member(team_id, member_id)

    await callback.answer(
        f"Игрок {escape_html(kicked_player['nickname'])} удалён из команды!",
        show_alert=True
    )

    # Возвращаемся к команде
    members = await db.get_team_members(team_id)
    text = format_team_info(team, members, team["captain_id"])

    await callback.message.edit_text(
        text,
        reply_markup=kb.team_manage(team_id, True, members),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^team_transfer_(\d+)$"))
async def callback_team_transfer(callback: CallbackQuery):
    """Выбор нового капитана."""
    team_id = int(callback.data.split("_")[2])

    player = await db.get_player(callback.from_user.id)
    team = await db.get_team(team_id)

    if not player or not team or team["captain_id"] != player["id"]:
        await callback.answer("Вы не капитан этой команды!", show_alert=True)
        return

    members = await db.get_team_members(team_id)

    if len(members) <= 1:
        await callback.answer("В команде нет других участников!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.CROWN} Передача капитанства</b>\n\n"
        f"Выберите нового капитана:",
        reply_markup=kb.team_members_select(team_id, members, "dotransfer", player["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^team_dotransfer_(\d+)_(\d+)$"))
async def callback_team_dotransfer(callback: CallbackQuery):
    """Передача капитанства."""
    parts = callback.data.split("_")
    team_id = int(parts[2])
    new_captain_id = int(parts[3])

    player = await db.get_player(callback.from_user.id)
    team = await db.get_team(team_id)

    if not player or not team or team["captain_id"] != player["id"]:
        await callback.answer("Вы не капитан этой команды!", show_alert=True)
        return

    new_captain = await db.get_player_by_id(new_captain_id)
    if not new_captain:
        await callback.answer("Игрок не найден!", show_alert=True)
        return

    await db.transfer_captaincy(team_id, new_captain_id)

    await callback.answer(
        f"Капитанство передано игроку {escape_html(new_captain['nickname'])}!",
        show_alert=True
    )

    # Возвращаемся к команде
    team = await db.get_team(team_id)
    members = await db.get_team_members(team_id)
    text = format_team_info(team, members, team["captain_id"])

    await callback.message.edit_text(
        text,
        reply_markup=kb.team_manage(team_id, False, members),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^team_disband_(\d+)$"))
async def callback_team_disband(callback: CallbackQuery):
    """Подтверждение роспуска команды."""
    team_id = int(callback.data.split("_")[2])

    player = await db.get_player(callback.from_user.id)
    team = await db.get_team(team_id)

    if not player or not team or team["captain_id"] != player["id"]:
        await callback.answer("Вы не капитан этой команды!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.WARNING} Роспуск команды</b>\n\n"
        f"Вы уверены, что хотите распустить команду <b>{escape_html(team['name'])}</b>?\n\n"
        f"Это действие необратимо!",
        reply_markup=kb.confirm_cancel(
            f"team_dodelete_{team_id}",
            f"team_{team_id}"
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^team_dodelete_(\d+)$"))
async def callback_team_dodelete(callback: CallbackQuery):
    """Удаление команды."""
    team_id = int(callback.data.split("_")[2])

    player = await db.get_player(callback.from_user.id)
    team = await db.get_team(team_id)

    if not player or not team or team["captain_id"] != player["id"]:
        await callback.answer("Вы не капитан этой команды!", show_alert=True)
        return

    await db.delete_team(team_id)

    await callback.message.edit_text(
        f"{Emoji.CHECK} Команда <b>{escape_html(team['name'])}</b> распущена.",
        reply_markup=kb.back_button("my_teams"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^team_leave_(\d+)$"))
async def callback_team_leave(callback: CallbackQuery):
    """Подтверждение выхода из команды."""
    team_id = int(callback.data.split("_")[2])

    player = await db.get_player(callback.from_user.id)
    team = await db.get_team(team_id)

    if not team:
        await callback.answer("Команда не найдена!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.WARNING} Выход из команды</b>\n\n"
        f"Вы уверены, что хотите покинуть команду <b>{escape_html(team['name'])}</b>?",
        reply_markup=kb.confirm_cancel(
            f"team_doleave_{team_id}",
            f"team_{team_id}"
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^team_doleave_(\d+)$"))
async def callback_team_doleave(callback: CallbackQuery):
    """Выход из команды."""
    team_id = int(callback.data.split("_")[2])

    player = await db.get_player(callback.from_user.id)
    team = await db.get_team(team_id)

    if not player or not team:
        await callback.answer("Ошибка: данные не найдены!", show_alert=True)
        return

    await db.remove_team_member(team_id, player["id"])

    await callback.message.edit_text(
        f"{Emoji.CHECK} Вы покинули команду <b>{escape_html(team['name'])}</b>.",
        reply_markup=kb.back_button("my_teams"),
        parse_mode="HTML"
    )
    await callback.answer()
