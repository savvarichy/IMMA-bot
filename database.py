"""Модуль работы с базой данных."""
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional
import json

from config import config


class Database:
    """Класс для работы с SQLite базой данных."""

    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Подключение к базе данных."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()

    async def disconnect(self) -> None:
        """Отключение от базы данных."""
        if self._connection:
            await self._connection.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        """Получить соединение."""
        if not self._connection:
            raise RuntimeError("Database not connected")
        return self._connection

    async def _create_tables(self) -> None:
        """Создание таблиц."""
        await self.conn.executescript("""
            -- Игроки
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                nickname TEXT NOT NULL,
                steam_link TEXT NOT NULL,
                contact TEXT NOT NULL,
                tournaments_played INTEGER DEFAULT 0,
                tournaments_won INTEGER DEFAULT 0,
                missed_checkins INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Команды
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                captain_id INTEGER NOT NULL,
                format TEXT NOT NULL,
                invite_code TEXT,
                invite_expires_at TIMESTAMP,
                tournaments_played INTEGER DEFAULT 0,
                tournaments_won INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (captain_id) REFERENCES players(id)
            );

            -- Участники команд
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(id),
                UNIQUE(team_id, player_id)
            );

            -- Турниры
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                format TEXT NOT NULL,
                maps TEXT NOT NULL,
                max_participants INTEGER NOT NULL,
                prize_type TEXT NOT NULL,
                prize_amount INTEGER DEFAULT 0,
                start_time TIMESTAMP NOT NULL,
                registration_deadline TIMESTAMP NOT NULL,
                checkin_hours INTEGER DEFAULT 0,
                status TEXT DEFAULT 'draft',
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES players(id)
            );

            -- Регистрации на турнир (для 1v1 - игроки)
            CREATE TABLE IF NOT EXISTS tournament_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                checked_in INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(id),
                UNIQUE(tournament_id, player_id)
            );

            -- Регистрации на турнир (для 2v2/5v5 - команды)
            CREATE TABLE IF NOT EXISTS tournament_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                checked_in INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams(id),
                UNIQUE(tournament_id, team_id)
            );

            -- Матчи
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                round INTEGER NOT NULL,
                match_number INTEGER NOT NULL,
                participant1_id INTEGER,
                participant2_id INTEGER,
                participant1_type TEXT NOT NULL,
                score1 INTEGER,
                score2 INTEGER,
                winner_id INTEGER,
                map TEXT,
                status TEXT DEFAULT 'pending',
                scheduled_time TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
            );

            -- Шаблоны турниров (пользовательские)
            CREATE TABLE IF NOT EXISTS tournament_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                format TEXT NOT NULL,
                maps TEXT NOT NULL,
                max_participants INTEGER NOT NULL,
                prize_type TEXT NOT NULL,
                prize_amount INTEGER DEFAULT 0,
                checkin_hours INTEGER DEFAULT 1,
                default_hour INTEGER DEFAULT 20,
                default_minute INTEGER DEFAULT 0,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES players(id)
            );

            -- Логи действий
            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Администраторы
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                added_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Настройки канала
            CREATE TABLE IF NOT EXISTS channel_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER UNIQUE NOT NULL,
                channel_username TEXT,
                added_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Посты турниров в каналах
            CREATE TABLE IF NOT EXISTS tournament_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                UNIQUE(tournament_id, channel_id)
            );

            -- Индексы
            CREATE INDEX IF NOT EXISTS idx_players_telegram ON players(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_teams_captain ON teams(captain_id);
            CREATE INDEX IF NOT EXISTS idx_teams_invite ON teams(invite_code);
            CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);
            CREATE INDEX IF NOT EXISTS idx_matches_tournament ON matches(tournament_id);
            CREATE INDEX IF NOT EXISTS idx_tournament_posts ON tournament_posts(tournament_id);
        """)
        await self.conn.commit()

    # ==================== ИГРОКИ ====================

    async def get_player(self, telegram_id: int) -> Optional[dict]:
        """Получить игрока по telegram_id."""
        async with self.conn.execute(
            "SELECT * FROM players WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_player_by_id(self, player_id: int) -> Optional[dict]:
        """Получить игрока по ID."""
        async with self.conn.execute(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_player(
        self,
        telegram_id: int,
        username: Optional[str],
        nickname: str,
        steam_link: str,
        contact: str
    ) -> int:
        """Создать нового игрока."""
        async with self.conn.execute(
            """INSERT INTO players (telegram_id, username, nickname, steam_link, contact)
               VALUES (?, ?, ?, ?, ?)""",
            (telegram_id, username, nickname, steam_link, contact)
        ) as cursor:
            await self.conn.commit()
            return cursor.lastrowid

    async def update_player(self, telegram_id: int, **kwargs) -> None:
        """Обновить данные игрока."""
        if not kwargs:
            return
        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [telegram_id]
        await self.conn.execute(
            f"UPDATE players SET {fields} WHERE telegram_id = ?", values
        )
        await self.conn.commit()

    async def get_top_players(self, limit: int = 10) -> list[dict]:
        """Получить топ игроков по победам."""
        async with self.conn.execute(
            """SELECT * FROM players
               WHERE is_banned = 0
               ORDER BY tournaments_won DESC, tournaments_played DESC
               LIMIT ?""",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_players(self, search: Optional[str] = None) -> list[dict]:
        """Получить всех игроков."""
        if search:
            async with self.conn.execute(
                """SELECT * FROM players
                   WHERE nickname LIKE ? OR username LIKE ?
                   ORDER BY created_at DESC""",
                (f"%{search}%", f"%{search}%")
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        else:
            async with self.conn.execute(
                "SELECT * FROM players ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def ban_player(self, telegram_id: int, reason: str) -> None:
        """Забанить игрока."""
        await self.update_player(telegram_id, is_banned=1, ban_reason=reason)

    async def unban_player(self, telegram_id: int) -> None:
        """Разбанить игрока."""
        await self.update_player(telegram_id, is_banned=0, ban_reason=None)

    async def increment_player_stats(
        self, telegram_id: int, won: bool = False, missed_checkin: bool = False
    ) -> None:
        """Увеличить статистику игрока."""
        player = await self.get_player(telegram_id)
        if not player:
            return

        updates = {"tournaments_played": player["tournaments_played"] + 1}
        if won:
            updates["tournaments_won"] = player["tournaments_won"] + 1
        if missed_checkin:
            updates["missed_checkins"] = player["missed_checkins"] + 1

        await self.update_player(telegram_id, **updates)

    # ==================== КОМАНДЫ ====================

    async def get_team(self, team_id: int) -> Optional[dict]:
        """Получить команду по ID."""
        async with self.conn.execute(
            "SELECT * FROM teams WHERE id = ?", (team_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_team_by_invite(self, invite_code: str) -> Optional[dict]:
        """Получить команду по инвайт-коду."""
        async with self.conn.execute(
            """SELECT * FROM teams
               WHERE invite_code = ? AND invite_expires_at > datetime('now')""",
            (invite_code.upper(),)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_player_teams(self, player_id: int) -> list[dict]:
        """Получить команды игрока."""
        async with self.conn.execute(
            """SELECT t.* FROM teams t
               JOIN team_members tm ON t.id = tm.team_id
               WHERE tm.player_id = ?
               ORDER BY t.created_at DESC""",
            (player_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_player_team_by_format(
        self, player_id: int, format: str
    ) -> Optional[dict]:
        """Получить команду игрока для определённого формата."""
        async with self.conn.execute(
            """SELECT t.* FROM teams t
               JOIN team_members tm ON t.id = tm.team_id
               WHERE tm.player_id = ? AND t.format = ?""",
            (player_id, format)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_team(
        self,
        name: str,
        captain_id: int,
        format: str,
        invite_code: str
    ) -> int:
        """Создать команду."""
        expires_at = datetime.now() + timedelta(seconds=config.INVITE_CODE_LIFETIME)
        async with self.conn.execute(
            """INSERT INTO teams (name, captain_id, format, invite_code, invite_expires_at)
               VALUES (?, ?, ?, ?, ?)""",
            (name, captain_id, format, invite_code.upper(), expires_at)
        ) as cursor:
            team_id = cursor.lastrowid

        # Добавляем капитана как участника
        await self.add_team_member(team_id, captain_id)
        await self.conn.commit()
        return team_id

    async def add_team_member(self, team_id: int, player_id: int) -> bool:
        """Добавить игрока в команду."""
        try:
            await self.conn.execute(
                "INSERT INTO team_members (team_id, player_id) VALUES (?, ?)",
                (team_id, player_id)
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def remove_team_member(self, team_id: int, player_id: int) -> None:
        """Удалить игрока из команды."""
        await self.conn.execute(
            "DELETE FROM team_members WHERE team_id = ? AND player_id = ?",
            (team_id, player_id)
        )
        await self.conn.commit()

    async def get_team_members(self, team_id: int) -> list[dict]:
        """Получить участников команды."""
        async with self.conn.execute(
            """SELECT p.* FROM players p
               JOIN team_members tm ON p.id = tm.player_id
               WHERE tm.team_id = ?
               ORDER BY tm.joined_at""",
            (team_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_team_member_count(self, team_id: int) -> int:
        """Получить количество участников команды."""
        async with self.conn.execute(
            "SELECT COUNT(*) as cnt FROM team_members WHERE team_id = ?",
            (team_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def update_team(self, team_id: int, **kwargs) -> None:
        """Обновить команду."""
        if not kwargs:
            return
        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [team_id]
        await self.conn.execute(
            f"UPDATE teams SET {fields} WHERE id = ?", values
        )
        await self.conn.commit()

    async def regenerate_invite_code(self, team_id: int, new_code: str) -> None:
        """Обновить инвайт-код команды."""
        expires_at = datetime.now() + timedelta(seconds=config.INVITE_CODE_LIFETIME)
        await self.update_team(
            team_id,
            invite_code=new_code.upper(),
            invite_expires_at=expires_at
        )

    async def delete_team(self, team_id: int) -> None:
        """Удалить команду."""
        await self.conn.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        await self.conn.commit()

    async def transfer_captaincy(self, team_id: int, new_captain_id: int) -> None:
        """Передать капитанство."""
        await self.update_team(team_id, captain_id=new_captain_id)

    async def get_all_teams(self) -> list[dict]:
        """Получить все команды."""
        async with self.conn.execute(
            "SELECT * FROM teams ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_top_teams(self, limit: int = 10) -> list[dict]:
        """Получить топ команд по победам."""
        async with self.conn.execute(
            """SELECT * FROM teams
               ORDER BY tournaments_won DESC, tournaments_played DESC
               LIMIT ?""",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ==================== ТУРНИРЫ ====================

    async def create_tournament(
        self,
        name: str,
        format: str,
        maps: list[str],
        max_participants: int,
        prize_type: str,
        prize_amount: int,
        start_time: datetime,
        registration_deadline: datetime,
        checkin_hours: int,
        created_by: int
    ) -> int:
        """Создать турнир."""
        async with self.conn.execute(
            """INSERT INTO tournaments
               (name, format, maps, max_participants, prize_type, prize_amount,
                start_time, registration_deadline, checkin_hours, created_by, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')""",
            (name, format, json.dumps(maps), max_participants, prize_type,
             prize_amount, start_time, registration_deadline, checkin_hours, created_by)
        ) as cursor:
            await self.conn.commit()
            return cursor.lastrowid

    async def get_tournament(self, tournament_id: int) -> Optional[dict]:
        """Получить турнир по ID."""
        async with self.conn.execute(
            "SELECT * FROM tournaments WHERE id = ?", (tournament_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data["maps"] = json.loads(data["maps"])
                return data
            return None

    async def get_tournaments_by_status(self, status: str) -> list[dict]:
        """Получить турниры по статусу."""
        async with self.conn.execute(
            "SELECT * FROM tournaments WHERE status = ? ORDER BY start_time",
            (status,)
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                data = dict(r)
                data["maps"] = json.loads(data["maps"])
                result.append(data)
            return result

    async def get_active_tournaments(self) -> list[dict]:
        """Получить активные турниры (открытые/чекин/идущие)."""
        async with self.conn.execute(
            """SELECT * FROM tournaments
               WHERE status IN ('open', 'checkin', 'active')
               ORDER BY start_time"""
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                data = dict(r)
                data["maps"] = json.loads(data["maps"])
                result.append(data)
            return result

    async def get_all_tournaments(self) -> list[dict]:
        """Получить все турниры."""
        async with self.conn.execute(
            "SELECT * FROM tournaments ORDER BY start_time DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                data = dict(r)
                data["maps"] = json.loads(data["maps"])
                result.append(data)
            return result

    async def update_tournament(self, tournament_id: int, **kwargs) -> None:
        """Обновить турнир."""
        if not kwargs:
            return
        if "maps" in kwargs:
            kwargs["maps"] = json.dumps(kwargs["maps"])
        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [tournament_id]
        await self.conn.execute(
            f"UPDATE tournaments SET {fields} WHERE id = ?", values
        )
        await self.conn.commit()

    async def update_tournament_status(self, tournament_id: int, status: str) -> None:
        """Обновить статус турнира."""
        await self.update_tournament(tournament_id, status=status)

    # ==================== РЕГИСТРАЦИИ НА ТУРНИР ====================

    async def register_player_to_tournament(
        self, tournament_id: int, player_id: int
    ) -> bool:
        """Зарегистрировать игрока на турнир (1v1)."""
        try:
            await self.conn.execute(
                """INSERT INTO tournament_players (tournament_id, player_id)
                   VALUES (?, ?)""",
                (tournament_id, player_id)
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def unregister_player_from_tournament(
        self, tournament_id: int, player_id: int
    ) -> None:
        """Снять регистрацию игрока с турнира."""
        await self.conn.execute(
            """DELETE FROM tournament_players
               WHERE tournament_id = ? AND player_id = ?""",
            (tournament_id, player_id)
        )
        await self.conn.commit()

    async def register_team_to_tournament(
        self, tournament_id: int, team_id: int
    ) -> bool:
        """Зарегистрировать команду на турнир."""
        try:
            await self.conn.execute(
                """INSERT INTO tournament_teams (tournament_id, team_id)
                   VALUES (?, ?)""",
                (tournament_id, team_id)
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def unregister_team_from_tournament(
        self, tournament_id: int, team_id: int
    ) -> None:
        """Снять регистрацию команды с турнира."""
        await self.conn.execute(
            """DELETE FROM tournament_teams
               WHERE tournament_id = ? AND team_id = ?""",
            (tournament_id, team_id)
        )
        await self.conn.commit()

    async def get_tournament_players(self, tournament_id: int) -> list[dict]:
        """Получить игроков турнира (1v1)."""
        async with self.conn.execute(
            """SELECT p.*, tp.checked_in FROM players p
               JOIN tournament_players tp ON p.id = tp.player_id
               WHERE tp.tournament_id = ?
               ORDER BY tp.registered_at""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_tournament_teams(self, tournament_id: int) -> list[dict]:
        """Получить команды турнира."""
        async with self.conn.execute(
            """SELECT t.*, tt.checked_in FROM teams t
               JOIN tournament_teams tt ON t.id = tt.team_id
               WHERE tt.tournament_id = ?
               ORDER BY tt.registered_at""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_tournament_participant_count(self, tournament_id: int) -> int:
        """Получить количество участников турнира."""
        tournament = await self.get_tournament(tournament_id)
        if not tournament:
            return 0

        if tournament["format"] == "1v1":
            async with self.conn.execute(
                "SELECT COUNT(*) as cnt FROM tournament_players WHERE tournament_id = ?",
                (tournament_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row["cnt"] if row else 0
        else:
            async with self.conn.execute(
                "SELECT COUNT(*) as cnt FROM tournament_teams WHERE tournament_id = ?",
                (tournament_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row["cnt"] if row else 0

    async def is_player_registered(self, tournament_id: int, player_id: int) -> bool:
        """Проверить регистрацию игрока на турнир."""
        async with self.conn.execute(
            """SELECT 1 FROM tournament_players
               WHERE tournament_id = ? AND player_id = ?""",
            (tournament_id, player_id)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def is_team_registered(self, tournament_id: int, team_id: int) -> bool:
        """Проверить регистрацию команды на турнир."""
        async with self.conn.execute(
            """SELECT 1 FROM tournament_teams
               WHERE tournament_id = ? AND team_id = ?""",
            (tournament_id, team_id)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def checkin_player(self, tournament_id: int, player_id: int) -> None:
        """Check-in игрока."""
        await self.conn.execute(
            """UPDATE tournament_players SET checked_in = 1
               WHERE tournament_id = ? AND player_id = ?""",
            (tournament_id, player_id)
        )
        await self.conn.commit()

    async def checkin_team(self, tournament_id: int, team_id: int) -> None:
        """Check-in команды."""
        await self.conn.execute(
            """UPDATE tournament_teams SET checked_in = 1
               WHERE tournament_id = ? AND team_id = ?""",
            (tournament_id, team_id)
        )
        await self.conn.commit()

    async def get_checked_in_players(self, tournament_id: int) -> list[dict]:
        """Получить игроков прошедших check-in."""
        async with self.conn.execute(
            """SELECT p.* FROM players p
               JOIN tournament_players tp ON p.id = tp.player_id
               WHERE tp.tournament_id = ? AND tp.checked_in = 1""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_checked_in_teams(self, tournament_id: int) -> list[dict]:
        """Получить команды прошедшие check-in."""
        async with self.conn.execute(
            """SELECT t.* FROM teams t
               JOIN tournament_teams tt ON t.id = tt.team_id
               WHERE tt.tournament_id = ? AND tt.checked_in = 1""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ==================== МАТЧИ ====================

    async def create_match(
        self,
        tournament_id: int,
        round_num: int,
        match_number: int,
        participant1_id: Optional[int],
        participant2_id: Optional[int],
        participant_type: str,
        map_name: Optional[str] = None
    ) -> int:
        """Создать матч."""
        async with self.conn.execute(
            """INSERT INTO matches
               (tournament_id, round, match_number, participant1_id, participant2_id,
                participant1_type, map, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (tournament_id, round_num, match_number, participant1_id,
             participant2_id, participant_type, map_name)
        ) as cursor:
            await self.conn.commit()
            return cursor.lastrowid

    async def get_match(self, match_id: int) -> Optional[dict]:
        """Получить матч по ID."""
        async with self.conn.execute(
            "SELECT * FROM matches WHERE id = ?", (match_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_tournament_matches(self, tournament_id: int) -> list[dict]:
        """Получить все матчи турнира."""
        async with self.conn.execute(
            """SELECT * FROM matches
               WHERE tournament_id = ?
               ORDER BY round, match_number""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_tournament_matches_by_round(
        self, tournament_id: int, round_num: int
    ) -> list[dict]:
        """Получить матчи раунда турнира."""
        async with self.conn.execute(
            """SELECT * FROM matches
               WHERE tournament_id = ? AND round = ?
               ORDER BY match_number""",
            (tournament_id, round_num)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_pending_matches(self, tournament_id: int) -> list[dict]:
        """Получить незавершённые матчи."""
        async with self.conn.execute(
            """SELECT * FROM matches
               WHERE tournament_id = ? AND status = 'pending'
               ORDER BY round, match_number""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_match(self, match_id: int, **kwargs) -> None:
        """Обновить матч."""
        if not kwargs:
            return
        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [match_id]
        await self.conn.execute(
            f"UPDATE matches SET {fields} WHERE id = ?", values
        )
        await self.conn.commit()

    async def set_match_result(
        self, match_id: int, score1: int, score2: int, winner_id: int
    ) -> None:
        """Установить результат матча."""
        await self.update_match(
            match_id,
            score1=score1,
            score2=score2,
            winner_id=winner_id,
            status="completed",
            completed_at=datetime.now()
        )

    async def update_match_participant(
        self, match_id: int, position: int, participant_id: int
    ) -> None:
        """Обновить участника матча (для прохождения по сетке)."""
        field = f"participant{position}_id"
        await self.update_match(match_id, **{field: participant_id})

    async def get_next_match_for_winner(
        self, tournament_id: int, current_round: int, current_match: int
    ) -> Optional[dict]:
        """Получить следующий матч для победителя."""
        next_round = current_round + 1
        next_match_num = (current_match + 1) // 2
        async with self.conn.execute(
            """SELECT * FROM matches
               WHERE tournament_id = ? AND round = ? AND match_number = ?""",
            (tournament_id, next_round, next_match_num)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    # ==================== ШАБЛОНЫ ====================

    async def create_template(
        self,
        name: str,
        format: str,
        maps: list[str],
        max_participants: int,
        prize_type: str,
        prize_amount: int,
        checkin_hours: int,
        default_hour: int,
        default_minute: int,
        created_by: int
    ) -> int:
        """Создать шаблон турнира."""
        async with self.conn.execute(
            """INSERT INTO tournament_templates
               (name, format, maps, max_participants, prize_type, prize_amount,
                checkin_hours, default_hour, default_minute, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, format, json.dumps(maps), max_participants, prize_type,
             prize_amount, checkin_hours, default_hour, default_minute, created_by)
        ) as cursor:
            await self.conn.commit()
            return cursor.lastrowid

    async def get_template(self, template_id: int) -> Optional[dict]:
        """Получить шаблон по ID."""
        async with self.conn.execute(
            "SELECT * FROM tournament_templates WHERE id = ?", (template_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data["maps"] = json.loads(data["maps"])
                return data
            return None

    async def get_all_templates(self) -> list[dict]:
        """Получить все шаблоны."""
        async with self.conn.execute(
            "SELECT * FROM tournament_templates ORDER BY name"
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                data = dict(r)
                data["maps"] = json.loads(data["maps"])
                result.append(data)
            return result

    async def delete_template(self, template_id: int) -> None:
        """Удалить шаблон."""
        await self.conn.execute(
            "DELETE FROM tournament_templates WHERE id = ?", (template_id,)
        )
        await self.conn.commit()

    # ==================== АДМИНИСТРАТОРЫ ====================

    async def is_admin(self, telegram_id: int) -> bool:
        """Проверить является ли пользователь админом."""
        if telegram_id in config.ADMIN_IDS or telegram_id == config.OWNER_ID:
            return True
        async with self.conn.execute(
            "SELECT 1 FROM admins WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def add_admin(self, telegram_id: int, added_by: int) -> bool:
        """Добавить администратора."""
        try:
            await self.conn.execute(
                "INSERT INTO admins (telegram_id, added_by) VALUES (?, ?)",
                (telegram_id, added_by)
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def remove_admin(self, telegram_id: int) -> None:
        """Удалить администратора."""
        await self.conn.execute(
            "DELETE FROM admins WHERE telegram_id = ?", (telegram_id,)
        )
        await self.conn.commit()

    async def get_all_admins(self) -> list[dict]:
        """Получить всех админов."""
        async with self.conn.execute(
            "SELECT * FROM admins ORDER BY created_at"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ==================== ЛОГИ ====================

    async def log_action(self, admin_id: int, action: str, details: str = None) -> None:
        """Записать действие в лог."""
        await self.conn.execute(
            "INSERT INTO action_logs (admin_id, action, details) VALUES (?, ?, ?)",
            (admin_id, action, details)
        )
        await self.conn.commit()

    async def get_logs(self, limit: int = 50) -> list[dict]:
        """Получить последние логи."""
        async with self.conn.execute(
            "SELECT * FROM action_logs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ==================== КАНАЛЫ ====================

    async def get_channel(self) -> Optional[dict]:
        """Получить привязанный канал."""
        async with self.conn.execute(
            "SELECT * FROM channel_settings LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_channel(
        self, channel_id: int, channel_username: Optional[str], added_by: int
    ) -> None:
        """Установить канал для публикаций."""
        # Удаляем старый канал если есть
        await self.conn.execute("DELETE FROM channel_settings")
        await self.conn.execute(
            """INSERT INTO channel_settings (channel_id, channel_username, added_by)
               VALUES (?, ?, ?)""",
            (channel_id, channel_username, added_by)
        )
        await self.conn.commit()

    async def remove_channel(self) -> None:
        """Удалить привязку канала."""
        await self.conn.execute("DELETE FROM channel_settings")
        await self.conn.commit()

    # ==================== ПОСТЫ ТУРНИРОВ ====================

    async def get_tournament_post(self, tournament_id: int) -> Optional[dict]:
        """Получить пост турнира в канале."""
        async with self.conn.execute(
            "SELECT * FROM tournament_posts WHERE tournament_id = ?",
            (tournament_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def save_tournament_post(
        self, tournament_id: int, channel_id: int, message_id: int
    ) -> None:
        """Сохранить информацию о посте турнира."""
        await self.conn.execute(
            """INSERT OR REPLACE INTO tournament_posts
               (tournament_id, channel_id, message_id, published_at)
               VALUES (?, ?, ?, ?)""",
            (tournament_id, channel_id, message_id, datetime.now())
        )
        await self.conn.commit()

    async def delete_tournament_post(self, tournament_id: int) -> None:
        """Удалить запись о посте турнира."""
        await self.conn.execute(
            "DELETE FROM tournament_posts WHERE tournament_id = ?",
            (tournament_id,)
        )
        await self.conn.commit()

    async def get_all_tournament_posts(self) -> list[dict]:
        """Получить все посты турниров."""
        async with self.conn.execute(
            "SELECT * FROM tournament_posts"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# Глобальный экземпляр
db = Database()
