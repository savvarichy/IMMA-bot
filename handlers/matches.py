"""Обработчики матчей и турнирной сетки."""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards import kb, Emoji
from utils import (
    format_bracket_text, format_match_info, escape_html,
    generate_cybershoke_config
)

router = Router()


class MatchResultStates(StatesGroup):
    """Состояния ввода результата матча."""
    waiting_score = State()


# ==================== ПРОСМОТР СЕТКИ ====================

@router.callback_query(F.data.regexp(r"^tournament_bracket_(\d+)$"))
async def callback_tournament_bracket(callback: CallbackQuery):
    """Просмотр сетки турнира."""
    tournament_id = int(callback.data.split("_")[2])
    tournament = await db.get_tournament(tournament_id)

    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    matches = await db.get_tournament_matches(tournament_id)

    if not matches:
        await callback.message.edit_text(
            f"{Emoji.INFO} Сетка ещё не сформирована.",
            reply_markup=kb.back_button(f"tournament_{tournament_id}"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # Получаем имена участников
    participants = {}
    if tournament["format"] == "1v1":
        players = await db.get_tournament_players(tournament_id)
        for p in players:
            participants[p["id"]] = p["nickname"]
    else:
        teams = await db.get_tournament_teams(tournament_id)
        for t in teams:
            participants[t["id"]] = t["name"]

    text = format_bracket_text(matches, participants)

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button(f"tournament_{tournament_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== АДМИН: УПРАВЛЕНИЕ МАТЧАМИ ====================

@router.callback_query(F.data.regexp(r"^admin_t_matches_(\d+)$"))
async def callback_admin_matches(callback: CallbackQuery):
    """Список матчей турнира (админ)."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    matches = await db.get_tournament_matches(tournament_id)

    if not matches:
        await callback.message.edit_text(
            f"{Emoji.INFO} Матчи ещё не созданы.",
            reply_markup=kb.back_button(f"admin_t_manage_{tournament_id}"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # Группируем по раундам
    rounds = {}
    for m in matches:
        r = m["round"]
        if r not in rounds:
            rounds[r] = []
        rounds[r].append(m)

    # Получаем имена участников
    participants = {}
    if tournament["format"] == "1v1":
        players = await db.get_tournament_players(tournament_id)
        for p in players:
            participants[p["id"]] = p["nickname"]
    else:
        teams = await db.get_tournament_teams(tournament_id)
        for t in teams:
            participants[t["id"]] = t["name"]

    text = f"<b>{Emoji.SWORD} Матчи турнира</b>\n\n"

    for round_num in sorted(rounds.keys()):
        text += f"<b>Раунд {round_num}</b>\n"
        for match in rounds[round_num]:
            p1 = participants.get(match["participant1_id"], "TBD")
            p2 = participants.get(match["participant2_id"], "TBD")

            status_icon = {
                "pending": Emoji.CLOCK,
                "completed": Emoji.CHECK
            }.get(match["status"], Emoji.INFO)

            if match["status"] == "completed":
                text += f"{status_icon} {p1} {match['score1']}:{match['score2']} {p2}\n"
            else:
                text += f"{status_icon} {p1} vs {p2}\n"
        text += "\n"

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button(f"admin_t_manage_{tournament_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_t_result_(\d+)$"))
async def callback_admin_enter_result(callback: CallbackQuery):
    """Выбор матча для ввода результата."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    matches = await db.get_pending_matches(tournament_id)

    # Фильтруем только матчи с обоими участниками
    ready_matches = [m for m in matches if m["participant1_id"] and m["participant2_id"]]

    if not ready_matches:
        await callback.answer("Нет матчей, готовых к игре!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.PENCIL} Ввод результата</b>\n\n"
        "Выберите матч:",
        reply_markup=kb.matches_list(ready_matches, tournament_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^match_result_(\d+)$"))
async def callback_match_result(callback: CallbackQuery, state: FSMContext):
    """Выбор результата матча."""
    match_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    match = await db.get_match(match_id)
    if not match:
        await callback.answer("Матч не найден!", show_alert=True)
        return

    tournament = await db.get_tournament(match["tournament_id"])

    # Получаем имена участников
    if tournament["format"] == "1v1":
        p1 = await db.get_player_by_id(match["participant1_id"])
        p2 = await db.get_player_by_id(match["participant2_id"])
        p1_name = p1["nickname"] if p1 else "TBD"
        p2_name = p2["nickname"] if p2 else "TBD"
    else:
        t1 = await db.get_team(match["participant1_id"])
        t2 = await db.get_team(match["participant2_id"])
        p1_name = t1["name"] if t1 else "TBD"
        p2_name = t2["name"] if t2 else "TBD"

    await state.update_data(
        match_id=match_id,
        p1_name=p1_name,
        p2_name=p2_name,
        winner_position=1  # По умолчанию победитель - первый
    )

    text = (
        f"<b>{Emoji.SWORD} Матч #{match['match_number']}</b>\n\n"
        f"<b>{p1_name}</b>\n"
        f"      vs\n"
        f"<b>{p2_name}</b>\n\n"
        f"Выберите счёт (победа <b>{p1_name}</b>):"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.match_score_select(match_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^match_swap_(\d+)$"))
async def callback_match_swap_winner(callback: CallbackQuery, state: FSMContext):
    """Переключение победителя."""
    match_id = int(callback.data.split("_")[2])
    data = await state.get_data()

    current_pos = data.get("winner_position", 1)
    new_pos = 2 if current_pos == 1 else 1

    await state.update_data(winner_position=new_pos)

    winner_name = data["p1_name"] if new_pos == 1 else data["p2_name"]

    text = (
        f"<b>{Emoji.SWORD} Матч</b>\n\n"
        f"<b>{data['p1_name']}</b>\n"
        f"      vs\n"
        f"<b>{data['p2_name']}</b>\n\n"
        f"Выберите счёт (победа <b>{winner_name}</b>):"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.match_score_select(match_id),
        parse_mode="HTML"
    )
    await callback.answer(f"Победитель: {winner_name}")


@router.callback_query(F.data.regexp(r"^match_set_(\d+)_(\d+)_(\d+)_(\d)$"))
async def callback_match_set_score(callback: CallbackQuery, state: FSMContext):
    """Установка счёта матча."""
    parts = callback.data.split("_")
    match_id = int(parts[2])
    score1 = int(parts[3])
    score2 = int(parts[4])
    winner_pos = int(parts[5])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    data = await state.get_data()
    actual_winner_pos = data.get("winner_position", 1)

    # Если победитель второй - меняем счёт местами
    if actual_winner_pos == 2:
        score1, score2 = score2, score1

    match = await db.get_match(match_id)
    winner_id = match["participant1_id"] if actual_winner_pos == 1 else match["participant2_id"]

    # Сохраняем результат
    await db.set_match_result(match_id, score1, score2, winner_id)

    # Проводим победителя в следующий раунд
    await advance_winner(match, winner_id)

    await state.clear()

    # Проверяем, завершён ли турнир
    tournament = await db.get_tournament(match["tournament_id"])
    pending = await db.get_pending_matches(match["tournament_id"])

    if not pending:
        # Турнир завершён
        await db.update_tournament_status(match["tournament_id"], "finished")

        # Обновляем статистику победителя
        if tournament["format"] == "1v1":
            winner_player = await db.get_player_by_id(winner_id)
            await db.increment_player_stats(winner_player["telegram_id"], won=True)
        else:
            await db.update_team(winner_id, tournaments_won=tournament.get("tournaments_won", 0) + 1)

        await callback.message.edit_text(
            f"{Emoji.TROPHY} <b>Турнир завершён!</b>\n\n"
            f"Победитель определён. Счёт: {score1}:{score2}",
            reply_markup=kb.back_button("admin"),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"{Emoji.CHECK} Результат сохранён!\n\n"
            f"Счёт: {score1}:{score2}",
            reply_markup=kb.back_button(f"admin_t_manage_{match['tournament_id']}"),
            parse_mode="HTML"
        )

    await db.log_action(
        callback.from_user.id,
        "match_result",
        f"Match {match_id}: {score1}:{score2}"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^match_custom_(\d+)$"))
async def callback_match_custom_score(callback: CallbackQuery, state: FSMContext):
    """Ввод своего счёта."""
    match_id = int(callback.data.split("_")[2])
    await state.update_data(match_id=match_id)

    await callback.message.edit_text(
        f"<b>{Emoji.PENCIL} Ввод счёта</b>\n\n"
        f"Введите счёт в формате:\n"
        f"<code>счёт1:счёт2</code>\n\n"
        f"Например: <code>16:14</code>",
        reply_markup=kb.back_button("admin"),
        parse_mode="HTML"
    )
    await state.set_state(MatchResultStates.waiting_score)
    await callback.answer()


@router.message(MatchResultStates.waiting_score)
async def process_custom_score(message: Message, state: FSMContext):
    """Обработка своего счёта."""
    try:
        parts = message.text.strip().split(":")
        score1 = int(parts[0])
        score2 = int(parts[1])

        if score1 < 0 or score2 < 0:
            raise ValueError()

        if score1 == score2:
            await message.answer(
                f"{Emoji.CROSS} Счёт не может быть ничейным!",
                parse_mode="HTML"
            )
            return

    except (ValueError, IndexError):
        await message.answer(
            f"{Emoji.CROSS} Неверный формат. Введите как: 16:14",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    match_id = data["match_id"]
    actual_winner_pos = data.get("winner_position", 1)

    match = await db.get_match(match_id)

    # Определяем победителя по счёту
    if score1 > score2:
        winner_id = match["participant1_id"]
    else:
        winner_id = match["participant2_id"]

    # Сохраняем результат
    await db.set_match_result(match_id, score1, score2, winner_id)

    # Проводим победителя
    await advance_winner(match, winner_id)

    await state.clear()

    # Проверяем завершение турнира
    pending = await db.get_pending_matches(match["tournament_id"])

    if not pending:
        await db.update_tournament_status(match["tournament_id"], "finished")

    await message.answer(
        f"{Emoji.CHECK} Результат сохранён!\n"
        f"Счёт: {score1}:{score2}",
        reply_markup=kb.back_button("admin"),
        parse_mode="HTML"
    )


async def advance_winner(match: dict, winner_id: int) -> None:
    """Провести победителя в следующий раунд."""
    next_match = await db.get_next_match_for_winner(
        match["tournament_id"],
        match["round"],
        match["match_number"]
    )

    if next_match:
        # Определяем позицию (1 или 2) в следующем матче
        position = 1 if match["match_number"] % 2 == 1 else 2
        await db.update_match_participant(next_match["id"], position, winner_id)


# ==================== КОНФИГ CYBERSHOKE ====================

@router.callback_query(F.data.regexp(r"^match_config_(\d+)$"))
async def callback_match_config(callback: CallbackQuery):
    """Генерация конфига Cybershoke."""
    match_id = int(callback.data.split("_")[2])

    match = await db.get_match(match_id)
    if not match:
        await callback.answer("Матч не найден!", show_alert=True)
        return

    tournament = await db.get_tournament(match["tournament_id"])

    # Получаем имена
    if tournament["format"] == "1v1":
        p1 = await db.get_player_by_id(match["participant1_id"])
        p2 = await db.get_player_by_id(match["participant2_id"])
        name1 = p1["nickname"] if p1 else "Team 1"
        name2 = p2["nickname"] if p2 else "Team 2"
    else:
        t1 = await db.get_team(match["participant1_id"])
        t2 = await db.get_team(match["participant2_id"])
        name1 = t1["name"] if t1 else "Team 1"
        name2 = t2["name"] if t2 else "Team 2"

    config_text = generate_cybershoke_config(tournament, match, name1, name2)

    await callback.message.edit_text(
        config_text,
        reply_markup=kb.back_button(f"admin_t_matches_{tournament['id']}"),
        parse_mode="HTML"
    )
    await callback.answer()
