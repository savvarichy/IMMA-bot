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

    # Ищем АКТИВНЫЕ матчи (уже запущенные), а не pending
    matches = await db.get_active_matches(tournament_id)

    # Фильтруем только матчи с обоими участниками
    ready_matches = [m for m in matches if m["participant1_id"] and m["participant2_id"]]

    if not ready_matches:
        await callback.answer("Нет активных матчей для ввода результата!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.PENCIL} Ввод результата</b>\n\n"
        "Выберите активный матч:",
        reply_markup=kb.active_matches_list(ready_matches, tournament_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^match_result_(\d+)$"))
async def callback_match_result(callback: CallbackQuery, state: FSMContext):
    """Ввод результата матча - сразу запрашиваем счёт."""
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
        p2_name=p2_name
    )

    text = (
        f"<b>{Emoji.SWORD} Матч #{match['match_number']}</b>\n\n"
        f"<b>{p1_name}</b>\n"
        f"      vs\n"
        f"<b>{p2_name}</b>\n\n"
        f"{Emoji.PENCIL} <b>Введите счёт:</b>\n"
        f"Формат: <code>16:14</code>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button(f"mm_control_{match['tournament_id']}"),
        parse_mode="HTML"
    )
    await state.set_state(MatchResultStates.waiting_score)
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

    # Используем complete_manual_match который обновляет статусы участников
    success = await db.complete_manual_match(match_id, winner_id, score1, score2)

    await state.clear()

    if success:
        await callback.message.edit_text(
            f"{Emoji.CHECK} Результат сохранён!\n\n"
            f"Счёт: {score1}:{score2}",
            reply_markup=kb.back_button(f"mm_control_{match['tournament_id']}"),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"{Emoji.CROSS} Ошибка сохранения результата!",
            reply_markup=kb.back_button(f"mm_control_{match['tournament_id']}"),
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

    # Получаем матч для определения правильной кнопки назад
    match = await db.get_match(match_id)
    back_cb = f"admin_t_manage_{match['tournament_id']}" if match else "admin"

    await state.update_data(match_id=match_id, tournament_id=match["tournament_id"] if match else None)

    await callback.message.edit_text(
        f"<b>{Emoji.PENCIL} Ввод счёта</b>\n\n"
        f"Введите счёт в формате:\n"
        f"<code>счёт1:счёт2</code>\n\n"
        f"Например: <code>16:14</code>",
        reply_markup=kb.back_button(back_cb),
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
    match_id = data.get("match_id")
    tournament_id = data.get("tournament_id")

    if not match_id:
        await state.clear()
        await message.answer(f"{Emoji.CROSS} Ошибка: матч не найден!", parse_mode="HTML")
        return

    match = await db.get_match(match_id)
    if not match:
        await state.clear()
        await message.answer(
            f"{Emoji.CROSS} Матч не найден!",
            reply_markup=kb.back_button("admin_tournaments"),
            parse_mode="HTML"
        )
        return

    tournament_id = match["tournament_id"]

    # Определяем победителя по счёту
    if score1 > score2:
        winner_id = match["participant1_id"]
    else:
        winner_id = match["participant2_id"]

    # Используем complete_manual_match который обновляет статусы участников
    success = await db.complete_manual_match(match_id, winner_id, score1, score2)

    await state.clear()

    if success:
        await message.answer(
            f"{Emoji.CHECK} Результат сохранён!\n"
            f"Счёт: {score1}:{score2}",
            reply_markup=kb.back_button(f"mm_control_{tournament_id}"),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"{Emoji.CROSS} Ошибка сохранения результата!",
            reply_markup=kb.back_button(f"mm_control_{tournament_id}"),
            parse_mode="HTML"
        )


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
    if not match:
        await callback.answer("Матч не найден!", show_alert=True)
        return

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
    try:
        await callback.message.delete()
    except Exception:
        pass  # Сообщение уже удалено или недоступно


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

    # Проверяем, что игрок является участником турнира
    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    is_participant = False
    if tournament["format"] == "1v1":
        is_participant = await db.is_player_registered(tournament_id, player["id"])
    else:
        # Для командных турниров проверяем команду игрока
        team = await db.get_player_team_by_format(player["id"], tournament["format"])
        if team:
            is_participant = await db.is_team_registered(tournament_id, team["id"])

    if not is_participant:
        await callback.answer("Вы не являетесь участником этого турнира!", show_alert=True)
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


# ==================== РУЧНАЯ СИСТЕМА МАТЧЕЙ ====================

async def _show_mm_control(callback: CallbackQuery, tournament_id: int):
    """Показать экран управления ручными матчами."""
    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.message.edit_text(
            f"{Emoji.CROSS} Турнир не найден!",
            reply_markup=kb.back_button("admin_tournaments"),
            parse_mode="HTML"
        )
        return

    standings = await db.get_tournament_standings(tournament_id)

    # Подсчёт по статусам
    ready_count = sum(1 for s in standings if s["status"] == "ready")
    in_match_count = sum(1 for s in standings if s["status"] == "in_match")
    eliminated_count = sum(1 for s in standings if s["status"] == "eliminated")
    active_matches = await db.get_active_matches_count(tournament_id)

    text = (
        f"<b>🎮 Управление матчами</b>\n\n"
        f"<b>Турнир:</b> {tournament['name']}\n\n"
        f"🟢 Готовы: {ready_count}\n"
        f"🔴 В матче: {in_match_count}\n"
        f"❌ Выбыли: {eliminated_count}\n\n"
        f"Активных матчей: {active_matches}"
    )

    # Проверка на завершение турнира
    remaining = await db.count_remaining_participants(tournament_id)
    if remaining == 1 and active_matches == 0:
        text += f"\n\n{Emoji.TROPHY} <b>Остался 1 участник - можно завершить турнир!</b>"

    await callback.message.edit_text(
        text,
        reply_markup=kb.manual_match_control(
            tournament_id, ready_count, in_match_count, eliminated_count, active_matches
        ),
        parse_mode="HTML"
    )


async def _get_participants_with_names(tournament_id: int) -> list[dict]:
    """Получить участников с именами для отображения."""
    tournament = await db.get_tournament(tournament_id)
    standings = await db.get_tournament_standings(tournament_id)

    result = []
    if tournament["format"] == "1v1":
        players = await db.get_tournament_players(tournament_id)
        players_dict = {p["id"]: p["nickname"] for p in players}
        for s in standings:
            s["name"] = players_dict.get(s["participant_id"], f"ID:{s['participant_id']}")
            result.append(s)
    else:
        teams = await db.get_tournament_teams(tournament_id)
        teams_dict = {t["id"]: t["name"] for t in teams}
        for s in standings:
            s["name"] = teams_dict.get(s["participant_id"], f"ID:{s['participant_id']}")
            result.append(s)

    return result


@router.callback_query(F.data.regexp(r"^mm_control_(\d+)$"))
async def callback_mm_control(callback: CallbackQuery):
    """Главный экран управления ручными матчами."""
    tournament_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await _show_mm_control(callback, tournament_id)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^mm_create_(\d+)$"))
async def callback_mm_create(callback: CallbackQuery, state: FSMContext):
    """Выбор первого участника для матча."""
    tournament_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    participants = await _get_participants_with_names(tournament_id)
    ready = [p for p in participants if p["status"] == "ready"]

    if len(ready) < 2:
        await callback.answer("Недостаточно готовых участников для матча!", show_alert=True)
        return

    await state.update_data(mm_tournament_id=tournament_id)

    await callback.message.edit_text(
        f"<b>➕ Создание матча</b>\n\n"
        f"Выберите <b>первого</b> участника:",
        reply_markup=kb.participant_select(ready, tournament_id, "p1"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^mm_p1_(\d+)_(\d+)$"))
async def callback_mm_select_p1(callback: CallbackQuery, state: FSMContext):
    """Первый участник выбран, выбираем второго."""
    parts = callback.data.split("_")
    tournament_id = int(parts[2])
    p1_id = int(parts[3])

    await state.update_data(mm_p1_id=p1_id)

    participants = await _get_participants_with_names(tournament_id)
    ready = [p for p in participants if p["status"] == "ready" and p["participant_id"] != p1_id]

    p1_name = next((p["name"] for p in participants if p["participant_id"] == p1_id), "?")

    await callback.message.edit_text(
        f"<b>➕ Создание матча</b>\n\n"
        f"Первый: <b>{p1_name}</b>\n\n"
        f"Выберите <b>соперника</b>:",
        reply_markup=kb.participant_select(ready, tournament_id, "p2", exclude_id=p1_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^mm_p2_(\d+)_(\d+)$"))
async def callback_mm_select_p2(callback: CallbackQuery, state: FSMContext):
    """Второй участник выбран, показываем подтверждение."""
    parts = callback.data.split("_")
    tournament_id = int(parts[2])
    p2_id = int(parts[3])

    data = await state.get_data()
    p1_id = data.get("mm_p1_id")

    participants = await _get_participants_with_names(tournament_id)
    p1_name = next((p["name"] for p in participants if p["participant_id"] == p1_id), "?")
    p2_name = next((p["name"] for p in participants if p["participant_id"] == p2_id), "?")

    await state.update_data(mm_p2_id=p2_id)

    await callback.message.edit_text(
        f"<b>⚔️ Новый матч</b>\n\n"
        f"<b>{p1_name}</b>\n   vs\n<b>{p2_name}</b>\n\n"
        f"Введите ссылку на сервер или запустите без ссылки:",
        reply_markup=kb.match_confirm(tournament_id, p1_id, p2_id, p1_name, p2_name),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^mm_go_(\d+)_(\d+)_(\d+)$"))
async def callback_mm_go(callback: CallbackQuery, state: FSMContext):
    """Создать матч без ссылки."""
    parts = callback.data.split("_")
    tournament_id = int(parts[2])
    p1_id = int(parts[3])
    p2_id = int(parts[4])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    participant_type = "player" if tournament["format"] == "1v1" else "team"

    # Проверяем что оба участника всё ещё ready
    p1_status = await db.get_participant_status(tournament_id, p1_id, participant_type)
    p2_status = await db.get_participant_status(tournament_id, p2_id, participant_type)

    if not p1_status or p1_status["status"] != "ready":
        await callback.answer("Первый участник уже не готов!", show_alert=True)
        return

    if not p2_status or p2_status["status"] != "ready":
        await callback.answer("Второй участник уже не готов!", show_alert=True)
        return

    # Создаём матч
    match_id = await db.create_manual_match(
        tournament_id, p1_id, p2_id, participant_type
    )

    await state.clear()

    # Получаем имена для уведомлений
    participants = await _get_participants_with_names(tournament_id)
    p1_name = next((p["name"] for p in participants if p["participant_id"] == p1_id), "?")
    p2_name = next((p["name"] for p in participants if p["participant_id"] == p2_id), "?")

    # Отправляем уведомления участникам
    bot = callback.bot
    notification_text = (
        f"<b>⚔️ Ваш матч начался!</b>\n\n"
        f"<b>{p1_name}</b> vs <b>{p2_name}</b>\n\n"
        f"Турнир: {tournament['name']}"
    )

    if tournament["format"] == "1v1":
        # Уведомляем игроков
        for pid in [p1_id, p2_id]:
            player = await db.get_player_by_id(pid)
            if player:
                try:
                    await bot.send_message(player["telegram_id"], notification_text, parse_mode="HTML")
                except Exception:
                    pass
    else:
        # Уведомляем команды
        for tid in [p1_id, p2_id]:
            members = await db.get_team_members(tid)
            for member in members:
                try:
                    await bot.send_message(member["telegram_id"], notification_text, parse_mode="HTML")
                except Exception:
                    pass

    await callback.message.edit_text(
        f"<b>{Emoji.CHECK} Матч создан!</b>\n\n"
        f"<b>{p1_name}</b> vs <b>{p2_name}</b>\n\n"
        f"Уведомления отправлены участникам.",
        reply_markup=kb.back_button(f"mm_control_{tournament_id}"),
        parse_mode="HTML"
    )
    await callback.answer("Матч создан!")


@router.callback_query(F.data.regexp(r"^mm_active_(\d+)$"))
async def callback_mm_active(callback: CallbackQuery):
    """Список активных матчей."""
    tournament_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    matches = await db.get_active_matches(tournament_id)
    tournament = await db.get_tournament(tournament_id)

    if not matches:
        await callback.answer("Нет активных матчей!", show_alert=True)
        return

    # Получаем имена участников
    participants_names = {}
    if tournament["format"] == "1v1":
        players = await db.get_tournament_players(tournament_id)
        participants_names = {p["id"]: p["nickname"] for p in players}
    else:
        teams = await db.get_tournament_teams(tournament_id)
        participants_names = {t["id"]: t["name"] for t in teams}

    await callback.message.edit_text(
        f"<b>🔴 Активные матчи</b>\n\n"
        f"Выберите матч для управления:",
        reply_markup=kb.active_matches_control(matches, tournament_id, participants_names),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^mm_cancel_(\d+)$"))
async def callback_mm_cancel(callback: CallbackQuery):
    """Отменить матч."""
    match_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    match = await db.get_match(match_id)
    if not match:
        await callback.answer("Матч не найден!", show_alert=True)
        return

    success = await db.cancel_match(match_id)
    if success:
        await callback.answer("Матч отменён!", show_alert=True)
        # Возвращаемся к управлению
        await _show_mm_control(callback, match['tournament_id'])
    else:
        await callback.answer("Не удалось отменить матч!", show_alert=True)


@router.callback_query(F.data.regexp(r"^mm_restore_(\d+)$"))
async def callback_mm_restore(callback: CallbackQuery):
    """Выбор выбывшего участника для возврата."""
    tournament_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    participants = await _get_participants_with_names(tournament_id)
    eliminated = [p for p in participants if p["status"] == "eliminated"]

    if not eliminated:
        await callback.answer("Нет выбывших участников!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>🔄 Возврат участника</b>\n\n"
        f"Выберите участника для возврата в турнир:",
        reply_markup=kb.restore_participant_select(eliminated, tournament_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^mm_do_restore_(\d+)_(\d+)$"))
async def callback_mm_do_restore(callback: CallbackQuery):
    """Выполнить возврат участника."""
    parts = callback.data.split("_")
    tournament_id = int(parts[3])
    participant_id = int(parts[4])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    participant_type = "player" if tournament["format"] == "1v1" else "team"

    await db.restore_participant(tournament_id, participant_id, participant_type)

    await callback.answer("Участник возвращён в турнир!", show_alert=True)
    # Возвращаемся к управлению - показываем экран напрямую
    await _show_mm_control(callback, tournament_id)


@router.callback_query(F.data.regexp(r"^mm_participants_(\d+)$"))
async def callback_mm_participants(callback: CallbackQuery):
    """Показать всех участников со статусами."""
    tournament_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    participants = await _get_participants_with_names(tournament_id)

    status_icons = {"ready": "🟢", "in_match": "🔴", "eliminated": "❌"}
    has_eliminated = any(p["status"] == "eliminated" for p in participants)

    text = f"<b>👥 Участники турнира</b>\n\n"
    for p in participants:
        icon = status_icons.get(p["status"], "")
        losses = p.get("losses", 0)
        text += f"{icon} {p['name']} ({p['wins']}W/{losses}L)\n"

    await callback.message.edit_text(
        text,
        reply_markup=kb.participants_menu(tournament_id, has_eliminated),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^mm_match_(\d+)$"))
async def callback_mm_match_view(callback: CallbackQuery):
    """Просмотр и управление активным матчем."""
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
        p1_name = p1["nickname"] if p1 else "?"
        p2_name = p2["nickname"] if p2 else "?"
    else:
        t1 = await db.get_team(match["participant1_id"])
        t2 = await db.get_team(match["participant2_id"])
        p1_name = t1["name"] if t1 else "?"
        p2_name = t2["name"] if t2 else "?"

    text = (
        f"<b>🔴 Активный матч #{match['match_number']}</b>\n\n"
        f"<b>{p1_name}</b>\n   vs\n<b>{p2_name}</b>\n\n"
    )
    if match.get("server_link"):
        text += f"<b>Сервер:</b> {match['server_link']}\n"
    if match.get("started_at"):
        text += f"<b>Начат:</b> {match['started_at']}\n"

    await callback.message.edit_text(
        text,
        reply_markup=kb.match_actions(match_id, match["tournament_id"]),
        parse_mode="HTML"
    )
    await callback.answer()


class ManualMatchLinkStates(StatesGroup):
    """Состояния ввода ссылки для ручного матча."""
    waiting_link = State()
    waiting_password = State()


@router.callback_query(F.data.regexp(r"^mm_link_(\d+)_(\d+)_(\d+)$"))
async def callback_mm_link_start(callback: CallbackQuery, state: FSMContext):
    """Начать ввод ссылки на сервер для ручного матча."""
    parts = callback.data.split("_")
    tournament_id = int(parts[2])
    p1_id = int(parts[3])
    p2_id = int(parts[4])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(
        mm_tournament_id=tournament_id,
        mm_p1_id=p1_id,
        mm_p2_id=p2_id
    )

    participants = await _get_participants_with_names(tournament_id)
    p1_name = next((p["name"] for p in participants if p["participant_id"] == p1_id), "?")
    p2_name = next((p["name"] for p in participants if p["participant_id"] == p2_id), "?")

    await callback.message.edit_text(
        f"<b>🔗 Ссылка на сервер</b>\n\n"
        f"<b>{p1_name}</b> vs <b>{p2_name}</b>\n\n"
        f"Введите ссылку на сервер (например, connect ip:port):",
        reply_markup=kb.back_button(f"mm_control_{tournament_id}"),
        parse_mode="HTML"
    )
    await state.set_state(ManualMatchLinkStates.waiting_link)
    await callback.answer()


@router.message(ManualMatchLinkStates.waiting_link)
async def process_mm_link(message: Message, state: FSMContext):
    """Обработка ссылки — показываем кнопки для пароля."""
    # Проверка прав администратора
    if not await db.is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Нет доступа!")
        return

    data = await state.get_data()
    tournament_id = data.get("mm_tournament_id")
    p1_id = data.get("mm_p1_id")
    p2_id = data.get("mm_p2_id")
    server_link = message.text.strip()

    tournament = await db.get_tournament(tournament_id)
    participant_type = "player" if tournament["format"] == "1v1" else "team"

    # Проверяем что оба участника всё ещё ready
    p1_status = await db.get_participant_status(tournament_id, p1_id, participant_type)
    p2_status = await db.get_participant_status(tournament_id, p2_id, participant_type)

    if not p1_status or p1_status["status"] != "ready" or not p2_status or p2_status["status"] != "ready":
        await state.clear()
        await message.answer(
            f"{Emoji.CROSS} Один из участников уже не готов. Матч не создан.",
            reply_markup=kb.back_button(f"mm_control_{tournament_id}"),
            parse_mode="HTML"
        )
        return

    # Сохраняем ссылку и показываем кнопки для пароля
    await state.update_data(mm_server_link=server_link)

    participants = await _get_participants_with_names(tournament_id)
    p1_name = next((p["name"] for p in participants if p["participant_id"] == p1_id), "?")
    p2_name = next((p["name"] for p in participants if p["participant_id"] == p2_id), "?")

    await message.answer(
        f"<b>🔗 Ссылка сохранена!</b>\n\n"
        f"<b>{p1_name}</b> vs <b>{p2_name}</b>\n"
        f"<b>Сервер:</b> {server_link}\n\n"
        f"Добавить пароль к серверу?",
        reply_markup=kb.match_password_choice(tournament_id, p1_id, p2_id),
        parse_mode="HTML"
    )
    await state.set_state(None)  # Убираем состояние, ждём кнопку


@router.callback_query(F.data.regexp(r"^mm_add_pwd_(\d+)_(\d+)_(\d+)$"))
async def callback_mm_add_password(callback: CallbackQuery, state: FSMContext):
    """Запросить ввод пароля."""
    parts = callback.data.split("_")
    tournament_id = int(parts[3])
    p1_id = int(parts[4])
    p2_id = int(parts[5])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(
        mm_tournament_id=tournament_id,
        mm_p1_id=p1_id,
        mm_p2_id=p2_id
    )

    await callback.message.edit_text(
        f"<b>🔑 Введите пароль сервера:</b>",
        reply_markup=kb.back_button(f"mm_control_{tournament_id}"),
        parse_mode="HTML"
    )
    await state.set_state(ManualMatchLinkStates.waiting_password)
    await callback.answer()


@router.message(ManualMatchLinkStates.waiting_password)
async def process_mm_password(message: Message, state: FSMContext):
    """Обработка пароля и создание матча."""
    if not await db.is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Нет доступа!")
        return

    data = await state.get_data()
    server_password = message.text.strip()

    await _create_match_with_notification(
        message, state, data, server_password
    )


@router.callback_query(F.data.regexp(r"^mm_no_pwd_(\d+)_(\d+)_(\d+)$"))
async def callback_mm_no_password(callback: CallbackQuery, state: FSMContext):
    """Создать матч без пароля."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    data = await state.get_data()

    await _create_match_with_notification(
        callback, state, data, None
    )


async def _create_match_with_notification(
    event,
    state: FSMContext,
    data: dict,
    server_password: str = None
):
    """Создание матча и отправка уведомлений."""
    tournament_id = data.get("mm_tournament_id")
    p1_id = data.get("mm_p1_id")
    p2_id = data.get("mm_p2_id")
    server_link = data.get("mm_server_link")

    tournament = await db.get_tournament(tournament_id)
    participant_type = "player" if tournament["format"] == "1v1" else "team"

    # Проверяем что оба участника всё ещё ready
    p1_status = await db.get_participant_status(tournament_id, p1_id, participant_type)
    p2_status = await db.get_participant_status(tournament_id, p2_id, participant_type)

    if not p1_status or p1_status["status"] != "ready" or not p2_status or p2_status["status"] != "ready":
        await state.clear()
        error_text = f"{Emoji.CROSS} Один из участников уже не готов. Матч не создан."
        if isinstance(event, Message):
            await event.answer(
                error_text,
                reply_markup=kb.back_button(f"mm_control_{tournament_id}"),
                parse_mode="HTML"
            )
        else:
            await event.message.edit_text(
                error_text,
                reply_markup=kb.back_button(f"mm_control_{tournament_id}"),
                parse_mode="HTML"
            )
        return

    await state.clear()

    # Создаём матч с ссылкой и паролем
    match_id = await db.create_manual_match(
        tournament_id, p1_id, p2_id, participant_type, server_link, server_password
    )

    # Получаем имена для уведомлений
    participants = await _get_participants_with_names(tournament_id)
    p1_name = next((p["name"] for p in participants if p["participant_id"] == p1_id), "?")
    p2_name = next((p["name"] for p in participants if p["participant_id"] == p2_id), "?")

    # Формируем текст уведомления
    notification_text = (
        f"<b>⚔️ Ваш матч начался!</b>\n\n"
        f"<b>{p1_name}</b> vs <b>{p2_name}</b>\n\n"
        f"<b>Турнир:</b> {tournament['name']}\n"
        f"<b>🔗 Сервер:</b> <code>{server_link}</code>"
    )
    if server_password:
        notification_text += f"\n<b>🔑 Пароль:</b> <code>{server_password}</code>"

    # Отправляем уведомления участникам
    bot = event.bot if hasattr(event, 'bot') else event.message.bot
    if tournament["format"] == "1v1":
        for pid in [p1_id, p2_id]:
            player = await db.get_player_by_id(pid)
            if player:
                try:
                    await bot.send_message(player["telegram_id"], notification_text, parse_mode="HTML")
                except Exception:
                    pass
    else:
        for tid in [p1_id, p2_id]:
            members = await db.get_team_members(tid)
            for member in members:
                try:
                    await bot.send_message(member["telegram_id"], notification_text, parse_mode="HTML")
                except Exception:
                    pass

    # Формируем ответ админу
    admin_text = (
        f"<b>{Emoji.CHECK} Матч создан!</b>\n\n"
        f"<b>{p1_name}</b> vs <b>{p2_name}</b>\n\n"
        f"<b>Ссылка:</b> {server_link}\n"
    )
    if server_password:
        admin_text += f"<b>Пароль:</b> {server_password}\n"
    admin_text += f"\nУведомления отправлены участникам."

    if isinstance(event, Message):
        await event.answer(
            admin_text,
            reply_markup=kb.back_button(f"mm_control_{tournament_id}"),
            parse_mode="HTML"
        )
    else:
        await event.message.edit_text(
            admin_text,
            reply_markup=kb.back_button(f"mm_control_{tournament_id}"),
            parse_mode="HTML"
        )
