"""Генератор турнирной сетки (Single Elimination)."""
import random
import math
from typing import Optional

from database import db


class BracketGenerator:
    """Генератор турнирной сетки Single Elimination."""

    def __init__(
        self,
        tournament_id: int,
        participants: list[dict],
        participant_type: str  # "player" или "team"
    ):
        self.tournament_id = tournament_id
        self.participants = participants
        self.participant_type = participant_type

    async def generate(self) -> None:
        """Генерация сетки турнира."""
        # Проверка на пустой список участников
        if not self.participants:
            return

        # Перемешиваем участников
        shuffled = self.participants.copy()
        random.shuffle(shuffled)

        # Определяем количество раундов
        num_participants = len(shuffled)
        if num_participants == 1:
            # Один участник - автоматический победитель, матчи не нужны
            return
        num_rounds = math.ceil(math.log2(num_participants))

        # Количество слотов в первом раунде (степень двойки)
        bracket_size = 2 ** num_rounds

        # Количество bye (пустых слотов)
        num_byes = bracket_size - num_participants

        # Создаём список участников с bye
        # Bye размещаются так, чтобы игроки получили их равномерно
        participants_with_byes = self._distribute_byes(shuffled, bracket_size, num_byes)

        # Генерируем все раунды
        await self._generate_rounds(participants_with_byes, num_rounds)

    def _distribute_byes(
        self,
        participants: list[dict],
        bracket_size: int,
        num_byes: int
    ) -> list[Optional[dict]]:
        """
        Распределение bye (пропусков) в сетке.
        Возвращает список размером bracket_size, где None = bye.
        """
        result = [None] * bracket_size

        # Используем seeding для размещения участников
        # Топ-сиды получают bye
        seeds = self._generate_seeding(bracket_size)

        participant_idx = 0
        for seed_idx, position in enumerate(seeds):
            if participant_idx < len(participants):
                result[position] = participants[participant_idx]
                participant_idx += 1

        return result

    def _generate_seeding(self, bracket_size: int) -> list[int]:
        """
        Генерация порядка сидов (seeding).
        Возвращает позиции в порядке заполнения.
        """
        if bracket_size == 2:
            return [0, 1]

        # Рекурсивно генерируем сиды для половины
        half = bracket_size // 2
        smaller_seeds = self._generate_seeding(half)

        result = []
        for seed in smaller_seeds:
            result.append(seed)
            result.append(bracket_size - 1 - seed)

        return result

    async def _generate_rounds(
        self,
        first_round_participants: list[Optional[dict]],
        num_rounds: int
    ) -> None:
        """Генерация всех раундов турнира."""
        current_round_participants = first_round_participants
        match_number = 1

        for round_num in range(1, num_rounds + 1):
            next_round_participants = []
            num_matches = len(current_round_participants) // 2

            for i in range(num_matches):
                p1 = current_round_participants[i * 2]
                p2 = current_round_participants[i * 2 + 1]

                p1_id = p1["id"] if p1 else None
                p2_id = p2["id"] if p2 else None

                # Создаём матч
                match_id = await db.create_match(
                    tournament_id=self.tournament_id,
                    round_num=round_num,
                    match_number=match_number,
                    participant1_id=p1_id,
                    participant2_id=p2_id,
                    participant_type=self.participant_type
                )

                # Если один из участников bye - автоматическая победа
                if p1_id and not p2_id:
                    # Победа p1
                    await db.set_match_result(match_id, 1, 0, p1_id)
                    next_round_participants.append(p1)
                elif p2_id and not p1_id:
                    # Победа p2
                    await db.set_match_result(match_id, 0, 1, p2_id)
                    next_round_participants.append(p2)
                elif not p1_id and not p2_id:
                    # Оба bye - пустой слот в следующем раунде
                    next_round_participants.append(None)
                else:
                    # Оба участника есть - матч будет сыгран
                    next_round_participants.append(None)  # Placeholder

                match_number += 1

            # Создаём матчи следующего раунда (если не финал)
            if round_num < num_rounds:
                current_round_participants = [None] * len(next_round_participants)
                # Победители из предыдущего раунда будут добавлены по мере игры

        # Создаём пустые матчи для оставшихся раундов
        matches_in_round = len(first_round_participants) // 2
        for round_num in range(2, num_rounds + 1):
            matches_in_round //= 2
            for i in range(matches_in_round):
                # Матчи уже созданы выше с bye, создаём только если нужно
                pass


async def get_bracket_display(tournament_id: int) -> dict:
    """
    Получение данных сетки для отображения.
    Возвращает структуру для визуализации.
    """
    matches = await db.get_tournament_matches(tournament_id)
    tournament = await db.get_tournament(tournament_id)

    # Получаем имена участников
    participants = {}
    if tournament["format"] == "1v1":
        players = await db.get_tournament_players(tournament_id)
        for p in players:
            participants[p["id"]] = {
                "name": p["nickname"],
                "type": "player"
            }
    else:
        teams = await db.get_tournament_teams(tournament_id)
        for t in teams:
            participants[t["id"]] = {
                "name": t["name"],
                "type": "team"
            }

    # Группируем матчи по раундам
    rounds = {}
    for match in matches:
        r = match["round"]
        if r not in rounds:
            rounds[r] = []
        rounds[r].append({
            "id": match["id"],
            "match_number": match["match_number"],
            "participant1": participants.get(match["participant1_id"]),
            "participant2": participants.get(match["participant2_id"]),
            "score1": match["score1"],
            "score2": match["score2"],
            "winner_id": match["winner_id"],
            "status": match["status"]
        })

    return {
        "tournament_id": tournament_id,
        "tournament_name": tournament["name"],
        "rounds": rounds,
        "total_rounds": max(rounds.keys()) if rounds else 0
    }
