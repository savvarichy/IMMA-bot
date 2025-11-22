"""Вспомогательные функции."""
import re
import random
import string
from datetime import datetime
from typing import Optional

from keyboards import Emoji
from config import config


def generate_invite_code() -> str:
    """Генерация инвайт-кода команды (формат: IMMA-XXXX)."""
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=4))
    return f"IMMA-{code}"


def validate_nickname(nickname: str) -> tuple[bool, str]:
    """
    Валидация никнейма.
    Возвращает (is_valid, error_message).
    """
    if not nickname:
        return False, "Никнейм не может быть пустым"

    if len(nickname) < 2:
        return False, "Никнейм слишком короткий (минимум 2 символа)"

    if len(nickname) > 32:
        return False, "Никнейм слишком длинный (максимум 32 символа)"

    return True, ""


def validate_steam_link(link: str) -> tuple[bool, str]:
    """
    Валидация ссылки на Steam профиль.
    Возвращает (is_valid, error_message).
    """
    if not link:
        return False, "Ссылка не может быть пустой"

    # Паттерны для Steam ссылок
    patterns = [
        r"^https?://steamcommunity\.com/id/[\w-]+/?$",
        r"^https?://steamcommunity\.com/profiles/\d+/?$",
        r"^steamcommunity\.com/id/[\w-]+/?$",
        r"^steamcommunity\.com/profiles/\d+/?$",
    ]

    link = link.strip()
    for pattern in patterns:
        if re.match(pattern, link, re.IGNORECASE):
            return True, ""

    return False, (
        "Неверный формат ссылки Steam.\n"
        "Примеры:\n"
        "• https://steamcommunity.com/id/your_id\n"
        "• https://steamcommunity.com/profiles/76561198000000000"
    )


def validate_contact(contact: str) -> tuple[bool, str]:
    """
    Валидация контакта для связи.
    Возвращает (is_valid, error_message).
    """
    if not contact:
        return False, "Контакт не может быть пустым"

    if len(contact) < 3:
        return False, "Контакт слишком короткий"

    if len(contact) > 100:
        return False, "Контакт слишком длинный"

    return True, ""


def format_datetime(dt: datetime, include_year: bool = True) -> str:
    """Форматирование даты и времени для отображения."""
    months = [
        "", "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]

    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)

    day = dt.day
    month = months[dt.month]
    time = dt.strftime("%H:%M")

    if include_year:
        return f"{day} {month} {dt.year}, {time} МСК"
    return f"{day} {month}, {time} МСК"


def format_tournament_info(tournament: dict, participant_count: int) -> str:
    """Форматирование информации о турнире."""
    status_text = config.TOURNAMENT_STATUSES.get(tournament["status"], tournament["status"])
    format_text = config.TOURNAMENT_FORMATS.get(tournament["format"], {}).get("name", tournament["format"])
    prize_text = format_prizes(tournament)
    maps_text = ", ".join(m.replace("de_", "") for m in tournament["maps"])

    progress = Emoji.progress_bar(participant_count, tournament["max_participants"])

    text = f"""
<b>{Emoji.TROPHY} {tournament['name']}</b>

{Emoji.INFO} <b>Статус:</b> {status_text}
{Emoji.GAME} <b>Формат:</b> {format_text}
{Emoji.MAP} <b>Карты:</b> {maps_text}
{Emoji.PEOPLE} <b>Участники:</b> {participant_count}/{tournament['max_participants']}
{progress}
{Emoji.GIFT} <b>Призы:</b>
{prize_text}
{Emoji.CALENDAR} <b>Старт:</b> {format_datetime(tournament['start_time'])}
"""

    if tournament["checkin_hours"] > 0:
        text += f"{Emoji.BELL} <b>Check-in:</b> за {tournament['checkin_hours']} ч. до старта\n"

    return text.strip()


def format_prizes(tournament: dict) -> str:
    """Форматирование призов турнира."""
    prizes = tournament.get("prizes")
    prize_type = tournament.get("prize_type", "none")

    if prize_type == "none" or not prizes:
        # Старый формат с prize_amount
        amount = tournament.get("prize_amount", 0)
        if amount > 0:
            return format_prize_old(prize_type, amount)
        return "Без приза"

    # Новый формат с отдельными призами по местам
    lines = []
    for place, prize in sorted(prizes.items(), key=lambda x: int(x[0])):
        emoji = config.PRIZE_PLACES.get(int(place), f"{place}.")
        lines.append(f"{emoji} {prize}")

    return "\n".join(lines) if lines else "Без приза"


def format_prize_old(prize_type: str, amount: int) -> str:
    """Форматирование приза (старый формат)."""
    if prize_type == "none" or amount == 0:
        return "Без приза"

    if prize_type == "rub":
        return f"{amount:,}₽".replace(",", " ")
    elif prize_type == "stars":
        return f"{amount} ⭐ TG Stars"
    elif prize_type == "skins":
        return f"Скины на {amount:,}₽".replace(",", " ")

    return str(amount)


def format_player_info(player: dict) -> str:
    """Форматирование информации об игроке."""
    winrate = 0
    if player["tournaments_played"] > 0:
        winrate = (player["tournaments_won"] / player["tournaments_played"]) * 100

    text = f"""
<b>{Emoji.PERSON} Профиль игрока</b>

{Emoji.GAME} <b>Никнейм:</b> {player['nickname']}
{Emoji.LINK} <b>Steam:</b> {player['steam_link']}
{Emoji.SEND} <b>Контакт:</b> {player['contact']}

<b>{Emoji.CHART} Статистика:</b>
• Турниров сыграно: {player['tournaments_played']}
• Побед: {player['tournaments_won']}
• Винрейт: {winrate:.1f}%
• Пропущено check-in: {player['missed_checkins']}
"""

    if player.get("is_banned"):
        text += f"\n{Emoji.LOCK} <b>Заблокирован:</b> {player.get('ban_reason', 'Без причины')}"

    return text.strip()


def format_team_info(team: dict, members: list[dict], captain_id: int) -> str:
    """Форматирование информации о команде."""
    format_text = config.TOURNAMENT_FORMATS.get(team["format"], {}).get("name", team["format"])

    members_text = ""
    for member in members:
        icon = Emoji.CROWN if member["id"] == captain_id else Emoji.PERSON
        members_text += f"  {icon} {member['nickname']}\n"

    text = f"""
<b>{Emoji.PEOPLE} {team['name']}</b>

{Emoji.GAME} <b>Формат:</b> {format_text}
{Emoji.TROPHY} <b>Турниров:</b> {team['tournaments_played']} (побед: {team['tournaments_won']})

<b>Состав:</b>
{members_text.rstrip()}
"""

    if team.get("invite_code"):
        text += f"\n{Emoji.KEY} <b>Код приглашения:</b> <code>{team['invite_code']}</code>"

    return text.strip()


def format_match_info(
    match: dict,
    participant1_name: str,
    participant2_name: str
) -> str:
    """Форматирование информации о матче."""
    status_emoji = {
        "pending": Emoji.CLOCK,
        "active": Emoji.FIRE,
        "completed": Emoji.CHECK
    }.get(match["status"], Emoji.INFO)

    text = f"""
<b>{status_emoji} Матч #{match['match_number']}</b> (Раунд {match['round']})

{Emoji.SWORD} {participant1_name}
   vs
{Emoji.SWORD} {participant2_name}
"""

    if match["map"]:
        text += f"\n{Emoji.MAP} <b>Карта:</b> {match['map'].replace('de_', '')}"

    if match["status"] == "completed":
        text += f"\n\n{Emoji.TARGET} <b>Счёт:</b> {match['score1']} : {match['score2']}"

    return text.strip()


def format_bracket_text(matches: list[dict], participants: dict) -> str:
    """Визуальное отображение сетки турнира в текстовом формате."""
    if not matches:
        return "Сетка пока не сформирована"

    # Группируем матчи по раундам
    rounds: dict[int, list[dict]] = {}
    for match in matches:
        round_num = match["round"]
        if round_num not in rounds:
            rounds[round_num] = []
        rounds[round_num].append(match)

    total_rounds = max(rounds.keys()) if rounds else 0
    round_names = {
        total_rounds: "Финал",
        total_rounds - 1: "Полуфинал",
        total_rounds - 2: "Четвертьфинал"
    }

    text = f"<b>{Emoji.TARGET} Турнирная сетка</b>\n\n"

    for round_num in sorted(rounds.keys()):
        round_name = round_names.get(round_num, f"Раунд {round_num}")
        text += f"<b>━━━ {round_name} ━━━</b>\n\n"

        for match in sorted(rounds[round_num], key=lambda x: x["match_number"]):
            p1_name = participants.get(match["participant1_id"], "TBD") if match["participant1_id"] else "TBD"
            p2_name = participants.get(match["participant2_id"], "TBD") if match["participant2_id"] else "TBD"

            if match["status"] == "completed":
                # Выделяем победителя
                if match["winner_id"] == match["participant1_id"]:
                    text += f"<b>{Emoji.TROPHY} {p1_name}</b> {match['score1']}\n"
                    text += f"     {p2_name} {match['score2']}\n"
                else:
                    text += f"     {p1_name} {match['score1']}\n"
                    text += f"<b>{Emoji.TROPHY} {p2_name}</b> {match['score2']}\n"
            else:
                text += f"  {Emoji.SWORD} {p1_name}\n"
                text += f"  {Emoji.SWORD} {p2_name}\n"

            text += "\n"

    return text.strip()


def generate_cybershoke_config(
    tournament: dict,
    match: dict,
    team1_name: str,
    team2_name: str
) -> str:
    """Генерация конфига для Cybershoke сервера."""
    map_name = match.get("map") or tournament["maps"][0]

    config_text = f"""
<b>{Emoji.GEAR} Конфиг для Cybershoke</b>

<code>
mp_teamname_1 "{team1_name}"
mp_teamname_2 "{team2_name}"
changelevel {map_name}
mp_warmup_pausetimer 1
mp_warmuptime 60
mp_freezetime 15
mp_roundtime 1.92
mp_roundtime_defuse 1.92
mp_maxrounds 24
mp_overtime_enable 1
mp_overtime_maxrounds 6
</code>

{Emoji.MAP} Карта: <b>{map_name.replace('de_', '')}</b>
"""
    return config_text.strip()


def get_time_until(dt: datetime) -> str:
    """Получить текст о времени до события."""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)

    now = datetime.now()
    delta = dt - now

    if delta.total_seconds() < 0:
        return "Уже началось"

    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days} д.")
    if hours > 0:
        parts.append(f"{hours} ч.")
    if minutes > 0 and days == 0:
        parts.append(f"{minutes} мин.")

    return " ".join(parts) if parts else "Меньше минуты"


def is_power_of_two(n: int) -> bool:
    """Проверка, является ли число степенью двойки."""
    return n > 0 and (n & (n - 1)) == 0


def next_power_of_two(n: int) -> int:
    """Получить следующую степень двойки."""
    if n <= 0:
        return 1
    p = 1
    while p < n:
        p *= 2
    return p


def calculate_rounds_count(participants: int) -> int:
    """Рассчитать количество раундов для турнира."""
    import math
    if participants <= 1:
        return 0
    return math.ceil(math.log2(participants))


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезать текст с добавлением многоточия."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def escape_html(text: str) -> str:
    """Экранирование HTML символов."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
