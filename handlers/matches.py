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
from config import config as app_config

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
        tournament_id=match["tournament_id"],
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
        reply_markup=kb.match_score_select(match_id, match["tournament_id"]),
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
    tournament_id = data.get("tournament_id", 0)

    text = (
        f"<b>{Emoji.SWORD} Матч</b>\n\n"
        f"<b>{data['p1_name']}</b>\n"
        f"      vs\n"
        f"<b>{data['p2_name']}</b>\n\n"
        f"Выберите счёт (победа <b>{winner_name}</b>):"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.match_score_select(match_id, tournament_id),
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


# ==================== ОЧЕРЕДЬ МАТЧЕЙ ====================

class MatchLinkStates(StatesGroup):
    """Состояния ввода ссылки на матч."""
    waiting_link = State()


@router.callback_query(F.data.regexp(r"^admin_t_queue_(\d+)$"))
async def callback_admin_queue(callback: CallbackQuery):
    """Очередь матчей турнира."""
    from config import config
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    queued = await db.get_queued_matches(tournament_id)
    active = await db.get_active_matches(tournament_id)
    active_count = len(active)

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

    text = f"<b>{Emoji.PLAY} Очередь матчей</b>\n\n"

    if active:
        text += f"<b>🔴 Активные матчи ({active_count}):</b>\n"
        for m in active:
            p1 = participants.get(m["participant1_id"], "TBD")
            p2 = participants.get(m["participant2_id"], "TBD")
            text += f"• {p1} vs {p2}\n"
        text += "\n"

    if queued:
        text += f"<b>⏳ В очереди ({len(queued)}):</b>\n"
        for i, m in enumerate(queued[:5], 1):
            p1 = participants.get(m["participant1_id"], "TBD")
            p2 = participants.get(m["participant2_id"], "TBD")
            text += f"{i}. {p1} vs {p2}\n"
        if len(queued) > 5:
            text += f"...и ещё {len(queued) - 5}\n"
    else:
        text += f"{Emoji.CHECK} Все матчи завершены или запущены!"

    await callback.message.edit_text(
        text,
        reply_markup=kb.match_queue(queued, tournament_id, participants, active_count, config.MAX_ACTIVE_MATCHES),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^match_start_(\d+)$"))
async def callback_match_start(callback: CallbackQuery, state: FSMContext):
    """Начало запуска матча - запрос ссылки."""
    from config import config
    match_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    match = await db.get_match(match_id)
    if not match:
        await callback.answer("Матч не найден!", show_alert=True)
        return

    tournament = await db.get_tournament(match["tournament_id"])

    # Проверяем лимит
    active_count = await db.get_active_matches_count(tournament["id"])
    if active_count >= config.MAX_ACTIVE_MATCHES:
        await callback.answer(f"Лимит активных матчей: {config.MAX_ACTIVE_MATCHES}!", show_alert=True)
        return

    # Получаем имена
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

    await state.update_data(start_match_id=match_id, tournament_id=tournament["id"])

    await callback.message.edit_text(
        f"<b>{Emoji.PLAY} Запуск матча</b>\n\n"
        f"<b>{p1_name}</b> vs <b>{p2_name}</b>\n\n"
        f"Введите ссылку на сервер (или нажмите кнопку ниже):",
        reply_markup=kb.match_start_confirm(match_id, tournament["id"]),
        parse_mode="HTML"
    )
    await state.set_state(MatchLinkStates.waiting_link)
    await callback.answer()


@router.message(MatchLinkStates.waiting_link)
async def process_match_link(message: Message, state: FSMContext):
    """Обработка ссылки на сервер и запуск матча."""
    data = await state.get_data()
    match_id = data.get("start_match_id")
    tournament_id = data.get("tournament_id")
    server_link = message.text.strip()
    await state.clear()

    match = await db.get_match(match_id)
    tournament = await db.get_tournament(tournament_id)

    # Запускаем матч
    await db.start_match(match_id, server_link)

    # Получаем telegram_id участников и отправляем уведомления
    recipients = []
    if tournament["format"] == "1v1":
        p1 = await db.get_player_by_id(match["participant1_id"])
        p2 = await db.get_player_by_id(match["participant2_id"])
        p1_name = p1["nickname"] if p1 else "TBD"
        p2_name = p2["nickname"] if p2 else "TBD"
        if p1:
            recipients.append((p1["telegram_id"], p2_name))
        if p2:
            recipients.append((p2["telegram_id"], p1_name))
    else:
        t1 = await db.get_team(match["participant1_id"])
        t2 = await db.get_team(match["participant2_id"])
        p1_name = t1["name"] if t1 else "TBD"
        p2_name = t2["name"] if t2 else "TBD"
        if t1:
            members1 = await db.get_team_members(t1["id"])
            for m in members1:
                recipients.append((m["telegram_id"], p2_name))
        if t2:
            members2 = await db.get_team_members(t2["id"])
            for m in members2:
                recipients.append((m["telegram_id"], p1_name))

    sent = 0
    for tid, opponent in recipients:
        try:
            text = (
                f"<b>{Emoji.GAME} Ваш матч начинается!</b>\n\n"
                f"<b>Турнир:</b> {tournament['name']}\n"
                f"<b>Соперник:</b> {opponent}\n"
            )
            if server_link:
                text += f"\n<b>Сервер:</b> {server_link}"

            await message.bot.send_message(tid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            pass

    await message.answer(
        f"{Emoji.CHECK} Матч запущен!\n"
        f"Уведомления отправлены: {sent}",
        reply_markup=kb.back_button(f"admin_t_queue_{tournament_id}"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^match_go_(\d+)$"))
async def callback_match_go(callback: CallbackQuery, state: FSMContext):
    """Запуск матча без ссылки."""
    match_id = int(callback.data.split("_")[2])
    await state.clear()

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    match = await db.get_match(match_id)
    tournament = await db.get_tournament(match["tournament_id"])

    # Запускаем матч
    await db.start_match(match_id, None)

    # Уведомляем участников
    recipients = []
    if tournament["format"] == "1v1":
        p1 = await db.get_player_by_id(match["participant1_id"])
        p2 = await db.get_player_by_id(match["participant2_id"])
        p1_name = p1["nickname"] if p1 else "TBD"
        p2_name = p2["nickname"] if p2 else "TBD"
        if p1:
            recipients.append((p1["telegram_id"], p2_name))
        if p2:
            recipients.append((p2["telegram_id"], p1_name))
    else:
        t1 = await db.get_team(match["participant1_id"])
        t2 = await db.get_team(match["participant2_id"])
        p1_name = t1["name"] if t1 else "TBD"
        p2_name = t2["name"] if t2 else "TBD"
        if t1:
            members1 = await db.get_team_members(t1["id"])
            for m in members1:
                recipients.append((m["telegram_id"], p2_name))
        if t2:
            members2 = await db.get_team_members(t2["id"])
            for m in members2:
                recipients.append((m["telegram_id"], p1_name))

    sent = 0
    for tid, opponent in recipients:
        try:
            await callback.bot.send_message(
                tid,
                f"<b>{Emoji.GAME} Ваш матч начинается!</b>\n\n"
                f"<b>Турнир:</b> {tournament['name']}\n"
                f"<b>Соперник:</b> {opponent}\n\n"
                f"Свяжитесь с соперником и начните игру!",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            pass

    await callback.answer(f"Матч запущен! Уведомлений: {sent}", show_alert=True)
    # Возврат к очереди
    await callback.message.delete()


# ==================== ЛОББИ ====================

@router.callback_query(F.data.regexp(r"^admin_t_lobby_(\d+)$"))
async def callback_admin_lobby(callback: CallbackQuery):
    """Просмотр лобби (админ)."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    ready_players = await db.get_ready_players(tournament_id)
    participant_count = await db.get_tournament_participant_count(tournament_id)

    text = f"<b>{Emoji.PEOPLE} Лобби турнира</b>\n\n"
    text += f"<b>Турнир:</b> {tournament['name']}\n\n"

    if ready_players:
        text += f"<b>🟢 Готовы ({len(ready_players)}):</b>\n"
        for p in ready_players:
            text += f"• {escape_html(p['nickname'])}\n"
    else:
        text += f"{Emoji.INFO} Никто ещё не отметился как готовый."

    await callback.message.edit_text(
        text,
        reply_markup=kb.lobby_admin(tournament_id, ready_players, participant_count),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^lobby_remind_(\d+)$"))
async def callback_lobby_remind(callback: CallbackQuery):
    """Напоминание всем участникам о лобби."""
    tournament_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)

    # Получаем всех участников
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
    for tid in recipients:
        try:
            await callback.bot.send_message(
                tid,
                f"<b>{Emoji.BELL} Турнир {tournament['name']}</b>\n\n"
                f"Отметьтесь в лобби, когда будете готовы играть!",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            pass

    await callback.answer(f"Напоминания отправлены: {sent}", show_alert=True)


@router.callback_query(F.data.regexp(r"^lobby_ready_(\d+)$"))
async def callback_lobby_ready(callback: CallbackQuery):
    """Игрок отмечается как готовый."""
    tournament_id = int(callback.data.split("_")[2])

    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    await db.set_player_lobby_status(tournament_id, player["id"], "ready")
    await callback.answer("Вы отмечены как готовый!", show_alert=True)

    # Обновляем сообщение
    await callback.message.edit_text(
        f"<b>{Emoji.CHECK} Вы готовы к игре!</b>\n\n"
        f"Ожидайте начала матча.",
        reply_markup=kb.lobby_player(tournament_id, is_ready=True),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^lobby_away_(\d+)$"))
async def callback_lobby_away(callback: CallbackQuery):
    """Игрок отмечается как отошёл."""
    tournament_id = int(callback.data.split("_")[2])

    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    await db.set_player_lobby_status(tournament_id, player["id"], "away")
    await callback.answer("Статус изменён", show_alert=True)

    await callback.message.edit_text(
        f"<b>{Emoji.CLOCK} Вы отошли</b>\n\n"
        f"Нажмите кнопку ниже, когда будете готовы.",
        reply_markup=kb.lobby_player(tournament_id, is_ready=False),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^player_lobby_(\d+)$"))
async def callback_player_lobby(callback: CallbackQuery):
    """Лобби турнира для игрока."""
    tournament_id = int(callback.data.split("_")[2])

    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    is_ready = await db.get_player_lobby_status(tournament_id, player["id"]) == "ready"

    text = (
        f"<b>🟢 Лобби турнира</b>\n\n"
        f"<b>Турнир:</b> {tournament['name']}\n\n"
    )

    if is_ready:
        text += f"{Emoji.CHECK} Вы отмечены как <b>готовый</b>.\nОжидайте начала матча!"
    else:
        text += f"{Emoji.INFO} Отметьтесь как готовый, когда будете готовы играть."

    await callback.message.edit_text(
        text,
        reply_markup=kb.lobby_player(tournament_id, is_ready),
        parse_mode="HTML"
    )
    await callback.answer()
