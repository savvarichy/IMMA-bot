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
                prizes TEXT,
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

            -- Матчи (статусы: queued, active, completed)
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
                status TEXT DEFAULT 'queued',
                queue_position INTEGER DEFAULT 0,
                server_link TEXT,
                started_at TIMESTAMP,
                scheduled_time TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
            );

            -- Лобби (готовность игроков: ready, away)
            CREATE TABLE IF NOT EXISTS lobby (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                status TEXT DEFAULT 'away',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(id),
                UNIQUE(tournament_id, player_id)
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

            -- Резервный список турниров (игроки)
            CREATE TABLE IF NOT EXISTS tournament_reserve_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(id),
                UNIQUE(tournament_id, player_id)
            );

            -- Резервный список турниров (команды)
            CREATE TABLE IF NOT EXISTS tournament_reserve_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams(id),
                UNIQUE(tournament_id, team_id)
            );

            -- Баны игроков
            CREATE TABLE IF NOT EXISTS player_bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                banned_by INTEGER NOT NULL,
                reason TEXT,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_permanent BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (player_id) REFERENCES players(id),
                FOREIGN KEY (banned_by) REFERENCES admins(telegram_id)
            );

            -- Статусы участников турнира (для ручной системы матчей)
            CREATE TABLE IF NOT EXISTS tournament_participant_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                participant_id INTEGER NOT NULL,
                participant_type TEXT NOT NULL,
                status TEXT DEFAULT 'ready',
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                current_match_id INTEGER,
                eliminated_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                UNIQUE(tournament_id, participant_id, participant_type)
            );

            -- Индексы
            CREATE INDEX IF NOT EXISTS idx_players_telegram ON players(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_teams_captain ON teams(captain_id);
            CREATE INDEX IF NOT EXISTS idx_teams_invite ON teams(invite_code);
            CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);
            CREATE INDEX IF NOT EXISTS idx_matches_tournament ON matches(tournament_id);
            CREATE INDEX IF NOT EXISTS idx_tournament_posts ON tournament_posts(tournament_id);
            CREATE INDEX IF NOT EXISTS idx_player_bans ON player_bans(player_id, is_active);
        """)
        await self.conn.commit()

        # Миграции для старых баз данных
        await self._run_migrations()

    async def _run_migrations(self) -> None:
        """Выполнить миграции для старых баз."""
        # Проверяем и добавляем недостающие колонки в matches
        try:
            await self.conn.execute("SELECT created_at FROM matches LIMIT 1")
        except Exception:
            await self.conn.execute("ALTER TABLE matches ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            await self.conn.commit()

        try:
            await self.conn.execute("SELECT started_at FROM matches LIMIT 1")
        except Exception:
            await self.conn.execute("ALTER TABLE matches ADD COLUMN started_at TIMESTAMP")
            await self.conn.commit()

        try:
            await self.conn.execute("SELECT completed_at FROM matches LIMIT 1")
        except Exception:
            await self.conn.execute("ALTER TABLE matches ADD COLUMN completed_at TIMESTAMP")
            await self.conn.commit()

        try:
            await self.conn.execute("SELECT queue_position FROM matches LIMIT 1")
        except Exception:
            await self.conn.execute("ALTER TABLE matches ADD COLUMN queue_position INTEGER DEFAULT 0")
            await self.conn.commit()

        try:
            await self.conn.execute("SELECT server_link FROM matches LIMIT 1")
        except Exception:
            await self.conn.execute("ALTER TABLE matches ADD COLUMN server_link TEXT")
            await self.conn.commit()

        try:
            await self.conn.execute("SELECT scheduled_time FROM matches LIMIT 1")
        except Exception:
            await self.conn.execute("ALTER TABLE matches ADD COLUMN scheduled_time TIMESTAMP")
            await self.conn.commit()

        # Миграция для losses в tournament_participant_status
        try:
            await self.conn.execute("SELECT losses FROM tournament_participant_status LIMIT 1")
        except Exception:
            await self.conn.execute("ALTER TABLE tournament_participant_status ADD COLUMN losses INTEGER DEFAULT 0")
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

    async def get_all_players(self, search: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Получить всех игроков."""
        if search:
            async with self.conn.execute(
                """SELECT * FROM players
                   WHERE nickname LIKE ? OR username LIKE ?
                   ORDER BY created_at DESC LIMIT ?""",
                (f"%{search}%", f"%{search}%", limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        else:
            async with self.conn.execute(
                "SELECT * FROM players ORDER BY created_at DESC LIMIT ?",
                (limit,)
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

    async def get_all_teams(self, limit: int = 50) -> list[dict]:
        """Получить все команды."""
        async with self.conn.execute(
            "SELECT * FROM teams ORDER BY created_at DESC LIMIT ?",
            (limit,)
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
        created_by: int,
        prizes: Optional[dict] = None
    ) -> int:
        """Создать турнир."""
        prizes_json = json.dumps(prizes) if prizes else None
        async with self.conn.execute(
            """INSERT INTO tournaments
               (name, format, maps, max_participants, prize_type, prize_amount,
                prizes, start_time, registration_deadline, checkin_hours, created_by, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')""",
            (name, format, json.dumps(maps), max_participants, prize_type,
             prize_amount, prizes_json, start_time, registration_deadline, checkin_hours, created_by)
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
                if data.get("prizes"):
                    data["prizes"] = json.loads(data["prizes"])
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
                if data.get("prizes"):
                    data["prizes"] = json.loads(data["prizes"])
                result.append(data)
            return result

    async def get_recent_tournaments(self, limit: int = 10) -> list[dict]:
        """Получить последние турниры для дублирования."""
        async with self.conn.execute(
            """SELECT * FROM tournaments
               ORDER BY created_at DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                data = dict(r)
                data["maps"] = json.loads(data["maps"])
                if data.get("prizes"):
                    data["prizes"] = json.loads(data["prizes"])
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
                if data.get("prizes"):
                    data["prizes"] = json.loads(data["prizes"])
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
                if data.get("prizes"):
                    data["prizes"] = json.loads(data["prizes"])
                result.append(data)
            return result

    async def update_tournament(self, tournament_id: int, **kwargs) -> None:
        """Обновить турнир."""
        if not kwargs:
            return
        if "maps" in kwargs:
            kwargs["maps"] = json.dumps(kwargs["maps"])
        if "prizes" in kwargs and kwargs["prizes"] is not None:
            kwargs["prizes"] = json.dumps(kwargs["prizes"])
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

    # ==================== СТАТИСТИКА ====================

    async def get_stats(self) -> dict:
        """Получить общую статистику."""
        stats = {}

        # Количество игроков
        async with self.conn.execute("SELECT COUNT(*) as cnt FROM players") as cursor:
            row = await cursor.fetchone()
            stats["total_players"] = row["cnt"] if row else 0

        # Количество команд
        async with self.conn.execute("SELECT COUNT(*) as cnt FROM teams") as cursor:
            row = await cursor.fetchone()
            stats["total_teams"] = row["cnt"] if row else 0

        # Турниры по статусам
        async with self.conn.execute(
            "SELECT status, COUNT(*) as cnt FROM tournaments GROUP BY status"
        ) as cursor:
            rows = await cursor.fetchall()
            stats["tournaments_by_status"] = {r["status"]: r["cnt"] for r in rows}

        # Общее количество турниров
        async with self.conn.execute("SELECT COUNT(*) as cnt FROM tournaments") as cursor:
            row = await cursor.fetchone()
            stats["total_tournaments"] = row["cnt"] if row else 0

        # Завершённых турниров
        stats["finished_tournaments"] = stats["tournaments_by_status"].get("finished", 0)

        # Активных турниров
        active_count = (
            stats["tournaments_by_status"].get("open", 0) +
            stats["tournaments_by_status"].get("checkin", 0) +
            stats["tournaments_by_status"].get("active", 0)
        )
        stats["active_tournaments"] = active_count

        return stats

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

    # ==================== РЕЗЕРВНЫЙ СПИСОК ====================

    async def get_player_active_tournament_count(self, player_id: int) -> int:
        """Получить количество активных турниров игрока."""
        async with self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tournament_players tp
               JOIN tournaments t ON tp.tournament_id = t.id
               WHERE tp.player_id = ? AND t.status IN ('open', 'checkin', 'active')""",
            (player_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def get_team_active_tournament_count(self, team_id: int) -> int:
        """Получить количество активных турниров команды."""
        async with self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tournament_teams tt
               JOIN tournaments t ON tt.tournament_id = t.id
               WHERE tt.team_id = ? AND t.status IN ('open', 'checkin', 'active')""",
            (team_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def add_player_to_reserve(self, tournament_id: int, player_id: int) -> bool:
        """Добавить игрока в резервный список."""
        # Получаем текущую позицию
        async with self.conn.execute(
            """SELECT COALESCE(MAX(position), 0) + 1 as next_pos
               FROM tournament_reserve_players WHERE tournament_id = ?""",
            (tournament_id,)
        ) as cursor:
            row = await cursor.fetchone()
            position = row["next_pos"] if row else 1

        # Проверяем лимит резерва
        if position > config.RESERVE_LIST_SIZE:
            return False

        try:
            await self.conn.execute(
                """INSERT INTO tournament_reserve_players (tournament_id, player_id, position)
                   VALUES (?, ?, ?)""",
                (tournament_id, player_id, position)
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def add_team_to_reserve(self, tournament_id: int, team_id: int) -> bool:
        """Добавить команду в резервный список."""
        async with self.conn.execute(
            """SELECT COALESCE(MAX(position), 0) + 1 as next_pos
               FROM tournament_reserve_teams WHERE tournament_id = ?""",
            (tournament_id,)
        ) as cursor:
            row = await cursor.fetchone()
            position = row["next_pos"] if row else 1

        if position > config.RESERVE_LIST_SIZE:
            return False

        try:
            await self.conn.execute(
                """INSERT INTO tournament_reserve_teams (tournament_id, team_id, position)
                   VALUES (?, ?, ?)""",
                (tournament_id, team_id, position)
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def get_reserve_players(self, tournament_id: int) -> list[dict]:
        """Получить резервный список игроков."""
        async with self.conn.execute(
            """SELECT p.*, rp.position FROM players p
               JOIN tournament_reserve_players rp ON p.id = rp.player_id
               WHERE rp.tournament_id = ?
               ORDER BY rp.position""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_reserve_teams(self, tournament_id: int) -> list[dict]:
        """Получить резервный список команд."""
        async with self.conn.execute(
            """SELECT t.*, rt.position FROM teams t
               JOIN tournament_reserve_teams rt ON t.id = rt.team_id
               WHERE rt.tournament_id = ?
               ORDER BY rt.position""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def remove_player_from_reserve(self, tournament_id: int, player_id: int) -> None:
        """Удалить игрока из резервного списка."""
        await self.conn.execute(
            "DELETE FROM tournament_reserve_players WHERE tournament_id = ? AND player_id = ?",
            (tournament_id, player_id)
        )
        await self.conn.commit()

    async def remove_team_from_reserve(self, tournament_id: int, team_id: int) -> None:
        """Удалить команду из резервного списка."""
        await self.conn.execute(
            "DELETE FROM tournament_reserve_teams WHERE tournament_id = ? AND team_id = ?",
            (tournament_id, team_id)
        )
        await self.conn.commit()

    async def is_player_in_reserve(self, tournament_id: int, player_id: int) -> bool:
        """Проверить, находится ли игрок в резерве."""
        async with self.conn.execute(
            "SELECT 1 FROM tournament_reserve_players WHERE tournament_id = ? AND player_id = ?",
            (tournament_id, player_id)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def is_team_in_reserve(self, tournament_id: int, team_id: int) -> bool:
        """Проверить, находится ли команда в резерве."""
        async with self.conn.execute(
            "SELECT 1 FROM tournament_reserve_teams WHERE tournament_id = ? AND team_id = ?",
            (tournament_id, team_id)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def get_reserve_position(self, tournament_id: int, player_id: int = None, team_id: int = None) -> int:
        """Получить позицию в резерве (0 если не в резерве)."""
        if player_id:
            async with self.conn.execute(
                "SELECT position FROM tournament_reserve_players WHERE tournament_id = ? AND player_id = ?",
                (tournament_id, player_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row["position"] if row else 0
        elif team_id:
            async with self.conn.execute(
                "SELECT position FROM tournament_reserve_teams WHERE tournament_id = ? AND team_id = ?",
                (tournament_id, team_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row["position"] if row else 0
        return 0

    # ==================== БАНЫ ====================

    async def ban_player(
        self, player_id: int, banned_by: int, reason: str = None,
        days: int = None, is_permanent: bool = False
    ) -> bool:
        """Забанить игрока."""
        from datetime import datetime, timedelta
        expires_at = None
        if days and not is_permanent:
            expires_at = datetime.now() + timedelta(days=days)

        try:
            await self.conn.execute(
                """INSERT INTO player_bans (player_id, banned_by, reason, expires_at, is_permanent)
                   VALUES (?, ?, ?, ?, ?)""",
                (player_id, banned_by, reason, expires_at, is_permanent)
            )
            await self.conn.commit()
            return True
        except Exception:
            return False

    async def unban_player(self, player_id: int) -> bool:
        """Разбанить игрока."""
        await self.conn.execute(
            "UPDATE player_bans SET is_active = 0 WHERE player_id = ? AND is_active = 1",
            (player_id,)
        )
        await self.conn.commit()
        return True

    async def is_player_banned(self, player_id: int) -> bool:
        """Проверить, забанен ли игрок."""
        from datetime import datetime
        async with self.conn.execute(
            """SELECT * FROM player_bans
               WHERE player_id = ? AND is_active = 1
               AND (is_permanent = 1 OR expires_at > ?)""",
            (player_id, datetime.now())
        ) as cursor:
            return await cursor.fetchone() is not None

    async def get_player_ban(self, player_id: int) -> dict | None:
        """Получить информацию о бане игрока."""
        from datetime import datetime
        async with self.conn.execute(
            """SELECT * FROM player_bans
               WHERE player_id = ? AND is_active = 1
               AND (is_permanent = 1 OR expires_at > ?)
               ORDER BY banned_at DESC LIMIT 1""",
            (player_id, datetime.now())
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_bans(self, active_only: bool = True) -> list[dict]:
        """Получить список всех банов."""
        from datetime import datetime
        if active_only:
            async with self.conn.execute(
                """SELECT b.*, p.nickname, p.telegram_id
                   FROM player_bans b
                   JOIN players p ON b.player_id = p.id
                   WHERE b.is_active = 1
                   AND (b.is_permanent = 1 OR b.expires_at > ?)
                   ORDER BY b.banned_at DESC""",
                (datetime.now(),)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        else:
            async with self.conn.execute(
                """SELECT b.*, p.nickname, p.telegram_id
                   FROM player_bans b
                   JOIN players p ON b.player_id = p.id
                   ORDER BY b.banned_at DESC"""
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # ==================== УДАЛЕНИЕ ТУРНИРА ====================

    async def delete_tournament(self, tournament_id: int) -> bool:
        """Полностью удалить турнир."""
        try:
            await self.conn.execute(
                "DELETE FROM tournaments WHERE id = ?", (tournament_id,)
            )
            await self.conn.commit()
            return True
        except Exception:
            return False

    # ==================== РАСШИРЕННАЯ СТАТИСТИКА ====================

    async def get_extended_stats(self) -> dict:
        """Получить расширенную статистику."""
        from datetime import datetime, timedelta
        stats = await self.get_stats()

        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        # Новые игроки за сегодня
        async with self.conn.execute(
            "SELECT COUNT(*) as cnt FROM players WHERE created_at >= ?",
            (today_start,)
        ) as cursor:
            row = await cursor.fetchone()
            stats["players_today"] = row["cnt"] if row else 0

        # Новые игроки за неделю
        async with self.conn.execute(
            "SELECT COUNT(*) as cnt FROM players WHERE created_at >= ?",
            (week_start,)
        ) as cursor:
            row = await cursor.fetchone()
            stats["players_week"] = row["cnt"] if row else 0

        # Новые игроки за месяц
        async with self.conn.execute(
            "SELECT COUNT(*) as cnt FROM players WHERE created_at >= ?",
            (month_start,)
        ) as cursor:
            row = await cursor.fetchone()
            stats["players_month"] = row["cnt"] if row else 0

        # Турниры за неделю
        async with self.conn.execute(
            "SELECT COUNT(*) as cnt FROM tournaments WHERE created_at >= ?",
            (week_start,)
        ) as cursor:
            row = await cursor.fetchone()
            stats["tournaments_week"] = row["cnt"] if row else 0

        # Матчи за неделю
        async with self.conn.execute(
            "SELECT COUNT(*) as cnt FROM matches WHERE created_at >= ?",
            (week_start,)
        ) as cursor:
            row = await cursor.fetchone()
            stats["matches_week"] = row["cnt"] if row else 0

        # Топ-5 игроков по победам
        async with self.conn.execute(
            """SELECT p.nickname, p.tournaments_won as wins,
               (p.tournaments_played - p.tournaments_won) as losses
               FROM players p
               WHERE p.tournaments_won > 0
               ORDER BY p.tournaments_won DESC LIMIT 5"""
        ) as cursor:
            rows = await cursor.fetchall()
            stats["top_players"] = [dict(r) for r in rows]

        # Активные баны
        async with self.conn.execute(
            """SELECT COUNT(*) as cnt FROM player_bans
               WHERE is_active = 1 AND (is_permanent = 1 OR expires_at > ?)""",
            (now,)
        ) as cursor:
            row = await cursor.fetchone()
            stats["active_bans"] = row["cnt"] if row else 0

        return stats

    # ==================== ОЧЕРЕДЬ МАТЧЕЙ ====================

    async def get_queued_matches(self, tournament_id: int) -> list[dict]:
        """Получить матчи в очереди (pending)."""
        async with self.conn.execute(
            """SELECT * FROM matches
               WHERE tournament_id = ? AND status = 'pending'
               AND participant1_id IS NOT NULL AND participant2_id IS NOT NULL
               ORDER BY round, match_number""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_active_matches(self, tournament_id: int) -> list[dict]:
        """Получить активные матчи."""
        async with self.conn.execute(
            """SELECT * FROM matches
               WHERE tournament_id = ? AND status = 'active'
               ORDER BY started_at""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_active_matches_count(self, tournament_id: int) -> int:
        """Количество активных матчей."""
        async with self.conn.execute(
            "SELECT COUNT(*) as cnt FROM matches WHERE tournament_id = ? AND status = 'active'",
            (tournament_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def start_match(self, match_id: int, server_link: str = None) -> bool:
        """Активировать матч (начать игру)."""
        from datetime import datetime
        await self.conn.execute(
            """UPDATE matches SET status = 'active', started_at = ?, server_link = ?
               WHERE id = ?""",
            (datetime.now(), server_link, match_id)
        )
        await self.conn.commit()
        return True

    async def complete_match(self, match_id: int) -> None:
        """Завершить матч."""
        from datetime import datetime
        await self.conn.execute(
            "UPDATE matches SET status = 'completed', completed_at = ? WHERE id = ?",
            (datetime.now(), match_id)
        )
        await self.conn.commit()

    async def get_match_queue_position(self, match_id: int) -> int:
        """Получить позицию матча в очереди."""
        match = await self.get_match(match_id)
        if not match or match["status"] != "queued":
            return 0

        async with self.conn.execute(
            """SELECT COUNT(*) as cnt FROM matches
               WHERE tournament_id = ? AND status = 'queued'
               AND participant1_id IS NOT NULL AND participant2_id IS NOT NULL
               AND (round < ? OR (round = ? AND match_number < ?))""",
            (match["tournament_id"], match["round"], match["round"], match["match_number"])
        ) as cursor:
            row = await cursor.fetchone()
            return (row["cnt"] if row else 0) + 1

    async def update_match_server_link(self, match_id: int, server_link: str) -> None:
        """Обновить ссылку на сервер."""
        await self.conn.execute(
            "UPDATE matches SET server_link = ? WHERE id = ?",
            (server_link, match_id)
        )
        await self.conn.commit()

    # ==================== ЛОББИ ====================

    async def set_player_lobby_status(self, tournament_id: int, player_id: int, status: str) -> None:
        """Установить статус игрока в лобби."""
        from datetime import datetime
        await self.conn.execute(
            """INSERT INTO lobby (tournament_id, player_id, status, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(tournament_id, player_id)
               DO UPDATE SET status = ?, updated_at = ?""",
            (tournament_id, player_id, status, datetime.now(), status, datetime.now())
        )
        await self.conn.commit()

    async def get_player_lobby_status(self, tournament_id: int, player_id: int) -> str:
        """Получить статус игрока в лобби."""
        async with self.conn.execute(
            "SELECT status FROM lobby WHERE tournament_id = ? AND player_id = ?",
            (tournament_id, player_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row["status"] if row else "away"

    async def get_ready_players(self, tournament_id: int) -> list[dict]:
        """Получить готовых игроков в лобби."""
        async with self.conn.execute(
            """SELECT l.*, p.nickname, p.telegram_id
               FROM lobby l
               JOIN players p ON l.player_id = p.id
               WHERE l.tournament_id = ? AND l.status = 'ready'
               ORDER BY l.updated_at""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def clear_tournament_lobby(self, tournament_id: int) -> None:
        """Очистить лобби турнира."""
        await self.conn.execute(
            "DELETE FROM lobby WHERE tournament_id = ?",
            (tournament_id,)
        )
        await self.conn.commit()

    # ==================== СТАТУСЫ УЧАСТНИКОВ (РУЧНАЯ СИСТЕМА) ====================

    async def init_participant_statuses(self, tournament_id: int) -> None:
        """Инициализировать статусы участников турнира (учитывая check-in)."""
        tournament = await self.get_tournament(tournament_id)
        if not tournament:
            return

        # Учитываем check-in: если включён - берём только прошедших check-in
        has_checkin = tournament["checkin_hours"] > 0

        if tournament["format"] == "1v1":
            if has_checkin:
                players = await self.get_checked_in_players(tournament_id)
            else:
                players = await self.get_tournament_players(tournament_id)
            for player in players:
                await self.set_participant_status(
                    tournament_id, player["id"], "player", "ready"
                )
        else:
            if has_checkin:
                teams = await self.get_checked_in_teams(tournament_id)
            else:
                teams = await self.get_tournament_teams(tournament_id)
            for team in teams:
                await self.set_participant_status(
                    tournament_id, team["id"], "team", "ready"
                )

    async def set_participant_status(
        self,
        tournament_id: int,
        participant_id: int,
        participant_type: str,
        status: str,
        current_match_id: int = None
    ) -> None:
        """Установить статус участника турнира."""
        from datetime import datetime
        eliminated_at = datetime.now() if status == "eliminated" else None

        await self.conn.execute(
            """INSERT INTO tournament_participant_status
               (tournament_id, participant_id, participant_type, status, current_match_id, eliminated_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(tournament_id, participant_id, participant_type)
               DO UPDATE SET status = ?, current_match_id = ?, eliminated_at = COALESCE(eliminated_at, ?), updated_at = ?""",
            (tournament_id, participant_id, participant_type, status, current_match_id, eliminated_at, datetime.now(),
             status, current_match_id, eliminated_at, datetime.now())
        )
        await self.conn.commit()

    async def get_participant_status(
        self,
        tournament_id: int,
        participant_id: int,
        participant_type: str
    ) -> Optional[dict]:
        """Получить статус участника."""
        async with self.conn.execute(
            """SELECT * FROM tournament_participant_status
               WHERE tournament_id = ? AND participant_id = ? AND participant_type = ?""",
            (tournament_id, participant_id, participant_type)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_participants_by_status(
        self,
        tournament_id: int,
        status: str
    ) -> list[dict]:
        """Получить участников по статусу."""
        async with self.conn.execute(
            """SELECT * FROM tournament_participant_status
               WHERE tournament_id = ? AND status = ?
               ORDER BY wins DESC, updated_at""",
            (tournament_id, status)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_available_participants(self, tournament_id: int) -> list[dict]:
        """Получить доступных участников (ready)."""
        return await self.get_participants_by_status(tournament_id, "ready")

    async def get_eliminated_participants(self, tournament_id: int) -> list[dict]:
        """Получить выбывших участников."""
        return await self.get_participants_by_status(tournament_id, "eliminated")

    async def increment_participant_wins(
        self,
        tournament_id: int,
        participant_id: int,
        participant_type: str
    ) -> None:
        """Увеличить счётчик побед участника."""
        await self.conn.execute(
            """UPDATE tournament_participant_status SET wins = wins + 1, updated_at = ?
               WHERE tournament_id = ? AND participant_id = ? AND participant_type = ?""",
            (datetime.now(), tournament_id, participant_id, participant_type)
        )
        await self.conn.commit()

    async def increment_participant_losses(
        self,
        tournament_id: int,
        participant_id: int,
        participant_type: str
    ) -> None:
        """Увеличить счётчик поражений участника."""
        await self.conn.execute(
            """UPDATE tournament_participant_status SET losses = losses + 1, updated_at = ?
               WHERE tournament_id = ? AND participant_id = ? AND participant_type = ?""",
            (datetime.now(), tournament_id, participant_id, participant_type)
        )
        await self.conn.commit()

    async def restore_participant(
        self,
        tournament_id: int,
        participant_id: int,
        participant_type: str
    ) -> None:
        """Вернуть выбывшего участника в турнир."""
        await self.conn.execute(
            """UPDATE tournament_participant_status
               SET status = 'ready', eliminated_at = NULL, updated_at = ?
               WHERE tournament_id = ? AND participant_id = ? AND participant_type = ?""",
            (datetime.now(), tournament_id, participant_id, participant_type)
        )
        await self.conn.commit()

    async def get_tournament_standings(self, tournament_id: int) -> list[dict]:
        """Получить таблицу результатов турнира."""
        async with self.conn.execute(
            """SELECT * FROM tournament_participant_status
               WHERE tournament_id = ?
               ORDER BY
                   CASE status WHEN 'eliminated' THEN 1 ELSE 0 END,
                   wins DESC,
                   updated_at""",
            (tournament_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def count_remaining_participants(self, tournament_id: int) -> int:
        """Подсчитать оставшихся участников (не eliminated)."""
        async with self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tournament_participant_status
               WHERE tournament_id = ? AND status != 'eliminated'""",
            (tournament_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    # ==================== РУЧНОЕ СОЗДАНИЕ МАТЧЕЙ ====================

    async def create_manual_match(
        self,
        tournament_id: int,
        participant1_id: int,
        participant2_id: int,
        participant_type: str,
        server_link: str = None
    ) -> int:
        """Создать матч вручную и сразу активировать."""
        from datetime import datetime

        # Получаем номер следующего матча
        async with self.conn.execute(
            "SELECT COALESCE(MAX(match_number), 0) + 1 as next_num FROM matches WHERE tournament_id = ?",
            (tournament_id,)
        ) as cursor:
            row = await cursor.fetchone()
            match_number = row["next_num"] if row else 1

        # Создаём матч со статусом active
        async with self.conn.execute(
            """INSERT INTO matches
               (tournament_id, round, match_number, participant1_id, participant2_id,
                participant1_type, status, server_link, started_at)
               VALUES (?, 1, ?, ?, ?, ?, 'active', ?, ?)""",
            (tournament_id, match_number, participant1_id, participant2_id,
             participant_type, server_link, datetime.now())
        ) as cursor:
            match_id = cursor.lastrowid
            await self.conn.commit()

        # Обновляем статусы участников
        await self.set_participant_status(
            tournament_id, participant1_id, participant_type, "in_match", match_id
        )
        await self.set_participant_status(
            tournament_id, participant2_id, participant_type, "in_match", match_id
        )

        return match_id

    async def complete_manual_match(
        self,
        match_id: int,
        winner_id: int,
        score1: int,
        score2: int
    ) -> bool:
        """Завершить матч и обновить статусы участников (оба возвращаются в ready)."""
        from datetime import datetime

        match = await self.get_match(match_id)
        if not match or match["status"] != "active":
            return False

        # Определяем проигравшего
        loser_id = match["participant2_id"] if winner_id == match["participant1_id"] else match["participant1_id"]

        # Обновляем матч
        await self.set_match_result(match_id, score1, score2, winner_id)

        # Оба участника возвращаются в ready (турнир завершается только вручную)
        await self.set_participant_status(
            match["tournament_id"], winner_id, match["participant1_type"], "ready"
        )
        await self.set_participant_status(
            match["tournament_id"], loser_id, match["participant1_type"], "ready"
        )

        # Увеличиваем счётчик побед победителю
        await self.increment_participant_wins(
            match["tournament_id"], winner_id, match["participant1_type"]
        )

        # Увеличиваем счётчик поражений проигравшему
        await self.increment_participant_losses(
            match["tournament_id"], loser_id, match["participant1_type"]
        )

        return True

    async def cancel_match(self, match_id: int) -> bool:
        """Отменить матч и вернуть участников в ready."""
        match = await self.get_match(match_id)
        if not match or match["status"] != "active":
            return False

        # Удаляем матч
        await self.conn.execute("DELETE FROM matches WHERE id = ?", (match_id,))
        await self.conn.commit()

        # Возвращаем участников в ready
        await self.set_participant_status(
            match["tournament_id"], match["participant1_id"],
            match["participant1_type"], "ready"
        )
        await self.set_participant_status(
            match["tournament_id"], match["participant2_id"],
            match["participant1_type"], "ready"
        )

        return True


# Глобальный экземпляр
db = Database()
