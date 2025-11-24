"""Обработчики турниров (пользовательские и админские)."""
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery

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
    waiting_custom_map = State()
    waiting_participants = State()
    waiting_custom_participants = State()
    waiting_prize_type = State()
    waiting_prize_places = State()
    waiting_prize_1 = State()
    waiting_prize_2 = State()
    waiting_prize_3 = State()
    waiting_date = State()
    waiting_time = State()
    waiting_checkin = State()
    waiting_entry_fee = State()
    confirm = State()


class EditTournamentStates(StatesGroup):
    """Состояния редактирования турнира."""
    waiting_name = State()
    waiting_date = State()
    waiting_time = State()
    waiting_participants = State()
    waiting_prize_1 = State()
    waiting_prize_2 = State()
    waiting_prize_3 = State()
    waiting_custom_map = State()


class BroadcastStates(StatesGroup):
    """Состояния рассылки."""
    waiting_message = State()


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def _show_tournament_manage(callback: CallbackQuery, tournament_id: int) -> None:
    """Показать меню управления турниром (админ)."""
    from aiogram.exceptions import TelegramBadRequest

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    participant_count = await db.get_tournament_participant_count(tournament_id)
    text = format_tournament_info(tournament, participant_count)

    # Добавляем информацию о собранных взносах для админа
    entry_fee = tournament.get("entry_fee", 0)
    if entry_fee > 0:
        fees_info = await db.get_tournament_collected_fees(tournament_id)
        if fees_info:
            text += f"\n\n{Emoji.STAR} <b>Собрано взносов:</b> {fees_info['total']} ⭐ ({fees_info['count']} шт.)"

    # Проверяем статус участия админа как игрока
    is_registered = False
    can_register = False
    is_in_reserve = False

    player = await db.get_player(callback.from_user.id)
    if player:
        if tournament["format"] == "1v1":
            is_registered = await db.is_player_registered(tournament_id, player["id"])
            can_register = True
            if not is_registered:
                is_in_reserve = await db.is_player_in_reserve(tournament_id, player["id"])
        else:
            team = await db.get_player_team_by_format(player["id"], tournament["format"])
            if team:
                is_registered = await db.is_team_registered(tournament_id, team["id"])
                can_register = team["captain_id"] == player["id"]
                if not is_registered:
                    is_in_reserve = await db.is_team_in_reserve(tournament_id, team["id"])

    is_checkin = tournament["status"] == "checkin"

    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.admin_tournament_manage(
                tournament, is_registered, can_register, is_checkin, is_in_reserve
            ),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()


async def _show_tournament_view(callback: CallbackQuery, tournament_id: int) -> None:
    """Показать турнир пользователю."""
    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    # Если админ - показываем управление турниром
    if await db.is_admin(callback.from_user.id):
        await _show_tournament_manage(callback, tournament_id)
        return

    player = await db.get_player(callback.from_user.id)
    participant_count = await db.get_tournament_participant_count(tournament_id)

    is_registered = False
    can_register = False
    checked_in = False
    team_status_text = ""
    is_in_reserve = False
    reserve_position = 0

    if player:
        if tournament["format"] == "1v1":
            is_registered = await db.is_player_registered(tournament_id, player["id"])
            can_register = True
            if not is_registered:
                is_in_reserve = await db.is_player_in_reserve(tournament_id, player["id"])
                if is_in_reserve:
                    reserve_position = await db.get_reserve_position(tournament_id, player_id=player["id"])
        else:
            team = await db.get_player_team_by_format(player["id"], tournament["format"])
            if team:
                is_registered = await db.is_team_registered(tournament_id, team["id"])
                can_register = team["captain_id"] == player["id"]
                if not can_register and not is_registered:
                    team_status_text = f"\n\n{Emoji.INFO} Только капитан команды может зарегистрировать её на турнир."
                if not is_registered:
                    is_in_reserve = await db.is_team_in_reserve(tournament_id, team["id"])
                    if is_in_reserve:
                        reserve_position = await db.get_reserve_position(tournament_id, team_id=team["id"])
            else:
                format_name = config.TOURNAMENT_FORMATS.get(tournament["format"], {}).get("name", tournament["format"])
                team_status_text = f"\n\n{Emoji.WARNING} У вас нет команды формата <b>{format_name}</b>. Создайте или вступите в команду."

    is_checkin = tournament["status"] == "checkin"

    text = format_tournament_info(tournament, participant_count)

    if is_in_reserve:
        text += f"\n\n{Emoji.CLOCK} <b>Вы в резервном списке</b> (позиция {reserve_position})"

    if team_status_text:
        text += team_status_text

    from aiogram.exceptions import TelegramBadRequest
    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.tournament_view(
                tournament, is_registered, can_register, is_checkin, checked_in, is_in_reserve
            ),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()


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
    """Просмотр турнира (с определением контекста: админ или юзер)."""
    tournament_id = int(callback.data.split("_")[1])
    tournament = await db.get_tournament(tournament_id)

    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    # Если админ - показываем управление турниром
    if await db.is_admin(callback.from_user.id):
        await _show_tournament_manage(callback, tournament_id)
        return

    # Для обычных пользователей - просмотр турнира
    player = await db.get_player(callback.from_user.id)
    participant_count = await db.get_tournament_participant_count(tournament_id)

    is_registered = False
    can_register = False
    checked_in = False
    team_status_text = ""
    is_in_reserve = False
    reserve_position = 0

    if player:
        if tournament["format"] == "1v1":
            is_registered = await db.is_player_registered(tournament_id, player["id"])
            can_register = True
            # Проверяем резерв
            if not is_registered:
                is_in_reserve = await db.is_player_in_reserve(tournament_id, player["id"])
                if is_in_reserve:
                    reserve_position = await db.get_reserve_position(tournament_id, player_id=player["id"])
        else:
            # Проверяем команду нужного формата
            team = await db.get_player_team_by_format(player["id"], tournament["format"])
            if team:
                is_registered = await db.is_team_registered(tournament_id, team["id"])
                # Только капитан может регистрировать
                can_register = team["captain_id"] == player["id"]
                if not can_register and not is_registered:
                    team_status_text = f"\n\n{Emoji.INFO} Только капитан команды может зарегистрировать её на турнир."
                # Проверяем резерв для команды
                if not is_registered:
                    is_in_reserve = await db.is_team_in_reserve(tournament_id, team["id"])
                    if is_in_reserve:
                        reserve_position = await db.get_reserve_position(tournament_id, team_id=team["id"])
            else:
                # У игрока нет команды нужного формата
                format_name = config.TOURNAMENT_FORMATS.get(tournament["format"], {}).get("name", tournament["format"])
                team_status_text = f"\n\n{Emoji.WARNING} У вас нет команды формата <b>{format_name}</b>. Создайте или вступите в команду."

    is_checkin = tournament["status"] == "checkin"

    text = format_tournament_info(tournament, participant_count)

    # Показываем позицию в резерве
    if is_in_reserve:
        text += f"\n\n{Emoji.CLOCK} <b>Вы в резервном списке</b> (позиция {reserve_position})"

    if team_status_text:
        text += team_status_text

    await callback.message.edit_text(
        text,
        reply_markup=kb.tournament_view(
            tournament, is_registered, can_register, is_checkin, checked_in, is_in_reserve
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^tournament_leave_reserve_(\d+)$"))
async def callback_tournament_leave_reserve(callback: CallbackQuery):
    """Выход из резервного списка."""
    tournament_id = int(callback.data.split("_")[3])

    player = await db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    if tournament["format"] == "1v1":
        await db.remove_player_from_reserve(tournament_id, player["id"])
    else:
        team = await db.get_player_team_by_format(player["id"], tournament["format"])
        if team:
            await db.remove_team_from_reserve(tournament_id, team["id"])

    await callback.answer("Вы покинули резервный список!", show_alert=True)
    await _show_tournament_view(callback, tournament_id)


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

    # Проверяем бан
    if await db.is_player_banned(player["id"]):
        await callback.answer("Вы заблокированы и не можете участвовать в турнирах!", show_alert=True)
        return

    participant_count = await db.get_tournament_participant_count(tournament_id)
    is_full = participant_count >= tournament["max_participants"]

    entry_fee = tournament.get("entry_fee", 0)

    if tournament["format"] == "1v1":
        # Проверяем лимит турниров
        if config.MAX_ACTIVE_TOURNAMENTS_PER_PLAYER > 0:
            active_count = await db.get_player_active_tournament_count(player["id"])
            if active_count >= config.MAX_ACTIVE_TOURNAMENTS_PER_PLAYER:
                await callback.answer(
                    f"Вы уже зарегистрированы на {active_count} турниров! Лимит: {config.MAX_ACTIVE_TOURNAMENTS_PER_PLAYER}",
                    show_alert=True
                )
                return

        if is_full:
            # Предлагаем резерв (без оплаты)
            success = await db.add_player_to_reserve(tournament_id, player["id"])
            if success:
                pos = await db.get_reserve_position(tournament_id, player_id=player["id"])
                await callback.answer(f"Турнир заполнен! Вы добавлены в резерв (позиция {pos})", show_alert=True)
            else:
                await callback.answer("Турнир заполнен и резерв тоже!", show_alert=True)
        elif entry_fee > 0:
            # Проверяем, не зарегистрирован ли уже
            existing = await db.get_player_registration(tournament_id, player["id"])
            if existing:
                await callback.answer("Вы уже зарегистрированы!", show_alert=True)
                return

            # Отправляем инвойс на оплату
            await callback.bot.send_invoice(
                chat_id=callback.from_user.id,
                title=f"Участие в турнире",
                description=f"Взнос за участие в турнире «{tournament['name']}»",
                payload=f"tournament_player_{tournament_id}_{player['id']}",
                provider_token="",  # Пустой для Telegram Stars
                currency="XTR",
                prices=[LabeledPrice(label="Взнос", amount=entry_fee)]
            )
            await callback.answer()
            return
        else:
            success = await db.register_player_to_tournament(tournament_id, player["id"])
            if success:
                await callback.answer("Вы зарегистрированы на турнир!", show_alert=True)
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

        if is_full:
            # Предлагаем резерв (без оплаты)
            success = await db.add_team_to_reserve(tournament_id, team["id"])
            if success:
                pos = await db.get_reserve_position(tournament_id, team_id=team["id"])
                await callback.answer(f"Турнир заполнен! Команда добавлена в резерв (позиция {pos})", show_alert=True)
            else:
                await callback.answer("Турнир заполнен и резерв тоже!", show_alert=True)
        elif entry_fee > 0:
            # Проверяем, не зарегистрирована ли уже команда
            existing = await db.get_team_registration(tournament_id, team["id"])
            if existing:
                await callback.answer("Команда уже зарегистрирована!", show_alert=True)
                return

            # Отправляем инвойс на оплату (капитан платит за команду)
            await callback.bot.send_invoice(
                chat_id=callback.from_user.id,
                title=f"Участие команды в турнире",
                description=f"Взнос за участие команды «{team['name']}» в турнире «{tournament['name']}»",
                payload=f"tournament_team_{tournament_id}_{team['id']}",
                provider_token="",  # Пустой для Telegram Stars
                currency="XTR",
                prices=[LabeledPrice(label="Взнос", amount=entry_fee)]
            )
            await callback.answer()
            return
        else:
            success = await db.register_team_to_tournament(tournament_id, team["id"])
            if success:
                await callback.answer(
                    f"Команда {team['name']} зарегистрирована!",
                    show_alert=True
                )
                await _update_channel_post_if_exists(tournament_id, callback.bot)
            else:
                await callback.answer("Команда уже зарегистрирована!", show_alert=True)

    # Обновляем просмотр
    await _show_tournament_view(callback, tournament_id)


@router.callback_query(F.data.regexp(r"^tournament_unreg_(\d+)$"))
async def callback_tournament_unregister(callback: CallbackQuery):
    """Отмена регистрации."""
    tournament_id = int(callback.data.split("_")[2])
    tournament = await db.get_tournament(tournament_id)

    if not tournament or tournament["status"] not in ("open", "checkin"):
        await callback.answer("Нельзя отменить регистрацию!", show_alert=True)
        return

    player = await db.get_player(callback.from_user.id)
    refund_success = False
    refund_message = ""

    if tournament["format"] == "1v1":
        # Получаем регистрацию для возврата
        registration = await db.get_player_registration(tournament_id, player["id"])
        payment_charge_id = registration.get("payment_charge_id") if registration else None

        await db.unregister_player_from_tournament(tournament_id, player["id"])

        # Возвращаем Stars если был платёж
        if payment_charge_id:
            try:
                await callback.bot.refund_star_payment(
                    user_id=callback.from_user.id,
                    telegram_payment_charge_id=payment_charge_id
                )
                refund_success = True
                refund_message = f"\n{Emoji.STAR} Взнос {tournament.get('entry_fee', 0)} ⭐ возвращён!"
            except Exception as e:
                refund_message = f"\n{Emoji.WARNING} Ошибка возврата взноса"
    else:
        team = await db.get_player_team_by_format(player["id"], tournament["format"])
        if team and team["captain_id"] == player["id"]:
            # Получаем регистрацию для возврата
            registration = await db.get_team_registration(tournament_id, team["id"])
            payment_charge_id = registration.get("payment_charge_id") if registration else None

            await db.unregister_team_from_tournament(tournament_id, team["id"])

            # Возвращаем Stars если был платёж
            if payment_charge_id:
                try:
                    await callback.bot.refund_star_payment(
                        user_id=callback.from_user.id,
                        telegram_payment_charge_id=payment_charge_id
                    )
                    refund_success = True
                    refund_message = f"\n{Emoji.STAR} Взнос {tournament.get('entry_fee', 0)} ⭐ возвращён!"
                except Exception as e:
                    refund_message = f"\n{Emoji.WARNING} Ошибка возврата взноса"

    await callback.answer(f"Регистрация отменена!{refund_message}", show_alert=True)
    # Обновляем пост в канале
    await _update_channel_post_if_exists(tournament_id, callback.bot)
    await _show_tournament_view(callback, tournament_id)


# ==================== ПЛАТЕЖИ ====================

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout: PreCheckoutQuery):
    """Проверка перед оплатой."""
    payload = pre_checkout.invoice_payload

    # Проверяем формат payload
    if not payload.startswith("tournament_"):
        await pre_checkout.answer(ok=False, error_message="Неверный платёж")
        return

    parts = payload.split("_")
    if len(parts) != 4:
        await pre_checkout.answer(ok=False, error_message="Неверный формат платежа")
        return

    reg_type = parts[1]  # "player" или "team"
    tournament_id = int(parts[2])
    participant_id = int(parts[3])

    # Проверяем турнир
    tournament = await db.get_tournament(tournament_id)
    if not tournament or tournament["status"] != "open":
        await pre_checkout.answer(ok=False, error_message="Регистрация на турнир закрыта")
        return

    # Проверяем, что ещё есть места
    participant_count = await db.get_tournament_participant_count(tournament_id)
    if participant_count >= tournament["max_participants"]:
        await pre_checkout.answer(ok=False, error_message="Турнир уже заполнен")
        return

    # Проверяем, что участник ещё не зарегистрирован
    if reg_type == "player":
        existing = await db.get_player_registration(tournament_id, participant_id)
    else:
        existing = await db.get_team_registration(tournament_id, participant_id)

    if existing:
        await pre_checkout.answer(ok=False, error_message="Уже зарегистрирован")
        return

    # Всё ок, разрешаем оплату
    await pre_checkout.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Обработка успешного платежа."""
    payment = message.successful_payment
    payload = payment.invoice_payload

    if not payload.startswith("tournament_"):
        return

    parts = payload.split("_")
    if len(parts) != 4:
        return

    reg_type = parts[1]  # "player" или "team"
    tournament_id = int(parts[2])
    participant_id = int(parts[3])

    payment_charge_id = payment.telegram_payment_charge_id

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        return

    if reg_type == "player":
        # Регистрируем игрока
        success = await db.register_player_to_tournament(tournament_id, participant_id)
        if success:
            await db.set_player_payment(tournament_id, participant_id, payment_charge_id)
            await message.answer(
                f"{Emoji.CHECK} <b>Оплата прошла успешно!</b>\n\n"
                f"Вы зарегистрированы на турнир «{tournament['name']}».\n"
                f"Взнос: {payment.total_amount} ⭐",
                parse_mode="HTML"
            )
            await _update_channel_post_if_exists(tournament_id, message.bot)
    else:
        # Регистрируем команду
        success = await db.register_team_to_tournament(tournament_id, participant_id)
        if success:
            await db.set_team_payment(tournament_id, participant_id, payment_charge_id)
            team = await db.get_team(participant_id)
            team_name = team["name"] if team else "Команда"
            await message.answer(
                f"{Emoji.CHECK} <b>Оплата прошла успешно!</b>\n\n"
                f"Команда «{team_name}» зарегистрирована на турнир «{tournament['name']}».\n"
                f"Взнос: {payment.total_amount} ⭐",
                parse_mode="HTML"
            )
            await _update_channel_post_if_exists(tournament_id, message.bot)


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
    await _show_tournament_view(callback, tournament_id)


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
            # Формируем ссылку на профиль
            if p.get("username"):
                profile_link = f"<a href=\"https://t.me/{p['username']}\">{escape_html(p['nickname'])}</a>"
            else:
                profile_link = f"<a href=\"tg://user?id={p['telegram_id']}\">{escape_html(p['nickname'])}</a>"
            text += f"{i}. {profile_link} {check}\n"
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
    from aiogram.exceptions import TelegramBadRequest

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    try:
        await callback.message.edit_text(
            f"<b>{Emoji.GEAR} Управление турнирами</b>\n\n"
            "Выберите статус для просмотра:",
            reply_markup=kb.admin_tournament_statuses(),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
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
    await _show_tournament_manage(callback, tournament_id)


@router.callback_query(F.data.regexp(r"^admin_t_quickstart_(\d+)$"))
async def callback_admin_quickstart(callback: CallbackQuery):
    """Быстрый старт турнира (открыть + опубликовать)."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    # 1. Открываем регистрацию
    await db.update_tournament_status(tournament_id, "open")
    await db.log_action(callback.from_user.id, "tournament_quickstart", f"ID: {tournament_id}")

    # 2. Публикуем в канал
    channel = await db.get_channel()
    if channel:
        from services.channel import init_channel_service
        channel_service = init_channel_service(callback.bot)
        success, msg = await channel_service.publish_post(tournament_id)
        if success:
            await callback.answer("Регистрация открыта и пост опубликован!", show_alert=True)
        else:
            await callback.answer(f"Регистрация открыта, но пост не опубликован: {msg}", show_alert=True)
    else:
        await callback.answer("Регистрация открыта! Канал не привязан - пост не опубликован.", show_alert=True)

    await _show_tournament_manage(callback, tournament_id)


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
    await _show_tournament_manage(callback, tournament_id)


@router.callback_query(F.data.regexp(r"^admin_t_close_(\d+)$"))
async def callback_admin_close_tournament(callback: CallbackQuery):
    """Закрыть регистрацию."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await db.update_tournament_status(tournament_id, "draft")
    await callback.answer("Регистрация закрыта!", show_alert=True)

    await _show_tournament_manage(callback, tournament_id)


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

    await _show_tournament_manage(callback, tournament_id)


@router.callback_query(F.data.regexp(r"^admin_t_start_(\d+)$"))
async def callback_admin_start_tournament(callback: CallbackQuery):
    """Начать турнир (ручная система матчей)."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)

    # Получаем участников
    if tournament["format"] == "1v1":
        if tournament["checkin_hours"] > 0:
            participants = await db.get_checked_in_players(tournament_id)
        else:
            participants = await db.get_tournament_players(tournament_id)
    else:
        if tournament["checkin_hours"] > 0:
            participants = await db.get_checked_in_teams(tournament_id)
        else:
            participants = await db.get_tournament_teams(tournament_id)

    if len(participants) < 2:
        await callback.answer("Недостаточно участников!", show_alert=True)
        return

    # Инициализируем статусы участников для ручной системы матчей
    await db.init_participant_statuses(tournament_id)

    await db.update_tournament_status(tournament_id, "active")
    await db.log_action(callback.from_user.id, "tournament_start", f"ID: {tournament_id}")

    # Отправляем уведомления участникам
    from services.notifications import NotificationService
    notification_service = NotificationService(callback.bot)
    await notification_service.notify_tournament_start(tournament_id)

    await callback.answer("Турнир начался! Используйте 'Управление матчами' для создания матчей.", show_alert=True)

    await _show_tournament_manage(callback, tournament_id)


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


@router.callback_query(F.data.regexp(r"^admin_t_finish_(\d+)$"))
async def callback_admin_finish_tournament(callback: CallbackQuery):
    """Завершить турнир вручную."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    if tournament["status"] != "active":
        await callback.answer("Турнир не активен!", show_alert=True)
        return

    # Проверяем, есть ли активные матчи
    active_matches = await db.get_active_matches_count(tournament_id)
    if active_matches > 0:
        await callback.answer(f"Нельзя завершить: {active_matches} матч(ей) ещё идёт!", show_alert=True)
        return

    # Получаем финальную статистику участников
    standings = await db.get_tournament_standings(tournament_id)

    # Сортируем: по победам (убыв), затем по поражениям (возр)
    sorted_standings = sorted(
        standings,
        key=lambda x: (-x.get("wins", 0), x.get("losses", 0))
    )

    # Получаем имена участников
    participants_names = {}
    for s in sorted_standings:
        if s["participant_type"] == "player":
            p = await db.get_player_by_id(s["participant_id"])
            participants_names[s["participant_id"]] = p["nickname"] if p else f"ID:{s['participant_id']}"
        else:
            t = await db.get_team(s["participant_id"])
            participants_names[s["participant_id"]] = t["name"] if t else f"ID:{s['participant_id']}"

    # Получаем призы турнира
    prizes = tournament.get("prizes", []) or []
    if isinstance(prizes, str):
        import json
        try:
            prizes = json.loads(prizes)
        except Exception:
            prizes = []

    # Конвертируем dict в list если нужно
    if isinstance(prizes, dict):
        # Призы могут быть {"1": "приз1", "2": "приз2"} - конвертируем в список
        prizes = [prizes.get(str(i + 1), "") for i in range(len(prizes))]

    # Обновляем статистику победителя (1 место)
    if sorted_standings:
        winner = sorted_standings[0]
        if winner["participant_type"] == "player":
            player = await db.get_player_by_id(winner["participant_id"])
            if player:
                await db.increment_player_stats(player["telegram_id"], won=True)
        else:
            team = await db.get_team(winner["participant_id"])
            if team:
                await db.update_team(team["id"], tournaments_won=team.get("tournaments_won", 0) + 1)

    # Обновляем статус турнира
    await db.update_tournament_status(tournament_id, "finished")
    await db.log_action(callback.from_user.id, "tournament_finish", f"ID: {tournament_id}")

    # Формируем текст результатов
    text = f"<b>🏆 ТУРНИР ЗАВЕРШЁН!</b>\n\n"
    text += f"<b>{escape_html(tournament['name'])}</b>\n"
    text += f"Формат: {tournament['format']}\n\n"

    # Медали для мест
    place_medals = ["🥇", "🥈", "🥉"]

    text += "<b>📊 РЕЗУЛЬТАТЫ:</b>\n\n"

    for i, s in enumerate(sorted_standings):
        pid = s["participant_id"]
        name = participants_names.get(pid, f"ID:{pid}")
        wins = s.get("wins", 0)
        losses = s.get("losses", 0)

        # Медаль или номер места
        if i < 3:
            place_icon = place_medals[i]
        else:
            place_icon = f"{i + 1}."

        # Приз для этого места
        prize_text = ""
        if i < len(prizes) and prizes[i]:
            prize_text = f" — <b>{prizes[i]}</b>"

        text += f"{place_icon} {escape_html(name)} ({wins}W/{losses}L){prize_text}\n"

    # Статистика турнира
    completed_matches = await db.get_tournament_matches(tournament_id)
    completed_count = len([m for m in completed_matches if m["status"] == "completed"])
    text += f"\n<b>Всего матчей:</b> {completed_count}"

    # Публикуем результаты в канал
    channel_result = ""
    try:
        from services.channel import get_channel_service
        channel_service = get_channel_service()
        if channel_service:
            success, msg = await channel_service.publish_results(tournament_id)
            channel_result = f"\n\n{Emoji.SEND} Канал: {msg}"
    except Exception as e:
        channel_result = f"\n\n{Emoji.WARNING} Канал: ошибка - {str(e)}"

    # Отправляем уведомления о местах всем участникам
    notifications_sent = 0
    notifications_failed = 0
    for i, s in enumerate(sorted_standings):
        place = i + 1
        pid = s["participant_id"]
        name = participants_names.get(pid, f"ID:{pid}")

        # Определяем иконку места
        if place == 1:
            place_text = "🥇 1 место"
        elif place == 2:
            place_text = "🥈 2 место"
        elif place == 3:
            place_text = "🥉 3 место"
        else:
            place_text = f"📍 {place} место"

        # Формируем сообщение
        notif_text = (
            f"<b>🏆 Турнир завершён!</b>\n\n"
            f"<b>{escape_html(tournament['name'])}</b>\n\n"
            f"Ваш результат: <b>{place_text}</b>\n"
            f"Побед: {s.get('wins', 0)} | Поражений: {s.get('losses', 0)}"
        )

        # Добавляем приз если есть
        if i < len(prizes) and prizes[i]:
            notif_text += f"\n\n🎁 <b>Приз:</b> {escape_html(prizes[i])}"

            # Добавляем контакты админов призов
            prize_admins = await db.get_prize_admins()
            if prize_admins:
                notif_text += f"\n\n📞 <b>Для получения приза:</b>\n"
                for admin in prize_admins:
                    notif_text += f"@{admin}\n"
                notif_text += "\n⚠️ <i>Не доверяйте другим контактам!</i>"

        # Отправляем уведомление
        try:
            if s["participant_type"] == "player":
                player = await db.get_player_by_id(pid)
                if player:
                    await callback.bot.send_message(
                        player["telegram_id"],
                        notif_text,
                        parse_mode="HTML"
                    )
                    notifications_sent += 1
            else:
                # Команда - отправляем всем членам
                team_members = await db.get_team_members(pid)
                for member in team_members:
                    try:
                        await callback.bot.send_message(
                            member["telegram_id"],
                            notif_text,
                            parse_mode="HTML"
                        )
                        notifications_sent += 1
                    except Exception:
                        notifications_failed += 1
        except Exception:
            notifications_failed += 1

    notif_result = f"\n{Emoji.BELL} Уведомлений: {notifications_sent} отправлено"
    if notifications_failed > 0:
        notif_result += f", {notifications_failed} не доставлено"

    await callback.message.edit_text(
        text + channel_result + notif_result,
        reply_markup=kb.back_button("admin_tournaments"),
        parse_mode="HTML"
    )
    await callback.answer("Турнир завершён!")


@router.callback_query(F.data.regexp(r"^admin_t_participants_(\d+)$"))
async def callback_admin_participants(callback: CallbackQuery):
    """Участники турнира (админ)."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

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
            # Формируем ссылку на профиль
            if p.get("username"):
                profile_link = f"<a href=\"https://t.me/{p['username']}\">{escape_html(p['nickname'])}</a>"
            else:
                profile_link = f"<a href=\"tg://user?id={p['telegram_id']}\">{escape_html(p['nickname'])}</a>"
            text += f"{i}. {profile_link} {check}\n"
        text += f"\n<b>Всего:</b> {len(players)}/{tournament['max_participants']}"
    else:
        teams = await db.get_tournament_teams(tournament_id)
        for i, t in enumerate(teams, 1):
            check = Emoji.CHECK if t.get("checked_in") else ""
            text += f"{i}. {escape_html(t['name'])} {check}\n"
        text += f"\n<b>Всего:</b> {len(teams)}/{tournament['max_participants']}"

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button(f"admin_t_manage_{tournament_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== СОЗДАНИЕ ТУРНИРА ====================

@router.callback_query(F.data == "admin_create_tournament")
async def callback_admin_create_tournament(callback: CallbackQuery, state: FSMContext):
    """Меню создания турнира."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"Выберите способ создания:",
        reply_markup=kb.create_tournament_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "t_create")
async def callback_t_create(callback: CallbackQuery, state: FSMContext):
    """Возврат к меню создания турнира."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"Выберите способ создания:",
        reply_markup=kb.create_tournament_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "t_create_new")
async def callback_t_create_new(callback: CallbackQuery, state: FSMContext):
    """Создание нового турнира с нуля."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await state.update_data(maps=[])

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 1:</b> Введите название турнира:",
        reply_markup=kb.back_button("t_create"),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_name)
    await callback.answer()


@router.callback_query(F.data == "t_create_from_prev")
async def callback_t_create_from_prev(callback: CallbackQuery):
    """Список прошлых турниров для дублирования."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    # Получаем последние турниры
    tournaments = await db.get_recent_tournaments(limit=10)

    if not tournaments:
        await callback.answer("Нет прошлых турниров!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.REFRESH} Создать на основе</b>\n\n"
        f"Выберите турнир для копирования:",
        reply_markup=kb.prev_tournaments_list(tournaments),
        parse_mode="HTML"
    )
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


@router.callback_query(F.data == "t_map_custom", CreateTournamentStates.waiting_maps)
async def process_map_custom(callback: CallbackQuery, state: FSMContext):
    """Запросить ввод своей карты."""
    await callback.message.edit_text(
        f"<b>{Emoji.PENCIL} Своя карта</b>\n\n"
        f"Введите название карты (например: de_dust2 или workshop_map):",
        reply_markup=kb.back_button("admin_create_tournament"),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_custom_map)
    await callback.answer()


@router.message(CreateTournamentStates.waiting_custom_map)
async def process_custom_map_input(message: Message, state: FSMContext):
    """Обработка ввода своей карты."""
    custom_map = message.text.strip()

    if len(custom_map) < 2:
        await message.answer(
            f"{Emoji.CROSS} Название карты слишком короткое!",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    maps = data.get("maps", [])

    if custom_map not in maps:
        maps.append(custom_map)

    await state.update_data(maps=maps)
    await state.set_state(CreateTournamentStates.waiting_maps)

    await message.answer(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 3:</b> Выберите карты (можно несколько):\n"
        f"Выбрано: {len(maps)}\n"
        f"Добавлена: {custom_map}",
        reply_markup=kb.maps_select(maps),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("t_map_"), CreateTournamentStates.waiting_maps)
async def process_map_toggle(callback: CallbackQuery, state: FSMContext):
    """Переключение карты."""
    map_name = callback.data.replace("t_map_", "")

    # Пропускаем callback для custom (обрабатывается отдельно)
    if map_name == "custom":
        return

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

    data = await state.get_data()
    tournament_format = data.get("format", "1v1")
    participant_label = "команд" if tournament_format != "1v1" else "участников"

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"<b>Шаг 4:</b> Введите количество {participant_label} (от 2 до 128):",
        reply_markup=kb.back_button("admin_create_tournament"),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_custom_participants)
    await callback.answer()


@router.message(CreateTournamentStates.waiting_custom_participants)
async def process_custom_participants(message: Message, state: FSMContext):
    """Ввод своего количества участников."""
    try:
        num = int(message.text.strip())
        if num < 2 or num > 128:
            raise ValueError()
    except ValueError:
        await message.answer(
            f"{Emoji.CROSS} Введите число от 2 до 128.",
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

    # Проверяем что это не выбор количества мест
    if prize_type.startswith("places_"):
        return

    await state.update_data(prize_type=prize_type, prize_amount=0, prizes={})

    if prize_type == "none":
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
        # Выбор количества призовых мест
        prize_name = config.PRIZE_TYPES[prize_type]
        await callback.message.edit_text(
            f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
            f"Тип приза: <b>{prize_name}</b>\n\n"
            f"Сколько призовых мест?",
            reply_markup=kb.prize_places_select(),
            parse_mode="HTML"
        )
        await state.set_state(CreateTournamentStates.waiting_prize_places)
    await callback.answer()


@router.callback_query(F.data.startswith("t_prize_places_"), CreateTournamentStates.waiting_prize_places)
async def process_prize_places(callback: CallbackQuery, state: FSMContext):
    """Выбор количества призовых мест."""
    places = int(callback.data.replace("t_prize_places_", ""))
    data = await state.get_data()
    prize_type = data.get("prize_type")

    await state.update_data(prize_places=places)

    # Определяем название единицы измерения
    unit_hint = ""
    if prize_type == "stars":
        unit_hint = " (например: 50)"
    elif prize_type == "rub":
        unit_hint = " (например: 500)"
    elif prize_type == "skins":
        unit_hint = " (например: AWP Asiimov)"
    elif prize_type == "custom":
        unit_hint = " (например: Premium подписка)"

    await callback.message.edit_text(
        f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
        f"🥇 <b>Приз за 1 место:</b>\n"
        f"Введите приз{unit_hint}:",
        reply_markup=kb.back_button("admin_create_tournament"),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_prize_1)
    await callback.answer()


@router.message(CreateTournamentStates.waiting_prize_1)
async def process_prize_1(message: Message, state: FSMContext):
    """Ввод приза за 1 место."""
    data = await state.get_data()
    prizes = data.get("prizes", {})
    prizes["1"] = message.text.strip()
    await state.update_data(prizes=prizes)

    places = data.get("prize_places", 1)

    if places >= 2:
        await message.answer(
            f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
            f"🥈 <b>Приз за 2 место:</b>\n"
            f"Введите приз:",
            reply_markup=kb.back_button("admin_create_tournament"),
            parse_mode="HTML"
        )
        await state.set_state(CreateTournamentStates.waiting_prize_2)
    else:
        # Переходим к выбору даты
        now = datetime.now()
        await message.answer(
            f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
            f"<b>Шаг 6:</b> Выберите дату старта:",
            reply_markup=kb.calendar(now.year, now.month),
            parse_mode="HTML"
        )
        await state.set_state(CreateTournamentStates.waiting_date)


@router.message(CreateTournamentStates.waiting_prize_2)
async def process_prize_2(message: Message, state: FSMContext):
    """Ввод приза за 2 место."""
    data = await state.get_data()
    prizes = data.get("prizes", {})
    prizes["2"] = message.text.strip()
    await state.update_data(prizes=prizes)

    places = data.get("prize_places", 2)

    if places >= 3:
        await message.answer(
            f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
            f"🥉 <b>Приз за 3 место:</b>\n"
            f"Введите приз:",
            reply_markup=kb.back_button("admin_create_tournament"),
            parse_mode="HTML"
        )
        await state.set_state(CreateTournamentStates.waiting_prize_3)
    else:
        # Переходим к выбору даты
        now = datetime.now()
        await message.answer(
            f"<b>{Emoji.PLUS} Создание турнира</b>\n\n"
            f"<b>Шаг 6:</b> Выберите дату старта:",
            reply_markup=kb.calendar(now.year, now.month),
            parse_mode="HTML"
        )
        await state.set_state(CreateTournamentStates.waiting_date)


@router.message(CreateTournamentStates.waiting_prize_3)
async def process_prize_3(message: Message, state: FSMContext):
    """Ввод приза за 3 место."""
    data = await state.get_data()
    prizes = data.get("prizes", {})
    prizes["3"] = message.text.strip()
    await state.update_data(prizes=prizes)

    # Переходим к выбору даты
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

    # Переходим к выбору взноса
    text = (
        f"<b>{Emoji.STAR} Взнос за участие</b>\n\n"
        f"Укажите сумму взноса в Telegram Stars.\n"
        f"Выберите вариант или введите свою сумму.\n\n"
        f"<i>0 = бесплатное участие</i>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.entry_fee_select(),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_entry_fee)
    await callback.answer()


@router.callback_query(F.data.startswith("t_fee_"), CreateTournamentStates.waiting_entry_fee)
async def process_entry_fee_select(callback: CallbackQuery, state: FSMContext):
    """Выбор взноса из готовых вариантов."""
    fee_value = callback.data.replace("t_fee_", "")

    if fee_value == "custom":
        await callback.message.edit_text(
            f"<b>{Emoji.STAR} Введите сумму взноса</b>\n\n"
            f"Укажите число (количество Stars):",
            reply_markup=kb.back_button("admin_create_tournament"),
            parse_mode="HTML"
        )
        return

    entry_fee = int(fee_value)
    await state.update_data(entry_fee=entry_fee)
    await _show_tournament_confirm(callback, state)


@router.message(CreateTournamentStates.waiting_entry_fee)
async def process_entry_fee_input(message: Message, state: FSMContext):
    """Ввод произвольной суммы взноса."""
    try:
        entry_fee = int(message.text.strip())
        if entry_fee < 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            f"{Emoji.WARNING} Введите положительное число!",
            reply_markup=kb.back_button("admin_create_tournament"),
            parse_mode="HTML"
        )
        return

    await state.update_data(entry_fee=entry_fee)

    # Показываем подтверждение (нужно создать новое сообщение)
    data = await state.get_data()
    text, markup = await _get_confirm_content(data)

    await message.answer(text, reply_markup=markup, parse_mode="HTML")
    await state.set_state(CreateTournamentStates.confirm)


async def _show_tournament_confirm(callback: CallbackQuery, state: FSMContext):
    """Показать экран подтверждения создания турнира."""
    data = await state.get_data()
    text, markup = await _get_confirm_content(data)

    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await state.set_state(CreateTournamentStates.confirm)
    await callback.answer()


async def _get_confirm_content(data: dict) -> tuple[str, any]:
    """Получить текст и клавиатуру для подтверждения."""
    format_name = config.TOURNAMENT_FORMATS[data["format"]]["name"]
    maps_text = ", ".join(m.replace("de_", "") for m in data["maps"])

    # Формируем текст призов
    prize_text = "Без приза"
    prizes = data.get("prizes", {})
    if data["prize_type"] != "none" and prizes:
        prize_lines = []
        for place, prize in sorted(prizes.items(), key=lambda x: int(x[0])):
            emoji = config.PRIZE_PLACES.get(int(place), f"{place}.")
            prize_lines.append(f"{emoji} {prize}")
        prize_text = "\n".join(prize_lines)

    checkin_text = "Без check-in" if data.get("checkin_hours", 0) == 0 else f"За {data['checkin_hours']} ч."
    entry_fee = data.get("entry_fee", 0)
    fee_text = "Бесплатно" if entry_fee == 0 else f"{entry_fee} ⭐"

    text = (
        f"<b>{Emoji.CHECK} Подтверждение создания</b>\n\n"
        f"{Emoji.TROPHY} <b>Название:</b> {escape_html(data['name'])}\n"
        f"{Emoji.GAME} <b>Формат:</b> {format_name}\n"
        f"{Emoji.MAP} <b>Карты:</b> {maps_text}\n"
        f"{Emoji.PEOPLE} <b>Участников:</b> {data['max_participants']}\n"
        f"{Emoji.GIFT} <b>Призы:</b>\n{prize_text}\n"
        f"{Emoji.CALENDAR} <b>Старт:</b> {format_datetime(data['start_time'])}\n"
        f"{Emoji.BELL} <b>Check-in:</b> {checkin_text}\n"
        f"{Emoji.STAR} <b>Взнос:</b> {fee_text}\n"
    )

    return text, kb.tournament_confirm(data)


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
        prize_amount=data.get("prize_amount", 0),
        start_time=data["start_time"],
        registration_deadline=registration_deadline,
        checkin_hours=data["checkin_hours"],
        created_by=player["id"] if player else callback.from_user.id,
        prizes=data.get("prizes"),
        entry_fee=data.get("entry_fee", 0)
    )

    await db.log_action(callback.from_user.id, "tournament_create", f"ID: {tournament_id}")

    tournament = await db.get_tournament(tournament_id)
    participant_count = 0
    text = format_tournament_info(tournament, participant_count)
    text = f"{Emoji.CHECK} <b>Турнир создан!</b>\n\n" + text

    await callback.message.edit_text(
        text,
        reply_markup=kb.tournament_created_menu(tournament_id),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ШАБЛОНЫ ====================

@router.callback_query(F.data.in_({"admin_from_template", "templates_list"}))
async def callback_admin_from_template(callback: CallbackQuery):
    """Создание из шаблона."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    templates = await db.get_all_templates()

    text = f"<b>{Emoji.STAR} Шаблоны турниров</b>\n\n"
    if templates:
        text += f"Пользовательских шаблонов: {len(templates)}\n"
    text += "Выберите шаблон для создания турнира:"

    await callback.message.edit_text(
        text,
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
async def callback_admin_broadcast(callback: CallbackQuery):
    """Меню рассылки участникам турнира."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    participant_count = await db.get_tournament_participant_count(tournament_id)

    await callback.message.edit_text(
        f"<b>{Emoji.SEND} Рассылка участникам</b>\n\n"
        f"<b>Турнир:</b> {tournament['name']}\n"
        f"<b>Участников:</b> {participant_count}\n\n"
        f"Выберите тип рассылки:",
        reply_markup=kb.broadcast_menu(tournament_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^broadcast_announce_(\d+)$"))
async def callback_broadcast_announce(callback: CallbackQuery, state: FSMContext):
    """Объявление - ввод текста."""
    tournament_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(broadcast_tournament_id=tournament_id, broadcast_type="announce")

    await callback.message.edit_text(
        f"<b>{Emoji.BELL} Объявление</b>\n\n"
        f"Введите текст объявления:",
        reply_markup=kb.back_button(f"admin_t_broadcast_{tournament_id}"),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_message)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^broadcast_match_(\d+)$"))
async def callback_broadcast_match(callback: CallbackQuery):
    """Отправить ссылки на матчи участникам."""
    tournament_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if tournament["status"] != "active":
        await callback.answer("Турнир не активен!", show_alert=True)
        return

    # Получаем активные матчи
    matches = await db.get_tournament_matches(tournament_id)
    active_matches = [m for m in matches if m["status"] == "pending"]

    if not active_matches:
        await callback.answer("Нет активных матчей!", show_alert=True)
        return

    sent = 0
    bot = callback.bot

    for match in active_matches:
        # Отправляем обоим участникам
        participants = []
        if tournament["format"] == "1v1":
            if match.get("player1_id"):
                p1 = await db.get_player_by_id(match["player1_id"])
                if p1:
                    participants.append(p1["telegram_id"])
            if match.get("player2_id"):
                p2 = await db.get_player_by_id(match["player2_id"])
                if p2:
                    participants.append(p2["telegram_id"])
        else:
            if match.get("team1_id"):
                members1 = await db.get_team_members(match["team1_id"])
                participants.extend([m["telegram_id"] for m in members1])
            if match.get("team2_id"):
                members2 = await db.get_team_members(match["team2_id"])
                participants.extend([m["telegram_id"] for m in members2])

        for tid in participants:
            try:
                await bot.send_message(
                    tid,
                    f"<b>{Emoji.GAME} Ваш матч готов!</b>\n\n"
                    f"<b>Турнир:</b> {tournament['name']}\n"
                    f"<b>Раунд:</b> {match['round']}\n\n"
                    f"Свяжитесь с соперником и начните игру!",
                    parse_mode="HTML"
                )
                sent += 1
            except Exception:
                pass

    await callback.answer(f"Уведомления отправлены: {sent}", show_alert=True)
    await _show_tournament_manage(callback, tournament_id)


@router.callback_query(F.data.regexp(r"^broadcast_checkin_(\d+)$"))
async def callback_broadcast_checkin(callback: CallbackQuery):
    """Напоминание о check-in."""
    tournament_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)

    # Получаем участников без check-in
    recipients = []
    if tournament["format"] == "1v1":
        players = await db.get_tournament_players(tournament_id)
        recipients = [p["telegram_id"] for p in players if not p.get("checked_in")]
    else:
        teams = await db.get_tournament_teams(tournament_id)
        for team in teams:
            if not team.get("checked_in"):
                members = await db.get_team_members(team["id"])
                recipients.extend([m["telegram_id"] for m in members])

    if not recipients:
        await callback.answer("Все участники уже прошли check-in!", show_alert=True)
        return

    sent = 0
    bot = callback.bot

    for tid in recipients:
        try:
            await bot.send_message(
                tid,
                f"<b>{Emoji.CLOCK} Напоминание о Check-in!</b>\n\n"
                f"<b>Турнир:</b> {tournament['name']}\n\n"
                f"Пройдите check-in, чтобы подтвердить участие!",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            pass

    await callback.answer(f"Напоминания отправлены: {sent}/{len(recipients)}", show_alert=True)
    await _show_tournament_manage(callback, tournament_id)


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

@router.callback_query(F.data.regexp(r"^admin_t_preview_(\d+)$"))
async def callback_admin_preview(callback: CallbackQuery):
    """Превью поста о турнире."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    from services.channel import init_channel_service
    channel_service = init_channel_service(callback.bot)

    participant_count = await db.get_tournament_participant_count(tournament_id)
    bot_username = await channel_service.get_bot_username()
    text = channel_service.generate_post_text(tournament, participant_count, bot_username)

    await callback.message.edit_text(
        f"<b>{Emoji.SEARCH} Превью поста</b>\n"
        f"<i>Так будет выглядеть пост в канале:</i>\n\n"
        f"{'─' * 30}\n\n"
        f"{text}\n\n"
        f"{'─' * 30}",
        reply_markup=kb.confirm_cancel(
            f"admin_t_publish_{tournament_id}",
            f"admin_t_manage_{tournament_id}"
        ),
        parse_mode="HTML"
    )
    await callback.answer()


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

    # Возвращаемся к управлению турниром
    await _show_tournament_manage(callback, tournament_id)


# ==================== ДУБЛИРОВАНИЕ ТУРНИРА ====================

@router.callback_query(F.data.regexp(r"^admin_t_duplicate_(\d+)$"))
async def callback_admin_duplicate(callback: CallbackQuery, state: FSMContext):
    """Дублирование турнира."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    # Заполняем данные из турнира
    await state.update_data(
        name=f"{tournament['name']} (копия)",
        format=tournament["format"],
        maps=tournament["maps"],
        max_participants=tournament["max_participants"],
        prize_type=tournament["prize_type"],
        prize_amount=tournament.get("prize_amount", 0),
        prizes=tournament.get("prizes", {}),
        checkin_hours=tournament["checkin_hours"]
    )

    # Показываем календарь для выбора даты
    now = datetime.now()
    await callback.message.edit_text(
        f"<b>{Emoji.REFRESH} Дублирование турнира</b>\n\n"
        f"Турнир: <b>{escape_html(tournament['name'])}</b>\n\n"
        f"Выберите новую дату старта:",
        reply_markup=kb.calendar(now.year, now.month),
        parse_mode="HTML"
    )
    await state.set_state(CreateTournamentStates.waiting_date)
    await callback.answer()


# ==================== УДАЛЕНИЕ ТУРНИРА ====================

@router.callback_query(F.data.regexp(r"^admin_t_delete_(\d+)$"))
async def callback_admin_delete(callback: CallbackQuery):
    """Удаление турнира (подтверждение)."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.WARNING} Удаление турнира</b>\n\n"
        f"Вы уверены, что хотите удалить турнир\n"
        f"<b>{escape_html(tournament['name'])}</b>?\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=kb.confirm_cancel(
            f"admin_t_dodelete_{tournament_id}",
            f"admin_t_manage_{tournament_id}"
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_t_dodelete_(\d+)$"))
async def callback_admin_dodelete(callback: CallbackQuery):
    """Подтверждение удаления турнира."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    # Удаляем пост из канала если есть
    post = await db.get_tournament_post(tournament_id)
    if post:
        from services.channel import init_channel_service
        channel_service = init_channel_service(callback.bot)
        await channel_service.delete_post(tournament_id)

    # Удаляем турнир (каскадно удалятся регистрации и матчи)
    await db.conn.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
    await db.conn.commit()
    await db.log_action(callback.from_user.id, "tournament_delete", f"ID: {tournament_id}")

    await callback.answer("Турнир удалён!", show_alert=True)
    await callback.message.edit_text(
        f"{Emoji.CHECK} Турнир удалён.",
        reply_markup=kb.back_button("admin_tournaments"),
        parse_mode="HTML"
    )


# ==================== РЕДАКТИРОВАНИЕ ТУРНИРА ====================

@router.callback_query(F.data.regexp(r"^admin_t_edit_(\d+)$"))
async def callback_admin_edit(callback: CallbackQuery):
    """Меню редактирования турнира."""
    tournament_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.PENCIL} Редактирование турнира</b>\n\n"
        f"Турнир: <b>{escape_html(tournament['name'])}</b>\n\n"
        f"Выберите что изменить:",
        reply_markup=kb.tournament_edit_menu(tournament_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_t_edit_name_(\d+)$"))
async def callback_admin_edit_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия турнира."""
    tournament_id = int(callback.data.split("_")[4])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(edit_tournament_id=tournament_id)

    await callback.message.edit_text(
        f"<b>{Emoji.PENCIL} Изменение названия</b>\n\n"
        f"Введите новое название турнира:",
        reply_markup=kb.back_button(f"admin_t_edit_{tournament_id}"),
        parse_mode="HTML"
    )
    await state.set_state(EditTournamentStates.waiting_name)
    await callback.answer()


@router.message(EditTournamentStates.waiting_name)
async def process_edit_name(message: Message, state: FSMContext):
    """Обработка изменения названия."""
    data = await state.get_data()
    tournament_id = data.get("edit_tournament_id")
    await state.clear()

    name = message.text.strip()
    if len(name) < 3 or len(name) > 64:
        await message.answer(
            f"{Emoji.CROSS} Название должно быть от 3 до 64 символов.",
            reply_markup=kb.back_button(f"admin_t_edit_{tournament_id}"),
            parse_mode="HTML"
        )
        return

    await db.update_tournament(tournament_id, name=name)
    await db.log_action(message.from_user.id, "tournament_edit_name", f"ID: {tournament_id}")

    await message.answer(
        f"{Emoji.CHECK} Название изменено на <b>{escape_html(name)}</b>!",
        reply_markup=kb.back_button(f"admin_t_manage_{tournament_id}"),
        parse_mode="HTML"
    )


# ==================== СТАТИСТИКА ====================

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Расширенная статистика в админке."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    stats = await db.get_extended_stats()

    text = (
        f"<b>{Emoji.CHART} Статистика</b>\n\n"
        f"<b>⭐ Telegram Stars:</b>\n"
        f"• Всего заработано: <b>{stats.get('stars_total', 0)} ⭐</b>\n"
        f"• За сегодня: +{stats.get('stars_today', 0)} ⭐\n"
        f"• За неделю: +{stats.get('stars_week', 0)} ⭐\n"
        f"• За месяц: +{stats.get('stars_month', 0)} ⭐\n"
        f"• Платных турниров: {stats.get('paid_tournaments', 0)}\n\n"
        f"<b>{Emoji.PEOPLE} Игроки:</b>\n"
        f"• Всего: {stats['total_players']}\n"
        f"• За сегодня: +{stats.get('players_today', 0)}\n"
        f"• За неделю: +{stats.get('players_week', 0)}\n"
        f"• За месяц: +{stats.get('players_month', 0)}\n\n"
        f"<b>{Emoji.TROPHY} Команды:</b> {stats['total_teams']}\n\n"
        f"<b>{Emoji.GAME} Турниры:</b>\n"
        f"• Всего: {stats['total_tournaments']}\n"
        f"• Активных: {stats['active_tournaments']}\n"
        f"• Завершённых: {stats['finished_tournaments']}\n"
        f"• За неделю: {stats.get('tournaments_week', 0)}\n\n"
        f"<b>{Emoji.CROSS} Баны:</b> {stats.get('active_bans', 0)} активных\n\n"
    )

    # Топ игроков
    top_players = stats.get("top_players", [])
    if top_players:
        text += f"<b>{Emoji.STAR} Топ-5 игроков:</b>\n"
        for i, p in enumerate(top_players, 1):
            winrate = (p['wins'] / (p['wins'] + p['losses']) * 100) if (p['wins'] + p['losses']) > 0 else 0
            text += f"{i}. {escape_html(p['nickname'])} — {p['wins']}W ({winrate:.0f}%)\n"

    await callback.message.edit_text(
        text,
        reply_markup=kb.back_button("admin"),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== В ЧЕРНОВИК ====================

@router.callback_query(F.data.regexp(r"^admin_t_to_draft_(\d+)$"))
async def callback_admin_to_draft(callback: CallbackQuery):
    """Поместить турнир в черновик."""
    tournament_id = int(callback.data.split("_")[4])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await db.update_tournament_status(tournament_id, "draft")
    await callback.answer("Турнир помещён в черновик!", show_alert=True)

    await _show_tournament_manage(callback, tournament_id)


# ==================== БАНЫ ====================

@router.callback_query(F.data.regexp(r"^admin_player_ban_(\d+)$"))
async def callback_admin_player_ban(callback: CallbackQuery):
    """Начало бана игрока - выбор срока."""
    player_telegram_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    player = await db.get_player(player_telegram_id)
    if not player:
        await callback.answer("Игрок не найден!", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{Emoji.LOCK} Бан игрока</b>\n\n"
        f"<b>Игрок:</b> {escape_html(player['nickname'])}\n\n"
        f"Выберите срок бана:",
        reply_markup=kb.ban_duration_menu(player["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^ban_duration_(\d+)_(.+)$"))
async def callback_ban_duration(callback: CallbackQuery):
    """Применение бана с выбранным сроком."""
    parts = callback.data.split("_")
    player_id = int(parts[2])
    duration = parts[3]

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    if duration == "perm":
        await db.ban_player(player_id, callback.from_user.id, "Бан администратором", is_permanent=True)
        msg = "Игрок забанен навсегда!"
    else:
        days = int(duration)
        await db.ban_player(player_id, callback.from_user.id, "Бан администратором", days=days)
        msg = f"Игрок забанен на {days} дней!"

    await db.log_action(callback.from_user.id, "player_ban", f"Player ID: {player_id}, Duration: {duration}")

    await callback.answer(msg, show_alert=True)
    await callback.message.edit_text(
        f"{Emoji.CHECK} {msg}",
        reply_markup=kb.back_button("admin_players"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^admin_player_unban_(\d+)$"))
async def callback_admin_player_unban(callback: CallbackQuery):
    """Разбан игрока."""
    player_telegram_id = int(callback.data.split("_")[3])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    player = await db.get_player(player_telegram_id)
    if not player:
        await callback.answer("Игрок не найден!", show_alert=True)
        return

    await db.unban_player(player["id"])
    await db.log_action(callback.from_user.id, "player_unban", f"Player ID: {player['id']}")

    await callback.answer("Игрок разбанен!", show_alert=True)
    await callback.message.edit_text(
        f"{Emoji.CHECK} Игрок {escape_html(player['nickname'])} разбанен!",
        reply_markup=kb.back_button("admin_players"),
        parse_mode="HTML"
    )


# ==================== РЕДАКТИРОВАНИЕ ТУРНИРА ====================

@router.callback_query(F.data.regexp(r"^admin_t_edit_date_(\d+)$"))
async def callback_admin_edit_date(callback: CallbackQuery, state: FSMContext):
    """Редактирование даты турнира."""
    tournament_id = int(callback.data.split("_")[4])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(edit_tournament_id=tournament_id)
    await state.set_state(EditTournamentStates.waiting_date)

    now = datetime.now()
    await callback.message.edit_text(
        f"{Emoji.CALENDAR} <b>Выберите новую дату:</b>",
        reply_markup=kb.calendar(now.year, now.month, back_callback=f"admin_t_edit_{tournament_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("calendar_day_"), EditTournamentStates.waiting_date)
async def callback_edit_calendar_day(callback: CallbackQuery, state: FSMContext):
    """Выбор дня для редактирования."""
    # Парсим дату из формата calendar_day_YYYY_MM_DD
    parts = callback.data.split("_")
    year = int(parts[2])
    month = int(parts[3])
    day = int(parts[4])
    selected_date = datetime(year, month, day)

    await state.update_data(edit_date=selected_date)
    await state.set_state(EditTournamentStates.waiting_time)

    await callback.message.edit_text(
        f"{Emoji.CLOCK} <b>Выберите время:</b>",
        reply_markup=kb.time_select(selected_date),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("t_time_"), EditTournamentStates.waiting_time)
async def callback_edit_time(callback: CallbackQuery, state: FSMContext):
    """Выбор времени для редактирования."""
    # Парсим из формата t_time_YYYY-MM-DD_HH:MM
    parts = callback.data.split("_")
    # parts = ["t", "time", "YYYY-MM-DD", "HH:MM"]
    time_str = parts[3]  # "HH:MM"
    hour, minute = map(int, time_str.split(":"))

    data = await state.get_data()
    selected_date = data["edit_date"]
    tournament_id = data["edit_tournament_id"]

    new_start_time = datetime(
        selected_date.year, selected_date.month, selected_date.day,
        hour, minute
    )

    await db.update_tournament(tournament_id, start_time=new_start_time)
    await db.log_action(callback.from_user.id, "tournament_edit", f"Changed date to {new_start_time}")

    await state.clear()
    await callback.answer("Дата обновлена!", show_alert=True)
    await _show_tournament_manage(callback, tournament_id)


@router.callback_query(F.data.regexp(r"^admin_t_edit_maps_(\d+)$"))
async def callback_admin_edit_maps(callback: CallbackQuery, state: FSMContext):
    """Редактирование карт турнира."""
    tournament_id = int(callback.data.split("_")[4])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    await state.update_data(
        edit_tournament_id=tournament_id,
        selected_maps=tournament.get("maps", [])
    )

    await callback.message.edit_text(
        f"{Emoji.MAP} <b>Выберите карты:</b>\n\nТекущие: {', '.join(tournament.get('maps', []))}",
        reply_markup=kb.map_select(tournament.get("maps", []), tournament_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("t_map_"))
async def callback_edit_map_toggle(callback: CallbackQuery, state: FSMContext):
    """Переключение карты при редактировании."""
    # Пропускаем callback для своей карты (обрабатывается отдельно)
    if callback.data.startswith("t_map_custom_edit_"):
        return

    data = await state.get_data()
    if "edit_tournament_id" not in data:
        # Это может быть создание турнира, пропускаем
        return

    map_name = callback.data.replace("t_map_", "")
    selected = data.get("selected_maps", [])

    if map_name in selected:
        selected.remove(map_name)
    else:
        selected.append(map_name)

    await state.update_data(selected_maps=selected)

    tournament_id = data["edit_tournament_id"]
    await callback.message.edit_text(
        f"{Emoji.MAP} <b>Выберите карты:</b>\n\nВыбрано: {', '.join(selected) if selected else 'нет'}",
        reply_markup=kb.map_select(selected, tournament_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "t_maps_save")
async def callback_maps_save(callback: CallbackQuery, state: FSMContext):
    """Сохранение выбранных карт при редактировании."""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    data = await state.get_data()
    tournament_id = data.get("edit_tournament_id")
    selected_maps = data.get("selected_maps", [])

    if not tournament_id:
        await callback.answer("Ошибка: турнир не найден!", show_alert=True)
        return

    if not selected_maps:
        await callback.answer("Выберите хотя бы одну карту!", show_alert=True)
        return

    await db.update_tournament(tournament_id, maps=selected_maps)
    await state.clear()
    await callback.answer("Карты сохранены!", show_alert=True)
    await _show_tournament_manage(callback, tournament_id)


@router.callback_query(F.data == "t_maps_done")
async def callback_edit_maps_done(callback: CallbackQuery, state: FSMContext):
    """Завершение редактирования карт."""
    data = await state.get_data()
    if "edit_tournament_id" not in data:
        return

    tournament_id = data["edit_tournament_id"]
    selected_maps = data.get("selected_maps", [])

    if not selected_maps:
        await callback.answer("Выберите хотя бы одну карту!", show_alert=True)
        return

    await db.update_tournament(tournament_id, maps=selected_maps)
    await db.log_action(callback.from_user.id, "tournament_edit", f"Changed maps to {selected_maps}")

    await state.clear()
    await callback.answer("Карты обновлены!", show_alert=True)
    await _show_tournament_manage(callback, tournament_id)


@router.callback_query(F.data.regexp(r"^t_map_custom_edit_(\d+)$"))
async def callback_edit_map_custom(callback: CallbackQuery, state: FSMContext):
    """Запросить ввод своей карты при редактировании."""
    tournament_id = int(callback.data.split("_")[-1])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(edit_tournament_id=tournament_id)
    await callback.message.edit_text(
        f"<b>{Emoji.PENCIL} Своя карта</b>\n\n"
        f"Введите название карты (например: de_dust2 или workshop_map):",
        reply_markup=kb.back_button(f"admin_t_edit_maps_{tournament_id}"),
        parse_mode="HTML"
    )
    await state.set_state(EditTournamentStates.waiting_custom_map)
    await callback.answer()


@router.message(EditTournamentStates.waiting_custom_map)
async def process_edit_custom_map_input(message: Message, state: FSMContext):
    """Обработка ввода своей карты при редактировании."""
    custom_map = message.text.strip()

    if len(custom_map) < 2:
        await message.answer(
            f"{Emoji.CROSS} Название карты слишком короткое!",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    tournament_id = data.get("edit_tournament_id")
    selected_maps = data.get("selected_maps", [])

    if custom_map not in selected_maps:
        selected_maps.append(custom_map)

    await state.update_data(selected_maps=selected_maps)
    await state.set_state(None)  # Сбрасываем состояние

    await message.answer(
        f"{Emoji.MAP} <b>Выберите карты:</b>\n\n"
        f"Выбрано: {', '.join(selected_maps) if selected_maps else 'нет'}\n"
        f"Добавлена: {custom_map}",
        reply_markup=kb.map_select(selected_maps, tournament_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^admin_t_edit_participants_(\d+)$"))
async def callback_admin_edit_participants(callback: CallbackQuery, state: FSMContext):
    """Редактирование количества участников."""
    tournament_id = int(callback.data.split("_")[4])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    await state.update_data(edit_tournament_id=tournament_id)
    await state.set_state(EditTournamentStates.waiting_participants)

    participant_label = "команд" if tournament["format"] != "1v1" else "участников"

    await callback.message.edit_text(
        f"{Emoji.PEOPLE} <b>Введите новое количество {participant_label}:</b>\n\n"
        f"Текущее: {tournament['max_participants']}\n"
        f"(от 2 до 128)",
        reply_markup=kb.back_button(f"admin_t_edit_{tournament_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditTournamentStates.waiting_participants)
async def process_edit_participants(message: Message, state: FSMContext):
    """Обработка нового количества участников."""
    try:
        count = int(message.text.strip())
        if count < 2 or count > 128:
            await message.answer("Введите число от 2 до 128!")
            return
    except ValueError:
        await message.answer("Введите корректное число!")
        return

    data = await state.get_data()
    tournament_id = data["edit_tournament_id"]

    await db.update_tournament(tournament_id, max_participants=count)
    await db.log_action(message.from_user.id, "tournament_edit", f"Changed max_participants to {count}")

    await state.clear()

    tournament = await db.get_tournament(tournament_id)
    participant_count = await db.get_tournament_participant_count(tournament_id)
    text = format_tournament_info(tournament, participant_count)

    await message.answer(
        f"{Emoji.CHECK} Количество участников обновлено!\n\n{text}",
        reply_markup=kb.admin_tournament_manage(tournament),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^admin_t_edit_prizes_(\d+)$"))
async def callback_admin_edit_prizes(callback: CallbackQuery, state: FSMContext):
    """Редактирование призов турнира."""
    tournament_id = int(callback.data.split("_")[4])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(edit_tournament_id=tournament_id, edit_prizes={})
    await state.set_state(EditTournamentStates.waiting_prize_1)

    await callback.message.edit_text(
        f"{Emoji.GIFT} <b>Введите приз за 1 место:</b>\n\n"
        f"Например: 5000₽, скины, 100 Stars",
        reply_markup=kb.back_button(f"admin_t_edit_{tournament_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditTournamentStates.waiting_prize_1)
async def process_edit_prize_1(message: Message, state: FSMContext):
    """Приз за 1 место."""
    data = await state.get_data()
    prizes = data.get("edit_prizes", {})
    prizes["1"] = message.text.strip()
    await state.update_data(edit_prizes=prizes)
    await state.set_state(EditTournamentStates.waiting_prize_2)

    await message.answer(
        f"{Emoji.GIFT} <b>Введите приз за 2 место</b> (или отправьте '-' чтобы пропустить):",
        parse_mode="HTML"
    )


@router.message(EditTournamentStates.waiting_prize_2)
async def process_edit_prize_2(message: Message, state: FSMContext):
    """Приз за 2 место."""
    data = await state.get_data()
    prizes = data.get("edit_prizes", {})

    if message.text.strip() != "-":
        prizes["2"] = message.text.strip()
        await state.update_data(edit_prizes=prizes)

    await state.set_state(EditTournamentStates.waiting_prize_3)
    await message.answer(
        f"{Emoji.GIFT} <b>Введите приз за 3 место</b> (или отправьте '-' чтобы пропустить):",
        parse_mode="HTML"
    )


@router.message(EditTournamentStates.waiting_prize_3)
async def process_edit_prize_3(message: Message, state: FSMContext):
    """Приз за 3 место и сохранение."""
    data = await state.get_data()
    prizes = data.get("edit_prizes", {})
    tournament_id = data["edit_tournament_id"]

    if message.text.strip() != "-":
        prizes["3"] = message.text.strip()

    await db.update_tournament(tournament_id, prizes=prizes, prize_type="custom")
    await db.log_action(message.from_user.id, "tournament_edit", f"Changed prizes")

    await state.clear()

    tournament = await db.get_tournament(tournament_id)
    participant_count = await db.get_tournament_participant_count(tournament_id)
    text = format_tournament_info(tournament, participant_count)

    await message.answer(
        f"{Emoji.CHECK} Призы обновлены!\n\n{text}",
        reply_markup=kb.admin_tournament_manage(tournament),
        parse_mode="HTML"
    )


# ==================== ШАБЛОНЫ ====================

@router.callback_query(F.data.regexp(r"^admin_t_save_template_(\d+)$"))
async def callback_admin_save_template(callback: CallbackQuery):
    """Сохранить турнир как шаблон."""
    tournament_id = int(callback.data.split("_")[4])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    # Создаём шаблон на основе турнира
    # Получаем время из турнира
    start_time = tournament.get("start_time")
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    default_hour = start_time.hour if start_time else 18
    default_minute = start_time.minute if start_time else 0

    template_id = await db.create_template(
        name=f"Шаблон: {tournament['name']}",
        format=tournament["format"],
        maps=tournament["maps"],
        max_participants=tournament["max_participants"],
        prize_type=tournament.get("prize_type", "none"),
        prize_amount=tournament.get("prize_amount", 0),
        checkin_hours=tournament.get("checkin_hours", 0),
        default_hour=default_hour,
        default_minute=default_minute,
        created_by=callback.from_user.id
    )

    await db.log_action(callback.from_user.id, "template_create", f"From tournament {tournament_id}")

    await callback.answer("Шаблон создан!", show_alert=True)
    await _show_tournament_manage(callback, tournament_id)


@router.callback_query(F.data.regexp(r"^template_custom_(\d+)$"))
async def callback_template_custom(callback: CallbackQuery, state: FSMContext):
    """Использовать пользовательский шаблон."""
    template_id = int(callback.data.split("_")[2])

    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    template = await db.get_template(template_id)
    if not template:
        await callback.answer("Шаблон не найден!", show_alert=True)
        return

    # Загружаем данные шаблона в состояние создания турнира
    await state.update_data(
        format=template["format"],
        maps=template["maps"],
        max_participants=template["max_participants"],
        prize_type=template.get("prize_type", "none"),
        prize_amount=template.get("prize_amount", 0),
        checkin_hours=template.get("checkin_hours", 0)
    )
    await state.set_state(CreateTournamentStates.waiting_name)

    format_name = config.TOURNAMENT_FORMATS.get(template["format"], {}).get("name", template["format"])

    await callback.message.edit_text(
        f"{Emoji.TROPHY} <b>Создание турнира из шаблона</b>\n\n"
        f"Формат: {format_name}\n"
        f"Карты: {', '.join(template['maps'])}\n"
        f"Участников: {template['max_participants']}\n\n"
        f"{Emoji.EDIT} <b>Введите название турнира:</b>",
        reply_markup=kb.back_button("admin"),
        parse_mode="HTML"
    )
    await callback.answer()
